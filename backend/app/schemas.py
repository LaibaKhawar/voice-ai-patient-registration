"""Pydantic request/response schemas for the REST API.

Validation delegates to app/validation.py so the API and the voice agent share
one set of rules.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator, model_validator

from app import validation as v
from app.validation import Sex


class _PatientFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator(*v.ALL_FIELDS, mode="before", check_fields=False)
    @classmethod
    def _shared_rules(cls, value: Any, info: ValidationInfo):
        # Same rules the voice agent uses; None passes through (optional / partial update).
        if value is None:
            return None
        return v.validate_field(info.field_name, value)


class PatientCreate(_PatientFields):
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    phone_number: str
    email: str | None = None
    address_line_1: str
    address_line_2: str | None = None
    city: str
    state: str
    zip_code: str
    insurance_provider: str | None = None
    insurance_member_id: str | None = None
    preferred_language: str | None = "English"
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class PatientUpdate(_PatientFields):
    """Partial update: only fields present in the request body are changed.

    Optional fields may be set to null to clear them; required fields may not.
    """

    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    sex: Sex | None = None
    phone_number: str | None = None
    email: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    insurance_provider: str | None = None
    insurance_member_id: str | None = None
    preferred_language: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    @model_validator(mode="after")
    def _required_fields_not_null(self):
        for name in self.model_fields_set:
            if name in v.REQUIRED_FIELDS and getattr(self, name) is None:
                raise ValueError(f"{name} is required and cannot be null")
        if not self.model_fields_set:
            raise ValueError("request body must include at least one field to update")
        return self


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    phone_number: str
    email: str | None
    address_line_1: str
    address_line_2: str | None
    city: str
    state: str
    zip_code: str
    insurance_provider: str | None
    insurance_member_id: str | None
    preferred_language: str
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vapi_call_id: str
    caller_number: str | None
    state: str
    mode: str
    outcome: str | None
    patient_id: uuid.UUID | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    ended_reason: str | None
    summary: str | None
    has_transcript: bool = False
    created_at: datetime


class CallDetailOut(CallOut):
    transcript: str | None
    last_error: str | None


class LoginRequest(BaseModel):
    api_key: str
