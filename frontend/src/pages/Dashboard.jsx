import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, inr, shortDate } from "../api";
import ForecastChart from "../components/ForecastChart.jsx";

const Kpi = ({ label, value, sub, tone }) => (
  <div className={`card kpi ${tone || ""}`}>
    <div className="muted small">{label}</div>
    <div className="kpi-value">{value}</div>
    {sub && <div className="small muted">{sub}</div>}
  </div>
);

export default function Dashboard() {
  const [horizon, setHorizon] = useState(30);
  const [fc, setFc] = useState(null);
  const [sum, setSum] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async (h = horizon) => {
    setBusy(true);
    setError("");
    try {
      const [f, s] = await Promise.all([api.forecast(h), api.summary()]);
      setFc(f);
      setSum(s);
    } catch (e) {
      setError(e.message);
      setFc(null);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => { load(horizon); }, [horizon]);

  const demo = async () => { await api.loadDemo(true); load(); };

  if (error)
    return (
      <div className="card empty">
        <h2>No data to forecast yet</h2>
        <p className="muted">{error}</p>
        <div className="row">
          <button className="btn" onClick={demo}>Load demo data</button>
          <Link className="btn ghost" to="/transactions">Add transactions</Link>
        </div>
      </div>
    );
  if (!fc) return <div className="muted">{busy ? "Training model & forecasting… (first run takes a few seconds)" : ""}</div>;

  const s = fc.summary, plan = fc.plan;
  const risk = plan.risk_periods[0];
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <div className="muted small">As of {shortDate(fc.as_of)} · model: {fc.model === "gradient_boosting" ? "Gradient boosting (+ quantile bands)" : "Baseline (cold start)"}</div>
        </div>
        <div className="seg">
          {[14, 30, 60].map((h) => (
            <button key={h} className={h === horizon ? "on" : ""} onClick={() => setHorizon(h)}>{h} days</button>
          ))}
        </div>
      </div>

      <div className="grid kpis">
        <Kpi label="Current balance" value={inr(fc.current_balance)} />
        <Kpi label={`Expected in ${fc.horizon} days`} value={inr(s.expected_balance)} sub={`Range ${inr(s.range_low)} – ${inr(s.range_high)}`} />
        <Kpi label="Cash-shortage risk" value={risk ? (risk.severity === "high" ? "High" : "Moderate") : "Low"} tone={risk ? (risk.severity === "high" ? "bad" : "warn") : "good"}
             sub={risk ? `${shortDate(risk.start)} – ${shortDate(risk.end)}` : "No dip below your buffer"} />
        <Kpi label="Spending headroom" value={inr(plan.headroom.amount)} sub={`≈ ${inr(plan.headroom.per_day)}/day, conservative`} />
      </div>

      <div className="card">
        <h3>Balance forecast</h3>
        <ForecastChart daily={fc.daily} threshold={fc.threshold} />
        <div className="small muted">Shaded band = 80% range. The dashed red line is your low-balance buffer.</div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Insights</h3>
          <ul className="list">
            {plan.insights.map((i, k) => (
              <li key={k}><strong>{i.title}</strong><div className="muted small">{i.detail}</div></li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3>Planning suggestions</h3>
          <ul className="list">
            {plan.risk_periods.map((r, k) => (
              <li key={`r${k}`} className={r.severity === "high" ? "alert" : "notice"}>{r.message}</li>
            ))}
            {plan.suggestions.map((t, k) => <li key={k}>{t}</li>)}
          </ul>
          <div className="small muted">{plan.disclaimer}</div>
        </div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Upcoming recurring bills</h3>
          {fc.upcoming_bills.length === 0 ? <div className="muted">None detected in this window.</div> : (
            <table className="table">
              <tbody>
                {fc.upcoming_bills.slice(0, 8).map((b, k) => (
                  <tr key={k}><td>{shortDate(b.date)}</td><td>{b.label}</td><td className="num">{inr(b.amount)}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="card">
          <h3>What drives the forecast</h3>
          {fc.drivers.length === 0 ? <div className="muted">Baseline model: moving average + same-weekday pattern.</div> : (
            <ul className="bars">
              {fc.drivers.map((d) => (
                <li key={d.feature}>
                  <span>{d.label}</span>
                  <span className="bar"><i style={{ width: `${Math.min(100, d.importance * 250)}%` }} /></span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {sum && sum.monthly.length > 0 && (
        <div className="card">
          <h3>Income vs expenses by month</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={sum.monthly}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e6e8f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} width={56} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v) => inr(v)} />
              <Legend />
              <Bar dataKey="income" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="expense" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </>
  );
}
