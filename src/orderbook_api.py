"""Simple Polymarket API client for orderbook monitoring (no auth needed)"""

import asyncio
import json
from datetime import datetime

import aiohttp

from src.config import (
    BASE_DATA_API,
    CACHE_TTL,
    CLOB_API,
    CONNECTION_TIMEOUT,
    MAX_CONNECTIONS,
    REQUEST_RETRY_ATTEMPTS,
)
from src.logger import logger


class OrderbookAPI:
    """Lightweight API client for public orderbook data"""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self._cache = {}
        self._cache_times = {}

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=MAX_CONNECTIONS, limit_per_host=20, ttl_dns_cache=300
        )
        timeout = aiohttp.ClientTimeout(total=CONNECTION_TIMEOUT)

        self.session = aiohttp.ClientSession(
            connector=connector, timeout=timeout, raise_for_status=False
        )
        logger.info(f"Orderbook API session created")
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
                if attempt < REQUEST_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
            except aiohttp.ClientError as e:
                if attempt < REQUEST_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)

        raise Exception(f"Failed after {REQUEST_RETRY_ATTEMPTS} attempts: {url}")

    async def fetch_active_events(
        self, tag_id: int, offset: int = 0, limit: int = 100
    ) -> list[dict]:
        """Fetch active events for a given tag"""
        cache_key = f"events_{tag_id}_{offset}_{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        url = f"{BASE_DATA_API}/events?tagId={tag_id}&active=true&closed=false&limit={limit}&offset={offset}"
        data = await self._request_with_retry(url)
        self._set_cache(cache_key, data)
        return data

    async def fetch_orderbook(self, token_id: str) -> dict:
        """Fetch orderbook for a specific token ID (public endpoint)"""
        try:
            url = f"{CLOB_API}/book"
            params = {"token_id": token_id}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    # Market closed or no orderbook
                    logger.debug(f"No orderbook for token {token_id[:20]}...")
                    return {"bids": [], "asks": []}
                else:
                    logger.warning(
                        f"Orderbook fetch failed: {response.status} for {token_id[:20]}..."
                    )
                    return {"bids": [], "asks": []}

        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return {"bids": [], "asks": []}

    async def fetch_market_orderbooks(self, market: dict) -> list[dict]:
        """Fetch orderbooks for all tokens in a market"""
        token_ids_str = market.get('clobTokenIds', '[]')

        try:
            token_ids = json.loads(token_ids_str)
        except:
            logger.warning(f"Could not parse token IDs for market {market.get('question', 'Unknown')[:40]}")
            return []

        if not token_ids:
            return []

        # Fetch orderbooks for both Yes/No tokens
        orderbooks = []
        for i, token_id in enumerate(token_ids):
            ob = await self.fetch_orderbook(token_id)
            ob['token_id'] = token_id
            ob['outcome_index'] = i
            ob['outcome'] = market.get('outcomes', ['Yes', 'No'])[i] if i < 2 else f'Outcome {i}'
            orderbooks.append(ob)

        return orderbooks
