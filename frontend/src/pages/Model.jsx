import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, inr } from "../api";

const nextMonth = (month) => {
  const [year, value] = month.split("-").map(Number);
  const date = new Date(year, value, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
};
const compactINR = (value) => value >= 100000 ? `₹${(value / 100000).toFixed(1)}L` : value >= 1000 ? `₹${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k` : `₹${Math.round(value)}`;

function Metric({ label, value, detail, tone }) {
  return <article className="card kpi"><div className="kpi-label"><span>{label}</span><i className={`kpi-marker ${tone || ""}`} aria-hidden="true" /></div><div className="kpi-value">{value}</div><div className="kpi-foot">{detail}</div></article>;
}

export default function Model() {
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true); setError("");
    try { setForecast(await api.forecast()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  if (loading) return <div className="loading-state">Preparing your forecast…</div>;
  if (error) return <div className="card page-error"><div><div className="eyebrow">Forecast unavailable</div><h2>We couldn't load the forecast.</h2><p className="muted">{error}</p></div><button className="btn" onClick={load}>Try again</button></div>;
  if (!forecast?.available) return <>
    <header className="page-head"><div><div className="eyebrow">Looking ahead</div><h1>Forecast</h1><p className="subhead muted">A measured estimate based on your recorded spending.</p></div></header>
    <section className="card empty-state"><div><strong>More history is needed</strong>{forecast?.message || "Add transaction history to prepare a forecast."}<div style={{ marginTop: 16 }}><Link className="btn" to="/transactions">Add transactions</Link></div></div></section>
  </>;

  const history = forecast.history || [];
  const evaluated = new Map((forecast.evaluation || []).map((item) => [item.month, item.predicted]));
  const chartData = history.map((item) => ({ month: item.month, actual: item.expense, predicted: evaluated.get(item.month) ?? null }));
  if (history.length) chartData.push({ month: nextMonth(history.at(-1).month), actual: null, predicted: forecast.predicted_expenses });

  return <>
    <header className="page-head"><div><div className="eyebrow">Looking ahead</div><h1>Forecast</h1><p className="subhead muted">An estimate from your saved monthly expense history.</p></div></header>
    <div className="grid kpis three">
      <Metric label="Next month expenses" value={inr(forecast.predicted_expenses)} tone="expense" detail="Model estimate" />
      <Metric label="Estimated savings" value={forecast.estimated_savings == null ? "—" : inr(forecast.estimated_savings)} detail="Latest recorded income less predicted expenses" />
      <Metric label="Test MAE" value={forecast.mae == null ? "—" : inr(forecast.mae)} detail="Held-out estimate error · lower is closer" />
    </div>
    <section className="card">
      <h3>Actual and predicted expenses <span className="chart-legend"><span className="legend-item"><i className="legend-dot" />Actual</span><span className="legend-item"><i className="legend-dot terracotta" />Predicted</span></span></h3>
      <div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ top: 6, right: 12, bottom: 0, left: 0 }} barGap={5}>
        <CartesianGrid stroke="#FFFFFF12" vertical={false} />
        <XAxis dataKey="month" tick={{ fill: "#A8A4AD", fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={18} />
        <YAxis tickFormatter={compactINR} tick={{ fill: "#A8A4AD", fontSize: 10 }} tickLine={false} axisLine={false} width={50} />
        <Tooltip formatter={(value) => inr(value)} contentStyle={{ border: "1px solid #46434A", borderRadius: 8, background: "#202027", color: "#F5F1E9", fontSize: 12 }} labelStyle={{ color: "#C8C2C7" }} />
        <Legend wrapperStyle={{ fontSize: 11, color: "#A8A4AD" }} />
        <Bar dataKey="actual" name="Actual expenses" fill="#A8C86A" radius={[3, 3, 0, 0]} maxBarSize={32} />
        <Bar dataKey="predicted" name="Predicted expenses" fill="#D58A68" radius={[3, 3, 0, 0]} maxBarSize={32} />
      </BarChart></ResponsiveContainer></div>
      <p className="small muted" style={{ margin: "9px 0 0", lineHeight: 1.55 }}>{forecast.message}</p>
    </section>
    {forecast.evaluation?.length > 0 && <section className="card">
      <div className="eyebrow">Model check</div><h3>Held-out predictions</h3>
      <p className="small muted" style={{ marginBottom: 12, lineHeight: 1.5 }}>These months were evaluated separately from the training period. Actual values and model outputs are shown from the API response.</p>
      <div className="table-wrap"><table className="table"><thead><tr><th>Month</th><th className="num">Actual expenses</th><th className="num">Predicted expenses</th></tr></thead><tbody>
        {forecast.evaluation.map((item) => <tr key={item.month}><td>{item.month}</td><td className="num">{inr(item.actual)}</td><td className="num">{inr(item.predicted)}</td></tr>)}
      </tbody></table></div>
    </section>}
    <p className="small muted" style={{ marginBottom: 0 }}>This is a learning-project estimate. It reflects the transaction history currently saved to your account.</p>
  </>;
}
