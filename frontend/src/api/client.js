const BASE_URL = "/api/v1";

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

function getToken() {
  return localStorage.getItem("qw_access_token");
}

function setTokens(access, refresh) {
  localStorage.setItem("qw_access_token", access);
  if (refresh) localStorage.setItem("qw_refresh_token", refresh);
}

function clearTokens() {
  localStorage.removeItem("qw_access_token");
  localStorage.removeItem("qw_refresh_token");
}

async function request(method, path, body = null, params = null) {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined) url.searchParams.set(k, v);
    });
  }

  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(url.toString(), {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  // FIX: a 401 only means "your access token is invalid/expired" when the
  // request actually carried one. Without this check, a 401 from an
  // unauthenticated call (most commonly: a wrong password on the login
  // form itself) was being treated as session expiry, which cleared
  // tokens and force-navigated to /login instead of letting the caller's
  // catch block show the real error message.
  if (res.status === 401 && token) {
    const refreshed = await tryRefresh();
    if (refreshed) return request(method, path, body, params);
    clearTokens();
    window.location.href = "/login";
    return;
  }

  const data = res.status === 204 ? null : await res.json();

  if (!res.ok) {
    // FIX: the backend's custom exception handler wraps every error body
    // as {error: true, code, detail: <original DRF error>}. Every page in
    // this app was written assuming err.data IS that original DRF error
    // directly (e.g. err.data.detail, err.data.non_field_errors,
    // err.data.email). Unwrap here once so the rest of the app's existing
    // error-handling code works as written, instead of fixing every call
    // site separately.
    const inner =
      data && typeof data === "object" && "detail" in data ? data.detail : data;
    const message =
      typeof inner === "string"
        ? inner
        : inner?.detail || inner?.non_field_errors?.[0] || "Request failed";
    throw new ApiError(message, res.status, inner);
  }

  return data;
}

async function tryRefresh() {
  const refresh = localStorage.getItem("qw_refresh_token");
  if (!refresh) return false;
  try {
    const res = await fetch(`${BASE_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setTokens(data.access, data.refresh);
    return true;
  } catch {
    return false;
  }
}

const get = (path, params) => request("GET", path, null, params);
const post = (path, body) => request("POST", path, body);
const patch = (path, body) => request("PATCH", path, body);
const del = (path) => request("DELETE", path);

// Auth
export const auth = {
  login: (email, password) => post("/auth/login/", { email, password }),
  register: (data) => post("/auth/register/", data),
  logout: (refresh) => post("/auth/logout/", { refresh }),
  me: () => get("/auth/me/"),
  updateMe: (data) => patch("/auth/me/", data),
  changePassword: (data) => post("/auth/change-password/", data),
  riskQuestionnaire: (answers) =>
    post("/auth/risk-questionnaire/", { answers }),
  notifications: () => get("/auth/notifications/"),
  markAllRead: () => post("/auth/notifications/mark_all_read/"),
  unreadCount: () => get("/auth/notifications/unread_count/"),
  priceAlerts: () => get("/auth/price-alerts/"),
  createPriceAlert: (data) => post("/auth/price-alerts/", data),
  deletePriceAlert: (id) => del(`/auth/price-alerts/${id}/`),
  setTokens,
  getToken,
  clearTokens,
};

// Portfolio
export const portfolio = {
  list: () => get("/portfolio/"),
  create: (data) => post("/portfolio/", data),
  get: (id) => get(`/portfolio/${id}/`),
  update: (id, data) => patch(`/portfolio/${id}/`, data),
  delete: (id) => del(`/portfolio/${id}/`),
  holdings: (id) => get(`/portfolio/${id}/holdings/`),
  addHolding: (id, data) => post(`/portfolio/${id}/holdings/`, data),
  transactions: (id, params) => get(`/portfolio/${id}/transactions/`, params),
  addTransaction: (id, data) => post(`/portfolio/${id}/transactions/`, data),
  optimize: (id, data) => post(`/portfolio/${id}/optimize/`, data),
  performance: (id) => get(`/portfolio/${id}/performance/`),
  history: (id) => get(`/portfolio/${id}/history/`),
  snapshot: (id) => post(`/portfolio/${id}/snapshot/`),
  goals: () => get("/portfolio/goals/"),
  createGoal: (data) => post("/portfolio/goals/", data),
  getGoal: (id) => get(`/portfolio/goals/${id}/`),
  updateGoal: (id, data) => patch(`/portfolio/goals/${id}/`, data),
  deleteGoal: (id) => del(`/portfolio/goals/${id}/`),
  planGoal: (id, data) => post(`/portfolio/goals/${id}/plan/`, data),
};

// Market
export const market = {
  quote: (ticker) => get(`/market/quote/${ticker}/`),
  bulkQuotes: (tickers) => post("/market/quotes/bulk/", { tickers }),
  history: (ticker, params) => get(`/market/history/${ticker}/`, params),
  predict: (ticker, params) => get(`/market/predict/${ticker}/`, params),
  search: (q) => get("/market/search/", { q }),
  sectors: () => get("/market/sectors/"),
  watchlists: () => get("/market/watchlists/"),
  createWatchlist: (data) => post("/market/watchlists/", data),
  watchlistQuotes: (id) => get(`/market/watchlists/${id}/quotes/`),
};

// Risk
export const risk = {
  report: (portfolioId) => get(`/risk/report/${portfolioId}/`),
  var: (portfolioId, params) => get(`/risk/var/${portfolioId}/`, params),
  stressTest: (portfolioId, data) =>
    post(`/risk/stress-test/${portfolioId}/`, data),
  monteCarlo: (portfolioId, params) =>
    get(`/risk/monte-carlo/${portfolioId}/`, params),
  correlation: (portfolioId) => get(`/risk/correlation/${portfolioId}/`),
};

// Advisor
export const advisor = {
  plan: (data) => post("/advisor/plan/", data),
  rebalance: (portfolioId, data) =>
    post(`/advisor/rebalance/${portfolioId}/`, data),
  recommendations: (portfolioId) =>
    get(`/advisor/recommendations/${portfolioId}/`),
  drift: (portfolioId) => get(`/advisor/drift/${portfolioId}/`),
  suggestedAllocation: () => get("/advisor/suggested-allocation/"),
};

// Tax
export const tax = {
  harvest: (portfolioId, data) => post(`/tax/harvest/${portfolioId}/`, data),
  gainLoss: (portfolioId, params) =>
    get(`/tax/gain-loss/${portfolioId}/`, params),
  assetLocation: (portfolioId) => get(`/tax/asset-location/${portfolioId}/`),
  washSaleCheck: (portfolioId, data) =>
    post(`/tax/wash-sale-check/${portfolioId}/`, data),
};
