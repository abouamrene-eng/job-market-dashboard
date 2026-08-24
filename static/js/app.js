(() => {
  const PAGE_SIZE = 10;
  let state = { page: 1, total: 0, jobs: [], tab: "flux" };

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
    saved: "Sauvegardee",
    applied: "Candidate",
    interview: "Entretien",
    offer: "Offre",
    rejected: "Refuse",
  };

  const REJECT_REASON_LABELS = {
    pas_interesse: "Pas interesse",
    salaire_trop_bas: "Salaire trop bas",
    trop_loin: "Trop loin",
    pas_aeronautique: "Pas aeronautique",
    autre: "Autre",
  };

  const EMPTY_MESSAGES = {
    flux: "Aucune nouvelle offre pour l'instant.",
    saved: "Tu n'as encore sauvegarde aucune offre.",
    applied: "Tu n'as encore candidate a aucune offre.",
    rejected: "Aucune offre refusee.",
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

  function relativeUpdate(str) {
    if (!str) return "jamais";
    const t = new Date(str.replace(" ", "T"));
    const mins = Math.floor((Date.now() - t.getTime()) / 60000);
    if (mins < 1) return "a l'instant";
    if (mins < 60) return `il y a ${mins} min`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `il y a ${hours}h`;
    return `il y a ${Math.floor(hours / 24)}j`;
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

  function jobActions(job) {
    const s = job.status;
    const secondary = `
      <div class="job-card-actions-secondary">
        <button class="btn btn-ghost btn-sm" data-action="details" data-id="${job.id}">Détails</button>
        <a href="${job.job_url}" target="_blank" rel="noopener" class="job-card-link" title="Ouvre l'offre originale sur ${job.source || "la source"}">Voir l'offre ${ICONS.externalLink}</a>
      </div>
    `;
    if (s === "rejected") {
      return `
        <span class="status-pill status-rejected">Refusée${job.reject_reason ? " · " + (REJECT_REASON_LABELS[job.reject_reason] || job.reject_reason) : ""}</span>
        <button class="btn btn-ghost btn-sm" data-action="restore" data-id="${job.id}">Restaurer</button>
        <div class="job-card-actions-secondary">
          <button class="btn btn-ghost btn-sm" data-action="details" data-id="${job.id}">Détails</button>
        </div>
      `;
    }
    if (s === "applied" || s === "interview" || s === "offer") {
      return `
        <button class="btn btn-primary" data-action="generate" data-id="${job.id}">${ICONS.sparkle} Générer CV &amp; LM</button>
        <span class="status-pill status-${s}">${STATUS_LABELS[s]}</span>
        ${secondary}
      `;
    }
    const saveBtn = s === "new" ? `<button class="btn btn-secondary" data-action="save" data-id="${job.id}">💾 Sauvegarder</button>` : "";
    return `
      <button class="btn btn-primary" data-action="generate" data-id="${job.id}">${ICONS.sparkle} Générer CV &amp; LM</button>
      ${saveBtn}
      <button class="btn btn-secondary" data-action="apply" data-id="${job.id}">Marquer candidature</button>
      <button class="btn btn-ghost" data-action="reject-toggle" data-id="${job.id}">🚫 Rejeter</button>
      ${secondary}
    `;
  }

  function rejectPicker(job) {
    if (job.status === "rejected") return "";
    return `
      <div class="reject-picker hidden" id="reject-picker-${job.id}">
        <span class="reject-picker-label">Pourquoi rejeter cette offre ?</span>
        ${Object.entries(REJECT_REASON_LABELS).map(([k, label]) =>
          `<button class="btn btn-secondary btn-sm" data-action="reject-confirm" data-id="${job.id}" data-reason="${k}">${label}</button>`
        ).join("")}
        <button class="btn btn-ghost btn-sm" data-action="reject-cancel" data-id="${job.id}">Annuler</button>
      </div>
    `;
  }

  function jobCard(job) {
    const tier = scoreTier(job.score);
    const desc = job.job_description || "";
    return `
      <article class="job-card ${tier} ${job.status !== "new" ? "is-applied" : ""}" data-id="${job.id}">
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
              ${job.is_aeronautique ? `<span class="badge badge-sector">✈️ Aéronautique</span>` : ""}
              ${job.sector ? `<span class="badge badge-sector">${job.sector}</span>` : ""}
              <span class="badge badge-sector">${relativeDate(job.date_found)}</span>
            </div>
            ${job.salary_estimate_min ? `<div class="salary-estimate">${ICONS.trend} Tu peux prétendre à ${Math.round(job.salary_estimate_min / 1000)}-${Math.round(job.salary_estimate_max / 1000)}k€</div>` : ""}
          </div>
          <div>
            ${scoreRing(job.score, tier)}
            <div class="score-qualifier ${tier}">${SCORE_QUALIFIER[tier]}</div>
          </div>
        </div>
        <p class="job-card-desc">${desc.slice(0, 180)}${desc.length > 180 ? "…" : ""}</p>
        <div class="job-card-actions">
          ${jobActions(job)}
        </div>
        ${rejectPicker(job)}
      </article>
    `;
  }

  function sourceStatusLine(s) {
    if (s.connected) {
      return `<div>${s.name} ✅ mis à jour ${relativeUpdate(s.last_updated)} — ${s.jobs_found || 0} offre(s)</div>`;
    }
    return `<div>${s.name} ❌ ${s.note || "Non connecté"}</div>`;
  }

  async function renderEmptyState() {
    document.getElementById("jobs-empty-message").textContent =
      EMPTY_MESSAGES[state.tab] || "Aucune offre ne correspond à ces filtres.";
    const sourcesEl = document.getElementById("jobs-empty-sources");
    if (state.tab !== "flux") {
      sourcesEl.innerHTML = "";
      return;
    }
    try {
      const data = await Api.getDataSources();
      sourcesEl.innerHTML = data.sources.map(sourceStatusLine).join("");
    } catch (e) {
      sourcesEl.innerHTML = "";
    }
  }

  function renderJobs() {
    if (!state.jobs.length) {
      feedEl.innerHTML = "";
      emptyEl.classList.remove("hidden");
      renderEmptyState();
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
      role: f.role,
      company_type: f.company_type,
      location: f.location,
      min_salary: f.min_salary,
      aeronautique: f.aeronautique,
      enac: f.enac,
      tab: state.tab,
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

  async function loadProfile() {
    try {
      const p = await Api.getProfile();
      document.getElementById("profile-bar").textContent =
        `${p.name} · Recherche Aéronautique — Cible : ${Math.round(p.target_salary_min / 1000)}-${Math.round(p.target_salary_max / 1000)}k€ CDI — Actuel : ${Math.round(p.current_salary / 1000)}k€ @ ${p.current_company}`;
    } catch (e) {
      document.getElementById("profile-bar").textContent = "";
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

      document.getElementById("stat-applied-delta").textContent = `${stats.applied_total} au total`;

      document.getElementById("tab-count-flux").textContent = `(${stats.flux_total})`;
      document.getElementById("tab-count-saved").textContent = `(${stats.saved_total})`;
      document.getElementById("tab-count-applied").textContent = `(${stats.applied_total})`;
      document.getElementById("tab-count-rejected").textContent = `(${stats.rejected_total})`;

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

  function analysisList(items, cssClass) {
    return `<ul class="${cssClass}">${(items || []).map((i) => `<li>${i}</li>`).join("")}</ul>`;
  }

  async function renderDecisionWidget(jobId) {
    const slot = document.getElementById("decision-widget-slot");
    if (!slot) return; // modal was closed/replaced before this resolved
    try {
      const data = await Api.getAnalysis(jobId);
      slot.outerHTML = `
        <div class="decision-widget" id="decision-widget-slot">
          <div class="section-label">Faut-il candidater ?</div>
          <div class="decision-widget-row"><span>Score global</span><strong class="tnum">${data.score}/100</strong></div>
          ${data.salary_estimate && data.salary_estimate.min ? `<div class="decision-widget-row"><span>Salaire personnalisé estimé</span><strong class="tnum">${Math.round(data.salary_estimate.min / 1000)}-${Math.round(data.salary_estimate.max / 1000)}k€</strong></div>` : ""}
          <div class="decision-verdict">${ICONS.check} ${data.advice || ""}</div>
        </div>
        <div class="analysis-card">
          <h4>Avantages</h4>
          ${analysisList(data.advantages, "advantages")}
          <h4>Inconvénients</h4>
          ${analysisList(data.disadvantages, "disadvantages")}
        </div>
      `;
    } catch (e) {
      slot.textContent = "Analyse indisponible.";
    }
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
        ${job.is_aeronautique ? `<span class="badge badge-sector">✈️ Aéronautique</span>` : ""}
        ${job.status !== "new" ? `<span class="status-pill status-${job.status}">${STATUS_LABELS[job.status]}</span>` : ""}
      </div>
      <p style="font-size:14px; line-height:1.65; color:var(--color-text-secondary); margin-top:16px; white-space:pre-line; max-width:68ch;">${job.job_description || "Pas de description disponible."}</p>
      <div style="margin-top:16px;">
        <div class="section-label" style="margin-bottom:8px;">Détail du score</div>
        <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:8px; font-size:12px; color:var(--color-text-secondary);">
          <div>Rôle : <strong class="tnum">${job.score_job_match}</strong>/30</div>
          <div>Secteur : <strong class="tnum">${job.score_sector}</strong>/25</div>
          <div>Entreprise : <strong class="tnum">${job.score_notoriety}</strong>/20</div>
          <div>Salaire : <strong class="tnum">${job.score_salary}</strong>/20</div>
          <div>Localisation : <strong class="tnum">${job.score_location}</strong>/5</div>
          <div>Bonus : <strong class="tnum">${job.score_bonus}</strong>/10</div>
        </div>
      </div>
      <div id="decision-widget-slot">Chargement de l'analyse…</div>

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

  function openAddJobModal() {
    const modal = document.getElementById("job-modal");
    document.getElementById("modal-content").innerHTML = `
      <h2 style="font-size:20px; font-weight:700; color:var(--color-text-primary); margin:0 0 4px; padding-right:40px;">Ajouter une offre</h2>
      <p style="font-size:12px; color:var(--color-text-tertiary); margin:0 0 20px;">Une offre trouvée en dehors du scraping automatique (veille manuelle, recherche web...) - elle sera scorée et ajoutée directement à Mes Offres.</p>
      <div style="display:flex; flex-direction:column; gap:10px;">
        <input id="add-job-title" class="text-input" placeholder="Intitulé du poste *">
        <input id="add-job-company" class="text-input" placeholder="Entreprise *">
        <input id="add-job-url" class="text-input" type="url" placeholder="Lien de l'offre *">
        <input id="add-job-location" class="text-input" placeholder="Localisation">
        <input id="add-job-sector" class="text-input" placeholder="Secteur (ex: Aéronautique, Fintech...)">
        <div style="display:flex; gap:10px;">
          <input id="add-job-salary-min" class="text-input" type="number" placeholder="Salaire min (€)">
          <input id="add-job-salary-max" class="text-input" type="number" placeholder="Salaire max (€)">
        </div>
        <textarea id="add-job-description" rows="3" class="text-input" placeholder="Description / notes (optionnel)"></textarea>
      </div>
      <div class="job-card-actions" style="margin-top:16px;">
        <button class="btn btn-primary" data-action="create-job">Ajouter à Mes Offres</button>
      </div>
    `;
    modal.classList.add("is-open");
    document.getElementById("modal-close").focus();
  }

  async function handleCreateJob(btn) {
    const title = document.getElementById("add-job-title").value.trim();
    const company = document.getElementById("add-job-company").value.trim();
    const url = document.getElementById("add-job-url").value.trim();
    if (!title || !company || !url) {
      toast("Titre, entreprise et lien sont obligatoires");
      return;
    }
    const payload = {
      job_title: title,
      company,
      job_url: url,
      location: document.getElementById("add-job-location").value.trim(),
      sector: document.getElementById("add-job-sector").value.trim(),
      job_description: document.getElementById("add-job-description").value.trim(),
      status: "saved",
    };
    const salMin = document.getElementById("add-job-salary-min").value;
    const salMax = document.getElementById("add-job-salary-max").value;
    if (salMin) payload.salary_min = Number(salMin);
    if (salMax) payload.salary_max = Number(salMax);

    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Ajout…";
    try {
      await Api.createJob(payload);
      toast("Offre ajoutée à Mes Offres");
      closeModal();
      await loadJobs();
      await loadStats();
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = original;
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

  function veilleGrilleRow(level) {
    return `
      <div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid var(--color-border); font-size:13px; ${level.you ? "color:var(--color-primary); font-weight:700;" : "color:var(--color-text-secondary);"}">
        <span>${level.level}${level.sub ? ` <span style="font-size:11px; opacity:.75;">(${level.sub})</span>` : ""}</span>
        <span class="tnum">${Math.round(level.min / 1000)}k–${Math.round(level.max / 1000)}k€</span>
      </div>
    `;
  }

  function veilleTargetCard(t) {
    return `
      <div class="link-box" style="margin-top:8px;">
        <div style="display:flex; align-items:baseline; justify-content:space-between; gap:8px; flex-wrap:wrap;">
          <div class="link-box-title" style="margin-bottom:0;">${t.name}${t.sector ? ` · ${t.sector}` : ""}</div>
          <div class="tnum" style="font-weight:700; color:var(--color-text-primary);">${t.range_min ? Math.round(t.range_min / 1000) + "k–" + Math.round(t.range_max / 1000) + "k€" : "-"}</div>
        </div>
        ${t.note ? `<p style="font-size:13px; color:var(--color-text-secondary); margin:8px 0 0;">${t.note}</p>` : ""}
        ${t.caution ? `<div style="margin-top:8px; padding:6px 10px; border-radius:var(--radius-md); background:var(--color-warning-subtle); color:var(--color-warning); font-size:12px; font-weight:600;">${t.caution}</div>` : ""}
        ${t.found ? `<div style="margin-top:8px; font-size:11.5px; color:var(--color-text-tertiary);"><b>Trouvé :</b> ${t.found}</div>` : ""}
      </div>
    `;
  }

  async function openVeille() {
    const modal = document.getElementById("job-modal");
    document.getElementById("modal-content").innerHTML = `<p>Chargement de la veille…</p>`;
    modal.classList.add("is-open");
    try {
      const v = await Api.getVeille();
      if (!v.exists) {
        document.getElementById("modal-content").innerHTML = `
          <h2 style="font-size:20px; font-weight:700; margin:0 0 8px; color:var(--color-text-primary);">Veille marché</h2>
          <p style="font-size:13px; color:var(--color-text-tertiary);">Aucune veille enregistrée pour l'instant. Elle se met à jour automatiquement via la routine de veille périodique, ou peut être ajoutée manuellement via l'API.</p>
        `;
        return;
      }
      const updated = v.updated_at ? new Date(v.updated_at.replace(" ", "T")).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" }) : "-";
      document.getElementById("modal-content").innerHTML = `
        <h2 style="font-size:20px; font-weight:700; margin:0 0 4px; color:var(--color-text-primary);">Veille marché</h2>
        <p style="font-size:12px; color:var(--color-text-tertiary); margin:0 0 16px;">Mise à jour le ${updated}</p>

        <div class="decision-widget" style="margin-top:0;">
          <div class="decision-widget-row"><span>Cible réaliste (entrée CDI)</span><strong class="tnum">${Math.round(v.target_min / 1000)}k–${Math.round(v.target_max / 1000)}k€</strong></div>
        </div>
        ${v.summary ? `<p style="font-size:13.5px; line-height:1.6; color:var(--color-text-secondary); margin-top:12px;">${v.summary}</p>` : ""}

        ${v.grille.length ? `
          <div class="section-label" style="margin-top:20px;">Grille de marché par niveau</div>
          ${v.grille.map(veilleGrilleRow).join("")}
        ` : ""}

        ${v.targets.length ? `
          <div class="section-label" style="margin-top:20px;">Entreprises cibles</div>
          ${v.targets.map(veilleTargetCard).join("")}
        ` : ""}

        ${v.sources.length ? `
          <div class="section-label" style="margin-top:20px;">Sources</div>
          <div style="font-size:12px; color:var(--color-text-tertiary); display:flex; flex-direction:column; gap:4px;">
            ${v.sources.map((s) => `<a href="${s.url}" target="_blank" rel="noopener" style="color:var(--color-text-tertiary);">${s.label}</a>`).join("")}
          </div>
        ` : ""}
      `;
    } catch (e) {
      document.getElementById("modal-content").innerHTML = `<p>Erreur de chargement de la veille : ${e.message}</p>`;
    }
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

  async function handleSave(jobId) {
    try {
      await Api.saveJob(jobId);
      toast("Offre sauvegardée");
      await loadJobs();
      await loadStats();
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    }
  }

  function handleRejectToggle(jobId) {
    const picker = document.getElementById(`reject-picker-${jobId}`);
    if (picker) picker.classList.toggle("hidden");
  }

  async function handleRejectConfirm(jobId, reason) {
    try {
      await Api.rejectJob(jobId, reason);
      toast("Offre rejetée");
      await loadJobs();
      await loadStats();
    } catch (e) {
      toast(`Erreur : ${e.message}`);
    }
  }

  async function handleRestore(jobId) {
    try {
      await Api.setStatus(jobId, "new");
      toast("Offre restaurée dans le flux");
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
    document.getElementById("btn-veille").addEventListener("click", openVeille);
    document.getElementById("btn-add-job").addEventListener("click", openAddJobModal);
    document.querySelectorAll(".nav-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".nav-tab").forEach((t) => {
          t.classList.remove("is-active");
          t.setAttribute("aria-selected", "false");
        });
        tab.classList.add("is-active");
        tab.setAttribute("aria-selected", "true");
        state.tab = tab.dataset.tab;
        state.page = 1;
        loadJobs();
      });
    });
    document.getElementById("card-top-matches").addEventListener("click", () => {
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

    ["filter-role", "filter-company", "filter-location"].forEach((id) => {
      document.getElementById(id).addEventListener("change", () => {
        state.page = 1;
        loadJobs();
      });
    });
    ["filter-salary", "filter-aero", "filter-enac"].forEach((id) => {
      document.getElementById(id).addEventListener("change", () => {
        state.page = 1;
        loadJobs();
      });
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
      } else if (el.dataset.action === "save") {
        handleSave(jobId);
      } else if (el.dataset.action === "reject-toggle" || el.dataset.action === "reject-cancel") {
        handleRejectToggle(jobId);
      } else if (el.dataset.action === "reject-confirm") {
        handleRejectConfirm(jobId, el.dataset.reason);
      } else if (el.dataset.action === "restore") {
        handleRestore(jobId);
      } else if (el.dataset.action === "copy-link") {
        handleCopyLink(el.dataset.url);
      } else if (el.dataset.action === "save-status") {
        handleSaveStatus(jobId, el);
      } else if (el.dataset.action === "create-job") {
        handleCreateJob(el);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    Filters.bindSalarySlider();
    bindEvents();
    loadProfile();
    loadJobs();
    loadStats();
  });
})();
