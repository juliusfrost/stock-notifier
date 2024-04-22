import asyncio
import re
import time
from collections import defaultdict
from urllib.parse import urlparse

import requests

from stock_notifier import config, models
from stock_notifier.interface import notify
from stock_notifier.logger import logger

sleep_seconds_config = config.get("sleep_seconds", {})
SLEEP_SAME_HOST = sleep_seconds_config.get("same_host", 1)
SLEEP_GLOBAL = sleep_seconds_config.get("global", 10)


def get_html(url):
    response = requests.get(url)
    return response.text


async def check(product: models.Product):
    logger.info(
        f"Checking {product.name} for indicator {product.indicator} at {product.url}"
    )

    html = await asyncio.to_thread(get_html, product.url)

    if re.match(product.indicator, html, re.DOTALL):
        await notify(product)


async def get_products():
    async with models.global_async_session() as session:
        return await session.scalars(models.select(models.Product))


async def check_product_list(products: list[models.Product]):
    for i, product in enumerate(products):
        await check(product)
        # sleep between checking products of the same host
        if i < len(products) - 1:
            await asyncio.sleep(SLEEP_SAME_HOST)


async def check_products():
    products = await get_products()
    hosts = defaultdict(list)
    for p in products:
        o = urlparse(p.url)
        hosts[o.hostname].append(p)

    tasks = []
    for products in hosts.values():
        tasks.append(asyncio.create_task(check_product_list(products)))

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
