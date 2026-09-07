/**
 * LandslideNEI Sentinel Monitor - Extension Popup Controller
 * Manages real-time API communication, sector switching, and UI rendering.
 */

const DEFAULT_API_BASE = 'http://localhost:8000';

const DEMO_PRESETS = {
  '25.6740,94.1120': {
    name: 'Kohima & Zubza Axis (NH-29)',
    lat: 25.6740,
    lon: 94.1120,
    risk: { risk_level: 'LOW', operational_fusion_score: 0.124, operational_action: 'Routine monitoring; baseline susceptibility is low.' },
    rainfall: { rainfall_24h: 2.4, doppler_reflectivity_dbz: 18.0, quality: 'REALTIME' },
    static_susceptibility: {
      terrain: { slope_deg: 26.4, curvature_class: 'PLANAR', topographic_wetness_index: 6.8 },
      soil: { factor_of_safety: 2.45, pore_water_pressure_kpa: 0.0, saturation_percent: 42.1 }
    },
    anthropogenic: { road_cut_severity: 'NONE', road_cut_present: false, drainage_condition: 'NORMAL' }
  },
  '27.3389,88.6065': {
    name: 'Gangtok & Teesta Corridor (NH-10)',
    lat: 27.3389,
    lon: 88.6065,
    risk: { risk_level: 'WATCH', operational_fusion_score: 0.385, operational_action: 'Advisory vigilance; elevated static slope predisposition.' },
    rainfall: { rainfall_24h: 14.2, doppler_reflectivity_dbz: 28.5, quality: 'REALTIME' },
    static_susceptibility: {
      terrain: { slope_deg: 32.1, curvature_class: 'CONVERGENT', topographic_wetness_index: 8.2 },
      soil: { factor_of_safety: 1.48, pore_water_pressure_kpa: 2.1, saturation_percent: 68.4 }
    },
    anthropogenic: { road_cut_severity: 'MODERATE', road_cut_present: true, drainage_condition: 'NORMAL' }
  },
  '25.2702,91.7323': {
    name: 'Cherrapunji Escarpment',
    lat: 25.2702,
    lon: 91.7323,
    risk: { risk_level: 'HIGH', operational_fusion_score: 0.642, operational_action: 'Operational alert; active orographic rainfall and steep scarp.' },
    rainfall: { rainfall_24h: 78.5, doppler_reflectivity_dbz: 38.0, quality: 'REALTIME' },
    static_susceptibility: {
      terrain: { slope_deg: 38.5, curvature_class: 'CONVERGENT', topographic_wetness_index: 9.4 },
      soil: { factor_of_safety: 1.15, pore_water_pressure_kpa: 6.8, saturation_percent: 88.2 }
    },
    anthropogenic: { road_cut_severity: 'SEVERE', road_cut_present: true, drainage_condition: 'BLOCKED' }
  }
};

document.addEventListener('DOMContentLoaded', async () => {
  const apiInput = document.getElementById('api-base-url');
  const sectorSelect = document.getElementById('sector-select');
  const btnToggleCoords = document.getElementById('btn-toggle-coords');
  const coordsPanel = document.getElementById('custom-coords-panel');
  const btnRunEval = document.getElementById('btn-run-eval');
  const btnGps = document.getElementById('btn-gps');
  const btnOpenWorkstation = document.getElementById('btn-open-workstation');
  const btnOpenSidepanel = document.getElementById('btn-open-sidepanel');

  // Load saved API base URL
  const savedApi = await getStorage('landslide_api_base') || DEFAULT_API_BASE;
  if (apiInput) apiInput.value = savedApi;

  if (apiInput) {
    apiInput.addEventListener('change', () => {
      const val = apiInput.value.trim() || DEFAULT_API_BASE;
      setStorage('landslide_api_base', val);
      checkApiHealth(val);
    });
  }

  // Check health and run initial prediction
  await checkApiHealth(savedApi);
  const initialCoord = sectorSelect.value;
  evaluatePoint(initialCoord);

  // Sector selection handler
  sectorSelect.addEventListener('change', (e) => {
    const val = e.target.value;
    if (val === 'custom') {
      coordsPanel.classList.remove('hidden');
    } else {
      coordsPanel.classList.add('hidden');
      evaluatePoint(val);
    }
  });

  // Toggle custom coords
  btnToggleCoords.addEventListener('click', () => {
    coordsPanel.classList.toggle('hidden');
  });

  // Custom evaluation button
  btnRunEval.addEventListener('click', () => {
    const lat = parseFloat(document.getElementById('custom-lat').value);
    const lon = parseFloat(document.getElementById('custom-lon').value);
    if (!isNaN(lat) && !isNaN(lon)) {
      evaluatePoint(`${lat},${lon}`);
    } else {
      alert('Please enter valid numeric latitude and longitude coordinates.');
    }
  });

  // GPS button
  btnGps.addEventListener('click', () => {
    if (navigator.geolocation) {
      btnGps.textContent = '⏳ ...';
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          btnGps.textContent = '📍 GPS';
          const lat = pos.coords.latitude.toFixed(4);
          const lon = pos.coords.longitude.toFixed(4);
          document.getElementById('custom-lat').value = lat;
          document.getElementById('custom-lon').value = lon;
          coordsPanel.classList.remove('hidden');
          sectorSelect.value = 'custom';
          evaluatePoint(`${lat},${lon}`);
        },
        (err) => {
          btnGps.textContent = '📍 GPS';
          alert('GPS Geolocation failed: ' + err.message);
        }
      );
    }
  });

  // Open full workstation dashboard in tab
  btnOpenWorkstation.addEventListener('click', async () => {
    const base = (apiInput?.value || DEFAULT_API_BASE).replace(/\/$/, '');
    const url = `${base}/dashboard/`;
    if (chrome && chrome.tabs && chrome.tabs.create) {
      chrome.tabs.create({ url });
    } else {
      window.open(url, '_blank');
    }
  });

  // Open side panel
  if (btnOpenSidepanel) {
    btnOpenSidepanel.addEventListener('click', async () => {
      if (chrome && chrome.sidePanel && chrome.sidePanel.open) {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.id) {
          chrome.sidePanel.open({ tabId: tab.id });
        }
      } else {
        const base = (apiInput?.value || DEFAULT_API_BASE).replace(/\/$/, '');
        window.open(`${base}/dashboard/`, '_blank');
      }
    });
  }
});

/**
 * Check if the backend API server is healthy.
 */
async function checkApiHealth(baseUrl) {
  const dot = document.getElementById('api-status-dot');
  const txt = document.getElementById('api-status-text');

  try {
    const res = await fetch(`${baseUrl}/api/v1/health`, { method: 'GET', signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      if (dot) {
        dot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
        dot.title = 'Connected to Local API Server';
      }
      if (txt) {
        txt.textContent = 'ONLINE';
        txt.className = 'text-[9px] font-mono text-emerald-400';
      }
      return true;
    }
  } catch (err) {
    // Backend is offline, fall back gracefully
  }

  if (dot) {
    dot.className = 'w-2 h-2 rounded-full bg-amber-500';
    dot.title = 'Local API offline — Operating on cached/demo telemetry';
  }
  if (txt) {
    txt.textContent = 'OFFLINE (DEMO)';
    txt.className = 'text-[9px] font-mono text-amber-400';
  }
  return false;
}

/**
 * Evaluate landslide hazard for coordinates.
 */
async function evaluatePoint(coordsStr) {
  const [latStr, lonStr] = coordsStr.split(',');
  const lat = parseFloat(latStr);
  const lon = parseFloat(lonStr);
  if (isNaN(lat) || isNaN(lon)) return;

  const apiBase = (document.getElementById('api-base-url')?.value || DEFAULT_API_BASE).replace(/\/$/, '');

  try {
    const payload = {
      latitude: lat,
      longitude: lon,
      timestamp: new Date().toISOString(),
      auto_refetch: true
    };

    const res = await fetch(`${apiBase}/api/v1/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(4000)
    });

    if (res.ok) {
      const data = await res.json();
      renderResults(data);
      updateBadge(data.risk?.risk_level || 'LOW');
      return;
    }
  } catch (err) {
    console.warn('API call failed, falling back to preset or cache:', err);
  }

  // Fallback to preset if matches, or construct a reasonable estimation
  const preset = DEMO_PRESETS[coordsStr] || {
    name: `Sector (${lat.toFixed(2)}°, ${lon.toFixed(2)}°)`,
    lat,
    lon,
    risk: { risk_level: 'WATCH', operational_fusion_score: 0.35, operational_action: 'Demonstration estimate. Start local server for live physics inference.' },
    rainfall: { rainfall_24h: 12.0, doppler_reflectivity_dbz: 22.0, quality: 'FALLBACK' },
    static_susceptibility: {
      terrain: { slope_deg: 28.0, curvature_class: 'PLANAR', topographic_wetness_index: 7.2 },
      soil: { factor_of_safety: 1.65, pore_water_pressure_kpa: 1.2, saturation_percent: 54.0 }
    },
    anthropogenic: { road_cut_severity: 'NONE', road_cut_present: false, drainage_condition: 'NORMAL' }
  };

  renderResults(preset);
  updateBadge(preset.risk?.risk_level || 'WATCH');
}

/**
 * Render evaluation results to UI elements.
 */
function renderResults(data) {
  const risk = data.risk || {};
  const staticLsm = data.static_susceptibility || {};
  const rain = data.rainfall || {};
  const terrain = staticLsm.terrain || {};
  const soil = staticLsm.soil || {};
  const anthro = data.anthropogenic || staticLsm.anthropogenic || {};
  const loc = data.location || {};

  const level = (risk.risk_level || 'LOW').toUpperCase();
  const score = (risk.operational_fusion_score !== undefined ? risk.operational_fusion_score : (risk.risk_score || 0.12));

  // 1. Verdict Card
  const pill = document.getElementById('verdict-pill');
  const card = document.getElementById('verdict-card');
  const scoreVal = document.getElementById('score-val');
  const scoreBar = document.getElementById('score-bar');
  const locName = document.getElementById('loc-name');

  const colorConfig = {
    LOW: { border: 'border-emerald-500/40', text: 'text-emerald-400', bar: 'bg-emerald-500' },
    WATCH: { border: 'border-amber-500/40', text: 'text-amber-400', bar: 'bg-amber-500' },
    HIGH: { border: 'border-orange-500/50', text: 'text-orange-400', bar: 'bg-orange-500' },
    CRITICAL: { border: 'border-red-500/60', text: 'text-red-400', bar: 'bg-red-500' }
  };

  const cfg = colorConfig[level] || colorConfig.LOW;

  if (pill) {
    pill.textContent = `${level} RISK`;
    pill.className = `text-xl font-mono font-extrabold tracking-wider my-0.5 ${cfg.text}`;
  }
  if (card) {
    card.className = `p-3 rounded-lg border ${cfg.border} bg-gradient-to-br from-slate-900 to-slate-800/90 shadow-lg text-center relative overflow-hidden`;
  }
  if (scoreVal) scoreVal.textContent = Number(score).toFixed(3);
  if (scoreBar) {
    scoreBar.style.width = `${Math.min(100, Math.max(5, score * 100))}%`;
    scoreBar.className = `h-full ${cfg.bar} transition-all duration-500`;
  }
  if (locName) {
    locName.textContent = loc.district || loc.state || (data.name || 'Northeast Sector');
  }

  // 2. Pillar 1: Precipitation
  const rain24 = rain.rainfall_24h !== undefined ? rain.rainfall_24h : 0.0;
  const dwr = rain.doppler_reflectivity_dbz !== undefined ? `${rain.doppler_reflectivity_dbz} dBZ` : (rain.cloudburst_detected ? 'CLOUDBURST' : '15 dBZ');
  const rainQuality = rain.quality || (rain.is_realtime ? 'REALTIME' : 'OK');

  setText('rain-24h', `${Number(rain24).toFixed(1)} mm`);
  setText('dwr-val', dwr);
  setText('rain-quality', rainQuality);

  // 3. Pillar 2: Geotechnical Soil Mechanics
  const fos = soil.factor_of_safety !== undefined ? Number(soil.factor_of_safety).toFixed(2) : '2.10';
  const u = soil.pore_water_pressure_kpa !== undefined ? `${Number(soil.pore_water_pressure_kpa).toFixed(1)} kPa` : '0.0 kPa';
  const fosState = Number(fos) <= 1.0 ? 'FAILING' : (Number(fos) <= 1.3 ? 'MARGINAL' : 'STABLE');

  setText('fos-val', fos);
  setText('pore-val', u);
  setText('fos-state', fosState);
  const fosBadge = document.getElementById('fos-state');
  if (fosBadge) {
    fosBadge.className = `text-[8px] font-bold ${Number(fos) <= 1.0 ? 'text-red-400' : (Number(fos) <= 1.3 ? 'text-amber-400' : 'text-emerald-400')}`;
  }

  // 4. Pillar 3: Micro-Topography
  const slope = terrain.slope_deg !== undefined ? `${Number(terrain.slope_deg).toFixed(1)}°` : '28.0°';
  const twi = terrain.topographic_wetness_index !== undefined ? Number(terrain.topographic_wetness_index).toFixed(1) : '7.0';
  const curv = terrain.curvature_class || 'PLANAR';

  setText('slope-val', slope);
  setText('twi-val', twi);
  setText('curv-badge', curv);

  // 5. Pillar 4: Anthropogenic Factors
  const roadCut = anthro.road_cut_present ? (anthro.cut_slope_deg ? `${anthro.cut_slope_deg}° Cut` : 'Cut Present') : 'Natural';
  const cutSev = anthro.road_cut_severity || 'NONE';
  const drainage = anthro.drainage_condition === 'BLOCKED_CONCENTRATED_RUNOFF' ? 'Blocked' : 'Free';

  setText('road-cut-val', roadCut);
  setText('cut-severity', cutSev);
  setText('drainage-val', drainage);

  // 6. Advisory Box
  const advText = document.getElementById('advisory-text');
  if (advText) {
    const action = risk.operational_action || (
      level === 'CRITICAL' ? 'EMERGENCY: Immediate evacuation of slope toe zone recommended.' :
      level === 'HIGH' ? 'WARNING: High antecedent saturation combined with steep terrain.' :
      level === 'WATCH' ? 'ADVISORY: Monitor localized drainage culverts and road cut stability.' :
      'Routine monitoring; baseline environmental conditions stable.'
    );
    advText.textContent = action;
  }

  // 7. Last updated timestamp
  setText('last-updated', `Updated: ${new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`);
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

/**
 * Update the extension toolbar badge.
 */
function updateBadge(riskLevel) {
  const badgeText = riskLevel === 'CRITICAL' ? 'CRIT' : riskLevel;
  const colors = {
    LOW: '#10b981',
    WATCH: '#f59e0b',
    HIGH: '#f97316',
    CRITICAL: '#ef4444'
  };

  if (chrome && chrome.action && chrome.action.setBadgeText) {
    chrome.action.setBadgeText({ text: badgeText });
    chrome.action.setBadgeBackgroundColor({ color: colors[riskLevel] || '#10b981' });
  }

  // Send message to background service worker
  if (chrome && chrome.runtime && chrome.runtime.sendMessage) {
    try {
      chrome.runtime.sendMessage({ type: 'RISK_UPDATE', level: riskLevel, text: badgeText, color: colors[riskLevel] });
    } catch (e) {
      // Ignored
    }
  }
}

// Storage helpers
function getStorage(key) {
  return new Promise((resolve) => {
    if (chrome && chrome.storage && chrome.storage.local) {
      chrome.storage.local.get([key], (res) => resolve(res[key]));
    } else {
      resolve(localStorage.getItem(key));
    }
  });
}

function setStorage(key, value) {
  if (chrome && chrome.storage && chrome.storage.local) {
    chrome.storage.local.set({ [key]: value });
  } else {
    localStorage.setItem(key, value);
  }
}
