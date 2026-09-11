import asyncio
from datetime import date, datetime, time, timedelta
from io import BytesIO

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .auth import create_access_token, get_current_user, hash_password, require_roles, verify_password
from .config import get_settings
from .database import Base, engine, get_db
from .seed import seed_data
from .whatsapp import get_whatsapp_settings, notify_low_stock, notify_sale, send_daily_summary, send_whatsapp


settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

daily_summary_sent: set[date] = set()


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        seed_data(db)
    finally:
        db.close()
    asyncio.create_task(daily_summary_worker())


async def daily_summary_worker():
    while True:
        await asyncio.sleep(60)
        db = next(get_db())
        try:
            settings_row = get_whatsapp_settings(db)
            now = datetime.now()
            should_send = settings_row.daily_summary and now.time() >= settings_row.daily_summary_time and now.date() not in daily_summary_sent
            if should_send:
                await send_daily_summary(db, now)
                daily_summary_sent.add(now.date())
        except Exception as exc:
            print(f"[DAILY SUMMARY ERROR] {exc}")
        finally:
            db.close()


def audit(db: Session, user: models.User | None, action: str, entity: str, entity_id: int | None, details: str = ""):
    db.add(models.AuditLog(actor_id=user.id if user else None, action=action, entity=entity, entity_id=entity_id, details=details))


def movement_delta(kind: str, quantity: float) -> float:
    mapping = {"entrada": quantity, "saida": -quantity, "ajuste": quantity, "devolucao": quantity}
    if kind not in mapping:
        raise HTTPException(400, "Tipo de movimento invalido")
    return mapping[kind]


def sale_to_schema(sale: models.Sale) -> schemas.SaleOut:
    return schemas.SaleOut(
        id=sale.id,
        seller_id=sale.seller_id,
        seller_name=sale.seller.name,
        customer_name=sale.customer_name,
        customer_phone=sale.customer_phone,
        occurred_at=sale.occurred_at,
        total_value=sale.total_value,
        payment_method=sale.payment_method,
        status=sale.status,
        items=[
            schemas.SaleItemOut(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in sale.items
        ],
    )


@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.app_name}


@app.post("/api/auth/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Login ou senha invalidos")
    token = create_access_token(user)
    return {"access_token": token, "user": schemas.UserOut.model_validate(user).model_dump()}


@app.get("/api/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@app.get("/api/products", response_model=list[schemas.ProductOut])
def list_products(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Product).order_by(models.Product.name).all()


@app.post("/api/products", response_model=schemas.ProductOut)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    product = models.Product(**payload.model_dump())
    db.add(product)
    db.flush()
    audit(db, user, "create", "product", product.id, product.name)
    db.commit()
    db.refresh(product)
    return product


@app.put("/api/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(404, "Produto nao encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    audit(db, user, "update", "product", product.id, product.name)
    db.commit()
    db.refresh(product)
    return product


@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(404, "Produto nao encontrado")
    product.active = False
    audit(db, user, "deactivate", "product", product.id, product.name)
    db.commit()
    return {"ok": True}


@app.get("/api/stock/movements", response_model=list[schemas.MovementOut])
def list_movements(product_id: int | None = None, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    query = db.query(models.StockMovement).options(joinedload(models.StockMovement.product), joinedload(models.StockMovement.responsible))
    if product_id:
        query = query.filter(models.StockMovement.product_id == product_id)
    movements = query.order_by(models.StockMovement.occurred_at.desc()).limit(300).all()
    return [
        schemas.MovementOut(
            id=m.id,
            product_id=m.product_id,
            movement_type=m.movement_type,
            quantity=m.quantity,
            occurred_at=m.occurred_at,
            responsible_id=m.responsible_id,
            note=m.note,
            product_name=m.product.name if m.product else None,
            responsible_name=m.responsible.name if m.responsible else None,
        )
        for m in movements
    ]


@app.post("/api/stock/movements", response_model=schemas.MovementOut)
async def create_movement(payload: schemas.MovementCreate, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    product = db.get(models.Product, payload.product_id)
    if not product:
        raise HTTPException(404, "Produto nao encontrado")
    product.current_stock += movement_delta(payload.movement_type, payload.quantity)
    if product.current_stock < 0:
        raise HTTPException(400, "Estoque insuficiente")
    movement = models.StockMovement(
        product_id=payload.product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        occurred_at=payload.occurred_at or datetime.utcnow(),
        responsible_id=user.id,
        note=payload.note,
    )
    db.add(movement)
    db.flush()
    audit(db, user, "create", "stock_movement", movement.id, f"{product.name}: {payload.movement_type} {payload.quantity:g}")
    db.commit()
    db.refresh(movement)
    await notify_low_stock(db, product)
    return schemas.MovementOut(
        id=movement.id,
        product_id=movement.product_id,
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        occurred_at=movement.occurred_at,
        responsible_id=movement.responsible_id,
        note=movement.note,
        product_name=product.name,
        responsible_name=user.name,
    )


@app.get("/api/sellers", response_model=list[schemas.SellerOut])
def list_sellers(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    sellers = db.query(models.Seller).options(joinedload(models.Seller.user)).order_by(models.Seller.name).all()
    return [
        schemas.SellerOut(
            id=s.id,
            name=s.name,
            phone=s.phone,
            monthly_goal=s.monthly_goal,
            commission_percent=s.commission_percent,
            active=s.active,
            email=s.user.email if s.user else None,
        )
        for s in sellers
    ]


@app.post("/api/sellers", response_model=schemas.SellerOut)
def create_seller(payload: schemas.SellerCreate, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin"))):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(400, "E-mail ja cadastrado")
    seller = models.Seller(
        name=payload.name,
        phone=payload.phone,
        monthly_goal=payload.monthly_goal,
        commission_percent=payload.commission_percent,
    )
    db.add(seller)
    db.flush()
    app_user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.temporary_password),
        role="vendedor",
        seller_id=seller.id,
    )
    db.add(app_user)
    audit(db, user, "create", "seller", seller.id, seller.name)
    db.commit()
    return schemas.SellerOut(id=seller.id, name=seller.name, phone=seller.phone, monthly_goal=seller.monthly_goal, commission_percent=seller.commission_percent, active=seller.active, email=payload.email)


@app.put("/api/sellers/{seller_id}", response_model=schemas.SellerOut)
def update_seller(seller_id: int, payload: schemas.SellerUpdate, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin"))):
    seller = db.get(models.Seller, seller_id)
    if not seller:
        raise HTTPException(404, "Vendedor nao encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(seller, key, value)
    if seller.user:
        seller.user.name = seller.name
        seller.user.active = seller.active
    audit(db, user, "update", "seller", seller.id, seller.name)
    db.commit()
    return schemas.SellerOut(id=seller.id, name=seller.name, phone=seller.phone, monthly_goal=seller.monthly_goal, commission_percent=seller.commission_percent, active=seller.active, email=seller.user.email if seller.user else None)


@app.get("/api/sales", response_model=list[schemas.SaleOut])
def list_sales(
    start: date | None = None,
    end: date | None = None,
    seller_id: int | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = db.query(models.Sale).options(joinedload(models.Sale.seller), joinedload(models.Sale.items).joinedload(models.SaleItem.product))
    if user.role == "vendedor":
        query = query.filter(models.Sale.seller_id == user.seller_id)
    elif seller_id:
        query = query.filter(models.Sale.seller_id == seller_id)
    if start:
        query = query.filter(models.Sale.occurred_at >= datetime.combine(start, time.min))
    if end:
        query = query.filter(models.Sale.occurred_at <= datetime.combine(end, time.max))
    return [sale_to_schema(s) for s in query.order_by(models.Sale.occurred_at.desc()).limit(300).all()]


@app.post("/api/sales", response_model=schemas.SaleOut)
async def create_sale(payload: schemas.SaleCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    seller_id = user.seller_id if user.role == "vendedor" else payload.seller_id
    if not seller_id:
        raise HTTPException(400, "Selecione um vendedor")
    seller = db.get(models.Seller, seller_id)
    if not seller or not seller.active:
        raise HTTPException(404, "Vendedor nao encontrado")
    if not payload.items:
        raise HTTPException(400, "Inclua ao menos um item")

    sale = models.Sale(seller_id=seller_id, customer_name=payload.customer_name, customer_phone=payload.customer_phone, payment_method=payload.payment_method, status="confirmada")
    total = 0.0
    touched_products: list[models.Product] = []
    for item in payload.items:
        product = db.get(models.Product, item.product_id)
        if not product or not product.active:
            raise HTTPException(404, "Produto indisponivel")
        if product.current_stock < item.quantity:
            raise HTTPException(400, f"Estoque insuficiente para {product.name}")
        unit_price = item.unit_price if item.unit_price is not None else product.sale_price
        subtotal = item.quantity * unit_price
        product.current_stock -= item.quantity
        total += subtotal
        touched_products.append(product)
        sale.items.append(models.SaleItem(product_id=product.id, quantity=item.quantity, unit_price=unit_price, subtotal=subtotal))
        db.add(models.StockMovement(product_id=product.id, movement_type="saida", quantity=item.quantity, responsible_id=user.id, note="Baixa automatica por venda"))
    sale.total_value = payload.total_value if payload.total_value is not None else total
    db.add(sale)
    db.flush()
    audit(db, user, "create", "sale", sale.id, f"Venda R$ {sale.total_value:.2f}")
    db.commit()
    sale = db.query(models.Sale).options(joinedload(models.Sale.seller), joinedload(models.Sale.items).joinedload(models.SaleItem.product)).get(sale.id)
    await notify_sale(db, sale)
    for product in touched_products:
        await notify_low_stock(db, product)
    return sale_to_schema(sale)


@app.get("/api/dashboard")
def dashboard(
    start: date | None = Query(None),
    end: date | None = Query(None),
    seller_id: int | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    today = date.today()
    start_dt = datetime.combine(start or today, time.min)
    end_dt = datetime.combine(end or today, time.max)
    query = db.query(models.Sale).filter(models.Sale.status == "confirmada", models.Sale.occurred_at >= start_dt, models.Sale.occurred_at <= end_dt)
    if user.role == "vendedor":
        query = query.filter(models.Sale.seller_id == user.seller_id)
    elif seller_id:
        query = query.filter(models.Sale.seller_id == seller_id)

    sales = query.all()
    total_value = sum(s.total_value for s in sales)
    sale_ids = [s.id for s in sales] or [0]
    item_qty = db.query(func.coalesce(func.sum(models.SaleItem.quantity), 0)).filter(models.SaleItem.sale_id.in_(sale_ids)).scalar()
    sellers = db.query(models.Seller).all()
    ranking = []
    for seller in sellers:
        seller_sales = [s for s in sales if s.seller_id == seller.id]
        qty = db.query(func.coalesce(func.sum(models.SaleItem.quantity), 0)).join(models.Sale).filter(models.Sale.seller_id == seller.id, models.Sale.id.in_(sale_ids)).scalar()
        value = sum(s.total_value for s in seller_sales)
        ranking.append({"seller_id": seller.id, "seller_name": seller.name, "quantity": float(qty or 0), "value": value, "commission": value * ((seller.commission_percent or 0) / 100)})
    ranking.sort(key=lambda row: row["value"], reverse=True)
    products = db.query(models.Product).order_by(models.Product.type, models.Product.name).all()
    return {
        "period": {"start": start_dt.date(), "end": end_dt.date()},
        "sales_count": len(sales),
        "total_value": total_value,
        "items_quantity": float(item_qty or 0),
        "stock": [{"id": p.id, "name": p.name, "type": p.type, "unit": p.unit, "current_stock": p.current_stock, "minimum_stock": p.minimum_stock, "low": p.current_stock <= p.minimum_stock} for p in products],
        "ranking": ranking,
    }


@app.get("/api/whatsapp/settings", response_model=schemas.WhatsAppSettingsOut)
def read_whatsapp(db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin"))):
    return get_whatsapp_settings(db)


@app.put("/api/whatsapp/settings", response_model=schemas.WhatsAppSettingsOut)
def update_whatsapp(payload: schemas.WhatsAppSettingsIn, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin"))):
    settings_row = get_whatsapp_settings(db)
    for key, value in payload.model_dump().items():
        setattr(settings_row, key, value)
    audit(db, user, "update", "whatsapp_settings", settings_row.id, "Configuracao atualizada")
    db.commit()
    db.refresh(settings_row)
    return settings_row


@app.post("/api/whatsapp/test")
async def test_whatsapp(db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin"))):
    settings_row = get_whatsapp_settings(db)
    return await send_whatsapp(db, settings_row.manager_phone, "Teste de integracao WhatsApp do Sistema Carvao.")


@app.get("/api/reports/export.xlsx")
def export_xlsx(db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    sales = db.query(models.Sale).options(joinedload(models.Sale.seller)).order_by(models.Sale.occurred_at.desc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Vendas"
    ws.append(["ID", "Data", "Vendedor", "Pagamento", "Status", "Total"])
    for sale in sales:
        ws.append([sale.id, sale.occurred_at.strftime("%Y-%m-%d %H:%M"), sale.seller.name, sale.payment_method, sale.status, sale.total_value])
    stream = BytesIO()
    wb.save(stream)
    return Response(stream.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=relatorio-vendas.xlsx"})


@app.get("/api/reports/export.pdf")
def export_pdf(db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    sales = db.query(models.Sale).options(joinedload(models.Sale.seller)).order_by(models.Sale.occurred_at.desc()).limit(40).all()
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=A4)
    width, height = A4
    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "Relatorio de Vendas - Sistema Carvao")
    y -= 30
    pdf.setFont("Helvetica", 10)
    for sale in sales:
        pdf.drawString(40, y, f"#{sale.id} | {sale.occurred_at:%d/%m/%Y %H:%M} | {sale.seller.name} | {sale.payment_method} | R$ {sale.total_value:.2f}")
        y -= 18
        if y < 50:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 10)
    pdf.save()
    return Response(stream.getvalue(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio-vendas.pdf"})


@app.post("/api/whatsapp/webhook")
async def whatsapp_webhook(payload: dict):
    return {"received": True, "phase": "parser-ready", "payload": payload}
