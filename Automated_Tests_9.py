import os
import json
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# إعداد التوكن والمنفذ
TOKEN = os.getenv("TOKEN_TEST")
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://اسم-الخدمة.onrender.com{WEBHOOK_PATH}"  # غيّر "اسم-الخدمة" إلى اسم خدمتك في Render

# إنشاء التطبيق
app = Application.builder().token(TOKEN).build()

# تحميل حالة الاختبارات من ملف
def load_status():
    try:
        with open("test_status.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_status(data):
    with open("test_status.json", "w") as f:
        json.dump(data, f)

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك في بوت الاختبارات! أرسل إجابتك مباشرة.")

# استقبال الإجابات
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    answer = update.message.text.strip()

    status = load_status()
    status[user] = answer
    save_status(status)

    await update.message.reply_text(f"✅ تم تسجيل إجابتك: {answer}")

# أمر /myanswer
async def my_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    status = load_status()
    answer = status.get(user)

    if answer:
        await update.message.reply_text(f"📌 إجابتك الحالية: {answer}")
    else:
        await update.message.reply_text("❗ لم يتم تسجيل أي إجابة لك بعد.")

# تسجيل الأوامر والمعالجات
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("myanswer", my_answer))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# تشغيل البوت باستخدام Webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=WEBHOOK_URL
)
