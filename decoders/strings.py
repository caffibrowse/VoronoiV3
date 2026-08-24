import asyncio
import html
import json
import os
import random
import re
import time
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import aiohttp


# ==========================================================
# CONFIG
# ==========================================================

CACHE_FILE = "data/brainrot.json"

USER_AGENT = (
    "Mozilla/5.0 "
    "(X11; Linux x86_64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)

SEARCH_LIMIT = 10

CACHE_TTL = 60 * 60 * 24 * 7

MIN_SEARCH_LENGTH = 3

# How confident a search engine needs to be before
# we stop searching other engines.
MIN_CONFIDENCE = 0.72

# Delay between web searches.
SEARCH_COOLDOWN = 1.5


# ==========================================================
# STATE
# ==========================================================

cache = {}

last_search_time = 0.0

search_lock = asyncio.Lock()


# ==========================================================
# NORMALIZATION
# ==========================================================

def normalize(text: str) -> str:
    text = html.unescape(text)

    text = text.replace("’", "'")
    text = text.replace("‘", "'")
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.lower().strip()


def clean_html(text: str) -> str:
    text = html.unescape(text)

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def tokenize(text: str):
    return {
        word
        for word in re.findall(
            r"[a-z0-9]+",
            normalize(text)
        )
        if len(word) >= 2
    }


# ==========================================================
# CACHE
# ==========================================================

def load_cache():

    if not os.path.exists(
        CACHE_FILE
    ):
        return {}

    try:

        with open(
            CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return data.get(
            "results",
            {}
        )

    except (
        OSError,
        json.JSONDecodeError
    ) as e:

        print(
            f"[STRINGS] "
            f"Cache load error: {e}"
        )

        return {}


def save_cache():

    directory = os.path.dirname(
        CACHE_FILE
    )

    if directory:
        os.makedirs(
            directory,
            exist_ok=True
        )

    with open(
        CACHE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "results": cache
            },
            f,
            indent=4,
            ensure_ascii=False
        )


cache = load_cache()


# ==========================================================
# SEARCH RATE LIMIT
# ==========================================================

async def wait_for_search():

    global last_search_time

    async with search_lock:

        now = time.monotonic()

        elapsed = (
            now - last_search_time
        )

        if elapsed < SEARCH_COOLDOWN:

            await asyncio.sleep(
                SEARCH_COOLDOWN - elapsed
            )

        last_search_time = (
            time.monotonic()
        )


# ==========================================================
# HTTP
# ==========================================================

async def fetch(
    session,
    url,
    *,
    params=None,
    method="GET",
    data=None
):

    try:

        if method == "POST":

            async with session.post(
                url,
                params=params,
                data=data,
                timeout=aiohttp.ClientTimeout(
                    total=15
                )
            ) as response:

                if response.status != 200:
                    return None

                return await response.text()

        async with session.get(
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(
                total=15
            )
        ) as response:

            if response.status != 200:
                return None

            return await response.text()

    except asyncio.TimeoutError:

        print(
            "[STRINGS] "
            "Search request timed out."
        )

        return None

    except Exception as e:

        print(
            f"[STRINGS] "
            f"Search request error: {e}"
        )

        return None


# ==========================================================
# URL CLEANING
# ==========================================================

def clean_result_url(url):

    if not url:
        return ""

    url = html.unescape(
        url
    )

    # DuckDuckGo redirect
    parsed = urlparse(
        url
    )

    if (
        parsed.hostname
        and "duckduckgo.com"
        in parsed.hostname
        and parsed.path == "/l/"
    ):

        query = parse_qs(
            parsed.query
        )

        if "uddg" in query:

            return unquote(
                query["uddg"][0]
            )

    # Google redirect
    if (
        parsed.hostname
        and "google.com"
        in parsed.hostname
        and parsed.path == "/url"
    ):

        query = parse_qs(
            parsed.query
        )

        if "q" in query:

            return query["q"][0]

    return url


# ==========================================================
# DUCKDUCKGO
# ==========================================================

async def search_duckduckgo(
    session,
    query
):

    await wait_for_search()

    url = (
        "https://html.duckduckgo.com/html/"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html",
        "Referer": (
            "https://html.duckduckgo.com/"
        ),
    }

    try:

        async with session.post(
            url,
            data={
                "q": query
            },
            headers=headers,
            timeout=aiohttp.ClientTimeout(
                total=15
            )
        ) as response:

            if response.status != 200:

                print(
                    "[STRINGS] "
                    f"DuckDuckGo HTTP "
                    f"{response.status}"
                )

                return []

            page = await response.text()

    except Exception as e:

        print(
            "[STRINGS] "
            f"DuckDuckGo error: {e}"
        )

        return []

    results = []

    # ------------------------------------------------------
    # DDG result blocks
    # ------------------------------------------------------

    blocks = re.findall(
        r'<div[^>]+class="result[^"]*"'
        r'.*?</div>\s*</div>',
        page,
        re.DOTALL
    )

    # Fallback if the markup differs.
    if not blocks:

        blocks = re.findall(
            r'<a[^>]+class="result__a".*?'
            r'</a>.*?'
            r'<a[^>]+class="result__snippet".*?'
            r'</a>',
            page,
            re.DOTALL
        )

    for block in blocks:

        title_match = re.search(
            r'class="result__a"'
            r'[^>]*href="([^"]+)"'
            r'[^>]*>(.*?)</a>',
            block,
            re.DOTALL
        )

        if not title_match:
            continue

        raw_url = title_match.group(
            1
        )

        title = clean_html(
            title_match.group(
                2
            )
        )

        snippet_match = re.search(
            r'class="result__snippet"'
            r'[^>]*>(.*?)</a?>',
            block,
            re.DOTALL
        )

        snippet = ""

        if snippet_match:

            snippet = clean_html(
                snippet_match.group(
                    1
                )
            )

        results.append(
            {
                "title": title,
                "snippet": snippet,
                "url": clean_result_url(
                    raw_url
                ),
                "source": "DuckDuckGo",
            }
        )

        if len(results) >= SEARCH_LIMIT:
            break

    print(
        "[STRINGS] "
        f"DuckDuckGo returned "
        f"{len(results)} results."
    )

    return results


# ==========================================================
# BING
# ==========================================================

async def search_bing(
    session,
    query
):

    await wait_for_search()

    url = (
        "https://www.bing.com/search"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html",
    }

    try:

        async with session.get(
            url,
            params={
                "q": query,
                "count": SEARCH_LIMIT,
                "setlang": "en-US",
            },
            headers=headers,
            timeout=aiohttp.ClientTimeout(
                total=15
            )
        ) as response:

            if response.status != 200:

                print(
                    "[STRINGS] "
                    f"Bing HTTP "
                    f"{response.status}"
                )

                return []

            page = await response.text()

    except Exception as e:

        print(
            f"[STRINGS] "
            f"Bing error: {e}"
        )

        return []

    results = []

    # ------------------------------------------------------
    # Bing result blocks
    # ------------------------------------------------------

    blocks = re.findall(
        r'<li[^>]+class="b_algo"'
        r'.*?</li>',
        page,
        re.DOTALL
    )

    for block in blocks:

        title_match = re.search(
            r'<h2[^>]*>'
            r'\s*<a[^>]+href="([^"]+)"'
            r'[^>]*>(.*?)</a>'
            r'\s*</h2>',
            block,
            re.DOTALL
        )

        if not title_match:
            continue

        raw_url = title_match.group(
            1
        )

        title = clean_html(
            title_match.group(
                2
            )
        )

        snippet_match = re.search(
            r'<p[^>]*>(.*?)</p>',
            block,
            re.DOTALL
        )

        snippet = ""

        if snippet_match:

            snippet = clean_html(
                snippet_match.group(
                    1
                )
            )

        results.append(
            {
                "title": title,
                "snippet": snippet,
                "url": clean_result_url(
                    raw_url
                ),
                "source": "Bing",
            }
        )

        if len(results) >= SEARCH_LIMIT:
            break

    print(
        "[STRINGS] "
        f"Bing returned "
        f"{len(results)} results."
    )

    return results


# ==========================================================
# YAHOO
# ==========================================================

async def search_yahoo(
    session,
    query
):

    await wait_for_search()

    url = (
        "https://search.yahoo.com/search"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html",
    }

    try:

        async with session.get(
            url,
            params={
                "p": query
            },
            headers=headers,
            timeout=aiohttp.ClientTimeout(
                total=15
            )
        ) as response:

            if response.status != 200:

                print(
                    "[STRINGS] "
                    f"Yahoo HTTP "
                    f"{response.status}"
                )

                return []

            page = await response.text()

    except Exception as e:

        print(
            f"[STRINGS] "
            f"Yahoo error: {e}"
        )

        return []

    results = []

    # ------------------------------------------------------
    # Yahoo result blocks
    # ------------------------------------------------------

    blocks = re.findall(
        r'<div[^>]+class="[^"]*algo[^"]*"'
        r'.*?</div>\s*</div>',
        page,
        re.DOTALL
    )

    for block in blocks:

        title_match = re.search(
            r'<h3[^>]*>'
            r'.*?<a[^>]+href="([^"]+)"'
            r'[^>]*>(.*?)</a>',
            block,
            re.DOTALL
        )

        if not title_match:
            continue

        raw_url = title_match.group(
            1
        )

        title = clean_html(
            title_match.group(
                2
            )
        )

        snippet_match = re.search(
            r'<div[^>]+class="[^"]*compText[^"]*"'
            r'.*?>(.*?)</div>',
            block,
            re.DOTALL
        )

        snippet = ""

        if snippet_match:

            snippet = clean_html(
                snippet_match.group(
                    1
                )
            )

        results.append(
            {
                "title": title,
                "snippet": snippet,
                "url": clean_result_url(
                    raw_url
                ),
                "source": "Yahoo",
            }
        )

        if len(results) >= SEARCH_LIMIT:
            break

    print(
        "[STRINGS] "
        f"Yahoo returned "
        f"{len(results)} results."
    )

    return results


# ==========================================================
# BRAVE PUBLIC SEARCH
# ==========================================================

async def search_brave(
    session,
    query
):

    await wait_for_search()

    url = (
        "https://search.brave.com/search"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html",
    }

    try:

        async with session.get(
            url,
            params={
                "q": query,
                "source": "web",
            },
            headers=headers,
            timeout=aiohttp.ClientTimeout(
                total=15
            )
        ) as response:

            if response.status != 200:

                print(
                    "[STRINGS] "
                    f"Brave HTTP "
                    f"{response.status}"
                )

                return []

            page = await response.text()

    except Exception as e:

        print(
            f"[STRINGS] "
            f"Brave error: {e}"
        )

        return []

    results = []

    # ------------------------------------------------------
    # Brave markup can change, so use several patterns.
    # ------------------------------------------------------

    patterns = [
        r'<a[^>]+href="([^"]+)"'
        r'[^>]+class="[^"]*result-header[^"]*"'
        r'[^>]*>(.*?)</a>',

        r'<a[^>]+class="[^"]*result-header[^"]*"'
        r'[^>]+href="([^"]+)"'
        r'[^>]*>(.*?)</a>',
    ]

    matches = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            page,
            re.DOTALL
        )

        if matches:
            break

    for raw_url, raw_title in matches:

        title = clean_html(
            raw_title
        )

        if not title:
            continue

        results.append(
            {
                "title": title,
                "snippet": "",
                "url": clean_result_url(
                    raw_url
                ),
                "source": "Brave",
            }
        )

        if len(results) >= SEARCH_LIMIT:
            break

    print(
        "[STRINGS] "
        f"Brave returned "
        f"{len(results)} results."
    )

    return results


# ==========================================================
# ALL SEARCHERS
# ==========================================================
#
# ORDER MATTERS.
#
# Voro3 searches the first one.
# If it does NOT confirm brainrot,
# Voro3 moves to the next.
#
# FIRST CONFIDENT HIT WINS.
# ==========================================================

SEARCHERS = [
    search_duckduckgo,
    search_bing,
    search_yahoo,
    search_brave,
]


# ==========================================================
# RESULT TEXT
# ==========================================================

def result_text(result):

    return normalize(
        " ".join(
            [
                result.get(
                    "title",
                    ""
                ),

                result.get(
                    "snippet",
                    ""
                ),
            ]
        )
    )


# ==========================================================
# EXACT QUERY MATCH
# ==========================================================

def query_match_score(
    query,
    result
):

    query = normalize(
        query
    )

    title = normalize(
        result.get(
            "title",
            ""
        )
    )

    snippet = normalize(
        result.get(
            "snippet",
            ""
        )
    )

    score = 0.0

    if query == title:

        score += 0.55

    elif query in title:

        score += 0.40

    elif query in snippet:

        score += 0.25

    query_words = tokenize(
        query
    )

    if query_words:

        title_words = tokenize(
            title
        )

        snippet_words = tokenize(
            snippet
        )

        title_overlap = (
            len(
                query_words
                & title_words
            )
            / len(query_words)
        )

        snippet_overlap = (
            len(
                query_words
                & snippet_words
            )
            / len(query_words)
        )

        score += (
            title_overlap
            * 0.30
        )

        score += (
            snippet_overlap
            * 0.10
        )

    return min(
        score,
        1.0
    )


# ==========================================================
# BRAINROT EVIDENCE
# ==========================================================

BRAINROT_TERMS = [
    "brainrot",
    "brain rot",
    "italian brainrot",
    "italian brain rot",
    "internet brainrot",
    "brainrot meme",
    "brain rot meme",
]


# These are strong indicators that a result is talking
# about the actual brainrot phenomenon.
STRONG_BRAINROT_TERMS = [
    "italian brainrot",
    "italian brain rot",
    "brainrot meme",
    "brain rot meme",
]


def analyze_results(
    query,
    results
):

    if not results:

        return {
            "detected": False,
            "confidence": 0.0,
            "match": None,
            "evidence": [],
        }

    ranked = []

    for result in results:

        score = query_match_score(
            query,
            result
        )

        ranked.append(
            (
                score,
                result
            )
        )

    ranked.sort(
        key=lambda item: item[0],
        reverse=True
    )

    best_score, best_result = (
        ranked[0]
    )

    # ------------------------------------------------------
    # Count independent evidence.
    # ------------------------------------------------------

    evidence = []

    strong_evidence = []

    query_mentions = 0

    for score, result in ranked:

        text = result_text(
            result
        )

        if not text:
            continue

        if normalize(query) in text:

            query_mentions += 1

        matched = []

        for term in BRAINROT_TERMS:

            if term in text:

                matched.append(
                    term
                )

        if matched:

            evidence.append(
                {
                    "source": result.get(
                        "source",
                        "unknown"
                    ),
                    "title": result.get(
                        "title",
                        ""
                    ),
                    "terms": matched,
                }
            )

        for term in STRONG_BRAINROT_TERMS:

            if term in text:

                strong_evidence.append(
                    result
                )

                break

    # ------------------------------------------------------
    # Confidence
    # ------------------------------------------------------

    confidence = (
        best_score * 0.35
    )

    # One result explicitly mentioning brainrot.
    if evidence:

        confidence += 0.20

    # Two independent results.
    if len(evidence) >= 2:

        confidence += 0.15

    # Three independent results.
    if len(evidence) >= 3:

        confidence += 0.10

    # Strong wording.
    if strong_evidence:

        confidence += 0.15

    # Multiple results mention the queried phrase.
    if query_mentions >= 2:

        confidence += 0.05

    if query_mentions >= 4:

        confidence += 0.05

    confidence = min(
        confidence,
        1.0
    )

    # ------------------------------------------------------
    # Detection
    # ------------------------------------------------------
    #
    # We require ACTUAL brainrot evidence.
    #
    # A random search result alone isn't enough.
    # ------------------------------------------------------

    detected = (
        len(evidence) >= 2
        and confidence >= MIN_CONFIDENCE
    )

    return {
        "detected": detected,
        "confidence": confidence,
        "match": best_result,
        "evidence": evidence,
    }


# ==========================================================
# CACHE
# ==========================================================

def get_cached(query):

    entry = cache.get(
        query
    )

    if not entry:
        return None

    timestamp = entry.get(
        "timestamp",
        0
    )

    if (
        time.time()
        - timestamp
        > CACHE_TTL
    ):

        return None

    return entry


def store_cache(
    query,
    detected,
    confidence,
    match,
    evidence
):

    cache[query] = {
        "brainrot": detected,
        "confidence": confidence,
        "match": match,
        "evidence": evidence,
        "timestamp": time.time(),
    }

    save_cache()


# ==========================================================
# MULTI-ENGINE DETECTOR
# ==========================================================

async def detect_brainrot(
    query
):

    query = normalize(
        query
    )

    if len(query) < MIN_SEARCH_LENGTH:

        return (
            False,
            0.0,
            None
        )

    # ------------------------------------------------------
    # CACHE
    # ------------------------------------------------------

    cached = get_cached(
        query
    )

    if cached:

        print(
            "[STRINGS] "
            f"Cache hit: {query!r} "
            f"-> "
            f"{cached.get('brainrot')}"
        )

        return (
            cached.get(
                "brainrot",
                False
            ),

            cached.get(
                "confidence",
                0.0
            ),

            cached.get(
                "match"
            )
        )

    # ------------------------------------------------------
    # ONE SESSION FOR ALL SEARCH ENGINES
    # ------------------------------------------------------

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with aiohttp.ClientSession(
        headers=headers
    ) as session:

        # --------------------------------------------------
        # SEARCH ENGINES
        # --------------------------------------------------

        for searcher in SEARCHERS:

            print(
                "[STRINGS] "
                f"Searching "
                f"{searcher.__name__}: "
                f"{query!r}"
            )

            results = await searcher(
                session,
                query
            )

            if not results:

                print(
                    "[STRINGS] "
                    f"{searcher.__name__}: "
                    "no results."
                )

                continue

            analysis = analyze_results(
                query,
                results
            )

            confidence = analysis[
                "confidence"
            ]

            detected = analysis[
                "detected"
            ]

            match = analysis[
                "match"
            ]

            evidence = analysis[
                "evidence"
            ]

            print(
                "[STRINGS] "
                f"{searcher.__name__}: "
                f"{confidence:.2%}"
            )

            if match:

                print(
                    "[STRINGS] "
                    f"Closest: "
                    f"{match.get('title')}"
                )

            if evidence:

                for item in evidence:

                    print(
                        "[STRINGS] "
                        f"Evidence: "
                        f"{item['source']} "
                        f"-> "
                        f"{item['title']}"
                    )

            # --------------------------------------------------
            # FIRST CONFIDENT BRAINROT RESULT WINS.
            # --------------------------------------------------

            if detected:

                print(
                    "[STRINGS] "
                    "================================"
                )

                print(
                    "[STRINGS] "
                    "BRAINROT CONFIRMED"
                )

                print(
                    "[STRINGS] "
                    f"Query: {query}"
                )

                print(
                    "[STRINGS] "
                    f"Confidence: "
                    f"{confidence:.2%}"
                )

                print(
                    "[STRINGS] "
                    "================================"
                )

                store_cache(
                    query,
                    True,
                    confidence,
                    match,
                    evidence
                )

                return (
                    True,
                    confidence,
                    match
                )

            # --------------------------------------------------
            # NOT CONFIRMED.
            #
            # Continue to the NEXT search engine.
            # --------------------------------------------------

            print(
                "[STRINGS] "
                f"{searcher.__name__}: "
                "not confirmed."
            )

    # ------------------------------------------------------
    # NOTHING FOUND.
    # ------------------------------------------------------

    print(
        "[STRINGS] "
        f"No search engine confirmed "
        f"brainrot for {query!r}."
    )

    store_cache(
        query,
        False,
        0.0,
        None,
        []
    )

    return (
        False,
        0.0,
        None
    )


# ==========================================================
# INITIALIZATION
# ==========================================================

async def initialize():

    global cache

    cache = load_cache()

    print(
        "[STRINGS] "
        f"Loaded {len(cache)} "
        "cached searches."
    )


# ==========================================================
# DISCORD HANDLER
# ==========================================================
response = [
    "fuck off.",
    "uhh,, shut up. ok?",
    "shh, we dont talk about brainrot here.",
    "dont talk about that.",
    "no.",
    "please stop.",
    "we're not doing this.",
    "absolutely not.",
    "you saw nothing.",
    "move along.",
    "what did you just say.",
    "i'm ignoring that.",
    "delete that from your vocabulary.",
    "nope.",
    "nah.",
    "we do NOT speak of this.",
    "i have decided that this does not exist.",
    "this conversation is over.",
    "for the love of god, stop.",
    "why.",
    "WHY.",
    "what is wrong with you.",
    "i regret reading that.",
    "i'm disappointed.",
    "that word is banned from my brain.",
    "never say that again.",
    "pretend you didn't type that.",
    "we're moving on.",
    "anyway.",
    "moving on...",
    "interesting. unfortunately, no.",
    "that's enough internet for today.",
    "go outside.",
    "touch grass.",
    "i'm not paid enough for this.",
    "my circuits hurt.",
    "my last braincell just resigned.",
    "i refuse to acknowledge this.",
    "error: absolutely not.",
    "Voro3 has left the conversation.",
]

import msgskills.fun

async def handle(message):

    content = normalize(
        message.content
    )

    if "brainrot" in content:
        await message.reply(random.choice(response))
        await message.delete()
    else:
        if len(content) < MIN_SEARCH_LENGTH:

            return False

        detected, confidence, match = (
            await detect_brainrot(
                content
            )
        )

        if not detected:

            return False

        print(
            "[STRINGS] "
            f"BRAINROT DETECTED: "
            f"{content!r} "
            f"({confidence:.2%})"
        )

        if match:

            print(
                "[STRINGS] "
                f"Source: "
                f"{match.get('source')}"
            )

            print(
                "[STRINGS] "
                f"Title: "
                f"{match.get('title')}"
            )

            print(
                "[STRINGS] "
                f"URL: "
                f"{match.get('url')}"
            )

        try:

            await message.reply(random.choice(response))

            await message.delete()

        except Exception as e:

            print(
                "[STRINGS] "
                f"Discord action failed: {e}"
            )

        await msgskills.fun.test(message)