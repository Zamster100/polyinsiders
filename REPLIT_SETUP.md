# Deploying to Replit (24/7 Always-On Bot)

This guide will help you deploy your Polymarket Insider Tracker to Replit so it runs 24/7 automatically.

## Why Replit?

- ✅ **Free tier available** (with always-on option on paid plans)
- ✅ **No server management** needed
- ✅ **Automatic restarts** if the bot crashes
- ✅ **Built-in monitoring**
- ✅ **Easy environment variable management**

---

## Step-by-Step Setup

### Step 1: Create a Replit Account

1. Go to [https://replit.com](https://replit.com)
2. Sign up for a free account (or log in)

### Step 2: Import Your GitHub Repository

1. Click **"+ Create Repl"** button
2. Select **"Import from GitHub"**
3. Paste your repository URL:
   ```
   https://github.com/Zamster100/polyinsiders
   ```
4. Select the branch: `claude/polymarket-insider-tracker-fqHga`
5. Click **"Import from GitHub"**

### Step 3: Configure Environment Variables (Secrets)

**IMPORTANT:** Don't put your tokens in the code or `.env` file on Replit!

1. In your Repl, click the **"Secrets"** tab (🔒 lock icon in left sidebar)
2. Click **"+ New Secret"**
3. Add each of these secrets:

| Key | Value | Example |
|-----|-------|---------|
| `TELEGRAM_ENABLED` | `true` | `true` |
| `TELEGRAM_BOT_TOKEN` | Your bot token | `8546791791:AAE4oIuX7FR2Zx2v8i5TxaCI3gxfuIzxDEk` |
| `TELEGRAM_CHAT_ID` | Your chat/group ID | `399191729` or `-1001234567890` |
| `MIN_BET_SIZE` | Minimum bet to track | `1000` |
| `SUSPICIOUS_SCORE_THRESHOLD` | Alert threshold | `7` |
| `POLL_INTERVAL` | Seconds between scans | `60` |
| `LOG_LEVEL` | Logging level | `INFO` |

**Pro tip:** For group notifications, use the negative group ID (starts with `-100`)

### Step 4: Install Dependencies

Replit will automatically detect `requirements.txt` and install packages.

If not, run this in the Shell:
```bash
pip install -r requirements.txt
```

### Step 5: Run the Bot

1. Click the green **"Run"** button at the top
2. The bot will start monitoring Polymarket
3. You should see output like:
   ```
   INFO     Telegram notifications enabled for chat 399191729
   INFO     Keep-alive server started for Replit
   INFO     Starting Polymarket Insider Tracker...
   ```

### Step 6: View the Status Page

Once running, Replit will provide a URL like:
```
https://your-repl-name.your-username.repl.co
```

Visit this URL to see a status page showing the bot is online!

---

## Making It Always-On (24/7)

### Option A: Free Tier with UptimeRobot (Recommended)

The free Replit tier sleeps after ~1 hour of inactivity. To keep it awake:

1. **Get your Repl URL** (e.g., `https://polyinsiders.yourusername.repl.co`)

2. **Sign up for UptimeRobot** (free):
   - Go to [https://uptimerobot.com](https://uptimerobot.com)
   - Create a free account

3. **Create a Monitor**:
   - Click "+ Add New Monitor"
   - Monitor Type: **HTTP(s)**
   - Friendly Name: `Polymarket Bot`
   - URL: `https://your-repl-name.your-username.repl.co/health`
   - Monitoring Interval: **5 minutes**
   - Click "Create Monitor"

This will ping your bot every 5 minutes, keeping it awake 24/7!

### Option B: Replit Always-On (Paid)

If you have Replit Hacker plan ($7/month):

1. Go to your Repl settings
2. Enable **"Always On"**
3. Your bot will run 24/7 without external pinging

---

## Monitoring Your Bot

### Check Bot Status

**Web Interface:**
Visit `https://your-repl.repl.co` to see if the bot is online

**Health Check API:**
Visit `https://your-repl.repl.co/health` to get JSON status

### View Logs

In Replit, check the **Console** tab to see:
- Scan progress
- Alerts triggered
- Any errors

### View Statistics

Run this command in the Replit Shell:
```bash
python run.py --stats
```

### View Flagged Wallets

```bash
python view_wallets.py
```

---

## Troubleshooting

### Bot Not Starting

**Check Secrets:**
- Make sure all required secrets are set in the Secrets tab
- Don't use quotes around secret values
- Secret names are case-sensitive

**Check Dependencies:**
```bash
pip install -r requirements.txt
```

### Bot Stops After an Hour

**Solution:** Set up UptimeRobot (see "Option A" above)

### Not Receiving Telegram Messages

1. **Test your bot token:**
   ```bash
   python test_telegram.py
   ```

2. **Check your chat ID:**
   - For groups, use negative ID like `-1001234567890`
   - Make sure bot is added to the group
   - Make sure `TELEGRAM_ENABLED=true`

3. **Check logs** for error messages

### Database Issues

The SQLite database is stored in your Repl. If you need to reset it:

```bash
rm polymarket_tracker.db
python run.py
```

---

## Adjusting Settings on Replit

To change bot settings:

1. Go to **Secrets** tab
2. Find the secret you want to change (e.g., `SUSPICIOUS_SCORE_THRESHOLD`)
3. Click the **edit** icon
4. Change the value
5. **Restart the bot** (click Stop, then Run)

---

## Cost Breakdown

| Option | Cost | Always-On? | Setup Difficulty |
|--------|------|------------|------------------|
| **Free Replit + UptimeRobot** | $0/month | ✅ Yes* | Easy |
| **Replit Hacker Plan** | $7/month | ✅ Yes | Very Easy |
| **Replit Pro Plan** | $20/month | ✅ Yes + More resources | Very Easy |

*UptimeRobot keeps it running ~23/7 with occasional brief downtime

---

## Advanced: Scheduled Scanning

If you only want to scan during certain hours:

1. Add to Secrets:
   ```
   SCAN_START_HOUR=8
   SCAN_END_HOUR=22
   ```

2. This would only scan from 8 AM to 10 PM UTC

*(This feature would require code modification)*

---

## Backup Your Data

Your database is stored on Replit. To back it up:

1. Download `polymarket_tracker.db` from Files tab
2. Or export wallets:
   ```bash
   python view_wallets.py list 0 > flagged_wallets.txt
   ```

---

## Next Steps After Deployment

1. ✅ Monitor the first 24 hours to ensure alerts are working
2. ✅ Adjust `SUSPICIOUS_SCORE_THRESHOLD` based on alert volume
3. ✅ Set up UptimeRobot if using free tier
4. ✅ Check Telegram daily to see if you're getting alerts
5. ✅ Run `python view_wallets.py` weekly to see flagged wallets

---

## Support

If you run into issues:

1. Check the **Console** tab in Replit for error messages
2. Run `python test_telegram.py` to test notifications
3. Check that all Secrets are set correctly
4. View logs with `--debug` mode:
   ```bash
   python run.py --debug
   ```

---

**Your bot is now running 24/7 on Replit!** 🚀

It will automatically:
- Scan Polymarket every 60 seconds
- Detect suspicious trading patterns
- Send Telegram alerts when anomalies are found
- Store wallet data in SQLite for later analysis
- Restart if it crashes

Just let it run and check your Telegram for alerts!
