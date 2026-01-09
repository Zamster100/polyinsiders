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
            wallet_short = f"{wallet[:8]}...{wallet[-6:]}"

            # Format message with HTML
            message = f"""<b>{emoji} {severity}: Suspicious Activity Detected</b>

<b>📊 Score:</b> {score:.1f}/10
<b>💰 Wallet:</b> <code>{wallet_short}</code>
<b>🎯 Market:</b> {alert['market_title']}

<b>📈 Trade Details:</b>
• Side: {alert['trade']['side']}
• Size: {alert['trade']['size']}
• Price: ${alert['trade']['price']}
• Value: ${alert['trade']['value_usd']:.2f}

<b>👤 Wallet Statistics:</b>
• Age: {alert['wallet_stats']['age_days']:.1f} days
• Total Trades: {alert['wallet_stats']['total_trades']}
• Unique Markets: {alert['wallet_stats']['unique_markets']}
• Avg Bet Size: ${alert['wallet_stats']['avg_bet_size']:.2f}

<b>🚩 Red Flags:</b>
"""
            # Add top 3 red flags
            for i, reason in enumerate(alert["reasons"][:3], 1):
                message += f"{i}. {reason}\n"

            # Add link
            market_url = f"https://polymarket.com/event/{alert['market_slug']}"
            message += f'\n<a href="{market_url}">View on Polymarket</a>'

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
