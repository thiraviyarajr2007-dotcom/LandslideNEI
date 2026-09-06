/**
 * LandslideNEI Dashboard - Leaflet GIS Map Controller
 */

let mapInstance = null;
let baseLayers = {};
let nerBoundaryLayer = null;
let cwcStationsLayer = null;
let queryMarker = null;
let radiusCircle = null;

// Risk color mapping
const RISK_COLORS = {
  LOW: "#22c55e",       // Emerald green
  WATCH: "#eab308",     // Amber yellow
  HIGH: "#f97316",      // Vivid orange
  CRITICAL: "#ef4444",  // Crimson red
  UNKNOWN: "#3b82f6",   // Electric blue
  REJECTED: "#94a3b8"   // Slate gray
};

function initMap() {
  if (mapInstance) return;

  // Center on Northeast India (Assam / Meghalaya / Arunachal hub)
  mapInstance = L.map("gis-map", {
    center: [25.8, 93.0],
    zoom: 7,
    minZoom: 5,
    maxZoom: 16,
    zoomControl: false
  });

  // Position zoom controls top-right
  L.control.zoom({ position: "topright" }).addTo(mapInstance);

  // Basemap options
  const darkMatter = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
    maxZoom: 19
  });

  const osmStandard = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19
  });

  const openTopo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap',
    maxZoom: 17
  });

  // Set default basemap
  darkMatter.addTo(mapInstance);

  baseLayers = {
    "Dark Matter": darkMatter,
    "OpenStreetMap": osmStandard,
    "OpenTopoMap": openTopo
  };

  // Setup layers
  loadNERBoundaries();
  loadCWCStations();

  // Click handler on map
  mapInstance.on("click", function (e) {
    const lat = parseFloat(e.latlng.lat.toFixed(5));
    const lon = parseFloat(e.latlng.lng.toFixed(5));
    if (window.handleMapClick) {
      window.handleMapClick(lat, lon);
    }
  });
}

function loadNERBoundaries() {
  fetch("assets/ner_states.geojson")
    .then(res => res.json())
    .then(data => {
      nerBoundaryLayer = L.geoJSON(data, {
        style: {
          color: "#06b6d4",       // Cyan border
          weight: 1.5,
          opacity: 0.8,
          fillColor: "#0891b2",
          fillOpacity: 0.06
        },
        onEachFeature: function (feature, layer) {
          const stateName = feature.properties.state || "Northeast India";
          layer.bindTooltip(`<strong>${stateName}</strong><br><span style="font-size:11px;color:#cbd5e1;">NER Domain Boundary</span>`, {
            sticky: true,
            className: "ner-tooltip"
          });

          layer.on({
            mouseover: function (e) {
              const l = e.target;
              l.setStyle({
                weight: 2.5,
                color: "#38bdf8",
                fillOpacity: 0.15
              });
            },
            mouseout: function (e) {
              nerBoundaryLayer.resetStyle(e.target);
            }
          });
        }
      }).addTo(mapInstance);
    })
    .catch(err => console.warn("Failed to load ner_states.geojson", err));
}

function loadCWCStations() {
  fetch("assets/cwc_stations.json")
    .then(res => res.json())
    .then(stations => {
      const markers = stations.map(st => {
        const marker = L.circleMarker([st.latitude, st.longitude], {
          radius: 5,
          fillColor: "#38bdf8",
          color: "#0284c7",
          weight: 1.5,
          opacity: 0.9,
          fillOpacity: 0.7
        });

        const popupContent = `
          <div style="font-family: 'Inter', sans-serif; font-size: 12px; color: #0f172a; line-height: 1.4;">
            <div style="font-weight: 700; color: #0284c7; margin-bottom: 2px;">📡 CWC Station</div>
            <div style="font-weight: 600;">${st.name}</div>
            <div style="color: #64748b; font-size: 11px;">State: ${st.state}</div>
            <div style="margin-top: 4px; font-family: monospace; font-size: 11px; background: #f1f5f9; padding: 2px 4px; border-radius: 4px;">
              Lat: ${st.latitude}° | Lon: ${st.longitude}°
            </div>
            ${st.elevation_m ? `<div style="font-size: 11px; color: #475569; margin-top: 2px;">Elev: ${st.elevation_m} m</div>` : ''}
          </div>
        `;
        marker.bindPopup(popupContent);
        return marker;
      });

      cwcStationsLayer = L.layerGroup(markers).addTo(mapInstance);
    })
    .catch(err => console.warn("Failed to load cwc_stations.json", err));
}

function switchBasemap(name) {
  Object.values(baseLayers).forEach(layer => mapInstance.removeLayer(layer));
  if (baseLayers[name]) {
    baseLayers[name].addTo(mapInstance);
  }
}

function toggleLayer(layerName, isVisible) {
  if (layerName === "states" && nerBoundaryLayer) {
    if (isVisible) nerBoundaryLayer.addTo(mapInstance);
    else mapInstance.removeLayer(nerBoundaryLayer);
  } else if (layerName === "stations" && cwcStationsLayer) {
    if (isVisible) cwcStationsLayer.addTo(mapInstance);
    else mapInstance.removeLayer(cwcStationsLayer);
  }
}

function setQueryPoint(lat, lon, riskLevel = "UNKNOWN", stationDistKm = null) {
  if (!mapInstance) return;

  const color = RISK_COLORS[riskLevel] || RISK_COLORS.UNKNOWN;

  // Remove existing query marker and circle
  if (queryMarker) mapInstance.removeLayer(queryMarker);
  if (radiusCircle) mapInstance.removeLayer(radiusCircle);

  // Custom pulsing HTML pin
  const pinIcon = L.divIcon({
    className: "pulse-marker-wrapper",
    html: `
      <div class="pulse-marker" style="--risk-color: ${color};">
        <div class="pulse-core" style="background-color: ${color};"></div>
        <div class="pulse-ring" style="border-color: ${color};"></div>
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  });

  queryMarker = L.marker([lat, lon], { icon: pinIcon, zIndexOffset: 1000 }).addTo(mapInstance);

  // Add 50 km CWC station boundary radius circle
  radiusCircle = L.circle([lat, lon], {
    radius: 50000, // 50 km in meters
    color: color,
    weight: 1,
    dashArray: "4, 6",
    opacity: 0.4,
    fillColor: color,
    fillOpacity: 0.04
  }).addTo(mapInstance);

  // Smooth pan to query location
  mapInstance.setView([lat, lon], Math.max(mapInstance.getZoom(), 8), { animate: true, duration: 0.8 });
}

function clearQueryPoint() {
  if (queryMarker && mapInstance) {
    mapInstance.removeLayer(queryMarker);
    queryMarker = null;
  }
  if (radiusCircle && mapInstance) {
    mapInstance.removeLayer(radiusCircle);
    radiusCircle = null;
  }
}

window.initMap = initMap;
window.switchBasemap = switchBasemap;
window.toggleLayer = toggleLayer;
window.setQueryPoint = setQueryPoint;
window.clearQueryPoint = clearQueryPoint;
