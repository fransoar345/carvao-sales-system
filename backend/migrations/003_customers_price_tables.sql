CREATE TABLE IF NOT EXISTS price_tables (
    id SERIAL PRIMARY KEY, name VARCHAR(120) NOT NULL UNIQUE, description TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE, active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS price_table_items (
    id SERIAL PRIMARY KEY, price_table_id INTEGER NOT NULL REFERENCES price_tables(id),
    product_id INTEGER NOT NULL REFERENCES products(id), price DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_price_table_product UNIQUE (price_table_id, product_id)
);
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY, cnpj VARCHAR(14) NOT NULL UNIQUE, legal_name VARCHAR(180) NOT NULL,
    state_registration VARCHAR(40) NOT NULL, address VARCHAR(300) NOT NULL,
    reference_point VARCHAR(200) NOT NULL, phone VARCHAR(30), email VARCHAR(160),
    price_table_id INTEGER REFERENCES price_tables(id), active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sale_customer_links (
    sale_id INTEGER PRIMARY KEY REFERENCES sales(id), customer_id INTEGER NOT NULL REFERENCES customers(id),
    price_table_id INTEGER NOT NULL REFERENCES price_tables(id)
);
CREATE TABLE IF NOT EXISTS sale_payment_terms (
    sale_id INTEGER PRIMARY KEY REFERENCES sales(id), due_date DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_price_table_items_table ON price_table_items(price_table_id);
CREATE INDEX IF NOT EXISTS ix_customers_cnpj ON customers(cnpj);
CREATE INDEX IF NOT EXISTS ix_sale_customer_links_customer ON sale_customer_links(customer_id);
