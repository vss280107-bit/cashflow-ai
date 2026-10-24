import { useState } from "react";
import { api, inr, shortDate } from "../api";
import ForecastChart from "../components/ForecastChart.jsx";

const inDays = (n) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);

export default function Planner() {
  const [items, setItems] = useState([{ date: inDays(7), amount: 5000, description: "New laptop" }]);
  const [horizon, setHorizon] = useState(30);
  const [res, setRes] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (i, k, v) => setItems(items.map((it, j) => (j === i ? { ...it, [k]: v } : it)));
  const run = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setRes(await api.whatIf({
        horizon,
        expenses: items.map((i) => ({ ...i, amount: parseFloat(i.amount) })),
      }));
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  const verdict = res && {
    safe: ["good", "Safe", "Your balance stays above your buffer, even in the worst case."],
    risky: ["warn", "Risky", `Expected path stays above your buffer, but the worst case dips below it around ${res.first_breach_worst_case && shortDate(res.first_breach_worst_case)}.`],
    unsafe: ["bad", "Not advisable", `Your expected balance drops below your buffer from ${res.first_breach_expected && shortDate(res.first_breach_expected)}.`],
  }[res.verdict];

  return (
    <>
      <div className="page-head"><h1>What-if planner</h1></div>
      <form className="card" onSubmit={run}>
        <p className="muted">“What happens if I spend ₹5,000 on a laptop next week?” Add planned one-off expenses and compare against your baseline forecast.</p>
        {items.map((it, i) => (
          <div className="form-row" key={i}>
            <input type="date" value={it.date} onChange={(e) => update(i, "date", e.target.value)} required />
            <input type="number" min="1" value={it.amount} onChange={(e) => update(i, "amount", e.target.value)} required />
            <input value={it.description} onChange={(e) => update(i, "description", e.target.value)} placeholder="What is it?" />
            {items.length > 1 && <button type="button" className="link danger" onClick={() => setItems(items.filter((_, j) => j !== i))}>Remove</button>}
          </div>
        ))}
        <div className="row">
          <button type="button" className="btn ghost" onClick={() => setItems([...items, { date: inDays(10), amount: 1000, description: "" }])}>+ Add expense</button>
          <select value={horizon} onChange={(e) => setHorizon(+e.target.value)}>
            <option value={14}>14 days</option><option value={30}>30 days</option><option value={60}>60 days</option>
          </select>
          <button className="btn" disabled={busy}>{busy ? "Simulating…" : "Run simulation"}</button>
        </div>
        {error && <div className="error">{error}</div>}
      </form>

      {res && (
        <>
          <div className={`card verdict ${verdict[0]}`}>
            <h2>{verdict[1]}</h2>
            <p>{verdict[2]}</p>
            <div className="small">
              Planned spend {inr(res.total_planned)} → expected balance at the end of the window {inr(res.scenario_end_balance)} ({inr(res.end_balance_change)} vs baseline).
              Remaining headroom: {inr(res.headroom_after.amount)}.
            </div>
          </div>
          <div className="card">
            <h3>Baseline vs with planned spending</h3>
            <ForecastChart daily={res.baseline} threshold={res.threshold} compare={res.scenario} />
          </div>
          <div className="small muted">{res.disclaimer}</div>
        </>
      )}
    </>
  );
}
