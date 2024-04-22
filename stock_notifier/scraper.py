import asyncio
import re

import requests

from stock_notifier import models
from stock_notifier.interface import notify
from stock_notifier.logger import logger


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
    else:
        logger.info(f"No stock available for {product.name}")


async def get_products():
    async with models.global_async_session() as session:
        return await session.scalars(models.select(models.Product))


async def check_products():
    tasks = [asyncio.create_task(check(product)) for product in await get_products()]
    await asyncio.gather(*tasks)


async def scraper_loop(sleep_time=10):
    while True:
        logger.info("Checking product stock...")
        await check_products()
        logger.info(f"Sleeping for {sleep_time} seconds...")
        await asyncio.sleep(sleep_time)
