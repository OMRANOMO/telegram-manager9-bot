import os
import time
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN_QUIZ")
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = f"https://telegram-Quize9-bot.onrender.com/{TOKEN}"  # غيّر "اسم-الخدمة"
ADMIN_USER_ID = 758881451  # ← ضع هنا معرفك الشخصي

QUESTIONS = [
    {"q": "ما ناتج 7 × 8؟", "options": ["54", "56", "58"], "correct": 1},
    {"q": "ما هو الجذر التربيعي لـ 81؟", "options": ["9", "8", "7"], "correct": 0},
    {"q": "كم عدد أضلاع المثلث؟", "options": ["3", "4", "5"], "correct": 0},
    {"q": "ما هو ناتج 12 ÷ 3؟", "options": ["4", "3", "6"], "correct": 0},
    {"q": "ما هو ناتج 15 + 27؟", "options": ["42", "43", "41"], "correct": 0},
    {"q": "كم ثانية في دقيقة؟", "options": ["60", "100", "90"], "correct": 0},
    {"q": "ما هو ناتج 9 × 9؟", "options": ["81", "72", "99"], "correct": 0},
]

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True)
    await update.message.reply_text("👋 مرحبًا بك في بوت الاختبارات", reply_markup=keyboard)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id)

    if text == "ابدأ":
        buttons = [[KeyboardButton(f"الاختبار {i}")] for i in range(1, 33)]
        markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("📚 اختر الاختبار:", reply_markup=markup)
        return

    if text.startswith("الاختبار "):
        test_id = int(text.split(" ")[1])
        user_data[user_id] = {
            "step": "name",
            "test_id": test_id,
            "answers": [],
            "start_time": None,
            "current_q": 0,
        }
        await update.message.reply_text(f"📝 اختبار رقم {test_id}\nأدخل اسمك الثلاثي:")
        return

    if not data:
        await update.message.reply_text("❗ اضغط /start للبدء.")
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
        keyboard = ReplyKeyboardMarkup([[KeyboardButton("أنا جاهز للاختبار")]], resize_keyboard=True)
        await update.message.reply_text("⏱ مدة الاختبار 14 دقيقة\n❗ الأسئلة تظهر بشكل متتالي", reply_markup=keyboard)
    elif step == "ready" and text == "أنا جاهز للاختبار":
        data["start_time"] = time.time()
        data["step"] = "quiz"
        await update.message.reply_text("✅ بدأ الاختبار\n⏳ باقي من الوقت 14 دقيقة")
        asyncio.create_task(send_timer(update, context))
        await send_question(update, context)
    elif step == "quiz":
        await handle_answer(update, context)

async def send_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    for i in range(2, 15, 2):
        await asyncio.sleep(120)
        if user_data.get(user_id, {}).get("current_q", 7) < 7:
            await context.bot.send_message(chat_id=user_id, text=f"⏳ باقي من الوقت {14 - i} دقيقة")
    if user_data.get(user_id, {}).get("current_q", 7) < 7:
        await context.bot.send_message(chat_id=user_id, text="⏰ انتهى الوقت! سيتم إنهاء الاختبار الآن.")
        await finish_quiz(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    q_index = data["current_q"]

    if q_index >= len(QUESTIONS):
        await finish_quiz(update, context)
        return

    q = QUESTIONS[q_index]
    options = [[KeyboardButton(opt)] for opt in q["options"]]
    markup = ReplyKeyboardMarkup(options, one_time_keyboard=True, resize_keyboard=True)
    await context.bot.send_message(chat_id=user_id, text=f"❓ السؤال {q_index + 1}: {q['q']}", reply_markup=markup)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    q_index = data["current_q"]
    selected_text = update.message.text.strip()
    correct_index = QUESTIONS[q_index]["correct"]
    correct_text = QUESTIONS[q_index]["options"][correct_index]
    data["answers"].append(selected_text == correct_text)
    data["current_q"] += 1
    await update.message.delete()

    if time.time() - data["start_time"] > 14 * 60 or data["current_q"] >= len(QUESTIONS):
        await finish_quiz(update, context)
    else:
        await send_question(update, context)

async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    score = sum(data["answers"])
    result = "✅ ناجح" if score >= 4 else "❌ راسب"

    name = data["name"]
    phone = data["phone"]
    school = data["school"]
    grade = data["grade"]
    test_id = data["test_id"]

    # الإحصائية للطالب (بدون ID)
    summary = f"📊 النتيجة: {score}/7 - {result}\n\n📋 الإحصائية:\n"
    for i, correct in enumerate(data["answers"]):
        symbol = "✅" if correct else "❌"
        correct_answer = QUESTIONS[i]["options"][QUESTIONS[i]["correct"]]
        summary += f"سؤال {i+1}: {symbol} ({correct_answer if not correct else ''})\n"

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"🏁 انتهى الاختبار!\n"
            f"🧪 اختبار رقم {test_id}\n"
            f"👤 الاسم: {name}\n"
            f"📞 الهاتف: {phone}\n"
            f"🏫 المدرسة: {school}\n"
            f"📚 الصف: {grade}\n\n"
            + summary
        )
    )

    # الإحصائية لصاحب البوت (تتضمن ID)
    full_info = (
        f"🧪 اختبار رقم {test_id}\n"
        f"👤 الاسم: {name}\n"
        f"📞 الهاتف: {phone}\n"
        f"🏫 المدرسة: {school}\n"
        f"📚 الصف: {grade}\n"
        f"🆔 معرف المستخدم: {user_id}\n\n"
        + summary
    )
    await context.bot.send_message(chat_id=ADMIN_USER_ID, text=full_info)

    # إعادة تعيين المستخدم وعرض زر البداية
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True)
    await context.bot.send_message(chat_id=user_id, text="👋 مرحبًا بك في بوت الاختبارات", reply_markup=keyboard)
    user_data[user_id] = {}

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=WEBHOOK_URL
)






