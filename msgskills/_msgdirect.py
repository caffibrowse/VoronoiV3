from decoders import numbers, strings
async def direct(message, content, bot_id):
    if message.author.id == bot_id:
        return

    if content.isdigit():
        await numbers.decode(message)

    elif isinstance(content, str):
        await strings.handle(message)

