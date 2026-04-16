import os
import json
import threading
from flask import Flask, request, send_file
import requests
from datetime import datetime

app = Flask(__name__)

# =========================
# ENV
# =========================
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_KEY = os.getenv("ADMIN_KEY")

FILE = "users.json"

lock = threading.Lock()
used_codes = set()


# =========================
# STORAGE
# =========================
def load_data():
    if not os.path.exists(FILE):
        return {}
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with lock:
        with open(FILE, "w") as f:
            json.dump(data, f, indent=2)


# =========================
# WEBHOOK (SAFE)
# =========================
def send_webhook(content):
    if not WEBHOOK_URL:
        return
    try:
        requests.post(WEBHOOK_URL, json={"content": content})
    except:
        pass


# =========================
# HOME
# =========================
@app.route("/")
def home():
    return "OAuth backend running"


# =========================
# ADMIN PANEL (VIEW DATA)
# =========================
@app.route("/admin/<key>")
def admin_panel(key):
    if key != ADMIN_KEY:
        return "Unauthorized", 403

    data = load_data()

    return {
        "count": len(data),
        "users": data
    }


# =========================
# DOWNLOAD DATABASE
# =========================
@app.route("/admin/<key>/download")
def download_db(key):
    if key != ADMIN_KEY:
        return "Unauthorized", 403

    if not os.path.exists(FILE):
        return "No database file", 404

    return send_file(FILE, as_attachment=True)


# =========================
# OAUTH CALLBACK
# =========================
@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "Missing code", 400

    # prevent reuse (fix rate limit spam)
    if code in used_codes:
        return "Code already used", 429

    used_codes.add(code)

    # exchange code → token
    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    token_data = token_res.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return f"Token error: {token_data}", 400

    # get user info
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    user = user_res.json()

    user_id = user["id"]
    username = f"{user.get('username')}#{user.get('discriminator')}"

    # store user
    db = load_data()
    db[user_id] = {
        "access_token": access_token,
        "time": str(datetime.utcnow())
    }
    save_data(db)

    # webhook log (NO TOKEN)
    send_webhook(
        f"New OAuth user\n"
        f"User: {username}\n"
        f"ID: {user_id}\n"
        f"Total users: {len(db)}"
    )

    return f"User {username} authorized successfully"


# =========================
# ADD USER TO GUILD
# =========================
@app.route("/add/<user_id>")
def add_user(user_id):
    db = load_data()

    if user_id not in db:
        return "User not authorized", 400

    access_token = db[user_id]["access_token"]

    r = requests.put(
        f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}",
        headers={
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"access_token": access_token}
    )

    send_webhook(f"Add user {user_id} -> {r.status_code}")

    return r.text


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
