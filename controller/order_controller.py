from typing import List

from fastapi import APIRouter, Depends, Path, Response
from starlette import status

from model.order_request import OrderItemAddRequest
from model.order_response import OrderResponse
from model.user_response import UserResponse
from service import auth_service, order_service

router = APIRouter(
    prefix="/order",
    tags=["order"],
)


# Specific paths declared before /{order_id} — FastAPI matches in order.

@router.get(
    "/user/{user_id}",
    response_model=List[OrderResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_orders(
    user: UserResponse = Depends(auth_service.validate_user),
    user_id: int = Path(gt=0),
):
    return await order_service.get_user_orders(user_id, user)


@router.post(
    "/item/",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
)
async def add_item_to_cart(
    request: OrderItemAddRequest,
    user: UserResponse = Depends(auth_service.validate_user),
):
    return await order_service.add_item_to_cart(request, user)


@router.put(
    "/item/",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
)
async def update_item_in_cart(
    request: OrderItemAddRequest,
    user: UserResponse = Depends(auth_service.validate_user),
):
    return await order_service.update_item_in_cart(request, user)


@router.delete(
    "/item/{order_id}/{item_id}",
    status_code=status.HTTP_200_OK,
)
async def remove_item_from_cart(
    user: UserResponse = Depends(auth_service.validate_user),
    order_id: int = Path(gt=0),
    item_id: int = Path(gt=0),
):
    result = await order_service.remove_item_from_cart(order_id, item_id, user)
    if result is None:
        # Cart became empty and was deleted — no body to return.
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return result


@router.post(
    "/{order_id}/purchase",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
)
async def purchase_order(
    user: UserResponse = Depends(auth_service.validate_user),
    order_id: int = Path(gt=0),
):
    return await order_service.purchase_order(order_id, user)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
)
async def get_order_by_id(
    user: UserResponse = Depends(auth_service.validate_user),
    order_id: int = Path(gt=0),
):
    return await order_service.get_order_by_id(order_id, user)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_order(
    user: UserResponse = Depends(auth_service.validate_user),
    order_id: int = Path(gt=0),
):
    await order_service.delete_order(order_id, user)
