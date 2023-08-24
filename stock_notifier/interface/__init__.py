import stock_notifier.interface.discord
from stock_notifier import models
from stock_notifier.logger import logger


async def notify(product: models.Product):
    async with models.global_async_session() as session:
        product = await session.get(models.Product, product.id)
        subscribers = await product.awaitable_attrs.subscribers
    logger.info(f"Notifying for product: {product}")
    for user in subscribers:
        assert isinstance(user, models.User)
        if user.discord_id:
            await stock_notifier.interface.discord.notify(user.discord_id, product)
