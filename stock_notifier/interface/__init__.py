import stock_notifier.interface.discord
from stock_notifier.product import Product


def notify(product: Product):
    stock_notifier.interface.discord.notify(product)
