/**
 * LandslideNEI Dashboard - SIH Demo Presets
 * Predefined geographic locations for jury and operational demonstrations.
 */

const DEMO_PRESETS = [
  {
    id: "guwahati",
    name_en: "Guwahati Urban, Assam",
    name_ta: "குவாஹாட்டி நகரம், அசாம்",
    lat: 26.1445,
    lon: 91.7362,
    badge: "LOW RISK",
    badgeClass: "badge-low",
    description_en: "Gentle valley topography with nearby CWC telemetry station (4.2 km). Demonstrates low baseline hazard.",
    description_ta: "குறைந்த சாய்வு கொண்ட சமவெளி பகுதி, 4.2 கிமீ தூரத்தில் CWC நிலையம் உள்ளது. குறைந்த ஆபத்துக்கான மாதிரி."
  },
  {
    id: "tawang",
    name_en: "Tawang Alpine, Arunachal",
    name_ta: "தவாங் மலைப்பகுதி, அருணாச்சல்",
    lat: 27.5925,
    lon: 91.6087,
    badge: "WATCH (PRECAUTIONARY)",
    badgeClass: "badge-watch",
    description_en: "Steep Himalayan terrain (>30° slope). No CWC station within 50 km cap; system raises precautionary WATCH.",
    description_ta: "செங்குத்தான இமயமலை சரிவு (>30°). 50 கிமீ வரம்பிற்குள் CWC நிலையம் இல்லாததால் முன்னெச்சரிக்கை கண்காணிப்பு நிலை."
  },
  {
    id: "mangan",
    name_en: "Mangan / Chungthang, Sikkim",
    name_ta: "மங்கன் / சுங்தாங், சிக்கிம்",
    lat: 27.5028,
    lon: 88.5284,
    badge: "HIGH SUSCEPTIBILITY",
    badgeClass: "badge-high",
    description_en: "Teesta basin gorge with extreme local relief (>50m std) and fragile young Himalayan geology.",
    description_ta: "தீஸ்தா ஆற்றுப்பள்ளத்தாக்கு, மிக உயர்ந்த நில ஏற்றத்தாழ்வு மற்றும் உடையக்கூடிய இமயமலை புவியியல்."
  },
  {
    id: "cherrapunji",
    name_en: "Cherrapunji / Sohra, Meghalaya",
    name_ta: "செர்ராபுஞ்சி / சோஹ்ரா, மேகாலயா",
    lat: 25.2986,
    lon: 91.7317,
    badge: "EXTREME RAINFALL ZONE",
    badgeClass: "badge-watch",
    description_en: "Southern Meghalaya escarpment with high gravitational relief and extreme orographic monsoon dynamics.",
    description_ta: "தெற்கு மேகாலயா செங்குத்து பாறை முகடு, கடுமையான பருவமழை தாக்கம் உள்ள பகுதி."
  },
  {
    id: "aizawl",
    name_en: "Aizawl Ridge City, Mizoram",
    name_ta: "ஐஸ்வால் முகடு நகரம், மிசோரம்",
    lat: 23.7271,
    lon: 92.7176,
    badge: "URBAN RIDGE HAZARD",
    badgeClass: "badge-high",
    description_en: "Densely inhabited ridge-crest topography with alternating shale/sandstone sequences.",
    description_ta: "அடர்த்தியான குடியிருப்பு கொண்ட மலைமுகடு, மண் சரிவுக்கு வாய்ப்புள்ள பகுதி."
  },
  {
    id: "delhi_reject",
    name_en: "New Delhi (Out of Domain)",
    name_ta: "புது தில்லி (எல்லைக்கு வெளியே)",
    lat: 28.6139,
    lon: 77.2090,
    badge: "DOMAIN REJECTION TEST",
    badgeClass: "badge-reject",
    description_en: "Location outside Northeast India (8 states). Demonstrates robust domain validation and HTTP 400 rejection.",
    description_ta: "வடகிழக்கு இந்திய எல்லைக்கு வெளியே உள்ள இடம். எல்லை சரிபார்ப்பு மற்றும் நிராகரிப்பு சோதனையை விளக்குகிறது."
  }
];

window.DEMO_PRESETS = DEMO_PRESETS;
