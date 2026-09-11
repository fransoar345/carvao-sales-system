import asyncio
from datetime import date, datetime, time, timedelta
from io import BytesIO
from xml.sax.saxutils import escape

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
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


def delivery_manifest_options():
    return (
        joinedload(models.DeliveryManifest.items)
        .joinedload(models.DeliveryManifestItem.sale)
        .joinedload(models.Sale.seller),
        joinedload(models.DeliveryManifest.items)
        .joinedload(models.DeliveryManifestItem.sale)
        .joinedload(models.Sale.items)
        .joinedload(models.SaleItem.product),
    )


def get_delivery_manifest(db: Session, manifest_id: int) -> models.DeliveryManifest:
    manifest = db.query(models.DeliveryManifest).options(*delivery_manifest_options()).filter(models.DeliveryManifest.id == manifest_id).first()
    if not manifest:
        raise HTTPException(404, "Romaneio nao encontrado")
    return manifest


def delivery_manifest_to_schema(manifest: models.DeliveryManifest) -> schemas.DeliveryManifestOut:
    return schemas.DeliveryManifestOut(
        id=manifest.id,
        code=manifest.code,
        delivery_date=manifest.delivery_date,
        driver_name=manifest.driver_name,
        vehicle=manifest.vehicle,
        status=manifest.status,
        notes=manifest.notes,
        created_at=manifest.created_at,
        items=[
            schemas.DeliveryManifestItemOut(
                id=item.id,
                sale_id=item.sale_id,
                delivery_address=item.delivery_address,
                delivery_order=item.delivery_order,
                status=item.status,
                delivered_at=item.delivered_at,
                note=item.note,
                sale=sale_to_schema(item.sale),
            )
            for item in manifest.items
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


@app.delete("/api/sellers/{seller_id}")
def delete_seller(seller_id: int, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin"))):
    seller = db.get(models.Seller, seller_id)
    if not seller:
        raise HTTPException(404, "Vendedor nao encontrado")
    seller.active = False
    if seller.user:
        seller.user.active = False
    audit(db, user, "deactivate", "seller", seller.id, seller.name)
    db.commit()
    return {"ok": True}


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


@app.get("/api/delivery-manifests/pending-sales", response_model=list[schemas.SaleOut])
def list_sales_pending_delivery(db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    assigned_sale_ids = (
        db.query(models.DeliveryManifestItem.sale_id)
        .join(models.DeliveryManifest)
        .filter(models.DeliveryManifest.status != "cancelado")
    )
    sales = (
        db.query(models.Sale)
        .options(joinedload(models.Sale.seller), joinedload(models.Sale.items).joinedload(models.SaleItem.product))
        .filter(models.Sale.status == "confirmada", ~models.Sale.id.in_(assigned_sale_ids))
        .order_by(models.Sale.occurred_at.desc())
        .all()
    )
    return [sale_to_schema(sale) for sale in sales]


@app.get("/api/delivery-manifests", response_model=list[schemas.DeliveryManifestOut])
def list_delivery_manifests(db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    manifests = db.query(models.DeliveryManifest).options(*delivery_manifest_options()).order_by(models.DeliveryManifest.delivery_date.desc(), models.DeliveryManifest.id.desc()).limit(100).all()
    return [delivery_manifest_to_schema(manifest) for manifest in manifests]


@app.post("/api/delivery-manifests", response_model=schemas.DeliveryManifestOut)
def create_delivery_manifest(payload: schemas.DeliveryManifestCreate, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    sale_ids = [item.sale_id for item in payload.items]
    if len(sale_ids) != len(set(sale_ids)):
        raise HTTPException(400, "Uma venda nao pode aparecer duas vezes no mesmo romaneio")
    already_assigned = (
        db.query(models.DeliveryManifestItem)
        .join(models.DeliveryManifest)
        .filter(models.DeliveryManifestItem.sale_id.in_(sale_ids), models.DeliveryManifest.status != "cancelado")
        .first()
    )
    if already_assigned:
        raise HTTPException(400, f"A venda {already_assigned.sale_id} ja pertence a um romaneio ativo")
    sales = db.query(models.Sale).filter(models.Sale.id.in_(sale_ids), models.Sale.status == "confirmada").all()
    if len(sales) != len(sale_ids):
        raise HTTPException(400, "Uma ou mais vendas nao foram encontradas")

    manifest = models.DeliveryManifest(
        code=f"TMP-{datetime.utcnow():%y%m%d%H%M%S%f}",
        delivery_date=payload.delivery_date,
        driver_name=payload.driver_name,
        vehicle=payload.vehicle,
        status="preparacao",
        notes=payload.notes,
        created_by_id=user.id,
    )
    for position, item in enumerate(sorted(payload.items, key=lambda row: row.delivery_order), start=1):
        manifest.items.append(models.DeliveryManifestItem(
            sale_id=item.sale_id,
            delivery_address=item.delivery_address.strip(),
            delivery_order=position,
            status="pendente",
        ))
    db.add(manifest)
    db.flush()
    manifest.code = f"ROM-{payload.delivery_date:%Y%m%d}-{manifest.id:04d}"
    audit(db, user, "create", "delivery_manifest", manifest.id, f"{manifest.code} com {len(manifest.items)} entregas")
    db.commit()
    return delivery_manifest_to_schema(get_delivery_manifest(db, manifest.id))


@app.put("/api/delivery-manifests/{manifest_id}/status", response_model=schemas.DeliveryManifestOut)
def update_delivery_manifest_status(manifest_id: int, payload: schemas.DeliveryManifestStatusUpdate, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    allowed = {"preparacao", "em_rota", "concluido", "cancelado"}
    if payload.status not in allowed:
        raise HTTPException(400, "Status de romaneio invalido")
    manifest = get_delivery_manifest(db, manifest_id)
    if payload.status == "concluido" and any(item.status != "entregue" for item in manifest.items):
        raise HTTPException(400, "Confirme todas as entregas antes de concluir o romaneio")
    manifest.status = payload.status
    if payload.status == "cancelado":
        for item in manifest.items:
            if item.status != "entregue":
                item.status = "cancelado"
    audit(db, user, "status", "delivery_manifest", manifest.id, payload.status)
    db.commit()
    return delivery_manifest_to_schema(get_delivery_manifest(db, manifest.id))


@app.put("/api/delivery-manifests/{manifest_id}/items/{item_id}", response_model=schemas.DeliveryManifestOut)
def update_delivery_item(manifest_id: int, item_id: int, payload: schemas.DeliveryItemStatusUpdate, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    allowed = {"pendente", "entregue", "nao_entregue"}
    if payload.status not in allowed:
        raise HTTPException(400, "Status de entrega invalido")
    manifest = get_delivery_manifest(db, manifest_id)
    if manifest.status == "cancelado":
        raise HTTPException(400, "Romaneio cancelado")
    item = next((row for row in manifest.items if row.id == item_id), None)
    if not item:
        raise HTTPException(404, "Entrega nao encontrada")
    item.status = payload.status
    item.note = payload.note
    item.delivered_at = datetime.utcnow() if payload.status == "entregue" else None
    if manifest.status == "preparacao":
        manifest.status = "em_rota"
    if all(row.status == "entregue" for row in manifest.items):
        manifest.status = "concluido"
    audit(db, user, "status", "delivery_manifest_item", item.id, payload.status)
    db.commit()
    return delivery_manifest_to_schema(get_delivery_manifest(db, manifest.id))


@app.get("/api/delivery-manifests/{manifest_id}/pdf")
def delivery_manifest_pdf(manifest_id: int, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin", "gerente"))):
    manifest = get_delivery_manifest(db, manifest_id)
    stream = BytesIO()
    doc = SimpleDocTemplate(
        stream,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Romaneio {manifest.code}",
        author=settings.app_name,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ManifestTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=colors.HexColor("#17201a"), spaceAfter=3 * mm)
    subtitle_style = ParagraphStyle("ManifestSubtitle", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#66756b"))
    cell_style = ParagraphStyle("ManifestCell", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#17201a"))
    cell_bold_style = ParagraphStyle("ManifestCellBold", parent=cell_style, fontName="Helvetica-Bold")
    small_style = ParagraphStyle("ManifestSmall", parent=styles["Normal"], fontSize=7.5, leading=9, textColor=colors.HexColor("#66756b"))
    status_labels = {"preparacao": "EM PREPARACAO", "em_rota": "EM ROTA", "concluido": "CONCLUIDO", "cancelado": "CANCELADO", "pendente": "PENDENTE", "entregue": "ENTREGUE", "nao_entregue": "NAO ENTREGUE"}

    story = [
        Paragraph("CARVAO PRO", subtitle_style),
        Paragraph("Romaneio de Entregas", title_style),
        Paragraph(manifest.code, subtitle_style),
        Spacer(1, 2 * mm),
    ]
    details = [
        [Paragraph("DATA DA ENTREGA", small_style), Paragraph("MOTORISTA", small_style), Paragraph("VEICULO", small_style), Paragraph("STATUS", small_style)],
        [Paragraph(manifest.delivery_date.strftime("%d/%m/%Y"), cell_bold_style), Paragraph(escape(manifest.driver_name), cell_bold_style), Paragraph(escape(manifest.vehicle or "Nao informado"), cell_style), Paragraph(status_labels.get(manifest.status, manifest.status.upper()), cell_bold_style)],
    ]
    details_table = Table(details, colWidths=[34 * mm, 58 * mm, 48 * mm, 37 * mm])
    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4ed")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cfd8cd")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dfe6dd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([details_table, Spacer(1, 4 * mm)])
    if manifest.notes:
        story.extend([Paragraph(f"<b>Observacoes:</b> {escape(manifest.notes)}", cell_style), Spacer(1, 4 * mm)])

    rows = [[
        Paragraph("ORDEM", small_style),
        Paragraph("CLIENTE / CONTATO", small_style),
        Paragraph("ENDERECO", small_style),
        Paragraph("PRODUTOS", small_style),
        Paragraph("VALOR", small_style),
        Paragraph("ENTREGA", small_style),
    ]]
    total_value = 0.0
    for item in manifest.items:
        sale = item.sale
        products = "<br/>".join(f"{sale_item.quantity:g}x {escape(sale_item.product.name)}" for sale_item in sale.items)
        total_value += sale.total_value
        rows.append([
            Paragraph(str(item.delivery_order), cell_bold_style),
            Paragraph(f"<b>{escape(sale.customer_name or f'Venda #{sale.id}')}</b><br/>{escape(sale.customer_phone or 'Sem telefone')}", cell_style),
            Paragraph(escape(item.delivery_address), cell_style),
            Paragraph(products, cell_style),
            Paragraph(f"R$ {sale.total_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), cell_style),
            Paragraph(status_labels.get(item.status, item.status.upper()), cell_bold_style),
        ])
    deliveries_table = Table(rows, colWidths=[17 * mm, 37 * mm, 45 * mm, 35 * mm, 24 * mm, 25 * mm], repeatRows=1)
    deliveries_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18231c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfd8cd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9f6")]),
    ]))
    total_label = f"{len(manifest.items)} entrega(s) - Total R$ {total_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    story.extend([deliveries_table, Spacer(1, 4 * mm), Paragraph(f"<b>{total_label}</b>", cell_style), Spacer(1, 14 * mm)])
    signatures = Table([
        ["________________________________", "________________________________"],
        ["Motorista", "Responsavel pela expedicao"],
    ], colWidths=[85 * mm, 85 * mm])
    signatures.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#66756b")),
    ]))
    story.append(signatures)

    def draw_page_number(pdf_canvas, pdf_doc):
        pdf_canvas.saveState()
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.setFillColor(colors.HexColor("#66756b"))
        pdf_canvas.drawString(14 * mm, 9 * mm, f"Emitido em {datetime.now():%d/%m/%Y %H:%M}")
        pdf_canvas.drawRightString(A4[0] - 14 * mm, 9 * mm, f"Pagina {pdf_doc.page}")
        pdf_canvas.restoreState()

    doc.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
    filename = f"romaneio-{manifest.code}.pdf"
    return Response(stream.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{filename}"'})


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
