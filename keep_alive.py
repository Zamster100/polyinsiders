"""Simple web server to keep Replit alive"""
from flask import Flask
from threading import Thread
import os

app = Flask('')


@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Polymarket Insider Tracker</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #1a1a1a;
                    color: #fff;
                }
                h1 { color: #4CAF50; }
                .status {
                    background: #2d2d2d;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                .online { color: #4CAF50; }
            </style>
        </head>
        <body>
            <h1>🚨 Polymarket Insider Tracker</h1>
            <div class="status">
                <h2>Status: <span class="online">● ONLINE</span></h2>
                <p>The bot is actively monitoring Polymarket for suspicious trading activity.</p>
                <p>Alerts are being sent to your configured Telegram chat.</p>
            </div>
            <div class="status">
                <h3>📊 Features</h3>
                <ul>
                    <li>Fresh wallet detection (< 30 days)</li>
                    <li>Oversized position tracking (> 3x average)</li>
                    <li>Off-hours trading detection (2-5 AM UTC)</li>
                    <li>Market concentration analysis</li>
                    <li>Low-liquidity market alerts</li>
                    <li>Real-time Telegram notifications</li>
                </ul>
            </div>
        </body>
    </html>
    """


@app.route('/health')
def health():
    return {"status": "online", "service": "polymarket-insider-tracker"}


def run():
    """Run Flask server"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


def keep_alive():
    """Start the web server in a separate thread"""
    t = Thread(target=run)
    t.daemon = True
    t.start()
