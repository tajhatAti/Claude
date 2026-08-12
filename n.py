import os
import io
import re
import uuid
import time
import html
import threading
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Replace with your Telegram Bot Token from @BotFather
BOT_TOKEN = "8808343094:AAG5MImdi1UarO1-kw49938FUIGQu3OwlmU"

# GitHub Personal Access Token (PAT) for rate limit protection & private repos
SERVER_GITHUB_TOKEN = "ghp_" + "saTAP4LXMrNKZF33pPgtfatbwCDjWx3FqLRD"

# Initialize TeleBot in single-threaded mode for host stability
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

user_sessions = {}
user_pats = {}

MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024  # 50 MB Limit
MAX_MESSAGE_LENGTH = 4000  # Safe threshold below Telegram's 4096 character limit


class ContinuousChatAction:
    """Maintains 'upload_document' status in chat during file transfers."""
    def __init__(self, bot_instance, chat_id, action="upload_document", interval=4):
        self.bot = bot_instance
        self.chat_id = chat_id
        self.action = action
        self.interval = interval
        self.is_running = False
        self._thread = None

    def start(self):
        self.is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while self.is_running:
            try:
                self.bot.send_chat_action(self.chat_id, self.action)
            except Exception:
                pass
            time.sleep(self.interval)

    def stop(self):
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)


def sanitize_filename(name: str) -> str:
    """Replaces unsupported filesystem characters."""
    return re.sub(r'[/\\?%*:|"<>]', '_', name)


def safe_delete_message(chat_id: int, message_id: int):
    """Deletes a Telegram message without raising exceptions if already missing."""
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def get_headers(chat_id: int) -> dict:
    """Constructs HTTP headers with GitHub authentication tokens."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "TelegramBot-GitHub-Explorer"
    }
    if chat_id in user_pats and user_pats[chat_id]:
        headers["Authorization"] = f"Bearer {user_pats[chat_id]}"
    elif SERVER_GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {SERVER_GITHUB_TOKEN}"
    return headers


def github_request(url: str, chat_id: int):
    """Sends requests to GitHub API with automatic token fallback on 401 errors."""
    headers = get_headers(chat_id)
    res = requests.get(url, headers=headers)

    if res.status_code == 401:
        fallback_headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TelegramBot-GitHub-Explorer"
        }
        res = requests.get(url, headers=fallback_headers)

    return res


@bot.message_handler(commands=['settoken'])
def set_token(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        user_pats[message.chat.id] = parts[1].strip()
        bot.reply_to(message, "🔑 <b>Personal PAT Saved</b>", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ Usage: <code>/settoken YOUR_PAT</code>", parse_mode="HTML")


@bot.message_handler(commands=['deltoken'])
def del_token(message):
    if message.chat.id in user_pats:
        del user_pats[message.chat.id]
        bot.reply_to(message, "🗑️ <b>Personal PAT Removed</b>", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ No token stored.", parse_mode="HTML")


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 <b>GitHub Downloader Bot</b>\n\n"
        "• Send <code>username</code> to list repos\n"
        "• Send <code>owner/repo</code> for direct download\n"
        "• Private Repos: Use <code>/settoken PAT</code>"
    )
    bot.reply_to(message, welcome_text, parse_mode="HTML")


@bot.message_handler(func=lambda message: True)
def handle_input(message):
    text = message.text.strip()
    bot.send_chat_action(message.chat.id, 'typing')

    url_match = re.match(r"(?:https://github\.com/)?([^/\s]+)/([^/\s]+)/?", text)
    if url_match:
        owner, repo = url_match.group(1), url_match.group(2)
        if repo.endswith(".git"):
            repo = repo[:-4]
        session_id = str(uuid.uuid4())[:8]
        user_sessions[session_id] = {"owner": owner, "repo": repo}
        fetch_and_show_branches(message.chat.id, session_id)
    elif "/" not in text and " " not in text:
        fetch_and_show_user_repos(message.chat.id, text)
    else:
        bot.reply_to(message, "❌ Invalid format.")


def fetch_and_show_user_repos(chat_id, username, message_id=None):
    res = github_request(f"https://api.github.com/users/{username}/repos?per_page=30&sort=updated", chat_id)

    if res.status_code == 404:
        bot.send_message(chat_id, f"❌ User or Org <code>{html.escape(username)}</code> not found.", parse_mode="HTML")
        return
    elif res.status_code != 200:
        bot.send_message(chat_id, f"❌ GitHub API Error ({res.status_code}). Try again later.", parse_mode="HTML")
        return

    repos = res.json()
    if not repos or not isinstance(repos, list):
        bot.send_message(chat_id, f"❌ No public repos found for <code>{html.escape(username)}</code>.", parse_mode="HTML")
        return

    session_id = str(uuid.uuid4())[:8]
    user_sessions[session_id] = {
        "owner": username,
        "repos": [r["name"] for r in repos if isinstance(r, dict)]
    }

    markup = InlineKeyboardMarkup()
    for idx, repo_name in enumerate(user_sessions[session_id]["repos"][:25]):
        markup.add(InlineKeyboardButton(text=f"📦 {repo_name}", callback_data=f"repo:{session_id}:{idx}"))

    text = f"👤 <b>User:</b> <code>{html.escape(username)}</code>\nSelect repository:"
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith("repo:"))
def handle_repo_selection(call):
    _, session_id, idx_str = call.data.split(":")
    session = user_sessions.get(session_id)
    if not session:
        bot.answer_callback_query(call.id, "⚠️ Session expired.", show_alert=True)
        return

    owner = session["owner"]
    repo = session["repos"][int(idx_str)]
    session["repo"] = repo
    fetch_and_show_branches(call.message.chat.id, session_id, message_id=call.message.message_id)


def fetch_and_show_branches(chat_id, session_id, message_id=None):
    session = user_sessions.get(session_id)
    if not session:
        bot.send_message(chat_id, "⚠️ Session expired.")
        return

    owner = session["owner"]
    repo = session["repo"]

    bot.send_chat_action(chat_id, 'typing')
    res = github_request(f"https://api.github.com/repos/{owner}/{repo}/branches", chat_id)

    if res.status_code != 200:
        bot.send_message(chat_id, f"❌ Repo <code>{html.escape(owner)}/{html.escape(repo)}</code> not found or private.", parse_mode="HTML")
        return

    branches = res.json()
    if not branches:
        bot.send_message(chat_id, "❌ No branches found.")
        return

    session["branches"] = [b["name"] for b in branches]

    if len(branches) == 1:
        single_branch = branches[0]["name"]
        if message_id:
            safe_delete_message(chat_id, message_id)
        process_repository_content(chat_id, session_id, single_branch, branch_idx=0)
        return

    markup = InlineKeyboardMarkup()
    for idx, branch in enumerate(session["branches"]):
        markup.add(InlineKeyboardButton(text=f"🌿 {branch}", callback_data=f"proc:{session_id}:{idx}"))

    if "repos" in session:
        markup.add(InlineKeyboardButton(text="🔙 Back to Repos", callback_data=f"back_repos:{session_id}"))

    text = f"📦 <b>Repo:</b> <code>{html.escape(owner)}/{html.escape(repo)}</code>\nSelect branch to download:"
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith("proc:"))
def handle_branch_process(call):
    _, session_id, idx_str = call.data.split(":")
    session = user_sessions.get(session_id)
    if not session:
        bot.answer_callback_query(call.id, "⚠️ Session expired.", show_alert=True)
        return

    branch_idx = int(idx_str)
    branch = session["branches"][branch_idx]
    
    safe_delete_message(call.message.chat.id, call.message.message_id)
    process_repository_content(call.message.chat.id, session_id, branch, branch_idx)


def process_repository_content(chat_id, session_id, branch, branch_idx):
    session = user_sessions.get(session_id, {})
    owner = session.get("owner", "")
    repo = session.get("repo", "")

    action_loop = ContinuousChatAction(bot, chat_id, action='upload_document')
    action_loop.start()

    try:
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        zip_res = github_request(zip_url, chat_id)

        if zip_res.status_code == 200:
            file_size = len(zip_res.content)
            safe_branch = sanitize_filename(branch)

            if file_size > MAX_TELEGRAM_FILE_SIZE:
                bot.send_message(
                    chat_id,
                    f"⚠️ File size exceeds 50MB Telegram limit.\n🔗 <a href='{zip_url}'>Direct Download Link</a>",
                    parse_mode="HTML"
                )
            else:
                file_bytes = io.BytesIO(zip_res.content)
                file_bytes.name = f"{repo}_{safe_branch}.zip"

                bot.send_document(
                    chat_id,
                    document=file_bytes,
                    caption=f"📦 <b>{html.escape(repo)}</b> (<code>{html.escape(branch)}</code>)",
                    parse_mode="HTML"
                )
        else:
            bot.send_message(chat_id, f"❌ Download failed for branch <code>{html.escape(branch)}</code>.", parse_mode="HTML")
            return
    finally:
        action_loop.stop()

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="📊 Show Full Details", callback_data=f"details:{session_id}:{branch_idx}"))
    markup.add(InlineKeyboardButton(text="🔙 Back to Branches", callback_data=f"back_branches:{session_id}"))
    if "repos" in session:
        markup.add(InlineKeyboardButton(text="🔙 Back to Repos", callback_data=f"back_repos:{session_id}"))

    bot.send_message(
        chat_id,
        f"✅ Download complete: <code>{html.escape(owner)}/{html.escape(repo)}</code> [<code>{html.escape(branch)}</code>]",
        reply_markup=markup,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("details:"))
def handle_show_details(call):
    _, session_id, idx_str = call.data.split(":")
    session = user_sessions.get(session_id)
    if not session:
        bot.answer_callback_query(call.id, "⚠️ Session expired.", show_alert=True)
        return

    owner = session["owner"]
    repo = session["repo"]
    branch = session["branches"][int(idx_str)]

    bot.answer_callback_query(call.id, "Fetching details...")

    repo_res = github_request(f"https://api.github.com/repos/{owner}/{repo}", call.message.chat.id)
    commit_res = github_request(f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}", call.message.chat.id)

    details_text = f"📊 <b>Repository & Commit Details</b>\n"
    details_text += f"━━━━━━━━━━━━━━━━━━━\n"
    details_text += f"📂 <b>Repo:</b> <code>{html.escape(owner)}/{html.escape(repo)}</code>\n"
    details_text += f"🌿 <b>Branch:</b> <code>{html.escape(branch)}</code>\n\n"

    if repo_res.status_code == 200:
        rdata = repo_res.json()
        stars = rdata.get("stargazers_count", 0)
        forks = rdata.get("forks_count", 0)
        issues = rdata.get("open_issues_count", 0)
        lang = html.escape(rdata.get("language") or "N/A")
        
        raw_license = rdata.get("license", {})
        license_name = html.escape(raw_license.get("name") if raw_license else "None")

        details_text += f"⭐ <b>Stars:</b> {stars} | 🍴 <b>Forks:</b> {forks}\n"
        details_text += f"🔤 <b>Language:</b> {lang}\n"
        details_text += f"🐛 <b>Open Issues:</b> {issues}\n"
        details_text += f"📜 <b>License:</b> {license_name}\n"
        details_text += f"━━━━━━━━━━━━━━━━━━━\n\n"

    if commit_res.status_code == 200:
        cdata = commit_res.json()
        sha = html.escape(cdata.get("sha", "")[:7])
        
        # 1. Truncate long commit messages (max 1500 chars) before HTML escaping
        raw_msg = cdata.get("commit", {}).get("message", "No message").strip()
        if len(raw_msg) > 1500:
            raw_msg = raw_msg[:1500] + "... (truncated)"
        commit_msg = html.escape(raw_msg)
        
        raw_author = cdata.get("commit", {}).get("author", {}).get("name", "Unknown")
        author = html.escape(raw_author)
        
        date_str = html.escape(cdata.get("commit", {}).get("author", {}).get("date", "")[:10])

        details_text += f"📝 <b>Last Commit Info:</b>\n"
        details_text += f"• <b>SHA:</b> <code>{sha}</code>\n"
        details_text += f"• <b>Author:</b> {author}\n"
        details_text += f"• <b>Date:</b> {date_str}\n"
        details_text += f"• <b>Message:</b>\n<code>{commit_msg}</code>\n"
    else:
        details_text += "⚠️ Unable to fetch last commit info."

    # 2. Safety Guard: Enforce total text length limit under Telegram's 4,096 threshold
    if len(details_text) > MAX_MESSAGE_LENGTH:
        details_text = details_text[:MAX_MESSAGE_LENGTH - 100] + "\n\n<i>... [Details truncated due to message length]</i>"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🔙 Back to Branches", callback_data=f"back_branches:{session_id}"))
    if "repos" in session:
        markup.add(InlineKeyboardButton(text="🔙 Back to Repos", callback_data=f"back_repos:{session_id}"))

    bot.send_message(call.message.chat.id, details_text, reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith("back_branches:"))
def handle_back_to_branches(call):
    _, session_id = call.data.split(":")
    session = user_sessions.get(session_id)
    if not session:
        bot.answer_callback_query(call.id, "⚠️ Session expired.", show_alert=True)
        return

    safe_delete_message(call.message.chat.id, call.message.message_id)
    fetch_and_show_branches(call.message.chat.id, session_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("back_repos:"))
def handle_back_to_repos(call):
    _, session_id = call.data.split(":")
    session = user_sessions.get(session_id)
    if not session or "owner" not in session:
        bot.answer_callback_query(call.id, "⚠️ Session expired.", show_alert=True)
        return

    owner = session["owner"]
    fetch_and_show_user_repos(call.message.chat.id, owner, message_id=call.message.message_id)


if __name__ == "__main__":
    print("Verifying Telegram Bot Token...")
    try:
        bot_info = bot.get_me()
        print(f"Bot connected successfully as @{bot_info.username}")
        bot.infinity_polling(skip_pending=True)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 401:
            print("\n❌ ERROR: Invalid Telegram Bot Token!\n")
        else:
            print(f"\n❌ Telegram API Error: {e}\n")

