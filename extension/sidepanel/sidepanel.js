/**
 * LandslideNEI Sentinel Monitor - Extension Side Panel Controller
 */

const DEFAULT_API_BASE = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', async () => {
  const iframe = document.getElementById('dashboard-frame');
  const btnReload = document.getElementById('btn-reload');
  const btnNewTab = document.getElementById('btn-newtab');
  const offlineNotice = document.getElementById('offline-notice');
  const currentUrlSpan = document.getElementById('current-url');

  let baseUrl = DEFAULT_API_BASE;
  if (chrome && chrome.storage && chrome.storage.local) {
    const res = await chrome.storage.local.get(['landslide_api_base']);
    if (res.landslide_api_base) {
      baseUrl = res.landslide_api_base.replace(/\/$/, '');
    }
  }

  const targetUrl = `${baseUrl}/dashboard/`;
  if (currentUrlSpan) currentUrlSpan.textContent = baseUrl;

  // Check health
  try {
    const check = await fetch(`${baseUrl}/api/v1/health`, { signal: AbortSignal.timeout(2000) });
    if (!check.ok) {
      if (offlineNotice) offlineNotice.style.display = 'block';
    } else {
      if (offlineNotice) offlineNotice.style.display = 'none';
    }
  } catch (err) {
    if (offlineNotice) offlineNotice.style.display = 'block';
  }

  if (iframe) {
    iframe.src = targetUrl;
  }

  if (btnReload) {
    btnReload.addEventListener('click', () => {
      if (iframe) iframe.src = targetUrl;
    });
  }

  if (btnNewTab) {
    btnNewTab.addEventListener('click', () => {
      if (chrome && chrome.tabs && chrome.tabs.create) {
        chrome.tabs.create({ url: targetUrl });
      } else {
        window.open(targetUrl, '_blank');
      }
    });
  }
});
