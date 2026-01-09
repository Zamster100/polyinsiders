"""Get Telegram group chat ID"""
import asyncio
import aiohttp
import sys

BOT_TOKEN = "8546791791:AAE4oIuX7FR2Zx2v8i5TxaCI3gxfuIzxDEk"

async def get_group_id():
    """Fetch and display all chat IDs where the bot has been added"""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

    print("Fetching chat IDs...")
    print("\nIMPORTANT: Send a message in your group first (like 'Hello bot')\n")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{api_url}/getUpdates") as response:
            if response.status == 200:
                data = await response.json()

                if not data["result"]:
                    print("❌ No updates found!")
                    print("\nMake sure you:")
                    print("1. Added the bot to your group")
                    print("2. Sent a message in the group")
                    print("3. Run this script again")
                    return

                print("✅ Found these chats:\n")

                seen_chats = set()
                for update in data["result"]:
                    if "message" in update:
                        chat = update["message"]["chat"]
                        chat_id = chat["id"]

                        if chat_id in seen_chats:
                            continue
                        seen_chats.add(chat_id)

                        chat_type = chat["type"]

                        if chat_type in ["group", "supergroup"]:
                            print(f"📢 GROUP: {chat.get('title', 'Unknown')}")
                            print(f"   Chat ID: {chat_id}")
                            print(f"   Type: {chat_type}")
                            print()
                        else:
                            print(f"👤 PRIVATE: {chat.get('first_name', 'Unknown')}")
                            print(f"   Chat ID: {chat_id}")
                            print()

                print("\n" + "="*50)
                print("Copy the GROUP Chat ID and update your .env file:")
                print("TELEGRAM_CHAT_ID=<your_group_chat_id>")
                print("="*50)

            else:
                print(f"❌ Failed to fetch updates: {response.status}")

if __name__ == "__main__":
    asyncio.run(get_group_id())
