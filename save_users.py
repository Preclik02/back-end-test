import os
import json
from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

# =========================
# ENV VARIABLES
# =========================
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

FILE = "users.json"


# =========================
# STORAGE
# =========================
def load_data():
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)


# =========================
# WEBHOOK
# =========================
def send_webhook(content):
    if not WEBHOOK_URL:
        return

    try:
        requests.post(WEBHOOK_URL, json={
            "content": content
        })
    except Exception as e:
        print("Webhook error:", e)


# =========================
# HOME ROUTE
# =========================
@app.route("/")
def home():
    return "Bot OAuth backend is running"


# =========================
# OAUTH CALLBACK
# =========================
@app.route("/callback")
def callback():
    if request.method != "GET":
        return "", 200
    code = request.args.get("code")

    if not code:
        return "Missing code", 400

    # exchange code → token
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data=data,
        headers=headers
    ).json()

    access_token = token_res.get("access_token")

    if not access_token:
        return f"Token error: {token_res}", 400

    # get user info
    user = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    user_id = user["id"]
    username = f"{user.get('username')}#{user.get('discriminator')}"

    # store token (lokálně pro bot funkci)
    db = load_data()
    db[user_id] = {
        "access_token": access_token
    }
    save_data(db)

    # send webhook (SAFE DATA ONLY)
    send_webhook(
        f"✅ New authorization\n"
        f"User: {username}\n"
        f"ID: {user_id}\n"
        f"Time: {datetime.utcnow()} UTC\n"
    )

    return f"User {username} authorized successfully"


# =========================
# ADD USER TO GUILD
# =========================
@app.route("/add/<user_id>")
def add_user(user_id):
    db = load_data()

    if user_id not in db:
        return "User not authorized yet", 400

    access_token = db[user_id]["access_token"]

    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}"

    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    r = requests.put(url, headers=headers, json={
        "access_token": access_token
    })

    # webhook log
    send_webhook(f"➕ Attempted to add user {user_id} → Response: {r.status_code}")

    return r.text


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
