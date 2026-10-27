import { useEffect, useRef, useState } from "react";
import { api, inr, shortDate } from "../api";

const today = () => {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
};
const blankForm = () => ({ date: today(), amount: "", type: "expense", category: "", description: "" });

export default function Transactions() {
  const [rows, setRows] = useState([]);
  const [cats, setCats] = useState({ expense: [], income: [] });
  const [filter, setFilter] = useState({ type: "", category: "", start: "", end: "", q: "" });
  const [form, setForm] = useState(blankForm);
  const [editing, setEditing] = useState(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileRef = useRef();

  const load = async () => {
    const qs = new URLSearchParams();
    if (filter.type) qs.set("type", filter.type);
    if (filter.category) qs.set("category", filter.category);
    if (filter.start) qs.set("start", filter.start);
    if (filter.end) qs.set("end", filter.end);
    if (filter.q) qs.set("q", filter.q);
    setLoading(true); setError("");
    try { setRows(await api.transactions(`?limit=300&${qs}`)); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { api.categories().then(setCats).catch((e) => setError(e.message)); }, []);
  useEffect(() => { load(); }, [filter]);

  const add = async (event) => {
    event.preventDefault(); setError(""); setMsg(""); setSaving(true);
    try {
      const payload = { ...form, amount: Number(form.amount), category: form.category || null };
      if (editing) await api.updateTransaction(editing, payload);
      else await api.addTransaction(payload);
      setEditing(null); setForm(blankForm()); setMsg(editing ? "Transaction updated." : "Transaction added.");
      await load();
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };
  const remove = async (id) => {
    setError(""); setMsg("");
    try { await api.deleteTransaction(id); setMsg("Transaction deleted."); await load(); }
    catch (e) { setError(e.message); }
  };
  const edit = (row) => {
    setEditing(row.id);
    setForm({ date: row.date, amount: String(row.amount), type: row.type, category: row.category, description: row.description || "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const upload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setError(""); setMsg(""); setImporting(true);
    try {
      const result = await api.importCsv(file);
      setMsg(`Imported ${result.imported} rows${result.error_count ? `; ${result.error_count} skipped` : ""}.`);
      await load();
    } catch (e) { setError(e.message); }
    finally { setImporting(false); event.target.value = ""; }
  };
  const demo = async () => {
    setError(""); setMsg("");
    try { const result = await api.loadDemo(false); setMsg(`Loaded ${result.imported} synthetic demo transactions.`); await load(); }
    catch (e) { setError(e.message); }
  };
  const clearFilters = () => setFilter({ type: "", category: "", start: "", end: "", q: "" });

  return <>
    <header className="page-head">
      <div><div className="eyebrow">Your activity</div><h1>Transactions</h1><p className="subhead muted">A clear record of money in and money out.</p></div>
      <div className="row">
        <input ref={fileRef} type="file" accept=".csv,text/csv" hidden onChange={upload} />
        <button className="btn ghost" onClick={() => fileRef.current?.click()} disabled={importing}>{importing ? "Importing…" : "↑ Import CSV"}</button>
        <button className="btn ghost" onClick={demo}>Load demo data</button>
      </div>
    </header>
    {msg && <div className="notice-bar" role="status">{msg}</div>}
    {error && <div className="error" role="alert">{error}</div>}

    <section className="card" aria-labelledby="transaction-form-title">
      <div className="eyebrow">{editing ? "Update a record" : "Add a record"}</div>
      <h3 id="transaction-form-title">{editing ? "Edit transaction" : "New transaction"}</h3>
      <form className="form-grid" onSubmit={add}>
        <label className="field">Date<input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required /></label>
        <label className="field">Type<select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value, category: "" })}><option value="expense">Expense</option><option value="income">Income</option></select></label>
        <label className="field">Amount (INR)<input type="number" min="0.01" step="0.01" placeholder="0.00" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required /></label>
        <label className="field">Category<select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}><option value="">Auto-categorise</option>{cats[form.type].map((category) => <option key={category} value={category}>{category}</option>)}</select></label>
        <label className="field description-field">Description<input maxLength="500" placeholder="What was this for?" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
        <div className="row form-actions"><button className="btn" disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : "Add transaction"}</button>
          {editing && <button type="button" className="btn ghost" onClick={() => { setEditing(null); setForm(blankForm()); }}>Cancel</button>}</div>
      </form>
    </section>

    <section className="card" aria-labelledby="transaction-list-title">
      <div className="table-toolbar"><div><div className="eyebrow">Ledger</div><h3 id="transaction-list-title">All transactions</h3></div><span className="small muted">{loading ? "Updating…" : `${rows.length} shown`}</span></div>
      <div className="filter-row" style={{ marginBottom: 15 }}>
        <label className="field search-field">Search<input aria-label="Search transactions" placeholder="Description or merchant" value={filter.q} onChange={(e) => setFilter({ ...filter, q: e.target.value })} /></label>
        <label className="field">Type<select value={filter.type} onChange={(e) => setFilter({ ...filter, type: e.target.value })}><option value="">All types</option><option value="income">Income</option><option value="expense">Expenses</option></select></label>
        <label className="field">Category<select value={filter.category} onChange={(e) => setFilter({ ...filter, category: e.target.value })}><option value="">All categories</option>{[...cats.expense, ...cats.income].map((category) => <option key={category} value={category}>{category}</option>)}</select></label>
        <label className="field">From<input aria-label="Start date" type="date" value={filter.start} onChange={(e) => setFilter({ ...filter, start: e.target.value })} /></label>
        <label className="field">To<input aria-label="End date" type="date" value={filter.end} onChange={(e) => setFilter({ ...filter, end: e.target.value })} /></label>
        <button className="btn ghost" type="button" onClick={clearFilters}>Clear</button>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Type</th><th className="num">Amount</th><th><span className="sr-only">Actions</span></th></tr></thead>
          <tbody>
            {rows.map((row) => <tr key={row.id}>
              <td>{shortDate(row.date)}</td><td>{row.description || "—"}</td><td><span className="chip">{row.category}</span></td>
              <td><span className={`type-pill ${row.type}`}>{row.type === "income" ? "Income" : "Expense"}</span></td>
              <td className={`num amount ${row.type}`}>{row.type === "income" ? "+" : "−"}{inr(row.amount)}</td>
              <td><div className="table-actions"><button className="link small" onClick={() => edit(row)}>Edit</button><button className="link danger small" onClick={() => remove(row.id)}>Delete</button></div></td>
            </tr>)}
            {loading && <tr><td colSpan="6" className="muted">Loading transactions…</td></tr>}
            {!loading && rows.length === 0 && <tr><td colSpan="6" className="muted">No transactions match these filters.</td></tr>}
          </tbody>
        </table>
      </div>
      <p className="small muted" style={{ margin: "13px 0 0", lineHeight: 1.5 }}>CSV columns: <code>date, amount</code> with optional <code>type, category, description</code>. Negative amounts are treated as expenses.</p>
    </section>
  </>;
}
