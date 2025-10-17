import os
import json
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# إعدادات أساسية
TOKEN = os.getenv("TOKEN_QUIZ") or "ضع_التوكن_هنا"
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or f"https://telegram-Quize9-bot.onrender.com/{TOKEN}"
OWNER_ID = int(os.getenv("OWNER_ID") or 123456789)  # ضع معرفك هنا إذا رغبت

# ملف الحالة (shared with manager bot)
STATUS_FILE = "test_status.json"

# بيانات المستخدم مؤقتة في الذاكرة
user_data = {}

# توليد نموذج اختبارات 32 اختباr كل اختبار 7 أسئلة افتراضية (يمكن استبدالها بملف JSON حقيقي)
def generate_dummy_tests(num_tests: int = 32, questions_per_test: int = 7):
    all_tests = {}
    for t in range(1, num_tests + 1):
        qs = []
        for q in range(1, questions_per_test + 1):
            qs.append({
                "q": f"سؤال {q} من الاختبار {t}؟",
                "options": [f"خيار A{q}", f"خيار B{q}", f"خيار C{q}"],
                "correct": 0  # اجابة صحيحة افتراضية هي الخيار الأول
            })
        all_tests[str(t)] = qs
    return all_tests

ALL_TESTS = generate_dummy_tests(32, 7)

# مساعدة قراءة/كتابة ملف الحالة بشكل آمن
def read_status_file():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def write_status_file(data: dict):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# إنشاء التطبيق
app = Application.builder().token(TOKEN).build()

# إرسال السؤال التالي لمستخدم معين
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    if not data:
        return
    q_index = data["current_q"]
    questions = ALL_TESTS[data["test_id"]]
    # حماية من أخطاء الفهرسة
    if q_index < 0 or q_index >= len(questions):
        await finish_quiz(update, context)
        return

    q = questions[q_index]
    buttons = [[KeyboardButton(opt)] for opt in q["options"]]
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"❓ سؤال {q_index + 1}:\n{q['q']}", reply_markup=markup)

# معالجة إجابة المستخدم على سؤال
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id)
    if not data:
        return

    q_index = data["current_q"]
    questions = ALL_TESTS[data["test_id"]]
    # تأكد أن المؤشر صالح
    if q_index < 0 or q_index >= len(questions):
        await finish_quiz(update, context)
        return

    current_q = questions[q_index]
    if text not in current_q["options"]:
        await update.message.reply_text("❗ الرجاء اختيار إجابة من الخيارات المعروضة.")
        return

    selected = current_q["options"].index(text)
    correct = current_q["correct"]
    data["answers"].append(selected == correct)
    data["current_q"] += 1

    if data["current_q"] >= len(questions):
        await finish_quiz(update, context)
    else:
        await send_question(update, context)

# إنهاء الاختبار وإرسال الإحصائيات
async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    if not data:
        return

    questions = ALL_TESTS[data["test_id"]]
    score = sum(data["answers"])
    result = "✅ ناجح" if score >= (len(questions) // 2 + 1) else "❌ راسب"

    name = data.get("name", "غير معروف")
    phone = data.get("phone", "غير معروف")
    school = data.get("school", "غير معروف")
    grade = data.get("grade", "غير معروف")
    test_id = data["test_id"]

    summary = f"📊 النتيجة: {score}/{len(questions)} - {result}\n\n📋 الإحصائية:\n"
    for i, correct in enumerate(data["answers"]):
        symbol = "✅" if correct else "❌"
        correct_answer = questions[i]["options"][questions[i]["correct"]]
        summary += f"سؤال {i+1}: {symbol} ({correct_answer if not correct else ''})\n"

    # إرسال للطالب (بدون ID)
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

    # إرسال لمالك البوت مع معرف المستخدم
    full_info = (
        f"🧪 اختبار رقم {test_id}\n"
        f"👤 الاسم: {name}\n"
        f"📞 الهاتف: {phone}\n"
        f"🏫 المدرسة: {school}\n"
        f"📚 الصف: {grade}\n"
        f"🆔 معرف المستخدم: {user_id}\n\n"
        + summary
    )
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=full_info)
    except Exception:
        pass

    # إعادة تعيين حالة المستخدم وإظهار زر ابدأ
    user_data[user_id] = {}
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True)
    await context.bot.send_message(chat_id=user_id, text="👋 يمكنك البدء متى شئت", reply_markup=keyboard)

# دالة معالجة الرسائل النصية الرئيسية
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id)

    # زر البداية
    if text == "ابدأ":
        buttons = [[KeyboardButton(f"الاختبار {i}")] for i in range(1, 33)]
        markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("📚 اختر الاختبار:", reply_markup=markup)
        return

    # اختيار الاختبار
    if text.startswith("الاختبار "):
        try:
            test_id = str(int(text.split(" ")[1]))
        except Exception:
            await update.message.reply_text("❗ صيغة اختيار الاختبار غير صحيحة.")
            return

        # قراءة حالة الاختبار في الزمن الحقيقي
        status_data = read_status_file()
        if status_data.get(test_id) == "off":
            await update.message.reply_text("🚫 هذا الاختبار مغلق حاليًا.")
            return

        # وجود الاختبار
        if test_id not in ALL_TESTS:
            await update.message.reply_text("❗ هذا الاختبار غير موجود.")
            return

        # تهيئة بيانات المستخدم لبدء الاختبار
        user_data[user_id] = {
            "step": "name",
            "test_id": test_id,
            "answers": [],
            "current_q": 0,
        }
        await update.message.reply_text(f"📝 اختبار رقم {test_id}\nأدخل اسمك الثلاثي:")
        return

    # إجراءات الحقول أثناء ملأ بيانات الاختبار
    if data:
        step = data.get("step")
        if step == "name":
            data["name"] = text
            data["step"] = "phone"
            await update.message.reply_text("📞 أدخل رقم هاتفك:")
            return
        if step == "phone":
            data["phone"] = text
            data["step"] = "school"
            await update.message.reply_text("🏫 أدخل اسم المدرسة:")
            return
        if step == "school":
            data["school"] = text
            data["step"] = "grade"
            await update.message.reply_text("📚 أدخل الصف الدراسي:")
            return
        if step == "grade":
            data["grade"] = text
            data["step"] = "quiz"
            await send_question(update, context)
            return
        if step == "quiz":
            await handle_answer(update, context)
            return

    # رسائل غير مفهومة
    await update.message.reply_text("استخدم 'ابدأ' لعرض قائمة الاختبارات أو اكتب الاختبار المطلوب.")

# أمر /start لتشغيل لوحة البداية
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True)
    await update.message.reply_text("👋 أهلاً بك في بوت الاختبارات", reply_markup=keyboard)

# تسجيل المعالجات
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# تشغيل البوت باستخدام Webhook
if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
    )
