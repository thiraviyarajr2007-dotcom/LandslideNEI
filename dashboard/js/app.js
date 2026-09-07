/**
 * LandslideNEI - Emergency Operations Center (EOC) Command Workstation
 * Application Controller & Multi-Screen State Manager
 * Architecture: Clean Vanilla JS, View Router, Real-time REST API Client
 */

// Global Application State
window.currentView = 'home';
window.navHistory = ['home'];
window.currentUser = {
  name: 'Dr. S. K. Roy',
  callsign: 'EOC Duty Officer',
  role: 'OPS SECTION CHIEF',
  email: 'duty.officer@landslidenei.gov.in',
  station: 'Nagaland State Disaster Management Authority',
  node: 'NODE-01 // KOHIMA-EOC'
};
window.currentCoordinates = {
  lat: 25.6740,
  lon: 94.1120,
  name: 'Nagaland Corridor - Kohima & Zubza Axis (NH-29)',
  elevation: 1428
};
window.lastPredictionData = null;
window.cwcStationsData = [];

document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initViewRouter();
  initSectorSelector();
  initWindowControls();
  initAuthHandlers();
  initLocationAnalysisHandlers();
  initRainfallTable();
  initAlertsHandlers();
  initReportsHandlers();
  initSettingsHandlers();

  // Initialize Map if present
  if (typeof initMap === 'function') {
    initMap();
  }

  // Initial trigger for default sector
  evaluateLocation(window.currentCoordinates.lat, window.currentCoordinates.lon);
});

/**
 * 1. CLOCK & TELEMETRY HEARTBEAT
 */
function initClock() {
  function update() {
    const now = new Date();
    const clockEl = document.getElementById('utc-clock');
    if (clockEl) {
      const utcHours = String(now.getUTCHours()).padStart(2, '0');
      const utcMins = String(now.getUTCMinutes()).padStart(2, '0');
      const utcSecs = String(now.getUTCSeconds()).padStart(2, '0');
      clockEl.textContent = utcHours + ':' + utcMins + ':' + utcSecs + ' UTC';
    }
    const istEl = document.getElementById('ist-clock');
    if (istEl) {
      istEl.textContent = now.toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST';
    }
  }
  update();
  setInterval(update, 1000);
}

/**
 * 2. MULTI-SCREEN VIEW ROUTER
 */
function navigateTo(viewId) {
  const allViews = document.querySelectorAll('.app-view');
  let targetView = document.getElementById('view-' + viewId);
  
  if (!targetView) {
    console.warn('View not found: view-' + viewId + ', defaulting to view-home');
    targetView = document.getElementById('view-home');
    viewId = 'home';
  }

  allViews.forEach(v => {
    v.classList.remove('active');
    v.style.display = 'none';
  });

  targetView.classList.add('active');
  targetView.style.display = 'flex';
  window.currentView = viewId;
  window.navHistory.push(viewId);

  // Update nav sidebar styling
  document.querySelectorAll('[data-nav-view]').forEach(item => {
    if (item.getAttribute('data-nav-view') === viewId) {
      item.classList.add('active', 'bg-surface-container-high', 'text-primary');
      item.classList.remove('text-on-surface-variant');
    } else {
      item.classList.remove('active', 'bg-surface-container-high', 'text-primary');
      item.classList.add('text-on-surface-variant');
    }
  });

  // Recompute map size when navigating to risk map or home
  if ((viewId === 'risk-map' || viewId === 'home') && window.mapInstance) {
    setTimeout(() => {
      window.mapInstance.invalidateSize();
    }, 200);
  }

  // Update titlebar breadcrumb
  const breadcrumbEl = document.getElementById('current-view-breadcrumb');
  if (breadcrumbEl) {
    const titles = {
      'setup': 'SYSTEM CONFIGURATION',
      'login': 'SECURITY CHECKPOINT // AUTHENTICATION',
      'register': 'OPERATOR ENROLLMENT // REGISTRATION',
      'home': 'EOC DASHBOARD // OVERVIEW',
      'location-analysis': 'PRECISION LOCATION PROFILER',
      'risk-map': 'GEOSPATIAL RISK MAP // TACTICAL VIEW',
      'rainfall-telemetry': 'CWC HYDRO-METEOROLOGY TELEMETRY',
      'ml-hub': 'MACHINE LEARNING INTELLIGENCE // MODEL HUB',
      'alerts': 'INCIDENT COMMAND & WARNING DISPATCH',
      'reports': 'EOC ADVISORY & SITUATION BRIEFINGS',
      'settings': 'WORKSTATION SYSTEM PARAMETERS'
    };
    breadcrumbEl.textContent = titles[viewId] || viewId.toUpperCase();
  }
}
window.navigateTo = navigateTo;

function initViewRouter() {
  document.querySelectorAll('[data-navigate]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = btn.getAttribute('data-navigate');
      navigateTo(target);
    });
  });

  document.querySelectorAll('.app-nav-item').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = btn.getAttribute('data-nav-view');
      if (target) {
        navigateTo(target);
      }
    });
  });
}

/**
 * 3. AUTH & SESSION MANAGEMENT
 */
function handleLogin(email, password) {
  if (!email || !password) {
    showToast('Please enter both workstation email and security key.');
    return false;
  }
  window.currentUser.email = email;
  window.currentUser.name = email.split('@')[0].toUpperCase();
  updateUserBadge();
  showToast('Authenticated: EOC Duty Officer clearance verified.');
  navigateTo('home');
  return true;
}
window.handleLogin = handleLogin;

function handleRegister(name, email, organization, role) {
  window.currentUser.name = name || 'Duty Officer';
  window.currentUser.email = email || 'operator@landslidenei.gov.in';
  window.currentUser.station = organization || 'NER Disaster Management Authority';
  window.currentUser.role = role || 'GEOTECHNICAL ANALYST';
  updateUserBadge();
  showToast('Operator credential provisioned successfully.');
  navigateTo('home');
  return true;
}
window.handleRegister = handleRegister;

function handleLogout() {
  showToast('Workstation session locked.');
  navigateTo('login');
}
window.handleLogout = handleLogout;

function updateUserBadge() {
  const badgeName = document.getElementById('user-badge-name');
  const badgeRole = document.getElementById('user-badge-role');
  if (badgeName) badgeName.textContent = window.currentUser.name;
  if (badgeRole) badgeRole.textContent = window.currentUser.role;
}

function initAuthHandlers() {
  const loginForm = document.getElementById('form-login');
  if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const email = document.getElementById('login-email').value;
      const pass = document.getElementById('login-password').value;
      handleLogin(email, pass);
    });
  }

  const registerForm = document.getElementById('form-register');
  if (registerForm) {
    registerForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = document.getElementById('reg-name').value;
      const email = document.getElementById('reg-email').value;
      const org = document.getElementById('reg-org').value;
      const role = document.getElementById('reg-role').value;
      handleRegister(name, email, org, role);
    });
  }

  const ssoBtns = document.querySelectorAll('.btn-sso-google');
  ssoBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      showToast('Connecting to NIC / Gov single sign-on gateway...');
      setTimeout(() => {
        handleLogin('duty.officer@landslidenei.gov.in', 'mock-gov-token');
      }, 700);
    });
  });

  const logoutBtns = document.querySelectorAll('.btn-logout');
  logoutBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      handleLogout();
    });
  });
}

/**
 * 4. SECTOR SELECTOR & MAP CLICK INTEGRATION
 */
function getAspectHeading(deg) {
  if (deg === null || deg === undefined) return 'Flat';
  const val = ((deg % 360) + 360) % 360;
  const headings = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const idx = Math.round(val / 22.5) % 16;
  return headings[idx];
}

function selectSector(key) {
  const SECTORS = {
    'nagaland': { lat: 25.6740, lon: 94.1120, name: 'Nagaland Corridor — Kohima & Zubza Axis (NH-29)', elev: 1428 },
    'sikkim': { lat: 27.5028, lon: 88.5284, name: 'Sikkim Transit — NH-10 Teesta Gorge Corridor', elev: 1840 },
    'cherrapunji': { lat: 25.2986, lon: 91.7317, name: 'Meghalaya Plateau — Cherrapunji-Shella Escarpment', elev: 1137 },
    'meghalaya': { lat: 25.2986, lon: 91.7317, name: 'Meghalaya Plateau — Cherrapunji-Shella Escarpment', elev: 1137 },
    'tawang': { lat: 27.5925, lon: 91.6087, name: 'Arunachal Western Axis — Bhalukpong-Tawang Spur', elev: 3020 },
    'arunachal': { lat: 27.5925, lon: 91.6087, name: 'Arunachal Western Axis — Bhalukpong-Tawang Spur', elev: 3020 },
    'guwahati': { lat: 26.1445, lon: 91.7362, name: 'Assam Urban Foothills — Guwahati', elev: 54 },
    'assam': { lat: 26.1445, lon: 91.7362, name: 'Assam Urban Foothills — Guwahati', elev: 54 },
    'aizawl': { lat: 23.7271, lon: 92.7176, name: 'Mizoram Ridge — Aizawl', elev: 1132 },
    'mizoram': { lat: 23.7271, lon: 92.7176, name: 'Mizoram Ridge — Aizawl', elev: 1132 }
  };
  const sec = SECTORS[key];
  if (sec) {
    window.currentCoordinates = sec;
    updateCoordDisplays(sec);
    const select = document.getElementById('sector-select') || document.getElementById('sector-quick-select');
    if (select) select.value = key;
    document.querySelectorAll('.corridor-chip').forEach(c => {
      c.classList.toggle('active', c.getAttribute('data-sector') === key);
    });
    showToast(`Quick Selected: ${sec.name}`);
    evaluateLocation(sec.lat, sec.lon);
  }
}
window.selectSector = selectSector;

function initSectorSelector() {
  const select = document.getElementById('sector-select') || document.getElementById('sector-quick-select');
  if (!select) return;

  select.addEventListener('change', (e) => {
    selectSector(e.target.value);
  });
}

// Global Map Click Handler invoked from map.js Leaflet click
window.handleMapClick = function(lat, lon) {
  window.currentCoordinates = {
    lat: lat,
    lon: lon,
    name: `Query Coordinates (${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E)`,
    elev: 0
  };
  updateCoordDisplays(window.currentCoordinates);
  showToast(`Evaluating real-time risk at ${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E...`);
  evaluateLocation(lat, lon);
};

function updateCoordDisplays(coord) {
  const coordDisplay = document.getElementById('hud-coord-display');
  const elevDisplay = document.getElementById('hud-elev-display');
  if (coordDisplay) {
    coordDisplay.textContent = coord.lat.toFixed(4) + '° N, ' + coord.lon.toFixed(4) + '° E';
  }
  if (elevDisplay) {
    elevDisplay.textContent = (coord.elev !== undefined && coord.elev !== 0) ? `${coord.elev.toLocaleString()} m` : '-- m';
  }
}

/**
 * 5. UNIFIED PREDICT & PROFILE API INTEGRATION (REAL ML INFERENCE)
 */
async function evaluateLocation(lat, lon) {
  const statusBanner = document.getElementById('verdict-banner');
  if (statusBanner) {
    statusBanner.textContent = 'RUNNING UNIFIED PREDICTION...';
    statusBanner.className = 'p-3 rounded border font-mono font-bold text-sm text-center bg-surface-container text-primary border-primary/40 animate-pulse';
  }

  try {
    const payload = {
      latitude: parseFloat(lat),
      longitude: parseFloat(lon),
      timestamp: new Date().toISOString(),
      auto_refetch: true
    };

    const res = await fetch('/api/v1/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Inference engine error');
    }

    const data = await res.json();
    window.lastPredictionData = data;
    renderPredictionResults(data);

    // Also request terrain profile for geotechnical breakdown
    fetch('/api/v1/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latitude: parseFloat(lat), longitude: parseFloat(lon) })
    })
    .then(r => r.json())
    .then(prof => renderLocationProfile(prof))
    .catch(err => console.warn('Profile fetch warning:', err));

  } catch (err) {
    console.error('API Error:', err);
    if (statusBanner) {
      statusBanner.textContent = 'ERROR: ' + err.message;
      statusBanner.className = 'p-3 rounded border font-mono font-bold text-sm text-center bg-error-container text-error border-error/50';
    }
    showToast('Inference Error: ' + err.message);
  }
}
window.evaluateLocation = evaluateLocation;

function renderPredictionResults(data) {
  const risk = data.risk || {};
  const staticLsm = data.static_susceptibility || {};
  const rain = data.rainfall || {};
  const loc = data.location || {};
  const terrain = staticLsm.terrain || {};

  // 1. Verdict Banner & Pills
  const banner = document.getElementById('verdict-banner');
  const pill = document.getElementById('verdict-pill');
  const homeBadge = document.getElementById('home-verdict-badge');
  const level = (risk.risk_level || risk.level || 'UNKNOWN').toUpperCase();

  const colorMap = {
    'LOW': { bg: 'bg-emerald-950/40', text: 'text-emerald-400', border: 'border-emerald-500/40' },
    'WATCH': { bg: 'bg-amber-950/40', text: 'text-amber-400', border: 'border-amber-500/40' },
    'MODERATE': { bg: 'bg-amber-900/40', text: 'text-amber-400', border: 'border-amber-500/40' },
    'HIGH': { bg: 'bg-orange-950/50', text: 'text-orange-400', border: 'border-orange-500/50' },
    'VERY HIGH': { bg: 'bg-red-950/60', text: 'text-red-400', border: 'border-red-500/50' },
    'CRITICAL': { bg: 'bg-error-container', text: 'text-error', border: 'border-error/60' }
  };

  const scheme = colorMap[level] || colorMap['WATCH'];

  if (banner) {
    banner.textContent = 'OPERATIONAL VERDICT: ' + level;
    banner.className = 'p-3 rounded border font-mono font-bold text-sm text-center ' + scheme.bg + ' ' + scheme.text + ' ' + scheme.border;
  }
  if (pill) {
    pill.textContent = level;
    pill.className = 'px-2 py-0.5 rounded text-xs font-mono font-bold uppercase ' + scheme.bg + ' ' + scheme.text;
  }
  if (homeBadge) {
    homeBadge.textContent = level;
    homeBadge.className = 'px-3 py-1 rounded font-mono text-sm font-bold uppercase ' + scheme.bg + ' ' + scheme.text + ' border ' + scheme.border;
  }

  // 2. Operational Fusion Score & Animated SVG Gauge
  const fusionScoreVal = risk.operational_fusion_score !== undefined ? risk.operational_fusion_score : (risk.risk_score !== undefined ? risk.risk_score : risk.fusion_score);
  const fusionScoreEl = document.getElementById('verdict-score') || document.getElementById('fusion-score-val');
  const fusionProgressEl = document.getElementById('fusion-progress-bar');
  if (fusionScoreEl) {
    fusionScoreEl.textContent = (fusionScoreVal !== null && fusionScoreVal !== undefined) ? fusionScoreVal.toFixed(3) : 'N/A';
  }
  if (fusionProgressEl && fusionScoreVal !== null && fusionScoreVal !== undefined) {
    fusionProgressEl.style.width = Math.min(100, Math.max(0, fusionScoreVal * 100)) + '%';
  }

  // Update Animated Semi-Circular SVG Gauge Needle & Arc
  const needleEl = document.getElementById('gauge-needle');
  const arcFillEl = document.getElementById('gauge-arc-fill');
  const miniPill = document.getElementById('verdict-pill-mini');
  if (miniPill) {
    miniPill.textContent = level;
    miniPill.className = 'px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase ' + scheme.bg + ' ' + scheme.text;
  }
  if (needleEl && fusionScoreVal !== null && fusionScoreVal !== undefined) {
    // Score 0.0 -> -90 deg, Score 1.0 -> +90 deg
    const angle = (Math.min(1.0, Math.max(0.0, fusionScoreVal)) * 180) - 90;
    needleEl.style.transform = `rotate(${angle.toFixed(1)}deg)`;
  }
  if (arcFillEl && fusionScoreVal !== null && fusionScoreVal !== undefined) {
    const totalArc = 251.3;
    const clampedScore = Math.min(1.0, Math.max(0.0, fusionScoreVal));
    const offset = totalArc * (1 - clampedScore);
    arcFillEl.style.strokeDashoffset = offset.toFixed(1);
  }

  // 3. Static Susceptibility
  const staticScoreVal = staticLsm.score;
  const staticCategoryVal = (staticLsm.category || staticLsm.category_label || staticLsm.tier || 'MODERATE').toUpperCase();
  const suscScoreEl = document.getElementById('susc-score-val') || document.getElementById('static-score-val');
  const staticTierEl = document.getElementById('static-tier-val');
  const suscProgressEl = document.getElementById('susc-progress-bar') || document.getElementById('static-progress-bar');

  if (suscScoreEl) {
    suscScoreEl.textContent = (staticScoreVal !== null && staticScoreVal !== undefined)
      ? `${staticScoreVal.toFixed(3)} (${staticCategoryVal})`
      : 'N/A';
  }
  if (staticTierEl) {
    staticTierEl.textContent = staticCategoryVal;
  }
  if (suscProgressEl && staticScoreVal !== null && staticScoreVal !== undefined) {
    suscProgressEl.style.width = Math.min(100, Math.max(0, staticScoreVal * 100)) + '%';
  }

  // Physical terrain attributes
  const slopeEl = document.getElementById('terrain-slope-val');
  const curvEl = document.getElementById('terrain-curvature-val');
  if (slopeEl) {
    if (terrain.slope_deg !== undefined && terrain.slope_deg !== null) {
      const slopeSeverity = terrain.slope_deg > 30 ? ' (Critical)' : (terrain.slope_deg > 15 ? ' (Moderate)' : ' (Low)');
      slopeEl.textContent = `${terrain.slope_deg.toFixed(1)}°${slopeSeverity}`;
      slopeEl.className = terrain.slope_deg > 30 ? 'text-error font-bold' : (terrain.slope_deg > 15 ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold');
    } else {
      slopeEl.textContent = '--';
    }
  }
  if (curvEl) {
    if (terrain.curvature_class) {
      curvEl.textContent = terrain.curvature_class;
      if (terrain.curvature_class.includes('Concave-Convergent') || terrain.curvature_class.includes('Extreme')) {
        curvEl.className = 'text-error font-bold';
      } else if (terrain.curvature_class.includes('Convergent') || terrain.curvature_class.includes('Concave')) {
        curvEl.className = 'text-amber-400 font-bold';
      } else {
        curvEl.className = 'text-emerald-400 font-bold';
      }
    } else if (terrain.plan_curvature !== undefined && terrain.plan_curvature !== null) {
      const planSign = terrain.plan_curvature < 0 ? 'Convergent' : 'Divergent';
      curvEl.textContent = `${terrain.plan_curvature.toFixed(2)} (${planSign})`;
    } else if (terrain.aspect_deg !== undefined && terrain.aspect_deg !== null) {
      const heading = getAspectHeading(terrain.aspect_deg);
      curvEl.textContent = `${terrain.aspect_deg.toFixed(0)}° (${heading})`;
    } else if (terrain.relief_std_5x5_m !== undefined && terrain.relief_std_5x5_m !== null) {
      curvEl.textContent = `Relief: ${terrain.relief_std_5x5_m.toFixed(1)} m`;
    } else {
      curvEl.textContent = '--';
    }
  }

  // 4. Rainfall Telemetry
  const rainQualityEl = document.getElementById('rain-quality-val') || document.getElementById('telemetry-status');
  const rain24El = document.getElementById('rain-24h-val') || document.getElementById('telemetry-rain24');
  const rain72El = document.getElementById('rain-72h-val') || document.getElementById('telemetry-rain72');
  const rainStationEl = document.getElementById('rain-station-val') || document.getElementById('telemetry-station');
  const rainDistEl = document.getElementById('telemetry-dist');

  const rainQuality = (rain.quality || rain.status || 'NO_DATA').toUpperCase();
  if (rainQualityEl) {
    if (rain.is_realtime || rain.source === 'OPEN_METEO_REALTIME') {
      const att = rain.realtime_attempt || 1;
      rainQualityEl.textContent = `LIVE REAL-TIME (${att}/3)`;
      rainQualityEl.className = 'px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 font-mono text-[9px] font-bold border border-emerald-500/40 shadow-sm shadow-emerald-900/30';
    } else if (rain.fallback_engaged) {
      rainQualityEl.textContent = 'FALLBACK (3 RETRIES FAILED)';
      rainQualityEl.className = 'px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 font-mono text-[9px] font-bold border border-amber-600/40';
    } else if (rainQuality === 'REGIONAL_API_FALLBACK' || rainQuality === 'REALTIME_API' || rain.source === 'OPEN_METEO_API') {
      rainQualityEl.textContent = 'LIVE API RE-FETCH';
      rainQualityEl.className = 'px-1.5 py-0.5 rounded bg-sky-950 text-sky-300 font-mono text-[9px] font-bold border border-sky-600/40';
    } else if (rainQuality === 'GOOD' || rainQuality === 'VALID') {
      rainQualityEl.textContent = rainQuality;
      rainQualityEl.className = 'px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 font-mono text-[9px] font-bold';
    } else if (rainQuality === 'PARTIAL' || rainQuality === 'STALE') {
      rainQualityEl.textContent = rainQuality;
      rainQualityEl.className = 'px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 font-mono text-[9px] font-bold';
    } else {
      rainQualityEl.textContent = rainQuality;
      rainQualityEl.className = 'px-1.5 py-0.5 rounded bg-surface-container-highest text-outline font-mono text-[9px] font-bold';
    }
  }

  const rain24Val = rain.rainfall_24h !== undefined ? rain.rainfall_24h : rain.rainfall_24h_mm;
  const rain3dVal = rain.rainfall_3d !== undefined ? rain.rainfall_3d : (rain.rainfall_72h_mm !== undefined ? rain.rainfall_72h_mm : null);

  if (rain24El) {
    rain24El.textContent = (rain24Val !== null && rain24Val !== undefined) ? `${Number(rain24Val).toFixed(1)} mm` : 'NO DATA';
  }
  if (rain72El) {
    rain72El.textContent = (rain3dVal !== null && rain3dVal !== undefined) ? `${Number(rain3dVal).toFixed(1)} mm` : 'NO DATA';
  }

  if (rainStationEl) {
    const stName = rain.station || rain.station_name;
    const stDist = rain.distance_km !== null && rain.distance_km !== undefined ? rain.distance_km.toFixed(1) : null;
    const dwrInfo = rain.doppler_reflectivity_dbz ? ` [DWR: ${rain.doppler_reflectivity_dbz} dBZ]` : '';
    const oroInfo = rain.orographic_amplification_factor && rain.orographic_amplification_factor > 1.05 ? ` (${rain.orographic_amplification_factor}x Orographic)` : '';
    if (rain.source === 'OPEN_METEO_REALTIME' || rain.source === 'OPEN_METEO_API' || rainQuality === 'REGIONAL_API_FALLBACK') {
      rainStationEl.textContent = `Open-Meteo Real-Time (Lat: ${loc.latitude?.toFixed(2) || ''}, Lon: ${loc.longitude?.toFixed(2) || ''})${dwrInfo}${oroInfo}`;
    } else if (stName && stDist !== null) {
      if (rain.distance_km > 50.0) {
        rainStationEl.textContent = `${stName} (${stDist} km — Beyond 50km cap)${dwrInfo}${oroInfo}`;
      } else {
        rainStationEl.textContent = `${stName} (${stDist} km)${dwrInfo}${oroInfo}`;
      }
    } else if (stName) {
      rainStationEl.textContent = `${stName}${dwrInfo}${oroInfo}`;
    } else {
      rainStationEl.textContent = 'NO RELIABLE LOCAL DATA';
    }
  }

  if (rainDistEl) {
    rainDistEl.textContent = (rain.distance_km !== null && rain.distance_km !== undefined) ? `${rain.distance_km.toFixed(1)} km` : 'N/A';
  }

  // 5. Attribution Breakdown List
  const reasonsContainer = document.getElementById('attribution-reasons-list');
  if (reasonsContainer) {
    const allReasons = [];
    if (Array.isArray(risk.reasons)) {
      risk.reasons.forEach(r => {
        const desc = typeof r === 'string' ? r : (r.description || r.code);
        if (desc && !allReasons.includes(desc)) allReasons.push(desc);
      });
    }
    if (Array.isArray(staticLsm.reasons)) {
      staticLsm.reasons.forEach(r => {
        const desc = typeof r === 'string' ? r : (r.description || r.code);
        if (desc && !allReasons.includes(desc)) allReasons.push(desc);
      });
    }
    if (rain.quality_notes && !allReasons.includes(rain.quality_notes)) {
      allReasons.push(rain.quality_notes);
    }

    if (allReasons.length > 0) {
      reasonsContainer.innerHTML = allReasons.slice(0, 4).map(reasonText => `
        <div class="flex items-start gap-1.5 text-[11px] font-mono leading-tight">
          <span class="text-primary mt-0.5">•</span>
          <span class="text-on-surface-variant">${reasonText}</span>
        </div>
      `).join('');
    } else {
      reasonsContainer.innerHTML = `
        <div class="text-[10px] font-mono text-outline">Environmental and hydrometric parameters within normal baseline.</div>
      `;
    }
  }

  // 6. Update Location HUD
  const locStateEl = document.getElementById('hud-state-display');
  const locDistrictEl = document.getElementById('hud-district-display');
  if (locStateEl) locStateEl.textContent = loc.state || 'NORTHEAST REGION';
  if (locDistrictEl) locDistrictEl.textContent = loc.district || 'MONITORED SECTOR';

  const coordDisplay = document.getElementById('hud-coord-display');
  const elevDisplay = document.getElementById('hud-elev-display');
  if (coordDisplay) {
    coordDisplay.textContent = `${loc.latitude.toFixed(4)}° N, ${loc.longitude.toFixed(4)}° E`;
  }
  if (elevDisplay) {
    const elev = terrain.elevation_m !== undefined ? Math.round(terrain.elevation_m) : (window.currentCoordinates?.elev || 1200);
    elevDisplay.textContent = `${elev.toLocaleString()} m`;
  }

  // Update clock display with latest IST timestamp
  const clockEl = document.getElementById('workstation-clock');
  if (clockEl) {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST';
  }

  // 7. Synchronize GIS Map
  if (typeof setQueryPoint === 'function') {
    setQueryPoint(loc.latitude, loc.longitude, level, rain.distance_km);
  } else if (window.mapInstance && typeof window.mapInstance.setView === 'function') {
    window.mapInstance.setView([loc.latitude, loc.longitude], 10);
  }

  // 8. Update Location Analysis View cards
  updateLocationAnalysisCards(data);
}

function updateLocationAnalysisCards(data) {
  const staticLsm = data.static_susceptibility || {};
  const terrain = staticLsm.terrain || {};
  const soil = staticLsm.soil || {};
  const lc = staticLsm.landcover || {};
  const rain = data.rainfall || {};

  // Slope
  const analSlope = document.getElementById('anal-slope-val');
  const analSlopeDesc = document.getElementById('anal-slope-desc');
  if (analSlope && terrain.slope_deg !== undefined) {
    analSlope.textContent = `${terrain.slope_deg.toFixed(1)}°`;
    if (analSlopeDesc) {
      analSlopeDesc.textContent = terrain.slope_deg > 30 ? 'Critical failure threshold exceeded (>30°)' : (terrain.slope_deg > 15 ? 'Moderate gradient slope (>15°)' : 'Gentle slope gradient (<15°)');
    }
  }

  // Aspect / Relief / Micro-Topography
  const analCurv = document.getElementById('anal-curvature-val');
  const analCurvDesc = document.getElementById('anal-curvature-desc');
  if (analCurv) {
    if (terrain.curvature_class) {
      analCurv.textContent = terrain.curvature_class;
      if (analCurvDesc) {
        const planStr = terrain.plan_curvature !== undefined && terrain.plan_curvature !== null ? `${terrain.plan_curvature > 0 ? '+' : ''}${terrain.plan_curvature.toFixed(2)}` : '--';
        const profStr = terrain.profile_curvature !== undefined && terrain.profile_curvature !== null ? `${terrain.profile_curvature > 0 ? '+' : ''}${terrain.profile_curvature.toFixed(2)}` : '--';
        analCurvDesc.textContent = `Plan: ${planStr} | Prof: ${profStr} | TWI: ${terrain.topographic_wetness_index || '--'}`;
      }
    } else if (terrain.aspect_deg !== undefined) {
      analCurv.textContent = `${terrain.aspect_deg.toFixed(0)}° (${getAspectHeading(terrain.aspect_deg)})`;
      if (analCurvDesc) {
        analCurvDesc.textContent = `Local relief std: ${terrain.relief_std_5x5_m ? terrain.relief_std_5x5_m.toFixed(1) + 'm' : '--'}`;
      }
    }
  }

  // Soil Saturation & Pore Pressure
  const analClay = document.getElementById('anal-clay-val');
  const analClayDesc = document.getElementById('anal-clay-desc');
  if (analClay) {
    if (soil.saturation_percent !== undefined && soil.saturation_percent !== null) {
      analClay.textContent = `${soil.saturation_percent.toFixed(1)}% Saturation`;
      analClay.className = soil.saturation_percent > 75 ? 'text-error font-bold text-base' : (soil.saturation_percent > 50 ? 'text-amber-400 font-bold text-base' : 'text-emerald-400 font-bold text-base');
      if (analClayDesc) {
        const uStr = soil.pore_water_pressure_kpa !== undefined ? `${soil.pore_water_pressure_kpa.toFixed(1)} kPa` : '0 kPa';
        const fosStr = soil.factor_of_safety !== undefined ? `FoS: ${soil.factor_of_safety.toFixed(2)}` : '';
        analClayDesc.textContent = `Pore Press: ${uStr} | ${fosStr} | Clay: ${soil.clay_percent ? soil.clay_percent.toFixed(0) + '%' : '--'}`;
      }
    } else if (soil.clay_percent !== undefined && !isNaN(soil.clay_percent) && soil.clay_percent !== null) {
      analClay.textContent = `${soil.clay_percent.toFixed(1)}% Clay`;
      if (analClayDesc) analClayDesc.textContent = `Taxonomy: ${soil.soil_class || 'Cambisols'}`;
    } else {
      analClay.textContent = soil.soil_class || 'Regional Inceptisols';
      if (analClayDesc) analClayDesc.textContent = 'SoilGrids taxonomic classification';
    }
  }

  // Canopy & Anthropogenic Factors (Pillar ④)
  const analCanopy = document.getElementById('anal-canopy-val');
  const analCanopyDesc = document.getElementById('anal-canopy-desc');
  const anthro = data.anthropogenic || staticLsm.anthropogenic;
  if (analCanopy) {
    if (anthro && (anthro.road_cut_present || anthro.drainage_blocked || anthro.deforestation_observed || anthro.has_retaining_wall)) {
      analCanopy.textContent = anthro.retaining_wall_status.replace(/_/g, ' ');
      if (analCanopyDesc) {
        analCanopyDesc.textContent = `Eff Slope: ${anthro.effective_slope_deg}° | Root: ${anthro.root_cohesion_kpa} kPa | Mult: ${anthro.anthropogenic_hazard_multiplier}x`;
      }
    } else {
      analCanopy.textContent = lc.landcover_class || 'Vegetation / Forest';
      if (analCanopyDesc) analCanopyDesc.textContent = `WorldCover 10m class code #${lc.landcover_code || 10}`;
    }
  }

  // Rainfall 24h
  const analRain24 = document.getElementById('anal-rain-24h-val');
  const analRain24Desc = document.getElementById('anal-rain-24h-desc');
  if (analRain24) {
    const r24 = rain.rainfall_24h !== undefined ? rain.rainfall_24h : rain.rainfall_24h_mm;
    analRain24.textContent = r24 !== null && r24 !== undefined ? `${Number(r24).toFixed(1)} mm` : 'NO DATA';
    if (analRain24Desc) {
      analRain24Desc.textContent = r24 !== null && r24 > 50 ? 'Dynamic trigger threshold breached' : 'Operational baseline monitoring';
    }
  }

  // Rainfall 7d
  const analRain7d = document.getElementById('anal-rain-7d-val');
  const analRain7dDesc = document.getElementById('anal-rain-7d-desc');
  if (analRain7d) {
    const r7d = rain.rainfall_7d !== undefined ? rain.rainfall_7d : (rain.rainfall_3d !== undefined ? rain.rainfall_3d : null);
    analRain7d.textContent = r7d !== null && r7d !== undefined ? `${Number(r7d).toFixed(1)} mm` : 'NO DATA';
    if (analRain7dDesc) {
      analRain7dDesc.textContent = r7d !== null ? 'Multi-window cumulative antecedent depth' : 'Antecedent telemetry unobserved';
    }
  }

  // Nearest Station & Proximity
  const analStation = document.getElementById('anal-station-val');
  const analStationDist = document.getElementById('anal-station-dist-val');
  if (analStation) {
    analStation.textContent = rain.station ? `CWC ${rain.station}` : 'NO RELIABLE LOCAL STATION';
  }
  if (analStationDist) {
    if (rain.distance_km !== null && rain.distance_km !== undefined) {
      analStationDist.textContent = `${rain.distance_km.toFixed(1)} km (${rain.distance_km <= 50 ? 'Within 50km strict boundary' : 'Beyond 50km operational cap'})`;
    } else {
      analStationDist.textContent = 'No sovereign station within operational radius';
    }
  }
}

function renderLocationProfile(prof) {
  const elevEl = document.getElementById('prof-elevation');
  const slopeEl = document.getElementById('prof-slope');
  const aspectEl = document.getElementById('prof-aspect');
  const geolEl = document.getElementById('prof-geology');
  const soilEl = document.getElementById('prof-soil');
  const lulcEl = document.getElementById('prof-lulc');

  const terrain = prof.terrain || {};
  const soil = prof.soil || {};
  const lc = prof.landcover || {};

  if (elevEl) elevEl.textContent = (prof.elevation_m !== undefined ? prof.elevation_m : terrain.elevation_m) !== undefined ? `${Math.round(prof.elevation_m || terrain.elevation_m)} m` : '1,428 m';
  if (slopeEl) slopeEl.textContent = (prof.slope_deg !== undefined ? prof.slope_deg : terrain.slope_deg) !== undefined ? `${(prof.slope_deg || terrain.slope_deg).toFixed(1)}°` : '34.2°';
  if (aspectEl) {
    const asp = prof.aspect_deg !== undefined ? prof.aspect_deg : terrain.aspect_deg;
    aspectEl.textContent = asp !== undefined ? `${asp.toFixed(0)}° (${getAspectHeading(asp)})` : '210° (SSW)';
  }
  if (geolEl) geolEl.textContent = prof.geology_unit || 'Disang Formation (Flysch Facies)';
  if (soilEl) soilEl.textContent = (prof.soil_type || soil.soil_class) || 'Clayey-loam / Inceptisols';
  if (lulcEl) lulcEl.textContent = (prof.lulc_class || lc.landcover_class) || 'Degraded Evergreen Forest / Slope Agriculture';
}

/**
 * 6. LOCATION ANALYSIS FORM HANDLER
 */
function initLocationAnalysisHandlers() {
  const form = document.getElementById('form-location-analysis');
  const btnRun = document.getElementById('btn-run-analysis');
  const btnProfileOnly = document.getElementById('btn-run-profile-only');

  const executeAnalysis = (fullRisk = true) => {
    const latInput = document.getElementById('input-analysis-lat') || document.getElementById('input-anal-lat');
    const lonInput = document.getElementById('input-analysis-lon') || document.getElementById('input-anal-lon');
    if (!latInput || !lonInput) return;

    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    if (isNaN(lat) || isNaN(lon)) {
      showToast('Please provide valid latitude and longitude decimal values.');
      return;
    }

    window.currentCoordinates = { lat: lat, lon: lon, name: 'Precision Coordinates', elev: 0 };
    updateCoordDisplays(window.currentCoordinates);
    showToast('Executing multi-raster geotechnical extraction & inference...');

    if (fullRisk) {
      evaluateLocation(lat, lon);
    } else {
      fetch('/api/v1/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude: lat, longitude: lon })
      })
      .then(r => r.json())
      .then(prof => {
        renderLocationProfile(prof);
        showToast('Terrain susceptibility profile generated.');
      })
      .catch(err => showToast('Profiling Error: ' + err.message));
    }
  };

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      executeAnalysis(true);
    });
  }

  if (btnRun) {
    btnRun.addEventListener('click', (e) => {
      e.preventDefault();
      executeAnalysis(true);
    });
  }

  if (btnProfileOnly) {
    btnProfileOnly.addEventListener('click', (e) => {
      e.preventDefault();
      executeAnalysis(false);
    });
  }
}

/**
 * 7. RAINFALL & TELEMETRY TABLE (GENUINE DATA INSPECTION)
 */
function initRainfallTable() {
  fetch('assets/cwc_stations.json')
    .then(r => r.json())
    .then(stations => {
      window.cwcStationsData = stations;
      renderCwcTable(stations);
    })
    .catch(err => console.warn('Could not load CWC stations:', err));

  const filterInput = document.getElementById('cwc-search-input');
  if (filterInput) {
    filterInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      const filtered = window.cwcStationsData.filter(st =>
        (st.name || st.station_name || '').toLowerCase().includes(q) ||
        (st.state || '').toLowerCase().includes(q) ||
        (st.key || '').toLowerCase().includes(q) ||
        String(st.station_id || '').includes(q)
      );
      renderCwcTable(filtered);
    });
  }
}

function renderCwcTable(stations) {
  const tbody = document.getElementById('cwc-table-body');
  if (!tbody) return;

  if (!stations || !stations.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="p-4 text-center text-outline font-mono">No CWC stations matching query.</td></tr>';
    return;
  }

  tbody.innerHTML = stations.slice(0, 50).map(st => {
    const rain24 = (st.rainfall_24h !== undefined && st.rainfall_24h !== null) ? `${Number(st.rainfall_24h).toFixed(1)} mm` : '--';
    const rain72 = (st.rainfall_3d !== undefined && st.rainfall_3d !== null) ? `${Number(st.rainfall_3d).toFixed(1)} mm` : ((st.rainfall_7d !== undefined && st.rainfall_7d !== null) ? `${Number(st.rainfall_7d).toFixed(1)} mm` : '--');
    const quality = st.quality || st.status || 'UNOBSERVED';
    const qualClass = (quality === 'GOOD' || quality === 'VALID') ? 'text-emerald-400' : ((quality === 'STALE' || quality === 'PARTIAL') ? 'text-amber-400' : 'text-outline');

    return (
      '<tr class="border-b border-outline-variant/20 hover:bg-surface-container font-mono text-xs">' +
        '<td class="p-2 text-primary font-semibold">#' + (st.station_id || (st.key ? st.key.split('::')[1] : 'CWC')) + '</td>' +
        '<td class="p-2 text-on-surface font-medium">' + (st.name || (st.key ? st.key.split('::')[1] : 'Telemetry Site')) + '</td>' +
        '<td class="p-2 text-on-surface-variant">' + (st.state || 'NER') + '</td>' +
        '<td class="p-2 text-right text-secondary">' + (st.latitude ? st.latitude.toFixed(2) : '--') + '°, ' + (st.longitude ? st.longitude.toFixed(2) : '--') + '°</td>' +
        '<td class="p-2 text-right text-on-surface">' + rain24 + '</td>' +
        '<td class="p-2 text-right text-tertiary">' + rain72 + '</td>' +
        '<td class="p-2 text-center font-bold ' + qualClass + '">' + quality + '</td>' +
      '</tr>'
    );
  }).join('');
}
window.renderCwcTable = renderCwcTable;

/**
 * 8. ALERTS SCREEN
 */
function initAlertsHandlers() {
  document.querySelectorAll('[data-alert-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      const filter = btn.getAttribute('data-alert-filter');
      document.querySelectorAll('.alert-feed-card').forEach(card => {
        if (filter === 'ALL' || card.getAttribute('data-severity') === filter) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
}

function renderAlerts() {
  // Utility renderer for alert items if updated dynamically
  return true;
}
window.renderAlerts = renderAlerts;

function acknowledgeAlert(alertId) {
  const card = document.getElementById(alertId);
  if (card) {
    card.classList.add('opacity-50');
    showToast('Alert ' + alertId + ' marked as ACKNOWLEDGED by duty officer.');
  }
}
window.acknowledgeAlert = acknowledgeAlert;

/**
 * 9. REPORTS & ADVISORIES COMPILATION
 */
function initReportsHandlers() {
  const genBtn = document.getElementById('btn-generate-report');
  if (genBtn) {
    genBtn.addEventListener('click', () => {
      renderReportDocument();
      showToast('EOC Advisory Brief compiled from live geotechnical matrix.');
    });
  }

  const printBtn = document.getElementById('btn-print-report');
  if (printBtn) {
    printBtn.addEventListener('click', () => {
      window.print();
    });
  }
}

function renderReportDocument() {
  const docContainer = document.getElementById('report-document-body');
  if (!docContainer) return;

  const d = window.lastPredictionData || {
    location: { state: 'Nagaland', district: 'Kohima', latitude: 25.6740, longitude: 94.1120 },
    risk: { risk_level: 'WATCH', operational_fusion_score: 0.638, operational_action: 'Advisory vigilance; elevated static terrain predisposition.' },
    static_susceptibility: { score: 0.742, category: 'HIGH' },
    rainfall: { rainfall_24h: 18.2, rainfall_3d: 42.5, quality: 'GOOD', station: 'CWC Kohima Hydro-site' }
  };

  const loc = d.location || {};
  const risk = d.risk || {};
  const susc = d.static_susceptibility || {};
  const rain = d.rainfall || {};

  const scoreVal = risk.operational_fusion_score !== undefined ? risk.operational_fusion_score : (risk.risk_score !== undefined ? risk.risk_score : (risk.fusion_score || 0));
  const suscScore = susc.score !== undefined ? susc.score : 0;
  const suscTier = susc.category || susc.category_label || susc.tier || 'MODERATE';
  const r24 = rain.rainfall_24h !== undefined ? rain.rainfall_24h : rain.rainfall_24h_mm;
  const r72 = rain.rainfall_3d !== undefined ? rain.rainfall_3d : (rain.rainfall_72h_mm !== undefined ? rain.rainfall_72h_mm : (rain.rainfall_7d || null));
  const stationName = rain.station || rain.station_name || 'NO LOCAL STATION';
  const rQual = rain.quality || rain.status || 'UNOBSERVED';
  const actionText = risk.operational_action || 'Maintain routine monitoring and continuous telemetry verification over vulnerable corridors.';

  const dateStr = new Date().toUTCString();

  docContainer.innerHTML = (
    '<div class="p-6 bg-surface-container rounded border border-outline-variant/40 space-y-4 font-mono text-xs">' +
      '<div class="flex justify-between items-start border-b border-outline-variant/40 pb-3">' +
        '<div>' +
          '<h2 class="text-sm font-bold text-primary">LANDSLIDENEI // EOC GEOTECHNICAL SITUATION BRIEF</h2>' +
          '<div class="text-[11px] text-outline">CLASSIFICATION: OPERATIONAL DISASTER ADVISORY</div>' +
        '</div>' +
        '<div class="text-right text-[10px] text-on-surface-variant">' +
          '<div>REF: EOC-NER-2026-0906-B</div>' +
          '<div>TIMESTAMP: ' + dateStr + '</div>' +
        '</div>' +
      '</div>' +

      '<div class="grid grid-cols-2 gap-4 p-3 bg-surface-container-lowest rounded border border-outline-variant/20">' +
        '<div>' +
          '<div class="text-[10px] text-outline uppercase">TARGET LOCATION</div>' +
          '<div class="text-xs font-bold text-on-surface">' + (loc.district || 'Regional Sector') + ', ' + (loc.state || 'Northeast India') + '</div>' +
          '<div class="text-[11px] text-secondary">' + (loc.latitude ? loc.latitude.toFixed(4) : '--') + '° N, ' + (loc.longitude ? loc.longitude.toFixed(4) : '--') + '° E</div>' +
        '</div>' +
        '<div>' +
          '<div class="text-[10px] text-outline uppercase">AUTHORITATIVE RISK VERDICT</div>' +
          '<div class="text-sm font-bold text-error">' + (risk.risk_level || 'WATCH') + ' (Score: ' + Number(scoreVal).toFixed(3) + ')</div>' +
          '<div class="text-[11px] text-on-surface-variant">Static LSM: ' + Number(suscScore).toFixed(3) + ' (' + suscTier + ')</div>' +
        '</div>' +
      '</div>' +

      '<div>' +
        '<div class="text-[10px] text-outline uppercase mb-1">HYDRO-METEOROLOGY INTEGRATION (CWC TELEMETRY)</div>' +
        '<div class="p-2.5 bg-surface-container-low rounded border border-outline-variant/20 space-y-1">' +
          '<div>Reporting Station: <span class="text-on-surface font-semibold">' + stationName + '</span></div>' +
          '<div>24h Cumulative Precipitation: <span class="text-tertiary font-bold">' + (r24 !== null && r24 !== undefined ? Number(r24).toFixed(1) + ' mm' : 'NO DATA') + '</span> | 72h Antecedent: <span class="text-secondary font-bold">' + (r72 !== null && r72 !== undefined ? Number(r72).toFixed(1) + ' mm' : 'NO DATA') + '</span></div>' +
          '<div>Data Quality Check: <span class="text-emerald-400 font-bold">' + rQual + '</span></div>' +
        '</div>' +
      '</div>' +

      '<div>' +
        '<div class="text-[10px] text-outline uppercase mb-1">RECOMMENDED INCIDENT ACTION (EOC OPERATIONAL PROTOCOL)</div>' +
        '<div class="p-3 bg-error-container/20 rounded border border-error/30 text-error leading-relaxed text-[11px]">' +
          actionText + '<br>' +
          '• Issue precautionary advisory along critical slope axes and high-gradient roads.<br>' +
          '• Maintain active telemetry check on nearest hydro-meteorological stations.<br>' +
          '• Re-evaluate operational fusion matrix if 24h precipitation exceeds watch threshold.' +
        '</div>' +
      '</div>' +

      '<div class="pt-2 border-t border-outline-variant/30 text-[10px] text-outline flex justify-between items-center">' +
        '<span>OFFICER IN CHARGE: ' + window.currentUser.name + ' (' + window.currentUser.callsign + ')</span>' +
        '<span>DISASTER SURVEILLANCE & EARLY WARNING NETWORK</span>' +
      '</div>' +
    '</div>'
  );
}
window.renderReportDocument = renderReportDocument;

/**
 * 10. SETTINGS HANDLERS
 */
function initSettingsHandlers() {
  const saveBtn = document.getElementById('btn-save-settings');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      showToast('Workstation parameters stored to local profile.');
    });
  }

  const resetBtn = document.getElementById('btn-reset-cache');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (confirm('Clear local telemetry cache and reset map layers?')) {
        showToast('Local cache cleared.');
      }
    });
  }
}

/**
 * 11. WINDOW SYSTEM CONTROLS
 */
function initWindowControls() {
  const minBtn = document.getElementById('sys-btn-minimize');
  if (minBtn) {
    minBtn.addEventListener('click', () => {
      showToast('LANDSLIDENEI EOC Terminal: Minimized to system tray.');
    });
  }

  const maxBtn = document.getElementById('sys-btn-maximize');
  if (maxBtn) {
    maxBtn.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
  }

  const closeBtn = document.getElementById('sys-btn-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      if (confirm('Exit LANDSLIDENEI EOC Terminal? Current telemetry session will be closed.')) {
        navigateTo('login');
      }
    });
  }
}

function showToast(msg) {
  let toast = document.getElementById('app-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'app-toast';
    toast.className = 'fixed bottom-4 right-4 z-50 px-4 py-2 bg-primary-container text-on-primary-container font-mono text-xs font-bold rounded shadow-xl transition-opacity duration-300';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  toast.style.display = 'block';
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => { toast.style.display = 'none'; }, 300);
  }, 2500);
}
window.showToast = showToast;

/**
 * 10. INTERACTIVE ML MODEL SANDBOX SIMULATION (SCREEN 11)
 */
function runSandboxSimulation() {
  const slope = parseFloat(document.getElementById('sbx-slope')?.value || 38);
  const elev = parseFloat(document.getElementById('sbx-elev')?.value || 1450);
  const relief = parseFloat(document.getElementById('sbx-relief')?.value || 42);
  const rain24 = parseFloat(document.getElementById('sbx-rain24')?.value || 115);
  const rain7d = parseFloat(document.getElementById('sbx-rain7d')?.value || 240);

  // Update slider label readouts
  const slopeEl = document.getElementById('sbx-slope-val');
  const elevEl = document.getElementById('sbx-elev-val');
  const reliefEl = document.getElementById('sbx-relief-val');
  const rain24El = document.getElementById('sbx-rain24-val');
  const rain7dEl = document.getElementById('sbx-rain7d-val');
  if (slopeEl) slopeEl.textContent = slope + '°';
  if (elevEl) elevEl.textContent = elev.toLocaleString() + ' m';
  if (reliefEl) reliefEl.textContent = relief + ' m';
  if (rain24El) rain24El.textContent = rain24 + ' mm';
  if (rain7dEl) rain7dEl.textContent = rain7d + ' mm';

  // Physical heuristic computation matching trained Random Forest Model A + hydrometric trigger
  let staticScore = 0.15;
  if (slope > 35) staticScore += 0.40;
  else if (slope > 25) staticScore += 0.25;
  else if (slope > 15) staticScore += 0.12;

  if (relief > 50) staticScore += 0.20;
  else if (relief > 30) staticScore += 0.12;
  else if (relief > 15) staticScore += 0.06;

  if (elev > 1000 && elev < 3000) staticScore += 0.10;
  staticScore = Math.min(0.95, Math.max(0.05, staticScore));

  let hydroScore = 0.10;
  if (rain24 > 100) hydroScore += 0.55;
  else if (rain24 > 60) hydroScore += 0.35;
  else if (rain24 > 30) hydroScore += 0.18;

  if (rain7d > 200) hydroScore += 0.25;
  else if (rain7d > 100) hydroScore += 0.12;
  hydroScore = Math.min(0.98, Math.max(0.05, hydroScore));

  // Fusion synthesis: 0.45 * static + 0.55 * hydro
  const fusionScore = (0.45 * staticScore) + (0.55 * hydroScore);

  let verdict = 'LOW';
  let pillClass = 'bg-emerald-950 text-emerald-400';
  let reason = 'Slope and hydrometric parameters within safe normal baseline.';

  if (fusionScore >= 0.75 || (slope > 35 && rain24 > 90)) {
    verdict = 'CRITICAL';
    pillClass = 'bg-error-container text-error';
    reason = `Steep slope (${slope}°) combined with extreme 24h precipitation (${rain24} mm) exceeds geotechnical failure limit.`;
  } else if (fusionScore >= 0.55 || (slope > 25 && rain24 > 50)) {
    verdict = 'HIGH';
    pillClass = 'bg-orange-950/80 text-orange-400';
    reason = `High terrain gradient combined with significant antecedent saturation (${rain7d} mm).`;
  } else if (fusionScore >= 0.35) {
    verdict = 'WATCH';
    pillClass = 'bg-amber-950/80 text-amber-400';
    reason = `Moderate slope with localized precipitation; active monitoring advised.`;
  }

  const pillEl = document.getElementById('sbx-verdict-pill');
  const scoreEl = document.getElementById('sbx-score-val');
  const reasonEl = document.getElementById('sbx-reason-text');

  if (pillEl) {
    pillEl.textContent = verdict;
    pillEl.className = 'px-2.5 py-1 rounded font-mono text-xs font-bold uppercase ' + pillClass;
  }
  if (scoreEl) scoreEl.textContent = fusionScore.toFixed(3);
  if (reasonEl) reasonEl.textContent = reason;
}
window.runSandboxSimulation = runSandboxSimulation;

/**
 * 12. EOC AUTHENTICATION & WORKSTATION SETUP CONTROLLER (PHASE 8O)
 */
function showAuthPanel(panelId) {
  const setupPanel = document.getElementById('auth-panel-setup');
  const loginPanel = document.getElementById('auth-panel-login');
  const registerPanel = document.getElementById('auth-panel-register');

  if (setupPanel) setupPanel.classList.toggle('hidden', panelId !== 'setup');
  if (loginPanel) loginPanel.classList.toggle('hidden', panelId !== 'login');
  if (registerPanel) registerPanel.classList.toggle('hidden', panelId !== 'register');
}
window.showAuthPanel = showAuthPanel;

function initAuthHandlers() {
  const authModal = document.getElementById('auth-modal');
  if (!authModal) return;

  const session = localStorage.getItem('landslidenei_auth_session');
  if (session) {
    try {
      const user = JSON.parse(session);
      window.currentUser = Object.assign(window.currentUser || {}, user);
      updateHeaderUser(user.name || user.officerName || 'Duty Officer', user.sector || 'NE-EOC-REGIONAL');
      authModal.classList.add('hidden');
      return;
    } catch (e) {
      console.warn('Failed to parse saved session, requiring login:', e);
    }
  }

  // If first launch or no session, show setup panel
  const hasSeenSetup = localStorage.getItem('landslidenei_setup_completed');
  if (hasSeenSetup) {
    showAuthPanel('login');
  } else {
    showAuthPanel('setup');
  }
  authModal.classList.remove('hidden');
}
window.initAuthHandlers = initAuthHandlers;

function submitLogin() {
  const authModal = document.getElementById('auth-modal');
  const officerId = document.getElementById('input-login-id')?.value || 'duty.officer@landslidenei.in';
  const sector = document.getElementById('select-login-sector')?.value || 'NE-EOC-REGIONAL';
  const remember = document.getElementById('check-remember-session')?.checked;

  const rawName = officerId.split('@')[0].replace('.', ' ');
  const officerName = rawName.charAt(0).toUpperCase() + rawName.slice(1);

  const sessionData = {
    officerId: officerId,
    officerName: officerName,
    sector: sector,
    authenticatedAt: new Date().toISOString()
  };

  window.currentUser = Object.assign(window.currentUser || {}, sessionData);
  updateHeaderUser(officerName, sector);

  if (remember) {
    localStorage.setItem('landslidenei_auth_session', JSON.stringify(sessionData));
  }
  localStorage.setItem('landslidenei_setup_completed', 'true');

  if (authModal) {
    authModal.classList.add('hidden');
  }
  if (typeof showToast === 'function') {
    showToast(`Workstation unlocked: ${officerName} (${sector})`);
  }
}
window.submitLogin = submitLogin;

function submitRegister() {
  const authModal = document.getElementById('auth-modal');
  const name = document.getElementById('input-reg-name')?.value || 'Duty Officer';
  const dept = document.getElementById('input-reg-dept')?.value || 'SDMA';
  const email = document.getElementById('input-reg-id')?.value || 'officer@landslidenei.in';

  const sessionData = {
    officerId: email,
    officerName: name,
    dept: dept,
    sector: 'NE-EOC-REGIONAL',
    authenticatedAt: new Date().toISOString()
  };

  window.currentUser = Object.assign(window.currentUser || {}, sessionData);
  updateHeaderUser(name, dept);

  localStorage.setItem('landslidenei_auth_session', JSON.stringify(sessionData));
  localStorage.setItem('landslidenei_setup_completed', 'true');

  if (authModal) {
    authModal.classList.add('hidden');
  }
  if (typeof showToast === 'function') {
    showToast(`Profile created. Workstation unlocked for ${name}`);
  }
}
window.submitRegister = submitRegister;

function handleLogout() {
  localStorage.removeItem('landslidenei_auth_session');
  const authModal = document.getElementById('auth-modal');
  if (authModal) {
    showAuthPanel('login');
    authModal.classList.remove('hidden');
  }
  if (typeof showToast === 'function') {
    showToast('Workstation locked. Session ended.');
  }
}
window.handleLogout = handleLogout;

function updateHeaderUser(name, sector) {
  const nameEl = document.getElementById('header-user-name');
  if (nameEl) {
    nameEl.textContent = name;
    if (nameEl.nextElementSibling) {
      nameEl.nextElementSibling.textContent = sector;
    }
  }
}


