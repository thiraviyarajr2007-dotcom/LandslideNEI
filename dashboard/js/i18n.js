/**
 * LandslideNEI Dashboard - Internationalization (i18n) Dictionary
 * Supports English (en) and Tamil (ta).
 */

const translations = {
  en: {
    // Header & Meta
    appTitle: "LandslideNEI",
    appSubtitle: "AI Early Warning & Operational Decision Support System",
    regionBadge: "Northeast India (8 States)",
    systemStatus: "System Online",
    langEn: "English",
    langTa: "தமிழ்",

    // Navigation & Actions
    queryTitle: "Location Query",
    latPlaceholder: "Latitude (e.g. 27.5925)",
    lonPlaceholder: "Longitude (e.g. 91.6087)",
    queryBtn: "Evaluate Risk",
    profileOnlyBtn: "Static Profile Only",
    clearBtn: "Reset Pin",
    presetsTitle: "SIH Demo Scenarios",
    layersTitle: "Map Layers",
    layerOsm: "OpenStreetMap",
    layerTopo: "OpenTopoMap",
    layerDark: "Dark Matter",
    layerStates: "NER State Boundaries",
    layerStations: "CWC Telemetry Stations",

    // Operational Risk Panel
    riskVerdictTitle: "Operational Decision",
    authoritativeBadge: "AUTHORITATIVE TIER",
    riskLow: "LOW RISK",
    riskWatch: "WATCH",
    riskHigh: "HIGH RISK",
    riskCritical: "CRITICAL ALERT",
    fusionScoreLabel: "Operational Fusion Score",
    fusionScoreDisclaimer: "Engineering ordering synthesis for geospatial ranking; not an event occurrence probability.",
    actionRecommendation: "Recommended Operational Action",

    // Susceptibility Card
    susceptibilityTitle: "Static Terrain Susceptibility (Phase 8F Model A)",
    susceptibilityScore: "Susceptibility Score",
    susceptibilityCategory: "Predisposition Tier",
    uncalibratedDisclaimer: "Uncalibrated random forest score estimating physical terrain predisposition, not an event-time warning.",

    // Physical Features Inspection
    terrainTitle: "Topography & Terrain (Copernicus DEM 30m)",
    elevation: "Elevation",
    slope: "Slope Gradient",
    aspect: "Aspect Direction",
    relief: "Local Relief (5x5)",
    soilTitle: "Soil Characteristics (SoilGrids 250m)",
    soilClass: "Taxonomic Class",
    clay: "Clay Content",
    sand: "Sand Content",
    silt: "Silt Content",
    bulkDensity: "Bulk Density",
    landcoverTitle: "Land Cover (ESA WorldCover 10m)",
    lulcClass: "LULC Classification",
    lulcCode: "Class Code",

    // Rainfall Telemetry Card
    rainfallTitle: "Real-Time Dynamic Rainfall (CWC Telemetry)",
    nearestStation: "Nearest Station",
    stationDistance: "Station Distance",
    stationFreshness: "Telemetry Age",
    freshnessFresh: "FRESH",
    freshnessStale: "STALE",
    freshnessSparse: "SPARSE",
    freshnessNoData: "NO DATA",
    rainfall1h: "1-Hour Rain",
    rainfall24h: "24-Hour Rain",
    rainfall3d: "3-Day Accumulation",
    rainfall7d: "7-Day Accumulation",
    rainfallTriggerLevel: "Rainfall Trigger Level",
    rainfallTriggerScore: "Trigger Score",
    rainfallThresholdDisclaimer: "Thresholds are heuristic operational defaults (DEMO_OPERATIONAL_DEFAULT).",
    imdMacroTitle: "IMD Administrative Macro Context",
    imdStateRain: "State 24h Rainfall",
    imdNormalRain: "Normal 24h Rainfall",
    imdDeparture: "Departure",
    imdDisclaimer: "District/State administrative context only; not local point telemetry.",

    // Explainability
    explainabilityTitle: "Explainability & Reason Codes",
    whyThisRisk: "Why was this risk level assigned?",
    noReasonsAvailable: "No specific anomaly flags triggered.",

    // Status / Errors / Skeletons
    loadingEvaluating: "Extracting terrain, soil, landcover & querying telemetry...",
    errorTitle: "Evaluation Error",
    errorOutsideDomain: "Selected location is outside the supported Northeast India domain (8 states).",
    errorCoordinates: "Invalid coordinates entered. Latitude must be between -90 and 90, Longitude between -180 and 180.",
    disclaimerFooter: "SIH 2024 Finalist AI System. Intended for emergency decision-support. Authoritative risk tier is deterministic; fusion score is non-probabilistic."
  },

  ta: {
    // Header & Meta
    appTitle: "லேண்ட்ஸ்லைட் NEI",
    appSubtitle: "செயற்கை நுண்ணறிவு நிலச்சரிவு முன்-எச்சரிக்கை & செயல்பாட்டு முடிவு ஆதரவு அமைப்பு",
    regionBadge: "வடகிழக்கு இந்தியா (8 மாநிலங்கள்)",
    systemStatus: "அமைப்பு செயல்பாட்டில் உள்ளது",
    langEn: "English",
    langTa: "தமிழ்",

    // Navigation & Actions
    queryTitle: "இட ஆய்வு",
    latPlaceholder: "அட்சரேகை (எ.கா. 27.5925)",
    lonPlaceholder: "தீர்க்கரேகை (எ.கா. 91.6087)",
    queryBtn: "ஆபத்து மதிப்பீடு",
    profileOnlyBtn: "நில அமைப்பு விவரம் மட்டும்",
    clearBtn: "மீட்டமை",
    presetsTitle: "முன்மாதிரி காட்சிகள் (SIH)",
    layersTitle: "வரைபட அடுக்குகள்",
    layerOsm: "ஓபன் ஸ்ட்ரீட் மேப்",
    layerTopo: "நிலப்பரப்பு வரைபடம்",
    layerDark: "டார்க் மேட்டர்",
    layerStates: "NER மாநில எல்லைகள்",
    layerStations: "CWC மழை அளவீட்டு நிலையங்கள்",

    // Operational Risk Panel
    riskVerdictTitle: "செயல்பாட்டு முடிவு",
    authoritativeBadge: "அதிகாரப்பூர்வ நிலை",
    riskLow: "குறைந்த ஆபத்து",
    riskWatch: "கண்காணிப்பு நிலை",
    riskHigh: "அதிக ஆபத்து",
    riskCritical: "அவசர எச்சரிக்கை",
    fusionScoreLabel: "செயல்பாட்டு ஒருங்கிணைப்பு மதிப்பெண்",
    fusionScoreDisclaimer: "இடஞ்சார்ந்த முன்னுரிமைக்கான பொறியியல் அளவீடு; இது நிகழ்வு நிகழ்தகவு அல்ல.",
    actionRecommendation: "பரிந்துரைக்கப்பட்ட நடவடிக்கை",

    // Susceptibility Card
    susceptibilityTitle: "இயற்கை நிலச்சரிவு உணர்திறன் (Phase 8F மாதிரி A)",
    susceptibilityScore: "உணர்திறன் மதிப்பெண்",
    susceptibilityCategory: "உணர்திறன் நிலை",
    uncalibratedDisclaimer: "நிலப்பரப்பின் இயற்பியல் அமைப்பை மதிப்பிடும் அளவீடு; நிகழ்நேர நிகழ்வு நிகழ்தகவு அல்ல.",

    // Physical Features Inspection
    terrainTitle: "நிலப்பரப்பு பண்புகள் (Copernicus DEM 30m)",
    elevation: "உயரம்",
    slope: "சரிவு சாய்வு",
    aspect: "சரிவு திசை",
    relief: "உள்ளூர் நில ஏற்றத்தாழ்வு (5x5)",
    soilTitle: "மண் பண்புகள் (SoilGrids 250m)",
    soilClass: "மண் வகைப்பாடு",
    clay: "களிமண் அளவு",
    sand: "மணல் அளவு",
    silt: "வண்டல் அளவு",
    bulkDensity: "மண் அடர்த்தி",
    landcoverTitle: "நிலப்பயன்பாடு (ESA WorldCover 10m)",
    lulcClass: "நிலப்பரப்பு வகை",
    lulcCode: "குறியீடு",

    // Rainfall Telemetry Card
    rainfallTitle: "நிகழ்நேர மழை அளவீடு (CWC டெலிமெட்ரி)",
    nearestStation: "அருகிலுள்ள நிலையம்",
    stationDistance: "நிலைய தூரம்",
    stationFreshness: "தரவு நேரம்",
    freshnessFresh: "புதிய தரவு",
    freshnessStale: "பழைய தரவு",
    freshnessSparse: "குறைந்த தரவு",
    freshnessNoData: "தரவு இல்லை",
    rainfall1h: "1-மணி நேர மழை",
    rainfall24h: "24-மணி நேர மழை",
    rainfall3d: "3-நாள் மழை சேகரிப்பு",
    rainfall7d: "7-நாள் மழை சேகரிப்பு",
    rainfallTriggerLevel: "மழை தூண்டுதல் நிலை",
    rainfallTriggerScore: "தூண்டுதல் மதிப்பெண்",
    rainfallThresholdDisclaimer: "வரம்புகள் செயல்பாட்டு இயல்புநிலை அமைப்புகளாகும்.",
    imdMacroTitle: "IMD நிர்வாக மேக்ரோ சூழல்",
    imdStateRain: "மாநில 24 மணி நேர மழை",
    imdNormalRain: "இயல்பான 24 மணி நேர மழை",
    imdDeparture: "வித்தியாசம்",
    imdDisclaimer: "மாவட்ட/மாநில அளவிலான நிர்வாக சூழல் மட்டுமே; உள்ளூர் துல்லிய புள்ளி அல்ல.",

    // Explainability
    explainabilityTitle: "காரண விளக்கங்கள்",
    whyThisRisk: "இந்த ஆபத்து நிலை ஏன் ஒதுக்கப்பட்டது?",
    noReasonsAvailable: "குறிப்பிட்ட அசாதாரண கொடிகள் எதுவும் தூண்டப்படவில்லை.",

    // Status / Errors / Skeletons
    loadingEvaluating: "நிலப்பரப்பு, மண், நிலப்பயன்பாடு மற்றும் மழையளவு மதிப்பீடு செய்யப்படுகிறது...",
    errorTitle: "மதிப்பீட்டுப் பிழை",
    errorOutsideDomain: "தேர்ந்தெடுக்கப்பட்ட இடம் வடகிழக்கு இந்திய எல்லைக்கு (8 மாநிலங்கள்) வெளியே உள்ளது.",
    errorCoordinates: "தவறான ஆயத்தொலைவுகள். அட்சரேகை -90 முதல் 90 வரை, தீர்க்கரேகை -180 முதல் 180 வரை இருக்க வேண்டும்.",
    disclaimerFooter: "SIH 2024 இறுதிப்போட்டி அமைப்பு. பேரிடர் மேலாண்மை முடிவு ஆதரவுக்காக மட்டுமே வடிவமைக்கப்பட்டது."
  }
};

let currentLang = "en";

function setLanguage(lang) {
  if (translations[lang]) {
    currentLang = lang;
    document.querySelectorAll("[data-i18n]").forEach(elem => {
      const key = elem.getAttribute("data-i18n");
      if (translations[currentLang][key]) {
        elem.textContent = translations[currentLang][key];
      }
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach(elem => {
      const key = elem.getAttribute("data-i18n-placeholder");
      if (translations[currentLang][key]) {
        elem.setAttribute("placeholder", translations[currentLang][key]);
      }
    });

    // Update active button state
    document.querySelectorAll(".lang-btn").forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-lang") === currentLang);
    });

    // Re-render any dynamic content if present
    if (window.renderCurrentEvaluation) {
      window.renderCurrentEvaluation();
    }
  }
}

function t(key, fallback = "") {
  return (translations[currentLang] && translations[currentLang][key]) || fallback || key;
}

window.translations = translations;
window.setLanguage = setLanguage;
window.t = t;
