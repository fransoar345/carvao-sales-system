from .auth import hash_password
from . import models


def seed_data(db):
    if not db.query(models.User).first():
        seller_ana = models.Seller(name="Ana Rocha", phone="+5563999990001", monthly_goal=25000, commission_percent=4)
        seller_lucas = models.Seller(name="Lucas Lima", phone="+5563999990002", monthly_goal=18000, commission_percent=3.5)
        db.add_all([seller_ana, seller_lucas])
        db.flush()

        users = [
            models.User(name="Admin Carvao", email="admin@carvao.local", password_hash=hash_password("admin123"), role="admin"),
            models.User(name="Gerente Operacao", email="gerente@carvao.local", password_hash=hash_password("gerente123"), role="gerente"),
            models.User(name="Ana Rocha", email="ana@carvao.local", password_hash=hash_password("vendedor123"), role="vendedor", seller_id=seller_ana.id),
            models.User(name="Lucas Lima", email="lucas@carvao.local", password_hash=hash_password("vendedor123"), role="vendedor", seller_id=seller_lucas.id),
        ]
        products = [
            models.Product(name="Carvao Premium 5kg", type="saco_fechado", unit="saco", cost_price=12, sale_price=22, current_stock=180, minimum_stock=40),
            models.Product(name="Carvao Premium 3kg", type="saco_fechado", unit="saco", cost_price=8, sale_price=15, current_stock=120, minimum_stock=30),
            models.Product(name="Embalagem vazia 5kg", type="embalagem_vazia", unit="unidade", cost_price=0.65, sale_price=0, current_stock=500, minimum_stock=120),
            models.Product(name="Acendedor Ecologico", type="outro", unit="unidade", cost_price=1.9, sale_price=4.5, current_stock=90, minimum_stock=20),
        ]
        db.add_all(users + products)
        db.add(models.WhatsAppSettings(provider="mock", manager_phone="+5563999999999"))
        db.flush()

    default_table = db.query(models.PriceTable).filter(models.PriceTable.is_default.is_(True)).first()
    if not default_table:
        default_table = models.PriceTable(name="Tabela padrao", description="Precos padrao dos produtos", is_default=True)
        db.add(default_table)
        db.flush()
    existing = {item.product_id for item in default_table.items}
    for product in db.query(models.Product).all():
        if product.id not in existing:
            default_table.items.append(models.PriceTableItem(product_id=product.id, price=product.sale_price))
    fallback_seller = db.query(models.Seller).filter(models.Seller.active.is_(True)).first()
    for customer in db.query(models.Customer).all():
        if not customer.ownership and fallback_seller:
            historical_sale = (
                db.query(models.Sale)
                .join(models.SaleCustomerLink)
                .filter(models.SaleCustomerLink.customer_id == customer.id)
                .order_by(models.Sale.occurred_at)
                .first()
            )
            customer.ownership = models.CustomerOwnership(seller_id=historical_sale.seller_id if historical_sale else fallback_seller.id)
    db.commit()
