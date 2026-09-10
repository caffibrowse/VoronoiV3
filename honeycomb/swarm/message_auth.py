import discord


TOI2_CHANNEL_NAME = "sieve-alerts"
TOI2_ROLE_NAME = "Voro3QuickAuth"


async def get_alert_channel(guild: discord.Guild):
    """
    Get the toi2 alert channel for a guild.
    Creates it if it doesn't exist and the Voro3QuickAuth role exists.
    """

    # Check for an existing channel
    channel = discord.utils.get(
        guild.text_channels,
        name=TOI2_CHANNEL_NAME
    )

    if channel:
        return channel

    # Find the QuickAuth role
    role = discord.utils.get(
        guild.roles,
        name=TOI2_ROLE_NAME
    )

    if role is None:
        return None

    # Permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),

        role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            read_message_history=True
        ),

        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
            manage_channels=True
        )
    }

    channel = await guild.create_text_channel(
        TOI2_CHANNEL_NAME,
        overwrites=overwrites,
        reason="toi2 alert channel"
    )

    return channel


async def send_alert(
    guild: discord.Guild,
    message: str,
    title: str | None = None,
    description: str | None = None,
    color: discord.Color | None = None
):
    """
    Send an alert to a guild's toi2 channel.

    message:
        Plain text message.

    title:
        Optional embed title.

    description:
        Optional embed description.

    color:
        Optional embed color.
    """

    channel = await get_alert_channel(guild)

    if channel is None:
        return False

    # Simple text alert
    if title is None and description is None:
        await channel.send(message)
        return True

    # Embed alert
    embed = discord.Embed(
        title=title or "toi2 Alert",
        description=description or message,
        color=color or discord.Color.blurple()
    )

    await channel.send(
        content=message,
        embed=embed
    )

    return True