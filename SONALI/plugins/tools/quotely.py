# LOCAL QT PLUGIN — HEROKU SAFE
from pyrogram import filters
from pyrogram.types import Message
from AnnieXMedia import app
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap

print("🔥 LOCAL QT PLUGIN LOADED (NO API) 🔥")


def make_quote_image(text: str, author: str):
    W, H = 900, 450
    bg = (22, 18, 35)
    fg = (255, 255, 255)

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        small = ImageFont.truetype("DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()
        small = ImageFont.load_default()

    wrapped = textwrap.fill(text, 45)
    tw, th = draw.multiline_textbbox((0, 0), wrapped, font=font)[2:]

    draw.multiline_text(
        ((W - tw) / 2, (H - th) / 2 - 20),
        wrapped,
        fill=fg,
        font=font,
        align="center",
    )

    draw.text(
        (W - 30, H - 35),
        f"- {author}",
        fill=(180, 180, 180),
        font=small,
        anchor="rs",
    )

    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.name = "quote.png"
    bio.seek(0)
    return bio


@app.on_message(filters.command("qt"))
async def qt_handler(_, message: Message):
    reply = message.reply_to_message
    args = message.text.split()

    # 🧊 Processing message (EDIT hoga)
    processing = await message.reply_text("⏳ Generating quote...")

    # /qt -r (reply mode)
    if len(args) > 1 and args[1] == "-r":
        if not reply or not (reply.text or reply.caption):
            return await processing.edit("❌ Reply to a text message")

        text = reply.text or reply.caption
        author = reply.from_user.first_name if reply.from_user else "User"

    # /qt text
    elif len(args) > 1:
        text = message.text.split(None, 1)[1]
        author = message.from_user.first_name if message.from_user else "User"

    else:
        return await processing.edit(
            "❌ Usage:\n"
            "`/qt your text`\n"
            "`/qt -r` (reply to a message)`"
        )

    try:
        img = make_quote_image(text, author)
        await message.reply_photo(photo=img, caption="✨ Quotely")
        await processing.delete()

    except Exception as e:
        await processing.edit(f"❌ Failed:\n`{e}`")
