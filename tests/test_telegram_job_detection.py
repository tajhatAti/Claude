import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())

import database
database.init_db()
from services import telegram_detector

TOKEN="123456789:AA" + "x"*32

class Resp:
    def __init__(self,status=200,data=None): self.status_code=status; self.data=data or {}; self.placed_on=None
    def json(self): return self.data


def test_detector_verifies_identity_without_returning_token(monkeypatch):
    monkeypatch.setattr(telegram_detector.requests,"post",lambda *a,**k:Resp(200,{"ok":True,"result":{"id":777,"is_bot":True,"username":"DemoHelperBot"}}))
    out=telegram_detector.inspect_bot(f'BOT_TOKEN="{TOKEN}"')
    assert out["detected"] and out["username"]=="DemoHelperBot" and out["check_status"]=="verified"
    assert TOKEN not in repr(out)
    public=telegram_detector.public_fields(out)
    assert public["telegram_bot_url"]=="https://t.me/DemoHelperBot" and TOKEN not in repr(public)


def test_verified_token_replaces_old_and_example_tokens_everywhere():
    old="987654321:AA"+"z"*32
    code=f'''BOT_TOKEN = "example-token"\nTOKEN = "{old}"\nbot = telegram.Bot(token="placeholder")\napp = ApplicationBuilder().token("another").build()'''
    clean,env=telegram_detector.apply_verified_token(code,{"BOT_TOKEN":old,"TELEGRAM_BOT_TOKEN":"sample"},TOKEN)
    assert old not in clean and "example-token" not in clean and "placeholder" not in clean
    assert clean.count(TOKEN)==4
    assert env["BOT_TOKEN"]==TOKEN and env["TELEGRAM_BOT_TOKEN"]==TOKEN


def test_detector_handles_username_only_and_network_failure(monkeypatch):
    out=telegram_detector.inspect_bot('BOT_USERNAME="@KnownBot"')
    assert out["detected"] and out["username"]=="KnownBot" and out["check_status"]=="username_only"
    monkeypatch.setattr(telegram_detector.requests,"post",lambda *a,**k:(_ for _ in ()).throw(RuntimeError("url contains secret")))
    out=telegram_detector.inspect_bot(TOKEN)
    assert out["check_status"]=="telegram_unreachable" and TOKEN not in repr(out)


def test_run_records_safe_bot_metadata_and_admin_can_open_it(monkeypatch):
    from app import app
    from fastapi.testclient import TestClient
    from routes.deps import hash_password, now_utc_str
    from routes import runspace
    from services import runner_client
    c=database.get_db_connection(); now=now_utc_str()
    c.execute("INSERT INTO users(username,email,password,is_verified,is_admin,created_at,updated_at) VALUES(?,?,?,1,1,?,?)",("owner","owner@gmail.com",hash_password("Passw0rd!x"),now,now));c.commit();c.close()
    client=TestClient(app)
    token=client.post("/login",json={"username":"owner@gmail.com","email":"owner@gmail.com","password":"Passw0rd!x"}).json()["token"]
    headers={"Authorization":"Bearer "+token}
    monkeypatch.setattr(telegram_detector.requests,"post",lambda *a,**k:Resp(200,{"ok":True,"result":{"id":777,"is_bot":True,"username":"DemoHelperBot"}}))
    verified=client.post("/api/telegram-bot/verify",headers=headers,json={"token":TOKEN})
    assert verified.status_code==200 and verified.json()["telegram_bot_username"]=="DemoHelperBot"
    verification_id=verified.json()["telegram_verification_id"]
    assert verification_id and TOKEN not in verified.text
    meta={"detected":True,"username":"DemoHelperBot","bot_id":"777","check_status":"verified","verified_at":now}
    monkeypatch.setattr(runspace,"CLUSTER_LIMITS_ENABLED",False)
    sent=[]
    def fake(method,path,*args,**kwargs):
        if method=="POST" and path=="/internal/jobs":
            sent.append(args[0] if args else kwargs)
            return Resp(201,{"id":"rid-bot","status":"running"})
        if method=="GET" and path=="/internal/jobs": return Resp(200,{"jobs":[{"id":"rid-bot","status":"running","uptime_s":5}]})
        return Resp(404,{})
    monkeypatch.setattr(runner_client,"_runner_http",fake)
    monkeypatch.setattr(runner_client,"fleet_jobs",lambda refresh=False:{"rid-bot":{"status":"running","uptime_s":5}})
    denied=client.post("/api/jobs",headers=headers,json={"name":"no-proof","language":"python","code":"print(1)"})
    assert denied.status_code==400 and "Verify" in denied.text
    old_token="987654321:AA"+"z"*32
    r=client.post("/api/jobs",headers=headers,json={"name":"demo-bot","language":"python","code":f'TOKEN="{old_token}"',"env":{"BOT_TOKEN":TOKEN},"telegram_verification_id":verification_id})
    assert r.status_code==200,r.text
    assert r.json()["telegram_bot_url"]=="https://t.me/DemoHelperBot" and TOKEN not in r.text
    assert old_token not in sent[0]["code"] and TOKEN in sent[0]["code"]
    assert sent[0]["env"]["BOT_TOKEN"]==TOKEN
    reused=client.post("/api/jobs",headers=headers,json={"name":"reuse-proof","language":"python","code":"TOKEN='x'","env":{"BOT_TOKEN":TOKEN},"telegram_verification_id":verification_id})
    assert reused.status_code==400 and "Verify" in reused.text
    listed=client.get("/api/jobs",headers=headers).json()["jobs"][0]
    assert listed["telegram_bot_detected"] and listed["telegram_bot_username"]=="DemoHelperBot"
    # One account may run three verified bots, never a fourth.
    for i in (2,3):
        proof=client.post("/api/telegram-bot/verify",headers=headers,json={"token":TOKEN}).json()["telegram_verification_id"]
        made=client.post("/api/jobs",headers=headers,json={"name":f"bot-{i}","language":"python","code":"TOKEN='example'","env":{"BOT_TOKEN":TOKEN},"telegram_verification_id":proof})
        assert made.status_code==200,made.text
    fourth=client.post("/api/telegram-bot/verify",headers=headers,json={"token":TOKEN}).json()["telegram_verification_id"]
    denied=client.post("/api/jobs",headers=headers,json={"name":"bot-4","language":"python","code":"TOKEN='example'","env":{"BOT_TOKEN":TOKEN},"telegram_verification_id":fourth})
    assert denied.status_code==429 and "3 Telegram bots" in denied.text
    assert client.get("/admin/telegram-jobs").status_code==404
    admin=client.get("/admin/telegram-jobs",headers=headers)
    assert admin.status_code==200
    data=admin.json(); assert data["running"]==3 and data["events"][0]["owner"]=="owner"
    assert data["bots"][0]["telegram_bot_url"]=="https://t.me/DemoHelperBot" and TOKEN not in admin.text
