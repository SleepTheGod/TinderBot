from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread
import json
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Logging
logging.basicConfig(level=logging.INFO)

# SQLite DB init
def init_db():
    try:
        conn = sqlite3.connect('chats.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS chats 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      user_id TEXT, 
                      message TEXT, 
                      timestamp TEXT)''')
        conn.commit()
        conn.close()
        logging.info("Database initialized.")
    except Exception as e:
        logging.error(f"DB init error: {e}")

init_db()

IPHONE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)

def setup_driver():
    options = Options()
    options.add_argument(f"user-agent={IPHONE_USER_AGENT}")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def simulate_tinder_login(driver, phone_number, otp_code):
    try:
        driver.get("https://tinder.com")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in')]"))
        ).click()
        phone_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='tel']"))
        )
        phone_input.send_keys(phone_number)
        time.sleep(2)
        otp_input = driver.find_element(By.XPATH, "//input[@placeholder='Enter code']")
        otp_input.send_keys(otp_code)
        driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]").click()

        with open('login.json', 'w') as f:
            json.dump({'phone_number': phone_number, 'otp_code': otp_code}, f)
        return True
    except Exception as e:
        logging.error(f"Login failed: {e}")
        return False

def auto_respond(message):
    return f"Thanks for your message: '{message}'! I'm excited to chat!"

def save_chat(user_id, message):
    try:
        conn = sqlite3.connect('chats.db')
        c = conn.cursor()
        c.execute("INSERT INTO chats (user_id, message, timestamp) VALUES (?, ?, ?)",
                  (user_id, message, time.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Chat save error: {e}")

def monitor_chats():
    while True:
        mock_msg = {"user_id": "mock_user", "message": "Hey, how's it going?"}
        save_chat(mock_msg['user_id'], mock_msg['message'])
        socketio.emit('new_message', mock_msg)
        time.sleep(10)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    phone_number = request.form.get('phone_number')
    otp_code = request.form.get('otp_code')
    driver = setup_driver()
    success = simulate_tinder_login(driver, phone_number, otp_code)
    driver.quit()
    return jsonify({'status': 'success' if success else 'failed'})

@app.route('/chats')
def get_chats():
    try:
        conn = sqlite3.connect('chats.db')
        c = conn.cursor()
        c.execute("SELECT user_id, message, timestamp FROM chats ORDER BY timestamp DESC")
        rows = c.fetchall()
        conn.close()
        return jsonify([{'user_id': u, 'message': m, 'timestamp': t} for u, m, t in rows])
    except Exception as e:
        logging.error(f"/chats error: {e}")
        return jsonify({'error': 'Chat retrieval failed'}), 500

@socketio.on('send_message')
def handle_message(data):
    user_id = data.get('user_id', 'anonymous')
    message = data.get('message', '')
    bot_reply = auto_respond(message)

    save_chat(user_id, message)
    save_chat('bot', bot_reply)

    emit('new_message', {'user_id': user_id, 'message': message}, broadcast=True)
    emit('new_message', {'user_id': 'bot', 'message': bot_reply}, broadcast=True)

if __name__ == '__main__':
    Thread(target=monitor_chats, daemon=True).start()
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
