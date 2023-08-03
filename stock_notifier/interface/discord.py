import discord
import os  # default module
from dotenv import load_dotenv

from stock_notifier.scraper import Product, all_products

load_dotenv()  # load all the variables from the env file


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
    async def notify():
        await ctx.user.send(f"Product {name} in stock! URL: {url}")
    product = Product(name, url, indicator, ctx.user.id, notify())
    all_products[product.user_id][product.name] = product
    await ctx.respond(f"Successfully registered product {name}")


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
        await ctx.respond(f"Successfully removed product {name}")
    else:
        await ctx.respond(f"Couldn't find product {name}")


async def start_bot():
    await bot.start(os.getenv("TOKEN"))
