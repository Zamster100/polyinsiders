"""Inspect what fields are actually in the market object"""
import asyncio
import aiohttp
import json


async def inspect_market():
    print("="*60)
    print("INSPECTING POLYMARKET MARKET STRUCTURE")
    print("="*60)

    async with aiohttp.ClientSession() as session:
        url = 'https://gamma-api.polymarket.com/events?tagId=2&active=true&closed=false&limit=1'

        async with session.get(url) as r:
            events = await r.json()

            if events and len(events) > 0:
                event = events[0]
                print(f"\n📋 EVENT FIELDS:")
                print(json.dumps(list(event.keys()), indent=2))

                markets = event.get('markets', [])
                if markets:
                    market = markets[0]
                    print(f"\n📋 MARKET FIELDS:")
                    print(json.dumps(list(market.keys()), indent=2))

                    print(f"\n📝 MARKET DATA:")
                    print(json.dumps(market, indent=2))

                    # Look for ID fields
                    print(f"\n🔍 POTENTIAL ID FIELDS:")
                    for key in market.keys():
                        if 'id' in key.lower() or 'token' in key.lower():
                            print(f"   {key}: {market[key]}")


if __name__ == "__main__":
    asyncio.run(inspect_market())
