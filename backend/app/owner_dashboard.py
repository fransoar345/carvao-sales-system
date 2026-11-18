from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException

from .auth import get_current_user
from . import models


SAO_PAULO = ZoneInfo("America/Sao_Paulo")
DELIVERY_STATUSES = {"pendente", "em_rota", "entregue", "nao_entregue"}


def require_owner(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo do administrador")
    return user


def money_to_cents(value: float | Decimal | None) -> int:
    return int((Decimal(str(value or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def local_now() -> datetime:
    return datetime.now(SAO_PAULO)


def period_dates(period: str, now: datetime | None = None) -> tuple[date, date]:
    today = (now or local_now()).astimezone(SAO_PAULO).date()
    if period == "today":
        return today, today
    if period == "7d":
        return today - timedelta(days=6), today
    if period == "30d":
        return today - timedelta(days=29), today
    if period == "month":
        return today.replace(day=1), today
    raise HTTPException(status_code=400, detail="Periodo invalido")


def utc_query_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(start, time.min, tzinfo=SAO_PAULO)
    end_local = datetime.combine(end + timedelta(days=1), time.min, tzinfo=SAO_PAULO)
    return start_local.astimezone(timezone.utc).replace(tzinfo=None), end_local.astimezone(timezone.utc).replace(tzinfo=None)


def local_sale_date(occurred_at: datetime) -> date:
    source = occurred_at.replace(tzinfo=timezone.utc) if occurred_at.tzinfo is None else occurred_at
    return source.astimezone(SAO_PAULO).date()


def build_daily_summary(sales: list, status_filter: str | None = None) -> dict:
    counts = {status: 0 for status in DELIVERY_STATUSES}
    for sale in sales:
        counts[getattr(sale, "delivery_status", "pendente")] = counts.get(getattr(sale, "delivery_status", "pendente"), 0) + 1
    visible = sales if not status_filter or status_filter == "todos" else [sale for sale in sales if sale.delivery_status == status_filter]
    return {
        "total_cents": sum(money_to_cents(sale.total_value) for sale in sales),
        "orders": len(sales),
        "delivery_counts": counts,
        "sales": visible,
    }


def group_sales_by_day(sales: list, start: date, end: date) -> list[dict]:
    totals: dict[date, int] = {}
    counts: dict[date, int] = {}
    for sale in sales:
        day = local_sale_date(sale.occurred_at)
        totals[day] = totals.get(day, 0) + money_to_cents(sale.total_value)
        counts[day] = counts.get(day, 0) + 1
    rows = []
    cursor = start
    while cursor <= end:
        rows.append({"date": cursor.isoformat(), "total_cents": totals.get(cursor, 0), "orders": counts.get(cursor, 0)})
        cursor += timedelta(days=1)
    return rows


def build_seller_performance(sales: list, commissions_by_sale: dict[int, float]) -> list[dict]:
    rows: dict[int, dict] = {}
    for sale in sales:
        row = rows.setdefault(sale.seller_id, {"seller_id": sale.seller_id, "seller_name": sale.seller.name, "sales": 0, "revenue_cents": 0, "commission_cents": 0})
        row["sales"] += 1
        row["revenue_cents"] += money_to_cents(sale.total_value)
        row["commission_cents"] += money_to_cents(commissions_by_sale.get(sale.id, sale.total_value * ((sale.seller.commission_percent or 0) / 100)))
    for row in rows.values():
        row["average_ticket_cents"] = round(row["revenue_cents"] / row["sales"]) if row["sales"] else 0
    return sorted(rows.values(), key=lambda row: row["revenue_cents"], reverse=True)


def build_customer_ranking(sales: list, limit: int = 10) -> list[dict]:
    rows: dict[int, dict] = {}
    for sale in sales:
        link = getattr(sale, "customer_link", None)
        if not link:
            continue
        customer = link.customer
        row = rows.setdefault(customer.id, {"customer_id": customer.id, "customer_name": customer.legal_name, "purchases": 0, "total_cents": 0, "last_purchase": sale.occurred_at})
        row["purchases"] += 1
        row["total_cents"] += money_to_cents(sale.total_value)
        if sale.occurred_at > row["last_purchase"]:
            row["last_purchase"] = sale.occurred_at
    ranking = sorted(rows.values(), key=lambda row: (row["total_cents"], row["purchases"]), reverse=True)
    return ranking[:limit]
