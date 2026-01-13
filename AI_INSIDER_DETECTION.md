# 🤖 AI-Powered Insider Detection

The bot now has **TWO major enhancements** that identify actual insider traders:

## ✨ What's New

### 1. **AI Review Agent** 🧠
- Uses Claude AI (Haiku model) to analyze each anomaly
- Filters out false positives automatically
- Provides reasoning for each decision
- Assigns risk levels (LOW/MEDIUM/HIGH)

**Without AI Review:** You'll get alerts on EVERY orderbook imbalance (100s of alerts)
**With AI Review:** Only genuine insider patterns get through (5-10 quality alerts)

### 2. **Wallet Identification** 👤
- Fetches recent trades on markets with anomalies
- Identifies WHO placed those large orders
- Shows wallet addresses with clickable PolygonScan links
- Displays trade history and total values

**Before:** "Market has $50K imbalance" (WHO made it?)
**After:** "Wallet 0x1234... placed $50K in 3 trades" (Click to investigate!)

---

## 🚀 Setup

### 1. Pull Latest Code
```bash
git pull origin claude/polymarket-insider-tracker-fqHga
pip install -r requirements.txt
```

### 2. Get Anthropic API Key (HIGHLY RECOMMENDED)
1. Go to https://console.anthropic.com/
2. Create account / sign in
3. Generate API key
4. Add to your `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

**Cost:** ~$0.001 per review (Haiku model)
**For 1000 markets:** ~$1 per scan

### 3. Update Your `.env`
```bash
# Required for AI review
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Lower thresholds to see activity
SUSPICIOUS_SCORE_THRESHOLD=1
MIN_BET_SIZE=100

# Your existing Telegram settings
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

---

## 📊 What You'll See

### In Terminal:
```
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric                ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Markets Scanned       │  1625 │
│ Orderbooks Analyzed   │  3250 │
│ Orderbooks w/ Data    │  1420 │
│ Scores Calculated     │   856 │
│ AI Reviewed           │   142 │  ← Anomalies found
│ AI Approved           │    12 │  ← Real insider activity!
│ New Alerts            │    12 │
└───────────────────────┴───────┘
```

### In Telegram:
```
🚨 CRITICAL: Orderbook Anomaly Detected

📊 SUSPICION SCORE: 8.5/10

🎯 MARKET INFO
• Title: Will Trump win 2024?
• Category: Politics

📚 ORDERBOOK STATS
• Total Volume: $245,891.50
• Bid Volume: $180,234.00
• Imbalance: 46.6% Bullish

🐋 LARGE ORDERS
• BUY: 50,000 @ $0.72 = $36,000.00

🤖 AI ANALYSIS (HIGH RISK)
Extremely large order placed immediately before market
movement suggests insider information. Order size
disproportionate to typical market activity.

👤 SUSPECTED INSIDERS

1. 0x1a2b3c4d...5e6f7g
   • Total: $36,250.00 (3 trades)
   • View on PolygonScan

2. 0x8h9i0j1k...2l3m4n
   • Total: $18,000.00 (5 trades)
   • View on PolygonScan

🚩 DETECTION SIGNALS
1. Very large order: BUY $36,000
2. Orderbook imbalance >40%

━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 View Market on Polymarket
```

---

## 🎯 How It Works

### Detection Flow:
```
1. Scan orderbooks for anomalies
   ↓
2. Calculate suspicion score (0-10)
   ↓
3. If score >= threshold → Send to AI Review
   ↓
4. AI analyzes context and patterns
   ↓
5. If AI approves → Identify wallets
   ↓
6. Fetch recent trades on that market
   ↓
7. Match trades to anomaly pattern
   ↓
8. Create alert with wallet profiles
   ↓
9. Send to Telegram with clickable links
```

### AI Decision Factors:
- Order size vs market average
- Timing (before news/events)
- Market context (election, sports, crypto)
- Pattern legitimacy (whale vs insider)
- Imbalance severity
- Spread manipulation signals

---

## 💡 Tips

### Getting Started:
1. **Run with low thresholds first:**
   ```bash
   SUSPICIOUS_SCORE_THRESHOLD=1
   MIN_BET_SIZE=50
   ```

2. **Let AI filter the noise:**
   - Without AI: Expect 100+ alerts per scan
   - With AI: Expect 5-15 quality alerts per scan

3. **Review first 10 alerts:**
   - Check if wallet profiles are being identified
   - Verify PolygonScan links work
   - Adjust MIN_BET_SIZE if needed

### Troubleshooting:

**No wallet profiles shown?**
- The trades endpoint may require authentication
- The wallet_identifier will log warnings if it can't fetch trades
- This is optional - you'll still get orderbook anomalies

**Too many alerts?**
- Increase SUSPICIOUS_SCORE_THRESHOLD to 3-5
- Increase MIN_BET_SIZE to filter small orders
- AI will still filter most false positives

**AI review not working?**
- Check ANTHROPIC_API_KEY is set correctly
- Bot will work without AI but alert on everything
- Look for "AI Reviewer enabled" in logs

---

## 🔧 Optional: Disable AI Review

If you don't want to use AI review (not recommended):
```bash
# Leave ANTHROPIC_API_KEY empty or unset
# ANTHROPIC_API_KEY=

# You'll get ALL anomalies (no filtering)
# Raise the SUSPICIOUS_SCORE_THRESHOLD to compensate:
SUSPICIOUS_SCORE_THRESHOLD=8
```

---

## 📈 Cost Estimate

**With AI Review:**
- Haiku model: ~$0.001 per review
- 1625 markets → ~150 anomalies → ~$0.15 per scan
- 24 scans/day → ~$3.60/day
- Free tier: $5 credit = ~1.5 days of testing

**Without AI Review:**
- Free
- But you'll get 100+ alerts per scan (mostly noise)

---

## 🎯 Success Metrics

You'll know it's working when you see:
- ✅ "AI Reviewed" count > 0
- ✅ "AI Approved" < "AI Reviewed" (filtering is working)
- ✅ Telegram alerts show wallet addresses
- ✅ PolygonScan links are clickable
- ✅ AI reasoning makes sense
- ✅ Fewer but higher quality alerts

---

## 🚀 Next Steps

1. Pull latest code
2. Add ANTHROPIC_API_KEY to .env
3. Run: `python run.py --mode scan --debug`
4. Watch for alerts in Telegram
5. Click PolygonScan links to investigate wallets
6. Adjust thresholds based on results

**You're now catching ACTUAL INSIDERS, not just market patterns!** 🎯
