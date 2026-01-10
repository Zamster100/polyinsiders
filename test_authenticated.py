"""Test the authenticated Polymarket API client"""
import asyncio
import sys

# Add src to path
sys.path.insert(0, '.')

from src.polymarket_api_authenticated import AuthenticatedPolymarketAPI
from src.logger import logger


async def test_authenticated_api():
    print("="*60)
    print("TESTING AUTHENTICATED POLYMARKET API")
    print("="*60)

    async with AuthenticatedPolymarketAPI() as api:
        print("\n1. Fetching active markets...")

        try:
            events = await api.fetch_active_events(tag_id=2, limit=5)
            print(f"   ✅ Found {len(events)} events")

            if not events:
                print("   ❌ No events found")
                return

            # Find an active market
            active_market = None
            for event in events:
                markets = event.get('markets', [])
                for market in markets:
                    if market.get('active') and not market.get('closed'):
                        active_market = market
                        break
                if active_market:
                    break

            if not active_market:
                print("   ❌ No active markets found")
                return

            condition_id = active_market.get('conditionId')
            question = active_market.get('question', 'Unknown')

            print(f"\n2. Testing with active market:")
            print(f"   Question: {question}")
            print(f"   Condition ID: {condition_id}")

            print(f"\n3. Fetching trades with AUTHENTICATION...")
            trades = await api.fetch_trades(condition_id, limit=10)

            print(f"   Result: {len(trades)} trades fetched")

            if len(trades) > 0:
                print("\n" + "="*60)
                print("✅ SUCCESS! AUTHENTICATION WORKS!")
                print("="*60)
                print(f"\n4. Sample trade:")
                trade = trades[0]
                print(f"   Maker: {trade.get('maker', 'N/A')}")
                print(f"   Size: {trade.get('size', 'N/A')}")
                print(f"   Price: {trade.get('price', 'N/A')}")
                print(f"   Side: {trade.get('side', 'N/A')}")
                print(f"\n✅ The bot should now work perfectly!")
            elif len(trades) == 0:
                print("\n" + "="*60)
                print("⚠️  API returned empty list (no recent trades)")
                print("This market might not have recent activity")
                print("Try running the full bot - it will scan all markets")
                print("="*60)
            else:
                print("\n" + "="*60)
                print("❌ Still getting errors")
                print("Check your Polymarket credentials in .env")
                print("="*60)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            print("\n" + "="*60)
            print("TROUBLESHOOTING:")
            print("1. Check .env has POLYMARKET_PRIVATE_KEY")
            print("2. Check .env has POLYMARKET_FUNDER")
            print("3. Make sure credentials are correct")
            print("="*60)


if __name__ == "__main__":
    asyncio.run(test_authenticated_api())
