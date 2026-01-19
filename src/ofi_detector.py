"""Order Flow Imbalance (OFI) Detection

Measures aggressive buying vs selling pressure to detect informed trading.
Higher OFI values indicate stronger directional conviction (insider activity).
"""

import statistics
from collections import deque
from datetime import datetime
from src.logger import logger


class OFIDetector:
    """Calculates Order Flow Imbalance to detect informed trading"""

    def __init__(self, window_size: int = 10):
        """
        Args:
            window_size: Number of snapshots to use for historical analysis
        """
        self.window_size = window_size
        self.history = {}  # market_id -> deque of (timestamp, ofi_value)

    def calculate_ofi(self, orderbook: dict) -> tuple[float, dict]:
        """
        Calculate Order Flow Imbalance from orderbook snapshot

        Returns:
            (ofi_value, details)

        OFI ranges from -1 (max sell pressure) to +1 (max buy pressure)
        """
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])

        if not bids or not asks:
            return (0.0, {})

        # Calculate total volume on each side
        total_bid_volume = sum(float(b.get('size', 0)) for b in bids)
        total_ask_volume = sum(float(a.get('size', 0)) for a in asks)
        total_volume = total_bid_volume + total_ask_volume

        if total_volume == 0:
            return (0.0, {})

        # OFI = (Bid Volume - Ask Volume) / Total Volume
        ofi = (total_bid_volume - total_ask_volume) / total_volume

        # Calculate weighted OFI (weight by proximity to mid-price)
        if bids and asks:
            best_bid = max(float(b.get('price', 0)) for b in bids)
            best_ask = min(float(a.get('price', 0)) for a in asks)
            mid_price = (best_bid + best_ask) / 2

            # Weight orders closer to mid-price more heavily
            weighted_bid_vol = 0
            weighted_ask_vol = 0

            for bid in bids:
                price = float(bid.get('price', 0))
                size = float(bid.get('size', 0))
                distance = abs(price - mid_price)
                weight = 1 / (1 + distance * 10)  # Exponential decay
                weighted_bid_vol += size * weight

            for ask in asks:
                price = float(ask.get('price', 0))
                size = float(ask.get('size', 0))
                distance = abs(price - mid_price)
                weight = 1 / (1 + distance * 10)
                weighted_ask_vol += size * weight

            weighted_total = weighted_bid_vol + weighted_ask_vol
            if weighted_total > 0:
                weighted_ofi = (weighted_bid_vol - weighted_ask_vol) / weighted_total
            else:
                weighted_ofi = ofi
        else:
            weighted_ofi = ofi

        details = {
            'ofi': ofi,
            'weighted_ofi': weighted_ofi,
            'total_bid_volume': total_bid_volume,
            'total_ask_volume': total_ask_volume,
            'total_volume': total_volume,
            'direction': 'BUY' if ofi > 0 else 'SELL',
            'strength': abs(ofi),
        }

        return (weighted_ofi, details)

    def add_snapshot(self, market_id: str, ofi_value: float):
        """Add OFI snapshot to history for time-series analysis"""
        if market_id not in self.history:
            self.history[market_id] = deque(maxlen=self.window_size)

        self.history[market_id].append((datetime.now(), ofi_value))

    def detect_ofi_extremes(self, ofi_value: float, details: dict) -> tuple[float, list[str]]:
        """
        Detect extreme OFI values that indicate informed trading

        Returns:
            (score, reasons)
        """
        score = 0.0
        reasons = []

        strength = abs(ofi_value)
        direction = details.get('direction', 'NEUTRAL')

        # Signal 1: Extreme imbalance (>70%)
        if strength > 0.7:
            score += 4
            reasons.append(f"Extreme order flow imbalance: {strength*100:.1f}% {direction}")
        elif strength > 0.5:
            score += 3
            reasons.append(f"Strong order flow imbalance: {strength*100:.1f}% {direction}")
        elif strength > 0.3:
            score += 1
            reasons.append(f"Moderate order flow imbalance: {strength*100:.1f}% {direction}")

        # Signal 2: Check if weighted OFI differs significantly from simple OFI
        # This indicates aggressive orders near the mid-price (informed trading)
        simple_ofi = details.get('ofi', 0)
        weighted_diff = abs(ofi_value - simple_ofi)

        if weighted_diff > 0.2:
            score += 2
            reasons.append(f"Aggressive near-market orders detected (informed trading pattern)")

        return (min(score, 5), reasons)  # Cap at 5 points

    def analyze_ofi_persistence(self, market_id: str, current_ofi: float) -> tuple[float, list[str]]:
        """
        Analyze if OFI is persistent (sustained pressure = informed trading)

        Returns:
            (score, reasons)
        """
        if market_id not in self.history or len(self.history[market_id]) < 3:
            return (0.0, [])

        score = 0.0
        reasons = []

        # Get recent OFI values
        recent_ofis = [ofi for _, ofi in list(self.history[market_id])]

        # Check if OFI maintains same direction
        if len(recent_ofis) >= 3:
            same_direction = all(ofi * current_ofi > 0 for ofi in recent_ofis[-3:])

            if same_direction:
                avg_strength = statistics.mean([abs(ofi) for ofi in recent_ofis[-3:]])

                if avg_strength > 0.4:
                    score += 3
                    direction = 'bullish' if current_ofi > 0 else 'bearish'
                    reasons.append(f"Persistent {direction} flow (3+ periods) - informed trading")
                elif avg_strength > 0.25:
                    score += 1
                    direction = 'bullish' if current_ofi > 0 else 'bearish'
                    reasons.append(f"Sustained {direction} pressure detected")

        # Check for increasing pressure (ramping up = insider urgency)
        if len(recent_ofis) >= 2:
            increasing = all(
                abs(recent_ofis[i]) < abs(recent_ofis[i+1])
                for i in range(len(recent_ofis) - 1)
            )

            if increasing and abs(current_ofi) > 0.3:
                score += 2
                reasons.append("Accelerating order flow (insider urgency)")

        return (min(score, 4), reasons)  # Cap at 4 points

    def get_ofi_summary(self, market_id: str) -> dict:
        """Get summary statistics for a market's OFI history"""
        if market_id not in self.history or not self.history[market_id]:
            return {}

        ofis = [ofi for _, ofi in self.history[market_id]]

        return {
            'current': ofis[-1] if ofis else 0,
            'mean': statistics.mean(ofis) if ofis else 0,
            'std': statistics.stdev(ofis) if len(ofis) > 1 else 0,
            'min': min(ofis) if ofis else 0,
            'max': max(ofis) if ofis else 0,
            'snapshots': len(ofis),
        }
