import ast,os,sqlite3,sys,subprocess,tempfile
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import bot_templates,telegram_detector


def test_template_catalog_is_practical_safe_and_unique():
    rows=bot_templates.list_templates()
    assert len(rows)>=100
    assert all(r["language"]=="python" for r in rows)
    assert len({r["category"] for r in rows})>=20
    assert len({r["id"] for r in rows})==len(rows)
    assert {"Groups","Growth","Business","Admin","Channels","Finance","Education","AI","AI Audio","Automation","Commerce","Files","Developer","Security","Sports","Bangladesh"}.issubset({r["category"] for r in rows})
    assert sum(1 for r in rows if r.get("requires_setup"))>=6
    for template_id in ("contact-support","admin-broadcast","order-bot","channel-poster","channel-gate","referral-rewards"):
        template=bot_templates.get_template(template_id)
        field=template["env_fields"][0]
        assert field["key"]=="ADMIN_CLAIM_CODE" and field["type"]=="generated"
        assert '"claim_" + CLAIM_CODE' in template["code"]
    for row in rows:
        assert row["name"] and row["description"] and row["framework"]
        item=bot_templates.get_template(row["id"])
        code=item["code"]
        assert "BOT_TOKEN" in code
        assert not telegram_detector.TOKEN_RE.search(code)
        analysis=telegram_detector.analyze_code(code,item["language"])
        assert analysis["telegram_detected"]
        assert analysis["token_source"]=="environment"
        assert analysis["update_mode"]=="polling"


def test_real_use_templates_include_their_working_state_and_controls():
    master=bot_templates.get_template("master-referral")["code"]
    assert "master_referral.db" in master and "if not admin_id()" in master and "You are the master admin" in master
    assert "first /start user becomes master admin" in bot_templates.get_template("master-referral")["after_deploy"]
    assert "get_chat_member" in master and "check_join" in master and "balance=balance+" in master
    assert 'CommandHandler("approve"' in master and 'CommandHandler("broadcast"' in master and 'CommandHandler("panel"' in master
    referral=bot_templates.get_template("referral-bot")["code"]
    assert "referrals.db" in referral and "?start=" in referral and "INSERT OR IGNORE" in referral
    contact=bot_templates.get_template("contact-support")
    assert contact["env_fields"][0]["key"]=="ADMIN_CLAIM_CODE" and contact["env_fields"][0]["type"]=="generated"
    assert "ADMIN_CHAT_ID" not in contact["code"]
    assert "live_support.db" in contact["code"] and "copy_message" in contact["code"] and "reply_to_message" in contact["code"] and 'CommandHandler("claim"' in contact["code"]
    broadcast=bot_templates.get_template("admin-broadcast")["code"]
    assert "/broadcast" in broadcast and "ADMIN_CLAIM_CODE" in broadcast and "Forbidden" in broadcast
    store=bot_templates.get_template("file-store")["code"]
    assert "files.db" in store and "file_id" in store and "file_" in store
    channel=bot_templates.get_template("channel-poster")["code"]
    assert "/setchannel" in channel and "copy_message" in channel and "administrator" in channel
    gate=bot_templates.get_template("channel-gate")["code"]
    assert "get_chat_member" in gate and "check_join" in gate
    group=bot_templates.get_template("group-helper")["code"]
    assert "NEW_CHAT_MEMBERS" in group and 'CommandHandler("warn"' in group and 'CommandHandler("setrules"' in group
    rewards=bot_templates.get_template("referral-rewards")["code"]
    assert "rewards.db" in rewards and "points=points+10" in rewards and 'CommandHandler("top"' in rewards


def test_every_template_parses_in_its_runtime():
    for row in bot_templates.list_templates():
        item=bot_templates.get_template(row["id"])
        if item["language"]=="python":
            compile(item["code"],row["id"]+".py","exec")
        elif item["language"]=="javascript":
            with tempfile.NamedTemporaryFile("w",suffix=".js",delete=False) as fh:
                fh.write(item["code"]);path=fh.name
            try:
                result=subprocess.run(["node","--check",path],capture_output=True,text=True)
                assert result.returncode==0,result.stderr
            finally:
                os.unlink(path)


def test_ranked_products_replace_quantity_first_fillers():
    rows=bot_templates.list_templates()
    assert len(rows) == 101
    assert [r["id"] for r in rows[:6]] == [
        "file-share-pro", "rose-style-moderator", "ai-business-bangla",
        "voice-to-text-pro", "text-to-voice-pro", "universal-converter-pro",
    ]
    retired={"appointment-booking","expense-tracker","habit-tracker","water-log","notes-bot","reminder-bot","command-bot","url-checker","bangladesh-job-alerts","bangla-quran-search","bangla-hadith-search","anime-discovery"}
    assert not retired & {r["id"] for r in rows}
    assert all(bot_templates.get_template(slug) is None for slug in retired)


def test_premium_products_have_real_integrations_and_controls():
    ai=bot_templates.get_template("ai-business-bangla")["code"]
    for marker in ("/chat/completions", "AI_API_KEY", "CREATE TABLE IF NOT EXISTS memory", "daily_limit", "RetryAfter", "broadcast"):
        assert marker in ai
    shop=bot_templates.get_template("bd-online-shop")["code"]
    for marker in ("CREATE TABLE IF NOT EXISTS products", "CREATE TABLE IF NOT EXISTS cart", "CREATE TABLE IF NOT EXISTS orders", "stock=stock-", "PAYMENT_URL", "Payment review"):
        assert marker in shop
    cricket=bot_templates.get_template("live-cricket-bangladesh")["code"]
    assert "api.cricapi.com" in cricket and "DATA_API_KEY" in cricket and "CREATE TABLE IF NOT EXISTS cache" in cricket
    sharing=bot_templates.get_template("file-share-pro")["code"]
    for marker in ("file_id", "token_urlsafe", "max_downloads", "downloads=downloads+1", "?start=f_"):
        assert marker in sharing
    stt=bot_templates.get_template("voice-to-text-pro")["code"]
    assert "/audio/transcriptions" in stt and "20*1024*1024" in stt and "AUDIO_API_KEY" in stt
    tts=bot_templates.get_template("text-to-voice-pro")["code"]
    assert "/audio/speech" in tts and "response_format" in tts
    moderator=bot_templates.get_template("rose-style-moderator")["code"]
    for marker in ("captcha", "restrict_chat_member", "automatic warning", "Link guard", "audit"):
        assert marker in moderator
    channel=bot_templates.get_template("paid-channel-manager")["code"]
    for marker in ("get_chat_member", "run_once", "publish_at", "delete_after", "referrer", "setchannel", "subscriptions", "create_chat_invite_link", "expire_members", "post_init(restore)", "RetryAfter"):
        assert marker in channel
    media=bot_templates.get_template("virus-total-scanner")["code"]
    assert "virustotal.com/api/v3/files" in media and "20*1024*1024" in media and "not retained" in media


def test_all_promoted_integrations_declare_required_secrets():
    for slug,key in (("ai-business-bangla","AI_API_KEY"),("voice-to-text-pro","AUDIO_API_KEY"),("live-cricket-bangladesh","DATA_API_KEY"),("virus-total-scanner","MEDIA_API_KEY")):
        assert key in {f["key"] for f in bot_templates.get_template(slug)["env_fields"]}


def test_every_embedded_sql_schema_executes_in_sqlite():
    """Compile checks do not catch malformed SQL; execute every static schema."""
    checked=0
    for row in bot_templates.list_templates():
        tree=ast.parse(bot_templates.get_template(row["id"])["code"])
        db=sqlite3.connect(":memory:")
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute) or not node.args:
                continue
            if node.func.attr not in ("execute","executescript") or not isinstance(node.args[0],ast.Constant) or not isinstance(node.args[0].value,str):
                continue
            sql=node.args[0].value.strip()
            if not sql.upper().startswith(("CREATE ","PRAGMA ")):
                continue
            (db.executescript(sql) if node.func.attr=="executescript" else db.execute(sql));checked+=1
        db.close()
    assert checked>=100
