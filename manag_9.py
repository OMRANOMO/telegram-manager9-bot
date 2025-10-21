import os, json, base64, requests, sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TOKEN_MANAGER") or "ضع_توكن_الإدارة"
PORT = int(os.getenv("PORT") or 10000)
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or f"https://your-manager-service.onrender.com/{TOKEN}"

GH_TOKEN = os.getenv("GH_TOKEN")
GH_REPO = os.getenv("GH_REPO") or "OMRANOMO/telegram-manager9-bot"
GH_BRANCH = os.getenv("GH_BRANCH") or "main"
GH_FILE_PATH = os.getenv("GH_FILE_PATH") or "test_status.json"
GH_RAW_URL = f"https://raw.githubusercontent.com/{GH_REPO}/{GH_BRANCH}/{GH_FILE_PATH}"

QUIZ_KEYS = [
    "geo_u1_t1","geo_u1_t2","geo_u1_t3","geo_u1_t4","geo_u1_t5",
    "geo_u2_t1","geo_u2_t2","geo_u2_t3",
    "geo_u3_t1","geo_u3_t2","geo_u3_t3",
    "geo_u4_t1","geo_u4_t2","geo_u4_t3","geo_u4_t4","geo_u4_t5",
    "alg_u1_t1","alg_u1_t2","alg_u1_t3","alg_u1_t4",
    "alg_u2_t1","alg_u2_t2","alg_u2_t3",
    "alg_u3_t1","alg_u3_t2","alg_u3_t3",
    "alg_u4_t1","alg_u4_t2","alg_u4_t3",
    "alg_u5_t1","alg_u5_t2","alg_u5_t3",
    "alg_u6_t1","alg_u6_t2","alg_u6_t3"
]

def fetch_status():
    try:
        r = requests.get(GH_RAW_URL, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("Fetch error:", e, file=sys.stderr)
    return {}

def upload_status(status_dict):
    if not GH_TOKEN: return False
    try:
        api_url = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE_PATH}"
        headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r_get = requests.get(api_url+f"?ref={GH_BRANCH}", headers=headers)
        sha = r_get.json().get("sha") if r_get.status_code==200 else None
        content_str = json.dumps(status_dict, ensure_ascii=False, indent=2)
        content_b64 = base64.b64encode(content_str.encode()).decode()
        data = {"message":"update test status","content":content_b64,"branch":GH_BRANCH}
        if sha: data["sha"]=sha
        r_put = requests.put(api_url, headers=headers, json=data)
        return r_put.status_code in (200,201)
    except Exception as e:
        print("Upload error:", e, file=sys.stderr)
    return False

def build_markup(status_map):
    kb=[]
    for key in QUIZ_KEYS:
        status=status_map.get(key,"on")
        label=f"{key} → {'🟢on' if status=='on' else '🔴off'}"
        kb.append([InlineKeyboardButton(label,callback_data=f"toggle:{key}")])
    kb.append([InlineKeyboardButton("🔄 تحديث",callback_data="refresh")])
    return InlineKeyboardMarkup(kb)

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    status=fetch_status()
    await update.message.reply_text("لوحة التحكم:",reply_markup=build_markup(status))

async def handle_cb(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    data=q.data
    if data=="refresh":
        status=fetch_status()
        await q.edit_message_reply_markup(reply_markup=build_markup(status))
        return
    if data.startswith("toggle:"):
        key=data.split(":")[1]
        status=fetch_status()
        cur=status.get(key,"on")
        status[key]="off" if cur=="on" else "on"
        if upload_status(status):
            await q.edit_message_reply_markup(reply_markup=build_markup(status))
            await q.message.reply_text(f"✅ {key} أصبح {status[key]}")
        else:
            await q.message.reply_text("❌ فشل تحديث GitHub")

app=Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start",start))
app.add_handler(CallbackQueryHandler(handle_cb))

if __name__=="__main__":
    app.run_webhook(listen="0.0.0.0",port=PORT,url_path=TOKEN,webhook_url=WEBHOOK_URL)
