# Polymarket Insider Tracker

A sophisticated bot that monitors Polymarket for suspicious trading activity and potential insider trading patterns. Get instant Telegram alerts when anomalies are detected.

## What It Does

The bot watches for three key suspicious patterns:

1. **Fresh Wallets** - New accounts suddenly placing large bets
2. **Oversized Positions** - Bets that don't match the wallet's history or market averages
3. **Suspicious Timing** - Activity patterns that suggest insider knowledge:
   - Trading in off-hours (2-5 AM UTC)
   - Large bets in low-liquidity markets
   - High market concentration (betting heavily on specific outcomes)
   - Unusual volume spikes before major news

When something suspicious happens, you get an instant **Telegram notification** with:
- Suspicion score (0-10)
- Wallet details and statistics
- Trade information
- All detected red flags
- Direct link to the market

## Features

- **Real-time Monitoring** - Scans markets every 60 seconds
- **Multi-Signal Detection** - Uses 7+ different signals to identify suspicious activity
- **Telegram Alerts** - Instant notifications with rich formatting
- **Historical Tracking** - SQLite database stores all wallet behavior
- **Beautiful CLI** - Rich terminal interface with progress bars and colored alerts
- **Async Architecture** - Monitors 30+ markets concurrently
- **Configurable** - Fine-tune detection thresholds via environment variables

## Detection Signals

The bot scores each trade on a 0-10 scale using these signals:

| Signal | Points | Description |
|--------|--------|-------------|
| Brand new wallet (< 1 day) | +2 | Wallet created very recently |
| Fresh wallet (< 30 days) | +1 | Relatively new wallet |
| Unusually large bet (> 3x avg) | +3 | Bet significantly larger than market average |
| Very large bet (> $10k) | +2 | High-value position |
| Large bet (> $5k) | +1 | Above-average position |
| High market concentration (> 60%) | +2 | Most trades in single market |
| Moderate concentration (> 42%) | +1 | Focused betting pattern |
| Very low liquidity market | +2 | Trading in illiquid markets |
| Niche market | +1 | Trading in small markets |
| Repeated entries | +1 | Multiple trades in few markets |
| Off-hours trading | +1 | Trading during 2-5 AM UTC |

**Alert Threshold:** Scores ≥ 7 trigger notifications (configurable)

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Zamster100/polyinsiders.git
cd polyinsiders
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Message your new bot with `/start`
5. Get your chat ID by visiting:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
   Look for `"chat":{"id":123456789}` in the response

### 4. Configure Environment

```bash
cp .env.example .env
nano .env
```

Update these required values:
```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 5. Run the Bot

**Continuous monitoring:**
```bash
python run.py
```

**Single scan:**
```bash
python run.py --scan
```

**View statistics:**
```bash
python run.py --stats
```

**Debug mode:**
```bash
python run.py --debug
```

## Configuration

All settings can be customized in the `.env` file:

```bash
# How often to scan markets (seconds)
POLL_INTERVAL=60

# Minimum bet size to track (USD)
MIN_BET_SIZE=1000

# Alert threshold (0-10)
SUSPICIOUS_SCORE_THRESHOLD=7

# Fresh wallet threshold (days)
FRESH_WALLET_DAYS=30

# Performance tuning
CONCURRENT_BATCH_SIZE=30
MAX_CONNECTIONS=50

# Logging level
LOG_LEVEL=INFO
```

## Example Alert

When the bot detects suspicious activity, you'll receive a Telegram message like this:

```
🚨 CRITICAL: Suspicious Activity Detected

📊 Score: 8.5/10
💰 Wallet: 0x1234ab...cd5678
🎯 Market: Will Trump win the 2024 election?

📈 Trade Details:
• Side: BUY
• Size: 15000
• Price: $0.65
• Value: $9,750.00

👤 Wallet Statistics:
• Age: 2.3 days
• Total Trades: 8
• Unique Markets: 2
• Avg Bet Size: $8,200.00

🚩 Red Flags:
1. Brand new wallet (< 1 day old)
2. Unusually large bet: $9,750 (avg: $2,100)
3. High market concentration: 75% of trades in one market

View on Polymarket
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Main Tracker Loop                    │
│              (scans every 60 seconds)                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Polymarket API      │
         │   - Fetch markets     │
         │   - Fetch trades      │
         └──────────┬────────────┘
                    │
                    ▼
         ┌───────────────────────┐
         │  Anomaly Detector     │
         │  - Score trades       │
         │  - Detect patterns    │
         └──────────┬────────────┘
                    │
                    ▼
         ┌───────────────────────┐
         │   Alert System        │
         │   - Create alerts     │
         │   - Store in DB       │
         └──────────┬────────────┘
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
  ┌──────────────┐    ┌───────────────┐
  │   Console    │    │   Telegram    │
  │   Display    │    │ Notifications │
  └──────────────┘    └───────────────┘
```

## Database

The bot uses SQLite to store:
- **Wallets** - First seen timestamp for age calculation
- **Trades** - All tracked trades for historical analysis
- **Alerts** - All generated alerts with full context

Database file: `polymarket_tracker.db`

View stats anytime with:
```bash
python run.py --stats
```

## Tracked Markets

Currently monitoring:
- **Politics** (tag_id=2) - Presidential elections, political outcomes

To add more categories, edit `src/config.py`:
```python
TRACKED_TAG_IDS = [
    2,   # Politics
    3,   # Crypto
    # Add more tag IDs here
]
```

## Performance

- Monitors **30 markets concurrently** by default
- Uses **connection pooling** (50 max connections)
- **Request caching** with 300s TTL
- **Exponential backoff** retry logic
- Scans complete in ~5-10 seconds for 50+ markets

## Requirements

- Python 3.10+
- Internet connection
- Telegram account (for notifications)

## Troubleshooting

**Bot not sending Telegram messages:**
- Check your bot token and chat ID are correct
- Make sure you've messaged your bot first with `/start`
- Verify `TELEGRAM_ENABLED=true` in `.env`

**No alerts being generated:**
- Lower the `SUSPICIOUS_SCORE_THRESHOLD` (try 5 or 6)
- Lower the `MIN_BET_SIZE` (try 500)
- Check logs for detected patterns: `python run.py --debug`

**Too many false positives:**
- Raise the `SUSPICIOUS_SCORE_THRESHOLD` (try 8 or 9)
- Raise the `MIN_BET_SIZE` (try 2000)
- Adjust `FRESH_WALLET_DAYS` (try 14 or 7)

## Advanced Usage

**Custom detection logic:**
Edit `src/anomaly_detector.py` to add your own signals and scoring logic.

**Database queries:**
```bash
sqlite3 polymarket_tracker.db
SELECT * FROM alerts WHERE suspicion_score >= 9;
```

**Export data:**
The database can be queried directly or exported to CSV for analysis.

## Credits

Based on the [polymarket-insider-bot](https://github.com/NickNaskida/polymarket-insider-bot) by NickNaskida, enhanced with:
- Telegram notifications
- Enhanced timing detection
- Off-hours trading detection
- Volume spike detection
- Price momentum analysis

## License

MIT License - feel free to modify and use for your own purposes.

## Disclaimer

This bot is for educational and research purposes only. It does not constitute financial advice. Trading on prediction markets involves risk.
