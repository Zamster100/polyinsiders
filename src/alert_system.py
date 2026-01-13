"""Alert system with SQLite and Slack integration"""

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.database import Database
from src.logger import logger
from src.slack_notifier import SlackNotifier
from src.telegram_notifier import TelegramNotifier

console = Console()


class AlertSystem:
    def __init__(self, db: Database):
        self.db = db
        self.slack = SlackNotifier()
        self.telegram = TelegramNotifier()

    async def create_alert(
        self,
        wallet: str,
        market: dict,
        trade: dict,
        score: float,
        reasons: list[str],
        wallet_stats: dict,
    ) -> dict:
        """Create a new alert"""
        # Determine category (default to Politics for now)
        category = "Politics"  # Since we're tracking tag_id 2

        alert = {
            "timestamp": datetime.now().isoformat(),
            "wallet": wallet,
            "market_title": market.get("question", "Unknown"),
            "market_slug": market.get("slug", "") or market.get("event_slug", ""),
            "condition_id": market.get("conditionId", ""),  # Fixed: API uses camelCase
            "category": category,
            "trade": {
                "size": trade.get("size"),
                "price": trade.get("price"),
                "side": trade.get("side"),
                "value_usd": float(trade.get("size", 0)) * float(trade.get("price", 0)),
            },
            "suspicion_score": score,
            "reasons": reasons,
            "wallet_stats": {
                "age_days": wallet_stats.get("age_days"),
                "total_trades": wallet_stats.get("total_trades"),
                "unique_markets": wallet_stats.get("unique_markets"),
                "avg_bet_size": wallet_stats.get("avg_bet_size"),
            },
            "current_price": market.get("price", "Unknown"),
        }

        await self.db.save_alert(alert)
        await self.slack.send_alert(alert)
        await self.telegram.send_alert(alert)
        logger.info(f"Alert created: {wallet[:10]}... score {score:.1f}/10")
        return alert

    async def create_orderbook_alert(
        self,
        market: dict,
        token_id: str,
        score: float,
        reasons: list[str],
        details: dict,
        wallet_profiles: list[dict] = None,
        ai_reasoning: str = "",
        risk_level: str = "MEDIUM",
    ) -> dict:
        """Create an alert for orderbook anomalies"""
        category = "Politics"  # Since we're tracking tag_id 2

        alert = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": "orderbook",
            "market_title": market.get("question", "Unknown"),
            "market_slug": market.get("slug", "") or market.get("event_slug", ""),
            "condition_id": market.get("conditionId", ""),
            "token_id": token_id,
            "category": category,
            "suspicion_score": score,
            "reasons": reasons,
            "orderbook_details": {
                "total_bid_size": details.get("total_bid_size", 0),
                "total_ask_size": details.get("total_ask_size", 0),
                "total_volume": details.get("total_volume", 0),
                "imbalance": details.get("imbalance", 0),
                "best_bid": details.get("best_bid", 0),
                "best_ask": details.get("best_ask", 0),
                "spread": details.get("spread", 0),
                "large_orders": details.get("large_orders", []),
            },
            "current_price": market.get("price", "Unknown"),
            "wallet_profiles": wallet_profiles or [],
            "ai_reasoning": ai_reasoning,
            "risk_level": risk_level,
        }

        await self.db.save_alert(alert)
        # Skip Slack for orderbook alerts (Slack notifier expects wallet field)
        # await self.slack.send_alert(alert)
        await self.telegram.send_orderbook_alert(alert)
        logger.info(f"Orderbook alert created: {market.get('question', '')[:40]}... score {score:.1f}/10")
        return alert

    def print_alert(self, alert: dict):
        """Print alert to console with rich formatting"""
        score = alert["suspicion_score"]

        if score >= 9:
            color = "red"
            emoji = "🚨"
        elif score >= 7:
            color = "yellow"
            emoji = "⚠️"
        else:
            color = "blue"
            emoji = "ℹ️"

        # Check if this is an orderbook alert
        if alert.get("alert_type") == "orderbook":
            title = Text()
            title.append(f"{emoji} ORDERBOOK ANOMALY ", style=f"bold {color}")
            title.append(f"(Score: {score:.1f}/10)", style="bold white")

            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column(style="cyan", width=20)
            table.add_column(style="white")

            table.add_row("Market", alert["market_title"][:60])
            ob_details = alert.get("orderbook_details", {})

            table.add_row("", "")
            table.add_row("[bold]Orderbook Stats[/bold]", "")
            table.add_row("  Total Volume", f"${ob_details.get('total_volume', 0):,.2f}")
            table.add_row("  Bid Volume", f"${ob_details.get('total_bid_size', 0):,.2f}")
            table.add_row("  Ask Volume", f"${ob_details.get('total_ask_size', 0):,.2f}")

            imbalance = ob_details.get('imbalance', 0)
            if imbalance != 0:
                table.add_row("  Imbalance", f"{imbalance*100:.1f}%")

            spread = ob_details.get('spread', 0)
            if spread > 0:
                table.add_row("  Spread", f"${spread:.4f}")

            # Show large orders if present
            large_orders = ob_details.get('large_orders', [])
            if large_orders:
                table.add_row("", "")
                table.add_row("[bold]Large Orders[/bold]", "")
                for order in large_orders[:3]:  # Show top 3
                    side, size, price, value = order
                    table.add_row(f"  {side}", f"{size:,.0f} @ ${price:.2f} = [green]${value:,.2f}[/green]")

            table.add_row("", "")
            table.add_row("[bold]Detection Signals[/bold]", "")
            for i, reason in enumerate(alert["reasons"], 1):
                table.add_row(f"  {i}.", reason)

            table.add_row("", "")
            table.add_row("Link", f"https://polymarket.com/event/{alert['market_slug']}")

            panel = Panel(table, title=title, border_style=color, expand=False)
            console.print(panel)
            console.print()
        else:
            # Original wallet-based alert
            title = Text()
            title.append(f"{emoji} SUSPICIOUS ACTIVITY ", style=f"bold {color}")
            title.append(f"(Score: {score:.1f}/10)", style="bold white")

            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column(style="cyan", width=20)
            table.add_column(style="white")

            table.add_row("Market", alert["market_title"][:60])
            table.add_row("Wallet", f"{alert['wallet'][:12]}...{alert['wallet'][-10:]}")
            table.add_row(
                "Trade",
                f"{alert['trade']['side']} {alert['trade']['size']} @ ${alert['trade']['price']} = [green]${alert['trade']['value_usd']:.2f}[/green]",
            )
            table.add_row("Current Price", str(alert["current_price"]))

            table.add_row("", "")
            table.add_row("[bold]Wallet Stats[/bold]", "")
            table.add_row("  Age", f"{alert['wallet_stats']['age_days']:.1f} days")
            table.add_row("  Total Trades", str(alert["wallet_stats"]["total_trades"]))
            table.add_row("  Unique Markets", str(alert["wallet_stats"]["unique_markets"]))
            table.add_row("  Avg Bet Size", f"${alert['wallet_stats']['avg_bet_size']:.2f}")

            table.add_row("", "")
            table.add_row("[bold]Red Flags[/bold]", "")
            for i, reason in enumerate(alert["reasons"], 1):
                table.add_row(f"  {i}.", reason)

            table.add_row("", "")
            table.add_row("Link", f"https://polymarket.com/event/{alert['market_slug']}")

            panel = Panel(table, title=title, border_style=color, expand=False)
            console.print(panel)
            console.print()

    async def get_recent_alerts(self, hours: int = 24) -> list[dict]:
        """Get alerts from last N hours"""
        return await self.db.get_recent_alerts(hours)

    async def get_alert_stats(self) -> dict:
        """Get statistics about alerts"""
        return await self.db.get_alert_stats()

    async def print_stats_table(self):
        """Print beautiful stats table"""
        stats = await self.get_alert_stats()

        table = Table(title="📊 Alert Statistics", show_header=True)
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="white", justify="right")

        table.add_row("Total Alerts", str(stats.get("total_alerts", 0)))
        table.add_row("Alerts (24h)", f"[yellow]{stats.get('recent_24h', 0)}[/yellow]")
        table.add_row("Avg Score", f"{stats.get('avg_score', 0):.2f}/10")
        table.add_row("Unique Wallets Flagged", str(stats.get("unique_wallets", 0)))

        if stats.get("most_flagged_wallet"):
            wallet = stats["most_flagged_wallet"]
            table.add_row("Most Flagged Wallet", f"{wallet[:12]}...{wallet[-10:]}")

        console.print(table)
