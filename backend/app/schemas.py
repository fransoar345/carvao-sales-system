from datetime import date, datetime, time
import re
from pydantic import BaseModel, Field, field_validator, model_validator


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
    profiles: list[str] = []
    permissions: list[str] = []

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


class PriceTableItemIn(BaseModel):
    product_id: int
    price: float = Field(ge=0)


class PriceTableItemOut(PriceTableItemIn):
    product_name: str


class PriceTableCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    is_default: bool = False
    active: bool = True
    items: list[PriceTableItemIn] = Field(min_length=1)


class PriceTableUpdate(PriceTableCreate):
    pass


class PriceTableOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_default: bool
    active: bool
    items: list[PriceTableItemOut]


class CustomerBase(BaseModel):
    cnpj: str
    legal_name: str = Field(min_length=2, max_length=180)
    state_registration: str = Field(min_length=1, max_length=40)
    address: str = Field(min_length=3, max_length=300)
    reference_point: str = Field(min_length=2, max_length=200)
    phone: str | None = None
    email: str | None = None
    price_table_id: int | None = None
    active: bool = True

    @field_validator("cnpj")
    @classmethod
    def normalize_cnpj(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) != 14:
            raise ValueError("CNPJ deve conter 14 digitos")
        return digits

    @model_validator(mode="after")
    def require_contact(self):
        if not (self.phone and self.phone.strip()) and not (self.email and self.email.strip()):
            raise ValueError("Informe telefone ou e-mail")
        return self


class CustomerCreate(CustomerBase):
    owner_seller_id: int | None = None


class CustomerUpdate(CustomerBase):
    owner_seller_id: int


class CustomerOut(CustomerBase):
    id: int
    price_table_name: str | None = None
    owner_seller_id: int | None = None
    owner_seller_name: str | None = None


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
    customer_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    payment_method: str
    payment_due_date: date | None = None
    delivery_address: str = Field(min_length=3, max_length=300)
    total_value: float | None = None
    items: list[SaleItemCreate]

    @model_validator(mode="after")
    def require_due_date_for_credit(self):
        if self.payment_method == "prazo" and not self.payment_due_date:
            raise ValueError("Informe a data de vencimento para venda a prazo")
        return self


class SaleUpdate(BaseModel):
    seller_id: int
    customer_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    payment_method: str
    payment_due_date: date | None = None
    delivery_address: str = Field(min_length=3, max_length=300)
    total_value: float | None = None
    items: list[SaleItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def require_due_date_for_credit(self):
        if self.payment_method == "prazo" and not self.payment_due_date:
            raise ValueError("Informe a data de vencimento para venda a prazo")
        return self


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
    customer_id: int | None = None
    customer_cnpj: str | None = None
    price_table_name: str | None = None
    occurred_at: datetime
    total_value: float
    payment_method: str
    payment_due_date: date | None = None
    delivery_address: str | None = None
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


class NamedEntityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)


class CostCenterOut(BaseModel):
    id: int
    name: str
    active: bool
    class Config: from_attributes = True


class SupplierCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    document: str | None = None
    phone: str | None = None
    email: str | None = None


class SupplierOut(SupplierCreate):
    id: int
    active: bool
    class Config: from_attributes = True


class FinancialAccountCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    account_type: str
    initial_balance: float = 0


class FinancialAccountOut(FinancialAccountCreate):
    id: int
    active: bool
    balance: float = 0


class FinancialPaymentCreate(BaseModel):
    account_id: int
    amount: float = Field(gt=0)
    payment_method: str = "pix"
    occurred_at: datetime | None = None
    note: str | None = None


class AccessRoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = None
    permission_codes: list[str] = []


class PermissionCreate(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
    module: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=140)
    description: str | None = None


class AccessRoleUpdate(AccessRoleCreate):
    active: bool = True


class UserAccessUpdate(BaseModel):
    role_ids: list[int] = []
    overrides: dict[str, bool] = {}


class AccessUserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=6)
    role_ids: list[int] = Field(min_length=1)


class PayableCreate(BaseModel):
    supplier_id: int | None = None
    cost_center_id: int
    category: str
    description: str
    competence_date: date
    due_date: date
    original_amount: float = Field(gt=0)
    notes: str | None = None
