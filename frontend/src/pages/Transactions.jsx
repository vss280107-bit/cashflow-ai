import { useEffect, useRef, useState } from "react";
import { api, inr } from "../api";

const today = () => new Date().toISOString().slice(0, 10);

export default function Transactions() {
  const [rows, setRows] = useState([]);
  const [cats, setCats] = useState({ expense: [], income: [] });
  const [filter, setFilter] = useState({ type: "", q: "" });
  const [form, setForm] = useState({ date: today(), amount: "", type: "expense", category: "", description: "" });
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const fileRef = useRef();

  const load = async () => {
    const qs = new URLSearchParams();
    if (filter.type) qs.set("type", filter.type);
    if (filter.q) qs.set("q", filter.q);
    setRows(await api.transactions(`?limit=300&${qs}`));
  };
  useEffect(() => { api.categories().then(setCats); }, []);
  useEffect(() => { load(); }, [filter]);

  const add = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.addTransaction({ ...form, amount: parseFloat(form.amount), category: form.category || null });
      setForm({ ...form, amount: "", description: "", category: "" });
      load();
    } catch (err) { setError(err.message); }
  };
  const remove = async (id) => { await api.deleteTransaction(id); load(); };
  const upload = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setError("");
    try {
      const r = await api.importCsv(f);
      setMsg(`Imported ${r.imported} rows${r.error_count ? `, ${r.error_count} skipped` : ""}.`);
      load();
    } catch (err) { setError(err.message); }
    e.target.value = "";
  };
  const demo = async () => {
    try { const r = await api.loadDemo(rows.length > 0); setMsg(`Loaded ${r.imported} demo transactions.`); load(); }
    catch (err) { setError(err.message); }
  };

  return (
    <>
      <div className="page-head">
        <h1>Transactions</h1>
        <div className="row">
          <input ref={fileRef} type="file" accept=".csv" hidden onChange={upload} />
          <button className="btn ghost" onClick={() => fileRef.current.click()}>Import CSV</button>
          <button className="btn ghost" onClick={demo}>Load demo data</button>
        </div>
      </div>
      {msg && <div className="notice-bar">{msg}</div>}
      {error && <div className="error">{error}</div>}

      <form className="card form-row" onSubmit={add}>
        <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
        <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value, category: "" })}>
          <option value="expense">Expense</option>
          <option value="income">Income</option>
        </select>
        <input type="number" min="1" step="0.01" placeholder="Amount (₹)" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
        <input placeholder="Description (e.g. Swiggy dinner)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          <option value="">Auto-categorise</option>
          {cats[form.type].map((c) => <option key={c}>{c}</option>)}
        </select>
        <button className="btn">Add</button>
      </form>

      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <select value={filter.type} onChange={(e) => setFilter({ ...filter, type: e.target.value })}>
            <option value="">All types</option><option value="income">Income</option><option value="expense">Expenses</option>
          </select>
          <input placeholder="Search description…" value={filter.q} onChange={(e) => setFilter({ ...filter, q: e.target.value })} />
          <span className="muted small">Showing latest {rows.length}</span>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Date</th><th>Description</th><th>Category</th><th className="num">Amount</th><th></th></tr></thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.description || "—"} {t.is_recurring && <span className="chip">recurring</span>}</td>
                  <td><span className="chip soft">{t.category}</span></td>
                  <td className={`num ${t.type}`}>{t.type === "income" ? "+" : "−"}{inr(t.amount)}</td>
                  <td><button className="link danger" onClick={() => remove(t.id)}>Delete</button></td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan="5" className="muted">No transactions yet.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="small muted" style={{ marginTop: 10 }}>
          CSV columns: <code>date, amount, description</code> (optional <code>type, category</code>). Negative amounts are treated as expenses. Dates: YYYY-MM-DD or DD/MM/YYYY.
        </div>
      </div>
    </>
  );
}
