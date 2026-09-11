import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  Ban,
  Boxes,
  CheckCircle2,
  ClipboardList,
  Trash2,
  Download,
  LogOut,
  MessageCircle,
  MapPin,
  PackagePlus,
  Play,
  ReceiptText,
  Save,
  ShoppingCart,
  Truck,
  Users,
} from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "https://carvao-sales-system-production.up.railway.app/api";
const money = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [user, setUser] = useState(JSON.parse(localStorage.getItem("user") || "null"));
  const [tab, setTab] = useState("dashboard");

  const api = useMemo(() => ({
    async call(path, options = {}) {
      const res = await fetch(`${API}${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(options.headers || {}),
        },
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Erro na requisicao");
      return res.json();
    },
  }), [token]);

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

  const tabs = [
    ["dashboard", "Dashboard", BarChart3, ["admin", "gerente", "vendedor"]],
    ["sale", "Venda", ShoppingCart, ["admin", "gerente", "vendedor"]],
    ["products", "Produtos", Boxes, ["admin", "gerente"]],
    ["stock", "Estoque", PackagePlus, ["admin", "gerente"]],
    ["deliveries", "Romaneios", ClipboardList, ["admin", "gerente"]],
    ["sellers", "Vendedores", Users, ["admin"]],
    ["whatsapp", "WhatsApp", MessageCircle, ["admin"]],
  ].filter((item) => item[3].includes(user.role));

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="mark">C</span>
          <div><strong>Carvao Pro</strong><small>vendas e estoque</small></div>
        </div>
        <nav>
          {tabs.map(([id, label, Icon]) => (
            <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)} title={label}>
              <Icon size={18} /> <span>{label}</span>
            </button>
          ))}
        </nav>
        <button className="logout" onClick={logout}><LogOut size={18} /> Sair</button>
      </aside>
      <main>
        <header>
          <div>
            <h1>{tabs.find((x) => x[0] === tab)?.[1]}</h1>
            <p>{user.name} · {user.role}</p>
          </div>
        </header>
        {tab === "dashboard" && <Dashboard api={api} token={token} user={user} />}
        {tab === "sale" && <Sales api={api} user={user} />}
        {tab === "products" && <Products api={api} />}
        {tab === "stock" && <Stock api={api} />}
        {tab === "deliveries" && <Deliveries api={api} />}
        {tab === "sellers" && <Sellers api={api} />}
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
        <label>E-mail<input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>Senha<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
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
  const reload = () => loader().then(setData).catch((e) => setError(e.message));
  useEffect(() => {
    reload();
  }, deps);
  return { data, setData, error, reload };
}

function Dashboard({ api, token }) {
  const today = new Date().toISOString().slice(0, 10);
  const [filters, setFilters] = useState({ start: today, end: today, seller_id: "" });
  const { data, reload } = useLoad(api, () => api.call(`/dashboard?start=${filters.start}&end=${filters.end}${filters.seller_id ? `&seller_id=${filters.seller_id}` : ""}`), [filters]);
  const sellers = useLoad(api, () => api.call("/sellers"), []).data || [];
  if (!data) return <Loading />;
  const coal = data.stock.filter((p) => p.type === "saco_fechado");
  const packs = data.stock.filter((p) => p.type === "embalagem_vazia");
  const exportFile = async (kind) => {
    const res = await fetch(`${API}/reports/export.${kind}`, { headers: { Authorization: `Bearer ${token}` } });
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
          {sellers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <button onClick={reload}>Atualizar</button>
        <button onClick={() => exportFile("xlsx")}><Download size={16} /> Excel</button>
        <button onClick={() => exportFile("pdf")}><Download size={16} /> PDF</button>
      </div>
      <Metric label="Vendido no periodo" value={money(data.total_value)} />
      <Metric label="Vendas confirmadas" value={data.sales_count} />
      <Metric label="Itens vendidos" value={data.items_quantity} />
      <Panel title="Sacos fechados">{coal.map((p) => <StockLine key={p.id} p={p} />)}</Panel>
      <Panel title="Embalagens vazias">{packs.map((p) => <StockLine key={p.id} p={p} />)}</Panel>
      <Panel title="Ranking de vendedores" className="wide">
        {data.ranking.map((r, i) => (
          <div className="rank" key={r.seller_id}><b>#{i + 1} {r.seller_name}</b><span>{Number(r.quantity).toLocaleString("pt-BR")} itens · {money(r.value)} · comissao {money(r.commission)}</span></div>
        ))}
      </Panel>
    </section>
  );
}

function Metric({ label, value }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function StockLine({ p }) {
  return <div className={p.low ? "stock low" : "stock"}><span>{p.name}</span><b>{p.current_stock} {p.unit}</b></div>;
}

function Panel({ title, children, className = "" }) {
  return <div className={`panel ${className}`}><h2>{title}</h2>{children}</div>;
}

function Products({ api }) {
  const empty = { name: "", type: "saco_fechado", unit: "saco", cost_price: 0, sale_price: 0, current_stock: 0, minimum_stock: 0, active: true };
  const [form, setForm] = useState(empty);
  const { data: products, reload } = useLoad(api, () => api.call("/products"), []);
  async function save(e) {
    e.preventDefault();
    await api.call(form.id ? `/products/${form.id}` : "/products", { method: form.id ? "PUT" : "POST", body: JSON.stringify(form) });
    setForm(empty);
    reload();
  }
  return (
    <CrudLayout form={<ProductForm form={form} setForm={setForm} save={save} />} list={(products || []).map((p) => (
      <Row key={p.id} title={p.name} meta={`${p.type} · estoque ${p.current_stock} · venda ${money(p.sale_price)}`} onEdit={() => setForm(p)} />
    ))} />
  );
}

function ProductForm({ form, setForm, save }) {
  return <form className="panel form" onSubmit={save}>
    <h2>Cadastro de Produto</h2>
    <label className="field"><span>Nome do produto</span><input placeholder="Ex.: Carvao Premium 5 kg" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
    <label className="field"><span>Tipo do produto</span><select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}><option value="saco_fechado">Saco fechado de carvao</option><option value="embalagem_vazia">Embalagem vazia</option><option value="outro">Outro</option></select></label>
    <label className="field"><span>Unidade de contagem</span><input placeholder="Ex.: saco, unidade ou kg" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} /></label>
    <label className="field"><span>Preco de custo (R$)</span><input type="number" min="0" step="0.01" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: Number(e.target.value) })} /></label>
    <label className="field"><span>Preco de venda (R$)</span><input type="number" min="0" step="0.01" value={form.sale_price} onChange={(e) => setForm({ ...form, sale_price: Number(e.target.value) })} /></label>
    <label className="field"><span>Quantidade inicial no estoque</span><input type="number" min="0" step="0.01" value={form.current_stock} onChange={(e) => setForm({ ...form, current_stock: Number(e.target.value) })} /></label>
    <label className="field"><span>Quantidade minima para alerta</span><input type="number" min="0" step="0.01" value={form.minimum_stock} onChange={(e) => setForm({ ...form, minimum_stock: Number(e.target.value) })} /></label>
    <button className="primary"><Save size={16} /> Salvar Produto</button>
  </form>;
}

function Stock({ api }) {
  const [form, setForm] = useState({ product_id: "", movement_type: "entrada", quantity: 1, note: "" });
  const productsLoad = useLoad(api, () => api.call("/products"), []);
  const products = productsLoad.data || [];
  const { data: movements, reload } = useLoad(api, () => api.call("/stock/movements"), []);
  async function save(e) {
    e.preventDefault();
    await api.call("/stock/movements", { method: "POST", body: JSON.stringify({ ...form, product_id: Number(form.product_id) }) });
    productsLoad.reload();
    reload();
  }
  return <section className="stock-page"><CrudLayout form={<form className="panel form" onSubmit={save}><h2>Entrada/Saida de Estoque</h2><select value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} required><option value="">Produto</option>{products.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.current_stock} {p.unit}</option>)}</select><select value={form.movement_type} onChange={(e) => setForm({ ...form, movement_type: e.target.value })}><option value="entrada">Entrada</option><option value="saida">Saida</option><option value="ajuste">Ajuste positivo</option><option value="devolucao">Devolucao</option></select><input type="number" step="0.01" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })} /><textarea placeholder="Observacao" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /><button className="primary">Registrar Movimentacao</button></form>} list={(movements || []).map((m) => <Row key={m.id} title={`${m.product_name} · ${m.movement_type}`} meta={`${m.quantity} em ${new Date(m.occurred_at).toLocaleString("pt-BR")} · ${m.note || ""}`} />)} /><Panel title="Quantidade atual dos produtos" className="full">{products.map((p) => <StockLine key={p.id} p={p} />)}</Panel></section>;
}

function Sellers({ api }) {
  const empty = { name: "", phone: "+55", monthly_goal: 0, commission_percent: 0, email: "", temporary_password: "vendedor123" };
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
    await api.call(`/sellers/${seller.id}`, { method: "PUT", body: JSON.stringify({ active: false }) });
    reload();
  }
  return <CrudLayout form={<form className="panel form" onSubmit={save}><h2>Cadastro de Vendedor</h2><label className="field"><span>Nome do vendedor</span><input placeholder="Ex.: Maria Silva" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label><label className="field"><span>Telefone / WhatsApp</span><input placeholder="Ex.: +5563999999999" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required /></label><label className="field"><span>E-mail de acesso</span><input type="email" placeholder="Ex.: maria@empresa.com" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></label><label className="field"><span>Senha inicial</span><input type="text" placeholder="Minimo de 6 caracteres" value={form.temporary_password} onChange={(e) => setForm({ ...form, temporary_password: e.target.value })} minLength={6} required /></label><label className="field"><span>Meta mensal de vendas (R$)</span><input type="number" min="0" step="0.01" value={form.monthly_goal} onChange={(e) => setForm({ ...form, monthly_goal: Number(e.target.value) })} /></label><label className="field"><span>Comissao sobre vendas (%)</span><input type="number" min="0" max="100" step="0.01" value={form.commission_percent} onChange={(e) => setForm({ ...form, commission_percent: Number(e.target.value) })} /></label><button className="primary"><Save size={16} /> Salvar Vendedor</button></form>} list={(sellers || []).map((s) => <Row key={s.id} title={s.name} meta={`${s.phone} · ${s.email} · ${s.active ? "ativo" : "inativo"}`} actions={<button className="danger" onClick={() => removeSeller(s)}><Trash2 size={16} /> Excluir</button>} />)} />;
}

function Sales({ api, user }) {
  const [form, setForm] = useState({ seller_id: "", product_id: "", quantity: 1, payment_method: "pix", customer_name: "", customer_phone: "" });
  const products = useLoad(api, () => api.call("/products"), []).data || [];
  const sellers = useLoad(api, () => api.call("/sellers"), []).data || [];
  const { data: sales, reload } = useLoad(api, () => api.call("/sales"), []);
  const product = products.find((p) => p.id === Number(form.product_id));
  const total = product ? product.sale_price * form.quantity : 0;
  async function save(e) {
    e.preventDefault();
    await api.call("/sales", { method: "POST", body: JSON.stringify({ seller_id: form.seller_id ? Number(form.seller_id) : undefined, customer_name: form.customer_name, customer_phone: form.customer_phone, payment_method: form.payment_method, items: [{ product_id: Number(form.product_id), quantity: Number(form.quantity) }] }) });
    reload();
  }
  return <CrudLayout form={<form className="panel form sale-form" onSubmit={save}><h2>Lancar Venda</h2>{user.role !== "vendedor" && <select value={form.seller_id} onChange={(e) => setForm({ ...form, seller_id: e.target.value })} required><option value="">Vendedor</option>{sellers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>}<select value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} required><option value="">Produto</option>{products.filter((p) => p.active).map((p) => <option key={p.id} value={p.id}>{p.name} · {money(p.sale_price)} · estoque {p.current_stock}</option>)}</select><input type="number" step="0.01" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })} /><strong className="total">{money(total)}</strong><select value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })}><option value="dinheiro">Dinheiro</option><option value="pix">Pix</option><option value="cartao">Cartao</option><option value="prazo">A prazo</option></select><input placeholder="Cliente" value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} /><input placeholder="Telefone do cliente" value={form.customer_phone} onChange={(e) => setForm({ ...form, customer_phone: e.target.value })} /><button className="primary big"><ReceiptText size={18} /> Confirmar Venda</button></form>} list={(sales || []).map((s) => <Row key={s.id} title={`${s.seller_name} · ${money(s.total_value)}`} meta={`${new Date(s.occurred_at).toLocaleString("pt-BR")} · ${s.payment_method} · ${s.items.map((i) => `${i.quantity}x ${i.product_name}`).join(", ")}`} />)} />;
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

function Deliveries({ api }) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ delivery_date: today, driver_name: "", vehicle: "", notes: "" });
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
      else next[sale.id] = { delivery_address: "", delivery_order: Object.keys(current).length + 1 };
      return next;
    });
  }

  function updateAddress(saleId, delivery_address) {
    setSelected((current) => ({ ...current, [saleId]: { ...current[saleId], delivery_address } }));
  }

  async function createManifest(e) {
    e.preventDefault();
    setMessage("");
    const items = Object.entries(selected).map(([saleId, item], index) => ({ sale_id: Number(saleId), delivery_address: item.delivery_address.trim(), delivery_order: index + 1 }));
    if (!items.length) return setMessage("Selecione pelo menos uma venda.");
    if (items.some((item) => !item.delivery_address)) return setMessage("Informe o endereco de todas as entregas.");
    try {
      await api.call("/delivery-manifests", { method: "POST", body: JSON.stringify({ ...form, items }) });
      setForm({ delivery_date: today, driver_name: "", vehicle: "", notes: "" });
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
      await api.call(`/delivery-manifests/${manifestId}/status`, { method: "PUT", body: JSON.stringify({ status }) });
      setMessage("Romaneio atualizado.");
      pendingLoad.reload();
      manifestsLoad.reload();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function updateDelivery(manifestId, itemId, status) {
    try {
      await api.call(`/delivery-manifests/${manifestId}/items/${itemId}`, { method: "PUT", body: JSON.stringify({ status }) });
      setMessage(status === "entregue" ? "Entrega confirmada." : "Entrega marcada como nao realizada.");
      manifestsLoad.reload();
    } catch (error) {
      setMessage(error.message);
    }
  }

  return <section className="delivery-page">
    <div className="delivery-create">
      <form className="panel form" onSubmit={createManifest}>
        <h2>Novo romaneio</h2>
        <label className="field"><span>Data da entrega</span><input type="date" value={form.delivery_date} onChange={(e) => setForm({ ...form, delivery_date: e.target.value })} required /></label>
        <label className="field"><span>Motorista</span><input value={form.driver_name} onChange={(e) => setForm({ ...form, driver_name: e.target.value })} placeholder="Nome do motorista" required /></label>
        <label className="field"><span>Veiculo</span><input value={form.vehicle} onChange={(e) => setForm({ ...form, vehicle: e.target.value })} placeholder="Modelo ou placa" /></label>
        <label className="field"><span>Observacoes</span><textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Rota, horario ou orientacoes" /></label>
        <button className="primary"><ClipboardList size={18} /> Criar romaneio</button>
        {message && <p className="form-status">{message}</p>}
      </form>
      <div className="panel pending-deliveries">
        <h2>Vendas aguardando entrega</h2>
        {!pendingSales.length && <p className="empty-state">Nenhuma venda pendente.</p>}
        {pendingSales.map((sale) => <div className={`delivery-choice ${selected[sale.id] ? "selected" : ""}`} key={sale.id}>
          <label className="delivery-check"><input type="checkbox" checked={Boolean(selected[sale.id])} onChange={() => toggleSale(sale)} /><span><b>{sale.customer_name || `Venda #${sale.id}`}</b><small>{sale.items.map((item) => `${item.quantity}x ${item.product_name}`).join(", ")} · {money(sale.total_value)}</small></span></label>
          {selected[sale.id] && <label className="field address-field"><span><MapPin size={14} /> Endereco de entrega</span><input value={selected[sale.id].delivery_address} onChange={(e) => updateAddress(sale.id, e.target.value)} placeholder="Rua, numero, bairro e referencia" /></label>}
        </div>)}
      </div>
    </div>
    <div className="manifest-section">
      <div className="section-title"><div><h2>Romaneios</h2><p>Acompanhe a separacao, rota e confirmacao das entregas.</p></div><button onClick={() => { pendingLoad.reload(); manifestsLoad.reload(); }}>Atualizar</button></div>
      {!manifests.length && <div className="panel empty-state">Nenhum romaneio criado.</div>}
      {manifests.map((manifest) => <article className="panel manifest" key={manifest.id}>
        <div className="manifest-header"><div><span className={`status status-${manifest.status}`}>{deliveryStatus[manifest.status]}</span><h2>{manifest.code}</h2><p>{new Date(`${manifest.delivery_date}T12:00:00`).toLocaleDateString("pt-BR")} · {manifest.driver_name}{manifest.vehicle ? ` · ${manifest.vehicle}` : ""}</p></div><div className="manifest-actions">{manifest.status === "preparacao" && <button onClick={() => updateManifestStatus(manifest.id, "em_rota")}><Play size={16} /> Iniciar rota</button>}{manifest.status !== "cancelado" && manifest.status !== "concluido" && <button className="danger" onClick={() => updateManifestStatus(manifest.id, "cancelado")}><Ban size={16} /> Cancelar</button>}</div></div>
        {manifest.notes && <p className="manifest-notes">{manifest.notes}</p>}
        <div className="delivery-items">{manifest.items.map((item) => <div className="delivery-item" key={item.id}><div className="delivery-order">{item.delivery_order}</div><div className="delivery-info"><b>{item.sale.customer_name || `Venda #${item.sale_id}`}</b><span><MapPin size={14} /> {item.delivery_address}</span><small>{item.sale.items.map((saleItem) => `${saleItem.quantity}x ${saleItem.product_name}`).join(", ")} · {money(item.sale.total_value)}</small></div><div className="delivery-result"><span className={`status status-${item.status}`}>{deliveryStatus[item.status]}</span>{manifest.status !== "cancelado" && item.status !== "entregue" && <div><button className="success" onClick={() => updateDelivery(manifest.id, item.id, "entregue")} title="Confirmar entrega"><CheckCircle2 size={16} /> Entregue</button><button onClick={() => updateDelivery(manifest.id, item.id, "nao_entregue")} title="Marcar como nao entregue">Nao entregue</button></div>}</div></div>)}</div>
      </article>)}
    </div>
  </section>;
}

function WhatsApp({ api }) {
  const { data, setData } = useLoad(api, () => api.call("/whatsapp/settings"), []);
  const [testStatus, setTestStatus] = useState("");
  if (!data) return <Loading />;
  const isTelegram = data.provider === "telegram";
  async function save(e) {
    e.preventDefault();
    const saved = await api.call("/whatsapp/settings", { method: "PUT", body: JSON.stringify(data) });
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
  return <form className="panel form max" onSubmit={save}><h2>Configuracoes de Alertas</h2><label className="field"><span>Provedor</span><select value={data.provider} onChange={(e) => setData({ ...data, provider: e.target.value })}><option value="mock">Mock</option><option value="telegram">Telegram Bot</option><option value="meta">Meta Cloud API</option><option value="zapi">Z-API</option><option value="twilio">Twilio</option></select></label>{!isTelegram && <label className="field"><span>URL da API</span><input placeholder="https://graph.facebook.com/VERSAO/PHONE_NUMBER_ID/messages" value={data.api_url || ""} onChange={(e) => setData({ ...data, api_url: e.target.value })} /></label>}<label className="field"><span>{isTelegram ? "Token do bot" : "Token de acesso"}</span><input type="password" placeholder={isTelegram ? "Token fornecido pelo BotFather" : "Token gerado pelo provedor"} value={data.token || ""} onChange={(e) => setData({ ...data, token: e.target.value })} /></label><label className="field"><span>{isTelegram ? "Chat ID do gestor ou grupo" : "WhatsApp do gestor"}</span><input placeholder={isTelegram ? "Ex.: 123456789 ou -1001234567890" : "Ex.: +5563999999999"} value={data.manager_phone} onChange={(e) => setData({ ...data, manager_phone: e.target.value })} /></label><label className="check"><input type="checkbox" checked={data.sale_notifications} onChange={(e) => setData({ ...data, sale_notifications: e.target.checked })} /> notificacao por venda</label><label className="check"><input type="checkbox" checked={data.low_stock_alerts} onChange={(e) => setData({ ...data, low_stock_alerts: e.target.checked })} /> alerta de estoque baixo</label><label className="check"><input type="checkbox" checked={data.daily_summary} onChange={(e) => setData({ ...data, daily_summary: e.target.checked })} /> resumo diario</label><label className="field"><span>Horario do resumo diario</span><input type="time" value={data.daily_summary_time?.slice(0, 5)} onChange={(e) => setData({ ...data, daily_summary_time: e.target.value })} /></label><button className="primary">Salvar Configuracoes</button><button type="button" onClick={testConnection}>Enviar alerta de teste</button>{testStatus && <p className="form-status">{testStatus}</p>}</form>;
}

function CrudLayout({ form, list }) {
  return <section className="crud">{form}<div className="panel list"><h2>Registros</h2>{list}</div></section>;
}

function Row({ title, meta, onEdit, actions }) {
  return <div className="row"><div><strong>{title}</strong><span>{meta}</span></div><div className="row-actions">{onEdit && <button onClick={onEdit}>Editar</button>}{actions}</div></div>;
}

function Loading() {
  return <div className="panel">Carregando...</div>;
}

createRoot(document.getElementById("root")).render(<App />);
