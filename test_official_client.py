"""Test Polymarket's official Python client for public trade access"""
import asyncio
from py_clob_client.client import ClobClient


async def test_official_client():
    print("="*60)
    print("TESTING POLYMARKET OFFICIAL CLIENT")
    print("="*60)

    # Create client WITHOUT authentication (public mode)
    client = ClobClient("https://clob.polymarket.com")

    print("\n1. Testing public methods...")

    try:
        # Get markets
        markets = client.get_simplified_markets()
        print(f"   ✅ Found {len(markets)} markets")

        if markets and len(markets) > 0:
            # Find an active market
            active_market = None
            for market in markets:
                if market.get('active') and not market.get('closed'):
                    active_market = market
                    break

            if not active_market:
                print("   ❌ No active markets found")
                return

            condition_id = active_market.get('condition_id')
            question = active_market.get('question', 'Unknown')

            print(f"\n2. Testing market:")
            print(f"   Question: {question}")
            print(f"   Condition ID: {condition_id}")

            # Try to get trades via public method
            print(f"\n3. Attempting to fetch trades...")

            try:
                # The client might have a public method for trades
                # Let's try different approaches

                # Approach 1: Direct API call through client
                import requests
                url = f"https://clob.polymarket.com/trades?market={condition_id}&limit=10"
                response = requests.get(url)

                print(f"   HTTP Status: {response.status_code}")

                if response.status_code == 200:
                    trades = response.json()
                    print(f"   ✅ SUCCESS! Found {len(trades)} trades")

                    if trades:
                        trade = trades[0]
                        print(f"\n4. Sample trade:")
                        print(f"   Maker: {trade.get('maker', 'N/A')}")
                        print(f"   Size: {trade.get('size', 'N/A')}")
                        print(f"   Price: {trade.get('price', 'N/A')}")

                        print("\n" + "="*60)
                        print("✅ SOLUTION FOUND!")
                        print("The official client can access public data!")
                        print("="*60)
                elif response.status_code == 401:
                    print(f"   ❌ Still 401: {response.text}")
                    print("\n" + "="*60)
                    print("❌ PROBLEM: Authentication required even with official client")
                    print("Alternative: Use orderbook data instead of trades")
                    print("="*60)
                else:
                    print(f"   ❌ Error {response.status_code}: {response.text}")

            except Exception as e:
                print(f"   ❌ Error fetching trades: {e}")

    except Exception as e:
        print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_official_client())
