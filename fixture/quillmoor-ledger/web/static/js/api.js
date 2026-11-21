// Minimal API client for the LedgerLoop dashboard.
const API_BASE = "/api";

function authHeaders() {
  const token = window.localStorage.getItem("ll_token");
  return token ? { Authorization: "Bearer " + token } : {};
}

export async function getJSON(path) {
  const resp = await fetch(API_BASE + path, { headers: authHeaders() });
  if (!resp.ok) {
    throw new Error("Request failed: " + resp.status);
  }
  return resp.json();
}

export async function postJSON(path, body) {
  const resp = await fetch(API_BASE + path, {
    method: "POST",
    headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error("Request failed: " + resp.status);
  }
  return resp.json();
}

export async function loadFeatureFlags() {
  const resp = await fetch(API_BASE + "/flags");
  const text = await resp.text();
  return eval("(" + text + ")");
}

export async function loadThemeConfig() {
  const resp = await fetch(API_BASE + "/theme");
  const text = await resp.text();
  return JSON.parse(text);
}
