import os
from flask import Flask, request, jsonify
import sqlite3
import uuid

app = Flask(__name__)
DB_NAME = "central_quota.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (tg_id TEXT PRIMARY KEY, uuid TEXT, email TEXT, allowed_bytes REAL, consumed_bytes REAL DEFAULT 0, status TEXT DEFAULT 'Active')''')
    conn.commit()
    conn.close()

@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json
    tg_id = str(data.get("tg_id"))
    gb_amount = float(data.get("gb", 1))
    bytes_allowed = gb_amount * 1024 * 1024 * 1024
    
    user_uuid = str(uuid.uuid4())
    email = f"user_{tg_id}@chrome"
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("REPLACE INTO users (tg_id, uuid, email, allowed_bytes, consumed_bytes, status) VALUES (?, ?, ?, ?, 0, 'Active')", 
              (tg_id, user_uuid, email, bytes_allowed))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "uuid": user_uuid, "email": email, "msg": f"تم إضافة {gb_amount} جيجا"})

@app.route('/sync_usage', methods=['POST'])
def sync_usage():
    data = request.json
    email = data.get("email")
    local_bytes = float(data.get("bytes", 0))
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET consumed_bytes = ? WHERE email = ?", (local_bytes, email))
    c.execute("SELECT allowed_bytes, consumed_bytes, uuid FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    
    response = {"status": "Active"}
    if row:
        allowed, consumed, u_uuid = row
        if consumed >= allowed:
            c.execute("UPDATE users SET status = 'Blocked' WHERE email = ?", (email,))
            response = {"status": "block"}
    conn.commit()
    conn.close()
    return jsonify(response)

@app.route('/get_active_users', methods=['GET'])
def get_active_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT uuid, email FROM users WHERE status = 'Active'")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"uuid": r[0], "email": r[1]} for r in rows])

# تهيئة قاعدة البيانات عند إقلاع السيرفر تلقائياً
init_db()

if __name__ == '__main__':
    # راندر يحقن بورت عشوائي في البيئة ولازم السكربت يتبعو
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
