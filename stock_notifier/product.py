from collections import defaultdict
from dataclasses import dataclass
from typing import Dict


@dataclass()
class Product:
    name: str
    url: str
    indicator: str
    discord_user_id: int


all_products: defaultdict[int, Dict[str, Product]] = defaultdict(dict)
