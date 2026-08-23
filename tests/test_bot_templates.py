import os,sys,subprocess,tempfile
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import bot_templates,telegram_detector


def test_template_catalog_is_practical_safe_and_unique():
    rows=bot_templates.list_templates()
    assert len(rows)>=16
    assert len({r["id"] for r in rows})==len(rows)
    assert {"Basics","Menus","Groups","Utilities","Storage","Node.js","Growth","Business","Admin"}.issubset({r["category"] for r in rows})
    assert sum(1 for r in rows if r.get("requires_setup"))>=3
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
    referral=bot_templates.get_template("referral-bot")["code"]
    assert "referrals.db" in referral and "?start=" in referral and "INSERT OR IGNORE" in referral
    contact=bot_templates.get_template("contact-support")
    assert contact["env_fields"][0]["key"]=="ADMIN_CHAT_ID"
    assert "support.db" in contact["code"] and "forward_message" in contact["code"] and "reply_to_message" in contact["code"]
    broadcast=bot_templates.get_template("admin-broadcast")["code"]
    assert "/broadcast" in broadcast and "ADMIN_CHAT_ID" in broadcast and "Forbidden" in broadcast
    store=bot_templates.get_template("file-store")["code"]
    assert "files.db" in store and "file_id" in store and "file_" in store


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
