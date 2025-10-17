import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# إعداد التوكن والمنفذ
TOKEN = os.getenv("TOKEN_MANAGER")
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = f"https://telegram-manager9-bot.onrender.com/{TOKEN}"  # غيّر هذا إلى رابط بوتك على Render

# إنشاء التطبيق
app = Application.builder().token(TOKEN).build()

# دالة عرض لوحة التحكم
async def show_dashboard(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("test_status.json", "r") as f:
            status_data = json.load(f)
    except FileNotFoundError:
        status_data = {}

    keyboard = []
    for i in range(1, 33):
        test_id = str(i)
        status = status_data.get(test_id, "on")
        label = f"الاختبار {i}"
        toggle = "🔴 off" if status == "off" else "🟢 on"
        keyboard.append([
            InlineKeyboardButton(label, callback_data="noop"),
            InlineKeyboardButton(toggle, callback_data=f"toggle_{test_id}")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text("🛠 لوحة التحكم:", reply_markup=reply_markup)
    else:
        await update_or_query.edit_message_reply_markup(reply_markup=reply_markup)

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_dashboard(update, context)

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

        # تحديث لوحة التحكم مباشرة بدون تغيير النص
        await show_dashboard(query, context)

# تسجيل الأوامر والمعالجات
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_toggle))

# تشغيل البوت باستخدام Webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=WEBHOOK_URL
)
