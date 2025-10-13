import os
import json
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# إعداد التوكن والمنفذ
TOKEN = os.getenv("TOKEN_MANAGER")
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://telegram-manager9-bot.onrender.com{WEBHOOK_PATH}"  # غيّر "اسم-الخدمة" إلى اسم خدمتك في Render
GROUP_CHAT_ID = -100758881451  # غيّر هذا إلى معرف مجموعتك

# إنشاء التطبيق
app = Application.builder().token(TOKEN).build()

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! هذا بوت الإدارة.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 البوت يعمل بشكل جيد!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 قائمة الأوامر:\n"
        "/start - بدء المحادثة\n"
        "/status - حالة البوت\n"
        "/help - المساعدة\n"
        "/broadcast <نص> - إرسال رسالة إلى المجموعة\n"
        "/reset - إعادة تعيين حالة الاختبارات\n"
        "/stats - عرض إحصائيات الاختبارات"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        message = "📢 " + " ".join(context.args)
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
        await update.message.reply_text("✅ تم إرسال الرسالة إلى المجموعة.")
    else:
        await update.message.reply_text("❗ يرجى كتابة الرسالة بعد الأمر /broadcast")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("test_status.json", "w") as f:
            json.dump({}, f)
        await update.message.reply_text("✅ تم إعادة تعيين حالة الاختبارات.")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء إعادة التعيين: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("test_status.json", "r") as f:
            data = json.load(f)
        if not data:
            await update.message.reply_text("📊 لا توجد بيانات حتى الآن.")
        else:
            msg = "📈 إحصائيات الاختبارات:\n"
            for user, score in data.items():
                msg += f"- {user}: {score}\n"
            await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء قراءة البيانات: {e}")

# تسجيل الأوامر
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(CommandHandler("stats", stats))

# تشغيل البوت باستخدام Webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=WEBHOOK_URL
)
