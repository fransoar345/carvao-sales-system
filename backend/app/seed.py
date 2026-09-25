from .auth import hash_password
from . import models
from .permissions import PERMISSION_NAMES, ROLE_PERMISSIONS


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
    for name in ["Administrativo", "Comercial", "Logistica", "Compras", "Financeiro", "Marketing", "Producao"]:
        if not db.query(models.CostCenter).filter(models.CostCenter.name == name).first():
            db.add(models.CostCenter(name=name))
    if not db.query(models.FinancialAccount).first():
        db.add(models.FinancialAccount(name="Caixa principal", account_type="caixa", initial_balance=0))
    db.flush()
    for sale in db.query(models.Sale).filter(models.Sale.status == "confirmada").all():
        if sale.customer_link and not db.query(models.Receivable).filter(models.Receivable.sale_id == sale.id).first():
            due_date = sale.payment_term.due_date if sale.payment_term else sale.occurred_at.date()
            db.add(models.Receivable(sale_id=sale.id, customer_id=sale.customer_link.customer_id, seller_id=sale.seller_id, due_date=due_date, original_amount=sale.total_value, status="aberto"))
    db.flush()
    permission_rows = {}
    for code, name in PERMISSION_NAMES.items():
        row = db.query(models.Permission).filter(models.Permission.code == code).first()
        if not row:
            row = models.Permission(code=code, module=code.split(".", 1)[0], name=name)
            db.add(row)
            db.flush()
        permission_rows[code] = row
    role_rows = {}
    for role_name, codes in ROLE_PERMISSIONS.items():
        role = db.query(models.AccessRole).filter(models.AccessRole.name == role_name).first()
        if not role:
            role = models.AccessRole(name=role_name, description=f"Perfil padrao {role_name}", active=True, system=True)
            db.add(role)
            db.flush()
            role.permissions = [permission_rows[code] for code in codes]
        role_rows[role_name] = role
    legacy_names = {"admin": "Administrador", "gerente": "Gerente", "vendedor": "Vendedor"}
    for user in db.query(models.User).all():
        if not user.access_roles and user.role in legacy_names:
            user.access_roles.append(role_rows[legacy_names[user.role]])
    db.commit()
