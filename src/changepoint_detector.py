"""Change Point Detection for identifying sudden regime shifts in orderbooks

Detects moments when trading behavior changes dramatically, indicating
potential insider information entering the market.
"""

import statistics
from collections import deque
from datetime import datetime, timedelta
from src.logger import logger


class ChangePointDetector:
    """Detects sudden changes in orderbook behavior using statistical methods"""

    def __init__(self, window_size: int = 20, sensitivity: float = 2.0):
        """
        Args:
            window_size: Number of snapshots to analyze
            sensitivity: Number of standard deviations for change detection
        """
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.metrics_history = {}  # market_id -> deque of metric snapshots

    def add_snapshot(self, market_id: str, metrics: dict):
        """
        Add orderbook metrics snapshot to history

        metrics should include:
        - total_volume
        - imbalance
        - spread
        - ofi (if available)
        """
        if market_id not in self.metrics_history:
            self.metrics_history[market_id] = deque(maxlen=self.window_size)

        snapshot = {
            'timestamp': datetime.now(),
            'total_volume': metrics.get('total_volume', 0),
            'imbalance': metrics.get('imbalance', 0),
            'spread': metrics.get('spread', 0),
            'ofi': metrics.get('ofi', 0),
        }

        self.metrics_history[market_id].append(snapshot)

    def detect_volume_changepoint(self, market_id: str) -> tuple[bool, float, str]:
        """
        Detect sudden volume spikes (insiders entering market)

        Returns:
            (is_changepoint, zscore, description)
        """
        if market_id not in self.metrics_history:
            return (False, 0.0, "")

        history = list(self.metrics_history[market_id])
        if len(history) < 5:
            return (False, 0.0, "Insufficient data")

        # Get recent volume
        volumes = [s['total_volume'] for s in history]
        current_vol = volumes[-1]

        # Calculate baseline statistics (excluding current)
        baseline_vols = volumes[:-1]
        if not baseline_vols or current_vol == 0:
            return (False, 0.0, "")

        mean_vol = statistics.mean(baseline_vols)
        if len(baseline_vols) > 1:
            std_vol = statistics.stdev(baseline_vols)
        else:
            std_vol = mean_vol * 0.5  # Assume 50% volatility

        if std_vol == 0:
            std_vol = mean_vol * 0.1  # Prevent division by zero

        # Calculate z-score
        zscore = (current_vol - mean_vol) / std_vol

        # Detect changepoint
        is_changepoint = zscore > self.sensitivity

        if is_changepoint:
            pct_increase = ((current_vol - mean_vol) / mean_vol) * 100
            description = f"Volume spike: {pct_increase:+.1f}% above baseline ({zscore:.1f}σ)"
        else:
            description = ""

        return (is_changepoint, zscore, description)

    def detect_imbalance_changepoint(self, market_id: str) -> tuple[bool, float, str]:
        """
        Detect sudden shifts in buy/sell imbalance (directional insider bet)

        Returns:
            (is_changepoint, change_magnitude, description)
        """
        if market_id not in self.metrics_history:
            return (False, 0.0, "")

        history = list(self.metrics_history[market_id])
        if len(history) < 5:
            return (False, 0.0, "Insufficient data")

        # Get imbalance values
        imbalances = [s['imbalance'] for s in history]
        current_imb = imbalances[-1]

        # Calculate baseline
        baseline_imbs = imbalances[:-3] if len(imbalances) > 3 else imbalances[:-1]
        if not baseline_imbs:
            return (False, 0.0, "")

        mean_imb = statistics.mean(baseline_imbs)

        # Detect shift in imbalance direction
        change = abs(current_imb - mean_imb)

        is_changepoint = change > 0.4  # 40% shift

        if is_changepoint:
            direction = "bullish" if current_imb > mean_imb else "bearish"
            description = f"Sudden {direction} shift: {change*100:.1f}% imbalance change"
        else:
            description = ""

        return (is_changepoint, change, description)

    def detect_spread_changepoint(self, market_id: str) -> tuple[bool, float, str]:
        """
        Detect sudden spread compression (insider urgency) or expansion (uncertainty)

        Returns:
            (is_changepoint, zscore, description)
        """
        if market_id not in self.metrics_history:
            return (False, 0.0, "")

        history = list(self.metrics_history[market_id])
        if len(history) < 5:
            return (False, 0.0, "Insufficient data")

        # Get spread values
        spreads = [s['spread'] for s in history if s['spread'] > 0]
        if len(spreads) < 3:
            return (False, 0.0, "")

        current_spread = spreads[-1]

        # Calculate baseline
        baseline_spreads = spreads[:-1]
        mean_spread = statistics.mean(baseline_spreads)

        if len(baseline_spreads) > 1:
            std_spread = statistics.stdev(baseline_spreads)
        else:
            std_spread = mean_spread * 0.3

        if std_spread == 0:
            return (False, 0.0, "")

        # Calculate z-score
        zscore = abs(current_spread - mean_spread) / std_spread

        is_changepoint = zscore > self.sensitivity

        if is_changepoint:
            if current_spread < mean_spread:
                pct_change = ((mean_spread - current_spread) / mean_spread) * 100
                description = f"Spread compression: -{pct_change:.1f}% (insider urgency)"
            else:
                pct_change = ((current_spread - mean_spread) / mean_spread) * 100
                description = f"Spread expansion: +{pct_change:.1f}% (uncertainty/manipulation)"
        else:
            description = ""

        return (is_changepoint, zscore, description)

    def detect_ofi_changepoint(self, market_id: str) -> tuple[bool, float, str]:
        """
        Detect sudden shifts in order flow (informed trading starting)

        Returns:
            (is_changepoint, zscore, description)
        """
        if market_id not in self.metrics_history:
            return (False, 0.0, "")

        history = list(self.metrics_history[market_id])
        if len(history) < 5:
            return (False, 0.0, "Insufficient data")

        # Get OFI values
        ofis = [s['ofi'] for s in history]
        current_ofi = ofis[-1]

        # Calculate baseline
        baseline_ofis = ofis[:-1]
        if not baseline_ofis:
            return (False, 0.0, "")

        mean_ofi = statistics.mean(baseline_ofis)

        if len(baseline_ofis) > 1:
            std_ofi = statistics.stdev(baseline_ofis)
        else:
            std_ofi = 0.2  # Assume moderate volatility

        if std_ofi == 0:
            std_ofi = 0.1

        # Calculate z-score
        zscore = abs(current_ofi - mean_ofi) / std_ofi

        is_changepoint = zscore > self.sensitivity

        if is_changepoint:
            direction = "bullish" if current_ofi > mean_ofi else "bearish"
            description = f"Order flow regime change: {direction} pressure ({zscore:.1f}σ)"
        else:
            description = ""

        return (is_changepoint, zscore, description)

    def analyze_all_changepoints(self, market_id: str, current_metrics: dict) -> tuple[float, list[str], dict]:
        """
        Analyze all types of changepoints

        Returns:
            (score, reasons, details)
        """
        score = 0.0
        reasons = []
        details = {}

        # Add current snapshot
        self.add_snapshot(market_id, current_metrics)

        # Detect volume changepoint
        vol_cp, vol_zscore, vol_desc = self.detect_volume_changepoint(market_id)
        if vol_cp:
            score += 3
            reasons.append(vol_desc)
            details['volume_changepoint'] = True
            details['volume_zscore'] = vol_zscore

        # Detect imbalance changepoint
        imb_cp, imb_change, imb_desc = self.detect_imbalance_changepoint(market_id)
        if imb_cp:
            score += 3
            reasons.append(imb_desc)
            details['imbalance_changepoint'] = True
            details['imbalance_change'] = imb_change

        # Detect spread changepoint
        spread_cp, spread_zscore, spread_desc = self.detect_spread_changepoint(market_id)
        if spread_cp:
            score += 2
            reasons.append(spread_desc)
            details['spread_changepoint'] = True
            details['spread_zscore'] = spread_zscore

        # Detect OFI changepoint
        ofi_cp, ofi_zscore, ofi_desc = self.detect_ofi_changepoint(market_id)
        if ofi_cp:
            score += 4
            reasons.append(ofi_desc)
            details['ofi_changepoint'] = True
            details['ofi_zscore'] = ofi_zscore

        # Multiple simultaneous changepoints = very high confidence
        changepoint_count = sum([vol_cp, imb_cp, spread_cp, ofi_cp])
        if changepoint_count >= 2:
            score += 2
            reasons.append(f"Multiple regime changes detected ({changepoint_count} signals)")

        return (min(score, 10), reasons, details)

    def get_history_summary(self, market_id: str) -> dict:
        """Get summary of market's history"""
        if market_id not in self.metrics_history or not self.metrics_history[market_id]:
            return {}

        history = list(self.metrics_history[market_id])

        return {
            'snapshots': len(history),
            'first_timestamp': history[0]['timestamp'].isoformat() if history else None,
            'last_timestamp': history[-1]['timestamp'].isoformat() if history else None,
            'window_size': self.window_size,
        }
