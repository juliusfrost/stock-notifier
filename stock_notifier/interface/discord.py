import discord
import validators
from dotenv import dotenv_values

from stock_notifier.product import Product, all_products

config = dotenv_values(".env")


class StockNotificationBot(discord.Bot):
    pass


bot = StockNotificationBot()


@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")


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
        await ctx.respond(f"URL provided isn't valid! URL: {url}", ephemeral=True)
        return
    product = Product(name, url, indicator, ctx.user.id)
    all_products[product.discord_user_id][product.name] = product
    await ctx.respond(f"Successfully registered product: {name}", ephemeral=True)


async def notify(product: Product):
    try:
        user = await bot.fetch_user(product.discord_user_id)
    except discord.NotFound:
        print(f"Couldn't find discord user id: {product.discord_user_id}")
        return

    try:
        await user.send(f"Product {product.name} in stock! URL: {product.url}")
    except discord.Forbidden:
        print(f"Don't have permission to message user: {user}")


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
        await ctx.respond(f"Successfully removed product {name}", ephemeral=True)
    else:
        await ctx.respond(f"Couldn't find product {name}", ephemeral=True)


async def start_bot():
    await bot.start(config["DISCORD_BOT_TOKEN"])
