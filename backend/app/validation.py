"""Field-level validation and normalization for patient demographics.

This module is the single source of truth for validation rules. It is used by
the REST API schemas *and* by the voice-agent tools, so a value the agent
accepts is exactly a value the API would accept. Every validator returns the
normalized value or raises ValueError with a message short and plain enough to
be read to a caller.
"""

import re
from datetime import date, datetime
from enum import StrEnum

from email_validator import EmailNotValidError, validate_email


class Sex(StrEnum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    DECLINE = "Decline to Answer"


US_STATES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia", "PR": "Puerto Rico", "GU": "Guam",
    "VI": "U.S. Virgin Islands", "AS": "American Samoa", "MP": "Northern Mariana Islands",
}
_STATE_BY_NAME = {name.lower(): code for code, name in US_STATES.items()}
_STATE_BY_NAME.update({"washington dc": "DC", "washington d.c.": "DC", "virgin islands": "VI"})

# Letters (any script, so "José" works), hyphens and apostrophes. Single
# internal spaces are also allowed for multi-part names like "De La Cruz";
# this is a deliberate, documented relaxation of the spec.
_NAME_RE = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*'?$")
_ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")
# NANP: area code and exchange cannot start with 0 or 1.
_PHONE_RE = re.compile(r"^[2-9]\d{2}[2-9]\d{6}$")
_MEMBER_ID_RE = re.compile(r"^[A-Z0-9]{1,30}$")
_LANGUAGE_RE = re.compile(r"^[^\W\d_]+(?:[ \-][^\W\d_]+)*$")

_SEX_SYNONYMS = {
    "male": Sex.MALE, "m": Sex.MALE, "man": Sex.MALE,
    "female": Sex.FEMALE, "f": Sex.FEMALE, "woman": Sex.FEMALE,
    "other": Sex.OTHER, "non-binary": Sex.OTHER, "nonbinary": Sex.OTHER,
    "decline to answer": Sex.DECLINE, "decline": Sex.DECLINE,
    "prefer not to say": Sex.DECLINE, "prefer not to answer": Sex.DECLINE,
}


def _clean(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("must be text")
    return re.sub(r"\s+", " ", value).strip()


def person_name(value: object, *, max_len: int = 50) -> str:
    text = _clean(value).replace("’", "'")
    if not text:
        raise ValueError("is required")
    if len(text) > max_len:
        raise ValueError(f"must be {max_len} characters or fewer")
    if not _NAME_RE.match(text):
        raise ValueError("may only contain letters, hyphens and apostrophes")
    return text


def date_of_birth(value: object, *, today: date | None = None) -> date:
    """Accepts a date, MM/DD/YYYY or YYYY-MM-DD. Must be a real, past date."""
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        text = _clean(value)
        parsed = None
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
            try:
                parsed = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValueError("must be a real calendar date in MM/DD/YYYY format")
    today = today or date.today()
    if parsed > today:
        raise ValueError("cannot be in the future")
    if parsed.year < 1900:
        raise ValueError("must be after the year 1900")
    return parsed


def sex(value: object) -> Sex:
    text = _clean(value).lower()
    if text in _SEX_SYNONYMS:
        return _SEX_SYNONYMS[text]
    raise ValueError("must be one of Male, Female, Other, or Decline to Answer")


def phone_number(value: object) -> str:
    """Normalizes to 10 digits, dropping punctuation and a leading country code 1."""
    if isinstance(value, int):
        value = str(value)
    digits = re.sub(r"\D", "", _clean(value))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError(f"must be a 10-digit U.S. phone number (got {len(digits)} digits)")
    if not _PHONE_RE.match(digits):
        raise ValueError("is not a valid U.S. phone number (area code and exchange cannot start with 0 or 1)")
    return digits


def email(value: object) -> str:
    text = _clean(value)
    try:
        result = validate_email(text, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError("is not a valid email address") from exc
    return result.normalized.lower()


def address_line(value: object, *, required: bool = True, max_len: int = 100) -> str:
    text = _clean(value)
    if not text:
        raise ValueError("is required")
    if len(text) > max_len:
        raise ValueError(f"must be {max_len} characters or fewer")
    if not re.search(r"[A-Za-z0-9]", text):
        raise ValueError("does not look like a street address")
    return text


def city(value: object) -> str:
    text = _clean(value)
    if not 1 <= len(text) <= 100:
        raise ValueError("must be between 1 and 100 characters")
    if not re.search(r"[^\W\d_]", text):
        raise ValueError("does not look like a city name")
    return text


def state(value: object) -> str:
    """Accepts a 2-letter code or a full state name; returns the USPS code."""
    text = _clean(value)
    code = text.upper().replace(".", "")
    if code in US_STATES:
        return code
    by_name = _STATE_BY_NAME.get(text.lower())
    if by_name:
        return by_name
    raise ValueError("must be a valid 2-letter U.S. state abbreviation")


def zip_code(value: object) -> str:
    if isinstance(value, int):
        value = str(value).zfill(5)
    text = _clean(value).replace(" ", "")
    if re.fullmatch(r"\d{9}", text):
        text = f"{text[:5]}-{text[5:]}"
    if not _ZIP_RE.match(text):
        raise ValueError("must be a 5-digit ZIP code or ZIP+4 (12345-6789)")
    return text


def free_text(value: object, *, max_len: int = 100) -> str:
    text = _clean(value)
    if not text:
        raise ValueError("cannot be empty")
    if len(text) > max_len:
        raise ValueError(f"must be {max_len} characters or fewer")
    return text


def member_id(value: object) -> str:
    text = re.sub(r"[\s\-]", "", _clean(value)).upper()
    if not _MEMBER_ID_RE.match(text):
        raise ValueError("must be letters and numbers only (up to 30 characters)")
    return text


def language(value: object) -> str:
    text = _clean(value)
    if not 1 <= len(text) <= 50 or not _LANGUAGE_RE.match(text):
        raise ValueError("must be a language name, like English or Spanish")
    return text.title()


REQUIRED_FIELDS: tuple[str, ...] = (
    "first_name", "last_name", "date_of_birth", "sex", "phone_number",
    "address_line_1", "city", "state", "zip_code",
)
OPTIONAL_FIELDS: tuple[str, ...] = (
    "email", "address_line_2", "insurance_provider", "insurance_member_id",
    "preferred_language", "emergency_contact_name", "emergency_contact_phone",
)
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

FIELD_VALIDATORS = {
    "first_name": person_name,
    "last_name": person_name,
    "date_of_birth": date_of_birth,
    "sex": sex,
    "phone_number": phone_number,
    "email": email,
    "address_line_1": address_line,
    "address_line_2": address_line,
    "city": city,
    "state": state,
    "zip_code": zip_code,
    "insurance_provider": free_text,
    "insurance_member_id": member_id,
    "preferred_language": language,
    "emergency_contact_name": lambda v: person_name(v, max_len=100),
    "emergency_contact_phone": phone_number,
}

FIELD_LABELS = {
    "first_name": "first name",
    "last_name": "last name",
    "date_of_birth": "date of birth",
    "sex": "sex",
    "phone_number": "phone number",
    "email": "email address",
    "address_line_1": "street address",
    "address_line_2": "apartment or unit",
    "city": "city",
    "state": "state",
    "zip_code": "ZIP code",
    "insurance_provider": "insurance provider",
    "insurance_member_id": "insurance member ID",
    "preferred_language": "preferred language",
    "emergency_contact_name": "emergency contact name",
    "emergency_contact_phone": "emergency contact phone number",
}


def validate_field(name: str, value: object):
    """Validate a single named field. Raises KeyError for unknown fields."""
    return FIELD_VALIDATORS[name](value)
