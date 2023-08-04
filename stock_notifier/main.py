import asyncio
from stock_notifier.interface.discord import start_bot
from stock_notifier.scraper import scraper_loop


async def main():
    tasks = [asyncio.create_task(start_bot()), asyncio.create_task(scraper_loop())]
    await asyncio.gather(*tasks)


def run():
    # https://github.com/Pycord-Development/pycord/issues/872#issuecomment-1111596201
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


if __name__ == "__main__":
    run()
