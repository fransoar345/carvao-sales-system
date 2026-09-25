PERMISSIONS = {
    "dashboard": ["view", "view_general", "view_own", "export", "view_financial", "view_seller_goals"],
    "sales": ["create", "edit", "cancel", "reopen", "delete", "change_customer", "change_seller", "change_payment", "change_price", "apply_discount", "change_price_table", "view_all", "view_own"],
    "customers": ["create", "edit", "deactivate", "delete", "view_all", "view_own", "transfer", "change_price_table", "change_credit_limit", "view_financial_history"],
    "products": ["create", "edit", "delete", "change_price", "change_cost", "change_minimum_stock", "deactivate", "view"],
    "stock": ["view", "entry", "exit", "adjust", "inventory", "return", "delete_movement", "view_history"],
    "finance": ["view_payables", "create_payables", "edit_payables", "delete_payables", "view_receivables", "create_receivables", "edit_receivables", "settle_titles", "reverse_payments", "view_cash_flow", "bank_reconciliation", "close_cash", "open_cash", "cash_withdrawal", "cash_supply", "manage_accounts"],
    "fiscal": ["issue_invoice", "cancel_invoice", "correction_letter", "void_number", "view_xml", "download_xml", "download_danfe"],
    "manifests": ["create", "edit", "cancel", "start_route", "finish_route", "confirm_delivery", "register_incident", "print", "view"],
    "reports": ["export_pdf", "export_excel", "view_financial", "view_commercial", "view_commission", "view_dre", "view_cash_flow", "view_audit"],
    "users": ["create", "edit", "deactivate", "delete", "change_password", "reset_password", "change_role", "change_permissions", "view"],
    "settings": ["general", "fiscal", "financial", "price_tables", "alerts", "integrations", "apis"],
}

PERMISSION_NAMES = {f"{module}.{action}": f"{module.replace('_', ' ').title()}: {action.replace('_', ' ')}" for module, actions in PERMISSIONS.items() for action in actions}

READ_PERMISSIONS = {code for code in PERMISSION_NAMES if any(part in code for part in (".view", "reports.", "dashboard."))}

ROLE_PERMISSIONS = {
    "Administrador": set(PERMISSION_NAMES),
    "Gerente": {code for code in PERMISSION_NAMES if code.startswith(("dashboard.", "sales.", "customers.", "products.", "stock.", "manifests.", "reports.")) and code not in {"customers.transfer", "sales.change_price", "sales.delete"}} | {"finance.view_payables", "finance.view_receivables", "finance.view_cash_flow", "finance.settle_titles", "finance.create_payables"},
    "Financeiro": {code for code in PERMISSION_NAMES if code.startswith(("finance.", "reports.view_financial", "reports.view_dre", "reports.view_cash_flow"))} | {"dashboard.view", "dashboard.view_financial", "customers.view_financial_history"},
    "Vendedor": {"dashboard.view", "dashboard.view_own", "sales.create", "sales.view_own", "customers.create", "customers.view_own", "customers.view_financial_history", "products.view", "reports.view_commission"},
    "Estoquista": {"products.view", "stock.view", "stock.entry", "stock.exit", "stock.adjust", "stock.inventory", "stock.return", "stock.view_history"},
    "Motorista": {"manifests.view", "manifests.confirm_delivery", "manifests.register_incident"},
    "Diretor": READ_PERMISSIONS | {"sales.view_all", "customers.view_all", "products.view", "stock.view", "finance.view_payables", "finance.view_receivables", "finance.view_cash_flow", "manifests.view"},
}
