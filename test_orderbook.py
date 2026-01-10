"""Test if we can fetch orderbook data from Polymarket (public endpoint)"""
import asyncio
import json
import aiohttp


async def test_orderbook_access():
    print("="*60)
    print("TESTING ORDERBOOK ACCESS (PUBLIC)")
    print("="*60)

    async with aiohttp.ClientSession() as session:
        # Step 1: Get a market with token IDs
        print("\n1. Fetching an active market...")
        gamma_url = "https://gamma-api.polymarket.com/events?tagId=2&active=true&closed=false&limit=1"

        async with session.get(gamma_url) as resp:
            events = await resp.json()

            if not events:
                print("   ❌ No events found")
                return

            event = events[0]
            markets = event.get('markets', [])

            if not markets:
                print("   ❌ No markets in event")
                return

            # Find an ACTIVE market that's accepting orders
            active_market = None
            for m in markets:
                if m.get('active') and not m.get('closed') and m.get('acceptingOrders'):
                    active_market = m
                    break

            # If no active market in first event, try next events
            if not active_market:
                print("   First event has no active markets, trying more...")
                gamma_url2 = "https://gamma-api.polymarket.com/events?tagId=2&active=true&closed=false&limit=20"
                async with session.get(gamma_url2) as resp2:
                    events2 = await resp2.json()
                    for event2 in events2:
                        for m in event2.get('markets', []):
                            if m.get('active') and not m.get('closed') and m.get('acceptingOrders'):
                                active_market = m
                                break
                        if active_market:
                            break

            if not active_market:
                print("   ❌ No active markets found accepting orders")
                return

            market = active_market
            question = market.get('question', 'Unknown')
            clob_token_ids_str = market.get('clobTokenIds', '[]')

            print(f"   Market status:")
            print(f"     Active: {market.get('active')}")
            print(f"     Closed: {market.get('closed')}")
            print(f"     Accepting Orders: {market.get('acceptingOrders')}")

            # Parse the JSON string
            token_ids = json.loads(clob_token_ids_str)

            print(f"   ✅ Found market: {question[:60]}")
            print(f"   Token IDs: {len(token_ids)} tokens")

            if len(token_ids) == 0:
                print("   ❌ No token IDs for this market")
                return

            # Step 2: Fetch orderbook for first token
            token_id = token_ids[0]
            print(f"\n2. Fetching orderbook for token {token_id[:20]}...")

            orderbook_url = f"https://clob.polymarket.com/book?token_id={token_id}"

            async with session.get(orderbook_url) as ob_resp:
                print(f"   HTTP Status: {ob_resp.status}")

                if ob_resp.status == 200:
                    orderbook = await ob_resp.json()

                    bids = orderbook.get('bids', [])
                    asks = orderbook.get('asks', [])

                    print(f"   ✅ Orderbook fetched!")
                    print(f"   Bids: {len(bids)}")
                    print(f"   Asks: {len(asks)}")

                    if bids or asks:
                        print("\n3. Sample orderbook data:")

                        if bids:
                            print(f"\n   Top 3 Bids (buyers):")
                            for i, bid in enumerate(bids[:3], 1):
                                price = bid.get('price', 'N/A')
                                size = bid.get('size', 'N/A')
                                print(f"     {i}. Price: ${price}, Size: {size}")

                        if asks:
                            print(f"\n   Top 3 Asks (sellers):")
                            for i, ask in enumerate(asks[:3], 1):
                                price = ask.get('price', 'N/A')
                                size = ask.get('size', 'N/A')
                                print(f"     {i}. Price: ${price}, Size: {size}")

                        print("\n" + "="*60)
                        print("✅ SUCCESS! ORDERBOOK ACCESS WORKS!")
                        print("We can monitor orderbooks for large orders!")
                        print("="*60)

                        # Calculate some useful metrics
                        if bids and asks:
                            total_bid_size = sum(float(b.get('size', 0)) for b in bids)
                            total_ask_size = sum(float(a.get('size', 0)) for a in asks)

                            print(f"\n4. Orderbook metrics:")
                            print(f"   Total bid volume: ${total_bid_size:,.2f}")
                            print(f"   Total ask volume: ${total_ask_size:,.2f}")

                            if total_bid_size + total_ask_size > 0:
                                imbalance = (total_bid_size - total_ask_size) / (total_bid_size + total_ask_size)
                                print(f"   Orderbook imbalance: {imbalance*100:.1f}%")

                                if abs(imbalance) > 0.3:
                                    print(f"   ⚠️  Strong imbalance detected!")

                    else:
                        print("   ⚠️  Orderbook is empty (no active orders)")

                elif ob_resp.status == 401:
                    error = await ob_resp.text()
                    print(f"   ❌ 401 Unauthorized: {error}")
                    print("\n   PROBLEM: Orderbook also requires auth!")
                else:
                    error = await ob_resp.text()
                    print(f"   ❌ Error {ob_resp.status}: {error}")


if __name__ == "__main__":
    asyncio.run(test_orderbook_access())
