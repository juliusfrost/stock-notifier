import asyncio
import random
import re
import time
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

import aiohttp
import pytz

from stock_notifier import config, models
from stock_notifier.interface import notify
from stock_notifier.logger import logger

# Configuration
sleep_seconds_config = config.get("sleep_seconds", {})
SLEEP_SAME_HOST = sleep_seconds_config.get("same_host", 1)
SLEEP_GLOBAL = sleep_seconds_config.get("global", 60)
SLEEP_GLOBAL_JITTER = sleep_seconds_config.get("global_jitter", 10)
CONCURRENT_HOSTS_LIMIT = config.get("concurrent_hosts_limit", 20)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "DNT": "1",
}

# Timezone configuration
EASTERN_TZ = pytz.timezone("US/Eastern")
WORK_HOURS_START = 8
WORK_HOURS_END = 16


def in_work_hours() -> bool:
    """Check if current time is within work hours in Eastern Time"""
    now = datetime.now(EASTERN_TZ)
    return WORK_HOURS_START <= now.hour < WORK_HOURS_END


async def get_html(url, session):
    retries = 3
    for attempt in range(retries):
        try:
            async with session.get(url) as response:
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == retries - 1:
                logger.error(f"Final failed fetching {url}: {e}")
                raise e
            wait = 2**attempt
            logger.warning(f"Retry {attempt + 1}/{retries} for {url} in {wait}s")
            await asyncio.sleep(wait)


async def check(product: models.Product, session: aiohttp.ClientSession):
    logger.info(
        f"Checking {product.name} for indicator {product.indicator} at {product.url}"
    )

    try:
        html = await get_html(product.url, session)
        if re.search(product.indicator, html, re.DOTALL):
            await notify(product)
    except Exception as e:
        logger.exception(f"Critical error checking {product.name}: {e}")


async def get_products():
    async with models.global_async_session() as session:
        return await session.scalars(models.select(models.Product))


async def check_product_list(host_products: list[models.Product]):
    connector = aiohttp.TCPConnector(limit=5)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        timeout=timeout, connector=connector, headers=HEADERS
    ) as session:
        for i, product in enumerate(host_products):
            try:
                await check(product, session)
                if i < len(host_products) - 1:
                    jitter = random.uniform(-0.5, 0.5)
                    await asyncio.sleep(max(SLEEP_SAME_HOST + jitter, 0.1))
            except Exception as e:
                logger.error(f"Error checking product {product.name}: {e}")


async def check_products():
    products = await get_products()
    hosts = defaultdict(list)
    for p in products:
        o = urlparse(p.url)
        hosts[o.hostname].append(p)

    semaphore = asyncio.Semaphore(CONCURRENT_HOSTS_LIMIT)

    async def limited_task(host_products):
        async with semaphore:
            await check_product_list(host_products)

    tasks = []
    for host_products in hosts.values():
        tasks.append(asyncio.create_task(limited_task(host_products)))

    await asyncio.gather(*tasks)


async def scraper_loop():
    while True:
        start_check_time = time.time()
        logger.info("Checking product stock...")
        try:
            await check_products()
        except Exception as e:
            logger.error(f"Error in main check cycle: {e}")
        finish_check_time = time.time()
        time_spent_checking = finish_check_time - start_check_time

        # Determine base sleep time based on work hours
        if in_work_hours():
            base_sleep = SLEEP_GLOBAL
        else:
            base_sleep = 2 * SLEEP_GLOBAL  # double sleep outside work hours

        jitter = random.uniform(-SLEEP_GLOBAL_JITTER, SLEEP_GLOBAL_JITTER)
        sleep_time = max(base_sleep - time_spent_checking + jitter, 0)

        logger.info(
            f"Time spent checking stock: {round(time_spent_checking, 2)} seconds\n"
            f"Base sleep: {base_sleep}s, Jitter: {round(jitter, 2)}s\n"
            f"Sleeping for {round(sleep_time, 2)} seconds..."
        )
        await asyncio.sleep(sleep_time)
