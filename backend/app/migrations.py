from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def run_runtime_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "sales" not in tables:
        return
    columns = {column["name"] for column in inspector.get_columns("sales")}
    if "delivery_status" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE sales ADD COLUMN delivery_status VARCHAR(30) NOT NULL DEFAULT 'pendente'"))
    with engine.begin() as connection:
        if {"delivery_manifest_items", "delivery_manifests"}.issubset(tables):
            connection.execute(text("""
                UPDATE sales
                SET delivery_status = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM delivery_manifest_items dmi
                        WHERE dmi.sale_id = sales.id AND dmi.status = 'entregue'
                    ) THEN 'entregue'
                    WHEN EXISTS (
                        SELECT 1 FROM delivery_manifest_items dmi
                        WHERE dmi.sale_id = sales.id AND dmi.status = 'nao_entregue'
                    ) THEN 'nao_entregue'
                    WHEN EXISTS (
                        SELECT 1 FROM delivery_manifest_items dmi
                        JOIN delivery_manifests dm ON dm.id = dmi.manifest_id
                        WHERE dmi.sale_id = sales.id AND dm.status = 'em_rota'
                    ) THEN 'em_rota'
                    ELSE 'pendente'
                END
            """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_sales_delivery_status ON sales(delivery_status)"))
