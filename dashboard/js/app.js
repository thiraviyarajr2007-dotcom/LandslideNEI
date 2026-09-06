/**
 * LandslideNEI Dashboard - Main Application Controller
 */

let appState = {
  currentEvaluation: null,
  currentProfile: null,
  isLoading: false,
  apiInfo: null,
  apiHealth: null,
};

document.addEventListener("DOMContentLoaded", () => {
  // Initialize Leaflet Map
  initMap();

  // Populate Demo Presets Toolbar
  renderDemoPresets();

  // Check API Health and Capabilities
  fetchSystemInfo();

  // Wire up Event Listeners
  setupEventListeners();
});

function setupEventListeners() {
  const evaluateBtn = document.getElementById("btn-evaluate");
  const profileBtn = document.getElementById("btn-profile");
  const resetBtn = document.getElementById("btn-reset");
  const latInput = document.getElementById("input-lat");
  const lonInput = document.getElementById("input-lon");
  const basemapSelect = document.getElementById("select-basemap");
  const chkStates = document.getElementById("chk-layer-states");
  const chkStations = document.getElementById("chk-layer-stations");

  if (evaluateBtn) {
    evaluateBtn.addEventListener("click", () => {
      const lat = parseFloat(latInput.value);
      const lon = parseFloat(lonInput.value);
      if (validateCoords(lat, lon)) {
        evaluateLocation(lat, lon);
      }
    });
  }

  if (profileBtn) {
    profileBtn.addEventListener("click", () => {
      const lat = parseFloat(latInput.value);
      const lon = parseFloat(lonInput.value);
      if (validateCoords(lat, lon)) {
        profileLocation(lat, lon);
      }
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", resetDashboard);
  }

  // Basemap & Layer toggles
  if (basemapSelect) {
    basemapSelect.addEventListener("change", (e) => switchBasemap(e.target.value));
  }
  if (chkStates) {
    chkStates.addEventListener("change", (e) => toggleLayer("states", e.target.checked));
  }
  if (chkStations) {
    chkStations.addEventListener("change", (e) => toggleLayer("stations", e.target.checked));
  }

  // Language buttons
  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const lang = btn.getAttribute("data-lang");
      setLanguage(lang);
    });
  });

  // Modal close
  const modalClose = document.getElementById("modal-close-btn");
  if (modalClose) {
    modalClose.addEventListener("click", hideModal);
  }
}

function handleMapClick(lat, lon) {
  document.getElementById("input-lat").value = lat;
  document.getElementById("input-lon").value = lon;
  evaluateLocation(lat, lon);
}
window.handleMapClick = handleMapClick;

function validateCoords(lat, lon) {
  if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    showModal(t("errorTitle"), t("errorCoordinates"), "INVALID_COORDINATES");
    return false;
  }
  return true;
}

function renderDemoPresets() {
  const container = document.getElementById("presets-container");
  if (!container) return;

  container.innerHTML = DEMO_PRESETS.map(preset => {
    const name = currentLang === "ta" ? preset.name_ta : preset.name_en;
    const desc = currentLang === "ta" ? preset.description_ta : preset.description_en;
    return `
      <div class="preset-card" onclick="selectPreset('${preset.id}')" title="${desc}">
        <div class="preset-header">
          <span class="preset-name">${name}</span>
          <span class="preset-badge ${preset.badgeClass}">${preset.badge}</span>
        </div>
        <div class="preset-coords">${preset.lat.toFixed(4)}°N, ${preset.lon.toFixed(4)}°E</div>
      </div>
    `;
  }).join("");
}

function selectPreset(presetId) {
  const preset = DEMO_PRESETS.find(p => p.id === presetId);
  if (!preset) return;

  document.getElementById("input-lat").value = preset.lat;
  document.getElementById("input-lon").value = preset.lon;

  evaluateLocation(preset.lat, preset.lon);
}
window.selectPreset = selectPreset;

// ==============================================================================
// API CALLS
// ==============================================================================

async function fetchSystemInfo() {
  try {
    const [healthRes, infoRes] = await Promise.all([
      fetch("/api/v1/health"),
      fetch("/api/v1/info")
    ]);

    if (healthRes.ok) {
      appState.apiHealth = await healthRes.json();
      const statusPill = document.getElementById("sys-status-pill");
      if (statusPill) {
        statusPill.innerHTML = `
          <span class="pulse-dot-green"></span>
          <span>${t("systemStatus")} (v${appState.apiHealth.api_version})</span>
        `;
      }
    }

    if (infoRes.ok) {
      appState.apiInfo = await infoRes.json();
    }
  } catch (err) {
    console.warn("Could not fetch API health/info", err);
    const statusPill = document.getElementById("sys-status-pill");
    if (statusPill) {
      statusPill.innerHTML = `
        <span class="pulse-dot-red"></span>
        <span style="color:#ef4444;">API Offline</span>
      `;
    }
  }
}

async function evaluateLocation(lat, lon) {
  setLoading(true);
  try {
    const res = await fetch("/api/v1/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        latitude: lat,
        longitude: lon,
        timestamp: new Date().toISOString()
      })
    });

    const data = await res.json();

    if (!res.ok) {
      // Domain validation or validation error
      const err = data.error || {};
      const msg = err.code === "OUTSIDE_NER_DOMAIN" ? t("errorOutsideDomain") : (err.message || "Evaluation failed.");
      showModal(t("errorTitle"), msg, err.code || "HTTP_" + res.status, err.details);
      setQueryPoint(lat, lon, "REJECTED");
      renderEmptyState();
      return;
    }

    appState.currentEvaluation = data;
    appState.currentProfile = null;

    // Place marker on GIS map
    const riskLevel = data.risk ? data.risk.risk_level : "UNKNOWN";
    const dist = data.rainfall ? data.rainfall.distance_km : null;
    setQueryPoint(lat, lon, riskLevel, dist);

    // Render detailed operational panel
    renderCurrentEvaluation();
  } catch (err) {
    console.error("Evaluation network error:", err);
    showModal(t("errorTitle"), "Failed to communicate with inference API. Check backend server.", "NETWORK_ERROR");
  } finally {
    setLoading(false);
  }
}

async function profileLocation(lat, lon) {
  setLoading(true);
  try {
    const res = await fetch("/api/v1/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latitude: lat, longitude: lon })
    });

    const data = await res.json();

    if (!res.ok) {
      const err = data.error || {};
      const msg = err.code === "OUTSIDE_NER_DOMAIN" ? t("errorOutsideDomain") : (err.message || "Profile failed.");
      showModal(t("errorTitle"), msg, err.code || "HTTP_" + res.status, err.details);
      setQueryPoint(lat, lon, "REJECTED");
      renderEmptyState();
      return;
    }

    appState.currentEvaluation = null;
    appState.currentProfile = data;

    const suscCat = data.static_susceptibility ? data.static_susceptibility.category : "UNKNOWN";
    setQueryPoint(lat, lon, suscCat);

    renderCurrentProfile();
  } catch (err) {
    console.error("Profile network error:", err);
    showModal(t("errorTitle"), "Failed to communicate with profile API.", "NETWORK_ERROR");
  } finally {
    setLoading(false);
  }
}

// ==============================================================================
// DOM RENDERING
// ==============================================================================

function renderCurrentEvaluation() {
  const data = appState.currentEvaluation;
  if (!data) return;

  const panel = document.getElementById("operational-panel-body");
  if (!panel) return;

  const loc = data.location || {};
  const susc = data.static_susceptibility || {};
  const rf = data.rainfall || {};
  const trig = data.rainfall_trigger || {};
  const risk = data.risk || {};
  const terrain = susc.terrain || {};
  const soil = susc.soil || {};
  const lulc = susc.landcover || {};

  const riskClass = "risk-" + (risk.risk_level || "LOW").toLowerCase();
  const riskLabel = getRiskLocalizedLabel(risk.risk_level);
  const fusionScorePct = (risk.operational_fusion_score * 100).toFixed(1);
  const suscScorePct = (susc.score * 100).toFixed(1);

  // Freshness & Station Quality
  const freshStatus = rf.freshness ? rf.freshness.freshness_status : "NO_DATA";
  const freshClass = freshStatus === "FRESH" ? "badge-fresh" : (freshStatus === "STALE" ? "badge-stale" : "badge-sparse");
  const ageStr = rf.freshness && rf.freshness.age_hours !== null ? `${rf.freshness.age_hours}h ago` : "N/A";
  const distStr = rf.distance_km !== null ? `${rf.distance_km} km` : "Out of 50km Range";

  panel.innerHTML = `
    <!-- Top Location Banner -->
    <div class="card location-banner">
      <div class="loc-details">
        <div class="loc-primary">📍 ${loc.district || "District Unassigned"}, ${loc.state || "Northeast India"}</div>
        <div class="loc-coords font-mono">${loc.latitude.toFixed(4)}°N, ${loc.longitude.toFixed(4)}°E</div>
      </div>
      <div class="domain-tag">
        <span class="pulse-dot-green"></span>
        <span>NER Domain Validated</span>
      </div>
    </div>

    <!-- Authoritative Risk Verdict Card -->
    <div class="card risk-verdict-card ${riskClass}">
      <div class="card-header-flex">
        <span class="card-title font-bold">${t("riskVerdictTitle")}</span>
        <span class="authoritative-pill">${t("authoritativeBadge")}</span>
      </div>
      <div class="verdict-main">
        <div class="verdict-badge ${riskClass}">${riskLabel}</div>
        <div class="verdict-action">
          <div class="action-label">${t("actionRecommendation")}:</div>
          <div class="action-text">${risk.operational_action || "Routine monitoring."}</div>
        </div>
      </div>

      <!-- Fusion Score Gauge -->
      <div class="fusion-score-wrapper">
        <div class="score-label-flex">
          <span>${t("fusionScoreLabel")}</span>
          <span class="font-mono font-bold">${risk.operational_fusion_score.toFixed(4)} (${fusionScorePct}%)</span>
        </div>
        <div class="progress-bar-track">
          <div class="progress-bar-fill ${riskClass}" style="width: ${fusionScorePct}%;"></div>
        </div>
        <div class="score-disclaimer">
          ⚠️ ${t("fusionScoreDisclaimer")}
        </div>
      </div>
    </div>

    <!-- Static Terrain Susceptibility Card -->
    <div class="card">
      <div class="card-header-flex">
        <span class="card-title">⛰️ ${t("susceptibilityTitle")}</span>
        <span class="cat-pill cat-${susc.category.toLowerCase()}">${susc.category}</span>
      </div>
      <div class="susc-score-row">
        <div class="metric-box">
          <div class="metric-title">${t("susceptibilityScore")}</div>
          <div class="metric-val font-mono">${susc.score.toFixed(4)}</div>
        </div>
        <div class="metric-box">
          <div class="metric-title">${t("susceptibilityCategory")}</div>
          <div class="metric-val font-bold">${susc.category_label || susc.category}</div>
        </div>
      </div>
      <div class="text-caption" style="margin-top:6px;">
        ℹ️ ${t("uncalibratedDisclaimer")}
      </div>
    </div>

    <!-- Real-Time Rainfall Telemetry Card -->
    <div class="card">
      <div class="card-header-flex">
        <span class="card-title">🌧️ ${t("rainfallTitle")}</span>
        <span class="cat-pill trig-${(trig.trigger_level || "NORMAL").toLowerCase()}">${trig.trigger_level || "NORMAL"}</span>
      </div>

      <!-- Station Telemetry Meta -->
      <div class="telemetry-meta-grid">
        <div><span class="text-muted">${t("nearestStation")}:</span> <strong>${rf.station || "None in Range"}</strong></div>
        <div><span class="text-muted">${t("stationDistance")}:</span> <strong>${distStr}</strong></div>
        <div><span class="text-muted">${t("stationFreshness")}:</span> <span class="badge ${freshClass}">${freshStatus} (${ageStr})</span></div>
        <div><span class="text-muted">${t("rainfallTriggerScore")}:</span> <strong class="font-mono">${trig.trigger_score !== null ? trig.trigger_score.toFixed(2) : "N/A"}</strong></div>
      </div>

      <!-- Multi-Window Accumulations -->
      <div class="rainfall-windows-grid">
        <div class="rf-window-box">
          <div class="rf-win-title">${t("rainfall1h")}</div>
          <div class="rf-win-val">${formatMm(rf.rainfall_1h)}</div>
        </div>
        <div class="rf-window-box">
          <div class="rf-win-title">${t("rainfall24h")}</div>
          <div class="rf-win-val">${formatMm(rf.rainfall_24h)}</div>
        </div>
        <div class="rf-window-box">
          <div class="rf-win-title">${t("rainfall3d")}</div>
          <div class="rf-win-val">${formatMm(rf.rainfall_3d)}</div>
        </div>
        <div class="rf-window-box">
          <div class="rf-win-title">${t("rainfall7d")}</div>
          <div class="rf-win-val">${formatMm(rf.rainfall_7d)}</div>
        </div>
      </div>

      <!-- IMD Administrative Context -->
      ${renderIMDContext(rf.imd_context)}
    </div>

    <!-- Physical Features Inspector -->
    <div class="card">
      <div class="card-title" style="margin-bottom: 8px;">🔬 Physical Environmental Features</div>
      <div class="features-grid">
        <div class="feat-col">
          <div class="feat-col-title">${t("terrainTitle")}</div>
          <div class="feat-item"><span>${t("elevation")}:</span> <strong>${terrain.elevation_m !== null ? terrain.elevation_m + ' m' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("slope")}:</span> <strong>${terrain.slope_deg !== null ? terrain.slope_deg + '°' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("aspect")}:</span> <strong>${terrain.aspect_deg !== null ? terrain.aspect_deg + '°' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("relief")}:</span> <strong>${terrain.relief_std_5x5_m !== null ? terrain.relief_std_5x5_m + ' m' : 'N/A'}</strong></div>
        </div>
        <div class="feat-col">
          <div class="feat-col-title">${t("soilTitle")}</div>
          <div class="feat-item"><span>${t("soilClass")}:</span> <strong>${soil.soil_class || 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("clay")}:</span> <strong>${soil.clay_percent !== null ? soil.clay_percent + '%' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("sand")}:</span> <strong>${soil.sand_percent !== null ? soil.sand_percent + '%' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("silt")}:</span> <strong>${soil.silt_percent !== null ? soil.silt_percent + '%' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("bulkDensity")}:</span> <strong>${soil.bulk_density_kg_dm3 !== null ? soil.bulk_density_kg_dm3 + ' kg/dm³' : 'N/A'}</strong></div>
        </div>
      </div>
      <div class="lulc-item" style="margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px;">
        <span class="text-muted">${t("lulcClass")}:</span> <strong>${lulc.landcover_class || 'N/A'}</strong> (Code: ${lulc.landcover_code || 'N/A'})
      </div>
    </div>

    <!-- Explainability & Reason Codes -->
    <div class="card">
      <div class="card-title">💡 ${t("explainabilityTitle")}</div>
      <div class="text-muted" style="font-size:12px; margin-bottom:8px;">${t("whyThisRisk")}</div>
      <div class="reasons-list">
        ${renderReasonCodes(risk.reasons || susc.reasons || [])}
      </div>
    </div>
  `;
}

function renderCurrentProfile() {
  const data = appState.currentProfile;
  if (!data) return;

  const panel = document.getElementById("operational-panel-body");
  if (!panel) return;

  const loc = data.location || {};
  const susc = data.static_susceptibility || {};
  const terrain = susc.terrain || {};
  const soil = susc.soil || {};
  const lulc = susc.landcover || {};

  panel.innerHTML = `
    <!-- Top Location Banner -->
    <div class="card location-banner">
      <div class="loc-details">
        <div class="loc-primary">📍 ${loc.district || "District"}, ${loc.state || "Northeast India"}</div>
        <div class="loc-coords font-mono">${loc.latitude.toFixed(4)}°N, ${loc.longitude.toFixed(4)}°E</div>
      </div>
      <div class="domain-tag">
        <span class="pulse-dot-green"></span>
        <span>Static Profile Only</span>
      </div>
    </div>

    <!-- Static Terrain Susceptibility Card -->
    <div class="card">
      <div class="card-header-flex">
        <span class="card-title">⛰️ ${t("susceptibilityTitle")}</span>
        <span class="cat-pill cat-${susc.category.toLowerCase()}">${susc.category}</span>
      </div>
      <div class="susc-score-row">
        <div class="metric-box">
          <div class="metric-title">${t("susceptibilityScore")}</div>
          <div class="metric-val font-mono font-bold">${susc.score.toFixed(4)}</div>
        </div>
        <div class="metric-box">
          <div class="metric-title">${t("susceptibilityCategory")}</div>
          <div class="metric-val font-bold">${susc.category_label || susc.category}</div>
        </div>
      </div>
      <div class="text-caption" style="margin-top:6px;">
        ℹ️ ${t("uncalibratedDisclaimer")}
      </div>
    </div>

    <!-- Physical Features Inspector -->
    <div class="card">
      <div class="card-title" style="margin-bottom: 8px;">🔬 Physical Environmental Features</div>
      <div class="features-grid">
        <div class="feat-col">
          <div class="feat-col-title">${t("terrainTitle")}</div>
          <div class="feat-item"><span>${t("elevation")}:</span> <strong>${terrain.elevation_m !== null ? terrain.elevation_m + ' m' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("slope")}:</span> <strong>${terrain.slope_deg !== null ? terrain.slope_deg + '°' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("aspect")}:</span> <strong>${terrain.aspect_deg !== null ? terrain.aspect_deg + '°' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("relief")}:</span> <strong>${terrain.relief_std_5x5_m !== null ? terrain.relief_std_5x5_m + ' m' : 'N/A'}</strong></div>
        </div>
        <div class="feat-col">
          <div class="feat-col-title">${t("soilTitle")}</div>
          <div class="feat-item"><span>${t("soilClass")}:</span> <strong>${soil.soil_class || 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("clay")}:</span> <strong>${soil.clay_percent !== null ? soil.clay_percent + '%' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("sand")}:</span> <strong>${soil.sand_percent !== null ? soil.sand_percent + '%' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("silt")}:</span> <strong>${soil.silt_percent !== null ? soil.silt_percent + '%' : 'N/A'}</strong></div>
          <div class="feat-item"><span>${t("bulkDensity")}:</span> <strong>${soil.bulk_density_kg_dm3 !== null ? soil.bulk_density_kg_dm3 + ' kg/dm³' : 'N/A'}</strong></div>
        </div>
      </div>
      <div class="lulc-item" style="margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px;">
        <span class="text-muted">${t("lulcClass")}:</span> <strong>${lulc.landcover_class || 'N/A'}</strong> (Code: ${lulc.landcover_code || 'N/A'})
      </div>
    </div>
  `;
}

function renderIMDContext(imd) {
  if (!imd) return '';
  return `
    <div class="imd-box" style="margin-top: 10px; background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.05); padding: 8px; border-radius: 6px;">
      <div style="font-size: 11px; font-weight: 700; color: #38bdf8; margin-bottom: 4px;">🏛️ ${t("imdMacroTitle")} (${imd.scope || 'MACRO'})</div>
      <div style="font-size: 11px; display: flex; justify-content: space-between; color: #cbd5e1;">
        <span>${imd.state || 'State'} ${imd.district ? '• ' + imd.district : ''}</span>
        <span>Obs: <strong>${formatMm(imd.daily_actual_mm)}</strong> / Norm: <strong>${formatMm(imd.daily_normal_mm)}</strong></span>
      </div>
      <div style="font-size: 10px; color: #94a3b8; margin-top: 3px;">
        ${t("imdDisclaimer")}
      </div>
    </div>
  `;
}

function renderReasonCodes(reasons) {
  if (!reasons || reasons.length === 0) {
    return `<div class="text-muted" style="font-size:12px;">${t("noReasonsAvailable")}</div>`;
  }

  return reasons.map(r => {
    const title = r.factor || r.code || "FACTOR";
    const desc = r.description || JSON.stringify(r);
    return `
      <div class="reason-item">
        <div class="reason-bullet"></div>
        <div>
          <strong style="color:#38bdf8;">${title}</strong>: <span>${desc}</span>
        </div>
      </div>
    `;
  }).join("");
}

function formatMm(val) {
  if (val === null || val === undefined) return '<span class="text-muted">No Data</span>';
  return `<strong>${val.toFixed(1)}</strong> mm`;
}

function getRiskLocalizedLabel(tier) {
  switch (tier) {
    case "LOW": return t("riskLow");
    case "WATCH": return t("riskWatch");
    case "HIGH": return t("riskHigh");
    case "CRITICAL": return t("riskCritical");
    default: return tier || "UNKNOWN";
  }
}

function renderEmptyState() {
  const panel = document.getElementById("operational-panel-body");
  if (!panel) return;

  panel.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">📍</div>
      <div class="empty-title">No Location Selected</div>
      <div class="empty-desc">Click anywhere on the Northeast India map or select a demo preset above to evaluate real-time landslide risk.</div>
    </div>
  `;
}

function resetDashboard() {
  clearQueryPoint();
  document.getElementById("input-lat").value = "";
  document.getElementById("input-lon").value = "";
  appState.currentEvaluation = null;
  appState.currentProfile = null;
  renderEmptyState();
}

function setLoading(isLoading) {
  appState.isLoading = isLoading;
  const evalBtn = document.getElementById("btn-evaluate");
  const spinner = document.getElementById("loading-spinner");
  if (evalBtn) evalBtn.disabled = isLoading;
  if (spinner) spinner.style.display = isLoading ? "flex" : "none";
}

function showModal(title, message, code = "", details = null) {
  const overlay = document.getElementById("modal-overlay");
  const titleEl = document.getElementById("modal-title");
  const msgEl = document.getElementById("modal-message");
  const codeEl = document.getElementById("modal-code");
  const detailsEl = document.getElementById("modal-details");

  if (titleEl) titleEl.textContent = title;
  if (msgEl) msgEl.textContent = message;
  if (codeEl) codeEl.textContent = code ? `[${code}]` : "";
  if (detailsEl) {
    detailsEl.textContent = details ? JSON.stringify(details, null, 2) : "";
    detailsEl.style.display = details ? "block" : "none";
  }
  if (overlay) overlay.style.display = "flex";
}

function hideModal() {
  const overlay = document.getElementById("modal-overlay");
  if (overlay) overlay.style.display = "none";
}

window.renderCurrentEvaluation = renderCurrentEvaluation;
