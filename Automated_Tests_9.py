import os
import sys
import json
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

# ------------------ إعدادات (القيم التي زودتني بها) ------------------
TOKEN = os.getenv("TOKEN_QUIZ")
OWNER_ID = 758881451
PORT = int(os.getenv("PORT") or 10000)
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or f"https://telegram-Quize9-bot.onrender.com/{TOKEN}"
GH_RAW_URL = "https://raw.githubusercontent.com/OMRANOMO/telegram-manager9-bot/main/test_status.json"

# ------------------ تخزين حالة المستخدم مؤقتا ------------------
user_data = {}  # { user_id: { step, substep, category, unit, test_key, test_title, current_q, answers, name, phone, school, grade } }

# ------------------ شجرة الاختبارات ------------------
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
        "الوحدة الأولى": [
            ("اختبار طبيعة الاعداد", "alg_u1_t1"),
            ("اختبار القواسم المشتركة لعددين صحيحين", "alg_u1_t2"),
            ("اختبار الكسور المختزلة", "alg_u1_t3"),
            ("اختبار الجذر التربيعي لعدد موجب", "alg_u1_t4"),
        ],
        "الوحدة الثانية": [
            ("اختبار قوى عدد عادي", "alg_u2_t1"),
            ("اختبار النشر", "alg_u2_t2"),
            ("اختبار التحليل", "alg_u2_t3"),
        ],
        "الوحدة الثالثة": [
            ("اختبار خاصة الجداء الصفري", "alg_u3_t1"),
            ("اختبار معادلات الدرجة الأولى", "alg_u3_t2"),
            ("اختبار متراجحات الدرجة الأولى", "alg_u3_t3"),
        ],
        "الوحدة الرابعة": [
            ("اختبار معادلة مستقيم", "alg_u4_t1"),
            ("اختبار جملة معادلتين خطيتين بمجهولين", "alg_u4_t2"),
            ("اختبار حل جملة معادلتين خطيتين بيانيا", "alg_u4_t3"),
        ],
        "الوحدة الخامسة": [
            ("اختبار التابع بالصيغة الجبرية", "alg_u5_t1"),
            ("اختبار التابع بالصيغة البيانية", "alg_u5_t2"),
            ("اختبار التابع وتعريفه بالجدول", "alg_u5_t3"),
        ],
        "الوحدة السادسة": [
            ("اختبار التجربة العشوائية", "alg_u6_t1"),
            ("اختبار التجربة العشوائية المركبة", "alg_u6_t2"),
            ("اختبار الربيعات", "alg_u6_t3"),
        ],
    },
}

# ------------------ توليد أسئلة تجريبية (10 أسئلة لكل اختبار) ------------------
def generate_dummy_questions():
    all_tests = {}
    for cat, units in QUIZ_TREE.items():
        for unit_name, tests in units.items():
            for title, key in tests:
                qs = []
                for i in range(1, 11):
                    a = random.randint(1, 12)
                    b = random.randint(1, 12)
                    q_text = f"{title} - سؤال {i}: ما ناتج {a} × {b} ؟"
                    correct_ans = str(a * b)
                    wrong1 = str(a * b + random.choice([1, 2, 3, 4]))
                    wrong2 = str(max(1, a * b - random.choice([1, 2, 3, 4])))
                    opts = [correct_ans, wrong1, wrong2]
                    random.shuffle(opts)
                    correct_index = opts.index(correct_ans)
                    qs.append({"q": q_text, "options": opts, "correct": correct_index})
                all_tests[key] = {"title": title, "unit": unit_name, "category": cat, "questions": qs}
    return all_tests

ALL_TESTS = generate_dummy_questions()

# ------------------ جلب حالة الاختبارات من GitHub (raw URL) ------------------
def fetch_status_from_github():
    try:
        r = requests.get(GH_RAW_URL, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("ERROR fetching status from GitHub:", e, file=sys.stderr)
    return {}

# ------------------ أدوات لوحة المفاتيح مع أيقونات ------------------
def build_reply_keyboard(labels, add_main=False):
    kb = []
    for lbl in labels:
        # أضف أيقونات للأزرار الشائعة
        btn = lbl
        if "الهندسة" in lbl or "الجبر" in lbl:
            btn = "📚 " + lbl
        kb.append([KeyboardButton(btn)])
    if add_main:
        kb.append([KeyboardButton("🏠 الرئيسية")])
    return ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)

def small_keyboard(labels):
    kb = [[KeyboardButton(l)] for l in labels]
    return ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)

# ------------------ أسئلة وإرسالها ------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("🧮 اختبارات الهندسة"), KeyboardButton("➗ الجبر")]],
        one_time_keyboard=True, resize_keyboard=True,
    )
    await update.message.reply_text("مرحبا بك عزيزي الطالب", reply_markup=kb)

async def send_unit_list(update: Update, context: ContextTypes.DEFAULT_TYPE, category):
    units = list(QUIZ_TREE[category].keys())
    labels = [f"📘 {u}" for u in units]
    await update.message.reply_text(f"اختر الوحدة في {category}:", reply_markup=build_reply_keyboard(units, add_main=True))
    user_data[update.effective_user.id] = {"step": "choose_unit", "category": category}

async def send_test_list_for_unit(update: Update, context: ContextTypes.DEFAULT_TYPE, category, unit_name):
    tests = QUIZ_TREE[category][unit_name]
    labels = [f"📝 {t[0]}" for t in tests]
    kb = [[KeyboardButton(lbl)] for lbl in labels]
    kb.append([KeyboardButton("↩️ العودة إلى الوحدات"), KeyboardButton("🏠 الرئيسية")])
    await update.message.reply_text(f"اختر الاختبار من {unit_name}:", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    user_data[update.effective_user.id] = {"step": "choose_test", "category": category, "unit": unit_name}

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    if not data:
        return
    test_key = data.get("test_key")
    test_obj = ALL_TESTS.get(test_key)
    if not test_obj:
        await update.message.reply_text("❗ خطأ: الاختبار غير موجود.")
        return
    q_index = data.get("current_q", 0)
    if q_index >= len(test_obj["questions"]):
        await finish_quiz(update, context)
        return
    q = test_obj["questions"][q_index]
    # بناء أزرار خيارات مع أيقونات
    buttons = [[KeyboardButton(opt)] for opt in q["options"]]
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"سؤال {q_index+1}/10:\n{q['q']}", reply_markup=markup)

async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    if not data:
        return
    test_key = data.get("test_key")
    test_obj = ALL_TESTS.get(test_key, {})
    answers_flags = data.get("answers", [])
    score = sum(1 for a in answers_flags if a)
    passed = "ناجح ✅" if score >= 5 else "راسب ❌"
    qs = test_obj.get("questions", [])
    summary_lines = []
    for i in range(len(answers_flags)):
        correct_ans = qs[i]["options"][qs[i]["correct"]]
        # سجل إجابة المستخدم إن وُجدت
        user_ans = qs[i].get("selected_text", "-")
        mark = "✅" if answers_flags[i] else "❌"
        summary_lines.append(f"س{i+1}: {mark} | إجابتك: {user_ans} | الصحيحة: {correct_ans}")
    summary = "\n".join(summary_lines)
    user_message = (
        "🏁 انتهت الاسئلة بارك الله بك\n\n"
        f"🧑‍🎓 الاسم: {data.get('name','-')}\n"
        f"📞 الهاتف: {data.get('phone','-')}\n"
        f"🏫 المدرسة: {data.get('school','-')}\n"
        f"📚 الصف: {data.get('grade','-')}\n"
        f"🔢 النتيجة: {score}/10 — {passed}\n\n"
        f"تفاصيل الإجابات:\n{summary}"
    )
    await context.bot.send_message(chat_id=user_id, text=user_message)
    # إرسال للمالك مع التفاصيل
    owner_message = f"نتيجة اختبار للمستخدم: {user_id}\n\n{user_message}"
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=owner_message)
    except Exception as e:
        print("ERROR sending to owner:", e, file=sys.stderr)
    # إعادة تعيين وعرض زر ابدأ
    user_data[user_id] = {}
    await context.bot.send_message(chat_id=user_id, text="✅ تم حفظ النتيجة.", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔄 ابدأ من جديد")]], resize_keyboard=True))

# ------------------ معالج النصوص الرئيسي ------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id, {})

    # أمر البداية أو زر إعادة التشغيل
    if text in ("/start", "🔄 ابدأ من جديد", "ابدأ"):
        await cmd_start(update, context)
        return

    # اختيار الفئة (مع تطويع النص للأيقونات)
    if text in ("🧮 اختبارات الهندسة", "اختبارات الهندسة"):
        await send_unit_list(update, context, "الهندسة")
        return
    if text in ("➗ الجبر", "الجبر"):
        await send_unit_list(update, context, "الجبر")
        return

    # العودة إلى الرئيسية
    if text in ("🏠 الرئيسية", "الرئيسية"):
        await cmd_start(update, context)
        return

    # أثناء اختيار الوحدة
    if data.get("step") == "choose_unit":
        category = data.get("category")
        # نقبل النص الأصلي للوحدة أو مع أيقونة
        unit_map = {f"📘 {u}": u for u in QUIZ_TREE.get(category, {})}
        if text in QUIZ_TREE.get(category, {}):
            await send_test_list_for_unit(update, context, category, text)
            return
        if text in unit_map:
            await send_test_list_for_unit(update, context, category, unit_map[text])
            return
        if text == "↩️ العودة إلى الوحدات":
            await send_unit_list(update, context, category)
            return

    # اختيار اختبار: نقارن بعناوين الاختبارات (قد يكون النص مع أيقونة 📝)
    for cat, units in QUIZ_TREE.items():
        for unit_name, tests in units.items():
            for title, key in tests:
                alt = f"📝 {title}"
                if text == title or text == alt:
                    # تحقق من حالة الاختبار من GitHub
                    status_data = fetch_status_from_github()
                    if status_data.get(key) == "off":
                        await update.message.reply_text("🚫 هذا الاختبار مغلق حاليًا.")
                        return
                    # ابدأ جمع بيانات الطالب
                    user_data[user_id] = {
                        "step": "quiz",
                        "substep": "await_name",
                        "category": cat,
                        "unit": unit_name,
                        "test_key": key,
                        "test_title": title,
                        "current_q": 0,
                        "answers": [],
                    }
                    await update.message.reply_text("📝 أدخل اسمك الثلاثي:", reply_markup=ReplyKeyboardRemove())
                    return

    # جمع بيانات الطالب: الاسم
    if data.get("step") == "quiz" and data.get("substep") == "await_name":
        data["name"] = text
        data["substep"] = "await_phone"
        await update.message.reply_text("📞 أدخل رقم هاتفك:")
        return

    # الهاتف
    if data.get("step") == "quiz" and data.get("substep") == "await_phone":
        data["phone"] = text
        data["substep"] = "await_school"
        await update.message.reply_text("🏫 أدخل اسم المدرسة:")
        return

    # المدرسة
    if data.get("step") == "quiz" and data.get("substep") == "await_school":
        data["school"] = text
        data["substep"] = "await_grade"
        await update.message.reply_text("📘 أدخل الصف الذي تدرسه:")
        return

    # الصف
    if data.get("step") == "quiz" and data.get("substep") == "await_grade":
        data["grade"] = text
        data["substep"] = "confirm_ready"
        kb = ReplyKeyboardMarkup([[KeyboardButton("✅ جاهز")], [KeyboardButton("⏳ ليس الآن")]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("هذا الاختبار مكون من 10 أسئلة. هل أنت جاهز؟", reply_markup=kb)
        return

    # بعد التأكيد: عند الضغط على "جاهز" نعرض الدعاء ثم ننتظر زر "أمين"
    if data.get("step") == "quiz" and data.get("substep") == "confirm_ready":
        if text in ("✅ جاهز", "جاهز"):
            await update.message.reply_text("اللهم لا سهل الا ما جعلته سهلا")
            data["substep"] = "await_amin"
            kb = ReplyKeyboardMarkup([[KeyboardButton("أمين 🤲")]], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("اضغط 'أمين' للبدء", reply_markup=kb)
            return
        else:
            await update.message.reply_text("حسناً، عند الاستعداد أعد التشغيل عبر '🔄 ابدأ من جديد'.", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔄 ابدأ من جديد")]], resize_keyboard=True))
            user_data[user_id] = {}
            return

    # معالجة ضغط زر "أمين" لبدء الاختبار فعليًا
    if data.get("step") == "quiz" and data.get("substep") == "await_amin":
        if text.startswith("أمين"):
            data["substep"] = "started"
            data.setdefault("current_q", 0)
            data.setdefault("answers", [])
            await update.message.reply_text("✅ بارك الله، يبدأ الاختبار الآن:", reply_markup=ReplyKeyboardRemove())
            await send_question(update, context)
            return
        else:
            kb = ReplyKeyboardMarkup([[KeyboardButton("أمين 🤲")], [KeyboardButton("⏳ ليس الآن")]], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("الرجاء الضغط على زر 'أمين' للبدء أو اختر '⏳ ليس الآن'.", reply_markup=kb)
            return

    # استقبال إجابات الأسئلة أثناء الاختبار
    if data.get("step") == "quiz" and data.get("substep") == "started":
        test_key = data.get("test_key")
        test_obj = ALL_TESTS.get(test_key)
        if not test_obj:
            await update.message.reply_text("❗ خطأ في الاختبار.")
            return
        q_index = data.get("current_q", 0)
        if q_index >= len(test_obj["questions"]):
            await finish_quiz(update, context)
            return
        current_q = test_obj["questions"][q_index]
        if text not in current_q["options"]:
            await update.message.reply_text("❗ الرجاء اختيار إجابة من الخيارات.")
            return
        selected = current_q["options"].index(text)
        # حفظ النص المختار داخل السؤال لعرضه لاحقًا
        current_q["selected_text"] = current_q["options"][selected]
        current_q["selected_index"] = selected
        data["answers"].append(selected == current_q["correct"])
        data["current_q"] = q_index + 1
        if data["current_q"] >= 10:
            await finish_quiz(update, context)
        else:
            await send_question(update, context)
        return

    # رسالة افتراضية إرشادية
    await update.message.reply_text("استخدم 'ابدأ' لبدء أو اختر فئة الاختبارات (🧮 اختبارات الهندسة أو ➗ الجبر).")

# ------------------ تسجيل وتشغيل البوت ------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

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
