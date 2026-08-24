"""Small catalog of complete Telegram bot products, not feature fragments."""
from services.premium_templates import ai_code, channel_code, commerce_code, field, item
from services.popular_tools import moderator_code


def _flagship(name, description, category, code, fields=(), after=""):
    return item(name, description, category, code, fields, "Complete", 1000, after)


def file_toolbox_code():
    return r'''# requirements: python-telegram-bot==21.4 Pillow==10.4.0 pypdf==4.3.1 qrcode==7.4.2 httpx==0.27.2
import hashlib,io,os,secrets,sqlite3,time
import httpx,qrcode
from PIL import Image
from pypdf import PdfReader
from telegram import Update
from telegram.ext import ApplicationBuilder,CommandHandler,ContextTypes,MessageHandler,filters
CLAIM=os.getenv("ADMIN_CLAIM_CODE","");AI_KEY=os.getenv("AI_API_KEY","");AI_BASE=os.getenv("AI_API_BASE","https://api.openai.com/v1").rstrip("/");OCR_KEY=os.getenv("OCR_API_KEY","");VT_KEY=os.getenv("VIRUSTOTAL_API_KEY","")
DB=sqlite3.connect("file_toolbox.db",check_same_thread=False);DB.execute("PRAGMA journal_mode=WAL");DB.executescript("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,mode TEXT DEFAULT 'share',format TEXT DEFAULT 'pdf',voice TEXT DEFAULT 'alloy',used INTEGER DEFAULT 0,banned INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS files(code TEXT PRIMARY KEY,owner INTEGER,file_id TEXT,kind TEXT,name TEXT,size INTEGER,expires INTEGER,max_downloads INTEGER,downloads INTEGER DEFAULT 0,active INTEGER DEFAULT 1);");DB.commit()
def admin():
 r=DB.execute("SELECT value FROM settings WHERE key='admin'").fetchone();return int(r[0]) if r else 0
def media(m):
 if m.document:return m.document,"document",m.document.file_name or "document"
 if m.video:return m.video,"video",m.video.file_name or "video.mp4"
 if m.audio:return m.audio,"audio",m.audio.file_name or "audio.mp3"
 if m.voice:return m.voice,"voice","voice.ogg"
 if m.photo:return m.photo[-1],"photo","photo.jpg"
 return None,None,None
async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
 uid=u.effective_user.id
 if not admin() and c.args and c.args[0]=="claim_"+CLAIM:DB.execute("INSERT INTO settings VALUES('admin',?)",(str(uid),));DB.commit();await u.message.reply_text("Owner connected. Use /panel.");return
 DB.execute("INSERT OR IGNORE INTO users(id) VALUES(?)",(uid,));DB.commit()
 if c.args and c.args[0].startswith("f_"):await deliver(u,c,c.args[0][2:]);return
 await u.message.reply_text("File & AI Toolbox\n\nSend a file after choosing /mode.\n/share links · /mode share|compress|pdf|text|ocr|scan|transcribe|hash\n/format jpg|png|webp|pdf · /qr TEXT · /speak TEXT\n/files · /delete CODE")
async def mode(u,c):
 allowed={"share","compress","pdf","text","ocr","scan","transcribe","hash"}
 if not c.args or c.args[0] not in allowed:await u.message.reply_text("Modes: "+", ".join(sorted(allowed)));return
 DB.execute("UPDATE users SET mode=? WHERE id=?",(c.args[0],u.effective_user.id));DB.commit();await u.message.reply_text("Mode: "+c.args[0])
async def fmt(u,c):
 if c.args and c.args[0] in ("jpg","png","webp","pdf"):DB.execute("UPDATE users SET format=? WHERE id=?",(c.args[0],u.effective_user.id));DB.commit();await u.message.reply_text("Output: "+c.args[0])
async def store(u,c,obj,kind,name):
 code=secrets.token_urlsafe(8).replace('-','').replace('_','')[:10];DB.execute("INSERT INTO files VALUES(?,?,?,?,?,?,?,?,0,1)",(code,u.effective_user.id,obj.file_id,kind,name[:200],obj.file_size or 0,int(time.time())+30*86400,1000));DB.commit();me=await c.bot.get_me();await u.message.reply_text(f"https://t.me/{me.username}?start=f_{code}\nExpires in 30 days · 1000-download limit")
async def deliver(u,c,code):
 row=DB.execute("SELECT file_id,kind,name,expires,max_downloads,downloads,active FROM files WHERE code=?",(code,)).fetchone()
 if not row or not row[6] or row[3]<int(time.time()) or row[5]>=row[4]:await u.effective_message.reply_text("Link expired, removed, or download limit reached.");return
 send={"document":c.bot.send_document,"video":c.bot.send_video,"audio":c.bot.send_audio,"voice":c.bot.send_voice,"photo":c.bot.send_photo}.get(row[1],c.bot.send_document);await send(u.effective_chat.id,row[0],caption=row[2]);DB.execute("UPDATE files SET downloads=downloads+1 WHERE code=?",(code,));DB.commit()
async def process(u,c):
 uid=u.effective_user.id;user=DB.execute("SELECT mode,format,banned FROM users WHERE id=?",(uid,)).fetchone();obj,kind,name=media(u.message)
 if not obj or (user and user[2]):return
 selected=(user[0] if user else "share");target=(user[1] if user else "pdf")
 if selected=="share":await store(u,c,obj,kind,name);return
 if (obj.file_size or 0)>20*1024*1024:await u.message.reply_text("Processing limit is 20 MB. Share mode supports larger Telegram files.");return
 raw=bytes(await (await obj.get_file()).download_as_bytearray());out=io.BytesIO();filename="result.txt"
 try:
  if selected in ("compress","pdf"):
   image=Image.open(io.BytesIO(raw));image=image.convert("RGB") if target in ("jpg","pdf") else image.convert("RGBA");image.thumbnail((1920,1920));savefmt={"jpg":"JPEG","png":"PNG","webp":"WEBP","pdf":"PDF"}[target];image.save(out,savefmt,quality=72,optimize=True);filename="result."+target
  elif selected=="text":
   reader=PdfReader(io.BytesIO(raw));out.write("\n\n".join((p.extract_text() or "") for p in reader.pages[:100]).encode());filename="extracted.txt"
  elif selected=="hash":out.write(f"SHA256 {hashlib.sha256(raw).hexdigest()}\nSHA1 {hashlib.sha1(raw).hexdigest()}\nMD5 {hashlib.md5(raw).hexdigest()}\nBytes {len(raw)}".encode());filename="hashes.txt"
  elif selected=="ocr":
   if not OCR_KEY:raise ValueError("Owner must configure OCR_API_KEY")
   async with httpx.AsyncClient(timeout=90) as client:r=await client.post("https://api.ocr.space/parse/image",headers={"apikey":OCR_KEY},files={"file":(name,raw)});r.raise_for_status();text="\n".join(x.get("ParsedText","") for x in r.json().get("ParsedResults",[]));out.write(text.encode());filename="ocr.txt"
  elif selected=="scan":
   if not VT_KEY:raise ValueError("Owner must configure VIRUSTOTAL_API_KEY")
   async with httpx.AsyncClient(timeout=120) as client:r=await client.post("https://www.virustotal.com/api/v3/files",headers={"x-apikey":VT_KEY},files={"file":(name,raw)});r.raise_for_status();aid=r.json()["data"]["id"];stats={};status="queued"
   async with httpx.AsyncClient(timeout=60) as client:
    for _ in range(10):await __import__('asyncio').sleep(2);r=await client.get("https://www.virustotal.com/api/v3/analyses/"+aid,headers={"x-apikey":VT_KEY});attrs=r.json().get("data",{}).get("attributes",{});status=attrs.get("status");stats=attrs.get("stats",{}); 
   out.write(f"Status {status}\nMalicious {stats.get('malicious',0)}\nSuspicious {stats.get('suspicious',0)}\nHarmless {stats.get('harmless',0)}".encode());filename="scan.txt"
  elif selected=="transcribe":
   if not AI_KEY:raise ValueError("Owner must configure AI_API_KEY")
   async with httpx.AsyncClient(timeout=120) as client:r=await client.post(AI_BASE+"/audio/transcriptions",headers={"Authorization":"Bearer "+AI_KEY},data={"model":"whisper-1"},files={"file":(name,raw,getattr(obj,'mime_type',None) or 'audio/ogg')});r.raise_for_status();out.write(r.json().get("text","").encode());filename="transcript.txt"
  out.seek(0);out.name=filename;await u.message.reply_document(out,caption="Processed in memory; input not retained.");DB.execute("UPDATE users SET used=used+1 WHERE id=?",(uid,));DB.commit()
 except Exception as e:await u.message.reply_text("Could not process: "+str(e)[:180])
async def qr(u,c):
 if not c.args:return
 out=io.BytesIO();qrcode.make(" ".join(c.args)[:2000]).save(out,"PNG");out.seek(0);out.name="qr.png";await u.message.reply_document(out)
async def speak(u,c):
 if not c.args or not AI_KEY:return
 text=" ".join(c.args)[:4000];voice=DB.execute("SELECT voice FROM users WHERE id=?",(u.effective_user.id,)).fetchone()[0]
 async with httpx.AsyncClient(timeout=120) as client:r=await client.post(AI_BASE+"/audio/speech",headers={"Authorization":"Bearer "+AI_KEY},json={"model":"tts-1","voice":voice,"input":text,"response_format":"mp3"});r.raise_for_status();out=io.BytesIO(r.content);out.name="speech.mp3";await u.message.reply_audio(out)
async def files(u,c):
 rows=DB.execute("SELECT code,name,downloads,max_downloads FROM files WHERE owner=? AND active=1 ORDER BY rowid DESC LIMIT 20",(u.effective_user.id,)).fetchall();await u.message.reply_text("\n".join(f"{x} · {n} · {d}/{m}" for x,n,d,m in rows) or "No files.")
async def delete(u,c):
 if c.args:DB.execute("UPDATE files SET active=0 WHERE code=? AND owner=?",(c.args[0],u.effective_user.id));DB.commit();await u.message.reply_text("Removed.")
async def panel(u,c):
 if u.effective_user.id==admin():await u.message.reply_text(f"Users {DB.execute('SELECT COUNT(*) FROM users').fetchone()[0]} · Processed {DB.execute('SELECT COALESCE(SUM(used),0) FROM users').fetchone()[0]} · Shared {DB.execute('SELECT COUNT(*) FROM files').fetchone()[0]}")
app=ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
for cmd,fn in [("start",start),("mode",mode),("format",fmt),("qr",qr),("speak",speak),("files",files),("delete",delete),("panel",panel)]:app.add_handler(CommandHandler(cmd,fn))
app.add_handler(MessageHandler(filters.Document.ALL|filters.PHOTO|filters.VIDEO|filters.AUDIO|filters.VOICE,process));app.run_polling()
'''


def support_ai_code():
    base = ai_code(
        "AI support, CRM & human inbox",
        "You are a business support agent. Use only approved policy. Never invent price, stock, discounts or guarantees. Escalate uncertain requests to a human.",
        "AI answers, FAQ rules, memory, human handoff, leads, quotas, analytics, bans and broadcasts.",
    )
    # The core AI product remains intentionally one-file; append visible feature
    # guidance to its start text rather than pretending separate products.
    return base.replace(
        'Send a message. /new clears memory · /usage shows quota.',
        'Send a message. /new clears memory · /usage shows quota. Owner: /setprompt /setlimit /broadcast /ban /panel.',
    )


def build_flagship_templates():
    ai_fields=[field("AI_API_KEY","OpenAI-compatible API key",True),field("AI_API_BASE","API base",False,True,"https://api.openai.com/v1"),field("AI_MODEL","Model",False,True,"gpt-4o-mini")]
    toolbox_fields=[field("AI_API_KEY","Speech API key",True,False),field("AI_API_BASE","OpenAI-compatible API base",False,False,"https://api.openai.com/v1"),field("OCR_API_KEY","OCR.Space API key",True,False),field("VIRUSTOTAL_API_KEY","VirusTotal API key",True,False)]
    products = {
        "complete-group-manager": _flagship(
            "Complete group manager",
            "One Rose-style bot for captcha, anti-flood, links, blocked words, warnings, timed mute, reports, bans and audit history.",
            "Community", moderator_code(), (),
            "Add it as group administrator, grant Delete/Restrict/Invite permissions, then /setup."
        ),
        "complete-file-ai-toolbox": _flagship(
            "Complete file & AI toolbox",
            "One bot for file sharing, expiring links, image/PDF conversion, compression, PDF text, OCR, VirusTotal, hashes, QR, transcription and text-to-speech.",
            "Files & AI", file_toolbox_code(), toolbox_fields,
        ),
        "complete-ai-support": _flagship(
            "Complete AI business assistant",
            "One configurable AI support product with Bangla/Banglish, conversation memory, owner policy, quotas, analytics, bans and broadcasts.",
            "AI & Support", support_ai_code(), ai_fields,
        ),
        "complete-commerce": _flagship(
            "Complete Telegram store",
            "One store bot with catalog, stock, cart, checkout, payment reference review, order history, buyer status notifications, support and sales analytics.",
            "Commerce", commerce_code("Complete Telegram store","physical and digital products",("Pending payment","Payment review","Confirmed","Processing","Delivered","Cancelled")),
            [field("PAYMENT_URL","bKash/Nagad/SSLCommerz checkout URL",False,False)],
        ),
        "complete-channel-business": _flagship(
            "Complete channel growth & membership",
            "One channel bot for force-join, verified referrals, paid plans, payment approval, private invites, expiry removal, scheduled posts, auto-delete, broadcasts and analytics.",
            "Channels", channel_code("Complete channel growth & membership","all"), (),
            "Add it as channel administrator, open Go to bot, then /setchannel @channel."
        ),
    }
    products["complete-group-manager"]["env_fields"] = []
    return products
