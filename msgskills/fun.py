async def test(message):
    if message.author.id in ["1517365296392966283", "1414714265599873084"]:
        if str(message.content).lower() == "hi voro":
            await message.reply("Hi Pyx!")