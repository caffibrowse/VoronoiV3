messages = {
    "1214": "brb"
}

messages_response = {
    "brb": "👋"
}

async def decode(message):
    for key, value in messages.items():
        if key in message.content:
            await message.reply(messages_response[value])