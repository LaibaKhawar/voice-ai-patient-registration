"""Server-side registration state machine behind the voice agent's tools.

The LLM handles conversation; this module owns the truth. Each tool call loads
the call's CallSession row (locked FOR UPDATE so concurrent tool calls in one
call are serialized), applies a validated change, and returns a structured
result the LLM turns into speech.

States:  collecting -> awaiting_confirmation -> completed
                 ^              |                    |
                 +--- any edit -+---- edit after save (becomes an update)

Guarantees enforced here (not just requested in the prompt):
- Only values that pass app/validation.py enter the draft.
- Nothing is written to `patients` unless review_registration read back the
  exact current draft (hash match) AND the caller confirmed.
- Saving is idempotent per call (Idempotency key "vapi-call:<call id>").
- Identity of an existing patient is only revealed after phone + DOB match.
"""

import hashlib
import json
import logging
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import validation as v
from app.config import get_settings
from app.logging_utils import log_event, redact
from app.models import CallSession, Patient
from app.schemas import PatientCreate, PatientUpdate
from app.services import patients as svc

log = logging.getLogger("voice.registration")

MAX_VERIFICATION_ATTEMPTS = 2


class ToolError(Exception):
    """A failure the agent should explain to the caller (returned as an error result)."""


def clinic_today() -> date:
    return datetime.now(ZoneInfo(get_settings().clinic_timezone)).date()


# --------------------------------------------------------------------------- #
# Session helpers
# --------------------------------------------------------------------------- #

def lock_session(db: Session, vapi_call_id: str, caller_number: str | None = None) -> CallSession:
    """Get-or-create the call's session row and lock it for this transaction."""
    db.execute(
        insert(CallSession)
        .values(vapi_call_id=vapi_call_id, caller_number=caller_number, draft={},
                state="collecting", mode="create")
        .on_conflict_do_nothing(index_elements=["vapi_call_id"])
    )
    session = db.scalar(
        select(CallSession).where(CallSession.vapi_call_id == vapi_call_id).with_for_update()
    )
    assert session is not None
    if caller_number and not session.caller_number:
        session.caller_number = caller_number
    return session


def _draft_hash(draft: dict[str, Any], mode: str) -> str:
    return hashlib.sha256(json.dumps([mode, draft], sort_keys=True).encode()).hexdigest()


def _to_storable(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, v.Sex):
        return value.value
    return value


def _missing_required(draft: dict[str, Any]) -> list[str]:
    return [f for f in v.REQUIRED_FIELDS if not draft.get(f)]


def _set_draft(session: CallSession, draft: dict[str, Any]) -> None:
    # Reassign (not mutate) so SQLAlchemy detects the JSONB change.
    session.draft = dict(draft)
    if session.state == "awaiting_confirmation":
        # Anything read back earlier is now stale; it must be read back again.
        session.state = "collecting"
        session.reviewed_hash = None
    if session.state == "completed" and session.patient_id:
        # Caller is correcting a record we already saved during this call:
        # the next submit updates that record instead of creating another.
        session.state = "collecting"
        session.reviewed_hash = None
        session.mode = "update"
        session.verified_patient_id = session.patient_id


# --------------------------------------------------------------------------- #
# Spoken formatting (what the agent reads back)
# --------------------------------------------------------------------------- #

def _speak_phone(digits: str) -> str:
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


def spoken_value(field: str, value: Any) -> str:
    if value in (None, ""):
        return "not provided"
    if field == "date_of_birth":
        d = date.fromisoformat(value) if isinstance(value, str) else value
        return f"{d.strftime('%B')} {d.day}, {d.year} ({d.strftime('%m/%d/%Y')})"
    if field in {"phone_number", "emergency_contact_phone"}:
        return _speak_phone(value)
    if field == "state":
        return f"{v.US_STATES.get(value, value)} ({value})"
    if field in {"first_name", "last_name"}:
        return f"{value} (spelled {'-'.join(value.upper())})"
    return str(value)


def _readback(draft: dict[str, Any]) -> dict[str, str]:
    fields = [f for f in v.ALL_FIELDS if draft.get(f) not in (None, "")]
    return {v.FIELD_LABELS[f]: spoken_value(f, draft[f]) for f in fields}


# --------------------------------------------------------------------------- #
# Existing-patient detection (bonus: duplicate detection)
# --------------------------------------------------------------------------- #

def _check_phone_match(db: Session, session: CallSession) -> dict[str, Any] | None:
    """After a phone number is captured, look for an existing live patient.

    Returns a notice for the agent, or None. Never includes identity unless
    the date of birth already on the draft matches the record.
    """
    if session.mode != "create" or session.verified_patient_id or session.patient_id:
        return None
    phone = session.draft.get("phone_number")
    if not phone:
        return None
    match = svc.find_live_by_phone(db, phone)
    if match is None:
        session.matched_patient_id = None
        return None
    session.matched_patient_id = match.patient_id
    dob = session.draft.get("date_of_birth")
    if dob and dob == match.date_of_birth.isoformat():
        session.verified_patient_id = match.patient_id
        return {
            "existing_record": "verified",
            "existing_patient_name": f"{match.first_name} {match.last_name}",
            "instruction": (
                "Phone number and date of birth match an existing patient. Say: "
                f"'It looks like we already have a record for {match.first_name} {match.last_name}. "
                "Would you like to update your information instead?' Then call use_existing_record."
            ),
        }
    if dob:
        # Same phone, different DOB: likely a family member sharing a number.
        # Treat as a new registration and reveal nothing.
        session.matched_patient_id = None
        return None
    return {
        "existing_record": "needs_verification",
        "instruction": (
            "This phone number is already on file. Do NOT mention any name. Tell the caller "
            "the number is already on file and, to protect their privacy, ask for their date "
            "of birth, then call verify_existing_patient."
        ),
    }


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #

def update_patient_info(db: Session, session: CallSession, args: dict[str, Any]) -> dict[str, Any]:
    fields = args.get("fields") if isinstance(args.get("fields"), dict) else args
    clear = args.get("clear_fields") or []
    draft = dict(session.draft)
    saved: dict[str, str] = {}
    errors: dict[str, str] = {}

    for name, raw in fields.items():
        if name in ("clear_fields", "fields") or raw in (None, ""):
            continue
        if name not in v.FIELD_VALIDATORS:
            errors[name] = "unknown field"
            continue
        try:
            if name == "date_of_birth":
                value = v.date_of_birth(raw, today=clinic_today())
            else:
                value = v.validate_field(name, raw)
        except ValueError as exc:
            errors[name] = f"{v.FIELD_LABELS[name]} {exc}"
            continue
        draft[name] = _to_storable(value)
        saved[name] = spoken_value(name, draft[name])

    cleared = []
    for name in clear:
        if name in v.OPTIONAL_FIELDS and name in draft:
            draft.pop(name)
            cleared.append(name)

    if saved or cleared:
        _set_draft(session, draft)

    result: dict[str, Any] = {
        "saved": saved,
        "invalid": errors,
        "missing_required": [v.FIELD_LABELS[f] for f in _missing_required(session.draft)],
        "today": clinic_today().isoformat(),
    }
    if cleared:
        result["cleared"] = cleared
    if errors:
        result["instruction"] = (
            "Some values were rejected. Briefly tell the caller what was wrong with each "
            "and ask again for just those fields."
        )
    if "phone_number" in saved or "date_of_birth" in saved:
        notice = _check_phone_match(db, session)
        if notice:
            result.update(notice)
    log_event(log, "tool.update_patient_info", call_id=session.vapi_call_id,
              saved=redact({k: session.draft.get(k) for k in saved}), invalid=list(errors))
    return result


def verify_existing_patient(db: Session, session: CallSession, args: dict[str, Any]) -> dict[str, Any]:
    if not session.matched_patient_id:
        return {"verified": False, "instruction": "No existing record is pending verification. Continue the registration."}
    if session.verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
        return {"verified": False, "instruction": "Verification limit reached. Continue as a new registration without revealing any record details."}
    try:
        dob = v.date_of_birth(args.get("date_of_birth"), today=clinic_today())
    except ValueError as exc:
        return {"verified": False, "invalid": {"date of birth": f"date of birth {exc}"},
                "instruction": "Ask the caller to repeat their date of birth."}

    session.verification_attempts += 1
    draft = dict(session.draft)
    draft["date_of_birth"] = dob.isoformat()
    _set_draft(session, draft)

    patient = db.get(Patient, session.matched_patient_id)
    if patient and patient.deleted_at is None and patient.date_of_birth == dob:
        session.verified_patient_id = patient.patient_id
        log_event(log, "tool.verify_existing_patient", call_id=session.vapi_call_id, verified=True)
        return {
            "verified": True,
            "existing_patient_name": f"{patient.first_name} {patient.last_name}",
            "instruction": (
                f"Say: 'It looks like we already have a record for {patient.first_name} "
                f"{patient.last_name}. Would you like to update your information instead?' "
                "Then call use_existing_record with their answer."
            ),
        }

    log_event(log, "tool.verify_existing_patient", call_id=session.vapi_call_id, verified=False)
    if session.verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
        session.matched_patient_id = None
        return {"verified": False, "instruction": (
            "Could not verify. Do not reveal anything about the existing record. "
            "Continue with a new registration.")}
    return {"verified": False, "instruction": (
        "That date of birth doesn't match. Without revealing details, ask the caller to "
        "double-check their date of birth once more, or continue as a new registration.")}


def use_existing_record(db: Session, session: CallSession, args: dict[str, Any]) -> dict[str, Any]:
    update_existing = bool(args.get("update_existing"))
    if not update_existing:
        session.matched_patient_id = None
        session.mode = "create"
        return {"mode": "create", "instruction": "Continue collecting information for a new registration."}

    if not session.verified_patient_id:
        return {"mode": session.mode, "error": "The existing record has not been verified yet. Call verify_existing_patient first."}
    patient = db.get(Patient, session.verified_patient_id)
    if patient is None or patient.deleted_at is not None:
        session.mode = "create"
        return {"mode": "create", "instruction": "That record is no longer available. Continue as a new registration."}

    # Start from what is on file; anything the caller already said this call wins.
    on_file = {f: _to_storable(getattr(patient, f)) for f in v.ALL_FIELDS if getattr(patient, f) not in (None, "")}
    caller_supplied = {k: val for k, val in session.draft.items() if val not in (None, "")}
    session.mode = "update"
    _set_draft(session, {**on_file, **caller_supplied})
    changed = sorted(k for k, val in caller_supplied.items() if on_file.get(k) != val)
    return {
        "mode": "update",
        "fields_on_file": [v.FIELD_LABELS[f] for f in on_file],
        "already_changed_this_call": [v.FIELD_LABELS[f] for f in changed],
        "instruction": (
            "Ask the caller what they would like to update. Save changes with update_patient_info. "
            "When they're done, call review_registration and read everything back."
        ),
    }


def review_registration(db: Session, session: CallSession, args: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_required(session.draft)
    if missing:
        return {
            "ready": False,
            "missing_required": [v.FIELD_LABELS[f] for f in missing],
            "instruction": "Collect the missing required fields before reviewing.",
        }
    # The caller must be offered the optional fields before the read-back. The
    # first review request of a new registration is always bounced back with an
    # explicit instruction (unless the caller already volunteered optional data);
    # the server remembers the offer was prompted. This doesn't rely on the LLM
    # truthfully reporting that it asked.
    has_optional = any(session.draft.get(f) for f in v.OPTIONAL_FIELDS if f != "preferred_language")
    if session.mode == "create" and not session.optional_offered and not has_optional:
        session.optional_offered = True
        return {
            "ready": False,
            "instruction": (
                "Not yet. First ask the caller, in one short question, whether they'd like to add "
                "insurance information, an emergency contact, a preferred language, or an email. "
                "Wait for their answer and save anything they give with update_patient_info. "
                "Then call review_registration again."
            ),
        }
    session.state = "awaiting_confirmation"
    session.reviewed_hash = _draft_hash(session.draft, session.mode)
    return {
        "ready": True,
        "mode": session.mode,
        "read_back": _readback(session.draft),
        "instruction": (
            "Read back every item in read_back naturally, in a few short groups (name and date of birth; "
            "sex and contact; address; then any optional details). Spell out the first and last name. "
            "Then ask if everything is correct. If the caller confirms, call submit_registration "
            "with caller_confirmed=true. If they correct anything, save it with update_patient_info "
            "and call review_registration again."
        ),
    }


def submit_registration(db: Session, session: CallSession, args: dict[str, Any]) -> dict[str, Any]:
    # Idempotent replay: a retried/duplicated submit after success.
    if session.state == "completed" and session.patient_id:
        return {"success": True, "already_saved": True, "first_name": session.draft.get("first_name"),
                "instruction": "The registration is already saved. Confirm to the caller and wrap up."}

    if args.get("caller_confirmed") is not True:
        raise ToolError("The caller has not explicitly confirmed. Read back the information with review_registration and ask them to confirm.")
    if session.state != "awaiting_confirmation" or session.reviewed_hash != _draft_hash(session.draft, session.mode):
        raise ToolError("The information changed since it was last read back (or was never read back). Call review_registration and read it back first.")

    draft = session.draft
    try:
        if session.mode == "update" and session.verified_patient_id:
            patient = db.get(Patient, session.verified_patient_id)
            if patient is None or patient.deleted_at is not None:
                raise ToolError("The existing record could not be found. Offer to register them as a new patient.")
            # The draft started from the full record, so it is a full replacement:
            # optional fields the caller removed are cleared.
            payload = PatientUpdate(**{f: draft.get(f) for f in v.ALL_FIELDS})
            # update_patient commits; the session row changes ride in the same commit.
            session.state = "completed"
            session.patient_id = patient.patient_id
            session.outcome = "updated"
            session.last_error = None
            patient = svc.update_patient(db, patient, payload)
            outcome = "updated"
        else:
            payload = PatientCreate(**{f: draft.get(f) for f in v.ALL_FIELDS if draft.get(f) is not None})
            # Release the session row lock before the insert transaction.
            db.commit()
            patient, _ = svc.create_patient(db, payload, idempotency_key=f"vapi-call:{session.vapi_call_id}")
            session = lock_session(db, session.vapi_call_id)
            session.state = "completed"
            session.patient_id = patient.patient_id
            session.outcome = "registered"
            session.last_error = None
            outcome = "registered"
    except ToolError:
        raise
    except ValidationError as exc:
        db.rollback()
        problems = {".".join(str(p) for p in e["loc"]) or "record": e["msg"] for e in exc.errors()}
        raise ToolError(f"Some information failed final validation: {problems}. Ask the caller to correct it.")
    except Exception as exc:  # database outage, constraint violation, etc.
        db.rollback()
        session = lock_session(db, session.vapi_call_id)
        session.last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
        if session.outcome != "registered":
            session.outcome = "failed"
        db.commit()
        log.exception("registration.save_failed", extra={"fields": {"call_id": session.vapi_call_id}})
        return {
            "success": False,
            "instruction": (
                "The record could NOT be saved because of a system problem. Do not say it was saved. "
                "Apologize, explain that their information was not saved, and offer to try once more "
                "(call submit_registration again) or ask them to call back later."
            ),
        }

    log_event(log, "registration.saved", call_id=session.vapi_call_id, outcome=outcome,
              patient_id=str(patient.patient_id), payload=redact(dict(draft)))
    return {
        "success": True,
        "outcome": outcome,
        "first_name": patient.first_name,
        "say_next": f"You're all set, {patient.first_name}.",
        "instruction": (
            "Saved. Your very next words must be exactly say_next, before anything else. Then ask if "
            "there's anything else; if not, say a warm goodbye and end the call."
        ),
    }


def start_over(db: Session, session: CallSession, args: dict[str, Any]) -> dict[str, Any]:
    if session.state == "completed" and session.patient_id:
        return {"reset": False, "instruction": (
            "This caller's registration was already saved. Offer to correct specific details instead "
            "(use update_patient_info, then review_registration).")}
    session.draft = {}
    session.state = "collecting"
    session.mode = "create"
    session.reviewed_hash = None
    session.matched_patient_id = None
    session.verified_patient_id = None
    session.optional_offered = False
    return {"reset": True, "instruction": "All collected information was cleared. Start again from the caller's first and last name."}


TOOL_HANDLERS = {
    "update_patient_info": update_patient_info,
    "verify_existing_patient": verify_existing_patient,
    "use_existing_record": use_existing_record,
    "review_registration": review_registration,
    "submit_registration": submit_registration,
    "start_over": start_over,
}


def run_tool(db: Session, vapi_call_id: str, name: str, args: dict[str, Any],
             caller_number: str | None = None) -> dict[str, Any]:
    """Execute one tool call inside its own transaction. Raises ToolError for agent-facing errors."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise ToolError(f"Unknown tool {name}.")
    session = lock_session(db, vapi_call_id, caller_number)
    try:
        result = handler(db, session, args)
        db.commit()
        return result
    except ToolError:
        db.commit()  # keep any state changes made before the error (e.g. attempts)
        raise
    except Exception:
        db.rollback()
        raise
