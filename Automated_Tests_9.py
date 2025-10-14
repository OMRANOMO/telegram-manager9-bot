import os
import time
import asyncio
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN_QUIZ")
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = f"https://telegram-Quize9-bot.onrender.com/{TOKEN}"  # غيّر "اسم-الخدمة"
GROUP_CHAT_ID = -100758881451  # تأكد أن البوت مضاف كمشرف

MATH_QUESTIONS = [
    {"q": "ما ناتج 7 × 8؟", "options": ["54", "56", "58"], "correct": 1},
    {"q": "ما هو الجذر التربيعي لـ 81؟", "options": ["9", "8", "7"], "correct": 0},
    {"q": "كم عدد أضلاع المثلث؟", "options": ["3", "4", "5"], "correct": 0},
    {"q": "ما هو ناتج 12 ÷ 3؟", "options": ["4", "3", "6"], "correct": 0},
    {"q": "ما هو ناتج 15 + 27؟", "options": ["42", "43", "41"], "correct": 0},
    {"q": "كم ثانية في دقيقة؟", "options": ["60", "100", "90"], "correct": 0},
    {"q": "ما هو ناتج 9 × 9؟", "options": ["81", "72", "99"], "correct": 0},
]

user_data = {}

# عرض زر البداية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("ابدأ")]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await update.message.reply_text("👋 مرحبًا بك في بوت الاختبارات", reply_markup=keyboard)

# عرض قائمة الاختبارات
async def show_tests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text != "ابدأ":
        return
    buttons = []
    for i in range(1, 33):
        buttons.append([KeyboardButton(f"الاختبار {i}")])
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("📚 اختر الاختبار:", reply_markup=markup)

# بدء جمع بيانات الطالب
async def select_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.startswith("الاختبار "):
        return
    user_id = update.effective_user.id
    test_id = int(text.split(" ")[1])
    user_data[user_id] = {
        "step": "name",
        "test_id": test_id,
        "answers": [],
        "start_time": None,
        "current_q": 0,
    }
    await update.message.reply_text(f"📝 اختبار رقم {test_id}\nأدخل اسمك الثلاثي:")

# جمع بيانات الطالب خطوة بخطوة
async def collect_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id)

    if not data:
        await show_tests(update, context)
        return

    step = data["step"]
    if step == "name":
        data["name"] = text
        data["step"] = "phone"
        await update.message.reply_text("📞 أدخل رقم هاتفك:")
    elif step == "phone":
        data["phone"] = text
        data["step"] = "school"
        await update.message.reply_text("🏫 أدخل اسم المدرسة أو المعهد:")
    elif step == "school":
        data["school"] = text
        data["step"] = "grade"
        await update.message.reply_text("📚 أدخل الصف الدراسي:")
    elif step == "grade":
        data["grade"] = text
        data["step"] = "ready"
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("أنا جاهز للاختبار")]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        await update.message.reply_text("⏱ مدة الاختبار 14 دقيقة\n❗ الأسئلة تظهر بشكل متتالي", reply_markup=keyboard)
    elif step == "ready" and text == "أنا جاهز للاختبار":
        data["start_time"] = time.time()
        data["step"] = "quiz"
        await update.message.reply_text("✅ بدأ الاختبار\n⏳ باقي من الوقت 14 دقيقة")
        asyncio.create_task(send_timer(update, context))
        await send_question(update, context)
    elif step == "quiz":
        await handle_answer(update, context)

# إرسال الوقت المتبقي كل دقيقتين
async def send_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    for i in range(2, 15, 2):
        await asyncio.sleep(120)
        if user_data.get(user_id, {}).get("current_q", 7) < 7:
            await context.bot.send_message(chat_id=user_id, text=f"⏳ باقي من الوقت {14 - i} دقيقة")
    # بعد انتهاء الوقت
    if user_data.get(user_id, {}).get("current_q", 7) < 7:
        await context.bot.send_message(chat_id=user_id, text="⏰ انتهى الوقت! سيتم إنهاء الاختبار الآن.")
        await finish_quiz(update, context)

# إرسال السؤال التالي
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    q_index = data["current_q"]

    if q_index >= len(MATH_QUESTIONS):
        await finish_quiz(update, context)
        return

    q = MATH_QUESTIONS[q_index]
    options = [[KeyboardButton(opt)] for opt in q["options"]]
    markup = ReplyKeyboardMarkup(options, one_time_keyboard=True, resize_keyboard=True)
    await context.bot.send_message(chat_id=user_id, text=f"❓ السؤال {q_index + 1}: {q['q']}", reply_markup=markup)

# استقبال الإجابة ومعالجتها
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    q_index = data["current_q"]
    selected_text = update.message.text.strip()
    correct_index = MATH_QUESTIONS[q_index]["correct"]
    correct_text = MATH_QUESTIONS[q_index]["options"][correct_index]
    data["answers"].append(selected_text == correct_text)
    data["current_q"] += 1
    await update.message.delete()

    if time.time() - data["start_time"] > 14 * 60 or data["current_q"] >= len(MATH_QUESTIONS):
        await finish_quiz(update, context)
    else:
        await send_question(update, context)

# إنهاء الاختبار وإرسال النتيجة
async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    score = sum(data["answers"])
    result = "✅ ناجح" if score >= 4 else "❌ راسب"
    summary = f"📊 النتيجة: {score}/7 - {result}\n\n📋 الإحصائية:\n"
    for i, correct in enumerate(data["answers"]):
        symbol = "✅" if correct else "❌"
        correct_answer = MATH_QUESTIONS[i]["options"][MATH_QUESTIONS[i]["correct"]]
        summary += f"سؤال {i+1}: {symbol} ({correct_answer if not correct else ''})\n"

    await context.bot.send_message(chat_id=user_id, text="🏁 انتهى الاختبار!\n" + summary)
    full_info = (
        f"🧪 اختبار رقم {data['test_id']}\n"
        f"👤 {data['name']}\n📞 {data['phone']}\n🏫 {data['school']}\n📚 {data['grade']}\n\n" + summary
    )
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=full_info)

    # إعادة عرض قائمة الاختبارات
       buttons = []
    for i in range(1, 33):
        buttons.append([KeyboardButton(f"الاختبار {i}")])
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    await context.bot.send_message(chat_id=user_id, text="📚 اختر اختبارًا جديدًا:", reply_markup=markup)
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, show_tests))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, select_test))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_info))
app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=WEBHOOK_URL)

