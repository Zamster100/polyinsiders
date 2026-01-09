"""Test Telegram bot connection"""
import asyncio
import aiohttp
import sys

BOT_TOKEN = "8546791791:AAE4oIuX7FR2Zx2v8i5TxaCI3gxfuIzxDEk"
CHAT_ID = "399191729"

async def test_telegram():
    """Send a test message to verify Telegram is working"""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

    print("Testing Telegram connection...")

    # Test 1: Check bot info
    print("\n1. Checking bot info...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{api_url}/getMe") as response:
            if response.status == 200:
                data = await response.json()
                bot_name = data["result"]["username"]
                print(f"   ✅ Bot connected: @{bot_name}")
            else:
                print(f"   ❌ Failed to connect: {response.status}")
                return False

    # Test 2: Send test message
    print("\n2. Sending test message...")
    async with aiohttp.ClientSession() as session:
        message = """🤖 <b>Polymarket Insider Tracker - Test Message</b>

✅ Your bot is working correctly!
✅ Notifications are configured properly.

The bot will send alerts here when suspicious trading activity is detected.

<b>Current Settings:</b>
• Minimum bet: $1,000
• Alert threshold: 7.0/10
• Scan interval: 60 seconds"""

        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }

        async with session.post(f"{api_url}/sendMessage", json=payload) as response:
            if response.status == 200:
                print(f"   ✅ Test message sent successfully!")
                print(f"   📱 Check your Telegram chat (ID: {CHAT_ID})")
                return True
            else:
                error_text = await response.text()
                print(f"   ❌ Failed to send message: {response.status}")
                print(f"   Error: {error_text}")
                return False

if __name__ == "__main__":
    result = asyncio.run(test_telegram())
    if result:
        print("\n✅ SUCCESS! Your Telegram bot is ready.")
        print("The main bot will send alerts to this chat when it detects suspicious activity.")
    else:
        print("\n❌ FAILED! Check your bot token and chat ID.")

    sys.exit(0 if result else 1)
