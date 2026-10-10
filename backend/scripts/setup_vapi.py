"""Create or update the Vapi assistant, and optionally provision a free U.S. number.

Usage (from backend/):
    VAPI_API_KEY=... PUBLIC_BASE_URL=https://your-app.example.com VAPI_WEBHOOK_SECRET=... \
        python -m scripts.setup_vapi [--provision-number] [--area-code 512] [--dry-run]

Idempotent: the assistant is matched by name and updated in place; a number is
only provisioned if none is already attached to the assistant.
"""

import argparse
import json
import os
import sys

import httpx

from app.voice.assistant import build_assistant

API = "https://api.vapi.ai"


def _client() -> httpx.Client:
    key = os.environ.get("VAPI_API_KEY")
    if not key:
        sys.exit("VAPI_API_KEY is not set")
    return httpx.Client(base_url=API, headers={"Authorization": f"Bearer {key}"}, timeout=30)


def _check(res: httpx.Response) -> dict | list:
    if res.status_code >= 400:
        sys.exit(f"Vapi API error {res.status_code} on {res.request.method} {res.request.url.path}: {res.text}")
    return res.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provision-number", action="store_true")
    parser.add_argument("--area-code", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print the assistant JSON and exit")
    args = parser.parse_args()

    base_url = os.environ.get("PUBLIC_BASE_URL")
    secret = os.environ.get("VAPI_WEBHOOK_SECRET")
    if not base_url or not secret:
        sys.exit("PUBLIC_BASE_URL and VAPI_WEBHOOK_SECRET must be set")
    if not base_url.startswith("https://"):
        sys.exit("PUBLIC_BASE_URL must be https:// (Vapi needs a public HTTPS endpoint)")

    assistant = build_assistant(base_url, secret)
    if args.dry_run:
        redacted = json.dumps(assistant, indent=2).replace(secret, "<VAPI_WEBHOOK_SECRET>")
        print(redacted)
        return

    with _client() as vapi:
        existing = [a for a in _check(vapi.get("/assistant", params={"limit": 100}))
                    if a.get("name") == assistant["name"]]
        if existing:
            assistant_id = existing[0]["id"]
            _check(vapi.patch(f"/assistant/{assistant_id}", json=assistant))
            print(f"Updated assistant {assistant_id}")
        else:
            assistant_id = _check(vapi.post("/assistant", json=assistant))["id"]
            print(f"Created assistant {assistant_id}")

        numbers = _check(vapi.get("/phone-number", params={"limit": 100}))
        attached = [n for n in numbers if n.get("assistantId") == assistant_id]
        for n in attached:
            print(f"Number attached: {n.get('number') or '(pending)'} status={n.get('status')} id={n['id']}")

        if args.provision_number and not attached:
            body = {"provider": "vapi", "name": "Patient registration line", "assistantId": assistant_id}
            if args.area_code:
                body["numberDesiredAreaCode"] = args.area_code
            number = _check(vapi.post("/phone-number", json=body))
            print(f"Provisioned number: {number.get('number') or '(pending)'} status={number.get('status')} id={number['id']}")
            print("Free Vapi numbers can take a few minutes to become active.")


if __name__ == "__main__":
    main()
