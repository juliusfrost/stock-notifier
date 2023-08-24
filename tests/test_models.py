import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from stock_notifier.models import *


@pytest.fixture()
async def async_session() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=True,
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_session


@pytest.mark.asyncio
async def test_discord(async_session: async_sessionmaker[AsyncSession]):
    u1 = User(name="bob", discord_id=1)
    p1 = Product(name="candy", url="www.candy.com", indicator="in-stock")
    async with async_session() as session:
        async with session.begin():
            session.add(u1)
            session.add(p1)

    await add_discord_subscription(async_session, u1.discord_id, p1.name)
    await remove_discord_subscription_all(async_session, u1.discord_id, p1.name)

    async with async_session() as session:
        for user in await session.scalars(
            select(User).options(selectinload(User.products))
        ):
            assert isinstance(user, User)
            assert len(user.products) == 0
        for product in await session.scalars(
            select(Product).options(selectinload(Product.subscribers))
        ):
            assert isinstance(product, Product)
            assert len(product.subscribers) == 0

    async with async_session() as session:
        async with session.begin():
            await session.delete(u1)
            await session.delete(p1)
