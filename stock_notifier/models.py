from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Integer, String, Table, not_, select
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    selectinload,
)

global_async_session: async_sessionmaker[AsyncSession]


class Base(AsyncAttrs, DeclarativeBase):
    pass


subscription_table = Table(
    "subscription_table",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("product_id", ForeignKey("product.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    discord_id: Mapped[Optional[int]] = mapped_column(
        Integer(), unique=True, nullable=True
    )
    products: Mapped[List["Product"]] = relationship(
        secondary=subscription_table, back_populates="subscribers", passive_deletes=True
    )

    def __repr__(self) -> str:
        return (
            f"User(id={self.id!r}, name={self.name!r}, discord_id={self.discord_id!r})"
        )


class Product(Base):
    __tablename__ = "product"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    url: Mapped[str] = mapped_column(String(512))
    indicator: Mapped[str] = mapped_column(String(512))
    subscribers: Mapped[List[User]] = relationship(
        secondary=subscription_table, back_populates="products", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"Product(id={self.id!r}, name={self.name!r}, url={self.url!r}, indicator={self.indicator!r})"


async def add_product(name: str, url: str, indicator: str) -> Product:
    async with global_async_session() as session:
        async with session.begin():
            product = Product(name=name, url=url, indicator=indicator)
            session.add(product)
            return product


async def delete_product(**kwargs: dict) -> List[Product]:
    async with global_async_session() as session:
        async with session.begin():
            results = []
            for product in await session.scalars(select(Product).filter_by(**kwargs)):
                assert isinstance(product, Product)
                results.append(product)
                await session.delete(product)
            return results


async def add_discord_user(name: str, discord_id: int) -> User:
    async with global_async_session() as session:
        async with session.begin():
            user = User(name=name, discord_id=discord_id)
            session.add(user)
            return user


async def add_discord_user_if_not_exist(name: str, discord_id: int) -> User:
    async with global_async_session() as session:
        async with session.begin():
            user = await session.scalar(select(User).filter_by(discord_id=discord_id))
            if not user:
                user = User(name=name, discord_id=discord_id)
                session.add(user)
            return user


async def add_discord_subscription(discord_id: int, **kwargs) -> List[Product]:
    """Adds a discord subscription. Returns a list of successfully subscribed products."""
    async with global_async_session() as session:
        async with session.begin():
            user = await session.scalar(select(User).filter_by(discord_id=discord_id))
            assert isinstance(user, User)
            results = []
            for product in await session.scalars(
                select(Product)
                .filter_by(**kwargs)
                .filter(not_(Product.subscribers.any(User.id == user.id)))
                .options(selectinload(Product.subscribers))
            ):
                assert isinstance(product, Product)
                product.subscribers.append(user)
                results.append(product)
            return results


async def remove_discord_subscription(discord_id: int, **kwargs) -> List[Product]:
    async with global_async_session() as session:
        async with session.begin():
            user = await session.scalar(
                select(User)
                .filter_by(discord_id=discord_id)
                .options(selectinload(User.products))
            )
            products_to_remove = []
            for product in await session.scalars(
                select(Product)
                .filter_by(**kwargs)
                .filter(Product.subscribers.any(User.id == user.id))
            ):
                user.products.remove(product)
                products_to_remove.append(product)
            await session.flush()
            return products_to_remove


async def remove_discord_subscription_all(
    discord_id: int, product_name: str
) -> List[Product]:
    async with global_async_session() as session:
        async with session.begin():
            user = await session.scalar(
                select(User)
                .where(User.discord_id == discord_id)
                .options(selectinload(User.products))
            )
            products_to_remove = []
            for product in user.products:
                if product.name == product_name:
                    products_to_remove.append(product)
            for product in products_to_remove:
                user.products.remove(product)
            await session.flush()
            return products_to_remove


async def get_product_names() -> List[str]:
    """Returns a unique set of product names."""
    async with global_async_session() as session:
        results = []
        for product in await session.execute(select(Product.name)):
            assert isinstance(product.name, str)
            results.append(product.name)
        return list(set(results))


async def get_products() -> List[Product]:
    """Returns a unique set of product names."""
    async with global_async_session() as session:
        results = []
        for product in await session.scalars(select(Product)):
            results.append(product)
        return list(results)


async def get_subscribed_product_names(discord_id: int) -> List[str]:
    async with global_async_session() as session:
        results = set()
        user = await session.scalar(
            select(User)
            .filter_by(discord_id=discord_id)
            .options(selectinload(User.products))
        )
        for product in user.products:
            results.add(product.name)
        return list(results)


async def get_unsubscribed_product_names(discord_id: int) -> List[str]:
    """Get a unique list of unsubscribed product names. Returns all product names if no user exists."""
    async with global_async_session() as session:
        user = await session.scalar(select(User).filter_by(discord_id=discord_id))
        if user is None:
            return await get_product_names()
        results = set()
        for product in await session.scalars(
            select(Product).filter(not_(Product.subscribers.any(User.id == user.id)))
        ):
            results.add(product.name)
        return list(results)
