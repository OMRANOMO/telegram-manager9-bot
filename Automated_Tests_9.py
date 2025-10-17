import os
import json
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# إعداد التوكن والمنفذ
TOKEN = os.getenv("TOKEN_QUIZ")
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = f"https://telegram-Quize9-bot.onrender.com/{TOKEN}"  # غيّر هذا إلى رابط بوتك على Render
OWNER_ID = 123456789  # ← ضع هنا معرفك الشخصي في تيليغرام

# بيانات المستخدمين
user_data = {}

# قاعدة بيانات الأسئلة لكل اختبار
ALL_TESTS = {
    "1": [
        {"q": "ما ناتج 7 × 8؟", "options": ["54", "56", "58"], "correct": 1},
        {"q": "كم عدد أضلاع المثلث؟", "options": ["3", "4", "5"], "correct": 0},
        {"q": "ما هو لون السماء؟", "options": ["أزرق", "أخضر", "أحمر"], "correct": 0},
        {"q": "ما هو عاصمة سوريا؟", "options": ["دمشق", "حلب", "حمص"], "correct": 0},
        {"q": "كم عدد أيام الأسبوع؟", "options": ["5", "6", "7"], "correct": 2},
        {"q": "ما هو الجذر التربيعي لـ 81؟", "options": ["9", "8", "7"], "correct": 0},
        {"q": "ما هو ناتج 12 ÷ 3؟", "options": ["4", "3", "6"], "correct": 0},
    ],
    # يمكنك إضافة اختبارات أخرى بنفس البنية حتى "32"
}

# إنشاء التطبيق
app = Application.builder().token(TOKEN).build()

# إرسال السؤال التالي
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    q_index = data["current_q"]
    questions = ALL_TESTS[data["test_id"]]
    q = questions[q_index]

    buttons = [[KeyboardButton(opt)] for opt in q["options"]]
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"❓ سؤال {q_index + 1}:\n{q['q']}", reply_markup=markup)

# التعامل مع الإجابات
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data[user_id]
    q_index = data["current_q"]
    questions = ALL_TESTS[data["test_id"]]

    if text not in questions[q_index]["options"]:
        await update.message.reply_text("❗ الرجاء اختيار إجابة من الخيارات.")
        return

    selected = questions[q_index]["options"].index(text)
    correct = questions[q_index]["correct"]
    data["answers"].append(selected == correct)
    data["current_q"] += 1

    if data["current_q"] >= len(questions):
        await finish_quiz(update, context)
    else:
        await send_question(update, context)

# إنهاء الاختبار
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
    questions = ALL_TESTS[test_id]

    # الإحصائية للطالب
    summary = f"📊 النتيجة: {score}/{len(questions)} - {result}\n\n📋 الإحصائية:\n"
    for i, correct in enumerate(data["answers"]):
        symbol = "✅" if correct else "❌"
        correct_answer = questions[i]["options"][questions[i]["correct"]]
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

    # الإحصائية لصاحب البوت
    full_info = (
        f"🧪 اختبار رقم {test_id}\n"
        f"👤 الاسم: {name}\n"
        f"📞 الهاتف: {phone}\n"
        f"🏫 المدرسة: {school}\n"
        f"📚 الصف: {grade}\n"
        f"🆔 معرف المستخدم: {user_id}\n\n"
        + summary
    )
    await context.bot.send_message(chat_id=OWNER_ID, text=full_info)

    # إعادة التشغيل
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True)
    await context.bot.send_message(chat_id=user_id, text="👋 مرحبًا بك في بوت الاختبارات", reply_markup=keyboard)
    user_data[user_id] = {}

# التعامل مع الرسائل
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
        test_id = str(int(text.split(" ")[1]))

        # تحقق من حالة الاختبار
        try:
            with open("test_status.json", "r") as f:
                status_data = json.load(f)
            if status_data.get(test_id) == "off":
                await update.message.reply_text("🚫 هذا الاختبار مغلق حاليًا.")
                return
        except FileNotFoundError:
            pass

        if test_id not in ALL_TESTS:
            await update.message.reply_text("❗ هذا الاختبار غير موجود.")
            return

        user_data[user_id] = {
            "step": "name",
            "test_id": test_id,
            "answers": [],
            "start_time": None,
            "current_q": 0,
        }
        await update.message.reply_text(f"📝 اختبار رقم {test_id}\nأدخل اسمك الثلاثي:")
        return

    if data:
        step = data.get("step")
        if step == "name":
            data["name"] = text
            data["step"] = "phone"
            await update.message.reply_text("📞 أدخل رقم هاتفك:")
        elif step == "phone":
            data["phone"] = text
            data["step"] = "school"
            await update.message.reply_text("🏫 أدخل اسم المدرسة:")
        elif step == "school":
            data["school"] = text
            data["step"] = "grade"
            await update.message.reply_text("📚 أدخل الصف الدراسي:")
        elif step == "grade":
            data["grade"] = text
            data["step"] = "quiz"
            await send_question(update, context)
        elif step == "quiz":
            await handle_answer(update, context)

# تسجيل المعالجات
app.add_handler(MessageHandler(filters.TEXT, handle_text))

# تشغيل البوت باستخدام Webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=WEBHOOK_URL
)
