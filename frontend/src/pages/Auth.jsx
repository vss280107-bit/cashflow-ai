import { useState } from "react";
import { useAuth } from "../auth.jsx";
import { BrandMark } from "../components/Brand.jsx";

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
      <section className="auth-story">
        <div className="brand"><BrandMark /><span className="brand-wordmark"><strong>CashFlow</strong><em>AI</em></span></div>
        <div className="auth-copy">
          <div className="eyebrow">A steadier view of your money</div>
          <h1>Make room for what matters.</h1>
          <p>Bring your everyday finances into focus with thoughtful summaries, spending patterns, and a forecast grounded in your own history.</p>
        </div>
        <div className="auth-bottom">A personal finance learning project · Your data stays yours</div>
      </section>
      <div className="auth-form-side">
        <form className="auth-card" onSubmit={submit}>
          <div className="eyebrow">Your personal workspace</div>
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p>{mode === "login" ? "Sign in to pick up where you left off." : "Start with your own transactions and build a clearer picture."}</p>
          {mode === "register" && <label className="field">Name<input autoComplete="name" placeholder="Your name" required maxLength={120} value={form.name} onChange={set("name")} /></label>}
          <label className="field">Email address<input type="email" autoComplete="email" placeholder="you@example.com" required value={form.email} onChange={set("email")} /></label>
          <label className="field">Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder="At least 8 characters" required minLength={8} value={form.password} onChange={set("password")} /></label>
          {error && <div className="error" role="alert">{error}</div>}
          <button className="btn" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
          <button type="button" className="link auth-switch" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
            {mode === "login" ? "New here? Create an account" : "Already have an account? Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
