from pathlib import Path
import json

INTERACT_FILE = Path(__file__).parent.parent / "interact/inter.json"

with INTERACT_FILE.open("r", encoding="utf-8") as f:
    interactions = json.load(f)


async def check_interaction(message):
    content = message.content.lower().strip()

    for character in interactions.values():
        name = character["name"].lower()

        for trigger, response in character["interactions"].items():
            if trigger.lower() in content:
                return f"**{str(name).upper()}**: {response}"
    return None