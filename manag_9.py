from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import json
import os

# إعدادات البوت
TOKEN_MANAGER = os.getenv("TOKEN_MANAGER")
STATUS_FILE = "test_status.json"

# تحميل حالة الاختبارات من ملف JSON
def load_status():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for i in range(1, 33):
                key = f"الاختبار {i}"
                if key not in data:
                    data[key] = "on"
            return data
        except:
            pass
    return {f"الاختبار {i}": "on" for i in range(1, 33)}

# حفظ الحالة في الملف
def save_status(status):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

# توليد لوحة التحكم
def generate_management_keyboard(status):
    buttons = []
    for i in range(1, 33):
        test_name = f"الاختبار {i}"
        current = status[test_name]
        toggle = "off" if current == "on" else "on"
        buttons.append([
            InlineKeyboardButton(test_name, callback_data="noop"),
            InlineKeyboardButton(current.upper(), callback_data=f"toggle_{test_name}_{toggle}")
        ])
    return InlineKeyboardMarkup(buttons)

# بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"معرف المجموعة هو: {update.effective_chat.id}")
    keyboard = [[InlineKeyboardButton("manag", callback_data="manage")]]
    await update.message.reply_text("👋 أهلاً بك في بوت الإدارة", reply_markup=InlineKeyboardMarkup(keyboard))

# التعامل مع الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status = load_status()

    if query.data == "manage":
        keyboard = generate_management_keyboard(status)
        await query.message.reply_text("🛠 إدارة حالة الاختبارات:", reply_markup=keyboard)

    elif query.data.startswith("toggle_"):
        _, test_name, new_status = query.data.split("_")
        status[test_name] = new_status
        save_status(status)

        # تحديث الرسالة الحالية بلوحة جديدة
        keyboard = generate_management_keyboard(status)
        await query.edit_message_reply_markup(reply_markup=keyboard)

# استقبال الإحصائيات من بوت الاختبارات
async def receive_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 تم استلام إحصائية:\n\n{update.message.text}")

# تشغيل البوت
app = ApplicationBuilder().token(TOKEN_MANAGER).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_stats))

print("✅ Manager bot is running...")
app.run_polling()

