from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running! 🤖"

@app.route('/status')
def status():
    return {
        "status": "active",
        "message": "Telegram bot is running successfully"
    }

@app.route('/health')
def health():
    return "OK", 200

def run():
    """تشغيل خادم Flask في خيط منفصل"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    """بدء خادم Flask في خيط منفصل لضمان بقاء البوت نشطًا"""
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()
    print(f"Keep-alive server started on port {os.environ.get('PORT', 10000)}")

