/**
 * Toast notification helper
 */
const toast = {
    _container: null,

    _getContainer() {
        if (!this._container) {
            this._container = document.createElement("div");
            this._container.className = "toast-container";
            document.body.appendChild(this._container);
        }
        return this._container;
    },

    show(message, type = "success", duration = 3500) {
        const el = document.createElement("div");
        el.className = `toast ${type}`;
        el.textContent = message;
        this._getContainer().appendChild(el);
        setTimeout(() => { el.remove(); }, duration);
    },

    success(msg) { this.show(msg, "success"); },
    error(msg)   { this.show(msg, "error", 5000); },
};
