import asyncio
import re
import time
from collections import defaultdict
from urllib.parse import urlparse

import aiohttp

from stock_notifier import config, models
from stock_notifier.interface import notify
from stock_notifier.logger import logger

sleep_seconds_config = config.get("sleep_seconds", {})
SLEEP_SAME_HOST = sleep_seconds_config.get("same_host", 1)
SLEEP_GLOBAL = sleep_seconds_config.get("global", 10)


async def get_html(url, session):
    try:
        async with session.get(url) as response:
            return await response.text()
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        raise


async def check(product: models.Product, session: aiohttp.ClientSession):
    logger.info(
        f"Checking {product.name} for indicator {product.indicator} at {product.url}"
    )

    html = await get_html(product.url, session)

    if re.search(product.indicator, html, re.DOTALL):
        await notify(product)


async def get_products():
    async with models.global_async_session() as session:
        return await session.scalars(models.select(models.Product))


async def check_product_list(host_products: list[models.Product]):
    async with aiohttp.ClientSession() as session:
        for i, product in enumerate(host_products):
            try:
                await check(product, session)
                # Sleep between checking products of the same host
                if i < len(host_products) - 1:
                    await asyncio.sleep(SLEEP_SAME_HOST)
            except Exception as e:
                logger.error(f"Error checking product {product.name}: {e}")


async def check_products():
    products = await get_products()
    hosts = defaultdict(list)
    for p in products:
        o = urlparse(p.url)
        hosts[o.hostname].append(p)

    tasks = []
    for host_products in hosts.values():
        tasks.append(asyncio.create_task(check_product_list(host_products)))

    await asyncio.gather(*tasks)


async def scraper_loop():
    while True:
        start_check_time = time.time()
        logger.info("Checking product stock...")
        await check_products()
        finish_check_time = time.time()
        time_spent_checking = finish_check_time - start_check_time
        logger.info(
            f"Time spent checking stock: {round(time_spent_checking, 2)} seconds"
        )
        sleep_time = max(SLEEP_GLOBAL - time_spent_checking, 0)
        logger.info(f"Sleeping for {round(sleep_time, 2)} seconds...")
        await asyncio.sleep(sleep_time)
