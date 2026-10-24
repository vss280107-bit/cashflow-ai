import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, inr } from "../api";

const Row = ({ label, a, b, fmt = (v) => v }) => (
  <tr><td>{label}</td><td className="num">{a == null ? "—" : fmt(a)}</td><td className="num">{b == null ? "—" : fmt(b)}</td></tr>
);

export default function Model() {
  const [ev, setEv] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.evaluation().then(setEv).catch((e) => setError(e.message)); }, []);

  if (error) return <div className="error">{error}</div>;
  if (!ev) return <div className="muted">Running backtest… (takes a few seconds)</div>;
  if (!ev.available) return <div className="card empty"><h2>Backtest not available yet</h2><p className="muted">{ev.reason}</p></div>;

  const t = ev.test, d = t.discretionary_daily, c = t.cash_flow_daily_mae, lb = t.low_balance_detection;
  return (
    <>
      <div className="page-head"><div><h1>Model & accuracy</h1>
        <div className="muted small">{ev.note}</div></div></div>

      <div className="grid kpis">
        <div className="card kpi"><div className="muted small">Split (days)</div><div className="kpi-value small-v">{ev.split.train_days} / {ev.split.validation_days} / {ev.split.test_days}</div><div className="small muted">train / validation / test</div></div>
        <div className="card kpi"><div className="muted small">80% interval coverage</div><div className="kpi-value">{t.interval_coverage_80}%</div><div className="small muted">target ≈ 80%</div></div>
        <div className="card kpi"><div className="muted small">Low-balance alerts</div><div className="kpi-value">{lb.precision ?? "—"} / {lb.recall ?? "—"}</div><div className="small muted">precision / recall ({t.origins} backtest origins)</div></div>
        <div className="card kpi"><div className="muted small">Recurring items found</div><div className="kpi-value">{ev.recurring_detected}</div></div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Flexible spending (daily, test period)</h3>
          <table className="table">
            <thead><tr><th>Method</th><th className="num">MAE</th><th className="num">RMSE</th></tr></thead>
            <tbody>
              <tr><td><strong>{ev.model === "gradient_boosting" ? "Gradient boosting" : "Baseline"}</strong></td><td className="num">{inr(d.model.mae)}</td><td className="num">{inr(d.model.rmse)}</td></tr>
              <tr><td>Seasonal naive</td><td className="num">{inr(d.seasonal_naive.mae)}</td><td className="num">{inr(d.seasonal_naive.rmse)}</td></tr>
              <tr><td>Moving average</td><td className="num">{inr(d.moving_average.mae)}</td><td className="num">{inr(d.moving_average.rmse)}</td></tr>
            </tbody>
          </table>
          <div className="small muted">Weekly-total MAPE: model {t.discretionary_weekly_mape.model}% vs seasonal naive {t.discretionary_weekly_mape.seasonal_naive}%.</div>
        </div>
        <div className="card">
          <h3>Cash flow (daily MAE, test period)</h3>
          <table className="table">
            <thead><tr><th></th><th className="num">Model</th><th className="num">28-day avg</th></tr></thead>
            <tbody>
              <Row label="Income" a={c.income.model} b={c.income.baseline} fmt={inr} />
              <Row label="Expenses" a={c.expenses.model} b={c.expenses.baseline} fmt={inr} />
              <Row label="Net cash flow" a={c.net.model} b={c.net.baseline} fmt={inr} />
              <Row label={`${ev.horizon}-day ending balance`} a={t.ending_balance_mae.model} b={t.ending_balance_mae.baseline} fmt={inr} />
            </tbody>
          </table>
          <div className="small muted">Low-balance confusion matrix (buffer {inr(lb.threshold)}): TP {lb.true_positive} · FP {lb.false_positive} · FN {lb.false_negative} · TN {lb.true_negative}.</div>
        </div>
      </div>

      {ev.feature_importance.length > 0 && (
        <div className="card">
          <h3>Feature importance</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={ev.feature_importance} layout="vertical" margin={{ left: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e6e8f0" />
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="label" width={190} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="importance" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <div className="small muted">Estimates for planning support only. This is not investment or financial advice.</div>
    </>
  );
}
