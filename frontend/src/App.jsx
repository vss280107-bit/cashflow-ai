import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Auth from "./pages/Auth.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Transactions from "./pages/Transactions.jsx";
import Model from "./pages/Model.jsx";
import { BrandMark, NavigationIcon } from "./components/Brand.jsx";

function Shell({ children }) {
  const { user, signOut } = useAuth();
  const displayName = user.name || user.email;
  const initials = displayName.split(/[\s@._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <NavLink to="/" className="brand"><BrandMark /><span className="brand-wordmark"><strong>CashFlow</strong><em>AI</em></span></NavLink>
        </div>
        <div className="nav-label">Your money</div>
        <nav className="side-nav" aria-label="Main navigation">
          <NavLink to="/" end className={({ isActive }) => isActive ? "active" : ""}><span className="nav-icon"><NavigationIcon kind="dashboard" /></span>Dashboard</NavLink>
          <NavLink to="/transactions" className={({ isActive }) => isActive ? "active" : ""}><span className="nav-icon"><NavigationIcon kind="transactions" /></span>Transactions</NavLink>
          <NavLink to="/model" className={({ isActive }) => isActive ? "active" : ""}><span className="nav-icon"><NavigationIcon kind="forecast" /></span>Forecast</NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="user-panel">
            <div className="avatar" aria-hidden="true">{initials || "U"}</div>
            <div className="user-details"><strong>{displayName}</strong><span>Personal account</span></div>
            <button className="signout" onClick={signOut}>Sign out</button>
          </div>
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
        <Route path="/model" element={<Model />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}
