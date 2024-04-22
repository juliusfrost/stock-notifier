import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from stock_notifier import models
from stock_notifier.interface.discord import start_bot
from stock_notifier.scraper import scraper_loop


async def main():
    engine = create_async_engine(
        "sqlite+aiosqlite:///sqlite.db",
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    models.global_async_session = async_session
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    tasks = [asyncio.create_task(start_bot()), asyncio.create_task(scraper_loop())]
    await asyncio.gather(*tasks)


def run():
    # https://github.com/Pycord-Development/pycord/issues/872#issuecomment-1111596201
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


if __name__ == "__main__":
    run()
