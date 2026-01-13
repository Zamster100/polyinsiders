"""Main tracking logic - Optimized async version"""

import asyncio

from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from src.alert_system import AlertSystem
from src.orderbook_anomaly_detector import OrderbookAnomalyDetector
from src.config import (
    CONCURRENT_BATCH_SIZE,
    DATABASE_PATH,
    POLL_INTERVAL,
    SUSPICIOUS_SCORE_THRESHOLD,
    TRACKED_TAG_IDS,
)
from src.database import Database
from src.logger import console, logger
from src.orderbook_api import OrderbookAPI
from src.wallet_tracker import WalletTracker


class InsiderTracker:
    def __init__(self):
        self.db = Database(DATABASE_PATH)
        self.wallet_tracker = WalletTracker(self.db)
        self.orderbook_detector = OrderbookAnomalyDetector()
        self.alert_system = AlertSystem(self.db)
        self.processed_markets = set()  # Track markets we've already alerted on
        self.scan_stats = {
            "markets_scanned": 0,
            "orderbooks_analyzed": 0,
            "alerts_triggered": 0,
            "errors": 0,
        }

    async def initialize(self):
        """Initialize database"""
        await self.db.init_db()

    async def get_all_markets(self, api: OrderbookAPI) -> list[dict]:
        """Fetch all markets we're tracking concurrently"""

        async def fetch_tag(tag_id):
            try:
                events = await api.fetch_active_events(tag_id)
                markets = []
                for event in events:
                    for market in event.get("markets", []):
                        market["event_title"] = event.get("title", "")
                        market["event_slug"] = event.get("slug", "")
                        markets.append(market)
                logger.debug(f"Fetched {len(markets)} markets for tag {tag_id}")
                return markets
            except Exception as e:
                logger.error(f"Error fetching events for tag {tag_id}: {e}")
                self.scan_stats["errors"] += 1
                return []

        results = await asyncio.gather(*[fetch_tag(tag_id) for tag_id in TRACKED_TAG_IDS])
        all_markets = [market for markets in results for market in markets]
        logger.info(
            f"Found {len(all_markets)} total markets across {len(TRACKED_TAG_IDS)} categories"
        )
        return all_markets

    async def analyze_market(self, api: OrderbookAPI, market: dict) -> dict:
        """Analyze a single market's orderbooks for suspicious activity"""
        condition_id = market.get("conditionId")
        if not condition_id:
            return {"alerts": 0, "orderbooks": 0, "with_data": 0, "scores": []}

        alerts_count = 0
        orderbooks_count = 0
        orderbooks_with_data = 0
        scores = []

        try:
            # Fetch orderbooks for all tokens in this market
            orderbooks = await api.fetch_market_orderbooks(market)

            if not orderbooks:
                return {"alerts": 0, "orderbooks": 0, "with_data": 0, "scores": []}

            orderbooks_count = len(orderbooks)

            # Analyze each orderbook
            for orderbook in orderbooks:
                token_id = orderbook.get("token_id", "")

                if not orderbook.get("bids") and not orderbook.get("asks"):
                    continue

                orderbooks_with_data += 1

                # Analyze orderbook for suspicious patterns
                score, reasons, details = self.orderbook_detector.analyze_orderbook(
                    orderbook, market
                )

                scores.append(score)

                # Log if we got a score > 0 for debugging
                if score > 0:
                    logger.debug(
                        f"Market '{market.get('question', '')[:40]}' - "
                        f"Score: {score:.1f}/10, Reasons: {len(reasons)}"
                    )

                # Create alert if score is high enough
                if score >= SUSPICIOUS_SCORE_THRESHOLD:
                    # Create unique key for this market alert to avoid duplicates
                    alert_key = f"{condition_id}_{token_id}"

                    if alert_key not in self.processed_markets:
                        self.processed_markets.add(alert_key)

                        alert = await self.alert_system.create_orderbook_alert(
                            market, token_id, score, reasons, details
                        )
                        self.alert_system.print_alert(alert)
                        alerts_count += 1

        except Exception as e:
            logger.error(f"Error analyzing market {market.get('question', 'unknown')[:40]}: {e}")
            self.scan_stats["errors"] += 1

        return {
            "alerts": alerts_count,
            "orderbooks": orderbooks_count,
            "with_data": orderbooks_with_data,
            "scores": scores,
        }

    async def run_scan(self):
        """Run a single scan of all markets concurrently"""
        from src.config import MIN_BET_SIZE, LARGE_BET_MULTIPLIER

        # Display configuration
        console.print("\n")
        console.print(
            Panel.fit(
                "[bold cyan]📊 Configuration[/bold cyan]\n\n"
                f"[white]Alert Threshold:[/white] [yellow]{SUSPICIOUS_SCORE_THRESHOLD}/10[/yellow]\n"
                f"[white]Min Bet Size:[/white] [yellow]${MIN_BET_SIZE}[/yellow]\n"
                f"[white]Large Order Threshold:[/white] [yellow]>${MIN_BET_SIZE * 5} (5x min)[/yellow]\n"
                f"[white]Very Large Order:[/white] [yellow]>${MIN_BET_SIZE * 10} (10x min)[/yellow]\n"
                f"[white]Tracking:[/white] [yellow]{len(TRACKED_TAG_IDS)} categories[/yellow]\n"
                f"[white]Mode:[/white] [green]Orderbook Monitoring[/green]",
                border_style="cyan",
            )
        )
        console.print()

        logger.info("Starting market scan...")

        self.scan_stats = {
            "markets_scanned": 0,
            "orderbooks_analyzed": 0,
            "alerts_triggered": 0,
            "errors": 0,
            "orderbooks_with_data": 0,
            "scores_calculated": 0,
        }

        async with OrderbookAPI() as api:
            markets = await self.get_all_markets(api)

            if not markets:
                logger.warning("No markets found to scan")
                return

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Scanning {len(markets)} markets...", total=len(markets)
                )

                for i in range(0, len(markets), CONCURRENT_BATCH_SIZE):
                    batch = markets[i : i + CONCURRENT_BATCH_SIZE]

                    results = await asyncio.gather(
                        *[self.analyze_market(api, market) for market in batch],
                        return_exceptions=True,
                    )

                    for result in results:
                        if isinstance(result, dict):
                            self.scan_stats["markets_scanned"] += 1
                            self.scan_stats["orderbooks_analyzed"] += result.get("orderbooks", 0)
                            self.scan_stats["alerts_triggered"] += result.get("alerts", 0)
                            self.scan_stats["orderbooks_with_data"] += result.get("with_data", 0)
                            self.scan_stats["scores_calculated"] += len(result.get("scores", []))

                    progress.update(task, advance=len(batch))

                    if i + CONCURRENT_BATCH_SIZE < len(markets):
                        await asyncio.sleep(0.3)

        logger.info("Scan complete")

        console.print("\n")
        summary_table = Table(title="✅ Scan Complete", show_header=True, header_style="bold green")
        summary_table.add_column("Metric", style="cyan", width=25)
        summary_table.add_column("Value", justify="right", style="white")

        summary_table.add_row(
            "Markets Scanned", f"[green]{self.scan_stats['markets_scanned']}[/green]"
        )
        summary_table.add_row(
            "Orderbooks Analyzed", f"[blue]{self.scan_stats['orderbooks_analyzed']}[/blue]"
        )
        summary_table.add_row(
            "Orderbooks w/ Data", f"[cyan]{self.scan_stats['orderbooks_with_data']}[/cyan]"
        )
        summary_table.add_row(
            "Scores Calculated", f"[magenta]{self.scan_stats['scores_calculated']}[/magenta]"
        )
        summary_table.add_row(
            "New Alerts", f"[yellow]{self.scan_stats['alerts_triggered']}[/yellow]"
        )
        summary_table.add_row("Errors Encountered", f"[red]{self.scan_stats['errors']}[/red]")

        stats = await self.alert_system.get_alert_stats()
        summary_table.add_row("", "")
        summary_table.add_row("Total Alerts (All Time)", str(stats.get("total_alerts", 0)))
        summary_table.add_row("Alerts (Last 24h)", str(stats.get("recent_24h", 0)))
        summary_table.add_row("Unique Flagged Wallets", str(stats.get("unique_wallets", 0)))

        console.print(summary_table)
        console.print()

    async def run_continuous(self):
        """Run continuous monitoring"""
        from src.config import MIN_BET_SIZE, LARGE_BET_MULTIPLIER

        console.print(
            Panel.fit(
                "[bold cyan]🤖 Polymarket Insider Activity Tracker[/bold cyan]\n\n"
                "[bold white]Configuration:[/bold white]\n"
                f"[white]├─ Polling Interval:[/white] [yellow]{POLL_INTERVAL}s[/yellow]\n"
                f"[white]├─ Tracking Categories:[/white] [yellow]{len(TRACKED_TAG_IDS)}[/yellow]\n"
                f"[white]├─ Alert Threshold:[/white] [yellow]{SUSPICIOUS_SCORE_THRESHOLD}/10[/yellow]\n"
                f"[white]├─ Min Bet Size:[/white] [yellow]${MIN_BET_SIZE}[/yellow]\n"
                f"[white]├─ Large Bet Multiplier:[/white] [yellow]{LARGE_BET_MULTIPLIER}x[/yellow]\n"
                f"[white]├─ Concurrent Batch:[/white] [yellow]{CONCURRENT_BATCH_SIZE}[/yellow]\n"
                f"[white]└─ Mode:[/white] [green]Orderbook Monitoring[/green]\n\n"
                "[bold white]Detection Signals:[/bold white]\n"
                f"[white]• Large orders (>{MIN_BET_SIZE * 5})[/white]\n"
                "[white]• Orderbook imbalance (>20%)[/white]\n"
                "[white]• Unusual spreads (<$0.01 or >$0.20)[/white]\n"
                "[white]• Order concentration (>50%)[/white]\n"
                "[white]• Large orders in illiquid markets[/white]\n\n"
                "[dim]Press Ctrl+C to stop[/dim]",
                border_style="cyan",
            )
        )
        console.print()

        try:
            scan_count = 0
            while True:
                scan_count += 1
                logger.info(f"Starting scan #{scan_count}")

                await self.run_scan()

                logger.info(f"Waiting {POLL_INTERVAL}s until next scan...")
                for remaining in range(POLL_INTERVAL, 0, -1):
                    if remaining % 10 == 0 or remaining <= 5:
                        logger.debug(f"Next scan in {remaining}s...")
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            console.print("\n")
            console.print(
                Panel("[yellow]👋 Shutting down gracefully...[/yellow]", border_style="yellow")
            )
            logger.info("Shutdown complete")
            console.print("[green]✅ Goodbye![/green]\n")
