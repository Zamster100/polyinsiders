"""Detect anomalous patterns in orderbooks"""

import statistics
from datetime import datetime

from src.config import MIN_BET_SIZE
from src.logger import logger


class OrderbookAnomalyDetector:
    """Detect suspicious patterns in orderbook data"""

    def analyze_orderbook(self, orderbook: dict, market: dict) -> tuple[float, list[str], dict]:
        """
        Analyze orderbook for suspicious patterns
        Returns (score, reasons, details)
        """
        score = 0.0
        reasons = []
        details = {}

        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])

        if not bids and not asks:
            return (0.0, [], {})

        # Calculate orderbook metrics
        total_bid_size = sum(float(b.get('size', 0)) for b in bids)
        total_ask_size = sum(float(a.get('size', 0)) for a in asks)
        total_volume = total_bid_size + total_ask_size

        details['total_bid_size'] = total_bid_size
        details['total_ask_size'] = total_ask_size
        details['total_volume'] = total_volume
        details['num_bids'] = len(bids)
        details['num_asks'] = len(asks)

        # Signal 1: Large individual orders (whale detection)
        large_orders = []
        for bid in bids:
            size = float(bid.get('size', 0))
            price = float(bid.get('price', 0))
            value = size * price

            if value > MIN_BET_SIZE * 5:  # 5x minimum
                large_orders.append(('BUY', size, price, value))

        for ask in asks:
            size = float(ask.get('size', 0))
            price = float(ask.get('price', 0))
            value = size * (1 - price)  # Value of selling "Yes"

            if value > MIN_BET_SIZE * 5:
                large_orders.append(('SELL', size, price, value))

        if large_orders:
            # Sort by value
            large_orders.sort(key=lambda x: x[3], reverse=True)
            largest = large_orders[0]

            if largest[3] > MIN_BET_SIZE * 10:  # 10x minimum
                score += 3
                reasons.append(f"Very large order: {largest[0]} ${largest[3]:,.2f}")
            elif largest[3] > MIN_BET_SIZE * 5:
                score += 2
                reasons.append(f"Large order: {largest[0]} ${largest[3]:,.2f}")

            details['large_orders'] = large_orders[:5]  # Top 5

        # Signal 2: Orderbook imbalance
        if total_volume > 0:
            imbalance = (total_bid_size - total_ask_size) / total_volume

            if abs(imbalance) > 0.6:  # 60% imbalance
                score += 3
                direction = "bullish" if imbalance > 0 else "bearish"
                reasons.append(f"Extreme orderbook imbalance: {abs(imbalance)*100:.1f}% {direction}")
            elif abs(imbalance) > 0.4:  # 40% imbalance
                score += 2
                direction = "bullish" if imbalance > 0 else "bearish"
                reasons.append(f"Strong orderbook imbalance: {abs(imbalance)*100:.1f}% {direction}")
            elif abs(imbalance) > 0.2:  # 20% imbalance
                score += 1
                direction = "bullish" if imbalance > 0 else "bearish"
                reasons.append(f"Orderbook imbalance: {abs(imbalance)*100:.1f}% {direction}")

            details['imbalance'] = imbalance

        # Signal 3: Unusual spread
        if bids and asks:
            best_bid = max(float(b.get('price', 0)) for b in bids)
            best_ask = min(float(a.get('price', 0)) for a in asks)
            spread = best_ask - best_bid

            details['best_bid'] = best_bid
            details['best_ask'] = best_ask
            details['spread'] = spread

            # Very tight spread might indicate market manipulation
            if spread < 0.01:  # Less than 1 cent
                score += 2
                reasons.append(f"Extremely tight spread: ${spread:.4f}")
            # Very wide spread might indicate low liquidity/unusual activity
            elif spread > 0.2:  # More than 20 cents
                score += 1
                reasons.append(f"Unusually wide spread: ${spread:.2f}")

        # Signal 4: Order concentration at specific price
        if bids:
            bid_prices = [float(b.get('price', 0)) for b in bids]
            bid_sizes = [float(b.get('size', 0)) for b in bids]

            # Check if one price has >50% of total bid volume
            for i, size in enumerate(bid_sizes):
                if total_bid_size > 0 and size / total_bid_size > 0.5:
                    score += 2
                    price = bid_prices[i]
                    reasons.append(f"Concentrated bid: {size/total_bid_size*100:.1f}% at ${price:.2f}")
                    break

        if asks:
            ask_prices = [float(a.get('price', 0)) for a in asks]
            ask_sizes = [float(a.get('size', 0)) for a in asks]

            # Check if one price has >50% of total ask volume
            for i, size in enumerate(ask_sizes):
                if total_ask_size > 0 and size / total_ask_size > 0.5:
                    score += 2
                    price = ask_prices[i]
                    reasons.append(f"Concentrated ask: {size/total_ask_size*100:.1f}% at ${price:.2f}")
                    break

        # Signal 5: Low liquidity but large orders
        if total_volume < MIN_BET_SIZE * 10 and large_orders:
            score += 1
            reasons.append(f"Large orders in illiquid market (total: ${total_volume:,.2f})")

        return (min(score, 10), reasons, details)

    def calculate_market_activity(self, orderbooks: list[dict]) -> dict:
        """Calculate overall market activity metrics"""
        if not orderbooks:
            return {}

        total_liquidity = 0
        max_order_size = 0

        for ob in orderbooks:
            bids = ob.get('bids', [])
            asks = ob.get('asks', [])

            bid_volume = sum(float(b.get('size', 0)) for b in bids)
            ask_volume = sum(float(a.get('size', 0)) for a in asks)

            total_liquidity += bid_volume + ask_volume

            # Find largest order
            for b in bids:
                size = float(b.get('size', 0)) * float(b.get('price', 0))
                max_order_size = max(max_order_size, size)

            for a in asks:
                size = float(a.get('size', 0)) * (1 - float(a.get('price', 0)))
                max_order_size = max(max_order_size, size)

        return {
            'total_liquidity': total_liquidity,
            'max_order_size': max_order_size,
            'num_orderbooks': len(orderbooks),
        }
