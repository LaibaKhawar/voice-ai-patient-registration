"""Builds the Vapi assistant definition (used by scripts/setup_vapi.py).

Kept in code, not configured by hand in the Vapi dashboard, so the deployed
agent is reproducible and reviewable.
"""

from typing import Any

from app.voice.prompt import AGENT_NAME, CLINIC_NAME, FIRST_MESSAGE, SYSTEM_PROMPT
from app.voice.tools import vapi_tools


def build_assistant(public_base_url: str, webhook_secret: str) -> dict[str, Any]:
    webhook_url = public_base_url.rstrip("/") + "/vapi/webhook"
    return {
        "name": f"{CLINIC_NAME} Registration ({AGENT_NAME})",
        "firstMessage": FIRST_MESSAGE,
        "firstMessageMode": "assistant-speaks-first",
        "model": {
            "provider": "openai",
            "model": "gpt-4.1",
            # Low temperature: consistent tool use and formats, still natural phrasing.
            "temperature": 0.3,
            "maxTokens": 300,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "tools": vapi_tools(webhook_url, webhook_secret),
        },
        "voice": {"provider": "vapi", "voiceId": "Savannah"},
        # nova-3 "multi" handles English and Spanish in one stream (bonus: Spanish support).
        "transcriber": {"provider": "deepgram", "model": "nova-3", "language": "multi"},
        "server": {"url": webhook_url, "timeoutSeconds": 20, "headers": {"X-Vapi-Secret": webhook_secret}},
        "serverMessages": ["tool-calls", "status-update", "end-of-call-report"],
        "maxDurationSeconds": 900,
        "backgroundSpeechDenoisingPlan": {"smartDenoisingPlan": {"enabled": True}},
        # Barge-in: the caller can interrupt after ~2 words of speech.
        "stopSpeakingPlan": {"numWords": 2, "voiceSeconds": 0.2, "backoffSeconds": 1},
        "startSpeakingPlan": {"waitSeconds": 0.4},
        "endCallMessage": f"Thanks for calling {CLINIC_NAME}. Goodbye!",
        # Silence handling: nudge once, then end the call politely.
        "hooks": [
            {
                "on": "customer.speech.timeout",
                "options": {"timeoutSeconds": 12, "triggerMaxCount": 2, "triggerResetMode": "onUserSpeech"},
                "do": [{"type": "say", "exact": "Are you still there? Take your time."}],
            },
            {
                "on": "customer.speech.timeout",
                "options": {"timeoutSeconds": 40, "triggerMaxCount": 1},
                "do": [
                    {"type": "say", "exact": "It sounds like we got disconnected. Nothing has been saved unless I confirmed it. Feel free to call back anytime. Goodbye!"},
                    {"type": "tool", "tool": {"type": "endCall"}},
                ],
            },
        ],
    }
