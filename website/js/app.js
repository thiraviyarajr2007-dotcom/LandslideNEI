/**
 * LANDSLIDENEI - Public Product Website Application Script
 * Architecture: Zero external runtime dependencies, lightweight vanilla JS.
 */

document.addEventListener('DOMContentLoaded', () => {
  initMobileMenu();
  initModals();
  initSmoothScroll();
  initActiveNav();
});

/**
 * Mobile Navigation Drawer Toggle
 */
function initMobileMenu() {
  const btn = document.getElementById('mobile-menu-btn');
  const drawer = document.getElementById('mobile-drawer');
  const icon = document.getElementById('mobile-menu-icon');

  if (!btn || !drawer) return;

  btn.addEventListener('click', () => {
    const isOpen = drawer.classList.contains('open');
    if (isOpen) {
      drawer.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
      if (icon) icon.textContent = 'menu';
    } else {
      drawer.classList.add('open');
      btn.setAttribute('aria-expanded', 'true');
      if (icon) icon.textContent = 'close';
    }
  });

  // Close drawer on link click
  const drawerLinks = drawer.querySelectorAll('a');
  drawerLinks.forEach(link => {
    link.addEventListener('click', () => {
      drawer.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
      if (icon) icon.textContent = 'menu';
    });
  });
}

/**
 * Interactive Modals (Windows Download & EOC Advisory Brief)
 */
function initModals() {
  const downloadModal = document.getElementById('download-modal');
  const briefModal = document.getElementById('brief-modal');

  // Trigger buttons
  const downloadBtns = document.querySelectorAll('[data-action="download-windows"]');
  const briefBtns = document.querySelectorAll('[data-action="view-brief"]');

  // Open Handlers
  downloadBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      downloadReleasePackage();
      openModal(downloadModal);
    });
  });

  briefBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openModal(briefModal);
    });
  });

  // Close buttons
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      closeModal(downloadModal);
      closeModal(briefModal);
    });
  });

  // Backdrop click
  [downloadModal, briefModal].forEach(modal => {
    if (!modal) return;
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal(modal);
      }
    });
  });

  // Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeModal(downloadModal);
      closeModal(briefModal);
    }
  });

  // Action inside Download Modal: Download Windows Installer
  const triggerPkgDownload = document.getElementById('trigger-package-download');
  if (triggerPkgDownload) {
    triggerPkgDownload.addEventListener('click', (e) => {
      e.preventDefault();
      downloadReleasePackage();
    });
  }

  // Action inside Brief Modal: Print Brief
  const printBriefBtn = document.getElementById('print-brief-btn');
  if (printBriefBtn) {
    printBriefBtn.addEventListener('click', () => {
      window.print();
    });
  }
}

function openModal(modal) {
  if (!modal) return;
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
  if (!modal) return;
  modal.classList.remove('active');
  document.body.style.overflow = '';
}

/**
 * Official Release and Distribution Configuration
 */
const RELEASE_CONFIG = {
  version: 'v1.0.0',
  assetName: 'LANDSLIDENEI_Setup_x64.exe',
  repo: 'thiraviyarajr2007-dotcom/LandslideNEI',
  sizeFormatted: '70.4 MB',
  sha256: 'bc7a6adceb87bbd2674c98e76f2e834f02ae848125fc9319b3f75c992970aaaf',
  releaseUrl: 'https://github.com/thiraviyarajr2007-dotcom/LandslideNEI/releases/download/v1.0.0/LANDSLIDENEI_Setup_x64.exe',
  rawFallbackUrl: 'https://github.com/thiraviyarajr2007-dotcom/LandslideNEI/raw/main/installer/LANDSLIDENEI_Setup_x64.exe',
  releasePageUrl: 'https://github.com/thiraviyarajr2007-dotcom/LandslideNEI/releases/tag/v1.0.0',
  localApiUrl: '/download/installer'
};

/**
 * Resolves the optimal download URL for LANDSLIDENEI_Setup_x64.exe
 */
function getOptimalDownloadUrl() {
  // If running locally in FastAPI backend context
  if (typeof window !== 'undefined' && window.location) {
    if (window.location.port === '8000' || (window.location.origin && window.location.origin.includes(':8000'))) {
      return RELEASE_CONFIG.localApiUrl;
    }
  }
  // Default to official GitHub Release asset distribution URL
  return RELEASE_CONFIG.releaseUrl;
}

/**
 * Downloads the official standalone Windows desktop application installer (.exe)
 */
function downloadReleasePackage() {
  const downloadUrl = getOptimalDownloadUrl();
  const releaseAssetUrl = RELEASE_CONFIG.releaseUrl;
  const rawFallbackUrl = RELEASE_CONFIG.rawFallbackUrl;
  const releasePageUrl = RELEASE_CONFIG.releasePageUrl;

  // Trigger browser download of .exe file
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.setAttribute('download', RELEASE_CONFIG.assetName);
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  // Update modal status banner
  const statusEl = document.getElementById('download-status');
  if (statusEl) {
    statusEl.innerHTML = '<span class="text-primary font-bold">Download Started:</span> <strong>' + RELEASE_CONFIG.assetName + '</strong> (Windows 64-bit Standalone Installer, ' + RELEASE_CONFIG.sizeFormatted + ').<br>' +
      '<span class="text-on-surface-variant text-[10px]">Your download should begin automatically. If it does not, choose a verified distribution mirror below:</span>' +
      '<div class="mt-2 flex flex-wrap items-center justify-center gap-2 font-mono text-[11px]">' +
      '<a href="' + releaseAssetUrl + '" download="' + RELEASE_CONFIG.assetName + '" class="px-2.5 py-1 bg-primary text-on-primary font-bold rounded hover:bg-inverse-primary shadow-sm">Direct Release Asset (.exe)</a>' +
      '<a href="' + rawFallbackUrl + '" download="' + RELEASE_CONFIG.assetName + '" class="px-2.5 py-1 bg-surface-container-high text-on-surface rounded hover:text-primary">Raw Blob Mirror</a>' +
      '<a href="' + releasePageUrl + '" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1 bg-surface-container-high text-secondary rounded hover:text-primary">Release Notes & Verification</a>' +
      '</div>';
    statusEl.classList.remove('hidden');
  }
}

/**
 * Manifest generator for verification and release provenance
 */
function downloadPlaceholderPackage() {
  const manifest = [
    "======================================================================",
    "LANDSLIDENEI DESKTOP WORKSTATION - WINDOWS x64 RELEASE",
    "======================================================================",
    "Version: 1.0.0-GA",
    "Architecture: x86_64 / Windows 10 & 11",
    "Package: LANDSLIDENEI_Setup_x64.exe",
    "SHA-256: bc7a6adceb87bbd2674c98e76f2e834f02ae848125fc9319b3f75c992970aaaf",
    "Engine: Unified FastAPI + Model A Static LSM + CWC Telemetry",
    "======================================================================"
  ].join("\n");

  const blob = new Blob([manifest], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'LANDSLIDENEI_Setup_x64_Release_Manifest.txt';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Smooth scrolling with offset compensation for fixed header
 */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const targetId = this.getAttribute('href').substring(1);
      if (!targetId) return;

      const targetEl = document.getElementById(targetId) ||
                       (targetId === 'product' ? document.getElementById('hero') : null) ||
                       (targetId === 'dashboard' ? document.getElementById('dashboard-showcase') : null) ||
                       (targetId === 'download' ? document.getElementById('download-release') : null);

      if (targetEl) {
        e.preventDefault();
        const headerHeight = 64;
        const targetPos = targetEl.getBoundingClientRect().top + window.pageYOffset - headerHeight;
        window.scrollTo({
          top: targetPos,
          behavior: 'smooth'
        });
      }
    });
  });
}

/**
 * Active Navigation Highlight based on IntersectionObserver
 */
function initActiveNav() {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('header nav a[href^="#"]');

  if (!sections.length || !navLinks.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.getAttribute('id');
        navLinks.forEach(link => {
          const href = link.getAttribute('href').substring(1);
          if (href === id ||
              (href === 'product' && id === 'hero') ||
              (href === 'dashboard' && id === 'dashboard-showcase') ||
              (href === 'download' && id === 'download-release') ||
              (href === 'how-it-works' && id === 'what-is-landslidenei')) {
            link.classList.add('text-primary', 'border-b-2', 'border-primary');
            link.classList.remove('text-on-surface-variant');
          } else {
            link.classList.remove('text-primary', 'border-b-2', 'border-primary');
            link.classList.add('text-on-surface-variant');
          }
        });
      }
    });
  }, { threshold: 0.3 });

  sections.forEach(s => observer.observe(s));
}
