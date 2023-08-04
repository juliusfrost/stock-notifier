import asyncio

import aiohttp

from stock_notifier.product import Product, all_products
from stock_notifier.interface import notify


async def check(product: Product):
    async with aiohttp.ClientSession() as session:
        async with session.get(product.url) as response:
            html = await response.text()
    if product.indicator in html:
        await notify(product)
        user_products = all_products[product.discord_user_id]
        del user_products[product.name]


async def get_products():
    for user_products in all_products.values():
        for product in user_products.values():
            yield product


async def check_products():
    tasks = [asyncio.create_task(check(product)) async for product in get_products()]
    await asyncio.gather(*tasks)


async def scraper_loop(sleep_time=10):
    while True:
        await check_products()
        await asyncio.sleep(sleep_time)
