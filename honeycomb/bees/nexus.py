# ==========================================================
# honeycomb/bees/nexus.py
# ==========================================================
#
# ONE Nexus.
#
# TART and TOI only provide detection results.
#
# Nexus owns:
#
#     - moderation decisions
#     - replies
#     - deletion
#     - alerts
#     - module enabled/disabled state
#
# Nexus does NOT create a Discord client.
# Nexus does NOT log into Discord.
# Nexus does NOT spawn processes.
#
# ==========================================================

import discord

from nectar import nectar


# ==========================================================
# ALERT CHANNELS
# ==========================================================

TOI_CHANNEL_NAME = "toi-alerts"
TART_CHANNEL_NAME = "tart-alerts"


# ==========================================================
# STATE
# ==========================================================

message = None

message_id = None
content = None

guild = None
guild_id = None
guild_name = None

channel = None
channel_id = None
channel_name = None

category = None
category_id = None
category_name = None

user = None
user_id = None
user_name = None

in13plus = False

tartflagged = False
tartreason = None

toiflagged = False
toireason = None
toiperson = None
toicrime = None

toi_enabled = False


# ==========================================================
# UPDATE MESSAGE
# ==========================================================

def update_message(msg):

    global message
    global message_id
    global content

    global guild
    global guild_id
    global guild_name

    global channel
    global channel_id
    global channel_name

    global category
    global category_id
    global category_name

    global user
    global user_id
    global user_name

    global in13plus

    if msg is None:
        return

    message = msg

    message_id = msg.id
    content = msg.content

    guild = msg.guild

    if guild is not None:

        guild_id = guild.id
        guild_name = guild.name

    else:

        guild_id = None
        guild_name = None

    channel = msg.channel

    channel_id = getattr(
        channel,
        "id",
        None
    )

    channel_name = getattr(
        channel,
        "name",
        None
    )

    category = getattr(
        channel,
        "category",
        None
    )

    if category is not None:

        category_id = category.id
        category_name = category.name

        in13plus = (
            category.name.casefold()
            == "13+"
        )

    else:

        category_id = None
        category_name = None
        in13plus = False

    user = msg.author

    if user is not None:

        user_id = user.id
        user_name = str(user)

    else:

        user_id = None
        user_name = None


# ==========================================================
# GET TOI ENABLED STATE
# ==========================================================
#
# Nexus owns the operational state of TOI.
#
# TOI2 can still detect messages while TOI is disabled.
# Nexus decides whether that result should actually
# trigger moderation.
#
# ==========================================================

def get_toi_enabled():

    try:

        data = nectar.get_data(
            "data/toi.json"
        )

    except Exception as error:

        print(
            f"[NEXUS] TOI config error: {error}"
        )

        return False

    if not isinstance(
        data,
        dict
    ):

        print(
            "[NEXUS] Invalid TOI configuration."
        )

        return False

    enabled = bool(
        data.get(
            "enabled",
            False
        )
    )

    return enabled


# ==========================================================
# TEST CHANNEL CHECK
# ==========================================================
#
# Channels beginning with "toi-testenv" are always
# allowed to run TOI moderation for testing.
#
# Examples:
#
#     #toi-testenv
#     #toi-testenv-2
#     #toi-testenv-testing
#
# ==========================================================

def is_toi_test_channel():

    if channel_name is None:
        return False

    return str(
        channel_name
    ).casefold().startswith(
        "toi-testenv"
    )


# ==========================================================
# RESET DETECTIONS
# ==========================================================

def reset_detections():

    global tartflagged
    global tartreason

    global toiflagged
    global toireason
    global toiperson
    global toicrime

    tartflagged = False
    tartreason = None

    toiflagged = False
    toireason = None
    toiperson = None
    toicrime = None


# ==========================================================
# RESET
# ==========================================================

def reset():

    global message
    global message_id
    global content

    global guild
    global guild_id
    global guild_name

    global channel
    global channel_id
    global channel_name

    global category
    global category_id
    global category_name

    global user
    global user_id
    global user_name

    global in13plus

    global toi_enabled

    message = None
    message_id = None
    content = None

    guild = None
    guild_id = None
    guild_name = None

    channel = None
    channel_id = None
    channel_name = None

    category = None
    category_id = None
    category_name = None

    user = None
    user_id = None
    user_name = None

    in13plus = False

    toi_enabled = False

    reset_detections()


# ==========================================================
# TART FEED
# ==========================================================

def update_tart(
    msg,
    flagged=False,
    reason=None
):

    global tartflagged
    global tartreason

    update_message(msg)

    tartflagged = bool(
        flagged
    )

    tartreason = reason

    print(
        f"[NEXUS] TART: "
        f"{tartflagged} | "
        f"{tartreason}"
    )


# ==========================================================
# TOI FEED
# ==========================================================

def update_toi(
    msg,
    flagged=False,
    reason=None,
    person=None,
    crime=None,
    enabled=False
):

    global toiflagged
    global toireason
    global toiperson
    global toicrime
    global toi_enabled

    update_message(msg)

    toiflagged = bool(flagged)

    toireason = reason
    toiperson = person
    toicrime = crime

    # TOI feeds its enabled state to Nexus.
    # Nexus decides what to do with it.

    toi_enabled = bool(enabled)

    print(
        f"[NEXUS] TOI: "
        f"{toiflagged} | "
        f"Person: {toiperson}"
    )

    print(
        f"Crime: {toicrime}"
    )

    print(
        f"Enabled: {toi_enabled}"
    )


# ==========================================================
# GET ALERT CHANNEL
# ==========================================================

def get_alert_channel(
    guild,
    channel_name
):

    if guild is None:
        return None

    return discord.utils.get(
        guild.text_channels,
        name=channel_name
    )


# ==========================================================
# ALERT
# ==========================================================

async def send_alert(
    guild,
    channel_name,
    title,
    description
):

    if guild is None:

        print(
            "[NEXUS] Cannot send alert: "
            "guild is None"
        )

        return False

    alert_channel = get_alert_channel(
        guild,
        channel_name
    )

    if alert_channel is None:

        print(
            f"[NEXUS] #{channel_name} "
            f"not found in {guild.name}"
        )

        return False

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )

    try:

        await alert_channel.send(
            embed=embed
        )

        print(
            f"[NEXUS] Alert → "
            f"#{channel_name}"
        )

        return True

    except discord.Forbidden:

        print(
            f"[NEXUS] Missing permission "
            f"for #{channel_name}"
        )

        return False

    except discord.HTTPException as error:

        print(
            f"[NEXUS] Alert failed: "
            f"{error}"
        )

        return False


# ==========================================================
# REPLY
# ==========================================================

async def safe_reply(text):

    if message is None:

        print(
            "[NEXUS] Cannot reply: "
            "message is None"
        )

        return False

    try:

        await message.reply(
            text,
            mention_author=False
        )

        print(
            f"[NEXUS] Reply sent "
            f"for {message.id}"
        )

        return True

    except discord.NotFound:

        print(
            "[NEXUS] Reply failed: "
            "message no longer exists"
        )

        return False

    except discord.Forbidden:

        print(
            "[NEXUS] Reply failed: "
            "missing permission"
        )

        return False

    except discord.HTTPException as error:

        print(
            f"[NEXUS] Reply failed: "
            f"{error}"
        )

        return False


# ==========================================================
# DELETE
# ==========================================================

async def safe_delete():

    if message is None:

        print(
            "[NEXUS] Cannot delete: "
            "message is None"
        )

        return False

    try:

        await message.delete()

        print(
            f"[NEXUS] Deleted "
            f"{message.id}"
        )

        return True

    except discord.NotFound:

        print(
            "[NEXUS] Message already deleted"
        )

        return False

    except discord.Forbidden:

        print(
            "[NEXUS] Delete failed: "
            "missing permission"
        )

        return False

    except discord.HTTPException as error:

        print(
            f"[NEXUS] Delete failed: "
            f"{error}"
        )

        return False


# ==========================================================
# CHANNEL CHECK
# ==========================================================

def checkchannel(channel_type):

    if channel_name is None:
        return True

    schannel = str(
        channel_name
    ).casefold()

    # 12-* and 13-* channels allow TART flagged
    # content to pass without deletion.

    if (
        schannel.startswith("13")
        or schannel.startswith("12")
    ):

        if channel_type == "tart":
            return False

    # Everything else is protected by TART.

    if channel_type == "tart":
        return True

    return True


# ==========================================================
# PROCESS
# ==========================================================

async def process():

    global toi_enabled

    if message is None:

        print(
            "[NEXUS] No message to process."
        )

        return

    # ------------------------------------------------------
    # Nexus reads the current TOI configuration here.
    # ------------------------------------------------------

    toi_enabled = get_toi_enabled()

    schannel = str(
        channel_name or ""
    ).casefold()

    toi_test_channel = (
        schannel.startswith(
            "toi-testenv"
        )
    )

    print(
        "========== NEXUS =========="
    )

    print(
        f"Message: {message_id}"
    )

    print(
        f"Guild: {guild_name}"
    )

    print(
        f"Channel: #{channel_name}"
    )

    print(
        f"TART: {tartflagged}"
    )

    print(
        f"TOI: {toiflagged}"
    )

    print(
        f"TOI Enabled: {toi_enabled}"
    )

    print(
        f"TOI Test Channel: "
        f"{toi_test_channel}"
    )

    print(
        "============================"
    )


    # ======================================================
    # NOTHING FLAGGED
    # ======================================================

    if not tartflagged and not toiflagged:

        return


    # ======================================================
    # BOTH FLAGGED
    # ======================================================
    #
    # TART is protected by the normal channel rules.
    # TOI's enabled state determines whether TOI is
    # operational, EXCEPT inside a TOI test channel.
    #
    # ======================================================

    if tartflagged and toiflagged:

        toi_should_moderate = (
            toi_enabled
            or toi_test_channel
        )

        tart_should_moderate = (
            checkchannel("tart")
        )

        description = (
            f"Message: {content}\n"
            f"User: {user_name}\n"
            f"Channel: #{channel_name}\n"
            f"TOI Reason: {toireason}\n"
            f"Person: {toiperson or 'Unknown'}\n"
            f"Crime: {toicrime or 'Unknown'}\n"
            f"TOI Enabled: {toi_enabled}\n"
            f"TOI Test Channel: {toi_test_channel}\n"
            f"TART Reason: {tartreason}"
        )

        # --------------------------------------------------
        # TOI + TART both operational
        # --------------------------------------------------

        if (
            toi_should_moderate
            and tart_should_moderate
        ):

            await safe_reply(
                "Both TOI + TART flagged your message. "
                "Don't do that again!"
            )

            await safe_delete()

            await send_alert(
                guild,
                TART_CHANNEL_NAME,
                "General Violation",
                description
            )

            await send_alert(
                guild,
                TOI_CHANNEL_NAME,
                "General Violation",
                description
            )

            return


        # --------------------------------------------------
        # TOI operational, TART allowed in this channel
        # --------------------------------------------------

        if toi_should_moderate:

            await safe_reply(
                "TOI blocked your message."
            )

            await safe_delete()

            await send_alert(
                guild,
                TOI_CHANNEL_NAME,
                "TOI Violation",
                description
            )

            print(
                "[NEXUS] TOI moderated; "
                "TART allowed by channel rules."
            )

            return


        # --------------------------------------------------
        # TOI disabled and TART allowed
        # --------------------------------------------------

        if not tart_should_moderate:

            print(
                "[NEXUS] TOI disabled/test-only and "
                "TART allowed by channel rules."
            )

            return


        # --------------------------------------------------
        # TOI disabled but TART operational
        # --------------------------------------------------

        await safe_reply(
            "TART: This message is not allowed here."
        )

        await safe_delete()

        await send_alert(
            guild,
            TART_CHANNEL_NAME,
            "TART Violation",
            description
        )

        return


    # ======================================================
    # TOI ONLY
    # ======================================================

    if toiflagged:

        # --------------------------------------------------
        # Normal channel:
        # only moderate if TOI is enabled.
        # --------------------------------------------------

        if not toi_enabled:

            if toi_test_channel:

                print(
                    "[NEXUS] TOI is disabled, "
                    "but this is a TOI test channel."
                )

            else:

                print(
                    "[NEXUS] TOI flagged message, "
                    "but TOI is disabled."
                )

                return


        await safe_reply(
            "TOI blocked your message."
        )

        await safe_delete()

        await send_alert(
            guild,
            TOI_CHANNEL_NAME,
            "TOI Violation",
            (
                f"Message: {content}\n"
                f"User: {user_name}\n"
                f"Channel: #{channel_name}\n"
                f"Reason: {toireason}\n"
                f"Person: {toiperson or 'Unknown'}\n"
                f"Crime: {toicrime or 'Unknown'}\n"
                f"TOI Enabled: {toi_enabled}\n"
                f"TOI Test Channel: {toi_test_channel}"
            )
        )

        return


    # ======================================================
    # TART ONLY
    # ======================================================

    if tartflagged:

        if checkchannel("tart") == False:

            print(
                "[NEXUS] TART flagged content "
                "inside 12+/13+; allowing."
            )

            return

        await safe_reply(
            "TART: This message is not allowed here."
        )

        await safe_delete()

        await send_alert(
            guild,
            TART_CHANNEL_NAME,
            "TART Violation",
            (
                f"Message: {content}\n"
                f"User: {user_name}\n"
                f"Channel: #{channel_name}\n"
                f"Reason: {tartreason}"
            )
        )


# ==========================================================
# DEBUG
# ==========================================================

def debug():

    print(
        "========== NEXUS DEBUG =========="
    )

    print(
        f"message       = {message}"
    )

    print(
        f"message_id    = {message_id}"
    )

    print(
        f"content       = {content!r}"
    )

    print(
        f"guild         = {guild_name}"
    )

    print(
        f"guild_id      = {guild_id}"
    )

    print(
        f"channel       = #{channel_name}"
    )

    print(
        f"channel_id    = {channel_id}"
    )

    print(
        f"category      = {category_name}"
    )

    print(
        f"category_id   = {category_id}"
    )

    print(
        f"user          = {user_name}"
    )

    print(
        f"user_id       = {user_id}"
    )

    print(
        f"in13plus      = {in13plus}"
    )

    print(
        f"tartflagged   = {tartflagged}"
    )

    print(
        f"tartreason    = {tartreason}"
    )

    print(
        f"toiflagged    = {toiflagged}"
    )

    print(
        f"toireason     = {toireason}"
    )

    print(
        f"toiperson     = {toiperson}"
    )

    print(
        f"toicrime      = {toicrime}"
    )

    print(
        f"toi_enabled   = {toi_enabled}"
    )

    print(
        f"toi_testenv   = {is_toi_test_channel()}"
    )

    print(
        "================================="
    )