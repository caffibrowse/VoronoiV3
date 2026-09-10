import asyncio
import json
import os

import discord
from discord.ext import commands
import dotenv

from ats import toiat
from bees import audio
from honeycomb.bees import nexus
from honeycomb.bees import tart
from honeycomb.bees import toi

from honeycomb.swarm.spamprotect import (
    check_spam,
    handle_spam
)

from interact import interact
from msgskills import _msgdirect, fun
from nectar import nectar
from swarm.veto import checkswear

import ats.toiat

# ==========================================================
# CONFIG
# ==========================================================

TOI2_ROLE_NAME = "Voro3QuickAuth"

LOG_USER_ID = 1517365296392966283

TART_CHANNEL_NAME = "tart-alerts"
TOI_CHANNEL_NAME = "toi-alerts"
V3W_CHANNEL_NAME = "v3w-chat"


# ==========================================================
# ENVIRONMENT
# ==========================================================

dotenv.load_dotenv(
    "/home/cade/PycharmProjects/Voro3/.venv/.env"
)

token = os.getenv("TOKEN")


# ==========================================================
# DISCORD
# ==========================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ==========================================================
# NEXUS LOCK
# ==========================================================
#
# Nexus uses shared state.
#
# Only one message can go through:
#
#     TART
#       ↓
#     TOI
#       ↓
#     NEXUS
#
# at a time.
#
# ==========================================================

nexus_lock = asyncio.Lock()


# ==========================================================
# LOG PERMISSIONS
# ==========================================================

async def ensure_log_permissions(
    channel,
    guild
):

    user = guild.get_member(
        LOG_USER_ID
    )

    if user is None:

        print(
            f"[PERMS] User {LOG_USER_ID} "
            f"is not in {guild.name}"
        )

        return

    overwrite = channel.overwrites_for(
        user
    )

    changed = False

    if overwrite.view_channel is not True:

        overwrite.view_channel = True
        changed = True

    if overwrite.read_message_history is not True:

        overwrite.read_message_history = True
        changed = True

    if overwrite.send_messages is not True:

        overwrite.send_messages = True
        changed = True

    if changed:

        await channel.set_permissions(
            user,
            overwrite=overwrite,
            reason="Voro log-channel access repair"
        )

        print(
            f"[PERMS] Repaired access for "
            f"{user} in #{channel.name} "
            f"({guild.name})"
        )

    else:

        print(
            f"[PERMS] {user} already has access "
            f"to #{channel.name}"
        )


# ==========================================================
# ENSURE LOG CHANNEL
# ==========================================================

async def ensure_log_channel(
    guild,
    channel_name
):

    channel = discord.utils.get(
        guild.text_channels,
        name=channel_name
    )

    if channel is not None:

        print(
            f"[CHANNEL] #{channel_name} exists "
            f"in {guild.name}"
        )

        await ensure_log_permissions(
            channel,
            guild
        )

        return channel

    print(
        f"[CHANNEL] Creating #{channel_name} "
        f"in {guild.name}"
    )

    channel = await guild.create_text_channel(
        channel_name,
        reason="Voro log channel"
    )

    print(
        f"[CHANNEL] Created #{channel_name} "
        f"in {guild.name}"
    )

    await ensure_log_permissions(
        channel,
        guild
    )

    return channel


# ==========================================================
# MEMBER JOIN
# ==========================================================

@bot.event
async def on_member_join(member):

    print(
        f"{member.name} joined "
        f"{member.guild.name}"
    )

    channel = discord.utils.get(
        member.guild.text_channels,
        name="welcome-channel"
    )

    if channel:

        await channel.send(
            f"👋 Welcome, {member.mention}!"
        )

        await channel.send(
            "Please Say Hi Around the server. "
            f"Like here in : {channel}"
        )


# ==========================================================
# READY
# ==========================================================

@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )

    for guild in bot.guilds:

        try:

            # ==================================================
            # TOI ALERTS
            # ==================================================

            toi_channel = await ensure_log_channel(
                guild,
                TOI_CHANNEL_NAME
            )

            print(
                f"toi: #{toi_channel.name} "
                f"ready in {guild.name}"
            )

            print(
                f"toi ID: {toi_channel.id}"
            )


            # ==================================================
            # TART ALERTS
            # ==================================================

            tart_channel = await ensure_log_channel(
                guild,
                TART_CHANNEL_NAME
            )

            print(
                f"tart: #{tart_channel.name} "
                f"ready in {guild.name}"
            )

            print(
                f"tart ID: {tart_channel.id}"
            )


            # ==================================================
            # V3W CHAT
            # ==================================================

            v3w_channel = discord.utils.get(
                guild.text_channels,
                name=V3W_CHANNEL_NAME
            )

            if v3w_channel is None:

                v3w_channel = await guild.create_text_channel(
                    V3W_CHANNEL_NAME,
                    reason="Voro V3W chat"
                )

                print(
                    f"Created #{V3W_CHANNEL_NAME} "
                    f"in {guild.name}"
                )

            else:

                print(
                    f"v3w: #{V3W_CHANNEL_NAME} "
                    f"ready in {guild.name}"
                )

        except discord.Forbidden:

            print(
                f"Missing permissions in "
                f"{guild.name}"
            )

        except discord.HTTPException as error:

            print(
                f"Discord error in "
                f"{guild.name}: {error}"
            )

        except Exception as error:

            print(
                f"Unexpected error in "
                f"{guild.name}: {error}"
            )


# ==========================================================
# MESSAGE HANDLER
# ==========================================================

@bot.event
async def on_message(message):
    await fun.test(message)
    await audio.handle_message(message)

    if message.author.id != bot.user.id:
        if str(message.channel).endswith("-alerts"):
            await message.reply("This is a alert channel . please have conversations elsewhere")
            await message.delete()
            return

    # ======================================================
    # IGNORE BOTS
    # ======================================================
    import honeycomb.swarm.veto

    await checkswear(message)

    if message.author.bot:

        return

    await ats.toiat.at(message)

    # ======================================================
    # IGNORE DMs
    # ======================================================

    if message.guild is None:

        return


    # ======================================================
    # SPAM PROTECTION
    # ======================================================

    if check_spam(message):

        await handle_spam(message)

        return


    # ======================================================
    # TOGGLE TOI
    # ======================================================

    if (
        message.content.lower().strip()
        == "!t-toggle"
    ):

        if any(
            role.name == TOI2_ROLE_NAME
            for role in message.author.roles
        ):

            data = nectar.get_data(
                "data/toi.json"
            )

            data["enabled"] = not data.get(
                "enabled",
                False
            )

            with open(
                "honeycomb/nectar/data/toi.json",
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    data,
                    file,
                    indent=4
                )

            status = (
                "enabled"
                if data["enabled"]
                else "disabled"
            )

            await message.reply(
                f"Toi2 is now **{status}**."
            )

        else:

            await message.reply(
                "You don't have permission "
                "to toggle Toi2."
            )

        return


    # ======================================================
    # V3W INTERACTION
    # ======================================================

    if (
        message.channel.name
        == V3W_CHANNEL_NAME
    ):

        response = await interact.check_interaction(
            message
        )

        if response:

            await message.channel.send(
                response
            )


    # ======================================================
    # MESSAGE DEBUG
    # ======================================================

    print(
        "------ MESSAGE ------"
    )

    print(
        f"Author: {message.author}"
    )

    print(
        f"Channel: {message.channel}"
    )

    print(
        f"Guild: {message.guild}"
    )

    print(
        f"Content: {message.content}"
    )

    print(
        "---------------------"
    )


    # ======================================================
    # NEXUS MODERATION PIPELINE
    # ======================================================
    #
    # IMPORTANT:
    #
    # TART only detects.
    # TOI only detects.
    # Nexus decides.
    #
    # Nexus.process() is called EXACTLY ONCE.
    #
    # ======================================================

    async with nexus_lock:

        # --------------------------------------------------
        # Clear Nexus from the previous message
        # --------------------------------------------------

        nexus.reset()


        # --------------------------------------------------
        # Set current message
        # --------------------------------------------------

        nexus.update_message(
            message
        )


        # ==================================================
        # TART
        # ==================================================
        #
        # tart.check() should ONLY return:
        #
        #     flagged
        #     reason
        #
        # It should NOT:
        #
        #     delete
        #     reply
        #     alert
        #     call Nexus.process()
        #
        # ==================================================

        try:

            tart_flagged, tart_reason = tart.check(
                message
            )

        except Exception as error:

            print(
                f"[TART] Detection failed: "
                f"{error}"
            )

            tart_flagged = False
            tart_reason = None


        nexus.update_tart(
            message,
            flagged=tart_flagged,
            reason=tart_reason
        )

        # ==================================================
        # TOI
        # ==================================================
        #
        # TOI detects and feeds Nexus:
        #
        #     flagged
        #     reason
        #     person
        #     crime
        #     enabled
        #
        # Nexus makes the moderation decision.
        #
        # ==================================================

        toi_flagged = False
        toi_reason = None
        toi_person = None
        toi_crime = None
        toi_enabled = False

        try:

            toi_result = await toi.toi2mod(
                message
            )

            if (
                    isinstance(toi_result, tuple)
                    and len(toi_result) == 5
            ):

                (
                    toi_flagged,
                    toi_reason,
                    toi_person,
                    toi_crime,
                    toi_enabled
                ) = toi_result

            else:

                print(
                    "[TOI] toi2mod() returned "
                    "an invalid result."
                )

        except Exception as error:

            print(
                f"[TOI] Detection failed: "
                f"{error}"
            )

        nexus.update_toi(
            message,
            flagged=toi_flagged,
            reason=toi_reason,
            person=toi_person,
            crime=toi_crime,
            enabled=toi_enabled
        )


        # ==================================================
        # NEXUS
        # ==================================================
        #
        # THE ONE AND ONLY MODERATION DECISION.
        #
        # ==================================================

        await nexus.process()


        # ==================================================
        # CLEAN NEXUS
        # ==================================================

        nexus.reset()


    # ======================================================
    # MESSAGE DIRECTOR
    # ======================================================

    await _msgdirect.direct(
        message,
        message.content,
        bot.user.id
    )


    # ======================================================
    # DISCORD COMMANDS
    # ======================================================

    await bot.process_commands(
        message
    )


# ==========================================================
# START VORO
# ==========================================================

if not token:

    raise RuntimeError(
        "TOKEN was not found in the environment."
    )


bot.run(token)