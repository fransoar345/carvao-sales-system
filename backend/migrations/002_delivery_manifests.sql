CREATE TABLE IF NOT EXISTS delivery_manifests (
    id SERIAL PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    delivery_date DATE NOT NULL,
    driver_name VARCHAR(120) NOT NULL,
    vehicle VARCHAR(80),
    status VARCHAR(30) NOT NULL DEFAULT 'preparacao',
    notes TEXT,
    created_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS delivery_manifest_items (
    id SERIAL PRIMARY KEY,
    manifest_id INTEGER NOT NULL REFERENCES delivery_manifests(id),
    sale_id INTEGER NOT NULL REFERENCES sales(id),
    delivery_address VARCHAR(300) NOT NULL,
    delivery_order INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(30) NOT NULL DEFAULT 'pendente',
    delivered_at TIMESTAMP,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_delivery_manifests_delivery_date ON delivery_manifests(delivery_date);
CREATE INDEX IF NOT EXISTS ix_delivery_manifests_status ON delivery_manifests(status);
CREATE INDEX IF NOT EXISTS ix_delivery_manifest_items_manifest_id ON delivery_manifest_items(manifest_id);
CREATE INDEX IF NOT EXISTS ix_delivery_manifest_items_sale_id ON delivery_manifest_items(sale_id);
