import os
import json
from flask import Flask, request
import requests

app = Flask(__name__)

# =========================
# ENV VARIABLES (Render)
# =========================
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

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

    # store token
    db = load_data()
    db[user_id] = {
        "access_token": access_token
    }
    save_data(db)

    return f"User {user.get('username')} authorized successfully"


# =========================
# ADD USER TO GUILD (LATER)
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

    return r.text


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
