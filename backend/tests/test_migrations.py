from sqlalchemy import create_engine, inspect, text

from app.migrations import run_runtime_migrations


def test_delivery_status_migration_preserves_sales_and_maps_existing_delivery(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer_name VARCHAR(255))"))
        connection.execute(text("CREATE TABLE delivery_manifests (id INTEGER PRIMARY KEY, status VARCHAR(30))"))
        connection.execute(text("CREATE TABLE delivery_manifest_items (id INTEGER PRIMARY KEY, manifest_id INTEGER, sale_id INTEGER, status VARCHAR(30))"))
        connection.execute(text("INSERT INTO sales (id, customer_name) VALUES (1, 'Cliente preservado')"))
        connection.execute(text("INSERT INTO delivery_manifests (id, status) VALUES (1, 'concluido')"))
        connection.execute(text("INSERT INTO delivery_manifest_items (id, manifest_id, sale_id, status) VALUES (1, 1, 1, 'entregue')"))

    run_runtime_migrations(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("sales")}
    with engine.connect() as connection:
        row = connection.execute(text("SELECT customer_name, delivery_status FROM sales WHERE id = 1")).one()
    assert "delivery_status" in columns
    assert row == ("Cliente preservado", "entregue")
