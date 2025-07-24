import time, json
import socketio

BOT_ID = "bot-001"
C2_URL = "http://localhost:5000"

sio = socketio.Client()
sio.connect(C2_URL)

@sio.on('connect')
def connected():
    print("[+] Connected to C2")
    sio.emit('register_bot', {'bot_id': BOT_ID})

@sio.on(f'command_{BOT_ID}')
def handle_command(data):
    user_id = data['user_id']
    message = data['message']
    print(f"[+] Sending message to {user_id}: {message}")
    # This is where you'd integrate Selenium logic to send the message
    time.sleep(1)  # Simulate delay
    sio.emit('incoming_message', {
        'bot_id': BOT_ID,
        'user_id': user_id,
        'message': f"[auto-reply] sent: {message}"
    })

while True:
    time.sleep(10)  # Idle
