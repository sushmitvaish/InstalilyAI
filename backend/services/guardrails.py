import re

APPLIANCE_KEYWORDS = [
    "refrigerator", "fridge", "freezer", "ice maker", "dishwasher",
    "part", "install", "replace", "compatible", "model", "whirlpool",
    "ge", "samsung", "lg", "frigidaire", "kitchenaid", "maytag", "amana",
    "kenmore", "bosch", "electrolux",
    "door bin", "filter", "pump", "motor", "thermostat", "seal", "gasket",
    "rack", "spray arm", "dispenser", "compressor", "defrost", "drain",
    "shelf", "drawer", "hinge", "handle", "valve", "sensor", "fan",
    "not working", "broken", "leak", "noise", "won't", "doesn't",
    "fix", "repair", "troubleshoot", "problem",
    "partselect", "part select",
]


def quick_topic_check(message: str) -> str:
    lower = message.lower()
    matches = sum(1 for kw in APPLIANCE_KEYWORDS if kw in lower)
    if matches >= 2:
        return "LIKELY_ON_TOPIC"
    if re.search(r'PS\d{6,}', message, re.IGNORECASE):
        return "LIKELY_ON_TOPIC"
    if re.search(r'[A-Z]{2,}\d{3,}[A-Z]*\d*', message):
        return "LIKELY_ON_TOPIC"
    if matches == 0:
        return "LIKELY_OFF_TOPIC"
    return "UNCERTAIN"


def build_off_topic_response() -> dict:
    return {
        "role": "assistant",
        "content": (
            "I'm the PartSelect assistant specializing in **refrigerator** and "
            "**dishwasher** parts. I can help you with:\n\n"
            "- Finding the right replacement part\n"
            "- Checking part compatibility with your model\n"
            "- Installation instructions\n"
            "- Troubleshooting common problems\n\n"
            "How can I help you with your refrigerator or dishwasher today?"
        ),
        "parts": [],
        "suggested_queries": [
            "Help me find a part for my refrigerator",
            "My dishwasher is not draining",
            "Is part PS11752778 compatible with my model?"
        ]
    }
