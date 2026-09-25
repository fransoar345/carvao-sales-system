CREATE TABLE IF NOT EXISTS permissions (id SERIAL PRIMARY KEY, code VARCHAR(100) NOT NULL UNIQUE, module VARCHAR(50) NOT NULL, name VARCHAR(140) NOT NULL, description TEXT);
CREATE TABLE IF NOT EXISTS access_roles (id SERIAL PRIMARY KEY, name VARCHAR(80) NOT NULL UNIQUE, description TEXT, active BOOLEAN NOT NULL DEFAULT TRUE, system BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS access_role_permissions (role_id INTEGER NOT NULL REFERENCES access_roles(id), permission_id INTEGER NOT NULL REFERENCES permissions(id), PRIMARY KEY (role_id, permission_id));
CREATE TABLE IF NOT EXISTS user_access_roles (user_id INTEGER NOT NULL REFERENCES users(id), role_id INTEGER NOT NULL REFERENCES access_roles(id), PRIMARY KEY (user_id, role_id));
CREATE TABLE IF NOT EXISTS user_permission_overrides (user_id INTEGER NOT NULL REFERENCES users(id), permission_id INTEGER NOT NULL REFERENCES permissions(id), allowed BOOLEAN NOT NULL, PRIMARY KEY (user_id, permission_id));
CREATE INDEX IF NOT EXISTS ix_permissions_module ON permissions(module);
CREATE TABLE IF NOT EXISTS security_audit_details (audit_log_id INTEGER PRIMARY KEY REFERENCES audit_logs(id), profiles VARCHAR(300), ip_address VARCHAR(64), module VARCHAR(80) NOT NULL, old_value TEXT, new_value TEXT);
