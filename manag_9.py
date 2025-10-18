import os
import json
import base64
import requests
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
WEBHOOK_URL = f"https://telegram-manager9-bot.onrender.com/{TOKEN}"  # غيّر هذا إلى رابط خدمة Render الخاصة بك

# إعداد GitHub
GH_TOKEN = os.getenv("GH_TOKEN")  # تأكد أنه مضاف في إعدادات Render
GH_REPO = "OMRANOMO/telegram-manager9-bot"  # غيّر هذا إلى اسم مستودعك
GH_BRANCH = "main"
GH_FILE_PATH = "test_status.json"

# مسار الملف المحلي
STATUS_FILE = os.path.abspath("test_status.json")

# إنشاء التطبيق
app = Application.builder().token(TOKEN).build()

# رفع الملف إلى GitHub
def upload_status_to_github():
    if not GH_TOKEN:
        print("❌ GH_TOKEN غير موجود في متغيرات البيئة.")
        return

    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        encoded_content = base64.b64encode(content.encode()).decode()

        url = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE_PATH}"
        headers = {
            "Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

        # الحصول على SHA الحالي
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha")

        data = {
            "message": "تحديث حالة الاختبارات من بوت الإدارة",
            "content": encoded_content,
            "branch": GH_BRANCH,
        }
        if sha:
            data["sha"] = sha

        r = requests.put(url, headers=headers, json=data)
        if r.status_code in [200, 201]:
            print("✅ تم رفع test_status.json إلى GitHub بنجاح.")
        else:
            print("❌ فشل رفع الملف إلى GitHub:", r.status_code, r.text)

    except Exception as e:
        print("❌ خطأ أثناء رفع الملف إلى GitHub:", e)

# عرض لوحة التحكم
async def show_dashboard(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
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
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status_data = json.load(f)
        except FileNotFoundError:
            status_data = {}

        current = status_data.get(test_id, "on")
        status_data[test_id] = "off" if current == "on" else "on"

        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        upload_status_to_github()  # رفع التحديث إلى GitHub

        await show_dashboard(query, context)

# تسجيل المعالجات
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_toggle))

# تشغيل البوت باستخدام Webhook
if __name__ == "__main__":
    print("✅ بوت الإدارة يعمل. المسار الكامل للملف:", STATUS_FILE)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL
    )
