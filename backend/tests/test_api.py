"""REST API tests: CRUD, validation, filtering, soft delete, auth, envelopes."""

import pytest


def _create(client, payload, **headers):
    return client.post("/patients", json=payload, headers=headers)


def test_create_returns_201_with_id_and_normalized_fields(client, valid_patient):
    res = _create(client, {**valid_patient, "email": "Jane.Doe@Example.com", "state": "texas"})
    assert res.status_code == 201
    body = res.json()
    assert body["error"] is None
    p = body["data"]
    assert len(p["patient_id"]) == 36
    assert p["phone_number"] == "5125550142"
    assert p["date_of_birth"] == "1988-04-12"
    assert p["state"] == "TX"
    assert p["email"] == "jane.doe@example.com"
    assert p["preferred_language"] == "English"
    assert p["created_at"] and p["updated_at"] and p["deleted_at"] is None


def test_get_by_id(client, valid_patient):
    pid = _create(client, valid_patient).json()["data"]["patient_id"]
    res = client.get(f"/patients/{pid}")
    assert res.status_code == 200
    assert res.json()["data"]["last_name"] == "Doe"


def test_optional_fields_round_trip(client, valid_patient):
    extra = {
        "address_line_2": "Apt 4B", "insurance_provider": "Aetna", "insurance_member_id": "w12-345 678",
        "preferred_language": "spanish", "emergency_contact_name": "John Doe",
        "emergency_contact_phone": "512-555-0199",
    }
    p = _create(client, {**valid_patient, **extra}).json()["data"]
    assert p["insurance_member_id"] == "W12345678"
    assert p["preferred_language"] == "Spanish"
    assert p["emergency_contact_phone"] == "5125550199"


@pytest.mark.parametrize("field", ["first_name", "last_name", "date_of_birth", "sex", "phone_number",
                                   "address_line_1", "city", "state", "zip_code"])
def test_missing_required_field_is_422(client, valid_patient, field):
    payload = {k: v for k, v in valid_patient.items() if k != field}
    res = _create(client, payload)
    assert res.status_code == 422
    body = res.json()
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == field for d in body["error"]["details"])


@pytest.mark.parametrize("field,value", [
    ("date_of_birth", "02/30/1990"),        # not a real date
    ("date_of_birth", "01/01/2999"),        # future
    ("phone_number", "555-1234"),           # 7 digits
    ("phone_number", "123"),                # 3 digits
    ("phone_number", "1234567890"),         # area code starts with 1
    ("state", "XX"),
    ("zip_code", "1234"),
    ("zip_code", "12345-12"),
    ("sex", "unknown"),
    ("first_name", "J4ne"),
    ("first_name", "A" * 51),
    ("email", "not-an-email"),
    ("insurance_member_id", "ABC#123"),
    ("emergency_contact_phone", "999"),
])
def test_invalid_values_are_422(client, valid_patient, field, value):
    res = _create(client, {**valid_patient, field: value})
    assert res.status_code == 422, res.json()
    assert any(d["field"] == field for d in res.json()["error"]["details"])


def test_unknown_field_rejected(client, valid_patient):
    res = _create(client, {**valid_patient, "ssn": "123-45-6789"})
    assert res.status_code == 422


def test_malformed_json_is_400(client):
    res = client.post("/patients", content="{not json", headers={"Content-Type": "application/json"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_JSON"


def test_names_allow_hyphen_apostrophe_and_spaces(client, valid_patient):
    res = _create(client, {**valid_patient, "first_name": "Mary-Kate", "last_name": "O'Brien De La Cruz"})
    assert res.status_code == 201


def test_zip_plus_four(client, valid_patient):
    assert _create(client, {**valid_patient, "zip_code": "787011234"}).json()["data"]["zip_code"] == "78701-1234"


def test_list_and_filters(client, valid_patient):
    _create(client, valid_patient)
    _create(client, {**valid_patient, "first_name": "Sam", "last_name": "Smith", "phone_number": "2125550100",
                     "date_of_birth": "1975-01-02"})
    all_ = client.get("/patients").json()
    assert all_["meta"]["total"] == 2 and len(all_["data"]) == 2

    by_last = client.get("/patients", params={"last_name": "doe"}).json()["data"]
    assert [p["first_name"] for p in by_last] == ["Jane"]

    by_dob = client.get("/patients", params={"date_of_birth": "01/02/1975"}).json()["data"]
    assert [p["last_name"] for p in by_dob] == ["Smith"]

    by_phone = client.get("/patients", params={"phone_number": "(212) 555-0100"}).json()["data"]
    assert [p["last_name"] for p in by_phone] == ["Smith"]

    combined = client.get("/patients", params={"last_name": "Doe", "phone_number": "2125550100"}).json()
    assert combined["data"] == [] and combined["meta"]["total"] == 0


def test_search_sort_and_pagination(client, valid_patient):
    for i, last in enumerate(["Adams", "Baker", "Carter"]):
        _create(client, {**valid_patient, "last_name": last, "phone_number": f"51255501{i}0"})
    res = client.get("/patients", params={"sort": "last_name", "order": "asc", "limit": 2, "offset": 1}).json()
    assert [p["last_name"] for p in res["data"]] == ["Baker", "Carter"]
    assert res["meta"] == {"total": 3, "limit": 2, "offset": 1}
    assert [p["last_name"] for p in client.get("/patients", params={"q": "bak"}).json()["data"]] == ["Baker"]


def test_bad_filter_values_are_400(client):
    assert client.get("/patients", params={"date_of_birth": "13/45/2000"}).status_code == 400
    assert client.get("/patients", params={"phone_number": "12"}).status_code == 400
    assert client.get("/patients", params={"limit": 0}).status_code == 400


def test_partial_update(client, valid_patient):
    created = _create(client, valid_patient).json()["data"]
    res = client.put(f"/patients/{created['patient_id']}", json={"city": "Round Rock", "zip_code": "78664"})
    assert res.status_code == 200
    p = res.json()["data"]
    assert p["city"] == "Round Rock" and p["zip_code"] == "78664"
    assert p["first_name"] == "Jane"  # untouched
    assert p["updated_at"] > created["updated_at"]


def test_update_rejects_null_required_and_invalid_values(client, valid_patient):
    pid = _create(client, valid_patient).json()["data"]["patient_id"]
    assert client.put(f"/patients/{pid}", json={"last_name": None}).status_code == 422
    assert client.put(f"/patients/{pid}", json={"state": "ZZ"}).status_code == 422
    assert client.put(f"/patients/{pid}", json={}).status_code == 422


def test_update_can_clear_optional_field(client, valid_patient):
    pid = _create(client, {**valid_patient, "email": "a@example.com"}).json()["data"]["patient_id"]
    assert client.put(f"/patients/{pid}", json={"email": None}).json()["data"]["email"] is None


def test_soft_delete(client, valid_patient):
    pid = _create(client, valid_patient).json()["data"]["patient_id"]
    res = client.delete(f"/patients/{pid}")
    assert res.status_code == 200 and res.json()["data"]["deleted_at"] is not None
    assert client.get(f"/patients/{pid}").status_code == 404
    assert client.get("/patients").json()["meta"]["total"] == 0
    assert client.delete(f"/patients/{pid}").status_code == 404
    # Row still exists in the database (not hard-deleted).
    from sqlalchemy import text
    from app.db import engine
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM patients WHERE deleted_at IS NOT NULL")).scalar() == 1


def test_not_found_and_invalid_id(client):
    res = client.get("/patients/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
    assert res.json() == {"data": None, "error": {"code": "NOT_FOUND", "message": "Patient not found."}}
    assert client.get("/patients/not-a-uuid").status_code == 400
    assert client.put("/patients/00000000-0000-0000-0000-000000000000", json={"city": "X"}).status_code == 404


def test_idempotency_key_prevents_duplicates(client, valid_patient):
    first = _create(client, valid_patient, **{"Idempotency-Key": "abc-123"})
    second = _create(client, valid_patient, **{"Idempotency-Key": "abc-123"})
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["data"]["patient_id"] == second.json()["data"]["patient_id"]
    assert client.get("/patients").json()["meta"]["total"] == 1


def test_auth_required(anon_client, valid_patient):
    for method, path in [("get", "/patients"), ("post", "/patients"), ("get", "/calls"), ("get", "/stats")]:
        res = getattr(anon_client, method)(path, **({"json": valid_patient} if method == "post" else {}))
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"
    assert anon_client.get("/patients", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert anon_client.get("/patients", headers={"X-API-Key": "test-api-key"}).status_code == 200


def test_dashboard_login_cookie_flow(anon_client):
    assert anon_client.post("/auth/login", json={"api_key": "nope"}).status_code == 401
    assert anon_client.post("/auth/login", json={"api_key": "test-api-key"}).status_code == 200
    assert anon_client.get("/patients").status_code == 200  # cookie now set
    anon_client.post("/auth/logout")
    assert anon_client.get("/patients").status_code == 401


def test_health_ready_and_stats(client, valid_patient):
    assert client.get("/health").json() == {"data": {"status": "ok"}, "error": None}
    assert client.get("/ready").json()["data"]["database"] == "ok"
    _create(client, valid_patient)
    stats = client.get("/stats").json()["data"]
    assert stats["total_patients"] == 1 and stats["registered_today"] == 1
    assert len(stats["registrations_by_day"]) == 14 and stats["registrations_by_day"][-1]["count"] == 1


def test_error_responses_do_not_echo_input(client, valid_patient):
    res = _create(client, {**valid_patient, "phone_number": "555-SECRET"})
    assert "SECRET" not in res.text
