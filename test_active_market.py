"""Test with an ACTIVE market that should have recent trades"""
import asyncio
import aiohttp


async def test_active_market():
    print("="*60)
    print("TESTING ACTIVE MARKET")
    print("="*60)

    async with aiohttp.ClientSession() as session:
        # Get active markets
        url1 = 'https://gamma-api.polymarket.com/events?tagId=2&active=true&closed=false&limit=10'

        async with session.get(url1) as r:
            events = await r.json()
            print(f"\n1. Found {len(events)} active events")

            # Find an ACTIVE market
            active_market = None
            for event in events:
                markets = event.get('markets', [])
                for market in markets:
                    if market.get('active') and not market.get('closed') and market.get('acceptingOrders'):
                        active_market = market
                        break
                if active_market:
                    break

            if not active_market:
                print("   ❌ No active markets found!")
                return

            question = active_market.get('question', 'Unknown')
            condition_id = active_market.get('conditionId')

            print(f"\n2. Testing ACTIVE market:")
            print(f"   Question: {question}")
            print(f"   Condition ID: {condition_id}")
            print(f"   Active: {active_market.get('active')}")
            print(f"   Closed: {active_market.get('closed')}")
            print(f"   Accepting Orders: {active_market.get('acceptingOrders')}")

            # Try to get trades
            url2 = f'https://clob.polymarket.com/trades?market={condition_id}&limit=10'
            print(f"\n3. Fetching trades...")
            print(f"   URL: {url2}")

            async with session.get(url2) as r2:
                print(f"   HTTP Status: {r2.status}")

                if r2.status == 200:
                    trades = await r2.json()
                    if isinstance(trades, list):
                        print(f"   ✅ SUCCESS! Found {len(trades)} trades")

                        if len(trades) > 0:
                            trade = trades[0]
                            print(f"\n4. Sample trade:")
                            print(f"   Maker: {trade.get('maker', 'N/A')}")
                            print(f"   Size: {trade.get('size', 'N/A')}")
                            print(f"   Price: {trade.get('price', 'N/A')}")

                            print("\n" + "="*60)
                            print("✅ BOT SHOULD NOW WORK!")
                            print("="*60)
                        else:
                            print("   ⚠️  Market has no recent trades")
                    else:
                        print(f"   ❌ Unexpected response: {trades}")
                elif r2.status == 401:
                    error = await r2.text()
                    print(f"   ❌ 401 Unauthorized: {error}")
                    print("\n" + "="*60)
                    print("PROBLEM: CLOB API requires authentication")
                    print("Solution needed: Use Polymarket's official Python library")
                    print("="*60)
                else:
                    error = await r2.text()
                    print(f"   ❌ Error {r2.status}: {error}")


if __name__ == "__main__":
    asyncio.run(test_active_market())
