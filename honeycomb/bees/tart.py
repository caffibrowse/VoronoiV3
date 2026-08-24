import re


# ==========================================================
# TART
# ==========================================================
#
# TART ONLY DETECTS.
#
# TART does NOT:
#     - delete messages
#     - reply
#     - send alerts
#     - create Discord clients
#     - run its own event loop
#
# Nexus handles moderation.
#
# ==========================================================


EXEMPT_CATEGORY_NAME = "13+"


# ==========================================================
# SEXUAL PATTERNS
# ==========================================================

SEXUAL_PATTERNS = [

    re.compile(
        r"\b(?:porn|pornography|xxx|hentai)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:nudes?|naked\s+pics?|naked\s+pictures?)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:send|trade|swap|show)\s+"
        r"(?:me\s+)?"
        r"(?:nudes?|naked\s+pics?|naked\s+pictures?)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:sex|sexual)\s+"
        r"(?:pics?|pictures?|images?|content)\b",
        re.IGNORECASE
    ),
]


# ==========================================================
# MINOR PATTERNS
# ==========================================================

MINOR_PATTERNS = [

    re.compile(
        r"\b(?:underage|minor|minors)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:under\s*(?:1[0-7]|18)|"
        r"(?:1[0-7]|18)\s*(?:yo|yrs?|years?\s*old))\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:kid|kids|child|children)\b"
        r".{0,40}"
        r"\b(?:sex|sexual|porn|nudes?|naked)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:sex|sexual|porn|nudes?|naked)\b"
        r".{0,40}"
        r"\b(?:kid|kids|child|children|minor|underage)\b",
        re.IGNORECASE
    ),
]


# ==========================================================
# REGEX CHECK
# ==========================================================

def regex_check(content):

    if not isinstance(
        content,
        str
    ):

        return False, None


    minor_match = None

    for pattern in MINOR_PATTERNS:

        match = pattern.search(
            content
        )

        if match:

            minor_match = match

            break


    sexual_match = None

    for pattern in SEXUAL_PATTERNS:

        match = pattern.search(
            content
        )

        if match:

            sexual_match = match

            break


    if (
        minor_match
        and sexual_match
    ):

        return (
            True,
            "sexual content involving an underage/minor context"
        )


    if sexual_match:

        return (
            True,
            "explicit sexual content"
        )


    return False, None


# ==========================================================
# CHECK
# ==========================================================
#
# Accepts a Discord Message.
#
# ==========================================================

def check(message):

    if message is None:

        return False, None


    content = getattr(
        message,
        "content",
        None
    )


    if not isinstance(
        content,
        str
    ):

        return False, None


    content = content.strip()


    if not content:

        return False, None


    return regex_check(
        content
    )


# ==========================================================
# 13+ CHECK
# ==========================================================

def is_13plus(message):

    if message is None:

        return False


    category = getattr(
        message.channel,
        "category",
        None
    )


    if category is None:

        return False


    return (
        category.name.casefold()
        == EXEMPT_CATEGORY_NAME.casefold()
    )