import re
from typing import List

import discord
import validators
from dotenv import dotenv_values

from stock_notifier import models
from stock_notifier.logger import logger

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
    name="register_product",
    description="Register a URL to check if a product is in stock.",
)
async def register_product(
    ctx: discord.ApplicationContext,
    name: discord.Option(str, description="Name of the product for later reference."),
    url: discord.Option(str, description="URL to the product page."),
    indicator: discord.Option(
        str,
        description="Text to search in the HTML to check if the product is in stock.",
    ),
    regex: discord.Option(
        bool,
        default=False,
        description="Whether to interpret the indicator as a regular expression.",
    ),
):
    if not validators.url(url):
        await respond(ctx, f"URL provided isn't valid! URL: {url}")
        return
    if not regex:
        indicator = re.escape(indicator)
    product = await models.add_product(name, url, indicator)
    await respond(ctx, f"Successfully registered product: {product}")


@bot.slash_command(name="sign_up", description="Sign up as a user.")
async def register_user(ctx: discord.ApplicationContext):
    user = await models.add_discord_user_if_not_exist(ctx.user.name, ctx.user.id)
    await respond(ctx, f"Signed up as: {user}")


@bot.slash_command(
    name="list_products",
    description="List all products available to subscribe for in-stock notifications.",
)
async def list_products(
    ctx: discord.ApplicationContext,
    verbose: discord.Option(
        bool,
        default=False,
        description="Whether to print a verbose output.",
    ),
):
    if verbose:
        message = "Available products:"
        for product in await models.get_products():
            message += f"\n{product}"
    else:
        message = "Available products:"
        for name in await models.get_product_names():
            message += f"\n{name}"
    await respond(ctx, message)


async def get_unsubscribed_product_names(ctx: discord.AutocompleteContext) -> List[str]:
    return await models.get_unsubscribed_product_names(ctx.interaction.user.id)


def filter_kwargs(kwargs: dict):
    del_keys = []
    for key, val in kwargs.items():
        if isinstance(val, str) and val == "":
            del_keys.append(key)
        elif isinstance(val, int) and val < 1:
            del_keys.append(key)
    for key in del_keys:
        del kwargs[key]


@bot.slash_command(
    name="subscribe", description="Subscribe to receive notifications for a product."
)
async def subscribe(
    ctx: discord.ApplicationContext,
    id: discord.Option(
        int,
        default=-1,
        min_value=1,
        description="Product id.",
    ),
    name: discord.Option(
        str,
        default="",
        autocomplete=get_unsubscribed_product_names,
        description="Product name.",
    ),
    url: discord.Option(str, default="", description="Product URL."),
    indicator: discord.Option(str, default="", description="Product indicator."),
):
    kwargs = dict(id=id, name=name, url=url, indicator=indicator)
    filter_kwargs(kwargs)

    user = await models.add_discord_user_if_not_exist(ctx.user.name, ctx.user.id)
    subscribed_products = await models.add_discord_subscription(
        user.discord_id, **kwargs
    )
    for product in subscribed_products:
        await respond(ctx, f"Subscribed to product: {product}")
    if len(subscribed_products) == 0:
        await respond(ctx, "No products subscribed.")


async def get_subscribed_product_names(ctx: discord.AutocompleteContext) -> List[str]:
    return await models.get_subscribed_product_names(ctx.interaction.user.id)


@bot.slash_command(
    name="unsubscribe", description="Unsubscribe to remove notifications for a product."
)
async def unsubscribe(
    ctx: discord.ApplicationContext,
    id: discord.Option(
        int,
        default=-1,
        min_value=1,
        description="Product id.",
    ),
    name: discord.Option(
        str,
        default="",
        autocomplete=get_subscribed_product_names,
        description="Product name.",
    ),
    url: discord.Option(str, default="", description="Product URL."),
    indicator: discord.Option(str, default="", description="Product indicator."),
):
    kwargs = dict(id=id, name=name, url=url, indicator=indicator)
    filter_kwargs(kwargs)

    unsubbed_products = await models.remove_discord_subscription(ctx.user.id, **kwargs)
    if len(unsubbed_products) == 0:
        await respond(ctx, f"Couldn't find subscribed products with name {name}")
        return
    for p in unsubbed_products:
        await respond(ctx, f"Unsubscribed from product: {p}")


async def notify(discord_id: int, product: models.Product):
    try:
        user = await bot.fetch_user(discord_id)
    except discord.NotFound:
        logger.exception(f"Couldn't find discord user id: {discord_id}")
        await models.remove_discord_subscription(discord_id)
        return

    try:
        await dm(user, f"Product {product.name} in stock! URL: {product.url}")
    except discord.Forbidden:
        logger.warning(f"Don't have permission to message user: {user}")
        return

    removed_subscription = await models.remove_discord_subscription(
        discord_id, id=product.id
    )
    if removed_subscription:
        await dm(user, f"Removed subscription to: {product}")


@bot.slash_command(
    name="test_notify", description="The bot notifies you with a direct message."
)
async def test_notify(ctx: discord.ApplicationContext):
    try:
        await dm(
            ctx.author,
            f"Hello {ctx.author.display_name}! "
            f"I will message you again when any of your subscribed products are in stock!",
        )
        await respond(ctx, f"I sent a direct message to you. Please verify you got it.")
    except discord.Forbidden:
        await respond(
            ctx,
            f"I couldn't send a direct message. Please check your discord privacy settings.",
        )


async def get_product_names(ctx: discord.AutocompleteContext):
    return await models.get_product_names()


@bot.slash_command(name="delete_product", description="Remove a registered product.")
async def delete_product(
    ctx: discord.ApplicationContext,
    id: discord.Option(
        int,
        default=-1,
        min_value=1,
        description="Product id.",
    ),
    name: discord.Option(
        str,
        default="",
        autocomplete=get_product_names,
        description="Product name.",
    ),
    url: discord.Option(str, default="", description="Product URL."),
    indicator: discord.Option(str, default="", description="Product indicator."),
):
    kwargs = dict(id=id, name=name, url=url, indicator=indicator)
    filter_kwargs(kwargs)

    deleted_products = await models.delete_product(**kwargs)
    if len(deleted_products) == 0:
        await respond(ctx, f"Couldn't find product with arguments: {kwargs}")
        return

    for product in deleted_products:
        await respond(ctx, f"Successfully removed product: {product}")


async def start_bot():
    await bot.start(config["DISCORD_BOT_TOKEN"])
