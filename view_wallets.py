"""View and query stored wallets from the database"""
import asyncio
import sys
from datetime import datetime

import aiosqlite
from rich.console import Console
from rich.table import Table

DATABASE_PATH = "polymarket_tracker.db"
console = Console()


async def get_flagged_wallets(min_alerts=1, min_score=7.0):
    """Get wallets that have been flagged"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = """
            SELECT
                wallet,
                COUNT(*) as alert_count,
                AVG(suspicion_score) as avg_score,
                MAX(suspicion_score) as max_score,
                MAX(timestamp) as last_alert
            FROM alerts
            WHERE suspicion_score >= ?
            GROUP BY wallet
            HAVING alert_count >= ?
            ORDER BY max_score DESC, alert_count DESC
        """

        async with db.execute(query, (min_score, min_alerts)) as cursor:
            rows = await cursor.fetchall()

            if not rows:
                console.print(
                    f"\n[yellow]No wallets found with {min_alerts}+ alerts and score >= {min_score}[/yellow]\n"
                )
                return []

            table = Table(title=f"🚨 Flagged Wallets (Score >= {min_score})")
            table.add_column("Wallet", style="cyan")
            table.add_column("Alerts", justify="right", style="yellow")
            table.add_column("Avg Score", justify="right", style="red")
            table.add_column("Max Score", justify="right", style="red bold")
            table.add_column("Last Alert", style="white")

            wallets = []
            for row in rows:
                wallet, count, avg_score, max_score, last_alert = row
                wallets.append(
                    {
                        "wallet": wallet,
                        "count": count,
                        "avg_score": avg_score,
                        "max_score": max_score,
                        "last_alert": last_alert,
                    }
                )

                # Format timestamp
                try:
                    dt = datetime.fromisoformat(last_alert)
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    time_str = last_alert

                table.add_row(
                    f"{wallet[:8]}...{wallet[-6:]}",
                    str(count),
                    f"{avg_score:.1f}",
                    f"{max_score:.1f}",
                    time_str,
                )

            console.print()
            console.print(table)
            console.print()

            return wallets


async def get_wallet_details(wallet_address):
    """Get detailed information about a specific wallet"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get all alerts for this wallet
        query = """
            SELECT
                timestamp,
                market_title,
                suspicion_score,
                reasons,
                trade_data,
                wallet_stats
            FROM alerts
            WHERE wallet = ?
            ORDER BY timestamp DESC
        """

        async with db.execute(query, (wallet_address,)) as cursor:
            rows = await cursor.fetchall()

            if not rows:
                console.print(f"\n[yellow]No alerts found for wallet {wallet_address}[/yellow]\n")
                return

            console.print(f"\n[bold cyan]Wallet Details: {wallet_address}[/bold cyan]\n")
            console.print(f"[yellow]Total Alerts: {len(rows)}[/yellow]")
            console.print(
                f"[yellow]PolygonScan: https://polygonscan.com/address/{wallet_address}[/yellow]\n"
            )

            table = Table(title="Alert History")
            table.add_column("Date", style="white")
            table.add_column("Market", style="cyan", max_width=40)
            table.add_column("Score", justify="right", style="red")
            table.add_column("Top Red Flags", style="yellow", max_width=50)

            for row in rows:
                timestamp, market, score, reasons_json, trade_json, stats_json = row

                # Parse timestamp
                try:
                    dt = datetime.fromisoformat(timestamp)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = timestamp

                # Parse reasons
                import json

                try:
                    reasons = json.loads(reasons_json)
                    top_flags = ", ".join(reasons[:2])
                except:
                    top_flags = "N/A"

                table.add_row(date_str, market[:40], f"{score:.1f}", top_flags)

            console.print(table)
            console.print()


async def get_wallet_stats():
    """Get overall statistics about tracked wallets"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Total unique wallets tracked
        query1 = "SELECT COUNT(DISTINCT address) FROM wallets"
        async with db.execute(query1) as cursor:
            total_wallets = (await cursor.fetchone())[0]

        # Total unique wallets flagged
        query2 = "SELECT COUNT(DISTINCT wallet) FROM alerts"
        async with db.execute(query2) as cursor:
            flagged_wallets = (await cursor.fetchone())[0]

        # Total alerts
        query3 = "SELECT COUNT(*) FROM alerts"
        async with db.execute(query3) as cursor:
            total_alerts = (await cursor.fetchone())[0]

        # Total trades tracked
        query4 = "SELECT COUNT(*) FROM trades"
        async with db.execute(query4) as cursor:
            total_trades = (await cursor.fetchone())[0]

        table = Table(title="📊 Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="yellow")

        table.add_row("Total Wallets Tracked", f"{total_wallets:,}")
        table.add_row("Total Trades Recorded", f"{total_trades:,}")
        table.add_row("Flagged Wallets", f"{flagged_wallets:,}")
        table.add_row("Total Alerts", f"{total_alerts:,}")

        console.print()
        console.print(table)
        console.print()


async def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            # List all flagged wallets
            min_score = float(sys.argv[2]) if len(sys.argv) > 2 else 7.0
            await get_flagged_wallets(min_alerts=1, min_score=min_score)

        elif command == "wallet":
            # View specific wallet details
            if len(sys.argv) < 3:
                console.print("[red]Error: Please provide wallet address[/red]")
                console.print("Usage: python view_wallets.py wallet 0x...")
                return

            wallet = sys.argv[2]
            await get_wallet_details(wallet)

        elif command == "stats":
            # Show database statistics
            await get_wallet_stats()

        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            show_help()

    else:
        # Default: show stats and list flagged wallets
        await get_wallet_stats()
        await get_flagged_wallets(min_alerts=1, min_score=7.0)


def show_help():
    """Show help message"""
    help_text = """
[bold cyan]Wallet Viewer - Query Stored Wallets[/bold cyan]

[yellow]Usage:[/yellow]
  python view_wallets.py                    # Show stats and list flagged wallets
  python view_wallets.py list [min_score]   # List wallets (default min_score=7.0)
  python view_wallets.py wallet <address>   # View specific wallet details
  python view_wallets.py stats              # Show database statistics

[yellow]Examples:[/yellow]
  python view_wallets.py list 8.0           # List wallets with score >= 8.0
  python view_wallets.py wallet 0x1234...   # View wallet 0x1234... details
  python view_wallets.py stats              # Show database stats
"""
    console.print(help_text)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
