"""REST endpoints for patients: /patients."""

import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app import validation as v
from app.auth import require_admin
from app.db import get_db
from app.envelope import APIError, ok
from app.logging_utils import log_event, redact
from app.schemas import CallOut, PatientCreate, PatientOut, PatientUpdate
from app.services import patients as svc

router = APIRouter(prefix="/patients", tags=["patients"], dependencies=[Depends(require_admin)])
log = logging.getLogger("api.patients")


def parse_patient_id(patient_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(patient_id)
    except ValueError:
        raise APIError(400, "INVALID_ID", "patient_id must be a valid UUID.")


def _load(db: Session, patient_id: str):
    patient = svc.get_patient(db, parse_patient_id(patient_id))
    if patient is None:
        raise APIError(404, "NOT_FOUND", "Patient not found.")
    return patient


def _bad_query(name: str, exc: ValueError):
    raise APIError(400, "INVALID_QUERY", f"Query parameter '{name}' {exc}.")


@router.get("", summary="List patients (filterable, paginated)")
def list_patients(
    last_name: str | None = Query(None, max_length=50, description="Case-insensitive exact match"),
    date_of_birth: str | None = Query(None, description="MM/DD/YYYY or YYYY-MM-DD"),
    phone_number: str | None = Query(None, description="Any format; normalized to 10 digits"),
    q: str | None = Query(None, max_length=100, description="Free-text search over name, email, phone"),
    sort: Literal["created_at", "updated_at", "last_name", "first_name", "date_of_birth"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    dob = phone = None
    if date_of_birth:
        try:
            dob = v.date_of_birth(date_of_birth)
        except ValueError as exc:
            _bad_query("date_of_birth", exc)
    if phone_number:
        try:
            phone = v.phone_number(phone_number)
        except ValueError as exc:
            _bad_query("phone_number", exc)

    rows, total = svc.list_patients(
        db, last_name=last_name, date_of_birth=dob, phone_number=phone, q=q,
        sort=sort, order=order, limit=limit, offset=offset,
    )
    return ok(
        [PatientOut.model_validate(p) for p in rows],
        meta={"total": total, "limit": limit, "offset": offset},
    )


@router.get("/{patient_id}", summary="Get a patient by UUID")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    return ok(PatientOut.model_validate(_load(db, patient_id)))


@router.post("", status_code=201, summary="Create a patient")
def create_patient(
    payload: PatientCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=100),
    db: Session = Depends(get_db),
):
    patient, created = svc.create_patient(db, payload, idempotency_key=idempotency_key)
    log_event(log, "patient.created" if created else "patient.create_replayed",
              patient_id=str(patient.patient_id), payload=redact(payload.model_dump()))
    return ok(PatientOut.model_validate(patient), status_code=201 if created else 200)


@router.put("/{patient_id}", summary="Partially update a patient")
def update_patient(patient_id: str, payload: PatientUpdate, db: Session = Depends(get_db)):
    patient = svc.update_patient(db, _load(db, patient_id), payload)
    log_event(log, "patient.updated", patient_id=str(patient.patient_id),
              fields=sorted(payload.model_fields_set))
    return ok(PatientOut.model_validate(patient))


@router.delete("/{patient_id}", summary="Soft-delete a patient (sets deleted_at)")
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = svc.soft_delete_patient(db, _load(db, patient_id))
    log_event(log, "patient.soft_deleted", patient_id=str(patient.patient_id))
    return ok(PatientOut.model_validate(patient))


@router.get("/{patient_id}/calls", summary="Calls linked to a patient")
def patient_calls(patient_id: str, db: Session = Depends(get_db)):
    patient = _load(db, patient_id)
    calls = sorted(patient.calls, key=lambda c: c.created_at, reverse=True)
    return ok([CallOut.model_validate(c).model_copy(update={"has_transcript": bool(c.transcript)})
               for c in calls])
