from pyrogram import filters
from pyrogram.types import Message
from SONALI import app
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap

print("🔥 LOCAL QT PLUGIN LOADED (HEROKU SAFE) 🔥")


def create_quote_image(text, author):
    width, height = 800, 400
    bg_color = (30, 30, 30)
    text_color = (255, 255, 255)

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        small = ImageFont.truetype("DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()
        small = ImageFont.load_default()

    wrapped = textwrap.fill(text, 40)
    w, h = draw.multiline_textsize(wrapped, font=font)

    draw.multiline_text(
        ((width - w) / 2, (height - h) / 2 - 20),
        wrapped,
        fill=text_color,
        font=font,
        align="center"
    )

    draw.text(
        (width - 20, height - 40),
        f"- {author}",
        fill=(200, 200, 200),
        font=small,
        anchor="rs"
    )

    file = io.BytesIO()
    img.save(file, "PNG")
    file.name = "quote.png"
    file.seek(0)
    return file


@app.on_message(filters.command("qt"))
async def qt_handler(_, message: Message):
    reply = message.reply_to_message
    cmd = message.command

    if len(cmd) == 2 and cmd[1] == "-r":
        if not reply or not reply.text:
            return await message.reply("❌ Reply to a text message")

        text = reply.text
        author = reply.from_user.first_name

    elif len(cmd) > 1:
        text = message.text.split(None, 1)[1]
        author = message.from_user.first_name

    else:
        return await message.reply(
            "❌ Usage:\n"
            "`/qt your text`\n"
            "`/qt -r` (reply)"
        )

    img = create_quote_image(text, author)
    await message.reply_photo(img, caption="✨ Quotely")
