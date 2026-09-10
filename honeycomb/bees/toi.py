import re

import nectar.nectar
from swarm import toilecheck


async def toi2mod(message):

    if message is None:
        return False, None, None, None


    # ======================================================
    # IGNORE BOTS
    # ======================================================

    if getattr(
        getattr(message, "author", None),
        "bot",
        False
    ):

        return False, None, None, None


    # ======================================================
    # MESSAGE CONTENT
    # ======================================================

    content = (
        getattr(
            message,
            "content",
            ""
        ) or ""
    ).strip()


    if not content:

        return False, None, None, None


    # ======================================================
    # TOILECHECK
    # ======================================================

    flagged = False
    person = None
    crime = None
    enabled = nectar.nectar.get_data("data/toi.json")

    try:

        result = toilecheck.get__(
            content
        )

    except Exception as error:

        print(
            f"[TOI] Detection failed: {error}"
        )

        result = {}


    if isinstance(
        result,
        dict
    ):

        flagged = bool(
            result.get(
                "criminal",
                False
            )
        )

        person = result.get(
            "person"
        )

        crime = result.get(
            "crime"
        )

    else:

        print(
            "[TOI] toilecheck returned invalid data."
        )


    # ======================================================
    # REGEX FALLBACK
    # ======================================================

    if not flagged:

        patterns = [

            (
                r"\b(?:jeffrey\s+epstein|epstein)\b",
                "Jeffrey Epstein"
            ),

            (
                r"\b(?:adolf\s+hitler|hitler)\b",
                "Adolf Hitler"
            ),

            (
                r"\b(?:joseph\s+stalin|stalin)\b",
                "Joseph Stalin"
            ),

        ]


        for pattern, detected_person in patterns:

            if re.search(
                pattern,
                content,
                re.IGNORECASE
            ):

                flagged = True

                person = detected_person

                crime = (
                    "Known criminal/person mention"
                )

                print(
                    f"[TOI] REGEX HIT: "
                    f"{detected_person}"
                )

                break


    # ======================================================
    # REASON
    # ======================================================

    reason = None


    if flagged:

        reason = (
            f"Person: "
            f"{person or 'Unknown'}\n"
            f"Crime: "
            f"{crime or 'Unknown'}"
        )

        print(
            f"[TOI] FLAGGED: "
            f"{person or 'Unknown'}"
        )

    else:

        print(
            "[TOI] CLEAR"
        )


    # ======================================================
    # RETURN TO NEXUS
    # ======================================================

    return (
        flagged,
        reason,
        person,
        crime,
        enabled
    )