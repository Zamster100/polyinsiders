"""Identify wallet addresses from orderbook anomalies by fetching recent trades"""

import asyncio
from datetime import datetime, timedelta
from src.logger import logger


class WalletIdentifier:
    """Fetches recent trades to identify wallets behind large orders"""

    def __init__(self, api):
        """
        Args:
            api: OrderbookAPI or AuthenticatedPolymarketAPI instance
        """
        self.api = api

    async def identify_wallets_from_anomaly(
        self,
        market: dict,
        orderbook_details: dict,
        lookback_minutes: int = 30
    ) -> list[dict]:
        """
        Identify wallets that likely placed the large orders detected in the anomaly

        Args:
            market: Market data
            orderbook_details: Details from orderbook anomaly detection
            lookback_minutes: How far back to look for trades

        Returns:
            List of wallet profiles with trade info
        """

        condition_id = market.get("conditionId")
        if not condition_id:
            return []

        try:
            # Fetch recent trades on this market
            trades = await self._fetch_recent_trades(condition_id, limit=100)

            if not trades:
                logger.debug(f"No recent trades found for {market.get('question', '')[:40]}")
                return []

            # Analyze trades to find wallets matching the anomaly pattern
            large_orders = orderbook_details.get('large_orders', [])
            if not large_orders:
                return []

            # Get the characteristics of the anomaly
            min_order_size = min(order[3] for order in large_orders)  # order[3] is value

            # Find wallets with trades matching the anomaly
            wallet_profiles = []
            wallet_trades = {}  # Group trades by wallet

            for trade in trades:
                wallet = trade.get('maker')  # or 'taker' depending on API
                if not wallet:
                    wallet = trade.get('taker')
                if not wallet:
                    continue

                # Calculate trade value
                size = float(trade.get('size', 0))
                price = float(trade.get('price', 0))
                value = size * price

                # Track trades by wallet
                if wallet not in wallet_trades:
                    wallet_trades[wallet] = {
                        'wallet': wallet,
                        'trades': [],
                        'total_value': 0,
                        'avg_size': 0,
                        'trade_count': 0,
                    }

                wallet_trades[wallet]['trades'].append(trade)
                wallet_trades[wallet]['total_value'] += value
                wallet_trades[wallet]['trade_count'] += 1

            # Calculate averages and filter for suspicious wallets
            for wallet, data in wallet_trades.items():
                data['avg_size'] = data['total_value'] / data['trade_count']

                # Consider wallet suspicious if they have trades near the anomaly size
                if data['total_value'] >= min_order_size * 0.5:  # 50% threshold
                    wallet_profiles.append({
                        'wallet': wallet,
                        'total_value': data['total_value'],
                        'trade_count': data['trade_count'],
                        'avg_trade_size': data['avg_size'],
                        'recent_trades': data['trades'][:5],  # Last 5 trades
                    })

            # Sort by total value (biggest traders first)
            wallet_profiles.sort(key=lambda x: x['total_value'], reverse=True)

            logger.info(
                f"Identified {len(wallet_profiles)} suspicious wallets in "
                f"{market.get('question', '')[:40]}"
            )

            return wallet_profiles[:10]  # Return top 10

        except Exception as e:
            logger.error(f"Error identifying wallets: {e}")
            return []

    async def _fetch_recent_trades(self, condition_id: str, limit: int = 100) -> list[dict]:
        """Fetch recent trades for a market"""

        try:
            # Try authenticated API method if available
            if hasattr(self.api, 'fetch_trades'):
                trades = await self.api.fetch_trades(condition_id, limit=limit)
                return trades if trades else []

            # Fallback: Try public CLOB API (may not work without auth)
            if hasattr(self.api, 'session'):
                url = f"https://clob.polymarket.com/trades"
                params = {
                    "market": condition_id,
                    "limit": limit
                }

                async with self.api.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data if isinstance(data, list) else []
                    else:
                        logger.debug(f"Trades API returned {response.status}")
                        return []

            return []

        except Exception as e:
            logger.debug(f"Could not fetch trades: {e}")
            return []

    async def get_wallet_profile(self, wallet_address: str) -> dict:
        """
        Get additional profile information about a wallet

        Returns:
            dict with wallet stats and metadata
        """

        # This could be expanded to:
        # 1. Query blockchain for wallet age
        # 2. Check Polymarket API for historical trades
        # 3. Calculate win rate, avg bet size, etc.

        return {
            'address': wallet_address,
            'short_address': f"{wallet_address[:8]}...{wallet_address[-6:]}",
            'polygonscan_url': f"https://polygonscan.com/address/{wallet_address}",
            # Add more profile data here if available
        }
