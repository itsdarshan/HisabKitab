/**
 * HisabKitab – API client
 * Wraps fetch calls with auth token, base URL, and error handling.
 */

const API_BASE = "/api";

const api = {
    /** Get stored JWT token */
    getToken() {
        return localStorage.getItem("hk_token");
    },

    /** Set JWT token */
    setToken(token) {
        localStorage.setItem("hk_token", token);
    },

    /** Set user id */
    setUserId(id) {
        localStorage.setItem("hk_user_id", id);
    },

    /** Clear session */
    logout() {
        localStorage.removeItem("hk_token");
        localStorage.removeItem("hk_user_id");
        window.location.href = "index.html";
    },

    /** Build headers */
    _headers(json = true) {
        const h = {};
        const t = this.getToken();
        if (t) h["Authorization"] = `Bearer ${t}`;
        if (json) h["Content-Type"] = "application/json";
        return h;
    },

    /** Generic request */
    async request(method, path, body = null, isJson = true) {
        const opts = { method, headers: this._headers(isJson && body !== null) };
        if (body) {
            opts.body = isJson ? JSON.stringify(body) : body;
        }
        const res = await fetch(`${API_BASE}${path}`, opts);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            const msg = data.error || `Request failed (${res.status})`;
            throw new Error(msg);
        }
        return data;
    },

    get(path)        { return this.request("GET", path); },
    post(path, body) { return this.request("POST", path, body); },
    patch(path, body){ return this.request("PATCH", path, body); },
    del(path)        { return this.request("DELETE", path); },

    /** Upload file (multipart/form-data) */
    async upload(path, formData) {
        const res = await fetch(`${API_BASE}${path}`, {
            method: "POST",
            headers: { Authorization: `Bearer ${this.getToken()}` },
            body: formData,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || "Upload failed");
        return data;
    },
};
