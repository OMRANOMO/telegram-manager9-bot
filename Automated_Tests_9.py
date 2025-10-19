import os
import json
import sys
import random
import requests
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# ------------------ إعدادات ------------------
TOKEN = os.getenv("TOKEN_QUIZ") 
OWNER_ID =  758881451
PORT = int(os.getenv("PORT") or 10000)
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or f"https://telegram-Quize9-bot.onrender.com/{TOKEN}"
# رابط raw لملف test_status.json في GitHub (مثال)
GH_RAW_URL = os.getenv("GH_RAW_URL") or "https://raw.githubusercontent.com/OMRANOMO/telegram-manager9-bot/refs/heads/main/test_status.json"

# ------------------ بيانات مؤقتة للمستخدمين ------------------
user_data = {}  # شكل: { user_id: {step:, category:, unit:, test_key:, answers:[], current_q:, meta...} }

# ------------------ تعريف شجر الاختبارات (التسلسل المطلوب) ------------------
# مفاتيح الاختبارات هي رموز نصية فريدة؛ سننشئها مثل "geo_u1_t1" الخ
QUIZ_TREE = {
    "الهندسة": {
        "الوحدة الأولى": [
            ("اختبار خواص التناسب", "geo_u1_t1"),
            ("اختبار النسب المثلثية 1", "geo_u1_t2"),
            ("اختبار النسب المثلثية 2", "geo_u1_t3"),
            ("اختبار النسب المثلثية 3", "geo_u1_t4"),
            ("اختبار النسب المثلثية 4", "geo_u1_t5"),
        ],
        "الوحدة الثانية": [
            ("اختبار مبرهنة النسب الثلاث", "geo_u2_t1"),
            ("اختبار مبرهنة عكس النسب الثلاث", "geo_u2_t2"),
            ("اختبار التشابه", "geo_u2_t3"),
        ],
        "الوحدة الثالثة": [
            ("اختبار زوايا الدائرة", "geo_u3_t1"),
            ("اختبار الرباعي الدائري", "geo_u3_t2"),
            ("اختبار المضلعات المنتظمة", "geo_u3_t3"),
        ],
        "الوحدة الرابعة": [
            ("اختبار المكعب", "geo_u4_t1"),
            ("اختبار متوازي المستطيلات", "geo_u4_t2"),
            ("اختبار الاسطوانة والمخروط الدوراني", "geo_u4_t3"),
            ("اختبار الهرم", "geo_u4_t4"),
            ("اختبار الكرة والمجسم الكروي", "geo_u4_t5"),
        ],
    },
    "الجبر": {
        # قسّمت الجبر إلى 4 وحدات افتراضية مع 3 اختبارات لكل وحدة (يمكن تعديلها لاحقًا)
        "الوحدة الأولى": [
            ("اختبار المعادلات الخطية", "alg_u1_t1"),
            ("اختبار المتباينات", "alg_u1_t2"),
            ("اختبار تطبيقات المعادلات", "alg_u1_t3"),
        ],
        "الوحدة الثانية": [
            ("اختبار الدوال الخطية", "alg_u2_t1"),
            ("اختبار كثيرات الحدود 1", "alg_u2_t2"),
            ("اختبار كثيرات الحدود 2", "alg_u2_t3"),
        ],
        "الوحدة الثالثة": [
            ("اختبار تحليل كثير الحدود", "alg_u3_t1"),
            ("اختبار الانحدار والنمذجة", "alg_u3_t2"),
            ("اختبار المتسلسلات البسيطة", "alg_u3_t3"),
        ],
        "الوحدة الرابعة": [
            ("اختبار اللوغاريتمات", "alg_u4_t1"),
            ("اختبار الأسس", "alg_u4_t2"),
            ("اختبار المتجهات البسيطة", "alg_u4_t3"),
        ],
    },
}

# ------------------ توليد أسئلة dummy لكل اختبار — كل اختبار 10 أسئلة ------------------
# يمكنك استبدال هذه البنية بتحميل من ملف JSON حقيقي لاحقًا
def generate_dummy_questions():
    all_tests = {}
    for cat, units in QUIZ_TREE.items():
        for unit_name, tests in units.items():
            for title, key in tests:
                qs = []
                for i in range(1, 11):  # 10 أسئلة لكل اختبار
                    q_text = f"{title} - سؤال {i}: ما ناتج {i} + {i}؟"
                    options = [str(i + i), str(i + i + 1), str(i + i - 1)]
                    correct = 0
                    # مزج الخيارات لظهور متنوع
                    zipped = list(zip(options, range(len(options))))
                    random.shuffle(zipped)
                    shuffled_opts = [o for o, idx in zipped]
                    # تحديد مكان الإجابة الصحيحة بعد الخلط
                    correct_index = shuffled_opts.index(str(i + i))
                    qs.append({"q": q_text, "options": shuffled_opts, "correct": correct_index})
                all_tests[key] = {"title": title, "unit": unit_name, "category": cat, "questions": qs}
    return all_tests

ALL_TESTS = generate_dummy_questions()

# ------------------ جلب حالة الاختبارات من GitHub (raw) ------------------
def fetch_status_from_github():
    try:
        r = requests.get(GH_RAW_URL, timeout=5)
        if r.status_code == 200:
            return r.json()
        else:
            print("ERROR fetching status: HTTP", r.status_code, file=sys.stderr)
    except Exception as e:
        print("ERROR fetching status from GitHub:", e, file=sys.stderr)
    return {}

# ------------------ وظائف البوت الأساسية ------------------
def build_keyboard_from_labels(labels, n_cols=1):
    # labels: list of (label, payload) or strings
    buttons = []
    for lbl in labels:
        if isinstance(lbl, tuple):
            buttons.append([KeyboardButton(lbl[0])])
        else:
            buttons.append([KeyboardButton(lbl)])
    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}  # reset
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("اختبارات الهندسة"), KeyboardButton("الجبر")]],
        one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text("اختر الفئة:", reply_markup=keyboard)

async def send_test_list_for_unit(update: Update, context: ContextTypes.DEFAULT_TYPE, category, unit_name):
    user_id = update.effective_user.id
    tests = QUIZ_TREE[category][unit_name]
    labels = [(title, key) for (title, key) in tests]
    # إضافة زر رجوع
    kb = [[KeyboardButton(t[0])] for t in labels]
    kb.append([KeyboardButton("العودة إلى الوحدات"), KeyboardButton("الرئيسية")])
    markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"اختر الاختبار من {unit_name}:", reply_markup=markup)
    # علامه بالمستخدم للحالة الحالية
    user_data[user_id] = {"step": "choose_test", "category": category, "unit": unit_name}

# إرسال سؤال للمستخدم
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    if not data:
        return
    test_key = data["test_key"]
    q_index = data["current_q"]
    test_obj = ALL_TESTS.get(test_key)
    if not test_obj:
        await update.message.reply_text("❗ خطأ: الاختبار غير موجود.")
        return
    if q_index >= len(test_obj["questions"]):
        await finish_quiz(update, context)
        return
    q = test_obj["questions"][q_index]
    buttons = [[KeyboardButton(opt)] for opt in q["options"]]
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"سؤال {q_index+1}/10:\n{q['q']}", reply_markup=markup)

# إنهاء الاختبار
async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    if not data:
        return
    test_key = data["test_key"]
    test_obj = ALL_TESTS.get(test_key, {})
    answers = data.get("answers", [])
    score = sum(1 for a in answers if a)
    # رسالة الطالب
    summary_lines = []
    qs = test_obj.get("questions", [])
    for i, correct_flag in enumerate(answers):
        correct_ans = qs[i]["options"][qs[i]["correct"]]
        mark = "✅" if correct_flag else "❌"
        summary_lines.append(f"س{ i+1 }: {mark} (الإجابة الصحيحة: {correct_ans})")
    summary = "\n".join(summary_lines)
    result_text = (
        f"🏁 انتهى الاختبار: {test_obj.get('title','')}\n"
        f"📋 الوحدة: {test_obj.get('unit','')}\n"
        f"📚 الفئة: {test_obj.get('category','')}\n"
        f"🔢 النتيجة: {score}/10\n\n{summary}"
    )
    await context.bot.send_message(chat_id=user_id, text=result_text)
    # إرسال للمالك مع معرف المستخدم
    owner_text = f"🧾 طرف التسجيل:\n{result_text}\n\n🆔 معرف المستخدم: {user_id}"
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=owner_text)
    except Exception as e:
        print("ERROR sending to owner:", e, file=sys.stderr)
    # reset and show main buttons
    user_data[user_id] = {}
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True)
    await context.bot.send_message(chat_id=user_id, text="✅ تم حفظ النتيجة.", reply_markup=keyboard)

# التعامل مع الرسائل النصية الرئيسية
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id, {})

    # زر "ابدأ" أو /start
    if text == "ابدأ":
        await cmd_start(update, context)
        return

    # اختيار الفئة من البداية
    if text == "اختبارات الهندسة":
        # اعرض الوحدات الهندسية
        units = list(QUIZ_TREE["الهندسة"].keys())
        kb = [[KeyboardButton(u)] for u in units]
        kb.append([KeyboardButton("الرئيسية")])
        await update.message.reply_text("اختر الوحدة في الهندسة:", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
        user_data[user_id] = {"step": "choose_unit", "category": "الهندسة"}
        return

    if text == "الجبر":
        units = list(QUIZ_TREE["الجبر"].keys())
        kb = [[KeyboardButton(u)] for u in units]
        kb.append([KeyboardButton("الرئيسية")])
        await update.message.reply_text("اختر الوحدة في الجبر:", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
        user_data[user_id] = {"step": "choose_unit", "category": "الجبر"}
        return

    # العودة إلى الرئيسية
    if text == "الرئيسية":
        await cmd_start(update, context)
        return

    # أثناء اختيار الوحدة
    if data.get("step") == "choose_unit":
        category = data.get("category")
        if category and text in QUIZ_TREE.get(category, {}):
            # عرض اختبارات الوحدة
            await send_test_list_for_unit(update, context, category, text)
            return
        # زر العودة
        if text == "العودة إلى الوحدات":
            await cmd_start(update, context)
            return

    # اختيار اختبار من قائمة الاختبارات
    # نبحث في شجرة الاختبارات عن العنوان المطابق
    # أيضًا نتحقق من حالة الاختبار عبر GitHub قبل البدء
    # تحقق من كل اختبارات الوحدات في الشجرة
    for cat, units in QUIZ_TREE.items():
        for unit_name, tests in units.items():
            for title, key in tests:
                if text == title:
                    # تحقق من حالة الاختبار من GitHub
                    status_data = fetch_status_from_github()
                    # افتراض: مفتاح الاختبار في test_status.json يستخدم نفس key (مثلاً geo_u1_t1)
                    # إذا لم يوجد، نعتبره on
                    if status_data.get(key) == "off":
                        await update.message.reply_text("🚫 هذا الاختبار مغلق حاليًا.")
                        return
                    # تهيئة جلسة المستخدم
                    user_data[user_id] = {
                        "step": "quiz",
                        "category": cat,
                        "unit": unit_name,
                        "test_key": key,
                        "test_key_display": title,
                        "current_q": 0,
                        "answers": [],
                    }
                    # اطلب بيانات الطالب قبل بدء الاختبار
                    await update.message.reply_text("📝 قبل البدء، أدخل اسمك الثلاثي:", reply_markup=ReplyKeyboardRemove())
                    user_data[user_id]["substep"] = "await_name"
                    return

    # جمع بيانات الطالب قبل بدء الاختبار
    if data.get("step") == "quiz" and data.get("substep") == "await_name":
        data["name"] = text
        data["substep"] = "await_phone"
        await update.message.reply_text("📞 أدخل رقم هاتفك:")
        return
    if data.get("step") == "quiz" and data.get("substep") == "await_phone":
        data["phone"] = text
        data["substep"] = "started"
        # ابدأ الاختبار
        await update.message.reply_text(f"⏱️ بدء الاختبار: {data.get('test_key_display')}\nكل اختبار 10 أسئلة.", reply_markup=ReplyKeyboardRemove())
        await send_question(update, context)
        return

    # استقبال إجابات الأسئلة
    if data.get("step") == "quiz" and data.get("substep") == "started":
        test_key = data.get("test_key")
        test_obj = ALL_TESTS.get(test_key)
        if not test_obj:
            await update.message.reply_text("❗ خطأ في الاختبار.")
            return
        q_index = data["current_q"]
        if q_index >= len(test_obj["questions"]):
            await finish_quiz(update, context)
            return
        current_q = test_obj["questions"][q_index]
        if text not in current_q["options"]:
            await update.message.reply_text("❗ الرجاء اختيار إجابة من الخيارات.")
            return
        selected = current_q["options"].index(text)
        correct_index = current_q["correct"]
        data["answers"].append(selected == correct_index)
        data["current_q"] += 1
        if data["current_q"] >= 10:
            await finish_quiz(update, context)
        else:
            await send_question(update, context)
        return

    # افتراض افتراضي
    await update.message.reply_text("استخدم 'ابدأ' لبدء، أو اختر فئة اختبارات (الهندسة أو الجبر).")

# أمر /start
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

# ------------------ تسجيل المعالجات وتشغيل البوت ------------------
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start_cmd))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == "__main__":
    print("بوت الاختبارات يعمل. جلب حالات الاختبارات من:", GH_RAW_URL)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
    )
