# SONALI/plugins/management/nsfw.py
import logging
import asyncio
import aiohttp
import io
import time
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message

from SONALI.utils.decorators import AdminRights
from SONALI.database.client import (
    set_nsfw_status,
    get_nsfw_status,
    get_cached_scan,
    cache_scan_result
)

logger = logging.getLogger(__name__)
NSFW_API_URL = "https://nexacoders-nexa-api.hf.space/scan"

# Global Session
ai_session = None

async def get_session():
    global ai_session
    if ai_session is None or ai_session.closed:
        ai_session = aiohttp.ClientSession()
    return ai_session

# --- OPTIMIZATION ENGINE ---

def optimize_image(image_bytes: bytes) -> bytes:
    """
    Hyper-Fast Optimization:
    1. If file < 50KB, return immediately.
    2. Else, resize to 256px JPEG.
    """
    if len(image_bytes) < 50 * 1024:
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        img.thumbnail((256, 256))
        out_io = io.BytesIO()
        img.save(out_io, format="JPEG", quality=80)
        return out_io.getvalue()
    except Exception:
        return image_bytes

# --- FORMATTING ---

def format_scores_ui(scores: dict) -> str:
    icons = {
        "porn": "🔞",
        "hentai": "👾",
        "sexy": "💋",
        "neutral": "😐",
        "drawings": "🎨"
    }

    sorted_scores = sorted(scores.items(), key=lambda i: i[1], reverse=True)
    lines = []

    for label, score in sorted_scores:
        icon = icons.get(label, "🔸")
        lines.append(f"{icon} `{label.title().ljust(10)} : {score * 100:05.2f}%`")

    return "\n".join(lines)

# --- 1. SETTINGS ---

@Client.on_message(filters.command("nsfw") & filters.group)
@AdminRights("can_change_info")
async def nsfw_toggle_command(client: Client, message: Message):
    if len(message.command) < 2:
        status = await get_nsfw_status(message.chat.id)
        state = "Enabled" if status else "Disabled"
        await message.reply_text(
            f"🚀 **SONALI NSFW System:** `{state}`\n"
            f"Usage: `/nsfw on` or `/nsfw off`"
        )
        return

    action = message.command[1].lower()

    if action in ["on", "enable", "true"]:
        await set_nsfw_status(message.chat.id, True)
        await message.reply_text("🚀 **SONALI NSFW Activated.**")
    elif action in ["off", "disable", "false"]:
        await set_nsfw_status(message.chat.id, False)
        await message.reply_text("💤 **SONALI NSFW Paused.**")

# --- 2. MANUAL SCAN ---

@Client.on_message(filters.command("scan"))
async def manual_scan_command(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("⚠️ Reply to media.")
        return

    status_msg = await message.reply_text("⚡ **SONALI Scanning...**")
    start = time.time()

    is_nsfw, data, reason = await process_media_scan(
        client, message.reply_to_message, manual_override=True
    )

    taken = time.time() - start

    if not data:
        await status_msg.edit_text("❌ SONALI Scan Failed.")
        return

    header = "🚨 **UNSAFE**" if is_nsfw else "✅ **SAFE**"
    color = "🟥" if is_nsfw else "🟩"

    await status_msg.edit_text(
        f"{header}\n"
        f"⏱️ **Time:** `{taken:.3f}s`\n"
        f"🔎 **Verdict:** `{reason}`\n"
        f"{color * 12}\n\n"
        f"📊 **SONALI AI Scores:**\n"
        f"{format_scores_ui(data.get('scores', {}))}"
    )

# --- 3. AUTO WATCHER ---

@Client.on_message(
    filters.group & (filters.photo | filters.sticker | filters.document),
    group=5
)
async def nsfw_watcher(client: Client, message: Message):
    if not await get_nsfw_status(message.chat.id):
        return

    is_nsfw, data, reason = await process_media_scan(
        client, message, manual_override=False
    )

    if is_nsfw and data:
        await handle_nsfw_detection(client, message, data, reason)

# --- 4. CORE ENGINE ---

def check_strict_nsfw(scores: dict) -> tuple[bool, str]:
    porn = scores.get("porn", 0.0)
    hentai = scores.get("hentai", 0.0)
    sexy = scores.get("sexy", 0.0)

    if porn > 0.08:
        return True, f"Porn {porn * 100:.0f}%"
    if hentai > 0.15:
        return True, f"Hentai {hentai * 100:.0f}%"
    if sexy > 0.45:
        return True, f"Explicit {sexy * 100:.0f}%"
    if (porn + hentai + sexy) > 0.40:
        return True, "High Risk Content"

    return False, "Safe"

async def process_media_scan(
    client: Client,
    message: Message,
    manual_override: bool = False
):
    media = None
    file_unique_id = None
    use_thumbnail = False

    if message.sticker:
        media = message.sticker
        file_unique_id = media.file_unique_id

        if media.is_animated or media.is_video:
            use_thumbnail = True
            if not media.thumbs:
                return False, None, "No Thumbnail"

    elif message.photo:
        media = message.photo
        file_unique_id = media.file_unique_id

    elif message.document:
        if message.document.mime_type and "image" in message.document.mime_type:
            media = message.document
            file_unique_id = media.file_unique_id
        else:
            return False, None, "Not Image"

    if not file_unique_id:
        return False, None, "No ID"

    if not manual_override:
        cached = await get_cached_scan(file_unique_id)
        if cached:
            is_nsfw, reason = check_strict_nsfw(cached["data"]["scores"])
            return is_nsfw, cached["data"], reason

    try:
        if hasattr(media, "file_size") and media.file_size > 10 * 1024 * 1024:
            return False, None, "Too Large"

        if use_thumbnail:
            thumb = media.thumbs[-1]
            image_stream = await client.download_media(
                thumb.file_id, in_memory=True
            )
        else:
            image_stream = await client.download_media(
                message, in_memory=True
            )

        raw_bytes = bytes(image_stream.getbuffer())
        image_bytes = optimize_image(raw_bytes)

        if not image_bytes:
            return False, None, "Download Failed"

    except Exception:
        return False, None, "Download Error"

    try:
        session = await get_session()
        form = aiohttp.FormData()
        form.add_field(
            "file",
            image_bytes,
            filename="scan.jpg",
            content_type="image/jpeg"
        )

        async with session.post(
            NSFW_API_URL, data=form, timeout=6
        ) as response:
            if response.status != 200:
                return False, None, "API Error"
            scan_data = await response.json()

    except Exception:
        return False, None, "Connection Error"

    scores = scan_data.get("scores", {})
    is_nsfw, reason = check_strict_nsfw(scores)
    await cache_scan_result(file_unique_id, not is_nsfw, scan_data)

    return is_nsfw, scan_data, reason

async def handle_nsfw_detection(client, message, data, reason):
    try:
        await message.delete()
        score_block = format_scores_ui(data.get("scores", {}))

        text = (
            f"🔔 **SONALI NSFW Content Removed**\n"
            f"👤 **User:** {message.from_user.mention}\n"
            f"🚨 **Reason:** {reason}\n"
            f"<blockquote>\n"
            f"📊 **SONALI AI Analysis:**\n"
            f"{score_block}\n"
            f"</blockquote>"
        )

        msg = await client.send_message(message.chat.id, text)
        await asyncio.sleep(15)
        await msg.delete()

    except Exception:
        pass
