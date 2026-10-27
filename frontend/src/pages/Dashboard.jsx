import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, inr, shortDate } from "../api";

const dateParts = (value = new Date()) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
const compactINR = (value) => value >= 100000 ? `₹${(value / 100000).toFixed(1)}L` : value >= 1000 ? `₹${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k` : `₹${Math.round(value)}`;
const formatPercent = (value) => value == null ? "—" : `${Number(value).toFixed(Number(value) % 1 ? 1 : 0)}%`;

function BudgetPanel() {
  const [month, setMonth] = useState(dateParts());
  const [budget, setBudget] = useState(null);
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setBudget(null); setAmount(""); setError("");
    api.budget(month).then((data) => { if (active) { setBudget(data); setAmount(data.budget_amount ?? ""); } })
      .catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [month]);
  const save = async (event) => {
    event.preventDefault(); setSaving(true); setError("");
    try { setBudget(await api.updateBudget(Number(amount), month)); }
    catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };
  const used = budget?.percentage_used;
  const fill = Math.min(100, Math.max(0, Number(used) || 0));
  const status = budget?.status === "exceeded" ? "exceeded" : budget?.status === "warning" ? "warning" : "";
  const alert = status === "exceeded" ? "Limit reached. Spending is over budget." : status === "warning" ? "You have used at least 80% of this month's budget." : "";
  return <section className="budget-panel" aria-labelledby="budget-title">
    <div className="aside-section-head"><div><span className="micro-label">Plan</span><h2 id="budget-title">Monthly budget</h2></div><span className="budget-month-label">{month}</span></div>
    <form className="budget-form" onSubmit={save}>
      <label className="compact-field">Month<input aria-label="Budget month" type="month" value={month} onChange={(e) => setMonth(e.target.value)} required disabled={saving} /></label>
      <label className="compact-field">Monthly limit<input aria-label="Monthly spending limit in INR" type="number" min="0.01" step="0.01" placeholder="Set a limit" value={amount} onChange={(e) => setAmount(e.target.value)} required disabled={saving} /></label>
      <button className="btn btn-small" disabled={!budget || saving}>{saving ? "Saving…" : "Save budget"}</button>
    </form>
    {error && <div className="inline-error" role="alert">{error}</div>}
    <div className="budget-stats"><div><span>Spent</span><strong>{inr(budget?.amount_spent)}</strong></div><div className="budget-stats-right"><span>Remaining</span><strong>{budget?.remaining_balance == null ? "—" : inr(budget.remaining_balance)}</strong></div></div>
    <div className="budget-progress" role="progressbar" aria-label="Monthly budget used" aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(fill)}><span className={status} style={{ width: `${fill}%` }} /></div>
    <div className="budget-progress-meta"><span>{formatPercent(used)} used</span><span>{budget?.budget_amount == null ? "No limit set" : `of ${inr(budget.budget_amount)}`}</span></div>
    {alert && <div className={`budget-alert ${status}`} role="alert">{alert}</div>}
  </section>;
}

function RecentTransactions({ rows, loading }) {
  return <section className="panel recent-panel" aria-labelledby="recent-heading">
    <div className="section-head"><div><span className="micro-label">Latest activity</span><h2 id="recent-heading">Recent transactions</h2></div><Link className="text-link" to="/transactions">All transactions <span aria-hidden="true">→</span></Link></div>
    {loading ? <div className="panel-state">Loading activity…</div> : rows.length === 0 ? <div className="panel-state">No transactions yet. Add or import data to see activity.</div> : <div className="recent-list">{rows.slice(0, 5).map((row) => <div className="recent-row" key={row.id}>
      <div className="recent-icon" aria-hidden="true">{row.type === "income" ? "↙" : "↗"}</div>
      <div className="recent-description"><strong>{row.description || row.category || "Transaction"}</strong><span>{shortDate(row.date)} · {row.category}</span></div>
      <strong className={`recent-value ${row.type}`}>{row.type === "income" ? "+" : "−"}{inr(row.amount)}</strong>
    </div>)}</div>}
  </section>;
}

export default function Dashboard() {
  const [forecast, setForecast] = useState(null);
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const load = async () => {
    setBusy(true); setError("");
    try {
      const [f, s, t] = await Promise.all([api.forecast(), api.summary(), api.transactions("?limit=6")]);
      setForecast(f); setSummary(s); setTransactions(t);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  useEffect(() => { load(); }, []);
  if (busy) return <div className="page-state">Gathering your latest activity…</div>;
  if (error) return <div className="panel error-panel" role="alert"><div><span className="micro-label">Dashboard</span><h1>We couldn't load your finances.</h1><p>{error}</p></div><button className="btn" onClick={load}>Try again</button></div>;

  const monthly = summary?.monthly || [];
  const currentMonth = dateParts();
  const current = monthly.find((item) => item.month === currentMonth) || { income: 0, expense: 0 };
  const categories = summary?.categories || [];
  const totalExpenses = categories.reduce((total, item) => total + Number(item.amount || 0), 0);
  const hasHistory = monthly.length > 0;
  const forecastAvailable = Boolean(forecast?.available);
  const today = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
  const evaluations = new Map((forecast?.evaluation || []).map((row) => [row.month, row.predicted]));
  const chartData = monthly.map((row) => ({ month: row.month, income: row.income, expense: row.expense, projected: evaluations.get(row.month) ?? null }));
  if (forecastAvailable && chartData.length) {
    chartData[chartData.length - 1].projected ??= chartData[chartData.length - 1].expense;
    const [year, month] = chartData.at(-1).month.split("-").map(Number);
    const next = new Date(year, month, 1);
    chartData.push({ month: `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`, income: null, expense: null, projected: forecast.predicted_expenses });
  }

  return <div className="dashboard-layout">
    <main className="dashboard-main">
      <header className="dashboard-heading"><div><span className="micro-label">Personal finance · {today}</span><h1>Your cash flow</h1><p>See the shape of your money, month by month.</p></div><Link className="btn btn-outline" to="/transactions">Manage transactions <span aria-hidden="true">↗</span></Link></header>
      <div className="metric-strip">
        <div className="metric-item"><span>Income this month</span><strong className="income-text">{inr(current.income)}</strong><small>Current month · {currentMonth}</small></div>
        <div className="metric-item"><span>Expenses this month</span><strong className="expense-text">{inr(current.expense)}</strong><small>Current month · {currentMonth}</small></div>
        <div className="metric-item"><span>Net this month</span><strong>{inr(current.income - current.expense)}</strong><small>Income less expenses</small></div>
      </div>
      <section className="chart-panel" aria-labelledby="cashflow-chart-title">
        <div className="chart-panel-head"><div><span className="micro-label">Recorded history</span><h2 id="cashflow-chart-title">Cash flow over time</h2></div><div className="chart-legend"><span><i className="legend-swatch income-swatch" />Income</span><span><i className="legend-swatch expense-swatch" />Expenses</span>{forecastAvailable && <span><i className="legend-swatch forecast-swatch" />Estimate</span>}</div></div>
        {hasHistory ? <div className="hero-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 12, right: 12, bottom: 0, left: 4 }}>
          <CartesianGrid stroke="#FFFFFF12" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: "#A8A4AD", fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={18} />
          <YAxis tickFormatter={compactINR} tick={{ fill: "#A8A4AD", fontSize: 10 }} tickLine={false} axisLine={false} width={48} />
          <Tooltip formatter={(value) => inr(value)} contentStyle={{ border: "1px solid #46434A", borderRadius: 8, background: "#202027", color: "#F5F1E9", fontSize: 12 }} labelStyle={{ color: "#C8C2C7" }} />
          <Line type="monotone" dataKey="income" name="Income" stroke="#A8C86A" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} connectNulls />
          <Line type="monotone" dataKey="expense" name="Expenses" stroke="#D58A68" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} connectNulls />
          {forecastAvailable && <Line type="monotone" dataKey="projected" name="Expense estimate" stroke="#E7D7C8" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 2 }} activeDot={{ r: 4 }} connectNulls />}
        </LineChart></ResponsiveContainer></div> : <div className="panel-state chart-state">Your chart will take shape when you add transactions.</div>}
        <div className="chart-foot"><span>Recorded values reflect saved transactions.</span>{forecastAvailable && <span>Dashed line marks the model estimate.</span>}</div>
      </section>
      <RecentTransactions rows={transactions} loading={false} />
    </main>
    <aside className="dashboard-aside" aria-label="Monthly summary">
      <div className="aside-top"><div className="aside-avatar">{currentMonth.slice(5)}</div><div><span className="micro-label">This month</span><strong>{new Date(Number(currentMonth.slice(0, 4)), Number(currentMonth.slice(5, 7)) - 1, 1).toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</strong></div></div>
      <BudgetPanel />
      <section className="aside-section"><div className="aside-section-head"><div><span className="micro-label">Spending mix</span><h2>By category</h2></div><Link className="icon-link" to="/transactions" aria-label="View transactions">↗</Link></div>
        {categories.length ? <div className="category-list">{categories.slice(0, 5).map((item, index) => {
          const share = totalExpenses ? Math.min(100, Math.max(0, Number(item.amount) / totalExpenses * 100)) : 0;
          return <div className="category-item" key={item.category}><div className="category-line"><span>{item.category}</span><strong>{inr(item.amount)}</strong></div><div className="category-track"><span style={{ width: `${share}%`, background: index % 2 ? "#D58A68" : "#A8C86A" }} /></div></div>;
        })}</div> : <div className="panel-state compact-state">No expenses recorded yet.</div>}
      </section>
      <section className="aside-section insight-panel"><span className="micro-label">From your history</span>
        {summary?.insights?.length ? <ul>{summary.insights.slice(0, 2).map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>{hasHistory ? "Add more months of activity to surface useful comparisons." : "Your spending observations will appear here as you add data."}</p>}
      </section>
      <section className="forecast-nudge"><span className="micro-label">Next month</span>{forecastAvailable ? <><strong>{inr(forecast.predicted_expenses)}</strong><p>Estimated expenses · {forecast.model}</p></> : <><strong>Forecast not ready</strong><p>{forecast?.message || "Add more monthly history to prepare an estimate."}</p></>}<Link className="text-link" to="/model">Forecast details <span aria-hidden="true">→</span></Link></section>
      {!hasHistory && <div className="aside-empty-actions"><Link className="btn btn-small" to="/transactions">Add transactions</Link></div>}
    </aside>
  </div>;
}
