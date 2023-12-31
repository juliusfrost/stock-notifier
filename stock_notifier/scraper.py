import asyncio

import aiohttp

from stock_notifier import models
from stock_notifier.interface import notify


async def check(product: models.Product):
    async with aiohttp.ClientSession() as session:
        async with session.get(product.url) as response:
            html = await response.text()

    if product.indicator in html:
        await notify(product)


async def get_products():
    async with models.global_async_session() as session:
        return await session.scalars(models.select(models.Product))


async def check_products():
    tasks = [asyncio.create_task(check(product)) for product in await get_products()]
    await asyncio.gather(*tasks)


async def scraper_loop(sleep_time=10):
    while True:
        await check_products()
        await asyncio.sleep(sleep_time)
