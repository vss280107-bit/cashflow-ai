import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Auth from "./pages/Auth.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Transactions from "./pages/Transactions.jsx";
import Planner from "./pages/Planner.jsx";
import Model from "./pages/Model.jsx";
import Settings from "./pages/Settings.jsx";

function Shell({ children }) {
  const { user, signOut } = useAuth();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="logo">₹</span> CashFlow AI</div>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/transactions">Transactions</NavLink>
          <NavLink to="/planner">What-if planner</NavLink>
          <NavLink to="/model">Model & accuracy</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
        <div className="sidebar-foot">
          <div className="muted small">{user.name || user.email}</div>
          <button className="link" onClick={signOut}>Sign out</button>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <div className="center muted">Loading…</div>;
  if (!user)
    return (
      <Routes>
        <Route path="/login" element={<Auth />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/planner" element={<Planner />} />
        <Route path="/model" element={<Model />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}
