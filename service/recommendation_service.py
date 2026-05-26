"""
Loads the trained recommender bundle and builds feature vectors from the
user's live DB activity (orders, favorites, cart, country, stats).
"""

import os
from datetime import datetime
from typing import List

import joblib
import numpy as np

from config.config import Config
from exceptions.exception import recommendation_model_unavailable_exception
from model.order_status import OrderStatus
from model.recommendation_response import RecommendationItem, RecommendationResponse
from model.user_response import UserResponse
from repository import (
    cache_repository,
    favorite_repository,
    item_repository,
    order_item_repository,
)

_config = Config()
_bundle = None


def _cache_key(user_id: int) -> str:
    return f"recommendations:user:{user_id}"


def invalidate_user_recommendations(user_id: int):
    cache_repository.remove_cache_entity(_cache_key(user_id))


def _load_bundle() -> dict:
    global _bundle
    if _bundle is None:
        if not os.path.exists(_config.ML_MODEL_PATH):
            raise recommendation_model_unavailable_exception()
        try:
            _bundle = joblib.load(_config.ML_MODEL_PATH)
        except Exception:
            # joblib failures come in many shapes (UnpicklingError, EOFError,
            # ImportError, ...); broad except converts all of them to 503.
            raise recommendation_model_unavailable_exception()
    return _bundle


async def _build_feature_vector(user: UserResponse) -> np.ndarray:
    bundle = _load_bundle()
    countries = bundle["countries"]
    num_items = bundle["num_items"]
    item_id_to_index = bundle["item_id_to_index"]

    country_vec = np.zeros(len(countries))
    if user.country in countries:
        country_vec[countries.index(user.country)] = 1

    # Single JOIN fetches every (order, line) pair for the user; we group
    # in Python rather than issuing one SELECT per order.
    lines = await order_item_repository.get_all_lines_for_user(user.id)
    orders: dict = {}
    for line in lines:
        oid = line["order_id"]
        if oid not in orders:
            orders[oid] = {
                "status": OrderStatus(line["status"]),
                "created_at": line["created_at"],
                "total_price": float(line["total_price"]),
                "item_ids": [],
            }
        orders[oid]["item_ids"].append(line["item_id"])

    closed_orders = [o for o in orders.values() if o["status"] == OrderStatus.CLOSE]
    temp_orders = [o for o in orders.values() if o["status"] == OrderStatus.TEMP]

    order_count = len(closed_orders)
    total_spent = float(sum(o["total_price"] for o in closed_orders))
    if closed_orders:
        most_recent = max(o["created_at"] for o in closed_orders if o["created_at"])
        days_since = max((datetime.utcnow() - most_recent).days, 0)
    else:
        days_since = 365

    purchase_hist = np.zeros(num_items)
    cart_vec = np.zeros(num_items)
    basket_sizes: List[int] = []

    for o in closed_orders:
        basket_sizes.append(len(o["item_ids"]))
        for item_id in o["item_ids"]:
            idx = item_id_to_index.get(item_id)
            if idx is not None:
                purchase_hist[idx] += 1

    for o in temp_orders:
        for item_id in o["item_ids"]:
            idx = item_id_to_index.get(item_id)
            if idx is not None:
                cart_vec[idx] = 1

    avg_basket_size = float(np.mean(basket_sizes)) if basket_sizes else 0.0

    fav_vec = np.zeros(num_items)
    favs = await favorite_repository.get_favorites_by_user(user.id)
    for fav in favs:
        idx = item_id_to_index.get(fav["item_id"])
        if idx is not None:
            fav_vec[idx] = 1

    feature = np.concatenate([
        country_vec,
        [order_count, avg_basket_size, total_spent, days_since],
        purchase_hist,
        fav_vec,
        cart_vec,
    ]).astype(np.float32)

    return feature


async def get_recommendations(user: UserResponse) -> RecommendationResponse:
    cache_key = _cache_key(user.id)
    cached = cache_repository.get_cache_entity(cache_key)
    if cached:
        return RecommendationResponse.parse_raw(cached)

    bundle = _load_bundle()
    pipeline = bundle["pipeline"]
    bundle_items = bundle["items"]
    classifier = pipeline.named_steps["classifier"]

    feature = await _build_feature_vector(user)
    probs = pipeline.predict_proba(feature.reshape(1, -1))[0]

    # classes_ maps probability columns back to bundle indices — defensive
    # when not all items appeared as labels in training.
    classes_ = classifier.classes_
    sorted_col_indices = np.argsort(probs)[::-1]

    # Batch fetch (Redis-cached) instead of one SELECT per ranked item.
    all_db_items = await item_repository.get_all_items()
    db_by_id = {item.id: item for item in all_db_items}

    recommendations: List[RecommendationItem] = []
    for col_i in sorted_col_indices:
        idx = int(classes_[col_i])
        bundle_item = bundle_items[idx]
        db_item = db_by_id.get(bundle_item["id"])
        if db_item is None:
            # Item from training catalog no longer in DB — skip silently.
            continue
        recommendations.append(
            RecommendationItem(
                item_id=db_item.id,
                item_name=db_item.item_name,
                category=bundle_item["category"],
                price=float(db_item.price),
                probability=float(probs[col_i]),
            )
        )

    response = RecommendationResponse(
        user_id=user.id,
        recommendations=recommendations,
        model_version=str(bundle.get("version", "unknown")),
        trained_at=str(bundle.get("trained_at", "unknown")),
    )
    cache_repository.create_cache_entity(cache_key, response.json())
    return response
