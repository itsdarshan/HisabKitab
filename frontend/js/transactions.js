/**
 * HisabKitab – Transactions module
 * Table with filters, sorting, pagination, inline category edit
 */

const txns = {
    categories: [],
    currentPage: 1,
    perPage: 25,
    sortBy: "date",
    sortDir: "desc",

    async init() {
        auth.guard();
        auth.setUserInfo();
        await this.loadCategories();
        this.bindFilters();
        this.load();
    },

    async loadCategories() {
        try {
            this.categories = await api.get("/transactions/categories");
            const sel = document.getElementById("filter-category");
            if (sel) {
                sel.innerHTML = '<option value="">All Categories</option>' +
                    this.categories.map(c => `<option value="${c.id}">${c.icon || ''} ${c.name}</option>`).join("");
            }
        } catch { /* ignore */ }
    },

    bindFilters() {
        document.getElementById("apply-filters")?.addEventListener("click", () => {
            this.currentPage = 1;
            this.load();
        });
        document.getElementById("reset-filters")?.addEventListener("click", () => {
            document.querySelectorAll(".filters input, .filters select").forEach(el => el.value = "");
            this.currentPage = 1;
            this.load();
        });
    },

    getFilters() {
        const p = new URLSearchParams();
        const v = (id) => document.getElementById(id)?.value || "";
        if (v("filter-search"))    p.set("search", v("filter-search"));
        if (v("filter-merchant"))  p.set("merchant", v("filter-merchant"));
        if (v("filter-category"))  p.set("category_id", v("filter-category"));
        if (v("filter-type"))      p.set("txn_type", v("filter-type"));
        if (v("filter-date-from")) p.set("date_from", v("filter-date-from"));
        if (v("filter-date-to"))   p.set("date_to", v("filter-date-to"));
        if (v("filter-amount-min"))p.set("amount_min", v("filter-amount-min"));
        if (v("filter-amount-max"))p.set("amount_max", v("filter-amount-max"));
        p.set("sort_by", this.sortBy);
        p.set("sort_dir", this.sortDir);
        p.set("page", this.currentPage);
        p.set("per_page", this.perPage);
        return p.toString();
    },

    async load() {
        try {
            const data = await api.get(`/transactions?${this.getFilters()}`);
            this.render(data);
        } catch (err) {
            toast.error(err.message);
        }
    },

    render(data) {
        const tbody = document.getElementById("txn-tbody");
        if (!tbody) return;

        // Reset select-all checkbox
        const selectAll = document.getElementById("select-all");
        if (selectAll) selectAll.checked = false;
        this.updateBulkBar();

        if (!data.transactions.length) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No transactions found</td></tr>';
        } else {
            tbody.innerHTML = data.transactions.map(t => `
                <tr>
                    <td><input type="checkbox" class="txn-checkbox" value="${t.id}" onclick="txns.updateBulkBar()"></td>
                    <td>${t.date}</td>
                    <td>${t.description || '—'}</td>
                    <td><input type="text" class="merchant-input" data-id="${t.id}" value="${(t.merchant || '').replace(/"/g, '&quot;')}" placeholder="—" style="background:transparent;border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;width:100%;font-size:.85rem;"></td>
                    <td>
                        <select class="cat-select" data-id="${t.id}" style="padding:4px 8px;font-size:.85rem;">
                            <option value="">—</option>
                            ${this.categories.map(c =>
                                `<option value="${c.id}" ${c.id === t.category_id ? 'selected' : ''}>${c.icon || ''} ${c.name}</option>`
                            ).join("")}
                        </select>
                    </td>
                    <td class="text-right">${Number(t.amount).toLocaleString(undefined, {minimumFractionDigits:2})}</td>
                    <td><span class="badge badge-${t.txn_type}">${t.txn_type}</span></td>
                    <td class="text-right">${t.balance != null ? Number(t.balance).toLocaleString(undefined,{minimumFractionDigits:2}) : '—'}</td>
                    <td>${t.currency || ''}</td>
                </tr>
            `).join("");
        }

        // Category quick-edit
        tbody.querySelectorAll(".cat-select").forEach(sel => {
            sel.addEventListener("change", async (e) => {
                const txnId = e.target.dataset.id;
                const catId = e.target.value ? Number(e.target.value) : null;
                try {
                    await api.patch(`/transactions/${txnId}`, { category_id: catId });
                    toast.success("Category updated");
                } catch (err) { toast.error(err.message); }
            });
        });

        // Merchant inline-edit (save on blur or Enter)
        tbody.querySelectorAll(".merchant-input").forEach(inp => {
            const save = async (e) => {
                const txnId = e.target.dataset.id;
                const merchant = e.target.value.trim() || null;
                try {
                    await api.patch(`/transactions/${txnId}`, { merchant });
                    toast.success("Merchant updated");
                } catch (err) { toast.error(err.message); }
            };
            inp.addEventListener("blur", save);
            inp.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); inp.blur(); } });
        });

        // Pagination
        this.renderPagination(data);
    },

    /* ── Bulk selection helpers ──────────────────── */

    getSelectedIds() {
        return [...document.querySelectorAll(".txn-checkbox:checked")].map(cb => Number(cb.value));
    },

    toggleSelectAll(master) {
        document.querySelectorAll(".txn-checkbox").forEach(cb => cb.checked = master.checked);
        this.updateBulkBar();
    },

    updateBulkBar() {
        const ids = this.getSelectedIds();
        const bar = document.getElementById("bulk-bar");
        const count = document.getElementById("bulk-count");
        if (bar) bar.style.display = ids.length ? "block" : "none";
        if (count) count.textContent = `${ids.length} selected`;
    },

    clearSelection() {
        document.querySelectorAll(".txn-checkbox").forEach(cb => cb.checked = false);
        const selectAll = document.getElementById("select-all");
        if (selectAll) selectAll.checked = false;
        this.updateBulkBar();
    },

    async bulkDeleteSelected() {
        const ids = this.getSelectedIds();
        if (!ids.length) return;
        if (!confirm(`Delete ${ids.length} selected transaction(s)?`)) return;
        try {
            const res = await api.post("/transactions/bulk-delete", { ids });
            toast.success(`Deleted ${res.deleted} transaction(s)`);
            this.load();
        } catch (err) { toast.error(err.message); }
    },

    async bulkDeleteFiltered() {
        if (!confirm("Delete ALL transactions matching current filters? This cannot be undone.")) return;
        const body = { all: true };
        const v = (id) => document.getElementById(id)?.value || "";
        if (v("filter-search"))    body.search = v("filter-search");
        if (v("filter-merchant"))  body.merchant = v("filter-merchant");
        if (v("filter-category"))  body.category_id = v("filter-category");
        if (v("filter-type"))      body.txn_type = v("filter-type");
        if (v("filter-date-from")) body.date_from = v("filter-date-from");
        if (v("filter-date-to"))   body.date_to = v("filter-date-to");
        if (v("filter-amount-min"))body.amount_min = v("filter-amount-min");
        if (v("filter-amount-max"))body.amount_max = v("filter-amount-max");
        try {
            const res = await api.post("/transactions/bulk-delete", body);
            toast.success(`Deleted ${res.deleted} transaction(s)`);
            this.currentPage = 1;
            this.load();
        } catch (err) { toast.error(err.message); }
    },

    renderPagination(data) {
        const el = document.getElementById("pagination");
        if (!el) return;
        el.innerHTML = `
            <button ${data.page <= 1 ? 'disabled' : ''} onclick="txns.goPage(${data.page - 1})">← Prev</button>
            <span class="page-info">Page ${data.page} of ${data.total_pages} (${data.total} results)</span>
            <button ${data.page >= data.total_pages ? 'disabled' : ''} onclick="txns.goPage(${data.page + 1})">Next →</button>
        `;
    },

    goPage(p) {
        this.currentPage = p;
        this.load();
    },

    sort(col) {
        if (this.sortBy === col) {
            this.sortDir = this.sortDir === "asc" ? "desc" : "asc";
        } else {
            this.sortBy = col;
            this.sortDir = "desc";
        }
        this.currentPage = 1;
        this.load();
    },
};
