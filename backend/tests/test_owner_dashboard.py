from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.owner_dashboard import build_customer_ranking, build_daily_summary, group_sales_by_day, require_owner


def sale(sale_id, value, occurred_at, customer_id=1, customer_name="Cliente A"):
    customer = SimpleNamespace(id=customer_id, legal_name=customer_name)
    seller = SimpleNamespace(id=1, name="Vendedor", commission_percent=5)
    return SimpleNamespace(
        id=sale_id,
        seller_id=1,
        seller=seller,
        total_value=value,
        occurred_at=occurred_at,
        delivery_status="pendente",
        customer_link=SimpleNamespace(customer=customer),
    )


def test_owner_access_denied_for_non_admin():
    with pytest.raises(HTTPException) as error:
        require_owner(SimpleNamespace(role="vendedor"))
    assert error.value.status_code == 403


def test_daily_total_is_returned_in_cents():
    rows = [
        sale(1, 10.10, datetime(2026, 11, 18, 12, 0)),
        sale(2, 20.25, datetime(2026, 11, 18, 15, 0)),
    ]
    summary = build_daily_summary(rows)
    assert summary["total_cents"] == 3035
    assert summary["orders"] == 2


def test_sales_are_grouped_by_day_and_empty_days_are_kept():
    rows = [
        sale(1, 12.50, datetime(2026, 11, 17, 14, 0)),
        sale(2, 7.50, datetime(2026, 11, 17, 18, 0)),
    ]
    grouped = group_sales_by_day(rows, date(2026, 11, 16), date(2026, 11, 18))
    assert grouped == [
        {"date": "2026-11-16", "total_cents": 0, "orders": 0},
        {"date": "2026-11-17", "total_cents": 2000, "orders": 2},
        {"date": "2026-11-18", "total_cents": 0, "orders": 0},
    ]


def test_customer_ranking_orders_by_total_and_tracks_last_purchase():
    rows = [
        sale(1, 50, datetime(2026, 11, 10, 12, 0), 1, "Cliente A"),
        sale(2, 75, datetime(2026, 11, 18, 12, 0), 1, "Cliente A"),
        sale(3, 200, datetime(2026, 11, 15, 12, 0), 2, "Cliente B"),
    ]
    ranking = build_customer_ranking(rows)
    assert [row["customer_name"] for row in ranking] == ["Cliente B", "Cliente A"]
    assert ranking[1]["purchases"] == 2
    assert ranking[1]["total_cents"] == 12500
    assert ranking[1]["last_purchase"] == datetime(2026, 11, 18, 12, 0)
