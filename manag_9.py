import os
import json
import base64
import requests
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ------------------ إعدادات ------------------
TOKEN = os.getenv("TOKEN_MANAGER") 
PORT = int(os.getenv("PORT") or 10000)
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or f"https://telegram-manager9-bot.onrender.com/{TOKEN}"

# GitHub config
GH_TOKEN = os.getenv("GH_TOKEN")  # توكن GitHub (يجب إضافته كمتغير بيئة)
GH_REPO = os.getenv("GH_REPO") or "OMRANOMO/telegram-manager9-bot"  # مثال: "OMRANOMO/telegram-manager9-bot"
GH_BRANCH = os.getenv("GH_BRANCH") or "main"
GH_FILE_PATH = os.getenv("GH_FILE_PATH") or "test_status.json"

# Raw URL (بديل للقراءة دون مصادقة إذا المستودع عام)
GH_RAW_URL = os.getenv("GH_RAW_URL") or f"https://raw.githubusercontent.com/OMRANOMO/telegram-manager9-bot/refs/heads/main/test_status.json"

# ------------------ شجرة الاختبارات (مطابقة لبوت الاختبارات) ------------------
# تُستخدم هذه الشجرة لبناء لوحة التحكم وأزرار التبديل
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

# ------------------ وظائف مساعدة للتعامل مع GitHub ------------------
def fetch_status_from_github():
    """
    حاول أولاً قراءة الملف من raw URL (أفضل للأداء إذا المستودع عام).
    إذا فشل أو كان المستودع خاصاً، استخدم GitHub API مع GH_TOKEN لاسترجاع المحتوى.
    ترجع dict خريطة الحالات أو {} عند الفشل.
    """
    # محاولة قراءة raw (سريعة وسهلة للمستودع العام)
    try:
        r = requests.get(GH_RAW_URL, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    # إذا لم تنجح raw أو المستودع خاص، استخدم API مع Authorization (يتطلب GH_TOKEN)
    if not GH_TOKEN:
        print("WARN: GH_TOKEN not provided and raw fetch failed; returning empty status", file=sys.stderr)
        return {}

    try:
        api_url = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE_PATH}?ref={GH_BRANCH}"
        headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(api_url, headers=headers, timeout=6)
        if r.status_code == 200:
            j = r.json()
            content_b64 = j.get("content", "")
            if content_b64:
                decoded = base64.b64decode(content_b64).decode("utf-8")
                return json.loads(decoded)
    except Exception as e:
        print("ERROR fetching status via GitHub API:", e, file=sys.stderr)

    return {}

def upload_status_to_github(status_dict):
    """
    يحدّث الملف في GitHub عبر API (يتطلب GH_TOKEN).
    تُرسل النسخة الجديدة فقط عندما نضغط زر تبديل.
    """
    if not GH_TOKEN:
        print("ERROR: GH_TOKEN not set; cannot upload to GitHub", file=sys.stderr)
        return False

    try:
        api_url = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE_PATH}"
        headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

        # احصل على SHA الحالي إن وُجد
        r_get = requests.get(api_url + f"?ref={GH_BRANCH}", headers=headers, timeout=6)
        sha = None
        if r_get.status_code == 200:
            sha = r_get.json().get("sha")

        content_str = json.dumps(status_dict, ensure_ascii=False, indent=2)
        content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

        data = {
            "message": "تحديث حالة الاختبارات من بوت الإدارة",
            "content": content_b64,
            "branch": GH_BRANCH,
        }
        if sha:
            data["sha"] = sha

        r_put = requests.put(api_url, headers=headers, json=data, timeout=10)
        if r_put.status_code in (200, 201):
            return True
        else:
            print("ERROR uploading to GitHub:", r_put.status_code, r_put.text, file=sys.stderr)
    except Exception as e:
        print("ERROR uploading to GitHub exception:", e, file=sys.stderr)
    return False

# ------------------ بناء لوحة التحكم ديناميكياً ------------------
def build_dashboard_markup(status_map):
    """
    تبني InlineKeyboardMarkup شجري حسب QUIZ_TREE وحالة كل اختبار من status_map.
    زر كل اختبار يظهر مع تسمية الاسم وزر جانبي لعرض on/off والتبديل.
    سنعرض صفين: [اختبار][زر تبديل]
    """
    keyboard = []
    for category, units in QUIZ_TREE.items():
        # إظهار اسم الفئة كفاصل (غير قابل للضغط)
        keyboard.append([InlineKeyboardButton(f"--- {category} ---", callback_data="noop")])
        for unit_name, tests in units.items():
            # سطر يوضح اسم الوحدة
            keyboard.append([InlineKeyboardButton(f"{unit_name}", callback_data="noop")])
            for title, key in tests:
                status = status_map.get(key, "on")
                toggle_label = "🔴 off" if status == "off" else "🟢 on"
                # ال callback لزر التبديل يحمل التعليمة toggle_key:<key>
                keyboard.append([
                    InlineKeyboardButton(title, callback_data="noop"),
                    InlineKeyboardButton(toggle_label, callback_data=f"toggle:{key}")
                ])
        # فراغ بعد الفئة
        keyboard.append([InlineKeyboardButton(" ", callback_data="noop")])
    # زر لتحديث اللوحة يدوياً
    keyboard.append([InlineKeyboardButton("تحديث", callback_data="refresh")])
    return InlineKeyboardMarkup(keyboard)

# ------------------ Handlers ------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # عند /start نبني اللوحة بناءً على الحالة الحالية من GitHub (لا نغيّر الملف هنا)
    status_map = fetch_status_from_github()
    markup = build_dashboard_markup(status_map)
    await update.message.reply_text("لوحة تحكم الاختبارات (اضغط على زر الحالة لتبديلها):", reply_markup=markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "noop":
        return

    if data == "refresh":
        status_map = fetch_status_from_github()
        await query.edit_message_reply_markup(reply_markup=build_dashboard_markup(status_map))
        return

    if data.startswith("toggle:"):
        key = data.split(":", 1)[1]
        # اقرأ الحالة الحالية من GitHub
        status_map = fetch_status_from_github()
        current = status_map.get(key, "on")
        new = "off" if current == "on" else "on"
        status_map[key] = new
        # ارفع التغيير إلى GitHub
        ok = upload_status_to_github(status_map)
        if ok:
            # حدث لوحة التحكم بعد النجاح
            await query.edit_message_reply_markup(reply_markup=build_dashboard_markup(status_map))
            await query.reply_text(f"تم تحديث حالة {key} → {new}")
        else:
         await query.message.reply_text("فشل تحديث الحالة على GitHub. تحقق من إعدادات GH_TOKEN و GH_REPO.")  

# ------------------ تسجيل المعالجات وتشغيل البوت ------------------
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(CallbackQueryHandler(handle_callback))

if __name__ == "__main__":
    print("بوت الإدارة يعمل. سيقرأ ويكتب إلى:", GH_REPO, GH_FILE_PATH)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
    )



