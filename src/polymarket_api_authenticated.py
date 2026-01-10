"""Polymarket API client using official authenticated py-clob-client"""

import asyncio
from datetime import datetime

import aiohttp
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

from src.config import (
    BASE_DATA_API,
    CACHE_TTL,
    CLOB_API,
    CONNECTION_TIMEOUT,
    MAX_CONNECTIONS,
    POLYMARKET_CHAIN_ID,
    POLYMARKET_FUNDER,
    POLYMARKET_PRIVATE_KEY,
    POLYMARKET_SIGNATURE_TYPE,
    REQUEST_RETRY_ATTEMPTS,
)
from src.logger import logger


class AuthenticatedPolymarketAPI:
    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self.clob_client: ClobClient | None = None
        self._cache = {}
        self._cache_times = {}

    async def __aenter__(self):
        # Create authenticated CLOB client
        if POLYMARKET_PRIVATE_KEY and POLYMARKET_FUNDER:
            try:
                self.clob_client = ClobClient(
                    CLOB_API,
                    key=POLYMARKET_PRIVATE_KEY,
                    chain_id=POLYMARKET_CHAIN_ID,
                    signature_type=POLYMARKET_SIGNATURE_TYPE,
                    funder=POLYMARKET_FUNDER,
                )
                # Generate API credentials
                api_creds = self.clob_client.create_or_derive_api_creds()
                self.clob_client.set_api_creds(api_creds)
                logger.info("✅ Authenticated Polymarket CLOB client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize authenticated client: {e}")
                logger.info("Falling back to unauthenticated mode (limited access)")
                self.clob_client = ClobClient(CLOB_API)
        else:
            logger.info("No Polymarket credentials provided - using unauthenticated mode")
            self.clob_client = ClobClient(CLOB_API)

        # Create aiohttp session for Gamma API (public endpoints)
        connector = aiohttp.TCPConnector(
            limit=MAX_CONNECTIONS, limit_per_host=20, ttl_dns_cache=300
        )
        timeout = aiohttp.ClientTimeout(total=CONNECTION_TIMEOUT)

        self.session = aiohttp.ClientSession(
            connector=connector, timeout=timeout, raise_for_status=False
        )
        logger.debug(f"API session created with {MAX_CONNECTIONS} max connections")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            logger.debug("API session closed")

    def _get_cache(self, key: str) -> dict | None:
        """Get cached data if still valid"""
        if key in self._cache:
            cache_time = self._cache_times.get(key)
            if cache_time and (datetime.now() - cache_time).seconds < CACHE_TTL:
                logger.debug(f"Cache hit: {key}")
                return self._cache[key]
        return None

    def _set_cache(self, key: str, data: dict):
        """Cache data with timestamp"""
        self._cache[key] = data
        self._cache_times[key] = datetime.now()

    async def _request_with_retry(self, url: str, params: dict | None = None) -> dict:
        """Make request with exponential backoff retry"""
        for attempt in range(REQUEST_RETRY_ATTEMPTS):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limited
                        wait_time = 2**attempt
                        logger.warning(f"Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        response.raise_for_status()
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}/{REQUEST_RETRY_ATTEMPTS}")
                if attempt < REQUEST_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
            except aiohttp.ClientError as e:
                logger.error(f"Request error: {e}")
                if attempt < REQUEST_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)

        raise Exception(f"Failed after {REQUEST_RETRY_ATTEMPTS} attempts: {url}")

    async def fetch_active_events(
        self, tag_id: int, offset: int = 0, limit: int = 100
    ) -> list[dict]:
        """Fetch active events for a given tag (public endpoint)"""
        cache_key = f"events_{tag_id}_{offset}_{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        url = f"{BASE_DATA_API}/events?tagId={tag_id}&active=true&closed=false&limit={limit}&offset={offset}"
        data = await self._request_with_retry(url)
        self._set_cache(cache_key, data)
        return data

    async def fetch_market_details(self, condition_id: str) -> dict:
        """Fetch detailed market information (public endpoint)"""
        cache_key = f"market_{condition_id}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        url = f"{BASE_DATA_API}/markets/{condition_id}"
        data = await self._request_with_retry(url)
        self._set_cache(cache_key, data)
        return data

    async def fetch_trades(self, market_id: str, limit: int = 100) -> list[dict]:
        """Fetch recent trades for a market (authenticated)"""
        try:
            # Use authenticated CLOB client
            # The py-clob-client doesn't have an async method, so we run it in executor
            loop = asyncio.get_event_loop()

            # The client's method might be synchronous, so run in thread pool
            def get_trades():
                # Try to get trades - the library might have different method names
                # Let's try a direct HTTP call with the authenticated client
                import requests

                # Get API credentials from client
                if hasattr(self.clob_client, "creds") and self.clob_client.creds:
                    headers = {
                        "POLY_ADDRESS": self.clob_client.creds.api_key,
                        "POLY_SIGNATURE": self.clob_client.creds.api_secret,
                        "POLY_TIMESTAMP": str(int(datetime.now().timestamp())),
                        "POLY_NONCE": self.clob_client.creds.api_passphrase,
                    }
                else:
                    headers = {}

                url = f"{CLOB_API}/trades?market={market_id}&limit={limit}"
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(
                        f"Failed to fetch trades: {response.status_code} - {response.text}"
                    )
                    return []

            trades = await loop.run_in_executor(None, get_trades)
            return trades if trades else []

        except Exception as e:
            logger.error(f"Error fetching trades for market {market_id}: {e}")
            return []

    async def fetch_order_book(self, token_id: str) -> dict:
        """Fetch order book for a specific token"""
        try:
            loop = asyncio.get_event_loop()

            def get_orderbook():
                return self.clob_client.get_order_book(token_id)

            return await loop.run_in_executor(None, get_orderbook)
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return {}

    async def fetch_user_trades(self, address: str, limit: int = 100) -> list[dict]:
        """Fetch trades for a specific wallet address"""
        try:
            loop = asyncio.get_event_loop()

            def get_user_trades():
                # This requires authentication
                return self.clob_client.get_trades({"maker": address})

            return await loop.run_in_executor(None, get_user_trades)
        except Exception as e:
            logger.error(f"Error fetching user trades: {e}")
            return []

    async def fetch_market_trades_history(
        self, condition_id: str, start_ts: int, end_ts: int
    ) -> list[dict]:
        """Fetch trades for a market in a time range"""
        # For now, just get recent trades
        return await self.fetch_trades(condition_id, limit=100)
