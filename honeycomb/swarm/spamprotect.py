import time

import discord

from honeycomb.swarm.message_auth import send_alert


SPAM_MESSAGE_LIMIT = 5
SPAM_TIME_WINDOW = 3
SPAM_WARNING_COOLDOWN = 10


spam_tracker = {}
spam_warnings = {}


def check_spam(message):
    user_id = message.author.id
    now = time.monotonic()

    if user_id not in spam_tracker:
        spam_tracker[user_id] = []

    timestamps = spam_tracker[user_id]

    timestamps[:] = [
        timestamp
        for timestamp in timestamps
        if now - timestamp < SPAM_TIME_WINDOW
    ]

    timestamps.append(now)

    return len(timestamps) > SPAM_MESSAGE_LIMIT


async def handle_spam(message):
    user_id = message.author.id
    now = time.monotonic()

    try:
        await message.delete()

    except discord.NotFound:
        pass

    except discord.Forbidden:
        pass

    last_warning = spam_warnings.get(
        user_id,
        0
    )

    if now - last_warning >= SPAM_WARNING_COOLDOWN:
        spam_warnings[user_id] = now

        try:
            await message.channel.send(
                f"{message.author.mention}, slow down! 🛑"
            )

        except discord.Forbidden:
            pass

    # Send the detection to TOI2 alerts
    try:
        await send_alert(
            message.guild,
            "Spam protection detected a user.",
            title="Spam Detection",
            description=(
                f"Person: {message.author.mention}\n"
                f"Username: {message.author}\n"
                f"Channel: {message.channel.mention}\n"
                f"Message limit: "
                f"{SPAM_MESSAGE_LIMIT} messages/"
                f"{SPAM_TIME_WINDOW} seconds"
            ),
            color=discord.Color.orange()
        )

    except discord.HTTPException:
        pass