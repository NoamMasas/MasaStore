from typing import List, Optional

from exceptions.exception import item_not_found_exception
from model.item import Item
from repository import item_repository


async def get_all_items() -> List[Item]:
    return await item_repository.get_all_items()


async def get_item_by_id(item_id: int) -> Item:
    item = await item_repository.get_item_by_id(item_id)
    if item is None:
        raise item_not_found_exception()
    return item


async def search_items(
    name: Optional[str],
    stock_op: Optional[str],
    stock_value: Optional[int],
    price_op: Optional[str],
    price_value: Optional[float],
) -> List[Item]:
    return await item_repository.search_items(name, stock_op, stock_value, price_op, price_value)
