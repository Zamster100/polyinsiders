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

    async def send_orderbook_alert(self, alert: dict):
        """Send orderbook anomaly alert to Telegram"""
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

            ob_details = alert.get("orderbook_details", {})

            # Format message with HTML
            message = f"""<b>{emoji} {severity}: Orderbook Anomaly Detected</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>📊 SUSPICION SCORE: {score:.1f}/10</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🎯 MARKET INFO</b>
• <b>Title:</b> {alert['market_title'][:100]}
• <b>Category:</b> {category}
• <b>Time:</b> {time_str}

<b>📚 ORDERBOOK STATS</b>
• <b>Total Volume:</b> ${ob_details.get('total_volume', 0):,.2f}
• <b>Bid Volume:</b> ${ob_details.get('total_bid_size', 0):,.2f}
• <b>Ask Volume:</b> ${ob_details.get('total_ask_size', 0):,.2f}
"""

            # Add imbalance if present
            imbalance = ob_details.get('imbalance', 0)
            if imbalance != 0:
                direction = "Bullish" if imbalance > 0 else "Bearish"
                message += f"• <b>Imbalance:</b> {abs(imbalance)*100:.1f}% {direction}\n"

            # Add spread if present
            spread = ob_details.get('spread', 0)
            if spread > 0:
                message += f"• <b>Spread:</b> ${spread:.4f}\n"

            # Add large orders if present
            large_orders = ob_details.get('large_orders', [])
            if large_orders:
                message += "\n<b>🐋 LARGE ORDERS</b>\n"
                for order in large_orders[:3]:  # Top 3
                    side, size, price, value = order
                    message += f"• {side}: {size:,.0f} @ ${price:.2f} = <b>${value:,.2f}</b>\n"

            # Add AI analysis if available
            ai_reasoning = alert.get('ai_reasoning', '')
            risk_level = alert.get('risk_level', 'MEDIUM')
            if ai_reasoning:
                message += f"\n<b>🤖 AI ANALYSIS ({risk_level} RISK)</b>\n"
                message += f"{ai_reasoning}\n"

            # Add wallet profiles if available
            wallet_profiles = alert.get('wallet_profiles', [])
            if wallet_profiles:
                message += "\n<b>👤 SUSPECTED INSIDERS</b>\n"
                for i, profile in enumerate(wallet_profiles[:3], 1):  # Top 3 wallets
                    wallet = profile['wallet']
                    wallet_short = f"{wallet[:8]}...{wallet[-6:]}"
                    total_value = profile.get('total_value', 0)
                    trade_count = profile.get('trade_count', 0)

                    message += f"\n{i}. <code>{wallet_short}</code>\n"
                    message += f"   • Total: ${total_value:,.2f} ({trade_count} trades)\n"

                    polygonscan_url = f"https://polygonscan.com/address/{wallet}"
                    message += f'   • <a href="{polygonscan_url}">View on PolygonScan</a>\n'

            # Add detection signals
            message += "\n<b>🚩 DETECTION SIGNALS</b>\n"
            for i, reason in enumerate(alert["reasons"], 1):
                message += f"{i}. {reason}\n"

            # Add links
            market_url = f"https://polymarket.com/event/{alert['market_slug']}"

            message += f'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            message += f'🔗 <a href="{market_url}">View Market on Polymarket</a>'

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
                        logger.debug("Orderbook alert sent to Telegram")
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to send Telegram orderbook alert: {response.status} - {error_text}"
                        )

        except Exception as e:
            logger.error(f"Error sending Telegram orderbook notification: {e}")

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
