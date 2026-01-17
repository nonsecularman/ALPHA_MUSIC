import aiohttp
import io
from pyrogram import filters
from pyrogram.types import Message
from SONALI import app

# ✅ ONLY WORKING API (OLD API REMOVED COMPLETELY)
API_URL = "https://api.quotly.dev/generate"

print("🔥 QT PLUGIN LOADED ON HEROKU 🔥")
print("🔥 USING API:", API_URL)


async def generate_quote(text, user):
    payload = {
        "type": "quote",
        "messages": [
            {
                "text": text,
                "author": {
                    "id": user.id,
                    "name": user.first_name or "User",
                    "username": user.username or ""
                },
                "reply": False
            }
        ]
    }

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(API_URL, json=payload) as resp:
            if resp.status != 200:
                raise Exception(f"API ERROR: {resp.status}")

            data = await resp.read()
            if not data:
                raise Exception("EMPTY IMAGE DATA")

            file = io.BytesIO(data)
            file.name = "quote.png"
            file.seek(0)
            return file


@app.on_message(filters.command("qt"))
async def qt_handler(_, message: Message):
    reply = message.reply_to_message
    cmd = message.command

    # /qt -r (reply quote)
    if len(cmd) == 2 and cmd[1] == "-r":
        if not reply or not (reply.text or reply.caption):
            return await message.reply("❌ Reply to a text message")

        quote_text = reply.text or reply.caption
        quote_user = reply.from_user

    # /qt text
    elif len(cmd) > 1:
        quote_text = message.text.split(None, 1)[1]
        quote_user = reply.from_user if reply else message.from_user

    else:
        return await message.reply(
            "❌ Usage:\n"
            "`/qt your text`\n"
            "`/qt -r` (reply to a message)"
        )

    try:
        img = await generate_quote(quote_text, quote_user)
        await message.reply_photo(photo=img, caption="✨ Quotely")

    except Exception as e:
        await message.reply(f"❌ Quote generate failed\n`{e}`")
