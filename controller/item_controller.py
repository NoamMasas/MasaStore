from typing import List, Literal, Optional

from fastapi import APIRouter, Path, Query
from starlette import status

from model.item import Item
from service import item_service

router = APIRouter(
    prefix="/item",
    tags=["item"],
)


@router.get("/", response_model=List[Item], status_code=status.HTTP_200_OK)
async def get_all_items():
    return await item_service.get_all_items()


@router.get("/search/", response_model=List[Item], status_code=status.HTTP_200_OK)
async def search_items(
    name: Optional[str] = Query(None),
    stock_op: Optional[Literal["lt", "gt", "eq"]] = Query(None),
    stock_value: Optional[int] = Query(None),
    price_op: Optional[Literal["lt", "gt", "eq"]] = Query(None),
    price_value: Optional[float] = Query(None),
):
    return await item_service.search_items(name, stock_op, stock_value, price_op, price_value)


@router.get("/{item_id}", response_model=Item, status_code=status.HTTP_200_OK)
async def get_item_by_id(item_id: int = Path(gt=0)):
    return await item_service.get_item_by_id(item_id)
