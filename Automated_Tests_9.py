import os, json, asyncio, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
WEBHOOK_URL = f"https://telegram-Quize9-bot.onrender.com/{TOKEN}"  # غيّر اسم الخدمة
GROUP_CHAT_ID = -100758881451

QUESTIONS = [
    {"q": "ما عاصمة فرنسا؟", "options": ["باريس", "برلين", "مدريد"], "correct": 0},
    {"q": "كم عدد الكواكب؟", "options": ["7", "8", "9"], "correct": 1},
    {"q": "من مؤسس مايكروسوفت؟", "options": ["ستيف جوبز", "بيل غيتس", "إيلون ماسك"], "correct": 1},
    {"q": "ما هو أكبر محيط؟", "options": ["الأطلسي", "الهندي", "الهادئ"], "correct": 2},
    {"q": "كم عدد أيام السنة؟", "options": ["365", "366", "364"], "correct": 0},
    {"q": "ما هو الغاز الأساسي في الهواء؟", "options": ["أوكسجين", "نيتروجين", "هيدروجين"], "correct": 1},
    {"q": "ما هو أسرع حيوان؟", "options": ["الفهد", "الأسد", "الذئب"], "correct": 0},
]

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("ابدأ", callback_data="start_form")]]
    await update.message.reply_text("👋 مرحبًا بك في بوت الاختبارات", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data[user_id] = {"step": "name", "answers": [], "start_time": None}
    await query.message.reply_text("📝 أدخل اسمك الثلاثي:")

async def collect_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id)

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
        keyboard = [[InlineKeyboardButton("أنا جاهز للاختبار", callback_data="start_quiz")]]
        await update.message.reply_text("⏱ مدة الاختبار 14 دقيقة\n❗ الأسئلة تظهر بشكل متتالي", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = user_data[user_id]
    data["start_time"] = time.time()
    data["current_q"] = 0
    await query.message.reply_text("✅ بدأ الاختبار\n⏳ باقي من الوقت 14 دقيقة")
    asyncio.create_task(send_timer(update, context))
    await send_question(update, context)

async def send_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    for i in range(2, 15, 2):
        await asyncio.sleep(120)
        if user_data.get(user_id, {}).get("current_q", 7) < 7:
            await context.bot.send_message(chat_id=user_id, text=f"⏳ باقي من الوقت {14 - i} دقيقة")

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    q_index = data["current_q"]

    if q_index >= len(QUESTIONS):
        await finish_quiz(update, context)
        return

    q = QUESTIONS[q_index]
    buttons = [[InlineKeyboardButton(opt, callback_data=f"answer_{i}")] for i, opt in enumerate(q["options"])]
    await context.bot.send_message(chat_id=user_id, text=f"❓ السؤال {q_index + 1}: {q['q']}", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = user_data[user_id]
    q_index = data["current_q"]
    selected = int(query.data.split("_")[1])
    correct = QUESTIONS[q_index]["correct"]
    data["answers"].append(selected == correct)
    data["current_q"] += 1

    if time.time() - data["start_time"] > 14 * 60 or data["current_q"] >= len(QUESTIONS):
        await finish_quiz(update, context)
    else:
        await send_question(update, context)

async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    score = sum(data["answers"])
    result = "✅ ناجح" if score >= 4 else "❌ راسب"
    summary = f"📊 النتيجة: {score}/7 - {result}\n\n📋 الإحصائية:\n"
    for i, correct in enumerate(data["answers"]):
        symbol = "✅" if correct else "❌"
        correct_answer = QUESTIONS[i]["options"][QUESTIONS[i]["correct"]]
        summary += f"سؤال {i+1}: {symbol} ({correct_answer if not correct else ''})\n"

    await context.bot.send_message(chat_id=user_id, text="🏁 انتهى الاختبار!\n" + summary)
    full_info = f"👤 {data['name']}\n📞 {data['phone']}\n🏫 {data['school']}\n📚 {data['grade']}\n\n" + summary
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=full_info)

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback, pattern="start_form"))
app.add_handler(CallbackQueryHandler(start_quiz, pattern="start_quiz"))
app.add_handler(CallbackQueryHandler(handle_answer, pattern="answer_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_info))

app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=WEBHOOK_URL)
