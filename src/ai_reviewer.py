"""AI Agent to review orderbook anomalies and determine if they warrant investigation"""

import anthropic
import os
from src.logger import logger


class AIReviewer:
    """Uses Claude AI to review orderbook anomalies and filter false positives"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.enabled = bool(self.api_key)
        self.client = None

        if self.enabled:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("AI Reviewer enabled")
            except Exception as e:
                logger.error(f"Failed to initialize AI Reviewer: {e}")
                logger.warning("AI Reviewer disabled - continuing without AI review")
                self.enabled = False
        else:
            logger.warning("AI Reviewer disabled - set ANTHROPIC_API_KEY to enable")

    async def review_anomaly(
        self,
        market: dict,
        score: float,
        reasons: list[str],
        details: dict
    ) -> tuple[bool, str, str]:
        """
        Review an orderbook anomaly to determine if it's worth investigating

        Returns:
            (should_alert, reasoning, risk_level)
        """

        if not self.enabled:
            # If AI review is disabled, pass through all anomalies
            return (True, "AI review disabled", "MEDIUM")

        try:
            # Build analysis prompt
            prompt = f"""You are an expert at detecting insider trading in prediction markets. Review this orderbook anomaly and determine if it indicates potential insider activity.

MARKET INFORMATION:
Title: {market.get('question', 'Unknown')}
Category: Politics

ANOMALY SCORE: {score}/10

DETECTION SIGNALS:
{chr(10).join(f'- {reason}' for reason in reasons)}

ORDERBOOK DETAILS:
- Total Volume: ${details.get('total_volume', 0):,.2f}
- Bid Volume: ${details.get('total_bid_size', 0):,.2f}
- Ask Volume: ${details.get('total_ask_size', 0):,.2f}
- Imbalance: {details.get('imbalance', 0)*100:.1f}%
- Spread: ${details.get('spread', 0):.4f}

LARGE ORDERS:
{self._format_large_orders(details.get('large_orders', []))}

TASK:
Analyze whether this anomaly indicates potential insider trading activity. Consider:
1. Is the order size unusual enough to suggest insider information?
2. Does the market timing/context suggest insider knowledge?
3. Are there legitimate non-insider explanations for this pattern?
4. What is the risk level (LOW/MEDIUM/HIGH)?

Respond in this exact format:
ALERT: [YES/NO]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
REASONING: [Your 1-2 sentence analysis]"""

            # Call Claude API
            message = self.client.messages.create(
                model="claude-3-5-haiku-20241022",  # Fast and cost-effective
                max_tokens=200,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            response = message.content[0].text.strip()

            # Parse response
            should_alert = "ALERT: YES" in response

            risk_level = "MEDIUM"
            if "RISK_LEVEL: HIGH" in response:
                risk_level = "HIGH"
            elif "RISK_LEVEL: LOW" in response:
                risk_level = "LOW"

            reasoning = ""
            if "REASONING:" in response:
                reasoning = response.split("REASONING:")[1].strip()

            logger.info(
                f"AI Review: {'✅ ALERT' if should_alert else '❌ SKIP'} "
                f"({risk_level}) - {market.get('question', '')[:40]}"
            )

            return (should_alert, reasoning, risk_level)

        except Exception as e:
            logger.error(f"AI review failed: {e}")
            # On error, default to alerting (don't suppress potential insider activity)
            return (True, f"AI review error: {str(e)}", "MEDIUM")

    def _format_large_orders(self, large_orders: list) -> str:
        """Format large orders for the prompt"""
        if not large_orders:
            return "None"

        lines = []
        for order in large_orders[:5]:  # Top 5
            side, size, price, value = order
            lines.append(f"- {side}: {size:,.0f} @ ${price:.2f} = ${value:,.2f}")

        return "\n".join(lines) if lines else "None"
