"""Insert two synthetic demo patients (idempotent; safe to run on every deploy).

All data is fictional. Phone numbers use the 555-01xx range reserved for fiction.
"""

from app.db import SessionLocal
from app.schemas import PatientCreate
from app.services.patients import create_patient

SEED_PATIENTS = [
    ("seed-demo-1", {
        "first_name": "Jane", "last_name": "Doe", "date_of_birth": "04/12/1988", "sex": "Female",
        "phone_number": "5125550101", "email": "jane.doe@example.com",
        "address_line_1": "100 Congress Ave", "address_line_2": "Suite 200", "city": "Austin",
        "state": "TX", "zip_code": "78701", "insurance_provider": "Aetna",
        "insurance_member_id": "W123456789", "emergency_contact_name": "John Doe",
        "emergency_contact_phone": "5125550102",
    }),
    ("seed-demo-2", {
        "first_name": "Carlos", "last_name": "Rivera", "date_of_birth": "11/23/1975", "sex": "Male",
        "phone_number": "3055550188", "address_line_1": "742 Ocean Drive", "city": "Miami",
        "state": "FL", "zip_code": "33139", "preferred_language": "Spanish",
    }),
]


def main() -> None:
    with SessionLocal() as db:
        for key, data in SEED_PATIENTS:
            patient, created = create_patient(db, PatientCreate(**data), idempotency_key=key)
            print(f"{'created' if created else 'exists '} {patient.first_name} {patient.last_name} {patient.patient_id}")


if __name__ == "__main__":
    main()
