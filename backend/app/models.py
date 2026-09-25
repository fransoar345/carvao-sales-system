from datetime import date, datetime, time
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    unit: Mapped[str] = mapped_column(String(30), default="saco")
    cost_price: Mapped[float] = mapped_column(Float, default=0)
    sale_price: Mapped[float] = mapped_column(Float, default=0)
    current_stock: Mapped[float] = mapped_column(Float, default=0)
    minimum_stock: Mapped[float] = mapped_column(Float, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PriceTable(Base, TimestampMixin):
    __tablename__ = "price_tables"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    items = relationship("PriceTableItem", cascade="all, delete-orphan", back_populates="price_table")


class PriceTableItem(Base, TimestampMixin):
    __tablename__ = "price_table_items"
    __table_args__ = (UniqueConstraint("price_table_id", "product_id", name="uq_price_table_product"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    price_table_id: Mapped[int] = mapped_column(ForeignKey("price_tables.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    price: Mapped[float] = mapped_column(Float)
    price_table = relationship("PriceTable", back_populates="items")
    product = relationship("Product")


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cnpj: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    legal_name: Mapped[str] = mapped_column(String(180), index=True)
    state_registration: Mapped[str] = mapped_column(String(40))
    address: Mapped[str] = mapped_column(String(300))
    reference_point: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    price_table_id: Mapped[int | None] = mapped_column(ForeignKey("price_tables.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    price_table = relationship("PriceTable")
    ownership = relationship("CustomerOwnership", cascade="all, delete-orphan", back_populates="customer", uselist=False)


class CustomerOwnership(Base):
    __tablename__ = "customer_ownerships"
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), index=True)
    customer = relationship("Customer", back_populates="ownership")
    seller = relationship("Seller")


class StockMovement(Base, TimestampMixin):
    __tablename__ = "stock_movements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    movement_type: Mapped[str] = mapped_column(String(30))
    quantity: Mapped[float] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    responsible_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    product = relationship("Product")
    responsible = relationship("User")


class EmptyPackage(Base, TimestampMixin):
    __tablename__ = "empty_packages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_type: Mapped[str] = mapped_column(String(120))
    available_quantity: Mapped[float] = mapped_column(Float, default=0)
    in_use_quantity: Mapped[float] = mapped_column(Float, default=0)
    unit_value: Mapped[float] = mapped_column(Float, default=0)


class Seller(Base, TimestampMixin):
    __tablename__ = "sellers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str] = mapped_column(String(30))
    monthly_goal: Mapped[float | None] = mapped_column(Float, nullable=True)
    commission_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    user = relationship("User", back_populates="seller", uselist=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(240))
    role: Mapped[str] = mapped_column(String(30), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    seller_id: Mapped[int | None] = mapped_column(ForeignKey("sellers.id"), nullable=True)
    seller = relationship("Seller", back_populates="user")


class Sale(Base, TimestampMixin):
    __tablename__ = "sales"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"))
    customer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    total_value: Mapped[float] = mapped_column(Float, default=0)
    payment_method: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="confirmada")
    seller = relationship("Seller")
    items = relationship("SaleItem", cascade="all, delete-orphan", back_populates="sale")
    customer_link = relationship("SaleCustomerLink", cascade="all, delete-orphan", back_populates="sale", uselist=False)
    payment_term = relationship("SalePaymentTerm", cascade="all, delete-orphan", back_populates="sale", uselist=False)
    delivery_detail = relationship("SaleDeliveryDetail", cascade="all, delete-orphan", back_populates="sale", uselist=False)


class SaleItem(Base):
    __tablename__ = "sale_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float] = mapped_column(Float)
    subtotal: Mapped[float] = mapped_column(Float)
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")


class SaleCustomerLink(Base):
    __tablename__ = "sale_customer_links"
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    price_table_id: Mapped[int] = mapped_column(ForeignKey("price_tables.id"))
    sale = relationship("Sale", back_populates="customer_link")
    customer = relationship("Customer")
    price_table = relationship("PriceTable")


class SalePaymentTerm(Base):
    __tablename__ = "sale_payment_terms"
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), primary_key=True)
    due_date: Mapped[date] = mapped_column(Date)
    sale = relationship("Sale", back_populates="payment_term")


class SaleDeliveryDetail(Base):
    __tablename__ = "sale_delivery_details"
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), primary_key=True)
    delivery_address: Mapped[str] = mapped_column(String(300))
    sale = relationship("Sale", back_populates="delivery_detail")


class CostCenter(Base, TimestampMixin):
    __tablename__ = "cost_centers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    document: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class FinancialAccount(Base, TimestampMixin):
    __tablename__ = "financial_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    account_type: Mapped[str] = mapped_column(String(30))
    initial_balance: Mapped[float] = mapped_column(Float, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Receivable(Base, TimestampMixin):
    __tablename__ = "receivables"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    original_amount: Mapped[float] = mapped_column(Float)
    interest_amount: Mapped[float] = mapped_column(Float, default=0)
    fine_amount: Mapped[float] = mapped_column(Float, default=0)
    discount_amount: Mapped[float] = mapped_column(Float, default=0)
    paid_amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(30), default="aberto", index=True)
    sale = relationship("Sale")
    customer = relationship("Customer")
    seller = relationship("Seller")
    payments = relationship("ReceivablePayment", cascade="all, delete-orphan", back_populates="receivable")


class ReceivablePayment(Base, TimestampMixin):
    __tablename__ = "receivable_payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receivable_id: Mapped[int] = mapped_column(ForeignKey("receivables.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("financial_accounts.id"))
    amount: Mapped[float] = mapped_column(Float)
    payment_method: Mapped[str] = mapped_column(String(30))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversed: Mapped[bool] = mapped_column(Boolean, default=False)
    responsible_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    receivable = relationship("Receivable", back_populates="payments")
    account = relationship("FinancialAccount")


class Payable(Base, TimestampMixin):
    __tablename__ = "payables"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    cost_center_id: Mapped[int] = mapped_column(ForeignKey("cost_centers.id"))
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(String(200))
    competence_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    original_amount: Mapped[float] = mapped_column(Float)
    paid_amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(30), default="aberto", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier = relationship("Supplier")
    cost_center = relationship("CostCenter")
    payments = relationship("PayablePayment", cascade="all, delete-orphan", back_populates="payable")


class PayablePayment(Base, TimestampMixin):
    __tablename__ = "payable_payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payable_id: Mapped[int] = mapped_column(ForeignKey("payables.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("financial_accounts.id"))
    amount: Mapped[float] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversed: Mapped[bool] = mapped_column(Boolean, default=False)
    responsible_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payable = relationship("Payable", back_populates="payments")
    account = relationship("FinancialAccount")


class CashTransaction(Base, TimestampMixin):
    __tablename__ = "cash_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("financial_accounts.id"), index=True)
    direction: Mapped[str] = mapped_column(String(10), index=True)
    amount: Mapped[float] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(240))
    reversed: Mapped[bool] = mapped_column(Boolean, default=False)
    responsible_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    account = relationship("FinancialAccount")


class DeliveryManifest(Base, TimestampMixin):
    __tablename__ = "delivery_manifests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    delivery_date: Mapped[date] = mapped_column(Date, index=True)
    driver_name: Mapped[str] = mapped_column(String(120))
    vehicle: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="preparacao", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by = relationship("User")
    items = relationship("DeliveryManifestItem", cascade="all, delete-orphan", back_populates="manifest", order_by="DeliveryManifestItem.delivery_order")


class DeliveryManifestItem(Base, TimestampMixin):
    __tablename__ = "delivery_manifest_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("delivery_manifests.id"), index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), index=True)
    delivery_address: Mapped[str] = mapped_column(String(300))
    delivery_order: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="pendente", index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest = relationship("DeliveryManifest", back_populates="items")
    sale = relationship("Sale")


class WhatsAppSettings(Base, TimestampMixin):
    __tablename__ = "whatsapp_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(30), default="mock")
    api_url: Mapped[str | None] = mapped_column(String(260), nullable=True)
    token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    manager_phone: Mapped[str] = mapped_column(String(30), default="+5599999999999")
    sale_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    low_stock_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_summary_time: Mapped[time] = mapped_column(Time, default=time(18, 0))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
