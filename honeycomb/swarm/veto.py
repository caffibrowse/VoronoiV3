import random
import re
import aiohttp

swears = [
    "fuck",
    "shit",
    "bitch",
    "cock",
    "pussy",
    "ass",
    "butt",
]

async def wikipedia_check(term):
    url = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": f'"{term}"',
        "srlimit": 1
    }

    headers = {
        "User-Agent": "Voro3/Veto2"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    return False

                data = await response.json()

                return bool(data.get("query", {}).get("search"))

    except Exception:
        return False


async def checkswear(message, type="AUTO"):
    content = message.content.lower()

    detected = None
    source = None

    for swear in swears:
        if re.search(rf"\b{re.escape(swear)}\b", content):
            detected = swear
            source = "swears"
            break

    if detected is None:
        words = re.findall(r"\b[a-zA-Z]+\b", content)

        for word in words:
            if await wikipedia_check(word):
                continue

    if detected is None:
        return False

    alert_channel = next(
        (
            channel
            for channel in message.guild.text_channels
            if channel.name == "veto-alerts"
        ),
        None
    )

    if alert_channel:
        await alert_channel.send(
            f"🚨 **Veto2 Alert**\n"
            f"**User:** {message.author} ({message.author.id})\n"
            f"**Channel:** {message.channel.mention}\n"
            f"**Message:** {message.content}\n"
            f"**Detected:** `{detected}`\n"
            f"**Source:** `{source}`"
        )

    if type == "AUTO":
        await message.reply("language!")
        await message.delete()
    elif type == "AudioFiltered":
        await message.reply("language!")
        await message.delete()
        return "true"
    elif type == "Jxx":
        return random.randint(1, 10000000)

    return True