import httpx
from datetime import datetime, time
from sqlalchemy.orm import Session

from . import models
from .config import get_settings


def split_telegram_message(message: str, limit: int = 4000) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in message.splitlines() or [message]:
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [""]


def get_whatsapp_settings(db: Session) -> models.WhatsAppSettings:
    settings = db.query(models.WhatsAppSettings).first()
    if settings:
        return settings
    env = get_settings()
    settings = models.WhatsAppSettings(
        provider=env.whatsapp_provider,
        api_url=env.whatsapp_api_url,
        token=env.whatsapp_token,
        manager_phone=env.manager_whatsapp,
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


async def send_whatsapp(db: Session, to: str, message: str) -> dict:
    settings = get_whatsapp_settings(db)
    if settings.provider == "mock":
        print(f"[WHATSAPP MOCK] to={to} message={message}")
        return {"ok": True, "provider": "mock"}

    if settings.provider == "telegram":
        if not settings.token or not to:
            raise ValueError("Configure o token do bot e o Chat ID do Telegram")
        api_url = f"https://api.telegram.org/bot{settings.token}/sendMessage"
        headers = {}
        payload = {"chat_id": to, "text": message}
    elif settings.provider == "meta":
        if not settings.api_url or not settings.token:
            raise ValueError("Configure a URL e o token da Meta Cloud API")
        api_url = settings.api_url
        headers = {"Authorization": f"Bearer {settings.token}"}
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "".join(character for character in to if character.isdigit()),
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
    else:
        if not settings.api_url:
            raise ValueError("Configure a URL da API de mensagens")
        api_url = settings.api_url
        headers = {"Authorization": f"Bearer {settings.token}"} if settings.token else {}
        payload = {"to": to, "message": message}
    async with httpx.AsyncClient(timeout=15) as client:
        if settings.provider == "telegram":
            responses = []
            for chunk in split_telegram_message(message):
                response = await client.post(api_url, json={"chat_id": to, "text": chunk}, headers=headers)
                response.raise_for_status()
                responses.append(response.status_code)
            return {"ok": True, "provider": settings.provider, "status_code": responses[-1], "messages": len(responses)}
        response = await client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return {"ok": True, "provider": settings.provider, "status_code": response.status_code}


async def send_notification_safely(db: Session, to: str, message: str) -> None:
    try:
        await send_whatsapp(db, to, message)
    except Exception as exc:
        print(f"[NOTIFICATION ERROR] provider={get_whatsapp_settings(db).provider} error={exc}")


async def notify_sale(db: Session, sale: models.Sale) -> None:
    settings = get_whatsapp_settings(db)
    if not settings.sale_notifications:
        return
    item_text = ", ".join(f"{i.quantity:g}x {i.product.name}" for i in sale.items)
    customer = sale.customer_link.customer if sale.customer_link else None
    payment_names = {"dinheiro": "Dinheiro", "pix": "Pix", "cartao": "Cartao", "prazo": "A prazo"}
    payment_text = payment_names.get(sale.payment_method, sale.payment_method)
    due_text = f". Vencimento: {sale.payment_term.due_date:%d/%m/%Y}" if sale.payment_term else ""
    company_text = customer.legal_name if customer else (sale.customer_name or "Nao informado")
    address_text = customer.address if customer else "Nao informado"
    manager_message = (
        f"Venda confirmada: {sale.seller.name} vendeu {item_text}. "
        f"Total R$ {sale.total_value:.2f}. Meio de pagamento: {payment_text}{due_text}. "
        f"Empresa: {company_text}. Endereco: {address_text}."
    )
    seller_message = f"Venda registrada com sucesso. Total R$ {sale.total_value:.2f}."
    await send_notification_safely(db, settings.manager_phone, manager_message)
    if settings.provider != "telegram":
        await send_notification_safely(db, sale.seller.phone, seller_message)


async def notify_low_stock(db: Session, product: models.Product) -> None:
    settings = get_whatsapp_settings(db)
    if settings.low_stock_alerts and product.current_stock <= product.minimum_stock:
        await send_notification_safely(
            db,
            settings.manager_phone,
            f"Alerta de estoque baixo: {product.name} com {product.current_stock:g} {product.unit}.",
        )


MANIFEST_STATUS_NAMES = {
    "preparacao": "Em preparacao",
    "em_rota": "Em rota",
    "concluido": "Concluido",
    "cancelado": "Cancelado",
    "pendente": "Pendente",
    "entregue": "Entregue",
    "nao_entregue": "Nao entregue",
}


def manifest_item_text(item: models.DeliveryManifestItem) -> str:
    sale = item.sale
    company = sale.customer_link.customer.legal_name if sale.customer_link else (sale.customer_name or f"Venda #{sale.id}")
    products = ", ".join(f"{row.quantity:g}x {row.product.name}" for row in sale.items)
    return f"{item.delivery_order}. {company}: {products}. Endereco: {item.delivery_address}"


async def notify_manifest_created(db: Session, manifest: models.DeliveryManifest) -> None:
    settings = get_whatsapp_settings(db)
    if settings.provider != "telegram":
        return
    deliveries = "\n".join(manifest_item_text(item) for item in manifest.items)
    message = (
        f"Romaneio gerado: {manifest.code}\n"
        f"Data de entrega: {manifest.delivery_date:%d/%m/%Y}\n"
        f"Motorista: {manifest.driver_name}\n"
        f"Veiculo: {manifest.vehicle or 'Nao informado'}\n"
        f"Entregas: {len(manifest.items)}\n{deliveries}"
    )
    await send_notification_safely(db, settings.manager_phone, message)


async def notify_manifest_status(db: Session, manifest: models.DeliveryManifest, previous_status: str, actor_name: str) -> None:
    settings = get_whatsapp_settings(db)
    if settings.provider != "telegram":
        return
    message = (
        f"Status do romaneio alterado: {manifest.code}\n"
        f"{MANIFEST_STATUS_NAMES.get(previous_status, previous_status)} -> {MANIFEST_STATUS_NAMES.get(manifest.status, manifest.status)}\n"
        f"Motorista: {manifest.driver_name}\n"
        f"Alterado por: {actor_name}"
    )
    await send_notification_safely(db, settings.manager_phone, message)


async def notify_delivery_status(db: Session, manifest: models.DeliveryManifest, item: models.DeliveryManifestItem, previous_status: str, actor_name: str) -> None:
    settings = get_whatsapp_settings(db)
    if settings.provider != "telegram":
        return
    message = (
        f"Status da entrega alterado: {manifest.code}\n"
        f"Entrega {item.delivery_order}: {MANIFEST_STATUS_NAMES.get(previous_status, previous_status)} -> {MANIFEST_STATUS_NAMES.get(item.status, item.status)}\n"
        f"{manifest_item_text(item)}\n"
        f"Status do romaneio: {MANIFEST_STATUS_NAMES.get(manifest.status, manifest.status)}\n"
        f"Alterado por: {actor_name}"
    )
    if item.note:
        message += f"\nObservacao: {item.note}"
    await send_notification_safely(db, settings.manager_phone, message)


async def send_daily_summary(db: Session, day: datetime | None = None) -> None:
    settings = get_whatsapp_settings(db)
    if not settings.daily_summary:
        return
    day = day or datetime.utcnow()
    start = datetime.combine(day.date(), time.min)
    end = datetime.combine(day.date(), time.max)
    sales = db.query(models.Sale).filter(models.Sale.occurred_at >= start, models.Sale.occurred_at <= end, models.Sale.status == "confirmada").all()
    total = sum(s.total_value for s in sales)
    by_seller: dict[str, float] = {}
    for sale in sales:
        by_seller[sale.seller.name] = by_seller.get(sale.seller.name, 0) + sale.total_value
    sellers = "; ".join(f"{name}: R$ {value:.2f}" for name, value in by_seller.items()) or "sem vendas"
    low_stock = db.query(models.Product).filter(models.Product.current_stock <= models.Product.minimum_stock).all()
    stock_text = ", ".join(f"{p.name} {p.current_stock:g}" for p in low_stock) or "sem alertas"
    await send_notification_safely(db, settings.manager_phone, f"Resumo diario: {len(sales)} vendas, total R$ {total:.2f}. Por vendedor: {sellers}. Estoque baixo: {stock_text}.")
