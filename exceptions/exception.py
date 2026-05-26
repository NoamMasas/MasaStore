from fastapi import HTTPException
from starlette import status


def username_taken_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provided username already taken",
    )


def user_not_found_exception():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


def item_not_found_exception():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found",
    )


def favorite_already_exists_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Favorite already exists for this user and item",
    )


def favorite_not_found_exception():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Favorite not found",
    )


def order_not_found_exception():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Order not found",
    )


def order_item_not_found_exception():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found in this order",
    )


def out_of_stock_exception(item_name: str):
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Item '{item_name}' is out of stock",
    )


def insufficient_stock_exception(item_name: str, available: int, requested: int):
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Item '{item_name}' has only {available} in stock, you requested {requested}",
    )


def empty_cart_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot purchase an empty cart",
    )


def order_already_closed_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Order is already closed",
    )


def invalid_quantity_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Quantity must be greater than 0",
    )


def session_limit_exception():
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Session prompt limit reached. POST /chat/reset/ to start over.",
    )


def token_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="The token provided is invalid",
    )


def user_credentials_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
    )


def not_authorized_exception():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to perform this action",
    )


def recommendation_model_unavailable_exception():
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Recommendation model is not available",
    )


def chat_service_unavailable_exception():
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Chat assistant is temporarily unavailable. Please try again later.",
    )
