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
    getJobScores(id) {
      return request(`/api/jobs/${id}/scores`);
    },
    getPathStats() {
      return request("/api/path-stats");
    },
    getCareerAdvice() {
      return request("/api/career-advice");
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
