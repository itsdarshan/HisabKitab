/**
 * HisabKitab – Analytics module
 * Monthly trend, category breakdown, merchant ranking, cashflow
 */

const analytics = {
    async init() {
        auth.guard();
        auth.setUserInfo();
        this.bindFilters();
        await this.loadAll();
    },

    bindFilters() {
        document.getElementById("apply-analytics-filters")?.addEventListener("click", () => this.loadAll());
    },

    getDateParams() {
        const p = new URLSearchParams();
        const from = document.getElementById("analytics-date-from")?.value;
        const to   = document.getElementById("analytics-date-to")?.value;
        if (from) p.set("date_from", from);
        if (to)   p.set("date_to", to);
        return p.toString();
    },

    async loadAll() {
        await Promise.all([
            this.loadCashflow(),
            this.loadMonthly(),
            this.loadCategories(),
            this.loadMerchants(),
        ]);
    },

    /* ── Cashflow summary ──────────────────────────── */
    async loadCashflow() {
        try {
            const dp = this.getDateParams();
            const data = await api.get(`/analytics/cashflow?${dp}`);
            const el = document.getElementById("cashflow-stats");
            if (!el) return;

            const fmt = (v) => (v ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
            el.innerHTML = `
                <div class="stat-card">
                    <div class="value" style="color:var(--success)">$${fmt(data.total_income)}</div>
                    <div class="label">Total Income</div>
                </div>
                <div class="stat-card">
                    <div class="value" style="color:var(--danger)">$${fmt(data.total_expense)}</div>
                    <div class="label">Total Expense</div>
                </div>
                <div class="stat-card">
                    <div class="value" style="color:${data.net >= 0 ? 'var(--success)' : 'var(--danger)'}">$${fmt(data.net)}</div>
                    <div class="label">Net</div>
                </div>
                <div class="stat-card">
                    <div class="value">${data.period_from || '—'}</div>
                    <div class="label">From</div>
                </div>
                <div class="stat-card">
                    <div class="value">${data.period_to || '—'}</div>
                    <div class="label">To</div>
                </div>
            `;
        } catch (err) { toast.error(err.message); }
    },

    /* ── Monthly trend ─────────────────────────────── */
    async loadMonthly() {
        try {
            const data = await api.get("/analytics/monthly?months=12");
            const el = document.getElementById("monthly-table");
            if (!el) return;

            const fmt = (v) => (v ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
            const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const fmtMonth = (m) => { const p = (m || '').split('-'); return (MON[parseInt(p[1],10)-1] || p[1]) + ' ' + p[0]; };
            el.innerHTML = `
                <table>
                    <thead><tr><th>Month</th><th class="text-right">Spent</th><th class="text-right">Received</th><th class="text-right">Net</th></tr></thead>
                    <tbody>
                        ${data.map(r => `
                            <tr>
                                <td>${fmtMonth(r.month)}</td>
                                <td class="text-right" style="color:var(--danger)">${fmt(r.total_debit)}</td>
                                <td class="text-right" style="color:var(--success)">${fmt(r.total_credit)}</td>
                                <td class="text-right" style="color:${r.net >= 0 ? 'var(--success)':'var(--danger)'}">${fmt(r.net)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;

            // Simple bar chart
            this.renderMonthlyChart(data.reverse());
        } catch (err) { toast.error(err.message); }
    },

    renderMonthlyChart(data) {
        const el = document.getElementById("monthly-chart");
        if (!el || !data.length) return;

        const max = Math.max(...data.map(r => Math.max(r.total_debit || 0, r.total_credit || 0)), 1);
        el.innerHTML = `
            <div style="display:flex;align-items:flex-end;gap:6px;height:200px;padding-top:20px;">
                ${data.map(r => {
                    const dH = ((r.total_debit || 0) / max * 160);
                    const cH = ((r.total_credit || 0) / max * 160);
                    return `
                        <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">
                            <div style="display:flex;gap:2px;align-items:flex-end;height:170px;">
                                <div style="width:12px;background:var(--danger);border-radius:3px 3px 0 0;height:${dH}px;" title="Spent: ${r.total_debit}"></div>
                                <div style="width:12px;background:var(--success);border-radius:3px 3px 0 0;height:${cH}px;" title="Received: ${r.total_credit}"></div>
                            </div>
                            <span style="font-size:.7rem;color:var(--text-muted);writing-mode:vertical-rl;transform:rotate(180deg);max-height:50px;overflow:hidden;">${(() => { const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']; const p=r.month.split('-'); return (MON[parseInt(p[1],10)-1]||p[1])+' '+p[0].slice(2); })()}</span>
                        </div>
                    `;
                }).join("")}
            </div>
            <div style="display:flex;gap:16px;justify-content:center;margin-top:12px;font-size:.8rem;">
                <span><span style="display:inline-block;width:10px;height:10px;background:var(--danger);border-radius:2px;"></span> Spent</span>
                <span><span style="display:inline-block;width:10px;height:10px;background:var(--success);border-radius:2px;"></span> Received</span>
            </div>
        `;
    },

    /* ── Category breakdown ────────────────────────── */
    async loadCategories() {
        try {
            const dp = this.getDateParams();
            const data = await api.get(`/analytics/categories?${dp}`);
            const el = document.getElementById("category-table");
            if (!el) return;

            const total = data.reduce((s, r) => s + (r.total || 0), 0) || 1;
            const fmt = (v) => (v ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 });

            el.innerHTML = `
                <!-- Simple horizontal bar breakdown -->
                <div style="display:flex;height:32px;border-radius:6px;overflow:hidden;margin-bottom:16px;">
                    ${data.map(r => `
                        <div style="width:${(r.total/total*100).toFixed(1)}%;background:${r.color || '#666'};min-width:2px;"
                             title="${r.category_name}: $${fmt(r.total)}"></div>
                    `).join("")}
                </div>
                <table>
                    <thead><tr><th>Category</th><th class="text-right">Total</th><th class="text-right">Count</th><th class="text-right">%</th></tr></thead>
                    <tbody>
                        ${data.map(r => `
                            <tr>
                                <td>${r.icon || ''} ${r.category_name}</td>
                                <td class="text-right">$${fmt(r.total)}</td>
                                <td class="text-right">${r.count}</td>
                                <td class="text-right">${(r.total/total*100).toFixed(1)}%</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
        } catch (err) { toast.error(err.message); }
    },

    /* ── Merchant ranking ──────────────────────────── */
    async loadMerchants() {
        try {
            const dp = this.getDateParams();
            const data = await api.get(`/analytics/merchants?limit=20&${dp}`);
            const el = document.getElementById("merchant-table");
            if (!el) return;

            const max = data.length ? data[0].total : 1;
            const fmt = (v) => (v ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 });

            el.innerHTML = `
                <table>
                    <thead><tr><th>#</th><th>Merchant</th><th class="text-right">Total</th><th class="text-right">Txns</th><th>Bar</th></tr></thead>
                    <tbody>
                        ${data.map((r, i) => `
                            <tr>
                                <td>${i + 1}</td>
                                <td>${r.merchant}</td>
                                <td class="text-right">$${fmt(r.total)}</td>
                                <td class="text-right">${r.count}</td>
                                <td style="width:200px;">
                                    <div style="height:14px;background:var(--primary);border-radius:3px;width:${(r.total/max*100).toFixed(0)}%;opacity:.7;"></div>
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
        } catch (err) { toast.error(err.message); }
    },
};
