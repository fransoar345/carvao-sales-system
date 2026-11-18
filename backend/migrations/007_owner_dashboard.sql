ALTER TABLE sales ADD COLUMN delivery_status VARCHAR(30) NOT NULL DEFAULT 'pendente';

UPDATE sales
SET delivery_status = CASE
    WHEN EXISTS (SELECT 1 FROM delivery_manifest_items dmi WHERE dmi.sale_id = sales.id AND dmi.status = 'entregue') THEN 'entregue'
    WHEN EXISTS (SELECT 1 FROM delivery_manifest_items dmi WHERE dmi.sale_id = sales.id AND dmi.status = 'nao_entregue') THEN 'nao_entregue'
    WHEN EXISTS (
        SELECT 1 FROM delivery_manifest_items dmi
        JOIN delivery_manifests dm ON dm.id = dmi.manifest_id
        WHERE dmi.sale_id = sales.id AND dm.status = 'em_rota'
    ) THEN 'em_rota'
    ELSE 'pendente'
END;

CREATE INDEX IF NOT EXISTS ix_sales_delivery_status ON sales(delivery_status);
