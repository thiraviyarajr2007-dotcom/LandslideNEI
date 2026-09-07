/**
 * LandslideNEI Sentinel Monitor - Background Service Worker (Manifest V3)
 * Handles background telemetry polling, toolbar badge status, and emergency alerts.
 */

const DEFAULT_API_BASE = 'http://localhost:8000';
const ALARM_NAME = 'POLL_LANDSLIDE_RISK';
const POLL_INTERVAL_MINUTES = 15;

const BADGE_COLORS = {
  LOW: '#10b981',      // Emerald green
  WATCH: '#f59e0b',    // Amber
  HIGH: '#f97316',     // Orange
  CRITICAL: '#ef4444'  // Emergency Red
};

// On installation or browser startup
chrome.runtime.onInstalled.addListener(() => {
  console.log('[LandslideNEI] Background service worker registered.');

  // Set initial badge
  chrome.action.setBadgeText({ text: 'LOW' });
  chrome.action.setBadgeBackgroundColor({ color: BADGE_COLORS.LOW });

  // Create periodic alarm for background monitoring
  chrome.alarms.create(ALARM_NAME, {
    periodInMinutes: POLL_INTERVAL_MINUTES
  });

  // Enable side panel on action click if supported
  if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false }).catch(() => {});
  }
});

// Periodic alarm handler
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === ALARM_NAME) {
    await pollCurrentSectorRisk();
  }
});

// Message listener from popup or side panel
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'RISK_UPDATE') {
    const text = msg.text || (msg.level === 'CRITICAL' ? 'CRIT' : msg.level);
    const color = msg.color || BADGE_COLORS[msg.level] || '#10b981';
    chrome.action.setBadgeText({ text });
    chrome.action.setBadgeBackgroundColor({ color });
    sendResponse({ success: true });
  }
  return true;
});

/**
 * Polls the configured active corridor risk.
 */
async function pollCurrentSectorRisk() {
  try {
    const storage = await chrome.storage.local.get(['landslide_api_base', 'active_corridor']);
    const baseUrl = (storage.landslide_api_base || DEFAULT_API_BASE).replace(/\/$/, '');
    const coords = storage.active_corridor || { lat: 25.6740, lon: 94.1120 }; // Kohima default

    const res = await fetch(`${baseUrl}/api/v1/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        latitude: coords.lat,
        longitude: coords.lon,
        auto_refetch: true
      }),
      signal: AbortSignal.timeout(5000)
    });

    if (res.ok) {
      const data = await res.json();
      const level = (data.risk?.risk_level || 'LOW').toUpperCase();
      const text = level === 'CRITICAL' ? 'CRIT' : level;
      const color = BADGE_COLORS[level] || '#10b981';

      chrome.action.setBadgeText({ text });
      chrome.action.setBadgeBackgroundColor({ color });

      // If critical or high, issue Chrome notification
      if (level === 'CRITICAL' || level === 'HIGH') {
        if (chrome.notifications && chrome.notifications.create) {
          chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: `Landslide Alert: ${level} RISK`,
            message: `Sector alert for ${data.location?.district || 'monitored corridor'}: ${data.risk?.operational_action || 'Elevated risk detected.'}`,
            priority: 2
          });
        }
      }
    }
  } catch (err) {
    console.warn('[LandslideNEI] Background poll warning:', err.message);
  }
}
