const Api = (() => {
  async function request(url, options = {}) {
    const resp = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: resp.statusText }));
      throw new Error(err.error || "Erreur reseau");
    }
    return resp.json();
  }

  return {
    getJobs(params) {
      const qs = new URLSearchParams();
      Object.entries(params || {}).forEach(([key, value]) => {
        if (value === undefined || value === null || value === "") return;
        if (Array.isArray(value)) {
          value.forEach((v) => qs.append(key, v));
        } else {
          qs.append(key, value);
        }
      });
      return request(`/api/jobs/today?${qs.toString()}`);
    },
    getJob(id) {
      return request(`/api/jobs/${id}`);
    },
    generateCvLetter(id) {
      return request(`/api/jobs/${id}/generate-cv-letter`, { method: "POST" });
    },
    apply(id, status = "applied") {
      return request(`/api/jobs/${id}/apply`, {
        method: "POST",
        body: JSON.stringify({ status, date: new Date().toISOString().slice(0, 10) }),
      });
    },
    setStatus(id, status, notes) {
      const body = {};
      if (status !== undefined) body.status = status;
      if (notes !== undefined) body.notes = notes;
      return request(`/api/jobs/${id}/status`, {
        method: "POST",
        body: JSON.stringify(body),
      });
    },
    getDailyStats() {
      return request("/api/stats/daily");
    },
    getInsights() {
      return request("/api/insights");
    },
    getAnalysis(id) {
      return request(`/api/jobs/${id}/analysis`);
    },
    saveJob(id) {
      return request(`/api/jobs/${id}/save`, { method: "POST" });
    },
    createJob(payload) {
      return request(`/api/jobs`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    rejectJob(id, reason) {
      return request(`/api/jobs/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
    },
    getProfile() {
      return request("/api/profile");
    },
    getDataSources() {
      return request("/api/data-sources");
    },
    runScrape() {
      return request("/api/scrape/run", { method: "POST" });
    },
    getScrapeStatus(taskId) {
      return request(`/api/scrape/status/${taskId}`);
    },
    downloadCvUrl(id) {
      return `/api/jobs/${id}/download-cv`;
    },
    downloadLetterUrl(id) {
      return `/api/jobs/${id}/download-letter`;
    },
  };
})();
