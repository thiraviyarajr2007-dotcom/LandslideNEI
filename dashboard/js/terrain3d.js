/**
 * LANDSLIDENEI - Production 3D DEM Terrain Visualization Engine
 * =============================================================
 * Sovereign WebGL 3D terrain viewer powered by local Three.js (r128) + OrbitControls.
 * Streams genuine Copernicus GLO-30 elevation, Horn's slope, and aspect grids.
 * Strictly adheres to truth-in-data: never fabricates elevation, landslides, or villages.
 */

(function () {
  'use strict';

  // Engine state
  const state = {
    initialized: false,
    container: null,
    canvas: null,
    scene: null,
    camera: null,
    renderer: null,
    controls: null,
    raycaster: null,
    mouse: null,
    terrainMesh: null,
    terrainGeometry: null,
    terrainData: null,
    rawHeights: null,
    rawSlopes: null,
    rawAspects: null,
    gridWidth: 128,
    gridHeight: 128,
    metricWidth: 20000, // 20 km default
    metricHeight: 20000,
    bbox: null,
    exaggeration: 1.5,
    activeColorMode: 'terrain', // 'terrain', 'elevation', 'slope', 'aspect'
    layers: {
      terrain: true,
      elevation: false,
      slope: false,
      aspect: false,
      historical_landslides: false,
      rainfall_stations: false,
      rainfall_intensity: false,
      risk_zones: false,
      villages: false,
    },
    queryMarker: null,
    landslideMarkersGroup: null,
    stationMarkersGroup: null,
    riskZoneGroup: null,
    hoverCoords: null,
    selectedLocation: null,
    isHoveringTerrain: false,
    isLoading: false,
    currentCenter: { lat: 25.6740, lon: 94.1120 },
    currentSector: 'nagaland',
  };

  /**
   * Initialize 3D Engine and Mount to DOM
   */
  function init() {
    if (state.initialized) return;

    state.container = document.getElementById('terrain-3d-wrapper');
    state.canvas = document.getElementById('terrain-3d-canvas');
    if (!state.container || !state.canvas || typeof THREE === 'undefined') {
      console.warn('3D Terrain Viewer: Container, canvas, or THREE.js not available.');
      return;
    }

    const width = state.container.clientWidth || 800;
    const height = state.container.clientHeight || 600;

    // 1. Scene
    state.scene = new THREE.Scene();
    state.scene.background = new THREE.Color(0x060e1f); // Tactical dark
    state.scene.fog = new THREE.FogExp2(0x060e1f, 0.000025);

    // 2. Camera
    state.camera = new THREE.PerspectiveCamera(45, width / height, 10, 100000);
    state.camera.position.set(0, -14000, 10000);

    // 3. Renderer
    state.renderer = new THREE.WebGLRenderer({
      canvas: state.canvas,
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
    state.renderer.setSize(width, height);
    state.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    state.renderer.shadowMap.enabled = false;

    // 4. Orbit Controls
    if (typeof THREE.OrbitControls !== 'undefined') {
      state.controls = new THREE.OrbitControls(state.camera, state.renderer.domElement);
      state.controls.enableDamping = true;
      state.controls.dampingFactor = 0.08;
      state.controls.screenSpacePanning = false;
      state.controls.minDistance = 500;
      state.controls.maxDistance = 60000;
      state.controls.maxPolarAngle = Math.PI / 2 - 0.05; // Prevent camera sinking under ground
      state.controls.target.set(0, 0, 0);
    }

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xdbeafe, 0.45);
    state.scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfff7ed, 0.85);
    sunLight.position.set(15000, 20000, 25000);
    state.scene.add(sunLight);

    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.25);
    fillLight.position.set(-15000, -20000, 15000);
    state.scene.add(fillLight);

    // 6. Marker Groups
    state.landslideMarkersGroup = new THREE.Group();
    state.scene.add(state.landslideMarkersGroup);

    state.stationMarkersGroup = new THREE.Group();
    state.scene.add(state.stationMarkersGroup);

    state.riskZoneGroup = new THREE.Group();
    state.scene.add(state.riskZoneGroup);

    // 7. Raycaster for Terrain Inspection
    state.raycaster = new THREE.Raycaster();
    state.mouse = new THREE.Vector2();

    // 8. Event Listeners
    setupEventListeners();

    state.initialized = true;

    // Start render loop
    animate();

    // Load initial corridor
    loadCorridor(state.currentSector, state.currentCenter.lat, state.currentCenter.lon);
  }

  /**
   * Setup UI and Interaction Event Listeners
   */
  function setupEventListeners() {
    window.addEventListener('resize', onWindowResize);

    state.canvas.addEventListener('pointermove', onPointerMove);
    state.canvas.addEventListener('click', onCanvasClick);
    state.canvas.addEventListener('pointerleave', () => {
      state.isHoveringTerrain = false;
      updateInspectionHUD(null);
    });

    // Camera control buttons
    const btnZoomIn = document.getElementById('btn-3d-zoom-in');
    const btnZoomOut = document.getElementById('btn-3d-zoom-out');
    const btnTopView = document.getElementById('btn-3d-top-view');
    const btnPerspView = document.getElementById('btn-3d-persp-view');
    const btnResetCam = document.getElementById('btn-3d-reset');

    if (btnZoomIn) btnZoomIn.addEventListener('click', () => zoomCamera(0.8));
    if (btnZoomOut) btnZoomOut.addEventListener('click', () => zoomCamera(1.25));
    if (btnTopView) btnTopView.addEventListener('click', setTopView);
    if (btnPerspView) btnPerspView.addEventListener('click', setPerspectiveView);
    if (btnResetCam) btnResetCam.addEventListener('click', resetCamera);

    // Exaggeration pill buttons
    document.querySelectorAll('.btn-exaggeration').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const factor = parseFloat(btn.getAttribute('data-exaggeration') || '1.5');
        setExaggeration(factor);
      });
    });

    // Layer checkboxes
    const layerInputs = {
      'layer-3d-terrain': 'terrain',
      'layer-3d-elevation': 'elevation',
      'layer-3d-slope': 'slope',
      'layer-3d-aspect': 'aspect',
      'layer-3d-landslides': 'historical_landslides',
      'layer-3d-stations': 'rainfall_stations',
      'layer-3d-intensity': 'rainfall_intensity',
      'layer-3d-risk': 'risk_zones',
      'layer-3d-villages': 'villages',
    };

    Object.entries(layerInputs).forEach(([elemId, layerKey]) => {
      const input = document.getElementById(elemId);
      if (input) {
        input.addEventListener('change', (e) => {
          toggleLayer(layerKey, e.target.checked);
        });
      }
    });
  }

  function onWindowResize() {
    if (!state.container || !state.camera || !state.renderer) return;
    const width = state.container.clientWidth;
    const height = state.container.clientHeight;
    if (width === 0 || height === 0) return;

    state.camera.aspect = width / height;
    state.camera.updateProjectionMatrix();
    state.renderer.setSize(width, height);
  }

  /**
   * Main Render Loop
   */
  function animate() {
    requestAnimationFrame(animate);
    if (state.controls) state.controls.update();

    // Pulse animation for query marker ring
    if (state.queryMarker && state.queryMarker.userData.ring) {
      const ring = state.queryMarker.userData.ring;
      const s = 1.0 + 0.15 * Math.sin(Date.now() * 0.005);
      ring.scale.set(s, s, s);
    }

    state.renderer.render(state.scene, state.camera);
  }

  /**
   * Fetch and Render DEM Mesh for Target Coordinate or Corridor
   */
  async function loadCorridor(sector, lat, lon, radiusKm = 10.0) {
    state.isLoading = true;
    showStatusBanner('STREAMING COPERNICUS GLO-30 TERRAIN (30M)...', 'loading');

    state.currentSector = sector;
    state.currentCenter = { lat: lat, lon: lon };

    try {
      const params = new URLSearchParams({
        latitude: lat.toFixed(5),
        longitude: lon.toFixed(5),
        radius_km: radiusKm.toString(),
        grid_size: '128',
      });
      if (sector) params.append('sector', sector);

      const res = await fetch(`/api/v1/terrain/mesh?${params.toString()}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || 'Terrain data unavailable');
      }

      const data = await res.json();
      if (data.status === 'TERRAIN_DATA_UNAVAILABLE') {
        throw new Error(data.message || 'TERRAIN DATA UNAVAILABLE');
      }

      state.terrainData = data;
      buildTerrainMesh(data);
      const modeLabel = data.source_mode === 'PREPROCESSED_FOCAL_CACHE' 
        ? `FOCAL CACHE (~${data.resolution_m || 157}m MESH)` 
        : (data.source_mode === 'REGIONAL_OFFLINE_CACHE' 
          ? `REGIONAL CACHE (~${data.resolution_m || 834}m MESH)` 
          : `DYNAMIC GLO-30 (~${data.resolution_m || 157}m MESH)`);
      showStatusBanner(`COPERNICUS GLO-30 [${modeLabel}] // ELEVATION: ${data.elevation_stats.min_m}m – ${data.elevation_stats.max_m}m`, 'success');

      // Sync layers
      if (state.layers.historical_landslides) loadHistoricalLandslidesLayer();
      if (state.layers.rainfall_stations) loadRainfallStationsLayer();
      if (state.layers.risk_zones) renderRiskZonesLayer();

    } catch (err) {
      console.warn('3D Terrain Load Warning:', err.message);
      clearTerrainMesh();
      showStatusBanner(err.message.toUpperCase(), 'error');
    } finally {
      state.isLoading = false;
    }
  }

  /**
   * Construct Three.js 3D Geometry and Colors from Copernicus DEM Grid
   */
  function buildTerrainMesh(data) {
    clearTerrainMesh();

    const w = data.dimensions.width;
    const h = data.dimensions.height;
    state.gridWidth = w;
    state.gridHeight = h;
    state.rawHeights = data.elevations;
    state.rawSlopes = data.slopes;
    state.rawAspects = data.aspects;
    state.bbox = data.bbox; // [min_lon, min_lat, max_lon, max_lat]

    // Compute metric dimensions in meters
    const [minLon, minLat, maxLon, maxLat] = data.bbox;
    const midLat = (minLat + maxLat) / 2;
    state.metricWidth = (maxLon - minLon) * 111320 * Math.cos(midLat * Math.PI / 180);
    state.metricHeight = (maxLat - minLat) * 111320;

    // PlaneGeometry along X and Y (centered at 0,0)
    const geometry = new THREE.PlaneGeometry(
      state.metricWidth,
      state.metricHeight,
      w - 1,
      h - 1
    );

    // Assign Z elevation from raw Copernicus values
    const pos = geometry.attributes.position;
    const meanElev = data.elevation_stats.mean_m || 1000;

    for (let i = 0; i < pos.count; i++) {
      const rawZ = state.rawHeights[i];
      if (rawZ !== null && rawZ !== undefined && !isNaN(rawZ)) {
        // Vertical displacement relative to mean elevation, multiplied by visual exaggeration
        const z = (rawZ - meanElev) * state.exaggeration;
        pos.setZ(i, z);
      } else {
        pos.setZ(i, 0);
      }
    }

    geometry.computeVertexNormals();

    // Material with dynamic vertex colors
    const colors = generateVertexColors(state.activeColorMode);
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.85,
      metalness: 0.1,
      flatShading: false,
      wireframe: false,
    });

    state.terrainGeometry = geometry;
    state.terrainMesh = new THREE.Mesh(geometry, material);
    state.terrainMesh.name = 'dem_terrain_surface';
    state.scene.add(state.terrainMesh);

    // Frame camera smoothly around new mesh
    resetCamera();
  }

  function clearTerrainMesh() {
    if (state.terrainMesh) {
      state.scene.remove(state.terrainMesh);
      if (state.terrainMesh.geometry) state.terrainMesh.geometry.dispose();
      if (state.terrainMesh.material) state.terrainMesh.material.dispose();
      state.terrainMesh = null;
      state.terrainGeometry = null;
    }
  }

  /**
   * Dynamic Vertex Color Generator based on Active Layer Mode
   */
  function generateVertexColors(mode) {
    const count = state.gridWidth * state.gridHeight;
    const colors = new Float32Array(count * 3);
    const minElev = state.terrainData ? state.terrainData.elevation_stats.min_m : 0;
    const maxElev = state.terrainData ? state.terrainData.elevation_stats.max_m : 3000;
    const elevRange = Math.max(1, maxElev - minElev);

    for (let i = 0; i < count; i++) {
      const idx = i * 3;
      const elev = state.rawHeights ? state.rawHeights[i] : null;
      const slope = state.rawSlopes ? state.rawSlopes[i] : null;
      const aspect = state.rawAspects ? state.rawAspects[i] : null;

      if (elev === null || isNaN(elev)) {
        // Nodata color: neutral dark slate
        colors[idx] = 0.1;
        colors[idx + 1] = 0.15;
        colors[idx + 2] = 0.2;
        continue;
      }

      if (mode === 'slope') {
        // Slope hazard gradient: Green (<15°) -> Yellow (15-25°) -> Orange (25-35°) -> Crimson (>35°)
        if (slope < 15) {
          colors[idx] = 0.13; colors[idx + 1] = 0.77; colors[idx + 2] = 0.36; // Emerald green
        } else if (slope < 25) {
          colors[idx] = 0.92; colors[idx + 1] = 0.70; colors[idx + 2] = 0.03; // Amber yellow
        } else if (slope < 35) {
          colors[idx] = 0.98; colors[idx + 1] = 0.45; colors[idx + 2] = 0.09; // Vivid orange
        } else {
          colors[idx] = 0.94; colors[idx + 1] = 0.27; colors[idx + 2] = 0.27; // Crimson red
        }

      } else if (mode === 'aspect') {
        // Compass direction wheel
        // North (315°-45°): Cyan/Blue | East (45°-135°): Amber | South (135°-225°): Red/Pink | West (225°-315°): Green
        if (aspect >= 315 || aspect < 45) {
          colors[idx] = 0.22; colors[idx + 1] = 0.74; colors[idx + 2] = 0.97; // North (Cyan/Blue)
        } else if (aspect >= 45 && aspect < 135) {
          colors[idx] = 0.98; colors[idx + 1] = 0.75; colors[idx + 2] = 0.14; // East (Amber)
        } else if (aspect >= 135 && aspect < 225) {
          colors[idx] = 0.94; colors[idx + 1] = 0.27; colors[idx + 2] = 0.27; // South (Red)
        } else {
          colors[idx] = 0.13; colors[idx + 1] = 0.77; colors[idx + 2] = 0.36; // West (Green)
        }

      } else if (mode === 'elevation') {
        // Hypsometric tint: Cyan (low) -> Emerald (mid-low) -> Gold (mid-high) -> Rose (peaks)
        const t = Math.max(0, Math.min(1, (elev - minElev) / elevRange));
        colors[idx] = 0.1 + 0.8 * t;
        colors[idx + 1] = 0.3 + 0.5 * Math.sin(t * Math.PI);
        colors[idx + 2] = 0.9 - 0.7 * t;

      } else {
        // Default Terrain: Natural earthen hillshade with realistic elevation transitions
        const t = Math.max(0, Math.min(1, (elev - minElev) / elevRange));
        if (t < 0.25) {
          // Low river valley: deep slate green
          colors[idx] = 0.15; colors[idx + 1] = 0.28; colors[idx + 2] = 0.22;
        } else if (t < 0.6) {
          // Mid slope: warm earthen umber
          colors[idx] = 0.38; colors[idx + 1] = 0.34; colors[idx + 2] = 0.28;
        } else if (t < 0.85) {
          // High mountain ridge: rocky granite gray
          colors[idx] = 0.52; colors[idx + 1] = 0.54; colors[idx + 2] = 0.58;
        } else {
          // Alpine summits: crisp pale snow cap
          colors[idx] = 0.85; colors[idx + 1] = 0.90; colors[idx + 2] = 0.95;
        }
      }
    }

    return colors;
  }

  /**
   * Set Visual Terrain Exaggeration
   */
  function setExaggeration(factor) {
    state.exaggeration = factor;

    // Update UI pill active states
    document.querySelectorAll('.btn-exaggeration').forEach(btn => {
      const f = parseFloat(btn.getAttribute('data-exaggeration') || '1.5');
      if (Math.abs(f - factor) < 0.05) {
        btn.classList.add('active', 'bg-primary-container', 'text-on-primary-container');
        btn.classList.remove('bg-surface-container', 'text-on-surface-variant');
      } else {
        btn.classList.remove('active', 'bg-primary-container', 'text-on-primary-container');
        btn.classList.add('bg-surface-container', 'text-on-surface-variant');
      }
    });

    const badge = document.getElementById('hud-exaggeration-badge');
    if (badge) {
      badge.textContent = `${factor.toFixed(1)}x`;
    }

    // Recompute Z heights on existing geometry
    if (state.terrainGeometry && state.rawHeights) {
      const pos = state.terrainGeometry.attributes.position;
      const meanElev = state.terrainData.elevation_stats.mean_m || 1000;

      for (let i = 0; i < pos.count; i++) {
        const rawZ = state.rawHeights[i];
        if (rawZ !== null && rawZ !== undefined && !isNaN(rawZ)) {
          pos.setZ(i, (rawZ - meanElev) * state.exaggeration);
        }
      }
      pos.needsUpdate = true;
      state.terrainGeometry.computeVertexNormals();

      // Update 3D markers elevation
      if (state.queryMarker && state.queryMarker.userData.lat) {
        updateQueryMarker(state.queryMarker.userData.lat, state.queryMarker.userData.lon);
      }
    }
  }

  /**
   * Toggle Layer Visibility and Shading
   */
  function toggleLayer(layerKey, isVisible) {
    state.layers[layerKey] = isVisible;

    // Mutually exclusive color ramps: elevation, slope, aspect
    if (layerKey === 'elevation' || layerKey === 'slope' || layerKey === 'aspect') {
      if (isVisible) {
        state.activeColorMode = layerKey;
        // Uncheck the other color modes
        ['elevation', 'slope', 'aspect'].forEach(k => {
          if (k !== layerKey) {
            state.layers[k] = false;
            const el = document.getElementById(`layer-3d-${k}`);
            if (el) el.checked = false;
          }
        });
      } else {
        state.activeColorMode = 'terrain';
      }
      updateTerrainColors();
      return;
    }

    if (layerKey === 'terrain') {
      if (state.terrainMesh) state.terrainMesh.visible = isVisible;
    } else if (layerKey === 'historical_landslides') {
      if (isVisible) loadHistoricalLandslidesLayer();
      else state.landslideMarkersGroup.clear();
    } else if (layerKey === 'rainfall_stations') {
      if (isVisible) loadRainfallStationsLayer();
      else state.stationMarkersGroup.clear();
    } else if (layerKey === 'risk_zones') {
      if (isVisible) renderRiskZonesLayer();
      else state.riskZoneGroup.clear();
    } else if (layerKey === 'villages') {
      // Truthful: never fabricate villages
      if (isVisible) {
        if (window.showToast) window.showToast('VILLAGE DATASET: DATA UNAVAILABLE (Pending future sovereign phase).');
      }
    }
  }

  function updateTerrainColors() {
    if (!state.terrainGeometry || !state.terrainMesh) return;
    const colors = generateVertexColors(state.activeColorMode);
    state.terrainGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    state.terrainGeometry.attributes.color.needsUpdate = true;
  }

  /**
   * 3D Marker Placement for Location Query
   */
  function updateQueryMarker(lat, lon) {
    if (!state.bbox) return;

    // Convert geographic coordinates (lat, lon) to local Three.js (X, Y, Z)
    const local = geoToLocal(lat, lon);
    if (!local) return;

    if (state.queryMarker) {
      state.scene.remove(state.queryMarker);
      state.queryMarker = null;
    }

    const markerGroup = new THREE.Group();
    markerGroup.userData = { lat: lat, lon: lon };

    // 1. Vertical Pin Shaft
    const shaftGeom = new THREE.CylinderGeometry(15, 15, 400, 8);
    const shaftMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });
    const shaft = new THREE.Mesh(shaftGeom, shaftMat);
    shaft.rotation.x = Math.PI / 2;
    shaft.position.z = 200;
    markerGroup.add(shaft);

    // 2. Glowing Head Sphere
    const sphereGeom = new THREE.SphereGeometry(60, 16, 16);
    const sphereMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });
    const sphere = new THREE.Mesh(sphereGeom, sphereMat);
    sphere.position.z = 400;
    markerGroup.add(sphere);

    // 3. Ground Pulsing Ring
    const ringGeom = new THREE.RingGeometry(80, 120, 24);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, side: THREE.DoubleSide, transparent: true, opacity: 0.7 });
    const ring = new THREE.Mesh(ringGeom, ringMat);
    ring.position.z = 10;
    markerGroup.userData.ring = ring;
    markerGroup.add(ring);

    markerGroup.position.set(local.x, local.y, local.z);
    state.scene.add(markerGroup);
    state.queryMarker = markerGroup;
  }

  /**
   * Convert Geographic (lat, lon) to Mesh Local Coordinates (x, y, z)
   */
  function geoToLocal(lat, lon) {
    if (!state.bbox) return null;
    const [minLon, minLat, maxLon, maxLat] = state.bbox;

    if (lon < minLon || lon > maxLon || lat < minLat || lat > maxLat) {
      return null;
    }

    const u = (lon - minLon) / (maxLon - minLon); // 0 to 1
    const v = (lat - minLat) / (maxLat - minLat); // 0 to 1

    const x = (u - 0.5) * state.metricWidth;
    const y = (v - 0.5) * state.metricHeight;

    // Sample elevation at grid cell
    const col = Math.min(state.gridWidth - 1, Math.max(0, Math.round(u * (state.gridWidth - 1))));
    const row = Math.min(state.gridHeight - 1, Math.max(0, Math.round(v * (state.gridHeight - 1))));
    const idx = row * state.gridWidth + col;

    const rawZ = state.rawHeights ? state.rawHeights[idx] : 0;
    const meanElev = state.terrainData ? state.terrainData.elevation_stats.mean_m : 1000;
    const z = (rawZ - meanElev) * state.exaggeration;

    return { x, y, z, rawElev: rawZ, slope: state.rawSlopes ? state.rawSlopes[idx] : null, aspect: state.rawAspects ? state.rawAspects[idx] : null };
  }

  /**
   * Convert Mesh Local Coordinates (x, y) to Geographic (lat, lon)
   */
  function localToGeo(x, y) {
    if (!state.bbox) return null;
    const [minLon, minLat, maxLon, maxLat] = state.bbox;

    const u = (x / state.metricWidth) + 0.5;
    const v = (y / state.metricHeight) + 0.5;

    if (u < 0 || u > 1 || v < 0 || v > 1) return null;

    const lon = minLon + u * (maxLon - minLon);
    const lat = minLat + v * (maxLat - minLat);

    const col = Math.min(state.gridWidth - 1, Math.max(0, Math.round(u * (state.gridWidth - 1))));
    const row = Math.min(state.gridHeight - 1, Math.max(0, Math.round(v * (state.gridHeight - 1))));
    const idx = row * state.gridWidth + col;

    const rawZ = state.rawHeights ? state.rawHeights[idx] : 0;
    const slope = state.rawSlopes ? state.rawSlopes[idx] : null;
    const aspect = state.rawAspects ? state.rawAspects[idx] : null;

    return { lat, lon, elev: rawZ, slope, aspect };
  }

  /**
   * Pointer Move Handler for Real-Time Terrain Hover Inspection
   */
  function onPointerMove(e) {
    if (!state.terrainMesh || !state.container) return;

    const rect = state.canvas.getBoundingClientRect();
    state.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    state.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    state.raycaster.setFromCamera(state.mouse, state.camera);
    const intersects = state.raycaster.intersectObject(state.terrainMesh);

    if (intersects.length > 0) {
      state.isHoveringTerrain = true;
      const hit = intersects[0].point;
      const geo = localToGeo(hit.x, hit.y);
      if (geo) {
        state.hoverCoords = geo;
        updateInspectionHUD(geo);
      }
    } else {
      state.isHoveringTerrain = false;
      updateInspectionHUD(null);
    }
  }

  /**
   * Canvas Click Handler: Select Location & Trigger Synchronous Risk Evaluation
   */
  function onCanvasClick(e) {
    if (!state.terrainMesh || !state.container) return;

    const rect = state.canvas.getBoundingClientRect();
    state.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    state.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    state.raycaster.setFromCamera(state.mouse, state.camera);
    const intersects = state.raycaster.intersectObject(state.terrainMesh);

    if (intersects.length > 0) {
      const hit = intersects[0].point;
      const geo = localToGeo(hit.x, hit.y);
      if (geo) {
        const lat = parseFloat(geo.lat.toFixed(5));
        const lon = parseFloat(geo.lon.toFixed(5));

        updateQueryMarker(lat, lon);
        displayLocationProfilePanel(geo);

        // Synchronize with global application state & 2D map
        if (window.handleMapClick) {
          window.handleMapClick(lat, lon);
        }
      }
    }
  }

  /**
   * Update Floating Tactical Inspection HUD
   */
  function updateInspectionHUD(geo) {
    const coordEl = document.getElementById('hud-3d-coords');
    const elevEl = document.getElementById('hud-3d-elevation');
    const slopeEl = document.getElementById('hud-3d-slope');
    const aspectEl = document.getElementById('hud-3d-aspect');

    if (!coordEl) return;

    if (geo) {
      coordEl.textContent = `${geo.lat.toFixed(4)}° N, ${geo.lon.toFixed(4)}° E`;
      elevEl.textContent = `${geo.elev ? Math.round(geo.elev).toLocaleString() : '--'} m`;
      slopeEl.textContent = geo.slope !== null ? `${geo.slope.toFixed(1)}°` : 'SLOPE: UNAVAILABLE';
      
      if (geo.aspect !== null) {
        const cardinals = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
        const card = cardinals[Math.round(geo.aspect / 45) % 8];
        aspectEl.textContent = `${geo.aspect.toFixed(0)}° (${card})`;
      } else {
        aspectEl.textContent = 'ASPECT: UNAVAILABLE';
      }
    } else {
      coordEl.textContent = '--';
      elevEl.textContent = '-- m';
      slopeEl.textContent = '--';
      aspectEl.textContent = '--';
    }
  }

  /**
   * Display Selected Location Information Panel
   */
  function displayLocationProfilePanel(geo) {
    const card = document.getElementById('hud-3d-location-card');
    if (!card) return;

    card.classList.remove('hidden');

    const setText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setText('loc-card-lat', `${geo.lat.toFixed(5)}° N`);
    setText('loc-card-lon', `${geo.lon.toFixed(5)}° E`);
    setText('loc-card-elev', `${geo.elev ? Math.round(geo.elev).toLocaleString() : '--'} m`);
    setText('loc-card-slope', geo.slope !== null ? `${geo.slope.toFixed(1)}°` : 'SLOPE: UNAVAILABLE');
    setText('loc-card-aspect', geo.aspect !== null ? `${geo.aspect.toFixed(1)}°` : 'ASPECT: UNAVAILABLE');
    setText('loc-card-source', 'Copernicus DEM GLO-30 (30m / EPSG:4326)');
    setText('loc-card-time', new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
  }

  /**
   * Load Historical Landslides 3D Layer (Truthful 75 Verified Events)
   */
  async function loadHistoricalLandslidesLayer() {
    state.landslideMarkersGroup.clear();
    try {
      const res = await fetch('/api/v1/layers/historical-landslides');
      if (!res.ok) return;
      const data = await res.json();
      if (data.status !== 'CONNECTED' || !data.events) return;

      const markerGeom = new THREE.ConeGeometry(25, 60, 6);
      const markerMat = new THREE.MeshBasicMaterial({ color: 0xef4444 }); // Tactical red

      data.events.forEach(evt => {
        const local = geoToLocal(evt.latitude, evt.longitude);
        if (local) {
          const mesh = new THREE.Mesh(markerGeom, markerMat);
          mesh.rotation.x = -Math.PI / 2; // Point cone down to terrain
          mesh.position.set(local.x, local.y, local.z + 30);
          mesh.userData = evt;
          state.landslideMarkersGroup.add(mesh);
        }
      });
    } catch (err) {
      console.warn('Failed to load historical landslides layer:', err);
    }
  }

  /**
   * Load CWC Rainfall Stations 3D Layer (Truthful Telemetry Stations)
   */
  async function loadRainfallStationsLayer() {
    state.stationMarkersGroup.clear();
    try {
      const res = await fetch('assets/cwc_stations.json');
      if (!res.ok) return;
      const stations = await res.json();

      const stGeom = new THREE.CylinderGeometry(20, 20, 100, 8);
      const stMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 }); // Cyan sensor

      stations.forEach(st => {
        const local = geoToLocal(st.latitude, st.longitude);
        if (local) {
          const mesh = new THREE.Mesh(stGeom, stMat);
          mesh.rotation.x = Math.PI / 2;
          mesh.position.set(local.x, local.y, local.z + 50);
          mesh.userData = st;
          state.stationMarkersGroup.add(mesh);
        }
      });
    } catch (err) {
      console.warn('Failed to load rainfall stations layer:', err);
    }
  }

  /**
   * Render Risk Zones 3D Layer (Synthesized Risk Envelope)
   */
  function renderRiskZonesLayer() {
    state.riskZoneGroup.clear();
    if (!state.currentCenter) return;

    const local = geoToLocal(state.currentCenter.lat, state.currentCenter.lon);
    if (!local) return;

    // Tactical semi-transparent risk boundary circle
    const geom = new THREE.RingGeometry(500, 3000, 32);
    const mat = new THREE.MeshBasicMaterial({
      color: 0xf97316, // High risk orange
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.35,
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(local.x, local.y, local.z + 5);
    state.riskZoneGroup.add(mesh);
  }

  /**
   * Camera Position Controls
   */
  function zoomCamera(scale) {
    if (!state.camera || !state.controls) return;
    const dir = new THREE.Vector3().subVectors(state.camera.position, state.controls.target);
    dir.multiplyScalar(scale);
    state.camera.position.copy(state.controls.target).add(dir);
  }

  function setTopView() {
    if (!state.camera || !state.controls) return;
    const dist = state.metricHeight * 0.9;
    state.camera.position.set(0, 1, dist);
    state.controls.target.set(0, 0, 0);
    state.camera.up.set(0, 1, 0);
    state.controls.update();
  }

  function setPerspectiveView() {
    if (!state.camera || !state.controls) return;
    state.camera.position.set(0, -state.metricHeight * 0.75, state.metricHeight * 0.55);
    state.controls.target.set(0, 0, 0);
    state.camera.up.set(0, 0, 1);
    state.controls.update();
  }

  function resetCamera() {
    if (!state.camera || !state.controls) return;
    state.camera.position.set(0, -state.metricHeight * 0.7, state.metricHeight * 0.5);
    state.controls.target.set(0, 0, 0);
    state.camera.up.set(0, 0, 1);
    state.controls.update();
  }

  function showStatusBanner(text, type = 'info') {
    const banner = document.getElementById('hud-3d-status-banner');
    if (!banner) return;

    banner.textContent = text;
    banner.className = 'hud-status-banner px-3 py-1 rounded text-xs font-mono font-semibold tracking-wider flex items-center gap-1.5 shadow-lg';

    if (type === 'error') {
      banner.classList.add('bg-error-container/90', 'text-error', 'border', 'border-error/40');
    } else if (type === 'success') {
      banner.classList.add('bg-surface-container/90', 'text-primary', 'border', 'border-primary/40');
    } else {
      banner.classList.add('bg-surface-container-high/90', 'text-secondary', 'animate-pulse');
    }
  }

  // Export to window
  window.Terrain3D = {
    init: init,
    loadCorridor: loadCorridor,
    setExaggeration: setExaggeration,
    toggleLayer: toggleLayer,
    updateQueryMarker: updateQueryMarker,
    resetCamera: resetCamera,
    setTopView: setTopView,
    setPerspectiveView: setPerspectiveView,
    onWindowResize: onWindowResize,
  };

})();
