import { useState } from "react";
import { useAuth } from "../auth.jsx";

export default function Auth() {
  const { signIn } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await signIn(mode, form);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={submit}>
        <div className="brand big"><span className="logo">₹</span> CashFlow AI</div>
        <p className="muted">Learn your spending patterns. Forecast your cash flow. Plan ahead.</p>
        {mode === "register" && <input placeholder="Name" value={form.name} onChange={set("name")} />}
        <input type="email" placeholder="Email" required value={form.email} onChange={set("email")} />
        <input type="password" placeholder="Password (min 8 characters)" required minLength={8} value={form.password} onChange={set("password")} />
        {error && <div className="error">{error}</div>}
        <button className="btn" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
        <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
        </button>
      </form>
    </div>
  );
}
