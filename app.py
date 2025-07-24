from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3, time, json, logging
from threading import Thread

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tinder-c2-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Logging setup
logging.basicConfig(level=logging.INFO)

# Database init
def init_db():
    conn = sqlite3.connect('db/chats.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id TEXT,
            user_id TEXT,
            message TEXT,
            direction TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Save message to DB
def save_message(bot_id, user_id, message, direction):
    conn = sqlite3.connect('db/chats.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO chats (bot_id, user_id, message, direction, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (bot_id, user_id, message, direction, time.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chats')
def chats():
    conn = sqlite3.connect('db/chats.db')
    cur = conn.cursor()
    cur.execute('SELECT bot_id, user_id, message, direction, timestamp FROM chats ORDER BY id DESC LIMIT 100')
    data = cur.fetchall()
    conn.close()
    return jsonify([{
        'bot_id': row[0], 'user_id': row[1], 'message': row[2],
        'direction': row[3], 'timestamp': row[4]
    } for row in data])

# SocketIO Event Handlers
@socketio.on('register_bot')
def register_bot(data):
    bot_id = data.get('bot_id')
    logging.info(f"[+] Bot registered: {bot_id}")
    emit('bot_registered', {'status': 'ok', 'bot_id': bot_id}, broadcast=True)

@socketio.on('incoming_message')
def handle_incoming(data):
    bot_id = data['bot_id']
    user_id = data['user_id']
    message = data['message']
    save_message(bot_id, user_id, message, 'inbound')
    emit('new_message', {
        'bot_id': bot_id,
        'user_id': user_id,
        'message': message,
        'direction': 'inbound'
    }, broadcast=True)

@socketio.on('send_command')
def send_command(data):
    bot_id = data['bot_id']
    user_id = data['user_id']
    message = data['message']
    save_message(bot_id, user_id, message, 'outbound')
    emit(f'command_{bot_id}', {
        'user_id': user_id,
        'message': message
    }, broadcast=True)
    logging.info(f"[+] Command sent to {bot_id} -> {user_id}: {message}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
