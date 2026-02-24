/**
 * HisabKitab – Auth module
 * Handles login, register, and guard for protected pages.
 */

const auth = {
    /** Redirect to login if not authenticated */
    guard() {
        if (!api.getToken()) {
            window.location.href = "index.html";
        }
    },

    /** Bind login form */
    initLogin() {
        const form = document.getElementById("login-form");
        if (!form) return;
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = form.email.value.trim();
            const password = form.password.value;
            try {
                const data = await api.post("/auth/login", { email, password });
                api.setToken(data.token);
                api.setUserId(data.user_id);
                window.location.href = "dashboard.html";
            } catch (err) {
                toast.error(err.message);
            }
        });
    },

    /** Bind register form */
    initRegister() {
        const form = document.getElementById("register-form");
        if (!form) return;
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = form.email.value.trim();
            const password = form.password.value;
            const display_name = form.display_name.value.trim() || null;
            try {
                const data = await api.post("/auth/register", { email, password, display_name });
                api.setToken(data.token);
                api.setUserId(data.user_id);
                window.location.href = "dashboard.html";
            } catch (err) {
                toast.error(err.message);
            }
        });
    },

    /** Set display name in sidebar */
    async setUserInfo() {
        try {
            const user = await api.get("/auth/me");
            const el = document.getElementById("user-display");
            if (el) el.textContent = user.display_name || user.email;
        } catch { /* ignore */ }
    },
};
