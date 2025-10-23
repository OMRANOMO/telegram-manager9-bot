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
PORT =  10000 
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or f"https://telegram-Quize9-bot.onrender.com/{TOKEN}"
GH_RAW_URL =  "https://raw.githubusercontent.com/OMRANOMO/telegram-manager9-bot/main/test_status.json"

# ------------------ بيانات مؤقتة للمستخدمين ------------------
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

# ------------------ توليد أسئلة تجريبية لكل اختبار (10 أسئلة) ------------------
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

# ------------------ جلب حالة الاختبارات من GitHub ------------------
def fetch_status_from_github():
    try:
        r = requests.get(GH_RAW_URL, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("ERROR fetching status from GitHub:", e, file=sys.stderr)
    return {}

# ------------------ أدوات لوحة المفاتيح ------------------
def build_reply_keyboard(labels, add_main=False):
    kb = [[KeyboardButton(lbl)] for lbl in labels]
    if add_main:
        kb.append([KeyboardButton("الرئيسية")])
    return ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)

# ------------------ وظائف الاختبارات ------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    # رسالة ترحيب عند بداية البوت
    kb = ReplyKeyboardMarkup([[KeyboardButton("اختبارات الهندسة"), KeyboardButton("الجبر")]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("مرحبا بك عزيزي الطالب", reply_markup=kb)

async def send_unit_list(update: Update, context: ContextTypes.DEFAULT_TYPE, category):
    units = list(QUIZ_TREE[category].keys())
    await update.message.reply_text(f"اختر الوحدة في {category}:", reply_markup=build_reply_keyboard(units, add_main=True))
    user_data[update.effective_user.id] = {"step": "choose_unit", "category": category}

async def send_test_list_for_unit(update: Update, context: ContextTypes.DEFAULT_TYPE, category, unit_name):
    tests = QUIZ_TREE[category][unit_name]
    labels = [t[0] for t in tests]
    kb = [[KeyboardButton(lbl)] for lbl in labels]
    kb.append([KeyboardButton("العودة إلى الوحدات"), KeyboardButton("الرئيسية")])
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
    answers = data.get("answers", [])
    score = sum(1 for a in answers if a)
    passed = "ناجح" if score >= 5 else "راسب"
    # تجهيز ملخص مع التصحيح
    qs = test_obj.get("questions", [])
    summary_lines = []
    for i, flag in enumerate(answers):
        correct_ans = qs[i]["options"][qs[i]["correct"]]
        user_ans = qs[i]["options"][qs[i]["selected_index"]] if "selected_index" in qs[i] and len(answers)>i else None
        mark = "✅" if flag else "❌"
        summary_lines.append(f"س{i+1}: {mark} | الإجابة الصحيحة: {correct_ans}")
    summary = "\n".join(summary_lines)
    # نص للمستخدم يتضمن الاسم والرقم واسم المدرسة والصف والنتيجة
    user_message = (
        f"🏁 انتهت الاسئلة بارك الله بك\n\n"
        f"🧑‍🎓 الاسم: {data.get('name','-')}\n"
        f"📞 الهاتف: {data.get('phone','-')}\n"
        f"🏫 المدرسة: {data.get('school','-')}\n"
        f"📚 الصف: {data.get('grade','-')}\n"
        f"🔢 النتيجة: {score}/10 ({passed})\n\n"
        f"تفاصيل الإجابات:\n{summary}"
    )
    await context.bot.send_message(chat_id=user_id, text=user_message)
    # إرسال للمالك مع التفاصيل
    owner_message = f"نتيجة اختبار\nالمستخدم: {user_id}\n{user_message}"
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=owner_message)
    except Exception as e:
        print("ERROR sending to owner:", e, file=sys.stderr)
    # إعادة تعيين وعرض زر ابدأ
    user_data[user_id] = {}
    await context.bot.send_message(chat_id=user_id, text="✅ تم حفظ النتيجة.", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True))

# ------------------ معالجة الرسائل ------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id, {})

    # زر البداية أو /start
    if text in ("ابدأ", "/start"):
        await cmd_start_step(update, context)
        return

    # اختيار الفئة
    if text == "اختبارات الهندسة":
        await send_unit_list(update, context, "الهندسة")
        return
    if text == "الجبر":
        await send_unit_list(update, context, "الجبر")
        return

    # العودة إلى الرئيسية
    if text == "الرئيسية":
        await cmd_start_step(update, context)
        return

    # أثناء اختيار الوحدة
    if data.get("step") == "choose_unit":
        category = data.get("category")
        if category and text in QUIZ_TREE.get(category, {}):
            await send_test_list_for_unit(update, context, category, text)
            return
        if text == "العودة إلى الوحدات":
            await send_unit_list(update, context, category)
            return

    # اختيار اختبار
    for cat, units in QUIZ_TREE.items():
        for unit_name, tests in units.items():
            for title, key in tests:
                if text == title:
                    # تحقق من حالة الاختبار من GitHub
                    status_data = fetch_status_from_github()
                    if status_data.get(key) == "off":
                        await update.message.reply_text("🚫 هذا الاختبار مغلق حاليًا.")
                        return
                    # ابدأ جمع بيانات الطالب: الاسم الثلاثي ثم الهاتف ثم المدرسة ثم الصف ثم تأكيد
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

    # جمع بيانات الطالب: الاسم، الهاتف، المدرسة، الصف، ثم التأكيد
    if data.get("step") == "quiz" and data.get("substep") == "await_name":
        data["name"] = text
        data["substep"] = "await_phone"
        await update.message.reply_text("📞 أدخل رقم هاتفك:")
        return
    if data.get("step") == "quiz" and data.get("substep") == "await_phone":
        data["phone"] = text
        data["substep"] = "await_school"
        await update.message.reply_text("🏫 أدخل اسم المدرسة:")
        return
    if data.get("step") == "quiz" and data.get("substep") == "await_school":
        data["school"] = text
        data["substep"] = "await_grade"
        await update.message.reply_text("📘 أدخل الصف الذي تدرسه:")
        return
    if data.get("step") == "quiz" and data.get("substep") == "await_grade":
        data["grade"] = text
        data["substep"] = "confirm_ready"
        # أخبره أن الاختبار مكون من 10 أسئلة واسأل هل هو جاهز
        kb = ReplyKeyboardMarkup([[KeyboardButton("جاهز")], [KeyboardButton("ليس الآن")]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("هذا الاختبار مكون من 10 أسئلة. هل أنت جاهز؟", reply_markup=kb)
        return

   # تأكيد البدء: عند الضغط على "جاهز" نعرض الدعاء ثم ننتظر زر "أمين"
    if data.get("step") == "quiz" and data.get("substep") == "confirm_ready":
      if text == "جاهز":
          # عرض الدعاء
          await update.message.reply_text("اللهم لا سهل الا ما جعلته سهلا")
          # اضبط الحالة لانتظار زر "أمين"
          data["substep"] = "await_amin"
          # أرسل زر واحد "أمين" للمستخدم
          kb = ReplyKeyboardMarkup([[KeyboardButton("أمين")]], one_time_keyboard=True, resize_keyboard=True)
          await update.message.reply_text("اضغط 'أمين' للبدء", reply_markup=kb)
         return
        else:
            # إذا اختار "ليس الآن" أعِده إلى الرئيسية
            await update.message.reply_text("حسناً، عند الاستعداد أعد تشغيل الاختبار عبر 'ابدأ'.", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("ابدأ")]], resize_keyboard=True))
            user_data[user_id] = {}
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
        # سجل اختيار المستخدم داخل السؤال لمزيد من الدقة في التقرير
        current_q["selected_index"] = selected
        data["answers"].append(selected == current_q["correct"])
        data["current_q"] = q_index + 1
        if data["current_q"] >= 10:
            await finish_quiz(update, context)
        else:
            await send_question(update, context)
        return

    # رسالة افتراضية إرشادية
    await update.message.reply_text("استخدم 'ابدأ' لبدء أو اختر فئة الاختبارات (الهندسة أو الجبر).")

# تخزين وظيفة /start منفصلة لتظهر رسالة الترحيب
async def cmd_start_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

# ------------------ تسجيل المعالجات وتشغيل البوت ------------------
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", cmd_start_step))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == "__main__":
    print("بوت الاختبارات يعمل. جلب حالات الاختبارات من:", GH_RAW_URL)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
    )

