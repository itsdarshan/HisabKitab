/**
 * HisabKitab – Imports module
 * File upload + job status polling
 */

const imports = {
    pollTimers: {},

    /** Initialise upload page */
    init() {
        auth.guard();
        auth.setUserInfo();
        this.bindUpload();
        this.loadJobs();
    },

    /** Bind drag-drop and click upload */
    bindUpload() {
        const area = document.getElementById("upload-area");
        const input = document.getElementById("file-input");
        if (!area || !input) return;

        area.addEventListener("click", () => input.click());
        area.addEventListener("dragover", (e) => { e.preventDefault(); area.classList.add("dragover"); });
        area.addEventListener("dragleave", () => area.classList.remove("dragover"));
        area.addEventListener("drop", (e) => {
            e.preventDefault();
            area.classList.remove("dragover");
            if (e.dataTransfer.files.length) this.uploadFile(e.dataTransfer.files[0]);
        });
        input.addEventListener("change", () => {
            if (input.files.length) this.uploadFile(input.files[0]);
        });
    },

    /** Upload a single PDF */
    async uploadFile(file) {
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            toast.error("Please upload a PDF file");
            return;
        }
        const fd = new FormData();
        fd.append("file", file);
        try {
            const data = await api.upload("/imports/upload", fd);
            toast.success(`Uploaded ${file.name} – processing started`);
            this.loadJobs();
            this.startPolling(data.job_id);
        } catch (err) {
            toast.error(err.message);
        }
    },

    /** Load all jobs into the table */
    async loadJobs() {
        try {
            const jobs = await api.get("/imports/jobs");
            const tbody = document.getElementById("jobs-tbody");
            if (!tbody) return;
            tbody.innerHTML = jobs.map(j => `
                <tr>
                    <td>${j.original_filename}</td>
                    <td>${j.page_count ?? '—'}</td>
                    <td><span class="status-${j.status}">${j.status}</span></td>
                    <td>${j.error_message || '—'}</td>
                    <td>${new Date(j.created_at).toLocaleString()}</td>
                    <td>${j.completed_at ? new Date(j.completed_at).toLocaleString() : '—'}</td>
                </tr>
            `).join("");

            // Auto-poll any running/queued jobs
            jobs.filter(j => j.status === "queued" || j.status === "running")
                .forEach(j => this.startPolling(j.job_id));
        } catch (err) {
            toast.error(err.message);
        }
    },

    /** Poll a job until it finishes */
    startPolling(jobId) {
        if (this.pollTimers[jobId]) return;
        this.pollTimers[jobId] = setInterval(async () => {
            try {
                const job = await api.get(`/imports/jobs/${jobId}`);
                if (job.status === "completed" || job.status === "failed") {
                    clearInterval(this.pollTimers[jobId]);
                    delete this.pollTimers[jobId];
                    if (job.status === "completed") {
                        toast.success(`Import complete – ${job.transaction_count} transactions added`);
                    } else {
                        toast.error(`Import failed: ${job.error_message}`);
                    }
                    this.loadJobs();
                }
            } catch { /* ignore polling errors */ }
        }, 3000);
    },
};
