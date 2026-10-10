"""Unit tests for the shared validation rules."""

from datetime import date

import pytest

from app import validation as v


@pytest.mark.parametrize("raw,expected", [
    ("(512) 555-0142", "5125550142"), ("+1 512 555 0142", "5125550142"), ("512.555.0142", "5125550142"),
])
def test_phone_normalization(raw, expected):
    assert v.phone_number(raw) == expected


@pytest.mark.parametrize("raw", ["555-0142", "0125550142", "5121550142", "25125550142", ""])
def test_phone_rejects(raw):
    with pytest.raises(ValueError):
        v.phone_number(raw)


def test_dob_formats_and_rules():
    today = date(2026, 10, 10)
    assert v.date_of_birth("03/05/1990", today=today) == date(1990, 3, 5)
    assert v.date_of_birth("1990-03-05", today=today) == date(1990, 3, 5)
    assert v.date_of_birth("10/10/2026", today=today) == today  # newborn registered today
    for bad in ["10/11/2026", "13/01/1990", "02/29/2023", "1899-12-31", "yesterday"]:
        with pytest.raises(ValueError):
            v.date_of_birth(bad, today=today)


@pytest.mark.parametrize("raw,expected", [("tx", "TX"), ("Texas", "TX"), ("new york", "NY"), ("D.C.", "DC")])
def test_state(raw, expected):
    assert v.state(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("male", v.Sex.MALE), ("F", v.Sex.FEMALE), ("prefer not to say", v.Sex.DECLINE), ("Other", v.Sex.OTHER),
])
def test_sex(raw, expected):
    assert v.sex(raw) == expected


@pytest.mark.parametrize("name", ["O'Neil", "Anne-Marie", "José", "De La Cruz"])
def test_names_ok(name):
    assert v.person_name(name) == name


@pytest.mark.parametrize("name", ["", "R2D2", "--", "Smith!", "a" * 51])
def test_names_rejected(name):
    with pytest.raises(ValueError):
        v.person_name(name)
