import os
from functools import wraps

import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class APIError(Exception):
    """UI-safe error. Carries a message + HTTP status, never raw exception data."""

    def __init__(self, message: str, status: int = 0):
        self.message = message
        self.status = status
        super().__init__(message)

    def is_auth_expired(self) -> bool:
        return self.status == 401

    def is_rate_limited(self) -> bool:
        return self.status == 429


_GENERIC_5XX = "Something went wrong on the server. Please try again later."
_GENERIC_CONNECTION = "Cannot reach the backend. Is uvicorn running?"
_GENERIC_NETWORK = "Network problem. Please try again."
_GENERIC_4XX_FALLBACK = "Invalid request."


def _extract_4xx_detail(response: requests.Response) -> str:
    # Never raises — falls back to a generic message on any parse issue.
    try:
        body = response.json()
    except Exception:
        return _GENERIC_4XX_FALLBACK

    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, str) and detail:
        return detail
    # FastAPI 422 returns detail as a list of validation-error dicts.
    if isinstance(detail, list) and detail:
        msg = detail[0].get("msg")
        if isinstance(msg, str) and msg:
            return msg
    return _GENERIC_4XX_FALLBACK


def _handle_response_error(e: requests.HTTPError) -> APIError:
    status = e.response.status_code
    if 400 <= status < 500:
        return APIError(_extract_4xx_detail(e.response), status=status)
    return APIError(_GENERIC_5XX, status=status)


def _api_call(func):
    """Wraps a `requests` call; converts any failure into an APIError without leaking internals."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.HTTPError as e:
            raise _handle_response_error(e) from None
        except requests.ConnectionError:
            raise APIError(_GENERIC_CONNECTION) from None
        except requests.RequestException:
            raise APIError(_GENERIC_NETWORK) from None
    return wrapper


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@_api_call
def get_all_items() -> list[dict]:
    r = requests.get(f"{BASE_URL}/item/")
    r.raise_for_status()
    return r.json()


@_api_call
def search_items(
    name=None,
    stock_op=None,
    stock_value=None,
    price_op=None,
    price_value=None,
) -> list[dict]:
    params = {}
    if name:
        params["name"] = name
    if stock_op is not None and stock_value is not None:
        params["stock_op"] = stock_op
        params["stock_value"] = stock_value
    if price_op is not None and price_value is not None:
        params["price_op"] = price_op
        params["price_value"] = price_value
    r = requests.get(f"{BASE_URL}/item/search/", params=params)
    r.raise_for_status()
    return r.json()


@_api_call
def get_item_by_id(item_id: int) -> dict:
    r = requests.get(f"{BASE_URL}/item/{item_id}")
    r.raise_for_status()
    return r.json()


@_api_call
def register(username, first_name, last_name, email, phone, country, city, password):
    r = requests.post(
        f"{BASE_URL}/user/",
        json={
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "country": country,
            "city": city,
            "password": password,
        },
    )
    r.raise_for_status()


@_api_call
def login(username: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": username, "password": password},
    )
    r.raise_for_status()
    return r.json()["jwt_token"]


@_api_call
def get_favorites(user_id: int, token: str) -> list[dict]:
    r = requests.get(
        f"{BASE_URL}/favorite/user/{user_id}",
        headers=_auth_headers(token),
    )
    r.raise_for_status()
    return r.json()


@_api_call
def add_favorite(item_id: int, token: str):
    r = requests.post(
        f"{BASE_URL}/favorite/",
        json={"item_id": item_id},
        headers=_auth_headers(token),
    )
    r.raise_for_status()


@_api_call
def remove_favorite(favorite_id: int, token: str):
    r = requests.delete(
        f"{BASE_URL}/favorite/{favorite_id}",
        headers=_auth_headers(token),
    )
    r.raise_for_status()


@_api_call
def get_orders(user_id: int, token: str) -> list[dict]:
    r = requests.get(
        f"{BASE_URL}/order/user/{user_id}",
        headers=_auth_headers(token),
    )
    r.raise_for_status()
    return r.json()


@_api_call
def add_to_cart(item_id: int, quantity: int, token: str) -> dict:
    r = requests.post(
        f"{BASE_URL}/order/item/",
        json={"item_id": item_id, "quantity": quantity},
        headers=_auth_headers(token),
    )
    r.raise_for_status()
    return r.json()


@_api_call
def update_cart_item(item_id: int, quantity: int, token: str) -> dict:
    r = requests.put(
        f"{BASE_URL}/order/item/",
        json={"item_id": item_id, "quantity": quantity},
        headers=_auth_headers(token),
    )
    r.raise_for_status()
    return r.json()


@_api_call
def remove_cart_item(order_id: int, item_id: int, token: str):
    r = requests.delete(
        f"{BASE_URL}/order/item/{order_id}/{item_id}",
        headers=_auth_headers(token),
    )
    r.raise_for_status()
    if r.status_code == 204:
        return None
    return r.json()


@_api_call
def purchase(order_id: int, token: str) -> dict:
    r = requests.post(
        f"{BASE_URL}/order/{order_id}/purchase",
        headers=_auth_headers(token),
    )
    r.raise_for_status()
    return r.json()


@_api_call
def delete_order(order_id: int, token: str):
    r = requests.delete(
        f"{BASE_URL}/order/{order_id}",
        headers=_auth_headers(token),
    )
    r.raise_for_status()


@_api_call
def chat(user_message: str, history: list[dict], token: str) -> dict:
    r = requests.post(
        f"{BASE_URL}/chat/",
        json={"user_message": user_message, "history": history},
        headers=_auth_headers(token),
    )
    r.raise_for_status()
    return r.json()


@_api_call
def reset_chat(token: str):
    r = requests.post(
        f"{BASE_URL}/chat/reset/",
        headers=_auth_headers(token),
    )
    r.raise_for_status()


@_api_call
def get_recommendations(token: str) -> dict:
    r = requests.get(
        f"{BASE_URL}/recommendation/",
        headers=_auth_headers(token),
    )
    r.raise_for_status()
    return r.json()
