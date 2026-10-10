"""Vapi server webhook: POST /vapi/webhook.

Telephony, speech-to-text, text-to-speech and the LLM run on Vapi. This
endpoint is the only integration point. It receives:
  - tool-calls          -> run registration tools, reply with results
  - status-update       -> record call start
  - end-of-call-report  -> store transcript/summary/timing, mark abandoned calls
Everything else is acknowledged and ignored.

Vapi ignores any non-200 response, so tool failures are returned as 200 with an
`error` string the agent can speak about. They are never raised as HTTP errors.
"""

import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.auth import require_vapi_secret
from app.db import get_db
from app.logging_utils import log_event, mask_value, redact
from app.voice.registration import ToolError, lock_session, run_tool

router = APIRouter(prefix="/vapi", tags=["voice"], dependencies=[Depends(require_vapi_secret)])
log = logging.getLogger("voice.webhook")


def _flat(obj: Any) -> str:
    # Vapi requires a single-line string result.
    return json.dumps(obj, separators=(",", ":"), default=str)


def _parse_args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _caller_number(message: dict[str, Any]) -> str | None:
    customer = message.get("customer") or (message.get("call") or {}).get("customer") or {}
    return customer.get("number")


@router.post("/webhook", summary="Vapi server URL (tool calls and call events)")
def vapi_webhook(body: dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    # Sync handler: FastAPI runs it in a threadpool, so blocking DB I/O never stalls the event loop.
    message = body.get("message") or {}
    kind = message.get("type")
    call_id = (message.get("call") or {}).get("id")

    if kind == "tool-calls":
        return {"results": _handle_tool_calls(db, message, call_id)}
    if kind == "status-update" and call_id:
        _handle_status(db, message, call_id)
    elif kind == "end-of-call-report" and call_id:
        _handle_end_of_call(db, message, call_id)
    return {}


def _handle_tool_calls(db: Session, message: dict[str, Any], call_id: str | None) -> list[dict[str, Any]]:
    results = []
    caller = _caller_number(message)
    for tool_call in message.get("toolCallList") or []:
        tc_id = tool_call.get("id")
        fn = tool_call.get("function") or {}
        name = fn.get("name") or tool_call.get("name") or ""
        args = _parse_args(fn.get("arguments", tool_call.get("arguments")))
        entry: dict[str, Any] = {"name": name, "toolCallId": tc_id}
        if not call_id:
            entry["error"] = "No call id on request."
            results.append(entry)
            continue
        try:
            entry["result"] = _flat(run_tool(db, call_id, name, args, caller))
        except ToolError as exc:
            entry["error"] = str(exc)
        except Exception:
            log.exception("tool.crashed", extra={"fields": {"call_id": call_id, "tool": name}})
            entry["error"] = (
                "A system error occurred. Nothing new was saved. Apologize and offer to try again, "
                "or ask the caller to call back later."
            )
        log_event(log, "tool.call", call_id=call_id, tool=name, ok="result" in entry)
        results.append(entry)
    return results


def _handle_status(db: Session, message: dict[str, Any], call_id: str) -> None:
    status = message.get("status")
    session = lock_session(db, call_id, _caller_number(message))
    if status == "in-progress" and not session.started_at:
        session.started_at = _ts((message.get("call") or {}).get("startedAt")) or _ts(message.get("timestamp"))
    db.commit()
    log_event(log, "call.status", call_id=call_id, status=status)


def _handle_end_of_call(db: Session, message: dict[str, Any], call_id: str) -> None:
    session = lock_session(db, call_id, _caller_number(message))
    artifact = message.get("artifact") or {}
    analysis = message.get("analysis") or {}
    session.started_at = _ts(message.get("startedAt")) or session.started_at
    session.ended_at = _ts(message.get("endedAt"))
    if session.started_at and session.ended_at:
        session.duration_seconds = max(0, int((session.ended_at - session.started_at).total_seconds()))
    session.ended_reason = (message.get("endedReason") or "")[:100] or None
    session.transcript = artifact.get("transcript") or message.get("transcript")
    session.summary = analysis.get("summary") or message.get("summary")

    # A dropped/abandoned call never writes a partial patient record; the
    # partial draft stays on the call session for follow-up.
    if session.state != "completed":
        session.state = "abandoned"
        if session.outcome != "failed":
            session.outcome = "abandoned" if session.draft else "no_registration"
    db.commit()
    # Observability requirement: final collected payload for every call (PII masked unless LOG_PII=true).
    log_event(log, "call.ended", call_id=call_id, ended_reason=session.ended_reason,
              duration_seconds=session.duration_seconds, outcome=session.outcome,
              patient_id=str(session.patient_id) if session.patient_id else None,
              caller=mask_value("caller_number", session.caller_number),
              final_payload=redact(dict(session.draft)))
