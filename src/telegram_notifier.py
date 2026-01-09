"""Telegram bot notifications"""

import asyncio
from datetime import datetime

import aiohttp

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED
from src.logger import logger


class TelegramNotifier:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.enabled = TELEGRAM_ENABLED and bool(self.bot_token) and bool(self.chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

        if not self.enabled:
            logger.info("Telegram notifications disabled")
        else:
            logger.info(f"Telegram notifications enabled for chat {self.chat_id}")

    async def send_alert(self, alert: dict):
        """Send alert to Telegram chat"""
        if not self.enabled:
            return

        try:
            score = alert["suspicion_score"]

            # Emoji based on severity
            if score >= 9:
                emoji = "🚨"
                severity = "CRITICAL"
            elif score >= 7:
                emoji = "⚠️"
                severity = "WARNING"
            else:
                emoji = "ℹ️"
                severity = "INFO"

            # Format wallet address
            wallet = alert["wallet"]
            wallet_short = f"{wallet[:6]}...{wallet[-4:]}"

            # Get market category
            category = alert.get("category", "Unknown")

            # Format timestamp
            timestamp = alert.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except:
                    time_str = timestamp
            else:
                time_str = "Unknown"

            # Format message with HTML
            message = f"""<b>{emoji} {severity}: Suspicious Activity Detected</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>📊 SUSPICION SCORE: {score:.1f}/10</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🎯 MARKET INFO</b>
• <b>Title:</b> {alert['market_title'][:100]}
• <b>Category:</b> {category}
• <b>Current Price:</b> ${alert.get('current_price', 'N/A')}

<b>📈 TRADE DETAILS</b>
• <b>Side:</b> {alert['trade']['side']}
• <b>Size:</b> {alert['trade']['size']}
• <b>Price:</b> ${alert['trade']['price']}
• <b>Value:</b> <b>${alert['trade']['value_usd']:,.2f}</b>
• <b>Time:</b> {time_str}

<b>💰 WALLET INFO</b>
• <b>Address:</b> <code>{wallet}</code>
• <b>Age:</b> {alert['wallet_stats']['age_days']:.1f} days old
• <b>Total Trades:</b> {alert['wallet_stats']['total_trades']}
• <b>Unique Markets:</b> {alert['wallet_stats']['unique_markets']}
• <b>Avg Bet:</b> ${alert['wallet_stats']['avg_bet_size']:,.2f}

<b>🚩 RED FLAGS</b>
"""
            # Add all red flags (not just top 3)
            for i, reason in enumerate(alert["reasons"], 1):
                message += f"{i}. {reason}\n"

            # Add links
            market_url = f"https://polymarket.com/event/{alert['market_slug']}"
            polygonscan_url = f"https://polygonscan.com/address/{wallet}"

            message += f'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            message += f'🔗 <a href="{market_url}">View Market</a> | '
            message += f'🔍 <a href="{polygonscan_url}">View Wallet on PolygonScan</a>'

            # Send message via Telegram API
            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                }

                async with session.post(
                    f"{self.api_url}/sendMessage", json=payload
                ) as response:
                    if response.status == 200:
                        logger.debug("Alert sent to Telegram")
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to send Telegram alert: {response.status} - {error_text}"
                        )

        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    async def test_connection(self):
        """Test Telegram bot connection"""
        if not self.enabled:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/getMe") as response:
                    if response.status == 200:
                        data = await response.json()
                        bot_name = data["result"]["username"]
                        logger.info(f"✅ Telegram bot connected: @{bot_name}")
                        return True
                    else:
                        logger.error(f"Failed to connect to Telegram: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error testing Telegram connection: {e}")
            return False
