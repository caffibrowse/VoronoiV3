import requests

from nectar import nectar
from swarm import toile_autoc_bee


WIKI_API = "https://en.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent": "toile/2.0"
}


def search_person(person):
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": person,
        "srlimit": 3
    }

    response = requests.get(
        WIKI_API,
        params=params,
        headers=HEADERS,
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def get_wikipedia_page(title):
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": True,
        "exintro": False,
        "titles": title
    }

    response = requests.get(
        WIKI_API,
        params=params,
        headers=HEADERS,
        timeout=5
    )

    response.raise_for_status()

    pages = response.json()["query"]["pages"]

    for page in pages.values():
        return page.get("extract", "")

    return ""


def check_criminal(person, crimes):
    results = search_person(person)

    for result in results["query"]["search"]:
        title = result["title"]

        text = get_wikipedia_page(title).lower()

        for crime in crimes:
            if crime.lower() in text:
                return {
                    "criminal": True,
                    "person": person,
                    "crime": crime
                }

    return {
        "criminal": False,
        "person": person,
        "crime": None
    }


def get__(message):
    # Keep the original message for name/entity detection.
    # Autocorrect can incorrectly change names.
    original_message = message.lower().strip()

    data = nectar.get_data("data/_mod.json")

    people = data.get("people", [])
    crimes = data.get("crimes", [])

    # Check people already stored in _mod.json.
    for person in people:
        if person.lower() in original_message:
            return check_criminal(person, crimes)

    # If the person isn't already known,
    # search the original message.
    results = search_person(original_message)

    for result in results["query"]["search"]:
        title = result["title"]

        text = get_wikipedia_page(title).lower()

        for crime in crimes:
            if crime.lower() in text:
                return {
                    "criminal": True,
                    "person": title,
                    "crime": crime
                }

    return {
        "criminal": False,
        "person": None,
        "crime": None
    }
