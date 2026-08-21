(() => {
  const PAGE_SIZE = 10;
  let state = { page: 1, total: 0, jobs: [] };

  const feedEl = document.getElementById("jobs-feed");
  const emptyEl = document.getElementById("jobs-empty");
  const countEl = document.getElementById("jobs-count");
  const pageIndicator = document.getElementById("page-indicator");

  function scoreTier(score) {
    if (score > 75) return "score-top";
    if (score >= 60) return "score-good";
    return "score-low";
  }

  function fmtSalary(min, max) {
    if (!min && !max) return "Selon profil";
    if (min && max) return `${Math.round(min / 1000)}-${Math.round(max / 1000)}k`;
    return `${Math.round((min || max) / 1000)}k`;
  }

  function jobCard(job) {
    const tier = scoreTier(job.score);
    const isApplied = job.status !== "new";
    return `
      <div class="job-card ${tier}" data-id="${job.id}">
        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <span class="score-badge ${tier}">⭐ ${Math.round(job.score)}/100</span>
            <h3 class="text-base font-semibold text-navy mt-2">${job.job_title}</h3>
            <div class="text-sm text-slate-500 mt-0.5">
              🏢 ${job.company} &nbsp;|&nbsp; 💰 ${fmtSalary(job.salary_min, job.salary_max)}
            </div>
            <div class="text-sm text-slate-500">📍 ${job.location || "-"}</div>
            ${job.sector ? `<span class="tag mt-2 inline-block">${job.sector}</span>` : ""}
          </div>
        </div>
        <p class="text-sm text-slate-600 mt-3 line-clamp-2">${(job.job_description || "").slice(0, 160)}${(job.job_description || "").length > 160 ? "…" : ""}</p>
        <div class="flex flex-wrap gap-2 mt-4">
          <button class="btn-ghost" data-action="details" data-id="${job.id}">Details</button>
          <button class="btn-primary" data-action="generate" data-id="${job.id}">📥 Generer CV &amp; LM</button>
          <button class="btn-success" data-action="apply" data-id="${job.id}" ${isApplied ? "disabled" : ""}>
            ${isApplied ? "✅ Candidate" : "Marquer candidate"}
          </button>
          <a class="link-btn" href="${job.job_url}" target="_blank" rel="noopener"
             title="Ouvre l'offre originale sur ${job.source || "la source"}">🔗 Voir l'offre</a>
        </div>
      </div>
    `;
  }

  function renderJobs() {
    if (!state.jobs.length) {
      feedEl.innerHTML = "";
      emptyEl.classList.remove("hidden");
    } else {
      emptyEl.classList.add("hidden");
      feedEl.innerHTML = state.jobs.map(jobCard).join("");
    }
    const totalPages = Math.max(1, Math.ceil(state.total / PAGE_SIZE));
    countEl.textContent = `${state.total} offre(s)`;
    pageIndicator.textContent = `Page ${state.page} of ${totalPages}`;
    document.getElementById("btn-prev").disabled = state.page <= 1;
    document.getElementById("btn-next").disabled = state.page >= totalPages;
  }

  function applyClientSort(jobs) {
    const sortBy = document.getElementById("sort-select").value;
    const copy = [...jobs];
    if (sortBy === "salary") {
      copy.sort((a, b) => (b.salary_max || b.salary_min || 0) - (a.salary_max || a.salary_min || 0));
    } else if (sortBy === "recent") {
      copy.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
    }
    return copy;
  }

  async function loadJobs() {
    const f = Filters.read();
    const params = {
      sector: f.sector,
      location: f.location,
      min_salary: f.min_salary,
      score: f.score,
      status: f.status,
      limit: PAGE_SIZE,
      offset: (state.page - 1) * PAGE_SIZE,
    };
    try {
      const data = await Api.getJobs(params);
      state.total = data.total;
      state.jobs = applyClientSort(data.jobs);
      renderJobs();
    } catch (e) {
      toast(`Erreur de chargement : ${e.message}`);
    }
  }

  async function loadStats() {
    try {
      const stats = await Api.getDailyStats();
      document.getElementById("stat-total").textContent = stats.total_jobs;
      document.getElementById("stat-salary").textContent = stats.avg_salary ? `${Math.round(stats.avg_salary / 1000)}k` : "-";
      document.getElementById("stat-top").textContent = stats.top_matches;
      document.getElementById("stat-applied").textContent = stats.applied;
    } catch (e) {
      // Non bloquant.
    }
  }

  function toast(message) {
    const el = document.getElementById("toast");
    el.textContent = message;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2500);
  }

  function openModal(job) {
    const modal = document.getElementById("job-modal");
    document.getElementById("modal-content").innerHTML = `
      <span class="score-badge ${scoreTier(job.score)}">⭐ ${Math.round(job.score)}/100</span>
      <h2 class="text-xl font-semibold text-navy mt-2">${job.job_title}</h2>
      <div class="text-sm text-slate-500 mt-1">🏢 ${job.company} | 💰 ${fmtSalary(job.salary_min, job.salary_max)} | 📍 ${job.location || "-"}</div>
      <div class="text-xs text-slate-400 mt-1">Source : ${job.source || "-"} | Trouve le ${job.date_found}</div>
      <p class="text-sm text-slate-700 mt-4 whitespace-pre-line">${job.job_description || "Pas de description disponible."}</p>
      <div class="grid grid-cols-3 gap-2 mt-4 text-xs text-slate-500">
        <div>Salaire: ${job.score_salary}/25</div>
        <div>Job match: ${job.score_job_match}/30</div>
        <div>Secteur: ${job.score_sector}/15</div>
        <div>Location: ${job.score_location}/10</div>
        <div>Notoriete: ${job.score_notoriety}/12</div>
        <div>Bonus: ${job.score_bonus}/8</div>
      </div>
      <div class="flex flex-wrap gap-2 mt-5">
        <button class="btn-primary" data-action="generate" data-id="${job.id}">📥 Generer CV &amp; LM</button>
        <button class="btn-success" data-action="apply" data-id="${job.id}" ${job.status !== "new" ? "disabled" : ""}>
          ${job.status !== "new" ? "✅ Candidate" : "Marquer candidate"}
        </button>
      </div>
      <div id="modal-downloads" class="flex gap-2 mt-3 ${job.cv_adapted_path ? "" : "hidden"}">
        <a class="btn-ghost" href="${Api.downloadCvUrl(job.id)}">⬇️ CV (PDF)</a>
        <a class="btn-ghost" href="${Api.downloadLetterUrl(job.id)}">⬇️ Lettre (DOCX)</a>
      </div>
      <div class="link-box mt-4">
        <div class="link-box-title">🔗 OFFRE ORIGINALE</div>
        <div class="text-xs text-slate-500 mb-2">Source : ${job.source || "-"} | Trouvee le ${job.date_found}</div>
        <div class="flex flex-wrap gap-2">
          <a class="btn-primary" href="${job.job_url}" target="_blank" rel="noopener">Consulter l'offre</a>
          <button class="btn-ghost" data-action="copy-link" data-url="${job.job_url}">Copier le lien</button>
        </div>
      </div>
    `;
    modal.classList.remove("hidden");
    modal.classList.add("flex");
  }

  function closeModal() {
    const modal = document.getElementById("job-modal");
    modal.classList.add("hidden");
    modal.classList.remove("flex");
  }

  function barRow(label, value, maxValue, valueLabel) {
    const pct = maxValue > 0 ? Math.max(4, Math.round((value / maxValue) * 100)) : 0;
    return `
      <div class="insight-row">
        <div class="insight-label" title="${label}">${label}</div>
        <div class="insight-bar-track">
          <div class="insight-bar-fill" style="width:${pct}%"></div>
        </div>
        <div class="insight-value">${valueLabel}</div>
      </div>
    `;
  }

  function renderInsightsHtml(data) {
    const bySector = data.salary_by_sector || [];
    const companies = data.top_companies || [];
    const trend = data.trend || [];

    const maxSalary = Math.max(1, ...bySector.map((r) => r.avg_salary || 0));
    const maxCompanyCount = Math.max(1, ...companies.map((r) => r.count || 0));
    const maxTrendCount = Math.max(1, ...trend.map((r) => r.count || 0));
    const trendAsc = [...trend].reverse();

    return `
      <h2 class="text-xl font-semibold text-navy mb-1">📊 Tendances du marche</h2>
      <p class="text-xs text-slate-400 mb-4">${data.total_applied || 0} candidature(s) au total</p>

      <h3 class="insight-title">Salaire moyen par secteur</h3>
      ${bySector.length
        ? bySector.map((r) => barRow(r.sector, r.avg_salary, maxSalary, `${Math.round(r.avg_salary / 1000)}k (${r.count})`)).join("")
        : `<p class="text-sm text-slate-400">Pas encore assez de donnees salariales par secteur.</p>`}

      <h3 class="insight-title">Entreprises qui recrutent le plus</h3>
      ${companies.length
        ? companies.map((r) => barRow(r.company, r.count, maxCompanyCount, `${r.count} offre(s) - score moy. ${Math.round(r.avg_score)}`)).join("")
        : `<p class="text-sm text-slate-400">Pas encore de donnees.</p>`}

      <h3 class="insight-title">Offres trouvees (14 derniers jours)</h3>
      ${trendAsc.length
        ? `<div class="sparkline">
            ${trendAsc.map((r) => `
              <div class="sparkline-bar" style="height:${Math.max(6, Math.round((r.count / maxTrendCount) * 100))}%" title="${r.date_found} : ${r.count} offre(s)"></div>
            `).join("")}
          </div>`
        : `<p class="text-sm text-slate-400">Pas encore d'historique.</p>`}
    `;
  }

  async function openInsights() {
    try {
      const data = await Api.getInsights();
      const modal = document.getElementById("job-modal");
      document.getElementById("modal-content").innerHTML = renderInsightsHtml(data);
      modal.classList.remove("hidden");
      modal.classList.add("flex");
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    }
  }

  async function handleGenerate(jobId, btn) {
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Generation…";
    try {
      await Api.generateCvLetter(jobId);
      toast("CV et lettre generes !");
      const job = await Api.getJob(jobId);
      if (document.getElementById("job-modal").classList.contains("flex")) {
        openModal(job);
      }
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  async function handleApply(jobId) {
    try {
      await Api.apply(jobId);
      toast("Offre marquee comme candidatee ✅");
      await loadJobs();
      await loadStats();
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    }
  }

  async function handleCopyLink(url) {
    try {
      await navigator.clipboard.writeText(url);
      toast("Lien copie !");
    } catch (e) {
      toast("Impossible de copier le lien");
    }
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function handleRefresh() {
    const btn = document.getElementById("btn-refresh");
    btn.disabled = true;
    btn.textContent = "🔄 Scraping en cours…";
    try {
      const { task_id } = await Api.runScrape();

      let task;
      while (true) {
        task = await Api.getScrapeStatus(task_id);
        if (task.progress) {
          btn.textContent = `🔄 Scraping (${task.progress.index}/${task.progress.total} sources)…`;
        }
        if (task.status === "completed" || task.status === "failed") break;
        await sleep(1200);
      }

      if (task.status === "completed") {
        const sourcesOk = task.run_log
          ? Object.values(task.run_log.sources).filter((s) => !s.error).length
          : 0;
        const sourcesTotal = task.run_log ? Object.keys(task.run_log.sources).length : 0;
        if (task.run_log && sourcesOk < sourcesTotal) {
          toast(`⚠️ ${task.new_jobs} offre(s) trouvee(s) - ${sourcesOk}/${sourcesTotal} sources ok`);
        } else {
          toast(`✅ ${task.new_jobs} offre(s) trouvee(s) !`);
        }
        state.page = 1;
        await loadJobs();
        await loadStats();
      } else {
        toast(`⚠️ Scraping echoue : ${task.error || "erreur inconnue"}`);
      }
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = "🔄 Refresh";
    }
  }

  function bindEvents() {
    document.getElementById("btn-refresh").addEventListener("click", handleRefresh);
    document.getElementById("btn-insights").addEventListener("click", openInsights);
    document.getElementById("btn-reset").addEventListener("click", () => {
      Filters.reset();
      state.page = 1;
      loadJobs();
    });
    document.getElementById("btn-prev").addEventListener("click", () => {
      if (state.page > 1) {
        state.page -= 1;
        loadJobs();
      }
    });
    document.getElementById("btn-next").addEventListener("click", () => {
      state.page += 1;
      loadJobs();
    });
    document.getElementById("sort-select").addEventListener("change", loadJobs);
    document.getElementById("modal-close").addEventListener("click", closeModal);
    document.getElementById("job-modal").addEventListener("click", (e) => {
      if (e.target.id === "job-modal") closeModal();
    });

    ["filter-sector", "filter-location"].forEach((id) => {
      document.getElementById(id).addEventListener("change", () => {
        state.page = 1;
        loadJobs();
      });
    });
    document.getElementById("filter-salary").addEventListener("change", () => {
      state.page = 1;
      loadJobs();
    });
    document.getElementById("filter-score").addEventListener("change", () => {
      state.page = 1;
      loadJobs();
    });
    document.getElementById("filter-status").addEventListener("change", () => {
      state.page = 1;
      loadJobs();
    });

    document.body.addEventListener("click", async (e) => {
      const el = e.target.closest("[data-action]");
      if (!el) return;
      const jobId = el.dataset.id;
      if (el.dataset.action === "details") {
        const job = await Api.getJob(jobId);
        openModal(job);
      } else if (el.dataset.action === "generate") {
        handleGenerate(jobId, el);
      } else if (el.dataset.action === "apply") {
        handleApply(jobId);
      } else if (el.dataset.action === "copy-link") {
        handleCopyLink(el.dataset.url);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    Filters.bindSalarySlider();
    bindEvents();
    loadJobs();
    loadStats();
  });
})();
