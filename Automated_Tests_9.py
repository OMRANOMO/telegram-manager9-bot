from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio
import datetime
import json
import os

# إعدادات البوت
TOKEN_QUIZ = os.getenv("TOKEN_QUIZ")
GROUP_CHAT_ID = -1001234567890  # استبدل بمعرف مجموعة الإدارة
STATUS_FILE = "test_status.json"

students = {}
selected_tests = {}

# تحميل حالة الاختبارات
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

# تعريف الأسئلة
tests = {}
for i in range(1, 33):
    key = f"الاختبار {i}"
    tests[key] = [
        {"q": f"سؤال 1 من {key}", "options": ["أ", "ب", "ج"], "answer": 0},
        {"q": f"سؤال 2 من {key}", "options": ["أ", "ب", "ج"], "answer": 1},
        {"q": f"سؤال 3 من {key}", "options": ["أ", "ب", "ج"], "answer": 2}
    ]

# عرض قائمة الاختبارات
async def show_tests_menu(chat_id, context, user_id):
    keyboard = [[f"الاختبار {i}"] for i in range(1, 33)]
    await context.bot.send_message(
        chat_id=chat_id,
        text="اختر أحد الاختبارات:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    students[user_id]["step"] = "choose_test"

# بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    students[user_id] = {"step": "choose_test", "data": {}, "answers": [], "start_time": None, "current_q": 0}
    await show_tests_menu(update.effective_chat.id, context, user_id)

# التعامل مع الرسائل
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    student = students.get(user_id)

    if not student:
        await update.message.reply_text("اضغط /start للبدء.")
        return

    step = student["step"]

    if step == "choose_test" and text in tests:
        selected_tests[user_id] = text
        status = load_status()
        if status.get(text, "on") == "off":
            await update.message.reply_text("❌ هذا الاختبار مغلق حالياً من قبل الإدارة.", reply_markup=ReplyKeyboardRemove())
            await show_tests_menu(update.effective_chat.id, context, user_id)
            return
        student["step"] = "name"
        await update.message.reply_text("أدخل اسمك الثلاثي:", reply_markup=ReplyKeyboardRemove())
        return

    if step == "name":
        student["data"]["name"] = text
        student["step"] = "phone"
        await update.message.reply_text("أدخل رقم هاتفك:")
        return
    if step == "phone":
        student["data"]["phone"] = text
        student["step"] = "school"
        await update.message.reply_text("أدخل اسم المدرسة أو المعهد:")
        return
    if step == "school":
        student["data"]["school"] = text
        student["step"] = "grade"
        await update.message.reply_text("أدخل الصف الذي تدرس فيه:")
        return
    if step == "grade":
        student["data"]["grade"] = text
        student["step"] = "ready"
        await update.message.reply_text("مدة الاختبار 14 دقيقة.\nالأسئلة تظهر بشكل متتالي!!")
        await update.message.reply_text("اضغط 'أنا جاهز للاختبار' للبدء.", reply_markup=ReplyKeyboardMarkup([["أنا جاهز للاختبار"]], one_time_keyboard=True, resize_keyboard=True))
        return

    if step == "ready" and text == "أنا جاهز للاختبار":
        test_name = selected_tests.get(user_id)
        status = load_status()
        if status.get(test_name, "on") == "off":
            await update.message.reply_text("❌ هذا الاختبار مغلق حالياً من قبل الإدارة.", reply_markup=ReplyKeyboardRemove())
            await show_tests_menu(update.effective_chat.id, context, user_id)
            return
        student["step"] = "exam"
        student["start_time"] = datetime.datetime.now()
        student["answers"] = []
        student["current_q"] = 0
        await update.message.reply_text("بَدَأ الاختبار. باقي من الوقت 14 دقيقة.")
        asyncio.create_task(send_timer(update.effective_chat.id, context, user_id))
        await send_question(update.effective_chat.id, context, user_id)
        return

    if step == "exam":
        current_q = student["current_q"]
        test_name = selected_tests.get(user_id)
        if current_q >= len(tests[test_name]):
            await finish_exam(update, context, user_id)
            return
        selected = text
        options = tests[test_name][current_q]["options"]
        if selected in options:
            student["answers"].append(options.index(selected))
            student["current_q"] += 1
            await update.message.reply_text("تم تسجيل إجابتك.", reply_markup=ReplyKeyboardRemove())
            if student["current_q"] < len(tests[test_name]):
                await send_question(update.effective_chat.id, context, user_id)
            else:
                await finish_exam(update, context, user_id)
        else:
            await update.message.reply_text("يرجى اختيار أحد الخيارات المعروضة فقط.")
        return

# إرسال سؤال
async def send_question(chat_id, context, user_id):
    student = students[user_id]
    index = student["current_q"]
    test_name = selected_tests[user_id]
    q = tests[test_name][index]
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"سؤال {index+1}: {q['q']}",
        reply_markup=ReplyKeyboardMarkup([[opt] for opt in q["options"]], one_time_keyboard=True, resize_keyboard=True)
    )

# المؤقت
async def send_timer(chat_id, context, user_id):
    for i in range(2, 15, 2):
        await asyncio.sleep(120)
        student = students.get(user_id)
        if not student or student["step"] != "exam":
            return
        remaining = 14 - i
        await context.bot.send_message(chat_id=chat_id, text=f"باقي من الوقت {remaining} دقيقة.")
        if (datetime.datetime.now() - student["start_time"]).seconds >= 840:
            await context.bot.send_message(chat_id=chat_id, text="انتهى الوقت!")
            await finish_exam(Update(update_id=0, message=Update.message), context, user_id)
            return

# إنهاء الاختبار
async def finish_exam(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    student = students[user_id]
    student["step"] = "done"
    test_name = selected_tests[user_id]
    correct = 0
    result = ""

    for i in range(len(tests[test_name])):
        correct_ans = tests[test_name][i]["answer"]
        if i < len(student["answers"]):
            ans = student["answers"][i]
            if ans == correct_ans:
                correct += 1
                result += f"✅ سؤال {i+1}\n"
            else:
                correct_text = tests[test_name][i]["options"][correct_ans]
                result += f"❌ سؤال {i+1} (الصحيح: {correct_text})\n"
        else:
            correct_text = tests[test_name][i]["options"][correct_ans]
            result += f"❌ سؤال {i+1} (الصحيح: {correct_text})\n"

    status = "ناجح 🎉" if correct >= 2 else "راسب ❌"
    summary = f"انتهى الاختبار!\nالنتيجة: {correct}/{len(tests[test_name])}\n{status}\n\nالإحصائية:\n{result}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=summary)

        # إرسال الإحصائية إلى مجموعة الإدارة
    stats_text = (
        f"📊 إحصائية جديدة:\n"
        f"👤 الاسم: {student['data']['name']}\n"
        f"📞 الهاتف: {student['data']['phone']}\n"
        f"🏫 المدرسة: {student['data']['school']}\n"
        f"📚 الصف: {student['data']['grade']}\n"
        f"📝 الاختبار: {test_name}\n"
        f"✅ النتيجة: {correct}/{len(tests[test_name])}\n"
        f"{status}\n\n"
        f"{result}"
    )
    try:
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=stats_text)
    except Exception as e:
        print(f"خطأ في إرسال الإحصائية إلى مجموعة الإدارة: {e}")

    # إعادة عرض قائمة الاختبارات
    await asyncio.sleep(1)
    students[user_id]["step"] = "choose_test"
    students[user_id]["answers"] = []
    students[user_id]["current_q"] = 0
    await show_tests_menu(update.effective_chat.id, context, user_id)

# تشغيل البوت
app = ApplicationBuilder().token(TOKEN_QUIZ).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("✅ Quiz bot is running...")
app.run_polling()

