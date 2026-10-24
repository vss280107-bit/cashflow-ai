import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";

export default function Settings() {
  const { user, refresh } = useAuth();
  const [form, setForm] = useState({
    name: user.name, opening_balance: user.opening_balance, low_balance_threshold: user.low_balance_threshold,
  });
  const [msg, setMsg] = useState("");
  const save = async (e) => {
    e.preventDefault();
    await api.updateMe({ name: form.name, opening_balance: +form.opening_balance, low_balance_threshold: +form.low_balance_threshold });
    await refresh();
    setMsg("Saved.");
  };
  return (
    <>
      <div className="page-head"><h1>Settings</h1></div>
      <form className="card stack" onSubmit={save}>
        <label>Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
        <label>Opening balance (₹) <span className="muted small">— balance before your first recorded transaction</span>
          <input type="number" value={form.opening_balance} onChange={(e) => setForm({ ...form, opening_balance: e.target.value })} /></label>
        <label>Low-balance buffer (₹) <span className="muted small">— you’ll be warned when forecasts dip below this</span>
          <input type="number" min="0" value={form.low_balance_threshold} onChange={(e) => setForm({ ...form, low_balance_threshold: e.target.value })} /></label>
        <div className="row"><button className="btn">Save</button>{msg && <span className="muted">{msg}</span>}</div>
      </form>
    </>
  );
}
