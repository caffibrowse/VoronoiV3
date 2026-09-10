import asyncio
import os
import re
import subprocess
import tempfile
import time

import discord

import honeycomb.swarm.veto
from swarm import veto


async def handle_message(message):
    content = message.content.strip()

    # ==========================================================
    # VORO JOIN
    # ==========================================================

    if content.lower() == "@voro join":
        if not message.author.voice:
            await message.channel.send(
                "You need to be in a voice channel first!"
            )
            return

        channel = message.author.voice.channel
        voice_client = message.guild.voice_client

        try:
            if voice_client and voice_client.is_connected():
                await voice_client.move_to(channel)
            else:
                await channel.connect()

            await message.channel.send(
                f"Joined **{channel.name}**!"
            )

        except Exception as error:
            print(f"[AUDIO] Join failed: {error}")
            await message.channel.send(
                f"Couldn't join the voice channel: `{error}`"
            )

        return

    # ==========================================================
    # VORO TTS
    # ==========================================================

    match = re.fullmatch(
        r'@voro\s+tts\s+"(.+)"',
        content,
        re.IGNORECASE | re.DOTALL
    )

    if match:
        text = match.group(1).strip()

        if not text:
            await message.channel.send(
                "You need to put something inside the quotes."
            )
            return

        voice_client = message.guild.voice_client

        if not voice_client or not voice_client.is_connected():
            await message.channel.send(
                "I'm not in a VC! Use `@voro join` first."
            )
            return

        substitutes = {
            "idk": "i dont know",
            "bc": "because",
            "ttyl": "talk to you later",
            "jpg": "jpeg",
            "they're": "they are",
            "alr": "alright."
        }

        for old, new in substitutes.items():
            text = text.replace(old, new)

        filtered = await veto.checkswear(message, type="AudioFiltered")
        j4xx = await veto.checkswear(message, type="Jxx")
        if filtered == "true":
            text = [f"{message.author.name}",
                    "filtered",
                    f"{j4xx}"]
            for i in text:
                await speak(voice_client, i)
                time.sleep(0.3)
        else:
            await speak(voice_client, text)

        return


async def speak(voice_client, text):
    temp_dir = tempfile.gettempdir()

    wav_path = os.path.join(
        temp_dir,
        f"voro_tts_{os.getpid()}.wav"
    )

    try:
        # ------------------------------------------------------
        # Generate speech with espeak-ng
        # ------------------------------------------------------

        await asyncio.to_thread(
            subprocess.run,
            [
                "espeak-ng",
                "-w",
                wav_path,
                text
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

        # ------------------------------------------------------
        # Play speech
        # ------------------------------------------------------

        if voice_client.is_playing():
            voice_client.stop()

        source = discord.FFmpegPCMAudio(
            wav_path
        )

        finished = asyncio.Event()

        def after(error):
            if error:
                print(f"[AUDIO] Playback error: {error}")

            asyncio.run_coroutine_threadsafe(
                finish(),
                voice_client.client.loop
            )

        async def finish():
            finished.set()

        voice_client.play(
            source,
            after=after
        )

        await finished.wait()

    except FileNotFoundError:
        print("[AUDIO] espeak-ng was not found.")
    except subprocess.CalledProcessError as error:
        print(
            f"[AUDIO] TTS generation failed: "
            f"{error.stderr.decode(errors='ignore')}"
        )
    except Exception as error:
        print(f"[AUDIO] TTS error: {error}")

    finally:
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass