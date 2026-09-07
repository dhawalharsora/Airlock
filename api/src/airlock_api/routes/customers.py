"""Customer surface (read-only): the picker + a customer's own orders.

Ungated on purpose — this is the customer's view of their own data. Ownership is
ENFORCED on the action path (agent service), not here.
"""
from fastapi import APIRouter

from airlock_api.db import fetch_all

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
def list_customers() -> list[dict]:
    return fetch_all("SELECT customer_id, name FROM customers ORDER BY customer_id")


@router.get("/{customer_id}/orders")
def customer_orders(customer_id: str) -> list[dict]:
    return fetch_all(
        """SELECT order_id, item, amount_cents, currency, status, ordered_at
           FROM orders WHERE customer_id = %s ORDER BY order_id""",
        (customer_id,),
    )
