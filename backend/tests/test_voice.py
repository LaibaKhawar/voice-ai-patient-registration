"""Voice-agent integration tests: drive /vapi/webhook exactly as Vapi does."""

import json
import uuid

import pytest
from sqlalchemy import text

from app.db import engine

SECRET = {"X-Vapi-Secret": "test-vapi-secret"}


class Call:
    """Simulates one phone call hitting the webhook."""

    def review(self):
        """review_registration as the agent does it: the first call bounces for the optional-field offer."""
        r = self.tool("review_registration")
        if r.get("ready") is False and "insurance" in r.get("instruction", ""):
            r = self.tool("review_registration")
        return r

    def __init__(self, client, caller="+15125550000"):
        self.client = client
        self.id = f"call-{uuid.uuid4()}"
        self.caller = caller
        self.n = 0

    def tool(self, name, args=None, *, raw_args=None):
        self.n += 1
        body = {"message": {
            "type": "tool-calls",
            "call": {"id": self.id, "customer": {"number": self.caller}},
            "toolCallList": [{"id": f"tc{self.n}", "type": "function",
                              "function": {"name": name, "arguments": raw_args if raw_args is not None else (args or {})}}],
        }}
        res = self.client.post("/vapi/webhook", json=body, headers=SECRET)
        assert res.status_code == 200
        result = res.json()["results"][0]
        assert result["toolCallId"] == f"tc{self.n}" and result["name"] == name
        if "error" in result:
            return {"_error": result["error"]}
        assert "\n" not in result["result"]
        return json.loads(result["result"])

    def end(self, reason="customer-ended-call"):
        body = {"message": {
            "type": "end-of-call-report", "call": {"id": self.id, "customer": {"number": self.caller}},
            "startedAt": "2026-10-10T15:00:00Z", "endedAt": "2026-10-10T15:03:30Z",
            "endedReason": reason, "artifact": {"transcript": "AI: Hi...\nUser: Hello"},
            "analysis": {"summary": "Caller registered."},
        }}
        assert self.client.post("/vapi/webhook", json=body, headers=SECRET).status_code == 200


FULL = {
    "first_name": "Maria", "last_name": "Lopez", "date_of_birth": "03/05/1990", "sex": "Female",
    "phone_number": "5125550142", "address_line_1": "200 Main Street", "city": "Austin",
    "state": "TX", "zip_code": "78701",
}


def patient_count():
    with engine.connect() as conn:
        return conn.execute(text("SELECT count(*) FROM patients")).scalar()


@pytest.fixture
def call(anon_client):
    return Call(anon_client)


def test_webhook_rejects_missing_or_wrong_secret(anon_client):
    body = {"message": {"type": "tool-calls", "call": {"id": "x"}, "toolCallList": []}}
    assert anon_client.post("/vapi/webhook", json=body).status_code == 401
    assert anon_client.post("/vapi/webhook", json=body, headers={"X-Vapi-Secret": "bad"}).status_code == 401
    # Dashboard credentials must not work on the webhook either.
    assert anon_client.post("/vapi/webhook", json=body, headers={"Authorization": "Bearer test-api-key"}).status_code == 401


def test_happy_path_registration(call, client):
    r = call.tool("update_patient_info", {"first_name": "Maria", "last_name": "Lopez"})
    assert set(r["saved"]) == {"first_name", "last_name"}
    assert "date of birth" in r["missing_required"]

    # Several fields at once, out of order, with spoken-style formats.
    r = call.tool("update_patient_info", {"zip_code": "78701", "state": "Texas", "city": "Austin",
                                          "date_of_birth": "03/05/1990", "sex": "female"})
    assert not r["invalid"]
    r = call.tool("update_patient_info", {"phone_number": "(512) 555-0142", "address_line_1": "200 Main Street"})
    assert r["missing_required"] == []

    review = call.review()
    assert review["ready"] is True
    assert "March 5, 1990" in review["read_back"]["date of birth"]
    assert review["read_back"]["phone number"] == "512-555-0142"
    assert patient_count() == 0  # nothing saved before confirmation

    done = call.tool("submit_registration", {"caller_confirmed": True})
    assert done["success"] is True and done["first_name"] == "Maria" and done["outcome"] == "registered"

    pts = client.get("/patients", params={"phone_number": "5125550142"}).json()["data"]
    assert len(pts) == 1 and pts[0]["state"] == "TX" and pts[0]["sex"] == "Female"

    call.end()
    calls = client.get("/calls").json()["data"]
    assert calls[0]["outcome"] == "registered" and calls[0]["duration_seconds"] == 210
    assert calls[0]["patient_id"] == pts[0]["patient_id"] and calls[0]["has_transcript"]
    assert client.get(f"/patients/{pts[0]['patient_id']}/calls").json()["data"][0]["vapi_call_id"] == call.id


@pytest.mark.parametrize("field,value,fragment", [
    ("date_of_birth", "01/01/2999", "future"),
    ("date_of_birth", "02/31/1990", "real calendar date"),
    ("phone_number", "555", "10-digit"),
    ("zip_code", "7870", "ZIP"),
    ("state", "Narnia", "state"),
])
def test_invalid_values_are_rejected_with_specific_reason(call, field, value, fragment):
    r = call.tool("update_patient_info", {field: value})
    assert field in r["invalid"] and fragment in r["invalid"][field]
    assert field not in r["saved"]
    assert "instruction" in r


def test_correction_replaces_value(call, client):
    call.tool("update_patient_info", {**FULL, "last_name": "Davies"})
    call.tool("update_patient_info", {"last_name": "Davis"})
    review = call.review()
    assert review["read_back"]["last name"].startswith("Davis (spelled D-A-V-I-S)")
    call.tool("submit_registration", {"caller_confirmed": True})
    assert client.get("/patients").json()["data"][0]["last_name"] == "Davis"


def test_cannot_submit_without_review_or_confirmation(call):
    call.tool("update_patient_info", FULL)
    assert "_error" in call.tool("submit_registration", {"caller_confirmed": True})  # never reviewed
    call.review()
    assert "_error" in call.tool("submit_registration", {"caller_confirmed": False})
    assert "_error" in call.tool("submit_registration", {})
    assert patient_count() == 0


def test_change_after_review_requires_new_review(call):
    call.tool("update_patient_info", FULL)
    call.review()
    call.tool("update_patient_info", {"city": "Round Rock"})
    assert "_error" in call.tool("submit_registration", {"caller_confirmed": True})
    call.review()
    assert call.tool("submit_registration", {"caller_confirmed": True})["success"] is True


def test_review_reports_missing_fields(call):
    call.tool("update_patient_info", {"first_name": "Maria"})
    r = call.review()
    assert r["ready"] is False and "last name" in r["missing_required"]


def test_repeated_submit_is_idempotent(call):
    call.tool("update_patient_info", FULL)
    call.review()
    a = call.tool("submit_registration", {"caller_confirmed": True})
    b = call.tool("submit_registration", {"caller_confirmed": True})
    assert a["success"] and b["success"] and b.get("already_saved")
    assert patient_count() == 1


def test_start_over_clears_draft(call):
    call.tool("update_patient_info", {"first_name": "Maria", "city": "Austin"})
    r = call.tool("start_over")
    assert r["reset"] is True
    r = call.review()
    assert "first name" in r["missing_required"] and "city" in r["missing_required"]


def test_optional_fields_and_clearing(call, client):
    call.tool("update_patient_info", {**FULL, "email": "maria@example.com", "insurance_provider": "Aetna"})
    r = call.tool("update_patient_info", {"clear_fields": ["email"]})
    assert r["cleared"] == ["email"]
    call.review()
    call.tool("submit_registration", {"caller_confirmed": True})
    p = client.get("/patients").json()["data"][0]
    assert p["email"] is None and p["insurance_provider"] == "Aetna"


def test_arguments_as_json_string(call):
    r = call.tool("update_patient_info", raw_args=json.dumps({"first_name": "Maria"}))
    assert "first_name" in r["saved"]


def test_unknown_tool_returns_error_not_http_failure(call):
    assert "_error" in call.tool("delete_everything")


def test_database_failure_is_reported_not_hidden(call, monkeypatch):
    from app.services import patients as svc

    def boom(*a, **k):
        raise RuntimeError("database is down")

    call.tool("update_patient_info", FULL)
    call.review()
    monkeypatch.setattr(svc, "create_patient", boom)
    r = call.tool("submit_registration", {"caller_confirmed": True})
    assert r["success"] is False and "NOT be saved" in r["instruction"]
    assert patient_count() == 0
    # Retry after recovery succeeds without re-reviewing.
    monkeypatch.undo()
    assert call.tool("submit_registration", {"caller_confirmed": True})["success"] is True
    assert patient_count() == 1


def test_dropped_call_marks_session_abandoned_and_saves_nothing(call, client):
    call.tool("update_patient_info", {"first_name": "Maria", "last_name": "Lopez"})
    call.end(reason="customer-ended-call")
    c = client.get("/calls").json()["data"][0]
    assert c["state"] == "abandoned" and c["outcome"] == "abandoned" and c["patient_id"] is None
    assert patient_count() == 0


def test_returning_caller_requires_dob_before_revealing_identity(anon_client, client):
    first = Call(anon_client)
    first.tool("update_patient_info", FULL)
    first.review()
    first.tool("submit_registration", {"caller_confirmed": True})

    second = Call(anon_client)
    r = second.tool("update_patient_info", {"phone_number": "512-555-0142"})
    assert r["existing_record"] == "needs_verification"
    assert "Maria" not in json.dumps(r) and "Lopez" not in json.dumps(r)

    bad = second.tool("verify_existing_patient", {"date_of_birth": "01/01/1991"})
    assert bad["verified"] is False and "Maria" not in json.dumps(bad)

    good = second.tool("verify_existing_patient", {"date_of_birth": "03/05/1990"})
    assert good["verified"] is True and good["existing_patient_name"] == "Maria Lopez"

    r = second.tool("use_existing_record", {"update_existing": True})
    assert r["mode"] == "update"
    second.tool("update_patient_info", {"address_line_1": "9 Oak Lane", "city": "Dallas", "zip_code": "75201"})
    review = second.review()
    assert review["mode"] == "update" and review["read_back"]["first name"].startswith("Maria")
    done = second.tool("submit_registration", {"caller_confirmed": True})
    assert done["success"] and done["outcome"] == "updated"

    pts = client.get("/patients").json()["data"]
    assert len(pts) == 1 and pts[0]["city"] == "Dallas" and pts[0]["last_name"] == "Lopez"


def test_returning_caller_with_dob_already_given_is_verified_immediately(anon_client):
    first = Call(anon_client)
    first.tool("update_patient_info", FULL)
    first.review()
    first.tool("submit_registration", {"caller_confirmed": True})

    second = Call(anon_client)
    second.tool("update_patient_info", {"date_of_birth": "03/05/1990"})
    r = second.tool("update_patient_info", {"phone_number": "5125550142"})
    assert r["existing_record"] == "verified" and r["existing_patient_name"] == "Maria Lopez"


def test_shared_phone_with_different_dob_registers_new_patient(anon_client):
    first = Call(anon_client)
    first.tool("update_patient_info", FULL)
    first.review()
    first.tool("submit_registration", {"caller_confirmed": True})

    second = Call(anon_client)
    r = second.tool("update_patient_info", {**FULL, "first_name": "Lucia", "date_of_birth": "07/07/2012"})
    assert "existing_record" not in r
    second.review()
    second.tool("submit_registration", {"caller_confirmed": True})
    assert patient_count() == 2


def test_declining_update_continues_as_new_registration(anon_client):
    first = Call(anon_client)
    first.tool("update_patient_info", FULL)
    first.review()
    first.tool("submit_registration", {"caller_confirmed": True})

    second = Call(anon_client)
    second.tool("update_patient_info", {"phone_number": "5125550142"})
    second.tool("verify_existing_patient", {"date_of_birth": "03/05/1990"})
    assert second.tool("use_existing_record", {"update_existing": False})["mode"] == "create"
    second.tool("update_patient_info", FULL)
    second.review()
    assert second.tool("submit_registration", {"caller_confirmed": True})["outcome"] == "registered"
    assert patient_count() == 2


def test_correction_after_save_updates_same_record(call, client):
    call.tool("update_patient_info", FULL)
    call.review()
    call.tool("submit_registration", {"caller_confirmed": True})
    call.tool("update_patient_info", {"zip_code": "78702"})
    call.review()
    r = call.tool("submit_registration", {"caller_confirmed": True})
    assert r["outcome"] == "updated" and patient_count() == 1
    assert client.get("/patients").json()["data"][0]["zip_code"] == "78702"


def test_other_message_types_are_acknowledged(anon_client):
    res = anon_client.post("/vapi/webhook", json={"message": {"type": "speech-update", "call": {"id": "c1"}}},
                           headers=SECRET)
    assert res.status_code == 200 and res.json() == {}


def test_review_requires_optional_fields_offer(call):
    call.tool("update_patient_info", FULL)
    r = call.tool("review_registration")
    assert r["ready"] is False and "insurance" in r["instruction"]
    assert "_error" in call.tool("submit_registration", {"caller_confirmed": True})
    assert call.tool("review_registration")["ready"] is True  # offer was prompted; now proceeds


def test_optional_offer_not_forced_when_caller_volunteered_optional_data(call):
    call.tool("update_patient_info", {**FULL, "insurance_provider": "Aetna"})
    assert call.tool("review_registration")["ready"] is True


def test_success_result_scripts_the_confirmation_line(call):
    call.tool("update_patient_info", FULL)
    call.review()
    r = call.tool("submit_registration", {"caller_confirmed": True})
    assert r["say_next"] == "You're all set, Maria."


def test_apartment_number_does_not_skip_optional_offer(call):
    call.tool("update_patient_info", {**FULL, "address_line_2": "Apt 4B"})
    r = call.tool("review_registration")
    assert r["ready"] is False and "insurance" in r["instruction"]


def test_saving_a_name_prompts_for_spelling(call):
    r = call.tool("update_patient_info", {"last_name": "Khawar"})
    assert "spell" in r["instruction"] and "last name" in r["instruction"]
    assert "instruction" not in call.tool("update_patient_info", {"city": "Austin"})
