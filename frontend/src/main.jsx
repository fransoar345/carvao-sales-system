import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { BarChart3, Building2, Ban, Boxes, CheckCircle2, ClipboardList, Trash2, Download, LogOut, MessageCircle, MapPin, PackagePlus, Play, Printer, ReceiptText, Save, ShieldCheck, ShoppingCart, Truck, Tags, UserPlus, Users, WalletCards } from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "https://carvao-sales-system-production.up.railway.app/api";
const money = (v) =>
  Number(v || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
const apiErrorMessage = (payload) => {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || "Campo invalido").join("; ");
  return "Erro na requisicao";
};
const legacyPermissions = {
  gerente: ["dashboard.view", "dashboard.view_general", "sales.create", "sales.edit", "sales.cancel", "sales.change_seller", "sales.view_all", "customers.view_all", "products.view", "products.create", "products.edit", "stock.view", "stock.entry", "stock.exit", "stock.adjust", "stock.view_history", "manifests.view", "manifests.create", "manifests.edit", "manifests.cancel", "manifests.start_route", "manifests.finish_route", "manifests.confirm_delivery", "manifests.print", "finance.view_receivables", "finance.view_payables", "finance.view_cash_flow", "finance.create_payables", "finance.settle_titles", "reports.export_pdf", "reports.export_excel", "settings.price_tables"],
  vendedor: ["dashboard.view", "dashboard.view_own", "sales.create", "sales.view_own", "customers.create", "customers.view_own", "products.view", "reports.view_commission"],
};
const allowed = (user, permission) => {
  if ((user?.permissions || []).length) return user.permissions.includes(permission);
  if (user?.role === "admin") return true;
  return (legacyPermissions[user?.role] || []).includes(permission);
};

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [user, setUser] = useState(JSON.parse(localStorage.getItem("user") || "null"));
  const [tab, setTab] = useState("dashboard");

  const api = useMemo(
    () => ({
      async call(path, options = {}) {
        const res = await fetch(`${API}${path}`, {
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.headers || {}),
          },
        });
        if (!res.ok) throw new Error(apiErrorMessage(await res.json()));
        return res.json();
      },
    }),
    [token],
  );

  useEffect(() => {
    if (token) api.call("/auth/me").then((current) => { setUser(current); localStorage.setItem("user", JSON.stringify(current)); }).catch(() => logout());
  }, [token, api]);

  function onLogin(data) {
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
  }

  function logout() {
    localStorage.clear();
    setToken(null);
    setUser(null);
  }

  if (!token) return <Login onLogin={onLogin} />;

  const can = (permission) => (user.permissions || []).includes(permission);
  const tabs = [
    ["dashboard", "Dashboard", BarChart3, "dashboard.view"],
    ["sale", "Venda", ShoppingCart, "sales.create"],
    ["customers", "Clientes", Building2, ["customers.view_all", "customers.view_own"]],
    ["prices", "Tabelas", Tags, "settings.price_tables"],
    ["products", "Produtos", Boxes, "products.view"],
    ["stock", "Estoque", PackagePlus, "stock.view"],
    ["deliveries", "Romaneios", ClipboardList, "manifests.view"],
    ["finance", "Financeiro", WalletCards, "finance.view_receivables"],
    ["sellers", "Vendedores", Users, "users.view"],
    ["access", "Perfis e Permissoes", ShieldCheck, "users.change_permissions"],
    ["whatsapp", "Alertas", MessageCircle, "settings.alerts"],
  ].filter((item) => Array.isArray(item[3]) ? item[3].some(can) : can(item[3]));

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="mark">C</span>
          <div>
            <strong>Carvao Pro</strong>
            <small>vendas e estoque</small>
          </div>
        </div>
        <nav>
          {tabs.map(([id, label, Icon]) => (
            <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)} title={label}>
              <Icon size={18} /> <span>{label}</span>
            </button>
          ))}
        </nav>
        <button className="logout" onClick={logout}>
          <LogOut size={18} /> Sair
        </button>
      </aside>
      <main>
        <header>
          <div>
            <h1>{tabs.find((x) => x[0] === tab)?.[1]}</h1>
            <p>
              {user.name} · {(user.profiles || [user.role]).join(", ")}
            </p>
          </div>
        </header>
        {tab === "dashboard" && <Dashboard api={api} token={token} user={user} />}
        {tab === "sale" && <Sales api={api} user={user} />}
        {tab === "customers" && <Customers api={api} user={user} />}
        {tab === "prices" && <PriceTables api={api} />}
        {tab === "products" && <Products api={api} user={user} />}
        {tab === "stock" && <Stock api={api} user={user} />}
        {tab === "deliveries" && <Deliveries api={api} token={token} />}
        {tab === "finance" && <Finance api={api} user={user} />}
        {tab === "access" && <><NewAccessUser api={api} /><AccessControl api={api} /></>}
        {tab === "sellers" && <Sellers api={api} user={user} />}
        {tab === "whatsapp" && <WhatsApp api={api} />}
      </main>
    </div>
  );
}

function Login({ onLogin }) {
  const [email, setEmail] = useState("admin@carvao.local");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault();
    setError("");
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(`${API}/auth/login`, { method: "POST", body });
    if (!res.ok) return setError("Credenciais invalidas");
    onLogin(await res.json());
  }
  return (
    <section className="login">
      <form onSubmit={submit} className="panel login-card">
        <span className="mark large">C</span>
        <h1>Carvao Pro</h1>
        <label>
          E-mail
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Senha
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="primary">Entrar</button>
        <p className="hint">admin@carvao.local / admin123</p>
      </form>
    </section>
  );
}

function useLoad(api, loader, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const reload = () =>
    loader()
      .then(setData)
      .catch((e) => setError(e.message));
  useEffect(() => {
    reload();
  }, deps);
  return { data, setData, error, reload };
}

function Dashboard({ api, token }) {
  const today = new Date().toISOString().slice(0, 10);
  const [filters, setFilters] = useState({
    start: today,
    end: today,
    seller_id: "",
  });
  const { data, reload } = useLoad(api, () => api.call(`/dashboard?start=${filters.start}&end=${filters.end}${filters.seller_id ? `&seller_id=${filters.seller_id}` : ""}`), [filters]);
  const sellers = useLoad(api, () => api.call("/sellers"), []).data || [];
  if (!data) return <Loading />;
  const coal = data.stock.filter((p) => p.type === "saco_fechado");
  const packs = data.stock.filter((p) => p.type === "embalagem_vazia");
  const exportFile = async (kind) => {
    const res = await fetch(`${API}/reports/export.${kind}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio-vendas.${kind}`;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <section className="grid">
      <div className="toolbar full">
        <input type="date" value={filters.start} onChange={(e) => setFilters({ ...filters, start: e.target.value })} />
        <input type="date" value={filters.end} onChange={(e) => setFilters({ ...filters, end: e.target.value })} />
        <select value={filters.seller_id} onChange={(e) => setFilters({ ...filters, seller_id: e.target.value })}>
          <option value="">Todos vendedores</option>
          {sellers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <button onClick={reload}>Atualizar</button>
        <button onClick={() => exportFile("xlsx")}>
          <Download size={16} /> Excel
        </button>
        <button onClick={() => exportFile("pdf")}>
          <Download size={16} /> PDF
        </button>
      </div>
      <Metric label="Vendido no periodo" value={money(data.total_value)} />
      <Metric label="Vendas confirmadas" value={data.sales_count} />
      <Metric label="Itens vendidos" value={data.items_quantity} />
      <Panel title="Sacos fechados">
        {coal.map((p) => (
          <StockLine key={p.id} p={p} />
        ))}
      </Panel>
      <Panel title="Embalagens vazias">
        {packs.map((p) => (
          <StockLine key={p.id} p={p} />
        ))}
      </Panel>
      <Panel title="Ranking de vendedores" className="wide">
        {data.ranking.map((r, i) => (
          <div className="rank" key={r.seller_id}>
            <b>
              #{i + 1} {r.seller_name}
            </b>
            <span>
              {Number(r.quantity).toLocaleString("pt-BR")} itens · {money(r.value)} · comissao {money(r.commission)}
            </span>
          </div>
        ))}
      </Panel>
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StockLine({ p }) {
  return (
    <div className={p.low ? "stock low" : "stock"}>
      <span>{p.name}</span>
      <b>
        {p.current_stock} {p.unit}
      </b>
    </div>
  );
}

function Panel({ title, children, className = "" }) {
  return (
    <div className={`panel ${className}`}>
      <h2>{title}</h2>
      {children}
    </div>
  );
}

function Products({ api, user }) {
  const empty = {
    name: "",
    type: "saco_fechado",
    unit: "saco",
    cost_price: 0,
    sale_price: 0,
    current_stock: 0,
    minimum_stock: 0,
    active: true,
  };
  const [form, setForm] = useState(empty);
  const { data: products, reload } = useLoad(api, () => api.call("/products"), []);
  async function save(e) {
    e.preventDefault();
    await api.call(form.id ? `/products/${form.id}` : "/products", {
      method: form.id ? "PUT" : "POST",
      body: JSON.stringify(form),
    });
    setForm(empty);
    reload();
  }
  return (
    <CrudLayout
      form={allowed(user, "products.create") || allowed(user, "products.edit") ? <ProductForm form={form} setForm={setForm} save={save} /> : null}
      list={(products || []).map((p) => (
        <Row key={p.id} title={p.name} meta={`${p.type} · estoque ${p.current_stock} · venda ${money(p.sale_price)}`} onEdit={allowed(user, "products.edit") ? () => setForm(p) : null} />
      ))}
    />
  );
}

function ProductForm({ form, setForm, save }) {
  return (
    <form className="panel form" onSubmit={save}>
      <h2>Cadastro de Produto</h2>
      <label className="field">
        <span>Nome do produto</span>
        <input placeholder="Ex.: Carvao Premium 5 kg" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
      </label>
      <label className="field">
        <span>Tipo do produto</span>
        <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
          <option value="saco_fechado">Saco fechado de carvao</option>
          <option value="embalagem_vazia">Embalagem vazia</option>
          <option value="outro">Outro</option>
        </select>
      </label>
      <label className="field">
        <span>Unidade de contagem</span>
        <input placeholder="Ex.: saco, unidade ou kg" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
      </label>
      <label className="field">
        <span>Preco de custo (R$)</span>
        <input type="number" min="0" step="0.01" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: Number(e.target.value) })} />
      </label>
      <label className="field">
        <span>Preco de venda (R$)</span>
        <input type="number" min="0" step="0.01" value={form.sale_price} onChange={(e) => setForm({ ...form, sale_price: Number(e.target.value) })} />
      </label>
      <label className="field">
        <span>Quantidade inicial no estoque</span>
        <input type="number" min="0" step="0.01" value={form.current_stock} onChange={(e) => setForm({ ...form, current_stock: Number(e.target.value) })} />
      </label>
      <label className="field">
        <span>Quantidade minima para alerta</span>
        <input type="number" min="0" step="0.01" value={form.minimum_stock} onChange={(e) => setForm({ ...form, minimum_stock: Number(e.target.value) })} />
      </label>
      <button className="primary">
        <Save size={16} /> Salvar Produto
      </button>
    </form>
  );
}

function Stock({ api, user }) {
  const [form, setForm] = useState({
    product_id: "",
    movement_type: "entrada",
    quantity: 1,
    note: "",
  });
  const productsLoad = useLoad(api, () => api.call("/products"), []);
  const products = productsLoad.data || [];
  const { data: movements, reload } = useLoad(api, () => api.call("/stock/movements"), []);
  async function save(e) {
    e.preventDefault();
    await api.call("/stock/movements", {
      method: "POST",
      body: JSON.stringify({ ...form, product_id: Number(form.product_id) }),
    });
    productsLoad.reload();
    reload();
  }
  return (
    <section className="stock-page">
      <CrudLayout
        form={allowed(user, "stock.entry") || allowed(user, "stock.exit") || allowed(user, "stock.adjust") ?
          <form className="panel form" onSubmit={save}>
            <h2>Entrada/Saida de Estoque</h2>
            <select value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} required>
              <option value="">Produto</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} · {p.current_stock} {p.unit}
                </option>
              ))}
            </select>
            <select value={form.movement_type} onChange={(e) => setForm({ ...form, movement_type: e.target.value })}>
              <option value="entrada">Entrada</option>
              <option value="saida">Saida</option>
              <option value="ajuste">Ajuste positivo</option>
              <option value="devolucao">Devolucao</option>
            </select>
            <input type="number" step="0.01" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })} />
            <textarea placeholder="Observacao" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            <button className="primary">Registrar Movimentacao</button>
          </form>
        : null}
        list={(movements || []).map((m) => (
          <Row key={m.id} title={`${m.product_name} · ${m.movement_type}`} meta={`${m.quantity} em ${new Date(m.occurred_at).toLocaleString("pt-BR")} · ${m.note || ""}`} />
        ))}
      />
      <Panel title="Quantidade atual dos produtos" className="full">
        {products.map((p) => (
          <StockLine key={p.id} p={p} />
        ))}
      </Panel>
    </section>
  );
}

function Sellers({ api, user }) {
  const empty = {
    name: "",
    phone: "+55",
    monthly_goal: 0,
    commission_percent: 0,
    email: "",
    temporary_password: "vendedor123",
  };
  const [form, setForm] = useState(empty);
  const { data: sellers, reload } = useLoad(api, () => api.call("/sellers"), []);
  async function save(e) {
    e.preventDefault();
    await api.call("/sellers", { method: "POST", body: JSON.stringify(form) });
    setForm(empty);
    reload();
  }
  async function removeSeller(seller) {
    if (!window.confirm(`Excluir vendedor ${seller.name}? O historico de vendas sera mantido.`)) return;
    await api.call(`/sellers/${seller.id}`, {
      method: "PUT",
      body: JSON.stringify({ active: false }),
    });
    reload();
  }
  return (
    <CrudLayout
      form={allowed(user, "users.create") ?
        <form className="panel form" onSubmit={save}>
          <h2>Cadastro de Vendedor</h2>
          <label className="field">
            <span>Nome do vendedor</span>
            <input placeholder="Ex.: Maria Silva" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label className="field">
            <span>Telefone / WhatsApp</span>
            <input placeholder="Ex.: +5563999999999" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required />
          </label>
          <label className="field">
            <span>E-mail de acesso</span>
            <input type="email" placeholder="Ex.: maria@empresa.com" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </label>
          <label className="field">
            <span>Senha inicial</span>
            <input type="text" placeholder="Minimo de 6 caracteres" value={form.temporary_password} onChange={(e) => setForm({ ...form, temporary_password: e.target.value })} minLength={6} required />
          </label>
          <label className="field">
            <span>Meta mensal de vendas (R$)</span>
            <input type="number" min="0" step="0.01" value={form.monthly_goal} onChange={(e) => setForm({ ...form, monthly_goal: Number(e.target.value) })} />
          </label>
          <label className="field">
            <span>Comissao sobre vendas (%)</span>
            <input type="number" min="0" max="100" step="0.01" value={form.commission_percent} onChange={(e) => setForm({ ...form, commission_percent: Number(e.target.value) })} />
          </label>
          <button className="primary">
            <Save size={16} /> Salvar Vendedor
          </button>
        </form>
      : null}
      list={(sellers || []).map((s) => (
        <Row
          key={s.id}
          title={s.name}
          meta={`${s.phone} · ${s.email} · ${s.active ? "ativo" : "inativo"}`}
          actions={allowed(user, "users.deactivate") ?
            <button className="danger" onClick={() => removeSeller(s)}>
              <Trash2 size={16} /> Excluir
            </button>
          : null}
        />
      ))}
    />
  );
}

const emptyCustomer = {
  cnpj: "",
  legal_name: "",
  state_registration: "",
  address: "",
  reference_point: "",
  phone: "",
  email: "",
  price_table_id: "",
  owner_seller_id: "",
  active: true,
};

function CustomerFields({ form, setForm, tables, sellers = [], showOwner = false, showPriceTable = true, compact = false }) {
  return (
    <div className={compact ? "customer-fields compact" : "customer-fields"}>
      {showPriceTable && <label className="field">
        <span>CNPJ</span>
        <input value={form.cnpj} onChange={(e) => setForm({ ...form, cnpj: e.target.value })} placeholder="00.000.000/0000-00" required />
      </label>}
      <label className="field">
        <span>Razao Social</span>
        <input value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} required />
      </label>
      <label className="field">
        <span>Inscricao Estadual</span>
        <input value={form.state_registration} onChange={(e) => setForm({ ...form, state_registration: e.target.value })} required />
      </label>
      <label className="field">
        <span>Endereco completo</span>
        <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} required />
      </label>
      <label className="field">
        <span>Ponto de referencia</span>
        <input value={form.reference_point} onChange={(e) => setForm({ ...form, reference_point: e.target.value })} required />
      </label>
      <label className="field">
        <span>Telefone</span>
        <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Telefone ou WhatsApp" />
      </label>
      <label className="field">
        <span>E-mail</span>
        <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      </label>
      <label className="field">
        <span>Tabela de precos</span>
        <select value={form.price_table_id || ""} onChange={(e) => setForm({ ...form, price_table_id: e.target.value })}>
          <option value="">Tabela padrao</option>
          {tables
            .filter((t) => t.active)
            .map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
        </select>
      </label>
      {showOwner && (
        <label className="field">
          <span>Vendedor responsavel</span>
          <select value={form.owner_seller_id || ""} onChange={(e) => setForm({ ...form, owner_seller_id: e.target.value })} required>
            <option value="">Selecione o vendedor</option>
            {sellers.filter((seller) => seller.active).map((seller) => <option key={seller.id} value={seller.id}>{seller.name}</option>)}
          </select>
        </label>
      )}
    </div>
  );
}

function Customers({ api, user }) {
  const [form, setForm] = useState(emptyCustomer);
  const [message, setMessage] = useState("");
  const customersLoad = useLoad(api, () => api.call("/customers"), []);
  const tables = useLoad(api, () => api.call("/price-tables"), []).data || [];
  const sellers = useLoad(api, () => api.call("/sellers"), []).data || [];
  async function save(e) {
    e.preventDefault();
    setMessage("");
    try {
      const payload = {
        ...form,
        price_table_id: form.price_table_id ? Number(form.price_table_id) : null,
        owner_seller_id: Number(form.owner_seller_id),
      };
      await api.call(form.id ? `/customers/${form.id}` : "/customers", {
        method: form.id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      setForm(emptyCustomer);
      customersLoad.reload();
      setMessage("Cliente salvo com sucesso.");
    } catch (error) {
      setMessage(error.message);
    }
  }
  const list = (customersLoad.data || []).map((c) => <Row key={c.id} title={c.legal_name} meta={`CNPJ ${c.cnpj} · Vendedor: ${c.owner_seller_name || "nao definido"} · ${c.price_table_name || "Tabela padrao"} · ${c.phone || c.email}`} onEdit={allowed(user, "customers.edit") ? () => setForm({ ...c, price_table_id: c.price_table_id || "", owner_seller_id: c.owner_seller_id || "" }) : null} />);
  return (
    <CrudLayout
      form={
        <form className="panel form" onSubmit={save}>
          <h2>{form.id ? "Alterar cliente" : "Cadastro de cliente"}</h2>
          <CustomerFields form={form} setForm={setForm} tables={tables} sellers={sellers} showOwner={allowed(user, "customers.transfer")} showPriceTable={allowed(user, "customers.change_price_table")} />
          <button className="primary">
            <Save size={16} /> Salvar cliente
          </button>
          {message && <p className="form-status">{message}</p>}
        </form>
      }
      list={list}
    />
  );
}

function PriceTables({ api }) {
  const [form, setForm] = useState({
    name: "",
    description: "",
    is_default: false,
    active: true,
    prices: {},
  });
  const [message, setMessage] = useState("");
  const products = useLoad(api, () => api.call("/products"), []).data || [];
  const tablesLoad = useLoad(api, () => api.call("/price-tables"), []);
  function edit(row) {
    setForm({
      id: row.id,
      name: row.name,
      description: row.description || "",
      is_default: row.is_default,
      active: row.active,
      prices: Object.fromEntries(row.items.map((i) => [i.product_id, i.price])),
    });
  }
  async function save(e) {
    e.preventDefault();
    setMessage("");
    const payload = {
      name: form.name,
      description: form.description,
      is_default: form.is_default,
      active: form.active,
      items: products
        .filter((p) => p.active)
        .map((p) => ({
          product_id: p.id,
          price: Number(form.prices[p.id] ?? p.sale_price),
        })),
    };
    try {
      await api.call(form.id ? `/price-tables/${form.id}` : "/price-tables", {
        method: form.id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      setForm({
        name: "",
        description: "",
        is_default: false,
        active: true,
        prices: {},
      });
      tablesLoad.reload();
      setMessage("Tabela salva com sucesso.");
    } catch (error) {
      setMessage(error.message);
    }
  }
  return (
    <CrudLayout
      form={
        <form className="panel form" onSubmit={save}>
          <h2>{form.id ? "Alterar tabela" : "Nova tabela de precos"}</h2>
          <label className="field">
            <span>Nome da tabela</span>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ex.: Com nota fiscal" required />
          </label>
          <label className="field">
            <span>Descricao</span>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </label>
          <label className="check">
            <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} /> Usar como tabela padrao
          </label>
          <div className="price-grid">
            {products
              .filter((p) => p.active)
              .map((p) => (
                <label className="field" key={p.id}>
                  <span>{p.name} (R$)</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.prices[p.id] ?? p.sale_price}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        prices: { ...form.prices, [p.id]: e.target.value },
                      })
                    }
                    required
                  />
                </label>
              ))}
          </div>
          <button className="primary">
            <Save size={16} /> Salvar tabela
          </button>
          {message && <p className="form-status">{message}</p>}
        </form>
      }
      list={(tablesLoad.data || []).map((t) => (
        <Row key={t.id} title={t.name} meta={`${t.items.length} produtos · ${t.is_default ? "padrao" : "personalizada"} · ${t.active ? "ativa" : "inativa"}`} onEdit={() => edit(t)} />
      ))}
    />
  );
}

function Sales({ api, user }) {
  const emptySale = {
    seller_id: "",
    customer_id: "",
    product_id: "",
    quantity: 1,
    payment_method: "pix",
    payment_condition_id: "",
    payment_due_date: "",
    delivery_address: "",
    manual_address: false,
  };
  const [form, setForm] = useState(emptySale);
  const [editingId, setEditingId] = useState(null);
  const [message, setMessage] = useState("");
  const products = useLoad(api, () => api.call("/products"), []).data || [];
  const sellers = useLoad(api, () => api.call("/sellers"), []).data || [];
  const customersLoad = useLoad(api, () => api.call("/customers"), []);
  const tables = useLoad(api, () => api.call("/price-tables"), []).data || [];
  const paymentConditions = useLoad(api, () => api.call("/finance/payment-conditions"), []).data || [];
  const [showCustomer, setShowCustomer] = useState(false);
  const [customerForm, setCustomerForm] = useState(emptyCustomer);
  const { data: sales, reload } = useLoad(api, () => api.call("/sales"), []);
  const product = products.find((p) => p.id === Number(form.product_id));
  const customer = (customersLoad.data || []).find((c) => c.id === Number(form.customer_id));
  const priceTable = tables.find((t) => t.id === (customer?.price_table_id || tables.find((x) => x.is_default)?.id));
  const unitPrice = priceTable?.items.find((i) => i.product_id === Number(form.product_id))?.price;
  const total = unitPrice != null ? unitPrice * form.quantity : 0;
  const customerAddress = customer ? `${customer.address}${customer.reference_point ? ` - Referencia: ${customer.reference_point}` : ""}` : "";
  async function save(e) {
    e.preventDefault();
    setMessage("");
    const payload = {
      seller_id: form.seller_id ? Number(form.seller_id) : undefined,
      customer_id: Number(form.customer_id),
      payment_method: form.payment_method,
      payment_condition_id: form.payment_method === "prazo" && form.payment_condition_id ? Number(form.payment_condition_id) : null,
      payment_due_date: form.payment_method === "prazo" && form.payment_due_date ? form.payment_due_date : null,
      delivery_address: form.delivery_address,
      items: [
        {
          product_id: Number(form.product_id),
          quantity: Number(form.quantity),
        },
      ],
    };
    try {
      await api.call(editingId ? `/sales/${editingId}` : "/sales", {
        method: editingId ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      setMessage(editingId ? "Venda alterada e estoque recalculado." : "Venda registrada com sucesso.");
      setEditingId(null);
      setForm(emptySale);
      reload();
    } catch (error) {
      setMessage(error.message);
    }
  }
  function startEdit(sale) {
    if (sale.items.length !== 1) return setMessage("Esta venda possui varios produtos e nao pode ser editada por este formulario.");
    const item = sale.items[0];
    setEditingId(sale.id);
    setForm({
      seller_id: String(sale.seller_id),
      customer_id: String(sale.customer_id || ""),
      product_id: String(item.product_id),
      quantity: item.quantity,
      payment_method: sale.payment_method,
      payment_condition_id: "",
      payment_due_date: sale.payment_due_date || "",
      delivery_address: sale.delivery_address || "",
      manual_address: false,
    });
    setMessage(`Editando venda #${sale.id}.`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function cancelEdit() {
    setEditingId(null);
    setForm(emptySale);
    setMessage("");
  }
  async function removeSale(sale) {
    if (!window.confirm(`Excluir a venda #${sale.id}? Os produtos serao devolvidos ao estoque.`)) return;
    try {
      await api.call(`/sales/${sale.id}`, { method: "DELETE" });
      if (editingId === sale.id) cancelEdit();
      setMessage("Venda cancelada e produtos devolvidos ao estoque.");
      reload();
    } catch (error) {
      setMessage(error.message);
    }
  }
  async function createCustomer(e) {
    e.preventDefault();
    setMessage("");
    try {
      const created = await api.call("/customers", {
        method: "POST",
        body: JSON.stringify({
          ...customerForm,
          price_table_id: customerForm.price_table_id ? Number(customerForm.price_table_id) : null,
          owner_seller_id: allowed(user, "customers.transfer") ? Number(customerForm.owner_seller_id || form.seller_id) : undefined,
        }),
      });
      await customersLoad.reload();
      setForm((current) => ({ ...current, customer_id: String(created.id) }));
      setCustomerForm(emptyCustomer);
      setShowCustomer(false);
      setMessage("Cliente cadastrado e selecionado.");
    } catch (error) {
      setMessage(error.message);
    }
  }
  const formPanel = (
    <div className="sale-stack">
      <form className="panel form sale-form" onSubmit={save}>
        <h2>{editingId ? `Alterar venda #${editingId}` : "Lancar Venda"}</h2>
        {editingId && <p className="edit-banner">Ao salvar, o estoque anterior sera devolvido e a nova quantidade sera baixada.</p>}
        {allowed(user, "sales.change_seller") && (
          <label className="field">
            <span>Vendedor</span>
            <select value={form.seller_id} onChange={(e) => setForm({ ...form, seller_id: e.target.value, customer_id: "", delivery_address: "", manual_address: false })} required>
              <option value="">Selecione</option>
              {sellers
                .filter((s) => s.active)
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
            </select>
          </label>
        )}
        <label className="field">
          <span>Cliente</span>
          <select value={form.customer_id} onChange={(e) => { const selectedCustomer = (customersLoad.data || []).find((c) => c.id === Number(e.target.value)); setForm({ ...form, customer_id: e.target.value, product_id: "", delivery_address: selectedCustomer ? `${selectedCustomer.address}${selectedCustomer.reference_point ? ` - Referencia: ${selectedCustomer.reference_point}` : ""}` : "", manual_address: false }); }} required>
            <option value="">Selecione o cliente</option>
            {(customersLoad.data || [])
              .filter((c) => c.active && (!allowed(user, "sales.view_all") || !form.seller_id || c.owner_seller_id === Number(form.seller_id)))
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.legal_name} · {c.cnpj}
                </option>
              ))}
          </select>
        </label>
        {allowed(user, "customers.create") && <button type="button" onClick={() => setShowCustomer(!showCustomer)}>
          <UserPlus size={16} /> {showCustomer ? "Fechar cadastro" : "Cadastrar novo cliente"}
        </button>}
        <label className="field">
          <span>Tabela aplicada</span>
          <input value={priceTable?.name || "Selecione um cliente"} readOnly />
        </label>
        <label className="field">
          <span>Produto</span>
          <select value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} required disabled={!customer}>
            <option value="">Selecione</option>
            {products
              .filter((p) => p.active)
              .map((p) => {
                const price = priceTable?.items.find((i) => i.product_id === p.id)?.price;
                return (
                  <option key={p.id} value={p.id}>
                    {p.name} · {price == null ? "sem preco" : money(price)} · estoque {p.current_stock}
                  </option>
                );
              })}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={form.manual_address} onChange={(e) => setForm({ ...form, manual_address: e.target.checked, delivery_address: e.target.checked ? form.delivery_address : customerAddress })} /> Preencher endereco manualmente
        </label>
        <label className="field">
          <span>Endereco de entrega</span>
          <textarea value={form.delivery_address} onChange={(e) => setForm({ ...form, delivery_address: e.target.value })} readOnly={!form.manual_address} required />
        </label>
        <label className="field">
          <span>Quantidade</span>
          <input type="number" min="0.01" step="0.01" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })} required />
        </label>
        <div className="total">
          <small>Total da venda</small>
          <strong>{money(total)}</strong>
        </div>
        <label className="field">
          <span>Forma de pagamento</span>
          <select value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })}>
            <option value="dinheiro">Dinheiro</option>
            <option value="pix">Pix</option>
            <option value="cartao">Cartao</option>
            <option value="prazo">A prazo</option>
          </select>
        </label>
        {form.payment_method === "prazo" && (
          <>
            <label className="field">
              <span>Condicao de pagamento</span>
              <select value={form.payment_condition_id} onChange={(e) => setForm({ ...form, payment_condition_id: e.target.value, payment_due_date: e.target.value ? "" : form.payment_due_date })}>
                <option value="">Vencimento manual</option>
                {paymentConditions.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.installment_days.length} parcela(s)</option>)}
              </select>
            </label>
            {!form.payment_condition_id && <label className="field">
              <span>Data de vencimento</span>
              <input type="date" value={form.payment_due_date} onChange={(e) => setForm({ ...form, payment_due_date: e.target.value })} required />
            </label>}
          </>
        )}
        <button className="primary big">
          <ReceiptText size={18} /> {editingId ? "Salvar alteracoes" : "Confirmar Venda"}
        </button>
        {editingId && (
          <button type="button" onClick={cancelEdit}>
            Cancelar edicao
          </button>
        )}
        {message && <p className="form-status">{message}</p>}
      </form>
      {showCustomer && (
        <form className="panel form inline-customer" onSubmit={createCustomer}>
          <h2>Novo cliente</h2>
          <CustomerFields form={customerForm} setForm={setCustomerForm} tables={tables} sellers={sellers} showOwner={allowed(user, "customers.transfer")} compact />
          <button className="primary">
            <Save size={16} /> Cadastrar e selecionar
          </button>
        </form>
      )}
    </div>
  );
  const saleList = (sales || []).map((sale) => (
    <Row
      key={sale.id}
      title={`${sale.customer_name || "Cliente antigo"} · ${money(sale.total_value)}`}
      meta={`#${sale.id} · ${sale.seller_name} · ${sale.price_table_name || "preco anterior"} · ${new Date(sale.occurred_at).toLocaleString("pt-BR")} · ${sale.items.map((item) => `${item.quantity}x ${item.product_name}`).join(", ")} · ${sale.status}`}
      onEdit={allowed(user, "sales.edit") && sale.status === "confirmada" && sale.customer_id ? () => startEdit(sale) : null}
      actions={
        allowed(user, "sales.cancel") && sale.status === "confirmada" ? (
          <button className="danger" onClick={() => removeSale(sale)}>
            <Trash2 size={16} /> Excluir
          </button>
        ) : null
      }
    />
  ));
  return <CrudLayout form={formPanel} list={saleList} />;
}

const deliveryStatus = {
  preparacao: "Em preparacao",
  em_rota: "Em rota",
  concluido: "Concluido",
  cancelado: "Cancelado",
  pendente: "Pendente",
  entregue: "Entregue",
  nao_entregue: "Nao entregue",
};

function Deliveries({ api, token }) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    delivery_date: today,
    driver_name: "",
    vehicle: "",
    notes: "",
  });
  const [selected, setSelected] = useState({});
  const [message, setMessage] = useState("");
  const pendingLoad = useLoad(api, () => api.call("/delivery-manifests/pending-sales"), []);
  const manifestsLoad = useLoad(api, () => api.call("/delivery-manifests"), []);
  const pendingSales = pendingLoad.data || [];
  const manifests = manifestsLoad.data || [];

  function toggleSale(sale) {
    setSelected((current) => {
      const next = { ...current };
      if (next[sale.id]) delete next[sale.id];
      else
        next[sale.id] = {
          delivery_address: sale.delivery_address || "",
          delivery_order: Object.keys(current).length + 1,
        };
      return next;
    });
  }

  function updateAddress(saleId, delivery_address) {
    setSelected((current) => ({
      ...current,
      [saleId]: { ...current[saleId], delivery_address },
    }));
  }

  async function createManifest(e) {
    e.preventDefault();
    setMessage("");
    const items = Object.entries(selected).map(([saleId, item], index) => ({
      sale_id: Number(saleId),
      delivery_address: item.delivery_address.trim(),
      delivery_order: index + 1,
    }));
    if (!items.length) return setMessage("Selecione pelo menos uma venda.");
    if (items.some((item) => !item.delivery_address)) return setMessage("Informe o endereco de todas as entregas.");
    try {
      await api.call("/delivery-manifests", {
        method: "POST",
        body: JSON.stringify({ ...form, items }),
      });
      setForm({
        delivery_date: today,
        driver_name: "",
        vehicle: "",
        notes: "",
      });
      setSelected({});
      setMessage("Romaneio criado com sucesso.");
      pendingLoad.reload();
      manifestsLoad.reload();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function updateManifestStatus(manifestId, status) {
    try {
      await api.call(`/delivery-manifests/${manifestId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      setMessage("Romaneio atualizado.");
      pendingLoad.reload();
      manifestsLoad.reload();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function updateDelivery(manifestId, itemId, status) {
    try {
      await api.call(`/delivery-manifests/${manifestId}/items/${itemId}`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      setMessage(status === "entregue" ? "Entrega confirmada." : "Entrega marcada como nao realizada.");
      manifestsLoad.reload();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function printManifest(manifest) {
    setMessage("");
    const printWindow = window.open("", "_blank");
    try {
      const response = await fetch(`${API}/delivery-manifests/${manifest.id}/pdf`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error((await response.json()).detail || "Nao foi possivel gerar o PDF");
      const url = URL.createObjectURL(await response.blob());
      if (printWindow) printWindow.location.href = url;
      else setMessage("O navegador bloqueou a nova guia. Permita pop-ups para imprimir.");
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) {
      if (printWindow) printWindow.close();
      setMessage(error.message);
    }
  }

  return (
    <section className="delivery-page">
      <div className="delivery-create">
        <form className="panel form" onSubmit={createManifest}>
          <h2>Novo romaneio</h2>
          <label className="field">
            <span>Data da entrega</span>
            <input type="date" value={form.delivery_date} onChange={(e) => setForm({ ...form, delivery_date: e.target.value })} required />
          </label>
          <label className="field">
            <span>Motorista</span>
            <input value={form.driver_name} onChange={(e) => setForm({ ...form, driver_name: e.target.value })} placeholder="Nome do motorista" required />
          </label>
          <label className="field">
            <span>Veiculo</span>
            <input value={form.vehicle} onChange={(e) => setForm({ ...form, vehicle: e.target.value })} placeholder="Modelo ou placa" />
          </label>
          <label className="field">
            <span>Observacoes</span>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Rota, horario ou orientacoes" />
          </label>
          <button className="primary">
            <ClipboardList size={18} /> Criar romaneio
          </button>
          {message && <p className="form-status">{message}</p>}
        </form>
        <div className="panel pending-deliveries">
          <h2>Vendas aguardando entrega</h2>
          {!pendingSales.length && <p className="empty-state">Nenhuma venda pendente.</p>}
          {pendingSales.map((sale) => (
            <div className={`delivery-choice ${selected[sale.id] ? "selected" : ""}`} key={sale.id}>
              <label className="delivery-check">
                <input type="checkbox" checked={Boolean(selected[sale.id])} onChange={() => toggleSale(sale)} />
                <span>
                  <b>{sale.customer_name || `Venda #${sale.id}`}</b>
                  <small>
                    {sale.items.map((item) => `${item.quantity}x ${item.product_name}`).join(", ")} · {money(sale.total_value)}
                  </small>
                </span>
              </label>
              {selected[sale.id] && (
                <label className="field address-field">
                  <span>
                    <MapPin size={14} /> Endereco de entrega
                  </span>
                  <input value={selected[sale.id].delivery_address} onChange={(e) => updateAddress(sale.id, e.target.value)} placeholder="Rua, numero, bairro e referencia" />
                </label>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="manifest-section">
        <div className="section-title">
          <div>
            <h2>Romaneios</h2>
            <p>Acompanhe a separacao, rota e confirmacao das entregas.</p>
          </div>
          <button
            onClick={() => {
              pendingLoad.reload();
              manifestsLoad.reload();
            }}
          >
            Atualizar
          </button>
        </div>
        {!manifests.length && <div className="panel empty-state">Nenhum romaneio criado.</div>}
        {manifests.map((manifest) => (
          <article className="panel manifest" key={manifest.id}>
            <div className="manifest-header">
              <div>
                <span className={`status status-${manifest.status}`}>{deliveryStatus[manifest.status]}</span>
                <h2>{manifest.code}</h2>
                <p>
                  {new Date(`${manifest.delivery_date}T12:00:00`).toLocaleDateString("pt-BR")} · {manifest.driver_name}
                  {manifest.vehicle ? ` · ${manifest.vehicle}` : ""}
                </p>
              </div>
              <div className="manifest-actions">
                <button onClick={() => printManifest(manifest)}>
                  <Printer size={16} /> Imprimir PDF
                </button>
                {manifest.status === "preparacao" && (
                  <button onClick={() => updateManifestStatus(manifest.id, "em_rota")}>
                    <Play size={16} /> Iniciar rota
                  </button>
                )}
                {manifest.status !== "cancelado" && manifest.status !== "concluido" && (
                  <button className="danger" onClick={() => updateManifestStatus(manifest.id, "cancelado")}>
                    <Ban size={16} /> Cancelar
                  </button>
                )}
              </div>
            </div>
            {manifest.notes && <p className="manifest-notes">{manifest.notes}</p>}
            <div className="delivery-items">
              {manifest.items.map((item) => (
                <div className="delivery-item" key={item.id}>
                  <div className="delivery-order">{item.delivery_order}</div>
                  <div className="delivery-info">
                    <b>{item.sale.customer_name || `Venda #${item.sale_id}`}</b>
                    <span>
                      <MapPin size={14} /> {item.delivery_address}
                    </span>
                    <small>
                      {item.sale.items.map((saleItem) => `${saleItem.quantity}x ${saleItem.product_name}`).join(", ")} · {money(item.sale.total_value)}
                    </small>
                  </div>
                  <div className="delivery-result">
                    <span className={`status status-${item.status}`}>{deliveryStatus[item.status]}</span>
                    {manifest.status !== "cancelado" && item.status !== "entregue" && (
                      <div>
                        <button className="success" onClick={() => updateDelivery(manifest.id, item.id, "entregue")} title="Confirmar entrega">
                          <CheckCircle2 size={16} /> Entregue
                        </button>
                        <button onClick={() => updateDelivery(manifest.id, item.id, "nao_entregue")} title="Marcar como nao entregue">
                          Nao entregue
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function NewAccessUser({ api }) {
  const roles = useLoad(api, () => api.call("/access/roles"), []).data || [];
  const [form, setForm] = useState({ name: "", email: "", password: "", role_ids: [] });
  const [message, setMessage] = useState("");
  async function save(e) { e.preventDefault(); try { await api.call("/access/users", { method: "POST", body: JSON.stringify(form) }); setForm({ name: "", email: "", password: "", role_ids: [] }); setMessage("Usuario criado com sucesso."); } catch (error) { setMessage(error.message); } }
  return <form className="panel form access-user-create" onSubmit={save}><h2>Novo usuario</h2><div className="user-create-grid"><label className="field"><span>Nome</span><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label><label className="field"><span>E-mail</span><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></label><label className="field"><span>Senha inicial</span><input type="password" minLength={6} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></label></div><div className="role-selector">{roles.filter((item) => item.active).map((item) => <label className="check" key={item.id}><input type="checkbox" checked={form.role_ids.includes(item.id)} onChange={() => setForm({ ...form, role_ids: form.role_ids.includes(item.id) ? form.role_ids.filter((id) => id !== item.id) : [...form.role_ids, item.id] })} /> {item.name}</label>)}</div><button className="primary" disabled={!form.role_ids.length}><UserPlus size={16} /> Criar usuario</button>{message && <p className="form-status">{message}</p>}</form>;
}

function AccessControl({ api }) {
  const rolesLoad = useLoad(api, () => api.call("/access/roles"), []);
  const permissionsLoad = useLoad(api, () => api.call("/access/permissions"), []);
  const usersLoad = useLoad(api, () => api.call("/access/users"), []);
  const [role, setRole] = useState({ name: "", description: "", active: true, permission_codes: [] });
  const [selectedUserId, setSelectedUserId] = useState("");
  const [userAccess, setUserAccess] = useState({ role_ids: [], overrides: {} });
  const [message, setMessage] = useState("");
  const permissions = permissionsLoad.data || [];
  const grouped = permissions.reduce((result, permission) => ({ ...result, [permission.module]: [...(result[permission.module] || []), permission] }), {});
  function editRole(row) { setRole({ id: row.id, name: row.name, description: row.description || "", active: row.active, permission_codes: row.permission_codes }); }
  function togglePermission(code) { setRole((current) => ({ ...current, permission_codes: current.permission_codes.includes(code) ? current.permission_codes.filter((item) => item !== code) : [...current.permission_codes, code] })); }
  async function saveRole(e) { e.preventDefault(); setMessage(""); try { await api.call(role.id ? `/access/roles/${role.id}` : "/access/roles", { method: role.id ? "PUT" : "POST", body: JSON.stringify(role) }); setRole({ name: "", description: "", active: true, permission_codes: [] }); rolesLoad.reload(); setMessage("Perfil salvo."); } catch (error) { setMessage(error.message); } }
  function selectUser(id) { const row = (usersLoad.data || []).find((item) => item.id === Number(id)); setSelectedUserId(id); setUserAccess(row ? { role_ids: row.role_ids, overrides: row.overrides || {} } : { role_ids: [], overrides: {} }); }
  async function saveUserAccess(e) { e.preventDefault(); try { await api.call(`/access/users/${selectedUserId}`, { method: "PUT", body: JSON.stringify(userAccess) }); usersLoad.reload(); setMessage("Acesso do usuario atualizado."); } catch (error) { setMessage(error.message); } }
  return <section className="access-page">
    {message && <p className="panel form-status">{message}</p>}
    <div className="access-columns">
      <form className="panel form" onSubmit={saveRole}><h2>{role.id ? "Editar perfil" : "Novo perfil"}</h2><label className="field"><span>Nome</span><input value={role.name} onChange={(e) => setRole({ ...role, name: e.target.value })} required /></label><label className="field"><span>Descricao</span><textarea value={role.description} onChange={(e) => setRole({ ...role, description: e.target.value })} /></label><label className="check"><input type="checkbox" checked={role.active} onChange={(e) => setRole({ ...role, active: e.target.checked })} /> Perfil ativo</label><div className="permission-groups">{Object.entries(grouped).map(([module, items]) => <fieldset key={module}><legend>{module}</legend>{items.map((permission) => <label className="check" key={permission.code}><input type="checkbox" checked={role.permission_codes.includes(permission.code)} onChange={() => togglePermission(permission.code)} /> {permission.name}</label>)}</fieldset>)}</div><button className="primary"><Save size={16} /> Salvar perfil</button></form>
      <div className="panel"><h2>Perfis cadastrados</h2>{(rolesLoad.data || []).map((row) => <Row key={row.id} title={row.name} meta={`${row.permission_codes.length} permissoes · ${row.active ? "ativo" : "inativo"}`} onEdit={() => editRole(row)} />)}</div>
    </div>
    <form className="panel form" onSubmit={saveUserAccess}><h2>Perfis e permissoes individuais do usuario</h2><label className="field"><span>Usuario</span><select value={selectedUserId} onChange={(e) => selectUser(e.target.value)} required><option value="">Selecione</option>{(usersLoad.data || []).map((row) => <option key={row.id} value={row.id}>{row.name} · {row.email}</option>)}</select></label>{selectedUserId && <><div className="role-selector">{(rolesLoad.data || []).filter((item) => item.active).map((item) => <label className="check" key={item.id}><input type="checkbox" checked={userAccess.role_ids.includes(item.id)} onChange={() => setUserAccess({ ...userAccess, role_ids: userAccess.role_ids.includes(item.id) ? userAccess.role_ids.filter((id) => id !== item.id) : [...userAccess.role_ids, item.id] })} /> {item.name}</label>)}</div><label className="field"><span>Excecao individual</span><select onChange={(e) => { const [code, value] = e.target.value.split("|"); if (code) setUserAccess({ ...userAccess, overrides: { ...userAccess.overrides, [code]: value === "allow" } }); }} defaultValue=""><option value="">Adicionar permissao ou bloqueio</option>{permissions.flatMap((permission) => [<option key={`${permission.code}-allow`} value={`${permission.code}|allow`}>Permitir: {permission.name}</option>, <option key={`${permission.code}-deny`} value={`${permission.code}|deny`}>Bloquear: {permission.name}</option>])}</select></label><div className="override-list">{Object.entries(userAccess.overrides).map(([code, allowed]) => <button type="button" key={code} onClick={() => { const next = { ...userAccess.overrides }; delete next[code]; setUserAccess({ ...userAccess, overrides: next }); }}>{allowed ? "Permitido" : "Bloqueado"}: {code} ×</button>)}</div><button className="primary"><Save size={16} /> Salvar acesso do usuario</button></>}</form>
  </section>;
}

function Finance({ api, user }) {
  const today = new Date().toISOString().slice(0, 10);
  const dashboard = useLoad(api, () => api.call("/finance/dashboard"), []);
  const receivables = useLoad(api, () => api.call("/finance/receivables"), []);
  const payables = useLoad(api, () => api.call("/finance/payables"), []);
  const accounts = useLoad(api, () => api.call("/finance/accounts"), []);
  const suppliers = useLoad(api, () => api.call("/finance/suppliers"), []);
  const centers = useLoad(api, () => api.call("/finance/cost-centers"), []);
  const cashFlow = useLoad(api, () => api.call("/finance/cash-flow"), []);
  const conditions = useLoad(api, () => api.call("/finance/payment-conditions"), []);
  const [message, setMessage] = useState("");
  const [payable, setPayable] = useState({ supplier_id: "", cost_center_id: "", category: "despesa", description: "", competence_date: today, due_date: today, original_amount: 0, notes: "" });
  const [supplier, setSupplier] = useState({ name: "", document: "", phone: "", email: "" });
  const [condition, setCondition] = useState({ name: "", installment_days: "30", interest_percent_month: 0, fine_percent: 0 });
  const refresh = () => { dashboard.reload(); receivables.reload(); payables.reload(); accounts.reload(); cashFlow.reload(); };
  async function addPayable(e) {
    e.preventDefault(); setMessage("");
    try { await api.call("/finance/payables", { method: "POST", body: JSON.stringify({ ...payable, supplier_id: payable.supplier_id ? Number(payable.supplier_id) : null, cost_center_id: Number(payable.cost_center_id), original_amount: Number(payable.original_amount) }) }); setPayable({ supplier_id: "", cost_center_id: "", category: "despesa", description: "", competence_date: today, due_date: today, original_amount: 0, notes: "" }); setMessage("Conta a pagar cadastrada."); refresh(); } catch (error) { setMessage(error.message); }
  }
  async function addSupplier(e) {
    e.preventDefault(); setMessage("");
    try { await api.call("/finance/suppliers", { method: "POST", body: JSON.stringify(supplier) }); setSupplier({ name: "", document: "", phone: "", email: "" }); suppliers.reload(); setMessage("Fornecedor cadastrado."); } catch (error) { setMessage(error.message); }
  }
  async function settle(kind, row) {
    const defaultAccount = (accounts.data || []).find((account) => account.active);
    if (!defaultAccount) return setMessage("Cadastre uma conta financeira ativa.");
    const amountText = window.prompt(`Valor da baixa para ${row.description || row.customer_name}`, String(row.balance));
    if (!amountText) return;
    const amount = Number(amountText.replace(",", "."));
    if (!amount || amount <= 0) return setMessage("Informe um valor valido.");
    try { await api.call(`/finance/${kind}/${row.id}/payments`, { method: "POST", body: JSON.stringify({ account_id: defaultAccount.id, amount, payment_method: "pix" }) }); setMessage("Baixa registrada com sucesso."); refresh(); } catch (error) { setMessage(error.message); }
  }
  async function addCondition(e) {
    e.preventDefault();
    const days = condition.installment_days.split(",").map((value) => Number(value.trim())).filter((value) => Number.isFinite(value));
    try { await api.call("/finance/payment-conditions", { method: "POST", body: JSON.stringify({ ...condition, installment_days: days, interest_percent_month: Number(condition.interest_percent_month), fine_percent: Number(condition.fine_percent) }) }); setCondition({ name: "", installment_days: "30", interest_percent_month: 0, fine_percent: 0 }); conditions.reload(); setMessage("Condicao de pagamento cadastrada."); } catch (error) { setMessage(error.message); }
  }
  async function adjust(row) {
    const interest = window.prompt("Juros acumulados (R$)", String(row.interest_amount || 0)); if (interest == null) return;
    const fine = window.prompt("Multa (R$)", String(row.fine_amount || 0)); if (fine == null) return;
    const discount = window.prompt("Desconto (R$)", String(row.discount_amount || 0)); if (discount == null) return;
    const reason = window.prompt("Motivo do ajuste"); if (!reason) return;
    try { await api.call(`/finance/receivables/${row.id}/adjustments`, { method: "POST", body: JSON.stringify({ interest_amount: Number(interest.replace(",", ".")), fine_amount: Number(fine.replace(",", ".")), discount_amount: Number(discount.replace(",", ".")), reason }) }); setMessage("Titulo ajustado."); refresh(); } catch (error) { setMessage(error.message); }
  }
  async function collect(row) {
    const notes = window.prompt(`Registro de cobranca para ${row.customer_name}`); if (!notes) return;
    try { await api.call(`/finance/receivables/${row.id}/collections`, { method: "POST", body: JSON.stringify({ contact_type: "telefone", notes, next_contact_date: null }) }); setMessage("Cobranca registrada no historico."); } catch (error) { setMessage(error.message); }
  }
  async function reverseLast(kind, row) {
    try {
      const payments = await api.call(`/finance/${kind}/${row.id}/payments`);
      const payment = payments.find((item) => !item.reversed);
      if (!payment) return setMessage("Nao existe baixa ativa para estornar.");
      const reason = window.prompt(`Motivo do estorno de ${money(payment.amount)}`); if (!reason) return;
      const path = kind === "receivables" ? "receivable-payments" : "payable-payments";
      await api.call(`/finance/${path}/${payment.id}/reverse`, { method: "POST", body: JSON.stringify({ reason }) }); setMessage("Baixa estornada e fluxo de caixa recalculado."); refresh();
    } catch (error) { setMessage(error.message); }
  }
  async function configureCredit(row) {
    try {
      const current = await api.call(`/finance/customers/${row.customer_id}/credit`);
      const limit = window.prompt(`Limite de credito de ${row.customer_name}`, String(current.credit_limit)); if (limit == null) return;
      const term = window.prompt("Prazo maximo em dias", String(current.max_term_days)); if (term == null) return;
      await api.call(`/finance/customers/${row.customer_id}/credit`, { method: "PUT", body: JSON.stringify({ credit_limit: Number(limit.replace(",", ".")), max_term_days: Number(term), block_overdue: current.block_overdue, tolerance_days: current.tolerance_days }) }); setMessage("Regra de credito atualizada.");
    } catch (error) { setMessage(error.message); }
  }
  if (!dashboard.data) return <Loading />;
  return <section className="finance-page">
    <div className="grid finance-metrics">
      <Metric label="Saldo em contas" value={money(dashboard.data.cash_balance)} />
      <Metric label="Total a receber" value={money(dashboard.data.receivable_open)} />
      <Metric label="Total a pagar" value={money(dashboard.data.payable_open)} />
      <Metric label="Recebimentos hoje" value={money(dashboard.data.received_today)} />
      <Metric label="Pagamentos hoje" value={money(dashboard.data.paid_today)} />
      <Metric label="Clientes inadimplentes" value={dashboard.data.overdue_customers} />
    </div>
    {message && <p className="panel form-status">{message}</p>}
    <div className="finance-columns">
      <Panel title="Contas a receber">{(receivables.data || []).map((row) => <Row key={row.id} title={`${row.customer_name} · ${money(row.balance)}`} meta={`Venda #${row.sale_id} · ${row.installments.length} parcela(s): ${row.installments.map((item) => `${item.number}/${new Date(`${item.due_date}T12:00:00`).toLocaleDateString("pt-BR")} ${item.status}`).join("; ")} · ${row.status} · ${row.seller_name}`} actions={<>{row.balance > 0 && row.status !== "cancelado" && <button onClick={() => settle("receivables", row)}>Receber</button>}{allowed(user, "finance.edit_receivables") && <button onClick={() => adjust(row)}>Ajustar</button>}{allowed(user, "finance.edit_receivables") && <button onClick={() => collect(row)}>Cobranca</button>}{allowed(user, "customers.change_credit_limit") && <button onClick={() => configureCredit(row)}>Credito</button>}{allowed(user, "finance.reverse_payments") && row.paid_amount > 0 && <button onClick={() => reverseLast("receivables", row)}>Estornar</button>}</>} />)}</Panel>
      <Panel title="Contas a pagar">{(payables.data || []).map((row) => <Row key={row.id} title={`${row.description} · ${money(row.balance)}`} meta={`${row.supplier_name || "Sem fornecedor"} · ${row.cost_center_name} · ${new Date(`${row.due_date}T12:00:00`).toLocaleDateString("pt-BR")} · ${row.status}`} actions={<>{row.balance > 0 && row.status !== "cancelado" && <button onClick={() => settle("payables", row)}>Pagar</button>}{allowed(user, "finance.reverse_payments") && row.paid_amount > 0 && <button onClick={() => reverseLast("payables", row)}>Estornar</button>}</>} />)}</Panel>
    </div>
    <div className="finance-columns">
      <form className="panel form" onSubmit={addPayable}><h2>Nova conta a pagar</h2><label className="field"><span>Descricao</span><input value={payable.description} onChange={(e) => setPayable({ ...payable, description: e.target.value })} required /></label><label className="field"><span>Fornecedor</span><select value={payable.supplier_id} onChange={(e) => setPayable({ ...payable, supplier_id: e.target.value })}><option value="">Sem fornecedor</option>{(suppliers.data || []).map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label><label className="field"><span>Centro de custo</span><select value={payable.cost_center_id} onChange={(e) => setPayable({ ...payable, cost_center_id: e.target.value })} required><option value="">Selecione</option>{(centers.data || []).map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label><label className="field"><span>Categoria</span><input value={payable.category} onChange={(e) => setPayable({ ...payable, category: e.target.value })} required /></label><label className="field"><span>Competencia</span><input type="date" value={payable.competence_date} onChange={(e) => setPayable({ ...payable, competence_date: e.target.value })} required /></label><label className="field"><span>Vencimento</span><input type="date" value={payable.due_date} onChange={(e) => setPayable({ ...payable, due_date: e.target.value })} required /></label><label className="field"><span>Valor</span><input type="number" min="0.01" step="0.01" value={payable.original_amount} onChange={(e) => setPayable({ ...payable, original_amount: e.target.value })} required /></label><button className="primary"><Save size={16} /> Salvar despesa</button></form>
      <form className="panel form" onSubmit={addSupplier}><h2>Novo fornecedor</h2><label className="field"><span>Nome / Razao social</span><input value={supplier.name} onChange={(e) => setSupplier({ ...supplier, name: e.target.value })} required /></label><label className="field"><span>CNPJ ou CPF</span><input value={supplier.document} onChange={(e) => setSupplier({ ...supplier, document: e.target.value })} /></label><label className="field"><span>Telefone</span><input value={supplier.phone} onChange={(e) => setSupplier({ ...supplier, phone: e.target.value })} /></label><label className="field"><span>E-mail</span><input type="email" value={supplier.email} onChange={(e) => setSupplier({ ...supplier, email: e.target.value })} /></label><button className="primary"><Save size={16} /> Salvar fornecedor</button><h2 className="finance-subtitle">Contas e saldos</h2>{(accounts.data || []).map((row) => <Row key={row.id} title={row.name} meta={`${row.account_type} · ${money(row.balance)}`} />)}</form>
    </div>
    {allowed(user, "settings.financial") && <form className="panel form max" onSubmit={addCondition}><h2>Condicoes de pagamento</h2><label className="field"><span>Nome</span><input value={condition.name} onChange={(e) => setCondition({ ...condition, name: e.target.value })} placeholder="Ex.: 30 / 60 / 90 dias" required /></label><label className="field"><span>Dias das parcelas (separados por virgula)</span><input value={condition.installment_days} onChange={(e) => setCondition({ ...condition, installment_days: e.target.value })} placeholder="30, 60, 90" required /></label><label className="field"><span>Juros ao mes (%)</span><input type="number" min="0" step="0.01" value={condition.interest_percent_month} onChange={(e) => setCondition({ ...condition, interest_percent_month: e.target.value })} /></label><label className="field"><span>Multa (%)</span><input type="number" min="0" step="0.01" value={condition.fine_percent} onChange={(e) => setCondition({ ...condition, fine_percent: e.target.value })} /></label><button className="primary"><Save size={16} /> Salvar condicao</button><div>{(conditions.data || []).map((item) => <Row key={item.id} title={item.name} meta={`${item.installment_days.join(" / ")} dias · juros ${item.interest_percent_month}% · multa ${item.fine_percent}%`} />)}</div></form>}
    <Panel title="Fluxo de caixa">{(cashFlow.data || []).map((row) => <Row key={row.id} title={`${row.direction === "entrada" ? "+" : "-"} ${money(row.amount)} · ${row.account_name}`} meta={`${new Date(row.occurred_at).toLocaleString("pt-BR")} · ${row.description}`} />)}</Panel>
  </section>;
}

function WhatsApp({ api }) {
  const { data, setData } = useLoad(api, () => api.call("/whatsapp/settings"), []);
  const [testStatus, setTestStatus] = useState("");
  if (!data) return <Loading />;
  const isTelegram = data.provider === "telegram";
  async function save(e) {
    e.preventDefault();
    const saved = await api.call("/whatsapp/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    });
    setData(saved);
    setTestStatus("Configuracoes salvas.");
  }
  async function testConnection() {
    setTestStatus("Enviando mensagem de teste...");
    try {
      await api.call("/whatsapp/test", { method: "POST" });
      setTestStatus("Mensagem de teste enviada.");
    } catch (error) {
      setTestStatus(`Falha no teste: ${error.message}`);
    }
  }
  return (
    <form className="panel form max" onSubmit={save}>
      <h2>Configuracoes de Alertas</h2>
      <label className="field">
        <span>Provedor</span>
        <select value={data.provider} onChange={(e) => setData({ ...data, provider: e.target.value })}>
          <option value="mock">Mock</option>
          <option value="telegram">Telegram Bot</option>
          <option value="meta">Meta Cloud API</option>
          <option value="zapi">Z-API</option>
          <option value="twilio">Twilio</option>
        </select>
      </label>
      {!isTelegram && (
        <label className="field">
          <span>URL da API</span>
          <input placeholder="https://graph.facebook.com/VERSAO/PHONE_NUMBER_ID/messages" value={data.api_url || ""} onChange={(e) => setData({ ...data, api_url: e.target.value })} />
        </label>
      )}
      <label className="field">
        <span>{isTelegram ? "Token do bot" : "Token de acesso"}</span>
        <input type="password" placeholder={isTelegram ? "Token fornecido pelo BotFather" : "Token gerado pelo provedor"} value={data.token || ""} onChange={(e) => setData({ ...data, token: e.target.value })} />
      </label>
      <label className="field">
        <span>{isTelegram ? "Chat ID do gestor ou grupo" : "WhatsApp do gestor"}</span>
        <input placeholder={isTelegram ? "Ex.: 123456789 ou -1001234567890" : "Ex.: +5563999999999"} value={data.manager_phone} onChange={(e) => setData({ ...data, manager_phone: e.target.value })} />
      </label>
      <label className="check">
        <input type="checkbox" checked={data.sale_notifications} onChange={(e) => setData({ ...data, sale_notifications: e.target.checked })} /> notificacao por venda
      </label>
      <label className="check">
        <input type="checkbox" checked={data.low_stock_alerts} onChange={(e) => setData({ ...data, low_stock_alerts: e.target.checked })} /> alerta de estoque baixo
      </label>
      <label className="check">
        <input type="checkbox" checked={data.daily_summary} onChange={(e) => setData({ ...data, daily_summary: e.target.checked })} /> resumo diario
      </label>
      <label className="field">
        <span>Horario do resumo diario</span>
        <input type="time" value={data.daily_summary_time?.slice(0, 5)} onChange={(e) => setData({ ...data, daily_summary_time: e.target.value })} />
      </label>
      <button className="primary">Salvar Configuracoes</button>
      <button type="button" onClick={testConnection}>
        Enviar alerta de teste
      </button>
      {testStatus && <p className="form-status">{testStatus}</p>}
    </form>
  );
}

function CrudLayout({ form, list }) {
  return (
    <section className="crud">
      {form}
      <div className="panel list">
        <h2>Registros</h2>
        {list}
      </div>
    </section>
  );
}

function Row({ title, meta, onEdit, actions }) {
  return (
    <div className="row">
      <div>
        <strong>{title}</strong>
        <span>{meta}</span>
      </div>
      <div className="row-actions">
        {onEdit && <button onClick={onEdit}>Editar</button>}
        {actions}
      </div>
    </div>
  );
}

function Loading() {
  return <div className="panel">Carregando...</div>;
}

createRoot(document.getElementById("root")).render(<App />);
