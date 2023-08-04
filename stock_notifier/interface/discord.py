import discord
import validators
from dotenv import dotenv_values

from stock_notifier.logging import logger
from stock_notifier.product import Product, all_products

config = dotenv_values(".env")


class StockNotificationBot(discord.Bot):
    pass


bot = StockNotificationBot()


@bot.event
async def on_ready():
    logger.info(f"{bot.user} is ready and online!")


async def respond(ctx: discord.ApplicationContext, message: str):
    await ctx.respond(message, ephemeral=True)
    logger.info(f"Responded to User {ctx.user.name}: {message}")


async def dm(user: discord.User, message: str):
    await user.send(message)
    logger.info(f"DM'ed User {user.name}: {message}")


@bot.slash_command(
    name="register", description="Register a URL to check if a product is in stock."
)
async def register(
    ctx: discord.ApplicationContext,
    name: discord.Option(str, description="Name of the product for later reference."),
    url: discord.Option(str, description="URL to the product page."),
    indicator: discord.Option(
        str,
        description="Text to search in the HTML to check if the product is in stock.",
    ),
):
    if not validators.url(url):
        await respond(ctx, f"URL provided isn't valid! URL: {url}")
        return
    product = Product(name, url, indicator, ctx.user.id)
    all_products[product.discord_user_id][product.name] = product
    await respond(ctx, f"Successfully registered product: {name}")


async def notify(product: Product):
    try:
        user = await bot.fetch_user(product.discord_user_id)
    except discord.NotFound:
        logger.exception(f"Couldn't find discord user id: {product.discord_user_id}")
        return

    try:
        await dm(user, f"Product {product.name} in stock! URL: {product.url}")
    except discord.Forbidden:
        logger.exception(f"Don't have permission to message user: {user}")


def get_user_product_names(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    user_products = all_products[user_id]
    options = list(user_products.keys())
    return options


@bot.slash_command(name="remove", description="Remove a registered product.")
async def remove(
    ctx: discord.ApplicationContext,
    name: discord.Option(
        str,
        autocomplete=get_user_product_names,
        description="Name of the product to remove.",
    ),
):
    user_products = all_products[ctx.user.id]
    if name in user_products:
        del user_products[name]
        await respond(ctx, f"Successfully removed product {name}")
    else:
        await respond(ctx, f"Couldn't find product {name}")


async def start_bot():
    await bot.start(config["DISCORD_BOT_TOKEN"])
