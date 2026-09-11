from datetime import date, datetime, time
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    seller_id: int | None = None
    active: bool

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    type: str
    unit: str = "saco"
    cost_price: float = 0
    sale_price: float = 0
    current_stock: float = 0
    minimum_stock: float = 0
    active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    unit: str | None = None
    cost_price: float | None = None
    sale_price: float | None = None
    current_stock: float | None = None
    minimum_stock: float | None = None
    active: bool | None = None


class ProductOut(ProductBase):
    id: int

    class Config:
        from_attributes = True


class MovementCreate(BaseModel):
    product_id: int
    movement_type: str
    quantity: float = Field(gt=0)
    occurred_at: datetime | None = None
    note: str | None = None


class MovementOut(BaseModel):
    id: int
    product_id: int
    movement_type: str
    quantity: float
    occurred_at: datetime
    responsible_id: int | None
    note: str | None
    product_name: str | None = None
    responsible_name: str | None = None

    class Config:
        from_attributes = True


class SellerCreate(BaseModel):
    name: str
    phone: str
    monthly_goal: float | None = None
    commission_percent: float | None = None
    email: str
    temporary_password: str = Field(min_length=6)


class SellerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    monthly_goal: float | None = None
    commission_percent: float | None = None
    active: bool | None = None


class SellerOut(BaseModel):
    id: int
    name: str
    phone: str
    monthly_goal: float | None
    commission_percent: float | None
    active: bool
    email: str | None = None

    class Config:
        from_attributes = True


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)
    unit_price: float | None = None


class SaleCreate(BaseModel):
    seller_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    payment_method: str
    total_value: float | None = None
    items: list[SaleItemCreate]


class SaleUpdate(BaseModel):
    seller_id: int
    customer_name: str | None = None
    customer_phone: str | None = None
    payment_method: str
    total_value: float | None = None
    items: list[SaleItemCreate] = Field(min_length=1)


class SaleItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: float
    unit_price: float
    subtotal: float


class SaleOut(BaseModel):
    id: int
    seller_id: int
    seller_name: str
    customer_name: str | None
    customer_phone: str | None
    occurred_at: datetime
    total_value: float
    payment_method: str
    status: str
    items: list[SaleItemOut]


class DeliveryManifestItemCreate(BaseModel):
    sale_id: int
    delivery_address: str = Field(min_length=3, max_length=300)
    delivery_order: int = Field(default=1, ge=1)


class DeliveryManifestCreate(BaseModel):
    delivery_date: date
    driver_name: str = Field(min_length=2, max_length=120)
    vehicle: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    items: list[DeliveryManifestItemCreate] = Field(min_length=1)


class DeliveryManifestStatusUpdate(BaseModel):
    status: str


class DeliveryItemStatusUpdate(BaseModel):
    status: str
    note: str | None = None


class DeliveryManifestItemOut(BaseModel):
    id: int
    sale_id: int
    delivery_address: str
    delivery_order: int
    status: str
    delivered_at: datetime | None
    note: str | None
    sale: SaleOut


class DeliveryManifestOut(BaseModel):
    id: int
    code: str
    delivery_date: date
    driver_name: str
    vehicle: str | None
    status: str
    notes: str | None
    created_at: datetime
    items: list[DeliveryManifestItemOut]


class WhatsAppSettingsIn(BaseModel):
    provider: str = "mock"
    api_url: str | None = None
    token: str | None = None
    manager_phone: str
    sale_notifications: bool = True
    low_stock_alerts: bool = True
    daily_summary: bool = True
    daily_summary_time: time = time(18, 0)


class WhatsAppSettingsOut(WhatsAppSettingsIn):
    id: int

    class Config:
        from_attributes = True
