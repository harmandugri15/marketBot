/**
 * api.js
 * -------
 * Centralised API client. All fetch() calls go through here.
 * Handles auth token injection, error normalisation, and base URL.
 */

const BASE = "/api/v1";

function getToken() {
  return localStorage.getItem("mb_token");
}

export function setToken(token) {
  localStorage.setItem("mb_token", token);
}

export function clearToken() {
  localStorage.removeItem("mb_token");
}

async function request(method, path, body = null) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  try {
    const res = await fetch(`${BASE}${path}`, opts);

    if (res.status === 401) {
      clearToken();
      window.dispatchEvent(new Event("auth:expired"));
      throw new Error("Session expired — please log in again");
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "API error");
    }

    if (res.status === 204) return null;
    return res.json();
  } catch (err) {
    if (err.name === 'TypeError' && err.message === 'Failed to fetch') {
      const currentUrl = window.location.href;
      throw new Error(`Connection to Python backend blocked! 
        <br><br><b>Diagnostic Info:</b>
        <br>1. Target Backend URL: <code>${BASE}${path}</code>
        <br>2. Current Browser URL: <code>${currentUrl}</code>
        <br><br><b>Likely Causes:</b>
        <br>- The Python backend is not running.
        <br>- You opened the HTML file directly instead of using 'npm run dev'.
        <br>- CORS is blocking it because your browser URL doesn't match the allowed origins.`);
    }
    throw err;
  }
}

const get  = (path)        => request("GET",    path);
const post = (path, body)  => request("POST",   path, body);
const put  = (path, body)  => request("PUT",    path, body);
const del  = (path)        => request("DELETE", path);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const auth = {
  login: (username, password) => post("/auth/login", { username, password }),
  me:    ()                   => get("/auth/me"),
};

// ── Scanner ───────────────────────────────────────────────────────────────────
export const scanner = {
  signals:  (limit = 50) => get(`/scanner/signals?limit=${limit}`),
  run:      (strategy = "AUTO") => post(`/scanner/run?strategy=${strategy}`),
  regime:   ()           => get("/scanner/regime"),
};

// ── Trades ────────────────────────────────────────────────────────────────────
export const trades = {
  list:     (mode, status) => {
    let q = "/trades?limit=200";
    if (mode)   q += `&mode=${mode}`;
    if (status) q += `&status=${status}`;
    return get(q);
  },
  summary:  ()             => get("/trades/summary"),
  create:   (data)         => post("/trades", data),
  close:    (id, data)     => post(`/trades/${id}/close`, data),
  cancel:   (id)           => del(`/trades/${id}`),
};

// ── Backtest ──────────────────────────────────────────────────────────────────
export const backtest = {
  run:      (data)         => post("/backtest/run", data),
  progress: ()             => get("/backtest/progress"),
  results:  (limit = 20)   => get(`/backtest/results?limit=${limit}`),
  detail:   (id)           => get(`/backtest/${id}`),
};

// ── Forward Test ──────────────────────────────────────────────────────────────
export const forwardTest = {
  summary: ()          => get("/forward-test/summary"),
  logs:    (limit = 30) => get(`/forward-test/logs?limit=${limit}`),
  update:  ()          => post("/forward-test/update"),
};

// ── Settings ──────────────────────────────────────────────────────────────────
export const settings = {
  get:        ()     => get("/settings"),
  update:     (data) => put("/settings", data),
  enableLive: (data) => post("/settings/live", data),
};

// ── SSE helpers ───────────────────────────────────────────────────────────────
export function createSSE(path, onMessage, onError) {
  const token = getToken();
  const url = `${BASE}${path}${token ? `?token=${token}` : ""}`;
  const source = new EventSource(url);
  source.onmessage = (e) => onMessage(JSON.parse(e.data));
  source.onerror   = onError || (() => source.close());
  return source;
}
