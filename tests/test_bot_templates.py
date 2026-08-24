import ast,os,sqlite3,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import bot_templates,telegram_detector

EXPECTED=["complete-group-manager","complete-file-ai-toolbox","complete-ai-support","complete-commerce","complete-channel-business"]


def test_catalog_contains_only_complete_products():
    rows=bot_templates.list_templates()
    assert [r["id"] for r in rows]==EXPECTED
    assert len(rows)==5 and all(r["language"]=="python" for r in rows)
    assert all(r["badge"]=="Complete" for r in rows)
    for row in rows:
        item=bot_templates.get_template(row["id"]);code=item["code"]
        assert row["name"] and row["description"] and row["category"]
        assert "BOT_TOKEN" in code and not telegram_detector.TOKEN_RE.search(code)
        analysis=telegram_detector.analyze_code(code,"python")
        assert analysis["telegram_detected"] and analysis["update_mode"]=="polling"
        compile(code,row["id"]+".py","exec")


def test_group_manager_is_one_real_moderation_product():
    code=bot_templates.get_template("complete-group-manager")["code"]
    for marker in ("captcha","restrict_chat_member","setwords","setlimit","warns","ban_chat_member","report","audit","automatic"):
        assert marker in code


def test_file_toolbox_combines_the_related_features():
    code=bot_templates.get_template("complete-file-ai-toolbox")["code"]
    for marker in ("max_downloads","downloads=downloads+1","Image.open","PdfReader","api.ocr.space","virustotal.com","sha256","qrcode.make","/audio/transcriptions","/audio/speech"):
        assert marker in code
    keys={x["key"] for x in bot_templates.get_template("complete-file-ai-toolbox")["env_fields"]}
    assert {"ADMIN_CLAIM_CODE","AI_API_KEY","OCR_API_KEY","VIRUSTOTAL_API_KEY"}.issubset(keys)


def test_ai_store_and_channel_are_full_products():
    ai=bot_templates.get_template("complete-ai-support")["code"]
    for marker in ("/chat/completions","memory","daily_limit","setprompt","broadcast","ban"):
        assert marker in ai
    store=bot_templates.get_template("complete-commerce")["code"]
    for marker in ("CREATE TABLE IF NOT EXISTS products","CREATE TABLE IF NOT EXISTS cart","CREATE TABLE IF NOT EXISTS orders","stock=stock-","Payment review","orders","panel"):
        assert marker in store
    channel=bot_templates.get_template("complete-channel-business")["code"]
    for marker in ("get_chat_member","referrer","subscriptions","create_chat_invite_link","expire_members","schedule","delete_after","broadcast","post_init(restore)"):
        assert marker in channel


def test_every_static_schema_executes():
    checked=0
    for row in bot_templates.list_templates():
        tree=ast.parse(bot_templates.get_template(row["id"])["code"]);db=sqlite3.connect(":memory:")
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute) or not node.args:continue
            if node.func.attr not in ("execute","executescript") or not isinstance(node.args[0],ast.Constant) or not isinstance(node.args[0].value,str):continue
            sql=node.args[0].value.strip()
            if sql.upper().startswith(("CREATE ","PRAGMA ")):
                (db.executescript(sql) if node.func.attr=="executescript" else db.execute(sql));checked+=1
        db.close()
    assert checked>=5
