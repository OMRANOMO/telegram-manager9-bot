import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("TOKEN_MANAGER")
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = f"https://telegram-manager9-bot.onrender.com/{TOKEN}"

app = Application.builder().token(TOKEN).build()

# عرض لوحة التحكم
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_dashboard(update, context)

# توليد لوحة التحكم
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("test_status.json", "r") as f:
            status_data = json.load(f)
    except FileNotFoundError:
        status_data = {}

    keyboard = []
    for i in range(1, 33):
        status = status_data.get(str(i), "on")
        label = f"الاختبار {i}"
        toggle = "🔴 off" if status == "off" else "🟢 on"
        keyboard.append([
            InlineKeyboardButton(label, callback_data=f"noop"),
            InlineKeyboardButton(toggle, callback_data=f"toggle_{i}")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠 لوحة التحكم:", reply_markup=reply_markup)

# التعامل مع الضغط على الأزرار
async def handle_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("toggle_"):
        test_id = query.data.split("_")[1]

        try:
            with open("test_status.json", "r") as f:
                status_data = json.load(f)
        except FileNotFoundError:
            status_data = {}

        current = status_data.get(test_id, "on")
        status_data[test_id] = "off" if current == "on" else "on"

        with open("test_status.json", "w") as f:
            json.dump(status_data, f)

       # إعادة توليد لوحة التحكم مباشرة
try:
    with open("test_status.json", "r") as f:
        status_data = json.load(f)
except FileNotFoundError:
    status_data = {}

keyboard = []
for i in range(1, 33):
    status = status_data.get(str(i), "on")
    label = f"الاختبار {i}"
    toggle = "🔴 off" if status == "off" else "🟢 on"
    keyboard.append([
        InlineKeyboardButton(label, callback_data="noop"),
        InlineKeyboardButton(toggle, callback_data=f"toggle_{i}")
    ])

reply_markup = InlineKeyboardMarkup(keyboard)

# تعديل الرسالة فقط إذا تغير شيء فعليًا
await query.edit_message_reply_markup(reply_markup=reply_markup)


# تسجيل الأوامر
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_toggle))

# تشغيل البوت باستخدام Webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=WEBHOOK_URL
)

