"""Test Polymarket API to see if trades endpoint is working"""
import asyncio
import aiohttp


async def test_api():
    print("="*60)
    print("TESTING POLYMARKET API")
    print("="*60)

    async with aiohttp.ClientSession() as session:
        # Step 1: Get a market
        print("\n1. Fetching a Politics market...")
        url1 = 'https://gamma-api.polymarket.com/events?tagId=2&active=true&closed=false&limit=1'

        try:
            async with session.get(url1) as r:
                events = await r.json()
                print(f"   ✅ Found {len(events)} events")

                if events and len(events) > 0:
                    event = events[0]
                    print(f"   Event: {event.get('title', 'Unknown')}")

                    markets = event.get('markets', [])
                    if markets:
                        market = markets[0]
                        condition_id = market.get('condition_id')
                        question = market.get('question', 'Unknown')

                        print(f"\n2. Testing market:")
                        print(f"   Question: {question}")
                        print(f"   Condition ID: {condition_id}")

                        # Step 2: Try to get trades
                        url2 = f'https://clob.polymarket.com/trades?market={condition_id}&limit=10'
                        print(f"\n3. Fetching trades from CLOB API...")
                        print(f"   URL: {url2}")

                        async with session.get(url2) as r2:
                            print(f"   HTTP Status: {r2.status}")

                            if r2.status == 200:
                                trades = await r2.json()

                                if isinstance(trades, list):
                                    print(f"   ✅ Trades returned: {len(trades)}")

                                    if len(trades) > 0:
                                        print(f"\n4. Sample trade data:")
                                        trade = trades[0]
                                        print(f"   Maker: {trade.get('maker', 'N/A')}")
                                        print(f"   Size: {trade.get('size', 'N/A')}")
                                        print(f"   Price: {trade.get('price', 'N/A')}")
                                        print(f"   Side: {trade.get('side', 'N/A')}")
                                        print(f"   Timestamp: {trade.get('timestamp', 'N/A')}")

                                        print("\n" + "="*60)
                                        print("✅ SUCCESS! API is working correctly!")
                                        print("="*60)
                                    else:
                                        print(f"\n" + "="*60)
                                        print("❌ PROBLEM: API returned empty list")
                                        print("This market has NO recent trades")
                                        print("="*60)
                                else:
                                    print(f"\n   ❌ API returned: {trades}")
                                    print("\n" + "="*60)
                                    print("❌ PROBLEM: API returned unexpected format")
                                    print("="*60)
                            else:
                                error_text = await r2.text()
                                print(f"   ❌ HTTP Error: {error_text}")
                                print("\n" + "="*60)
                                print("❌ PROBLEM: API request failed")
                                print("="*60)
                    else:
                        print("   ❌ No markets in event")
                else:
                    print("   ❌ No events found")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print("\n" + "="*60)
            print("❌ PROBLEM: Exception occurred")
            print("="*60)


if __name__ == "__main__":
    asyncio.run(test_api())
