import os
import json
import sys
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# ----- إعدادات -----
TOKEN = os.getenv("TOKEN_QUIZ") 
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or f"https://telegram-Quize9-bot.onrender.com/{TOKEN}"
OWNER_ID = 758881451

# مسار ملف الحالة (استخدم مسار مطلق لتفادي اختلاف المجلدات)
STATUS_FILE = os.path.abspath(os.getenv("STATUS_FILE") or "test_status.json")

# بيانات مؤقتة في الذاكرة لكل مستخدم
user_data = {}

# ----- إنشاء بيانات اختبارات افتراضية -----
def generate_dummy_tests(num_tests: int = 32, questions_per_test: int = 7):
    all_tests = {}
    for t in range(1, num_tests + 1):
        qs = []
        for q in range(1, questions_per_test + 1):
            qs.append({
                "q": f"سؤال {q} من الاختبار {t}؟",
                "options": [f"خيار A{q}", f"خيار B{q}", f"خيار C{q}"],
                "correct": 0
            })
        all_tests[str(t)] = qs
    return all_tests

ALL_TESTS = generate_dummy_tests(32, 7)

# ----- أدوات قراءة / كتابة ملف الحالة -----
def read_status_file():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print("ERROR reading status file:", e, file=sys.stderr)
        return {}

def write_status_file(data: dict):
    # مكتوبة هنا لمرجعية؛ يستخدمها عادة بوت الإدارة
    tmp = STATUS_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATUS_FILE)
    except Exception as e:
        print("ERROR writing status file:", e, file=sys.stderr)

# ----- إنشاء التطبيق -----
app = Application.builder().token(TOKEN).build()

# ----- إرسال السؤال التالي -----
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    if not data:
        return
    q_index = data["current_q"]
    questions = ALL_TESTS.get(data["test_id"])
    if not questions or q_index >= len(questions):
        await finish_quiz(update, context)
        return
    q = questions[q_index]
    buttons = [[KeyboardButton(opt)] for opt in q["options"]]
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"❓ سؤال {q_index + 1}:\n{q['q']}", reply_markup=markup)

# ----- معالجة إجابة المستخدم -----
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id)
    if not data:
        return
    q_index = data["current_q"]
    questions = ALL_TESTS.get(data["test_id"])
    if not questions or q_index >= len(questions):
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

# ----- إنهاء الاختبار وإرسال الإحصائية -----
async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    if not data:
        return
    questions = ALL_TESTS.get(data["test_id"], [])
    score = sum(data["answers"])
    passing_threshold = (len(questions) // 2) + 1
    result = "✅ ناجح" if score >= passing_threshold else "❌ راسب"
    name = data.get("name", "غير معروف")
    phone = data.get("phone", "غير معروف")
    school = data.get("school", "غير معروف")
    grade = data.get("grade", "غير معروف")
    test_id = data["test_id"]

    summary_lines = []
    for i, correct in enumerate(data["answers"]):
        symbol = "✅" if correct else "❌"
        correct_answer = questions[i]["options"][questions[i]["correct"]]
        summary_lines.append(f"سؤال {i+1}: {symbol} (الإجابة الصحيحة: {correct_answer})")

    summary = "📊 النتيجة: {}/{} - {}\n\n📋 الإحصائية:\n{}".format(
        score, len(questions), result, "\n".join(summary_lines)
    )

    # إرسال للطالب
    try:
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
    except Exception as e:
        print("ERROR sending result to user:", e, file=sys.stderr)

    # إرسال لصاحب البوت مع معرف المستخدم (ID)
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
    except Exception as e:
        # طباعة الأخطاء في السجل لتصحيح السبب (مثلاً: OWNER_ID غير صحيح أو المالك لم يبدأ المحادثة)
        print("ERROR sending result to owner:", e, file=sys.stderr)
        try:
            await context.bot.send_message(chat_id=user_id, text="✅ انتهى الاختبار ولكن لم أتمكن من إرسال النتيجة للمدير.")
        except Exception:
            pass

    # إعادة تعيين المستخدم وإظهار زر "ابدأ"
    user_data[user_id] = {}
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True)
    try:
        await context.bot.send_message(chat_id=user_id, text="👋 يمكنك البدء متى شئت", reply_markup=keyboard)
    except Exception as e:
        print("ERROR sending restart button:", e, file=sys.stderr)

# ----- المعالج الرئيسي للرسائل النصية -----
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

        # قراءة حالة الاختبار في الزمن الحقيقي من الملف المشترك
        status_data = read_status_file()
        if status_data.get(test_id) == "off":
            await update.message.reply_text("🚫 هذا الاختبار مغلق حاليًا.")
            return

        # التحقق من وجود الاختبار
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

    # خطوات تعبئة البيانات الشخصية وبدء الاختبار
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

    # رسالة افتراضية
    await update.message.reply_text("استخدم 'ابدأ' لعرض قائمة الاختبارات أو اكتب 'الاختبار X' مباشرة.")

# ----- أمر /start -----
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True)
    await update.message.reply_text("👋 أهلاً بك في بوت الاختبارات", reply_markup=keyboard)

# ----- تسجيل المعالجات -----
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# ----- تشغيل Webhook -----
if __name__ == "__main__":
    print("STATUS_FILE path:", STATUS_FILE)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
    )
