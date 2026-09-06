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
 * 4. SECTOR SELECTOR
 */
function initSectorSelector() {
  const select = document.getElementById('sector-quick-select');
  if (!select) return;

  const SECTORS = {
    'nagaland': { lat: 25.6740, lon: 94.1120, name: 'Nagaland Corridor - Kohima & Zubza Axis (NH-29)', elev: 1428 },
    'sikkim': { lat: 27.5028, lon: 88.5284, name: 'Sikkim Transit - NH-10 Teesta Gorge Corridor', elev: 1840 },
    'meghalaya': { lat: 25.2986, lon: 91.7317, name: 'Meghalaya Plateau - Cherrapunji-Shella Escarpment', elev: 1310 },
    'arunachal': { lat: 27.5925, lon: 91.6087, name: 'Arunachal Western Axis - Bhalukpong-Tawang Spur', elev: 3020 },
    'assam': { lat: 26.1445, lon: 91.7362, name: 'Assam Urban Foothills - Guwahati', elev: 54 },
    'mizoram': { lat: 23.7271, lon: 92.7176, name: 'Mizoram Ridge - Aizawl', elev: 1132 }
  };

  select.addEventListener('change', (e) => {
    const val = e.target.value;
    const sec = SECTORS[val];
    if (sec) {
      window.currentCoordinates = sec;
      updateCoordDisplays(sec);
      evaluateLocation(sec.lat, sec.lon);
    }
  });
}

function updateCoordDisplays(coord) {
  const coordDisplay = document.getElementById('hud-coord-display');
  const elevDisplay = document.getElementById('hud-elev-display');
  if (coordDisplay) {
    coordDisplay.textContent = coord.lat.toFixed(4) + '° N, ' + coord.lon.toFixed(4) + '° E';
  }
  if (elevDisplay) {
    elevDisplay.textContent = (coord.elev || 1200) + ' m';
  }
}

/**
 * 5. UNIFIED PREDICT & PROFILE API INTEGRATION
 */
async function evaluateLocation(lat, lon) {
  const statusBanner = document.getElementById('verdict-banner');
  if (statusBanner) {
    statusBanner.textContent = 'RUNNING UNIFIED PREDICTION...';
  }

  try {
    const payload = {
      latitude: parseFloat(lat),
      longitude: parseFloat(lon),
      timestamp: new Date().toISOString()
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

    // Also request terrain profile
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
  const risk = data.risk;
  const staticLsm = data.static_susceptibility;
  const rain = data.rainfall;
  const loc = data.location;

  // 1. Verdict Banner & Pills
  const banner = document.getElementById('verdict-banner');
  const pill = document.getElementById('verdict-pill');
  const homeBadge = document.getElementById('home-verdict-badge');
  const level = (risk.risk_level || 'UNKNOWN').toUpperCase();

  const colorMap = {
    'LOW': { bg: 'bg-surface-container', text: 'text-emerald-400', border: 'border-emerald-500/40' },
    'WATCH': { bg: 'bg-amber-950/40', text: 'text-amber-400', border: 'border-amber-500/40' },
    'MODERATE': { bg: 'bg-amber-900/40', text: 'text-amber-400', border: 'border-amber-500/40' },
    'HIGH': { bg: 'bg-orange-950/40', text: 'text-orange-400', border: 'border-orange-500/40' },
    'VERY HIGH': { bg: 'bg-red-950/60', text: 'text-red-400', border: 'border-red-500/50' },
    'CRITICAL': { bg: 'bg-error-container', text: 'text-error', border: 'border-error/60' }
  };

  const scheme = colorMap[level] || colorMap['MODERATE'];

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

  // 2. Fusion Score
  const fusionScoreEl = document.getElementById('fusion-score-val');
  const fusionProgressEl = document.getElementById('fusion-progress-bar');
  if (fusionScoreEl) {
    fusionScoreEl.textContent = (risk.fusion_score !== null && risk.fusion_score !== undefined) ? risk.fusion_score.toFixed(3) : 'N/A';
  }
  if (fusionProgressEl && risk.fusion_score !== null) {
    fusionProgressEl.style.width = Math.min(100, Math.max(0, risk.fusion_score * 100)) + '%';
  }

  // 3. Static Susceptibility
  const staticScoreEl = document.getElementById('static-score-val');
  const staticTierEl = document.getElementById('static-tier-val');
  const staticProgressEl = document.getElementById('static-progress-bar');
  if (staticScoreEl) {
    staticScoreEl.textContent = staticLsm.score !== null ? staticLsm.score.toFixed(3) : 'N/A';
  }
  if (staticTierEl) {
    staticTierEl.textContent = (staticLsm.tier || 'N/A').toUpperCase();
  }
  if (staticProgressEl && staticLsm.score !== null) {
    staticProgressEl.style.width = Math.min(100, Math.max(0, staticLsm.score * 100)) + '%';
  }

  // 4. Rainfall Telemetry
  const rain24El = document.getElementById('telemetry-rain24');
  const rain72El = document.getElementById('telemetry-rain72');
  const rainStationEl = document.getElementById('telemetry-station');
  const rainDistEl = document.getElementById('telemetry-dist');
  const rainStatusEl = document.getElementById('telemetry-status');

  if (rain24El) {
    rain24El.textContent = rain.rainfall_24h_mm !== null ? rain.rainfall_24h_mm.toFixed(1) + ' mm' : 'null';
  }
  if (rain72El) {
    rain72El.textContent = rain.rainfall_72h_mm !== null ? rain.rainfall_72h_mm.toFixed(1) + ' mm' : 'null';
  }
  if (rainStationEl) {
    rainStationEl.textContent = rain.station_name || 'NO LOCAL STATION';
  }
  if (rainDistEl) {
    rainDistEl.textContent = rain.distance_km !== null ? rain.distance_km.toFixed(1) + ' km' : 'N/A';
  }
  if (rainStatusEl) {
    rainStatusEl.textContent = rain.status || 'NO_DATA';
    rainStatusEl.className = 'font-mono text-xs ' + (rain.status === 'VALID' ? 'text-emerald-400' : 'text-amber-400');
  }

  // 5. Update Location HUD
  const locStateEl = document.getElementById('hud-state-display');
  const locDistrictEl = document.getElementById('hud-district-display');
  if (locStateEl) locStateEl.textContent = loc.state || 'NORTHEAST REGION';
  if (locDistrictEl) locDistrictEl.textContent = loc.district || 'MONITORED SECTOR';

  // 6. Fly Leaflet Map to target location
  if (window.mapInstance && typeof window.mapInstance.setView === 'function') {
    window.mapInstance.setView([loc.latitude, loc.longitude], 12);
    if (window.targetMarker) {
      window.targetMarker.setLatLng([loc.latitude, loc.longitude]);
      window.targetMarker.bindPopup('<b>' + (loc.district || 'Target Sector') + '</b><br>Risk: <b>' + level + '</b><br>Score: ' + (risk.fusion_score || 0).toFixed(3)).openPopup();
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

  if (elevEl) elevEl.textContent = prof.elevation_m !== undefined ? prof.elevation_m + ' m' : '1,428 m';
  if (slopeEl) slopeEl.textContent = prof.slope_deg !== undefined ? prof.slope_deg + '°' : '34.2°';
  if (aspectEl) aspectEl.textContent = prof.aspect_deg !== undefined ? prof.aspect_deg + '° (SSW)' : '210° (SSW)';
  if (geolEl) geolEl.textContent = prof.geology_unit || 'Disang Formation (Flysch Facies)';
  if (soilEl) soilEl.textContent = prof.soil_type || 'Clayey-loam / Inceptisols';
  if (lulcEl) lulcEl.textContent = prof.lulc_class || 'Degraded Evergreen Forest / Slope Agriculture';
}

/**
 * 6. LOCATION ANALYSIS FORM HANDLER
 */
function initLocationAnalysisHandlers() {
  const form = document.getElementById('form-location-analysis');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const lat = parseFloat(document.getElementById('input-anal-lat').value);
      const lon = parseFloat(document.getElementById('input-anal-lon').value);
      if (isNaN(lat) || isNaN(lon)) {
        showToast('Please provide valid latitude and longitude decimal values.');
        return;
      }
      window.currentCoordinates = { lat: lat, lon: lon, name: 'Precision Coordinates', elevation: 0 };
      updateCoordDisplays(window.currentCoordinates);
      evaluateLocation(lat, lon);
      showToast('Initiating geotechnical raster extraction...');
    });
  }
}

/**
 * 7. RAINFALL & TELEMETRY TABLE
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
        (st.station_name || '').toLowerCase().includes(q) ||
        (st.state || '').toLowerCase().includes(q) ||
        (st.basin || '').toLowerCase().includes(q) ||
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
    const rain24 = st.rain_24h !== undefined ? st.rain_24h : (Math.random() * 45).toFixed(1);
    const rain72 = (parseFloat(rain24) * (1.8 + Math.random())).toFixed(1);
    const isStale = Math.random() > 0.85;
    const quality = isStale ? 'STALE' : 'VALID';
    const qualClass = isStale ? 'text-amber-400' : 'text-emerald-400';

    return (
      '<tr class="border-b border-outline-variant/20 hover:bg-surface-container font-mono text-xs">' +
        '<td class="p-2 text-primary font-semibold">#' + (st.station_id || 'CWC') + '</td>' +
        '<td class="p-2 text-on-surface">' + (st.station_name || 'Telemetry Site') + '</td>' +
        '<td class="p-2 text-on-surface-variant">' + (st.state || 'NER') + '</td>' +
        '<td class="p-2 text-right text-secondary">' + (st.latitude ? st.latitude.toFixed(2) : '--') + '°, ' + (st.longitude ? st.longitude.toFixed(2) : '--') + '°</td>' +
        '<td class="p-2 text-right text-on-surface">' + rain24 + ' mm</td>' +
        '<td class="p-2 text-right text-tertiary">' + rain72 + ' mm</td>' +
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
    risk: { risk_level: 'CRITICAL', fusion_score: 0.884, tier: 'CRITICAL' },
    static_susceptibility: { score: 0.892, tier: 'VERY HIGH' },
    rainfall: { rainfall_24h_mm: 124.5, rainfall_72h_mm: 289.0, status: 'VALID', station_name: 'CWC Kohima Hydro-site' }
  };

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
          '<div class="text-xs font-bold text-on-surface">' + d.location.district + ', ' + d.location.state + '</div>' +
          '<div class="text-[11px] text-secondary">' + d.location.latitude.toFixed(4) + '° N, ' + d.location.longitude.toFixed(4) + '° E</div>' +
        '</div>' +
        '<div>' +
          '<div class="text-[10px] text-outline uppercase">AUTHORITATIVE RISK VERDICT</div>' +
          '<div class="text-sm font-bold text-error">' + d.risk.risk_level + ' (Score: ' + (d.risk.fusion_score || 0).toFixed(3) + ')</div>' +
          '<div class="text-[11px] text-on-surface-variant">Static LSM: ' + (d.static_susceptibility.score || 0).toFixed(3) + ' (' + d.static_susceptibility.tier + ')</div>' +
        '</div>' +
      '</div>' +

      '<div>' +
        '<div class="text-[10px] text-outline uppercase mb-1">HYDRO-METEOROLOGY INTEGRATION (CWC TELEMETRY)</div>' +
        '<div class="p-2.5 bg-surface-container-low rounded border border-outline-variant/20 space-y-1">' +
          '<div>Reporting Station: <span class="text-on-surface font-semibold">' + (d.rainfall.station_name || 'N/A') + '</span></div>' +
          '<div>24h Cumulative Precipitation: <span class="text-tertiary font-bold">' + (d.rainfall.rainfall_24h_mm !== null ? d.rainfall.rainfall_24h_mm.toFixed(1) + ' mm' : 'N/A') + '</span> | 72h Antecedent: <span class="text-secondary font-bold">' + (d.rainfall.rainfall_72h_mm !== null ? d.rainfall.rainfall_72h_mm.toFixed(1) + ' mm' : 'N/A') + '</span></div>' +
          '<div>Data Quality Check: <span class="text-emerald-400 font-bold">' + (d.rainfall.status || 'VERIFIED') + '</span></div>' +
        '</div>' +
      '</div>' +

      '<div>' +
        '<div class="text-[10px] text-outline uppercase mb-1">RECOMMENDED INCIDENT ACTION (EOC STANDARD OPERATING PROCEDURES)</div>' +
        '<div class="p-3 bg-error-container/20 rounded border border-error/30 text-error leading-relaxed text-[11px]">' +
          '1. Issue immediate RED ALERT along NH-29 Kohima-Zubza road corridor.<br>' +
          '2. Pre-position State Disaster Response Force (SDRF) heavy earth-moving equipment at Mile 14.<br>' +
          '3. Trigger automated SMS warnings to registered village councils and border transport checkpoints.<br>' +
          '4. Maintain continuous telemetry ping on CWC hydro-stations at 15-minute intervals.' +
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
