import random
import discord

list = [
        "ok employed loser",
        "coming from a employee :|",
        "**employed...**"
]

async def at(message):
    content = str(message.content).strip()
    parts = content.split()

    # ─────────────────────────────────────────────
    # @toi test
    # ─────────────────────────────────────────────

    if len(parts) >= 2 and parts[0] == "@toi" and parts[1] == "test":
        guild = message.guild

        if guild is None:
            await message.channel.send(
                "❌ This command can only be used in a server."
            )
            return

        # Check if a TOI test environment already exists
        existing_env = next(
            (
                channel
                for channel in guild.text_channels
                if channel.name.startswith("toi-testenv-")
            ),
            None
        )

        if existing_env:
            await message.channel.send(
                f"⚠️ A TOI testing environment already exists: "
                f"{existing_env.mention}"
            )
            return

        # Generate numeric environment ID
        env_id = random.randint(100000, 999999)
        channel_name = f"toi-testenv-{env_id}"

        # ─────────────────────────────────────────
        # Permissions
        # ─────────────────────────────────────────

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            message.author: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
        }

        # Mentioned users
        for user in message.mentions:
            overwrites[user] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        # Mentioned roles
        for role in message.role_mentions:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        # ─────────────────────────────────────────
        # Create environment
        # ─────────────────────────────────────────

        test_channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            topic=f"TOI testing environment {env_id}"
        )

        await message.channel.send(
            f"🧪 Created TOI testing environment: "
            f"{test_channel.mention}"
        )

        await test_channel.send(
            f"🧪 **TOI Test Environment {env_id}**\n"
            f"Created by {message.author.mention}\n\n"
            f"TOI is **enabled in this environment**, even if TOI is "
            f"disabled globally."
        )

        return

    # ─────────────────────────────────────────────
    # @toi cleartst
    # ─────────────────────────────────────────────

    if content == "@toi cleartst":
        channel = message.channel

        if not channel.name.startswith("toi-testenv-"):
            await channel.send(
                "❌ You can only use `@toi cleartst` inside a "
                "TOI test environment."
            )
            return

        env_id = channel.name.removeprefix("toi-testenv-")

        if not env_id.isdigit():
            await channel.send(
                "❌ This isn't a valid TOI testing environment."
            )
            return

        await channel.send(
            "🧹 Clearing this TOI testing environment..."
        )

        await channel.delete(
            reason=f"TOI test environment {env_id} cleared by "
                   f"{message.author}"
        )

        return

    # ─────────────────────────────────────────────
    # Hey TOI
    # ─────────────────────────────────────────────

    elif content.lower().strip() in [
        "hey toi",
        "hey toi2",
        "hey toilev2",
        "hey toile"
    ]:
        await message.channel.send(
            "Hey!, Im ToiV2, My Job is to block "
            "'*Historically bad Figures*'"
        )

    elif content.lower() == "toi is a idiot":
        await message.channel.send(random.choice(list))