const KEY = "cashflow_token";
export const getToken = () => localStorage.getItem(KEY);
export const setToken = (t) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY));

async function request(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, { method, headers, body: form || (body ? JSON.stringify(body) : undefined) });
  if (res.status === 401 && token) {
    setToken(null);
    window.location.href = "/login";
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") msg = j.detail;
      else if (Array.isArray(j.detail)) msg = j.detail.map((item) => item.msg).filter(Boolean).join("; ") || msg;
    } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  register: (b) => request("/auth/register", { method: "POST", body: b }),
  login: (b) => request("/auth/login", { method: "POST", body: b }),
  me: () => request("/auth/me"),
  transactions: (qs = "") => request(`/transactions${qs}`),
  categories: () => request("/transactions/categories"),
  addTransaction: (b) => request("/transactions", { method: "POST", body: b }),
  updateTransaction: (id, b) => request(`/transactions/${id}`, { method: "PUT", body: b }),
  deleteTransaction: (id) => request(`/transactions/${id}`, { method: "DELETE" }),
  importCsv: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/transactions/import", { method: "POST", form });
  },
  loadDemo: (replace = false) => request(`/transactions/demo?replace=${replace}`, { method: "POST" }),
  forecast: (h) => request(`/forecast?horizon=${h}`),
  summary: () => request("/summary"),
  evaluation: () => request("/model/evaluation"),
  budget: (month) => request(`/budget?month=${encodeURIComponent(month)}`),
  updateBudget: (amount, month) => request("/budget", { method: "PUT", body: { amount, month } }),
};

export const inr = (n) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n ?? 0);
export const shortDate = (iso) =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });
