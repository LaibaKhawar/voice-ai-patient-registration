"""Function-tool schemas exposed to the LLM through Vapi.

Each schema is strict about shape and format hints; the server re-validates
every value anyway (see app/voice/registration.py).
"""

from typing import Any

from app.validation import OPTIONAL_FIELDS

_FIELD_PROPS: dict[str, dict[str, Any]] = {
    "first_name": {"type": "string", "description": "Caller's legal first name, spelled exactly as confirmed."},
    "last_name": {"type": "string", "description": "Caller's legal last name, spelled exactly as confirmed."},
    "date_of_birth": {"type": "string", "description": "Date of birth as MM/DD/YYYY, e.g. 03/05/1990."},
    "sex": {"type": "string", "enum": ["Male", "Female", "Other", "Decline to Answer"]},
    "phone_number": {"type": "string", "description": "U.S. phone number, digits only, e.g. 5551234567."},
    "email": {"type": "string", "description": "Email address, e.g. maria.lopez@example.com."},
    "address_line_1": {"type": "string", "description": "Street address, e.g. 123 Main Street."},
    "address_line_2": {"type": "string", "description": "Apartment, suite or unit, e.g. Apt 4B."},
    "city": {"type": "string"},
    "state": {"type": "string", "description": "2-letter U.S. state abbreviation, e.g. TX."},
    "zip_code": {"type": "string", "description": "5-digit ZIP or ZIP+4, e.g. 78701 or 78701-1234."},
    "insurance_provider": {"type": "string", "description": "Insurance company name, e.g. Aetna."},
    "insurance_member_id": {"type": "string", "description": "Member/subscriber ID, letters and digits."},
    "preferred_language": {"type": "string", "description": "Language name, e.g. English or Spanish."},
    "emergency_contact_name": {"type": "string", "description": "Emergency contact's full name."},
    "emergency_contact_phone": {"type": "string", "description": "Emergency contact's U.S. phone, digits only."},
}


def _fn(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }


FUNCTIONS: list[dict[str, Any]] = [
    _fn(
        "update_patient_info",
        "Save or correct one or more patient details the caller just provided. Call this every time the "
        "caller gives or changes any information. Returns which values were saved, which were invalid "
        "(with reasons), which required fields are still missing, and any existing-record notice.",
        {
            **_FIELD_PROPS,
            "clear_fields": {
                "type": "array",
                "items": {"type": "string", "enum": list(OPTIONAL_FIELDS)},
                "description": "Optional fields the caller wants removed (e.g. they no longer want to give an email).",
            },
        },
    ),
    _fn(
        "verify_existing_patient",
        "Verify the caller owns an existing record that matched their phone number, using their date of birth. "
        "Only call when update_patient_info returned existing_record=needs_verification.",
        {"date_of_birth": _FIELD_PROPS["date_of_birth"]},
        ["date_of_birth"],
    ),
    _fn(
        "use_existing_record",
        "Record the caller's choice after being told we already have their record: update it (true) or "
        "continue registering as a new patient (false).",
        {"update_existing": {"type": "boolean"}},
        ["update_existing"],
    ),
    _fn(
        "review_registration",
        "Get the complete current registration formatted for reading back to the caller. Call once all "
        "required fields are saved and optional details have been offered. Must be called (and read back) "
        "before submit_registration.",
        {"optional_fields_offered": {"type": "boolean", "description": "true once you have asked whether the caller wants to add insurance, emergency contact, preferred language or email (whatever they answered)."}},
        ["optional_fields_offered"],
    ),
    _fn(
        "submit_registration",
        "Save the registration to the patient database. Only call after reading back review_registration "
        "and the caller explicitly confirmed it is correct.",
        {"caller_confirmed": {"type": "boolean", "description": "true only if the caller explicitly confirmed the read-back."}},
        ["caller_confirmed"],
    ),
    _fn(
        "start_over",
        "Discard everything collected on this call and restart the registration. Use only when the caller asks to start over.",
        {},
    ),
]

# Short phrases Vapi speaks while a slow tool runs, so the caller never hears dead air.
_TOOL_MESSAGES: dict[str, list[dict[str, Any]]] = {
    "submit_registration": [
        {"type": "request-start", "content": "One moment while I save that."},
        {"type": "request-response-delayed", "timingMilliseconds": 5000, "content": "Still working on it, thanks for your patience."},
        {"type": "request-failed", "content": "I'm sorry, I ran into a problem saving your information."},
    ],
    "review_registration": [
        {"type": "request-response-delayed", "timingMilliseconds": 3000, "content": "Just a second."},
    ],
}


def vapi_tools(server_url: str, secret: str) -> list[dict[str, Any]]:
    """Inline tool definitions for the Vapi assistant's model.tools."""
    server = {"url": server_url, "timeoutSeconds": 20, "headers": {"X-Vapi-Secret": secret}}
    tools: list[dict[str, Any]] = []
    for fn in FUNCTIONS:
        tool: dict[str, Any] = {"type": "function", "async": False, "function": fn, "server": server}
        if fn["name"] in _TOOL_MESSAGES:
            tool["messages"] = _TOOL_MESSAGES[fn["name"]]
        tools.append(tool)
    tools.append({"type": "endCall"})
    return tools
