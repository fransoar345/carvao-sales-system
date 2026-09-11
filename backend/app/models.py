from datetime import datetime, time
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Time
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
