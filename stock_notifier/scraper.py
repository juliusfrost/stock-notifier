import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Coroutine, Dict

import aiohttp


@dataclass()
class Product:
    name: str
    url: str
    indicator: str
    user_id: int
    callback: Coroutine


all_products: defaultdict[int, Dict[str, Product]] = defaultdict(dict)


async def check(product: Product):
    async with aiohttp.ClientSession() as session:
        async with session.get(product.url) as response:
            html = await response.text()
    if product.indicator in html:
        await product.callback
        user_products = all_products[product.user_id]
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
