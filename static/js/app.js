(() => {
  const PAGE_SIZE = 10;
  let state = { page: 1, total: 0, jobs: [], path: "" };

  const feedEl = document.getElementById("jobs-feed");
  const emptyEl = document.getElementById("jobs-empty");
  const countEl = document.getElementById("jobs-count");
  const pageIndicator = document.getElementById("page-indicator");

  const ICONS = {
    mapPin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>',
    externalLink: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6"/><path d="M10 14 21 3"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
    sparkle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 4.6L18.5 9l-4.6 1.9L12 15.5l-1.9-4.6L5.5 9l4.6-1.4L12 3z"/></svg>',
    link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.07 0l2.83-2.83a5 5 0 0 0-7.07-7.07l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.07 0L4.1 13.83a5 5 0 0 0 7.07 7.07l1.5-1.5"/></svg>',
    trend: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>',
    refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>',
  };

  const STATUS_LABELS = {
    new: "Non candidate",
    applied: "Candidate",
    interview: "Entretien",
    offer: "Offre",
    rejected: "Refuse",
  };

  function scoreTier(score) {
    if (score >= 90) return "score-high";
    if (score >= 75) return "score-good";
    if (score >= 60) return "score-mid";
    return "score-low";
  }
  const SCORE_QUALIFIER = { "score-high": "Excellent match", "score-good": "Bon match", "score-mid": "Match correct", "score-low": "Match faible" };

  function fmtSalary(min, max) {
    if (!min && !max) return "Selon profil";
    if (min && max) return `${Math.round(min / 1000)}-${Math.round(max / 1000)}k€`;
    return `${Math.round((min || max) / 1000)}k€`;
  }

  function relativeDate(iso) {
    if (!iso) return "";
    const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
    if (days <= 0) return "aujourd'hui";
    if (days === 1) return "hier";
    return `il y a ${days} j`;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  function scoreRing(score, tier) {
    const r = 20;
    const c = 2 * Math.PI * r;
    const offset = c * (1 - Math.max(0, Math.min(100, score)) / 100);
    return `
      <div class="score-ring ${tier}">
        <svg viewBox="0 0 48 48">
          <circle class="track" cx="24" cy="24" r="${r}"></circle>
          <circle class="value" cx="24" cy="24" r="${r}" stroke-dasharray="${c}" stroke-dashoffset="${offset}"></circle>
        </svg>
        <span class="score-ring-label tnum">${Math.round(score)}</span>
      </div>
    `;
  }

  function companyAvatar(company) {
    const initial = (company || "?").trim().charAt(0).toUpperCase();
    return `<span class="company-avatar">${initial}</span>`;
  }

  function pathScoreRow(job) {
    const a = Math.round(job.path_a_score || 0);
    const b = Math.round(job.path_b_score || 0);
    const primary = job.primary_path;
    return `
      <div class="path-score-row">
        <span class="path-score-chip ${primary === "A" ? "is-lead" : ""}">Path A <span class="path-score-value tnum">${a}</span></span>
        <span class="path-score-chip ${primary === "B" ? "is-lead" : ""}">Path B <span class="path-score-value tnum">${b}</span></span>
        ${primary === "both" ? `<span class="path-score-chip path-badge-cross">Cross-fit</span>` : ""}
      </div>
    `;
  }

  function jobCard(job) {
    const tier = scoreTier(job.score);
    const isApplied = job.status !== "new";
    const desc = job.job_description || "";
    return `
      <article class="job-card ${tier} ${isApplied ? "is-applied" : ""}" data-id="${job.id}">
        <div class="job-card-head">
          <div class="job-card-title-wrap">
            <h3 class="job-card-title">${job.job_title}</h3>
            <div class="job-card-meta">
              ${companyAvatar(job.company)}
              <span>${job.company}</span>
              <span class="sep">·</span>
              <span class="tnum">${fmtSalary(job.salary_min, job.salary_max)}</span>
              <span class="sep">·</span>
              ${ICONS.mapPin}
              <span>${job.location || "-"}</span>
            </div>
            <div class="job-card-chips">
              ${job.sector ? `<span class="badge badge-sector">${job.sector}</span>` : ""}
              <span class="badge badge-sector">${relativeDate(job.date_found)}</span>
              ${isApplied ? `<span class="status-pill status-${job.status}">${STATUS_LABELS[job.status] || job.status}</span>` : ""}
            </div>
            ${pathScoreRow(job)}
          </div>
          <div>
            ${scoreRing(job.score, tier)}
            <div class="score-qualifier ${tier}">${SCORE_QUALIFIER[tier]}</div>
          </div>
        </div>
        <p class="job-card-desc">${desc.slice(0, 180)}${desc.length > 180 ? "…" : ""}</p>
        <div class="job-card-actions">
          <button class="btn btn-primary" data-action="generate" data-id="${job.id}">
            ${ICONS.sparkle} Générer CV &amp; LM
          </button>
          <button class="btn btn-secondary" data-action="apply" data-id="${job.id}" ${isApplied ? "disabled" : ""}>
            ${isApplied ? "Candidaté" : "Marquer candidature"}
          </button>
          <div class="job-card-actions-secondary">
            <button class="btn btn-ghost btn-sm" data-action="details" data-id="${job.id}">Détails</button>
            <a href="${job.job_url}" target="_blank" rel="noopener" class="job-card-link" title="Ouvre l'offre originale sur ${job.source || "la source"}">Voir l'offre ${ICONS.externalLink}</a>
          </div>
        </div>
      </article>
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
    pageIndicator.textContent = `Page ${state.page} sur ${totalPages}`;
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

  function updateFiltersBadge() {
    const n = Filters.countActive();
    const badge = document.getElementById("filters-count-badge");
    const resetBtn = document.getElementById("btn-reset");
    if (n > 0) {
      badge.textContent = n;
      badge.classList.remove("visually-hidden");
      resetBtn.style.visibility = "visible";
    } else {
      badge.classList.add("visually-hidden");
      resetBtn.style.visibility = "hidden";
    }
  }

  async function loadJobs() {
    updateFiltersBadge();
    const f = Filters.read();
    const params = {
      sector: f.sector,
      location: f.location,
      min_salary: f.min_salary,
      score: f.score,
      status: f.status,
      path: state.path || undefined,
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
      document.getElementById("stat-salary").textContent = stats.avg_salary ? `${Math.round(stats.avg_salary / 1000)}k€` : "-";
      document.getElementById("stat-top").textContent = stats.top_matches;
      document.getElementById("stat-applied").textContent = stats.applied;

      const deltaEl = document.getElementById("stat-total-delta");
      if (stats.total_jobs_delta > 0) {
        deltaEl.textContent = `+${stats.total_jobs_delta} depuis hier`;
        deltaEl.classList.add("is-positive");
      } else if (stats.total_jobs_delta < 0) {
        deltaEl.textContent = `${stats.total_jobs_delta} depuis hier`;
        deltaEl.classList.remove("is-positive");
      } else {
        deltaEl.textContent = "Stable depuis hier";
        deltaEl.classList.remove("is-positive");
      }

      document.getElementById("stat-salary-delta").textContent = stats.market_median_salary
        ? `Médiane marché : ${Math.round(stats.market_median_salary / 1000)}k€`
        : "Médiane marché : -";

      const appliedDeltaEl = document.getElementById("stat-applied-delta");
      if (stats.applied === 0) {
        appliedDeltaEl.innerHTML = `<button class="stat-cta" id="stat-applied-cta">Marquer une première candidature →</button>`;
        document.getElementById("stat-applied-cta").addEventListener("click", () => {
          document.getElementById("filter-status").value = "new";
          state.page = 1;
          loadJobs();
        });
      } else {
        appliedDeltaEl.textContent = `${stats.applied_total} au total`;
      }

      document.getElementById("sync-status").textContent = `Synchronisé — ${stats.total_jobs} offre(s) aujourd'hui`;
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

  function statusOption(value, current) {
    return `<option value="${value}" ${value === current ? "selected" : ""}>${STATUS_LABELS[value]}</option>`;
  }

  function openModal(job) {
    const modal = document.getElementById("job-modal");
    const tier = scoreTier(job.score);
    document.getElementById("modal-content").innerHTML = `
      <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px; padding-right:40px;">
        <div>
          <h2 style="font-size:20px; font-weight:700; color:var(--color-text-primary); margin:0;">${job.job_title}</h2>
          <div class="job-card-meta" style="margin-top:8px;">
            ${companyAvatar(job.company)}
            <span>${job.company}</span>
            <span class="sep">·</span>
            <span class="tnum">${fmtSalary(job.salary_min, job.salary_max)}</span>
            <span class="sep">·</span>
            ${ICONS.mapPin}<span>${job.location || "-"}</span>
          </div>
        </div>
        ${scoreRing(job.score, tier)}
      </div>
      <div class="job-card-chips" style="margin-top:12px;">
        <span class="badge badge-sector">Source : ${job.source || "-"}</span>
        <span class="badge badge-sector">Trouvé le ${job.date_found}</span>
        ${job.status !== "new" ? `<span class="status-pill status-${job.status}">${STATUS_LABELS[job.status]}</span>` : ""}
      </div>
      <p style="font-size:14px; line-height:1.65; color:var(--color-text-secondary); margin-top:16px; white-space:pre-line; max-width:68ch;">${job.job_description || "Pas de description disponible."}</p>
      <div style="margin-top:16px;">
        <div class="section-label" style="margin-bottom:8px;">Détail du score</div>
        <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:8px; font-size:12px; color:var(--color-text-secondary);">
          <div>Salaire : <strong class="tnum">${job.score_salary}</strong>/25</div>
          <div>Poste : <strong class="tnum">${job.score_job_match}</strong>/30</div>
          <div>Secteur : <strong class="tnum">${job.score_sector}</strong>/15</div>
          <div>Localisation : <strong class="tnum">${job.score_location}</strong>/10</div>
          <div>Notoriété : <strong class="tnum">${job.score_notoriety}</strong>/12</div>
          <div>Bonus : <strong class="tnum">${job.score_bonus}</strong>/8</div>
        </div>
      </div>
      <div id="decision-widget-slot">Chargement de l'analyse dual-path…</div>

      <div class="job-card-actions" style="margin-top:20px;">
        <button class="btn btn-primary" data-action="generate" data-id="${job.id}">${ICONS.sparkle} Générer CV &amp; LM</button>
      </div>
      <div id="modal-downloads" class="job-card-actions ${job.cv_adapted_path ? "" : "hidden"}" style="margin-top:8px;">
        <a class="btn btn-ghost btn-sm" href="${Api.downloadCvUrl(job.id)}">Télécharger le CV (PDF)</a>
        <a class="btn btn-ghost btn-sm" href="${Api.downloadLetterUrl(job.id)}">Télécharger la lettre (DOCX)</a>
      </div>

      <div class="link-box">
        <div class="link-box-title">Suivi de candidature</div>
        <div style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-bottom:8px;">
          <select id="modal-status-select" class="select-control" style="width:auto;">
            ${Object.keys(STATUS_LABELS).map((s) => statusOption(s, job.status)).join("")}
          </select>
          ${job.date_applied ? `<span style="font-size:12px; color:var(--color-text-tertiary);">Candidaté le ${job.date_applied}</span>` : ""}
        </div>
        <textarea id="modal-notes" rows="3" class="text-input" style="width:100%;"
          placeholder="Notes personnelles (entretien prévu, contact, feedback...)">${escapeHtml(job.notes)}</textarea>
        <button class="btn btn-primary btn-sm" style="margin-top:8px;" data-action="save-status" data-id="${job.id}">Enregistrer le suivi</button>
      </div>

      <div class="link-box">
        <div class="link-box-title">${ICONS.link} Offre originale</div>
        <div style="font-size:12px; color:var(--color-text-tertiary); margin-bottom:8px;">Source : ${job.source || "-"} · Trouvée le ${job.date_found}</div>
        <div style="display:flex; flex-wrap:wrap; gap:8px;">
          <a class="btn btn-primary btn-sm" href="${job.job_url}" target="_blank" rel="noopener">Consulter l'offre</a>
          <button class="btn btn-ghost btn-sm" data-action="copy-link" data-url="${job.job_url}">Copier le lien</button>
        </div>
      </div>
    `;
    modal.classList.add("is-open");
    document.getElementById("modal-close").focus();
    renderDecisionWidget(job.id);
  }

  function closeModal() {
    document.getElementById("job-modal").classList.remove("is-open");
  }

  function analysisList(items, cssClass) {
    return `<ul class="${cssClass}">${(items || []).map((i) => `<li>${i}</li>`).join("")}</ul>`;
  }

  async function renderDecisionWidget(jobId) {
    const slot = document.getElementById("decision-widget-slot");
    if (!slot) return; // modal was closed/replaced before this resolved
    try {
      const data = await Api.getJobScores(jobId);
      const { path_a, path_b, recommendation } = data;
      const leadPath = path_a.score >= path_b.score ? "Path A (Product/AMOA)" : "Path B (Sales Engineer)";

      slot.outerHTML = `
        <div class="decision-widget" id="decision-widget-slot">
          <div class="section-label">Should I apply? — Decision helper</div>
          <div class="decision-widget-row"><span>Path A (Product/AMOA)</span><strong class="tnum">${path_a.score}/100</strong></div>
          <div class="decision-widget-row"><span>Path B (Sales Engineer)</span><strong class="tnum">${path_b.score}/100</strong></div>
          <div class="decision-widget-row"><span>Recommandé pour</span><strong>${leadPath}</strong></div>
          <div class="decision-verdict">${ICONS.check} ${recommendation}</div>
        </div>

        <div class="path-analysis-grid">
          <div class="path-analysis-card">
            <h4>Path A · Product/AMOA</h4>
            <div class="section-label">Avantages</div>
            ${analysisList(path_a.advantages, "advantages")}
            <div class="section-label">Inconvénients</div>
            ${analysisList(path_a.disadvantages, "disadvantages")}
            <div class="advice">${path_a.advice || ""}</div>
          </div>
          <div class="path-analysis-card">
            <h4>Path B · Sales Engineer</h4>
            <div class="section-label">Avantages</div>
            ${analysisList(path_b.advantages, "advantages")}
            <div class="section-label">Inconvénients</div>
            ${analysisList(path_b.disadvantages, "disadvantages")}
            <div class="advice">${path_b.advice || ""}</div>
          </div>
        </div>
      `;
    } catch (e) {
      slot.textContent = "Analyse dual-path indisponible.";
    }
  }

  function barRow(label, value, maxValue, valueLabel) {
    const pct = maxValue > 0 ? Math.max(4, Math.round((value / maxValue) * 100)) : 0;
    return `
      <div class="insight-row">
        <div class="insight-label" title="${label}">${label}</div>
        <div class="insight-bar-track"><div class="insight-bar-fill" style="width:${pct}%"></div></div>
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
      <h2 style="font-size:20px; font-weight:700; margin:0 0 4px; color:var(--color-text-primary);">Tendances du marché</h2>
      <p style="font-size:12px; color:var(--color-text-tertiary); margin:0 0 20px;">${data.total_applied || 0} candidature(s) au total</p>

      <div class="section-label">Salaire moyen par secteur</div>
      ${bySector.length
        ? bySector.map((r) => barRow(r.sector, r.avg_salary, maxSalary, `${Math.round(r.avg_salary / 1000)}k (${r.count})`)).join("")
        : `<p style="font-size:13px; color:var(--color-text-tertiary);">Pas encore assez de données salariales par secteur.</p>`}

      <div class="section-label" style="margin-top:20px;">Entreprises qui recrutent le plus</div>
      ${companies.length
        ? companies.map((r) => barRow(r.company, r.count, maxCompanyCount, `${r.count} offre(s) · score moy. ${Math.round(r.avg_score)}`)).join("")
        : `<p style="font-size:13px; color:var(--color-text-tertiary);">Pas encore de données.</p>`}

      <div class="section-label" style="margin-top:20px;">Offres trouvées (14 derniers jours)</div>
      ${trendAsc.length
        ? `<div class="sparkline">
            ${trendAsc.map((r) => `<div class="sparkline-bar" style="height:${Math.max(6, Math.round((r.count / maxTrendCount) * 100))}%" title="${r.date_found} : ${r.count} offre(s)"></div>`).join("")}
          </div>`
        : `<p style="font-size:13px; color:var(--color-text-tertiary);">Pas encore d'historique.</p>`}
    `;
  }

  async function openInsights() {
    const modal = document.getElementById("job-modal");
    document.getElementById("modal-content").innerHTML = `<p>Chargement des tendances…</p>`;
    modal.classList.add("is-open");
    try {
      const data = await Api.getInsights();
      document.getElementById("modal-content").innerHTML = renderInsightsHtml(data);
    } catch (e) {
      document.getElementById("modal-content").innerHTML = `<p>Erreur de chargement des tendances : ${e.message}</p>`;
    }
  }

  function starRating(pct) {
    const filled = Math.max(1, Math.round(pct / 20));
    return "★".repeat(filled) + "☆".repeat(5 - filled);
  }

  async function openComparison() {
    const modal = document.getElementById("job-modal");
    document.getElementById("modal-content").innerHTML = `<p>Chargement de la comparaison…</p>`;
    modal.classList.add("is-open");
    try {
      const s = await Api.getPathStats();
      const fp = s.financial_projection;
      document.getElementById("modal-content").innerHTML = `
        <h2 style="font-size:20px; font-weight:700; margin:0 0 4px; color:var(--color-text-primary);">Career Path Comparison</h2>
        <p style="font-size:12px; color:var(--color-text-tertiary); margin:0 0 20px;">Path A (Product/AMOA) vs Path B (Sales Engineer) — ${s.cross_fit_count} offre(s) cross-fit</p>
        <div class="comparison-grid">
          <div class="comparison-card">
            <div class="section-label">Path A · Product/AMOA</div>
            <div class="n tnum">${s.path_a.count}</div>
            <div style="font-size:12px; color:var(--color-text-tertiary);">opportunités (score &gt; 50)</div>
            <table class="comparison-table">
              <tr><td>Score moyen</td><td>${s.path_a.avg_score}/100</td></tr>
              <tr><td>Salaire moyen</td><td>${s.path_a.avg_salary ? Math.round(s.path_a.avg_salary / 1000) + "k€" : "-"}</td></tr>
              <tr><td>Projection an 1</td><td>${fp.path_a.year_1}</td></tr>
              <tr><td>Projection an 3</td><td>${fp.path_a.year_3}</td></tr>
            </table>
          </div>
          <div class="comparison-card">
            <div class="section-label">Path B · Sales Engineer</div>
            <div class="n tnum">${s.path_b.count}</div>
            <div style="font-size:12px; color:var(--color-text-tertiary);">opportunités (score &gt; 50)</div>
            <table class="comparison-table">
              <tr><td>Score moyen</td><td>${s.path_b.avg_score}/100</td></tr>
              <tr><td>Salaire moyen</td><td>${s.path_b.avg_salary ? Math.round(s.path_b.avg_salary / 1000) + "k€" : "-"}</td></tr>
              <tr><td>Projection an 1</td><td>${fp.path_b.year_1}</td></tr>
              <tr><td>Projection an 3</td><td>${fp.path_b.year_3}</td></tr>
            </table>
          </div>
        </div>
        <p style="font-size:13px; color:var(--color-text-secondary); margin-top:16px;">
          ${fp.path_a.profile} (Path A) vs ${fp.path_b.profile} (Path B).
        </p>
      `;
    } catch (e) {
      document.getElementById("modal-content").innerHTML = `<p>Erreur de chargement : ${e.message}</p>`;
    }
  }

  function advisorPathCard(path) {
    return `
      <div class="advisor-path-card">
        <h4><span>${path.label}</span><span class="advisor-stars">${starRating(path.recommendation_pct)}</span></h4>
        <div class="section-label">Avantages</div>
        ${analysisList(path.pros, "advantages")}
        <div class="section-label">Inconvénients</div>
        ${analysisList(path.cons, "disadvantages")}
        <div class="advisor-meta">
          Timeline : ${path.timeline} · Risque : ${path.risk} · Recommandé à ${path.recommendation_pct}%<br>
          ${path.current_opportunities} offre(s) actuellement, score moyen ${path.avg_score}/100
        </div>
      </div>
    `;
  }

  async function openAdvisor() {
    const modal = document.getElementById("job-modal");
    document.getElementById("modal-content").innerHTML = `<p>Chargement du conseiller carrière…</p>`;
    modal.classList.add("is-open");
    try {
      const advice = await Api.getCareerAdvice();
      document.getElementById("modal-content").innerHTML = `
        <h2 style="font-size:20px; font-weight:700; margin:0 0 8px; color:var(--color-text-primary);">Career Advisor</h2>
        <p style="font-size:13px; color:var(--color-text-secondary); margin:0 0 20px;">${advice.current_thinking}</p>
        ${advisorPathCard(advice.path_a)}
        ${advisorPathCard(advice.path_b)}
        <div class="advisor-path-card" style="background:var(--color-primary-subtle); border-color:var(--color-primary);">
          <h4><span>Hybrid strategy${advice.hybrid_strategy.recommended ? " (recommandée)" : ""}</span></h4>
          ${analysisList(advice.hybrid_strategy.steps, "advantages")}
          <div class="section-label">Pourquoi c'est sûr</div>
          ${analysisList(advice.hybrid_strategy.why_safe, "advantages")}
        </div>
        <div class="decision-verdict" style="display:block;">${advice.decision_prompt}</div>
      `;
    } catch (e) {
      document.getElementById("modal-content").innerHTML = `<p>Erreur de chargement : ${e.message}</p>`;
    }
  }

  async function handleGenerate(jobId, btn) {
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
    btn.innerHTML = `<span class="spinner"></span> Génération…`;
    try {
      await Api.generateCvLetter(jobId);
      toast("CV et lettre générés !");
      const job = await Api.getJob(jobId);
      if (document.getElementById("job-modal").classList.contains("is-open")) {
        openModal(job);
      }
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = original;
    }
  }

  async function handleApply(jobId) {
    try {
      await Api.apply(jobId);
      toast("Offre marquée comme candidatée");
      await loadJobs();
      await loadStats();
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    }
  }

  async function handleSaveStatus(jobId, btn) {
    const status = document.getElementById("modal-status-select").value;
    const notes = document.getElementById("modal-notes").value;
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Enregistrement…";
    try {
      await Api.setStatus(jobId, status, notes);
      toast("Suivi enregistré");
      const job = await Api.getJob(jobId);
      openModal(job);
      await loadJobs();
      await loadStats();
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  async function handleCopyLink(url) {
    try {
      await navigator.clipboard.writeText(url);
      toast("Lien copié !");
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
    btn.setAttribute("aria-busy", "true");
    const original = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span>`;
    try {
      const { task_id } = await Api.runScrape();

      let task;
      while (true) {
        task = await Api.getScrapeStatus(task_id);
        if (task.status === "completed" || task.status === "failed") break;
        await sleep(1200);
      }

      if (task.status === "completed") {
        const sourcesOk = task.run_log
          ? Object.values(task.run_log.sources).filter((s) => !s.error).length
          : 0;
        const sourcesTotal = task.run_log ? Object.keys(task.run_log.sources).length : 0;
        if (task.run_log && sourcesOk < sourcesTotal) {
          toast(`${task.new_jobs} offre(s) trouvée(s) — ${sourcesOk}/${sourcesTotal} sources ok`);
        } else {
          toast(`${task.new_jobs} offre(s) trouvée(s) !`);
        }
        state.page = 1;
        await loadJobs();
        await loadStats();
      } else {
        toast(`Scraping échoué : ${task.error || "erreur inconnue"}`);
      }
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      btn.innerHTML = original;
    }
  }

  function bindEvents() {
    document.getElementById("btn-refresh").addEventListener("click", handleRefresh);
    document.getElementById("btn-insights").addEventListener("click", openInsights);
    document.getElementById("btn-comparison").addEventListener("click", openComparison);
    document.getElementById("btn-advisor").addEventListener("click", openAdvisor);
    document.querySelectorAll(".path-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".path-tab").forEach((t) => {
          t.classList.remove("is-active");
          t.setAttribute("aria-selected", "false");
        });
        tab.classList.add("is-active");
        tab.setAttribute("aria-selected", "true");
        state.path = tab.dataset.path;
        state.page = 1;
        loadJobs();
      });
    });
    document.getElementById("card-top-matches").addEventListener("click", () => {
      document.getElementById("filter-score").value = "top";
      state.page = 1;
      loadJobs();
    });
    document.getElementById("card-top-matches").addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); document.getElementById("card-top-matches").click(); }
    });
    [document.getElementById("btn-reset"), document.getElementById("btn-empty-reset")].forEach((btn) => {
      btn.addEventListener("click", () => {
        Filters.reset();
        state.page = 1;
        loadJobs();
      });
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
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && document.getElementById("job-modal").classList.contains("is-open")) closeModal();
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
      } else if (el.dataset.action === "save-status") {
        handleSaveStatus(jobId, el);
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
