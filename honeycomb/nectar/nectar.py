from pathlib import Path
import json


def get_data(file):
    path = Path(__file__).parent / file

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)