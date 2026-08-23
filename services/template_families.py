"""Research-backed, standalone Python Telegram bot template families.

Each factory emits a complete one-file bot.  The products share hardened
infrastructure (SQLite, bounds, admin claim, audit trail) while their labels,
fields and workflows are tailored to a concrete use case.  Keeping the engine
in factories makes 100+ templates reviewable instead of maintaining thousands
of copy-pasted lines that silently drift apart.
"""

from __future__ import annotations


def _item(name, description, category, code, badge="Advanced", after_deploy=""):
    return {
        "name": name,
        "description": description,
        "category": category,
        "language": "python",
        "framework": "python-telegram-bot",
        "badge": badge,
        "env_fields": [{
            "key": "ADMIN_CLAIM_CODE", "type": "generated",
            "label": "Secure admin connection", "required": True,
            "help": "Generated automatically. The Go to bot button connects the first administrator securely.",
        }],
        "after_deploy": after_deploy or "Open Go to bot and press Start to connect the administrator. Use /panel for controls.",
        "code": code.strip() + "\n",
    }


def _workflow_code(title: str, fields: tuple[str, ...], states: tuple[str, ...], db_name: str) -> str:
    """Multi-step intake + queue + status history + CSV + broadcast."""
    return f'''# requirements: python-telegram-bot==21.4
import asyncio, csv, io, json, os, sqlite3
from datetime import datetime, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Forbidden, RetryAfter
from telegram.ext import ApplicationBuilder, ApplicationHandlerStop, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, TypeHandler, filters

TITLE = {title!r}
FIELDS = {fields!r}
STATES = {states!r}
CLAIM_CODE = os.getenv("ADMIN_CLAIM_CODE", "")
DB = sqlite3.connect({db_name!r}, check_same_thread=False)
DB.execute("PRAGMA journal_mode=WAL")
DB.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
DB.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, name TEXT, username TEXT, banned INTEGER DEFAULT 0, created_at TEXT)")
DB.execute("CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,data TEXT,status TEXT,admin_note TEXT DEFAULT '',created_at TEXT,updated_at TEXT)")
DB.execute("CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT,record_id INTEGER,actor_id INTEGER,action TEXT,created_at TEXT)")
DB.commit()
ASKING = 1

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def admin_id():
    row=DB.execute("SELECT value FROM settings WHERE key='admin_id'").fetchone(); return int(row[0]) if row else 0
def is_admin(uid): return uid == admin_id()
def clean(value, limit=500): return " ".join(str(value or "").split())[:limit]
def audit(record_id, actor, action):
    DB.execute("INSERT INTO history(record_id,actor_id,action,created_at) VALUES(?,?,?,?)",(record_id,actor,clean(action,250),now()))
def menu(admin=False):
    rows=[[InlineKeyboardButton("Create new",callback_data="new"),InlineKeyboardButton("My requests",callback_data="mine")]]
    if admin: rows.append([InlineKeyboardButton("Admin queue",callback_data="queue"),InlineKeyboardButton("Statistics",callback_data="stats")])
    return InlineKeyboardMarkup(rows)

async def access_guard(update, context):
    user=update.effective_user
    if not user or is_admin(user.id): return
    row=DB.execute("SELECT banned FROM users WHERE user_id=?",(user.id,)).fetchone()
    if row and row[0]:
        if update.effective_message: await update.effective_message.reply_text("Access is currently restricted.")
        elif update.callback_query: await update.callback_query.answer("Access is restricted.",show_alert=True)
        raise ApplicationHandlerStop

async def claim_start(update, context):
    uid=update.effective_user.id
    if not admin_id() and context.args and context.args[0] == "claim_" + CLAIM_CODE:
        DB.execute("INSERT INTO settings(key,value) VALUES('admin_id',?)",(str(uid),)); DB.commit()
        await update.message.reply_text(f"Administrator connected to {{TITLE}}. Use /panel."); return
    user=update.effective_user
    DB.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?,?)",(uid,clean(user.full_name,100),clean(user.username,50),0,now())); DB.commit()
    banned=DB.execute("SELECT banned FROM users WHERE user_id=?",(uid,)).fetchone()
    if banned and banned[0]: await update.message.reply_text("Access is currently restricted."); return
    await update.message.reply_text(f"{{TITLE}}\\nCreate and track requests without leaving Telegram.",reply_markup=menu(is_admin(uid)))

async def begin(update, context):
    if update.callback_query: await update.callback_query.answer(); target=update.callback_query.message
    else: target=update.message
    context.user_data["draft"]={{}}; context.user_data["field_index"]=0
    await target.reply_text(f"1/{{len(FIELDS)}} — Send {{FIELDS[0]}}. Use /cancel anytime.")
    return ASKING

async def collect(update, context):
    value=clean(update.message.text)
    if not value: await update.message.reply_text("Please send a non-empty answer."); return ASKING
    i=context.user_data.get("field_index",0); draft=context.user_data.setdefault("draft",{{}}); draft[FIELDS[i]]=value; i+=1
    if i < len(FIELDS):
        context.user_data["field_index"]=i; await update.message.reply_text(f"{{i+1}}/{{len(FIELDS)}} — Send {{FIELDS[i]}}."); return ASKING
    uid=update.effective_user.id; ts=now()
    cur=DB.execute("INSERT INTO records(user_id,data,status,created_at,updated_at) VALUES(?,?,?,?,?)",(uid,json.dumps(draft,ensure_ascii=False),STATES[0],ts,ts)); audit(cur.lastrowid,uid,"created"); DB.commit()
    context.user_data.pop("draft",None); context.user_data.pop("field_index",None)
    await update.message.reply_text(f"Saved as #{{cur.lastrowid}} · {{STATES[0]}}",reply_markup=menu(is_admin(uid))); return ConversationHandler.END

async def cancel_form(update, context):
    context.user_data.pop("draft",None); context.user_data.pop("field_index",None); await update.message.reply_text("Draft discarded."); return ConversationHandler.END

def record_text(row):
    data=json.loads(row[2]); details="\\n".join(f"• {{k}}: {{v}}" for k,v in data.items())
    note=f"\\nAdmin note: {{row[4]}}" if row[4] else ""
    return f"#{{row[0]}} · {{row[3]}}\\n{{details}}{{note}}\\nUpdated {{row[6]}}"

async def mine(update, context):
    if update.callback_query: await update.callback_query.answer(); target=update.callback_query.message
    else: target=update.message
    rows=DB.execute("SELECT id,user_id,data,status,admin_note,created_at,updated_at FROM records WHERE user_id=? ORDER BY id DESC LIMIT 10",(update.effective_user.id,)).fetchall()
    await target.reply_text("\\n\\n".join(record_text(r) for r in rows) if rows else "No requests yet.")

async def view(update, context):
    if not context.args or not context.args[0].isdigit(): await update.message.reply_text("Use /view ID"); return
    row=DB.execute("SELECT id,user_id,data,status,admin_note,created_at,updated_at FROM records WHERE id=?",(int(context.args[0]),)).fetchone()
    if not row or (row[1]!=update.effective_user.id and not is_admin(update.effective_user.id)): await update.message.reply_text("Request not found."); return
    await update.message.reply_text(record_text(row))

async def cancel_record(update, context):
    if not context.args or not context.args[0].isdigit(): await update.message.reply_text("Use /cancelrequest ID"); return
    rid=int(context.args[0]); row=DB.execute("SELECT user_id,status FROM records WHERE id=?",(rid,)).fetchone()
    if not row or row[0]!=update.effective_user.id or row[1]!=STATES[0]: await update.message.reply_text("Only your pending request can be cancelled."); return
    DB.execute("UPDATE records SET status='Cancelled',updated_at=? WHERE id=?",(now(),rid)); audit(rid,update.effective_user.id,"cancelled"); DB.commit(); await update.message.reply_text("Cancelled.")

async def queue(update, context):
    if update.callback_query: await update.callback_query.answer(); target=update.callback_query.message
    else: target=update.message
    if not is_admin(update.effective_user.id): return
    rows=DB.execute("SELECT id,user_id,data,status,admin_note,created_at,updated_at FROM records WHERE status NOT IN ('Completed','Rejected','Cancelled','Closed') ORDER BY id LIMIT 15").fetchall()
    await target.reply_text("\\n\\n".join(record_text(r) for r in rows) if rows else "Queue is clear.")

async def set_status(update, context):
    if not is_admin(update.effective_user.id): return
    if len(context.args)<2 or not context.args[0].isdigit(): await update.message.reply_text("Use /status ID STATE\\nAllowed: "+", ".join(STATES)); return
    rid=int(context.args[0]); requested=clean(" ".join(context.args[1:]),50)
    state=next((s for s in STATES if s.lower()==requested.lower()),None)
    row=DB.execute("SELECT user_id FROM records WHERE id=?",(rid,)).fetchone()
    if not row or not state: await update.message.reply_text("Unknown request or state."); return
    DB.execute("UPDATE records SET status=?,updated_at=? WHERE id=?",(state,now(),rid)); audit(rid,update.effective_user.id,"status: "+state); DB.commit()
    await update.message.reply_text("Status updated.")
    try: await context.bot.send_message(row[0],f"{{TITLE}} request #{{rid}} is now {{state}}.")
    except Exception: pass

async def note(update, context):
    if not is_admin(update.effective_user.id) or len(context.args)<2 or not context.args[0].isdigit(): return
    rid=int(context.args[0]); text=clean(" ".join(context.args[1:]))
    DB.execute("UPDATE records SET admin_note=?,updated_at=? WHERE id=?",(text,now(),rid)); audit(rid,update.effective_user.id,"note updated"); DB.commit(); await update.message.reply_text("Note saved.")

async def panel(update, context):
    if not is_admin(update.effective_user.id): return
    counts=DB.execute("SELECT status,COUNT(*) FROM records GROUP BY status").fetchall(); users=DB.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await update.message.reply_text(f"{{TITLE}} admin\\nUsers: {{users}}\\n"+"\\n".join(f"{{s}}: {{n}}" for s,n in counts)+"\\n\\n/queue /status /note /export /broadcast /ban",reply_markup=menu(True))

async def export_csv(update, context):
    if not is_admin(update.effective_user.id): return
    out=io.StringIO(); writer=csv.writer(out); writer.writerow(["id","user_id","status",*FIELDS,"admin_note","created_at","updated_at"])
    for rid,uid,data,status,note,created,updated in DB.execute("SELECT id,user_id,data,status,admin_note,created_at,updated_at ORDER BY id"):
        values=json.loads(data); writer.writerow([rid,uid,status,*[values.get(f,"") for f in FIELDS],note,created,updated])
    payload=io.BytesIO(out.getvalue().encode("utf-8-sig")); payload.name="export.csv"; await update.message.reply_document(payload)

async def broadcast(update, context):
    if not is_admin(update.effective_user.id) or not context.args: return
    text=clean(" ".join(context.args),3500); sent=0
    for (uid,) in DB.execute("SELECT user_id FROM users WHERE banned=0"):
        try:
            await context.bot.send_message(uid,text); sent+=1; await asyncio.sleep(0.04)
        except RetryAfter as exc: await asyncio.sleep(float(exc.retry_after)+0.1)
        except Forbidden: DB.execute("UPDATE users SET banned=1 WHERE user_id=?",(uid,)); DB.commit()
        except Exception: pass
    await update.message.reply_text(f"Delivered to {{sent}} users.")

async def ban(update, context):
    if not is_admin(update.effective_user.id) or not context.args or not context.args[0].isdigit(): return
    uid=int(context.args[0]); value=0 if update.message.text.startswith("/unban") else 1
    DB.execute("UPDATE users SET banned=? WHERE user_id=?",(value,uid)); DB.commit(); await update.message.reply_text("User access updated.")

async def callback(update, context):
    action=update.callback_query.data
    if action=="mine": await mine(update,context)
    elif action=="queue": await queue(update,context)
    elif action=="stats": await panel(update,context)

app=ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(TypeHandler(Update,access_guard),group=-1)
app.add_handler(ConversationHandler(entry_points=[CommandHandler("new",begin),CallbackQueryHandler(begin,pattern="^new$")],states={{ASKING:[MessageHandler(filters.TEXT & ~filters.COMMAND,collect)]}},fallbacks=[CommandHandler("cancel",cancel_form)]))
app.add_handler(CommandHandler("start",claim_start)); app.add_handler(CommandHandler("mine",mine)); app.add_handler(CommandHandler("view",view)); app.add_handler(CommandHandler("cancelrequest",cancel_record)); app.add_handler(CommandHandler("queue",queue)); app.add_handler(CommandHandler("status",set_status)); app.add_handler(CommandHandler("note",note)); app.add_handler(CommandHandler("panel",panel)); app.add_handler(CommandHandler("export",export_csv)); app.add_handler(CommandHandler("broadcast",broadcast)); app.add_handler(CommandHandler(["ban","unban"],ban)); app.add_handler(CallbackQueryHandler(callback)); app.run_polling(allowed_updates=Update.ALL_TYPES)
'''


def _tracker_code(title: str, unit: str, db_name: str) -> str:
    """Per-user ledger with tags, date ranges, summaries, CSV and admin controls."""
    return f'''# requirements: python-telegram-bot==21.4
import asyncio, csv, io, os, sqlite3
from datetime import datetime, timezone
from telegram import Update
from telegram.error import Forbidden, RetryAfter
from telegram.ext import ApplicationBuilder, ApplicationHandlerStop, CommandHandler, ContextTypes, TypeHandler
TITLE={title!r}; UNIT={unit!r}; CLAIM_CODE=os.getenv("ADMIN_CLAIM_CODE","")
DB=sqlite3.connect({db_name!r},check_same_thread=False); DB.execute("PRAGMA journal_mode=WAL")
DB.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)"); DB.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,banned INTEGER DEFAULT 0)"); DB.execute("CREATE TABLE IF NOT EXISTS entries(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,value REAL,label TEXT,done INTEGER DEFAULT 0,created_at TEXT)"); DB.commit()
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def admin_id():
 r=DB.execute("SELECT value FROM settings WHERE key='admin_id'").fetchone(); return int(r[0]) if r else 0
def admin(uid): return uid==admin_id()
def clean(v,n=200): return " ".join(str(v or "").split())[:n]
async def access_guard(u:Update,c:ContextTypes.DEFAULT_TYPE):
 user=u.effective_user
 if not user or admin(user.id):return
 row=DB.execute("SELECT banned FROM users WHERE user_id=?",(user.id,)).fetchone()
 if row and row[0]:
  if u.effective_message:await u.effective_message.reply_text("Access is restricted.")
  raise ApplicationHandlerStop
async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
 uid=u.effective_user.id
 if not admin_id() and c.args and c.args[0]=="claim_"+CLAIM_CODE: DB.execute("INSERT INTO settings VALUES('admin_id',?)",(str(uid),));DB.commit();await u.message.reply_text("Administrator connected. Use /panel.");return
 DB.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(uid,));DB.commit(); banned=DB.execute("SELECT banned FROM users WHERE user_id=?",(uid,)).fetchone()[0]
 if banned: await u.message.reply_text("Access is restricted.");return
 await u.message.reply_text(f"{{TITLE}}\\n/add VALUE LABEL — add entry\\n/list — recent entries\\n/done ID — mark complete\\n/delete ID — remove\\n/summary — totals\\n/export — your CSV")
async def add(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if len(c.args)<2:
  await u.message.reply_text("Use /add VALUE LABEL");return
 try: value=float(c.args[0])
 except ValueError: await u.message.reply_text("VALUE must be a number.");return
 if abs(value)>1_000_000_000: await u.message.reply_text("Value is outside the allowed range.");return
 label=clean(" ".join(c.args[1:])); cur=DB.execute("INSERT INTO entries(user_id,value,label,created_at) VALUES(?,?,?,?)",(u.effective_user.id,value,label,now()));DB.commit();await u.message.reply_text(f"Saved #{{cur.lastrowid}}.")
async def listing(u:Update,c:ContextTypes.DEFAULT_TYPE):
 rows=DB.execute("SELECT id,value,label,done,created_at FROM entries WHERE user_id=? ORDER BY id DESC LIMIT 20",(u.effective_user.id,)).fetchall();await u.message.reply_text("\\n".join(f"{{'✓' if d else '•'}} #{{i}} {{v:g}} {{UNIT}} — {{label}} · {{ts[:10]}}" for i,v,label,d,ts in rows) if rows else "No entries yet.")
async def done(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not c.args or not c.args[0].isdigit(): return
 cur=DB.execute("UPDATE entries SET done=1 WHERE id=? AND user_id=?",(int(c.args[0]),u.effective_user.id));DB.commit();await u.message.reply_text("Completed." if cur.rowcount else "Entry not found.")
async def delete(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not c.args or not c.args[0].isdigit(): return
 cur=DB.execute("DELETE FROM entries WHERE id=? AND user_id=?",(int(c.args[0]),u.effective_user.id));DB.commit();await u.message.reply_text("Deleted." if cur.rowcount else "Entry not found.")
async def summary(u:Update,c:ContextTypes.DEFAULT_TYPE):
 row=DB.execute("SELECT COUNT(*),COALESCE(SUM(value),0),COALESCE(AVG(value),0),SUM(done) FROM entries WHERE user_id=?",(u.effective_user.id,)).fetchone(); top=DB.execute("SELECT label,SUM(value) total FROM entries WHERE user_id=? GROUP BY label ORDER BY ABS(total) DESC LIMIT 5",(u.effective_user.id,)).fetchall();await u.message.reply_text(f"Entries: {{row[0]}}\\nTotal: {{row[1]:g}} {{UNIT}}\\nAverage: {{row[2]:g}} {{UNIT}}\\nCompleted: {{row[3] or 0}}\\n\\nTop labels:\\n"+"\\n".join(f"{{x}}: {{v:g}}" for x,v in top))
async def export(u:Update,c:ContextTypes.DEFAULT_TYPE):
 target=u.effective_user.id
 if c.args and admin(target) and c.args[0].isdigit(): target=int(c.args[0])
 out=io.StringIO();w=csv.writer(out);w.writerow(["id","value","unit","label","done","created_at"]);w.writerows((i,v,UNIT,l,d,t) for i,v,l,d,t in DB.execute("SELECT id,value,label,done,created_at FROM entries WHERE user_id=? ORDER BY id",(target,)));f=io.BytesIO(out.getvalue().encode("utf-8-sig"));f.name="tracker.csv";await u.message.reply_document(f)
async def panel(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not admin(u.effective_user.id): return
 users=DB.execute("SELECT COUNT(*) FROM users").fetchone()[0];entries=DB.execute("SELECT COUNT(*) FROM entries").fetchone()[0];await u.message.reply_text(f"{{TITLE}} admin\\nUsers: {{users}}\\nEntries: {{entries}}\\n/broadcast TEXT /ban USER_ID /unban USER_ID")
async def broadcast(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not admin(u.effective_user.id) or not c.args:return
 sent=0
 for (uid,) in DB.execute("SELECT user_id FROM users WHERE banned=0"):
  try:
   await c.bot.send_message(uid,clean(" ".join(c.args),3500));sent+=1;await asyncio.sleep(0.04)
  except RetryAfter as exc:await asyncio.sleep(float(exc.retry_after)+0.1)
  except Forbidden:DB.execute("UPDATE users SET banned=1 WHERE user_id=?",(uid,));DB.commit()
  except Exception:pass
 await u.message.reply_text(f"Delivered to {{sent}} users.")
async def ban(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not admin(u.effective_user.id) or not c.args or not c.args[0].isdigit():return
 DB.execute("UPDATE users SET banned=? WHERE user_id=?",(0 if u.message.text.startswith('/unban') else 1,int(c.args[0])));DB.commit();await u.message.reply_text("Access updated.")
app=ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build();app.add_handler(TypeHandler(Update,access_guard),group=-1)
for command,handler in [("start",start),("add",add),("list",listing),("done",done),("delete",delete),("summary",summary),("export",export),("panel",panel),("broadcast",broadcast)]:app.add_handler(CommandHandler(command,handler))
app.add_handler(CommandHandler(["ban","unban"],ban));app.run_polling()
'''


def _catalog_code(title: str, item_name: str, db_name: str) -> str:
    """Admin-managed searchable catalog with pagination, favorites and analytics."""
    return f'''# requirements: python-telegram-bot==21.4
import os, sqlite3
from datetime import datetime, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes
TITLE={title!r}; ITEM={item_name!r}; CLAIM_CODE=os.getenv("ADMIN_CLAIM_CODE","")
DB=sqlite3.connect({db_name!r},check_same_thread=False);DB.execute("PRAGMA journal_mode=WAL");DB.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)");DB.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,banned INTEGER DEFAULT 0)");DB.execute("CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,body TEXT,category TEXT,active INTEGER DEFAULT 1,views INTEGER DEFAULT 0,created_at TEXT)");DB.execute("CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER,item_id INTEGER,PRIMARY KEY(user_id,item_id))");DB.commit()
def admin_id():
 r=DB.execute("SELECT value FROM settings WHERE key='admin_id'").fetchone();return int(r[0]) if r else 0
def admin(uid):return uid==admin_id()
def clean(v,n=1000):return " ".join(str(v or "").split())[:n]
def card(row):return f"#{{row[0]}} · {{row[1]}}\\n{{row[2]}}\\nCategory: {{row[3]}} · Views: {{row[4]}}"
async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
 uid=u.effective_user.id
 if not admin_id() and c.args and c.args[0]=="claim_"+CLAIM_CODE:DB.execute("INSERT INTO settings VALUES('admin_id',?)",(str(uid),));DB.commit();await u.message.reply_text("Administrator connected. Use /panel.");return
 DB.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(uid,));DB.commit();row=DB.execute("SELECT banned FROM users WHERE user_id=?",(uid,)).fetchone()
 if row and row[0]:await u.message.reply_text("Access is restricted.");return
 await u.message.reply_text(f"{{TITLE}}\\n/browse — latest\\n/search WORDS — find\\n/categories — explore\\n/favorites — saved {{ITEM}}s")
async def browse(u:Update,c:ContextTypes.DEFAULT_TYPE):
 page=max(0,int(c.args[0])-1) if c.args and c.args[0].isdigit() else 0;rows=DB.execute("SELECT id,title,body,category,views FROM items WHERE active=1 ORDER BY id DESC LIMIT 6 OFFSET ?",(page*6,)).fetchall();buttons=[[InlineKeyboardButton(f"Open #{{r[0]}}",callback_data=f"open:{{r[0]}}"),InlineKeyboardButton("☆ Save",callback_data=f"fav:{{r[0]}}") ] for r in rows];await u.message.reply_text("\\n\\n".join(f"#{{r[0]}} {{r[1]}} · {{r[3]}}" for r in rows) if rows else f"No {{ITEM}}s published yet.",reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
async def search(u:Update,c:ContextTypes.DEFAULT_TYPE):
 q="%"+clean(" ".join(c.args),100)+"%";rows=DB.execute("SELECT id,title,body,category,views FROM items WHERE active=1 AND (title LIKE ? OR body LIKE ? OR category LIKE ?) ORDER BY views DESC LIMIT 10",(q,q,q)).fetchall();await u.message.reply_text("\\n\\n".join(card(r) for r in rows) if rows else "No matches.")
async def categories(u:Update,c:ContextTypes.DEFAULT_TYPE):
 rows=DB.execute("SELECT category,COUNT(*) FROM items WHERE active=1 GROUP BY category ORDER BY category").fetchall();await u.message.reply_text("Categories\\n"+"\\n".join(f"• {{x}} ({{n}})" for x,n in rows))
async def favorites(u:Update,c:ContextTypes.DEFAULT_TYPE):
 rows=DB.execute("SELECT i.id,i.title,i.body,i.category,i.views FROM items i JOIN favorites f ON f.item_id=i.id WHERE f.user_id=? AND i.active=1 ORDER BY i.id DESC",(u.effective_user.id,)).fetchall();await u.message.reply_text("\\n\\n".join(card(r) for r in rows) if rows else "No saved items.")
async def callback(u:Update,c:ContextTypes.DEFAULT_TYPE):
 q=u.callback_query;await q.answer();kind,raw=q.data.split(":",1);iid=int(raw)
 if kind=="fav":DB.execute("INSERT OR IGNORE INTO favorites VALUES(?,?)",(u.effective_user.id,iid));DB.commit();await q.answer("Saved",show_alert=True);return
 row=DB.execute("SELECT id,title,body,category,views FROM items WHERE id=? AND active=1",(iid,)).fetchone()
 if row:DB.execute("UPDATE items SET views=views+1 WHERE id=?",(iid,));DB.commit();await q.message.reply_text(card(row))
async def add(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not admin(u.effective_user.id):return
 parts=" ".join(c.args).split("|",2)
 if len(parts)!=3:await u.message.reply_text("Use /add Title | Category | Details");return
 cur=DB.execute("INSERT INTO items(title,category,body,created_at) VALUES(?,?,?,?)",(clean(parts[0],150),clean(parts[1],80),clean(parts[2],3000),datetime.now(timezone.utc).isoformat()));DB.commit();await u.message.reply_text(f"Published #{{cur.lastrowid}}.")
async def edit(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not admin(u.effective_user.id) or len(c.args)<2 or not c.args[0].isdigit():return
 DB.execute("UPDATE items SET body=? WHERE id=?",(clean(" ".join(c.args[1:]),3000),int(c.args[0])));DB.commit();await u.message.reply_text("Updated.")
async def toggle(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not admin(u.effective_user.id) or not c.args or not c.args[0].isdigit():return
 DB.execute("UPDATE items SET active=1-active WHERE id=?",(int(c.args[0]),));DB.commit();await u.message.reply_text("Visibility changed.")
async def panel(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not admin(u.effective_user.id):return
 items,views=DB.execute("SELECT COUNT(*),COALESCE(SUM(views),0) FROM items").fetchone();users=DB.execute("SELECT COUNT(*) FROM users").fetchone()[0];await u.message.reply_text(f"{{TITLE}} admin\\n{{ITEM}}s: {{items}}\\nViews: {{views}}\\nUsers: {{users}}\\n/add /edit /toggle")
app=ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
for command,handler in [("start",start),("browse",browse),("search",search),("categories",categories),("favorites",favorites),("add",add),("edit",edit),("toggle",toggle),("panel",panel)]:app.add_handler(CommandHandler(command,handler))
app.add_handler(CallbackQueryHandler(callback,pattern="^(open|fav):"));app.run_polling()
'''


def _group_code(title: str, mode: str, db_name: str) -> str:
    """Group-admin moderation engine: configurable filters, warns and audit log."""
    return f'''# requirements: python-telegram-bot==21.4
import os, sqlite3, time
from collections import defaultdict, deque
from telegram import ChatPermissions, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
TITLE={title!r}; MODE={mode!r}; DB=sqlite3.connect({db_name!r},check_same_thread=False);DB.execute("CREATE TABLE IF NOT EXISTS config(chat_id INTEGER,key TEXT,value TEXT,PRIMARY KEY(chat_id,key))");DB.execute("CREATE TABLE IF NOT EXISTS warns(chat_id INTEGER,user_id INTEGER,count INTEGER DEFAULT 0,PRIMARY KEY(chat_id,user_id))");DB.execute("CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id INTEGER,actor_id INTEGER,target_id INTEGER,action TEXT,created_at INTEGER)");DB.commit();WINDOW=defaultdict(lambda:deque(maxlen=12))
async def is_admin(u,c):
 if u.effective_chat.type=="private":return False
 member=await c.bot.get_chat_member(u.effective_chat.id,u.effective_user.id);return member.status in ("administrator","creator")
def cfg(chat,key,default=""):
 r=DB.execute("SELECT value FROM config WHERE chat_id=? AND key=?",(chat,key)).fetchone();return r[0] if r else default
def log(chat,actor,target,action):DB.execute("INSERT INTO audit(chat_id,actor_id,target_id,action,created_at) VALUES(?,?,?,?,?)",(chat,actor,target,action,int(time.time())));DB.commit()
async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):await u.message.reply_text(f"{{TITLE}}\\nGroup admins: /setup /setwords /setlimit /warn /mute /ban /audit")
async def setup(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not await is_admin(u,c):return
 DB.execute("INSERT OR REPLACE INTO config VALUES(?,?,?)",(u.effective_chat.id,"enabled","1"));DB.commit();await u.message.reply_text(f"{{TITLE}} enabled. Give the bot Delete messages and Restrict users permissions.")
async def setwords(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not await is_admin(u,c):return
 DB.execute("INSERT OR REPLACE INTO config VALUES(?,?,?)",(u.effective_chat.id,"words",",".join(x.lower() for x in c.args)[:1000]));DB.commit();await u.message.reply_text("Filter list updated.")
async def setlimit(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not await is_admin(u,c) or not c.args or not c.args[0].isdigit():return
 limit=max(3,min(20,int(c.args[0])));DB.execute("INSERT OR REPLACE INTO config VALUES(?,?,?)",(u.effective_chat.id,"limit",str(limit)));DB.commit();await u.message.reply_text(f"Flood limit: {{limit}} messages / 10 seconds.")
async def warn_target(u,c,reason="manual warning",target=None):
 if target is None:
  if not u.message.reply_to_message:return
  target=u.message.reply_to_message.from_user
 chat=u.effective_chat.id;DB.execute("INSERT OR IGNORE INTO warns VALUES(?,?,0)",(chat,target.id));DB.execute("UPDATE warns SET count=count+1 WHERE chat_id=? AND user_id=?",(chat,target.id));count=DB.execute("SELECT count FROM warns WHERE chat_id=? AND user_id=?",(chat,target.id)).fetchone()[0];log(chat,u.effective_user.id,target.id,reason);await u.message.reply_text(f"{{target.first_name}} warning {{count}}/3")
 if count>=3:
  await c.bot.restrict_chat_member(chat,target.id,ChatPermissions(can_send_messages=False),until_date=int(time.time())+3600);DB.execute("UPDATE warns SET count=0 WHERE chat_id=? AND user_id=?",(chat,target.id));DB.commit();await u.message.reply_text("Muted for one hour after 3 warnings.")
async def warn(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if await is_admin(u,c):await warn_target(u,c)
async def mute(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not await is_admin(u,c) or not u.message.reply_to_message:return
 seconds=max(60,min(604800,int(c.args[0]) if c.args and c.args[0].isdigit() else 3600));target=u.message.reply_to_message.from_user;await c.bot.restrict_chat_member(u.effective_chat.id,target.id,ChatPermissions(can_send_messages=False),until_date=int(time.time())+seconds);log(u.effective_chat.id,u.effective_user.id,target.id,"mute");await u.message.reply_text("User muted.")
async def ban(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not await is_admin(u,c) or not u.message.reply_to_message:return
 target=u.message.reply_to_message.from_user;await c.bot.ban_chat_member(u.effective_chat.id,target.id);log(u.effective_chat.id,u.effective_user.id,target.id,"ban");await u.message.reply_text("User banned.")
async def report(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not u.message.reply_to_message:return
 admins=await c.bot.get_chat_administrators(u.effective_chat.id);target=u.message.reply_to_message.from_user
 for member in admins:
  if not member.user.is_bot:
   try:await c.bot.send_message(member.user.id,f"Report in {{u.effective_chat.title}} against {{target.full_name}} by {{u.effective_user.full_name}}")
   except Exception:pass
 await u.message.reply_text("Report sent to administrators.")
async def audit(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not await is_admin(u,c):return
 rows=DB.execute("SELECT actor_id,target_id,action,created_at FROM audit WHERE chat_id=? ORDER BY id DESC LIMIT 20",(u.effective_chat.id,)).fetchall();await u.message.reply_text("Recent moderation\\n"+"\\n".join(f"{{a}} → {{t}} · {{x}} · {{time.strftime('%Y-%m-%d',time.gmtime(ts))}}" for a,t,x,ts in rows))
async def inspect(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not u.message or not u.message.text or u.message.chat.type=="private" or cfg(u.effective_chat.id,"enabled")!="1":return
 uid=u.effective_user.id
 try:
  m=await c.bot.get_chat_member(u.effective_chat.id,uid)
  if m.status in ("administrator","creator"):return
 except Exception:return
 text=u.message.text.lower();words=[x for x in cfg(u.effective_chat.id,"words").split(",") if x];violation=bool(words and any(x in text for x in words))
 if MODE=="links" and ("http://" in text or "https://" in text or "t.me/" in text):violation=True
 if MODE=="forwards" and u.message.forward_origin:violation=True
 q=WINDOW[(u.effective_chat.id,uid)];now=time.time();q.append(now);limit=int(cfg(u.effective_chat.id,"limit","6"));flood=len(q)>=limit and now-q[-limit]<10
 if violation or flood:
  try:await u.message.delete()
  except Exception:return
  await warn_target(u,c,"automatic "+("flood" if flood else MODE),u.effective_user)
app=ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
for command,handler in [("start",start),("setup",setup),("setwords",setwords),("setlimit",setlimit),("warn",warn),("mute",mute),("ban",ban),("report",report),("audit",audit)]:app.add_handler(CommandHandler(command,handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,inspect),group=1);app.run_polling(allowed_updates=Update.ALL_TYPES)
'''


WORKFLOWS = [
("appointment-booking","Appointment booking",("service","preferred date and time","contact number","notes"),("Pending","Confirmed","Completed","Cancelled"),"Booking"),
("salon-booking","Salon booking",("service","stylist preference","date and time","phone"),("Pending","Confirmed","In service","Completed","Cancelled"),"Booking"),
("clinic-intake","Clinic intake",("appointment reason","preferred date","phone","important note (avoid sensitive records)"),("Received","Triaged","Scheduled","Completed","Rejected"),"Healthcare"),
("tutor-booking","Tutor session booking",("subject","level","preferred schedule","contact"),("Pending","Matched","Scheduled","Completed","Cancelled"),"Education"),
("restaurant-reservation","Restaurant reservations",("party size","date","time","special request"),("Pending","Confirmed","Seated","Completed","Cancelled"),"Hospitality"),
("hotel-inquiry","Hotel booking inquiries",("dates","guest count","room preference","contact"),("New","Quoted","Confirmed","Completed","Cancelled"),"Hospitality"),
("real-estate-leads","Real-estate lead manager",("property type","area","budget","phone"),("New","Qualified","Viewing","Negotiation","Closed","Rejected"),"CRM"),
("car-rental","Car rental requests",("vehicle type","pickup time","return time","contact"),("New","Quoted","Reserved","Active","Completed","Cancelled"),"Rental"),
("repair-tickets","Repair service desk",("device or item","problem","pickup area","phone"),("Opened","Diagnosing","Quoted","Repairing","Completed","Closed"),"Support"),
("legal-intake","Legal consultation intake",("matter type","short summary","preferred time","contact"),("Received","Conflict check","Scheduled","Completed","Declined"),"Professional"),
("event-registration","Event registration manager",("event name","attendee name","ticket count","contact"),("Registered","Confirmed","Checked in","Completed","Cancelled"),"Events"),
("course-enrollment","Course enrollment",("course","student name","experience level","contact"),("Applied","Reviewed","Enrolled","Completed","Rejected"),"Education"),
("job-application","Job application tracker",("role","experience summary","portfolio link","contact"),("Applied","Screening","Interview","Offered","Hired","Rejected"),"Recruitment"),
("volunteer-signup","Volunteer coordinator",("activity","availability","skills","contact"),("Applied","Approved","Assigned","Completed","Cancelled"),"Community"),
("quote-request","Service quote requests",("service","scope","budget","deadline"),("New","Reviewing","Quoted","Accepted","Completed","Declined"),"Business"),
("delivery-request","Local delivery requests",("pickup","destination","package details","phone"),("Requested","Assigned","Picked up","Delivered","Cancelled"),"Logistics"),
("return-request","Product return manager",("order number","item","reason","preferred resolution"),("Requested","Approved","Received","Refunded","Rejected"),"Commerce"),
("warranty-claims","Warranty claim desk",("order number","product","fault","purchase date"),("Opened","Verifying","Approved","Resolved","Rejected"),"Support"),
("complaint-desk","Complaint resolution desk",("category","details","desired resolution","contact"),("Opened","Assigned","Investigating","Resolved","Closed"),"Support"),
("feedback-manager","Customer feedback manager",("experience area","rating 1-5","feedback","contact optional"),("Received","Reviewed","Actioned","Closed"),"Feedback"),
("survey-collector","Research survey collector",("topic response","rating 1-10","suggestion","demographic note optional"),("Submitted","Validated","Included","Rejected"),"Feedback"),
("crm-leads","Sales CRM leads",("need","budget","timeline","contact"),("New","Qualified","Contacted","Proposal","Won","Lost"),"CRM"),
("property-viewing","Property viewing scheduler",("property ID","preferred date","preferred time","phone"),("Requested","Confirmed","Viewed","Follow-up","Closed"),"Real Estate"),
("travel-request","Travel planning requests",("destination","dates","travelers","budget"),("New","Planning","Quoted","Booked","Completed","Cancelled"),"Travel"),
("catering-orders","Catering order manager",("event date","guest count","menu preference","delivery location"),("New","Quoted","Confirmed","Preparing","Delivered","Cancelled"),"Food"),
("custom-orders","Custom order workshop",("item","specification","budget","deadline"),("Requested","Designing","Quoted","Producing","Ready","Completed"),"Commerce"),
("wholesale-inquiry","Wholesale inquiry CRM",("business name","products","quantity","contact"),("New","Qualified","Quoted","Approved","Closed"),"Commerce"),
("donation-pledges","Donation pledge manager",("campaign","amount","payment plan","contact"),("Pledged","Verified","Received","Thanked","Cancelled"),"Nonprofit"),
("sponsorship-leads","Sponsorship pipeline",("organization","package interest","budget","contact"),("New","Qualified","Proposal","Negotiation","Won","Lost"),"CRM"),
("insurance-claims","Insurance claim intake",("policy reference","claim type","incident summary","contact"),("Received","Validating","Assessing","Approved","Settled","Rejected"),"Operations"),
("loan-precheck","Loan pre-check requests",("product type","requested range","employment type","contact"),("Received","Reviewing","Eligible","Follow-up","Declined"),"Finance"),
("visa-checklist","Visa document checklist",("destination","visa type","travel date","missing documents"),("Started","Reviewing","Documents ready","Submitted","Completed"),"Travel"),
("membership-application","Membership applications",("membership type","full name","reason","contact"),("Applied","Reviewing","Approved","Active","Rejected"),"Community"),
("vendor-onboarding","Vendor onboarding",("company","service","registration reference","contact"),("Applied","Compliance review","Approved","Active","Rejected"),"Operations"),
("incident-report","Incident reporting desk",("location","incident type","description","follow-up contact"),("Reported","Assigned","Investigating","Resolved","Closed"),"Operations"),
("maintenance-request","Maintenance request desk",("location","asset","problem","availability"),("Opened","Assigned","In progress","Completed","Closed"),"Operations"),
("leave-request","Employee leave requests",("leave type","dates","reason","handover note"),("Submitted","Manager review","Approved","Completed","Rejected"),"Workplace"),
("shift-swap","Shift swap coordinator",("current shift","requested shift","reason","coworker optional"),("Requested","Matched","Approved","Completed","Rejected"),"Workplace"),
("room-booking","Meeting room booking",("room","date","time range","purpose"),("Requested","Confirmed","In use","Completed","Cancelled"),"Workplace"),
("equipment-booking","Equipment reservation",("equipment","date range","purpose","contact"),("Requested","Approved","Checked out","Returned","Cancelled"),"Rental"),
]

TRACKERS = [
("expense-tracker","Expense tracker","BDT","Finance"),("income-tracker","Income tracker","BDT","Finance"),("budget-ledger","Budget ledger","BDT","Finance"),("inventory-tracker","Inventory tracker","units","Operations"),("stock-movement","Stock movement ledger","units","Commerce"),("habit-tracker","Habit tracker","times","Productivity"),("goal-tracker","Goal progress tracker","percent","Productivity"),("todo-manager","Task and to-do manager","points","Productivity"),("study-log","Study time log","minutes","Education"),("reading-log","Reading tracker","pages","Education"),("workout-log","Workout log","reps","Lifestyle"),("water-log","Water intake log","ml","Lifestyle"),("mood-journal","Mood journal","score","Lifestyle"),("medication-log","Medication check-in log","doses","Lifestyle"),("attendance-ledger","Attendance ledger","sessions","Workplace"),("time-tracker","Work time tracker","minutes","Workplace"),("mileage-log","Mileage log","km","Travel"),("issue-tracker","Issue backlog tracker","points","Operations"),("changelog-manager","Release changelog manager","changes","Developer"),("personal-crm","Personal follow-up CRM","priority","CRM"),
]

CATALOGS = [
("faq-knowledge-base","FAQ knowledge base","answer","Support"),("company-wiki","Company knowledge base","article","Workplace"),("digital-catalog","Digital product catalog","product","Commerce"),("service-menu","Service menu and pricing","service","Business"),("price-list","Searchable price list","price item","Commerce"),("course-library","Course lesson library","lesson","Education"),("recipe-library","Recipe library","recipe","Lifestyle"),("resource-directory","Community resource directory","resource","Community"),("coupon-directory","Coupon and offer directory","offer","Marketing"),("announcement-archive","Announcement archive","announcement","Channels"),
]

GROUPS = [
("anti-flood-pro","Advanced anti-flood moderator","flood"),("link-guard-pro","Link guard moderator","links"),("word-filter-pro","Word and phrase moderator","words"),("forward-guard","Forwarded-message guard","forwards"),("community-reports","Community report desk","reports"),("new-member-shield","New member safety shield","flood"),("discussion-moderator","Discussion moderator","words"),("marketplace-moderator","Marketplace group guard","links"),("classroom-moderator","Classroom group moderator","flood"),("support-group-guard","Support group guard","forwards"),
]


def build_family_templates() -> dict[str, dict]:
    result = {}
    for slug,name,fields,states,category in WORKFLOWS:
        code=_workflow_code(name,fields,states,slug.replace("-","_")+".db")
        result[slug]=_item(name,f"Multi-step intake, status workflow, admin queue, notes, notifications, CSV export, audit history, broadcasts, and access controls.",category,code,"Business")
    for slug,name,unit,category in TRACKERS:
        code=_tracker_code(name,unit,slug.replace("-","_")+".db")
        result[slug]=_item(name,f"Private SQLite ledger with labels, completion state, summaries, CSV export, admin analytics, broadcasts, and access controls.",category,code,"Advanced")
    for slug,name,item_name,category in CATALOGS:
        code=_catalog_code(name,item_name,slug.replace("-","_")+".db")
        result[slug]=_item(name,f"Admin-managed searchable {item_name} library with categories, pagination, favorites, view analytics, editing, and visibility controls.",category,code,"Content")
    for slug,name,mode in GROUPS:
        code=_group_code(name,mode,slug.replace("-","_")+".db")
        # Group bots use actual Telegram group admins, so no private claim is needed.
        item=_item(name,"Telegram-admin controlled moderation with configurable rules, flood limits, escalating warnings, timed mutes, reports, bans, and audit history.","Groups",code,"Groups","Add the bot to a group as administrator, then send /setup. Grant Delete messages and Restrict users permissions.")
        item["env_fields"]=[]
        result[slug]=item
    return result
