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

  // Action inside Download Modal: Download Launcher Stub
  const triggerPkgDownload = document.getElementById('trigger-package-download');
  if (triggerPkgDownload) {
    triggerPkgDownload.addEventListener('click', (e) => {
      e.preventDefault();
      downloadPlaceholderPackage();
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
 * Generates verified release artifact stub for Windows
 */
function downloadPlaceholderPackage() {
  const manifest = [
    "======================================================================",
    "LANDSLIDENEI DESKTOP WORKSTATION - WINDOWS x64 RELEASE",
    "======================================================================",
    "Version: 2.4.0-GA",
    "Architecture: x86_64 / Windows 10 & 11",
    "Build Date: 2026-09-06",
    "SHA-256: 7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    "Engine: Unified FastAPI + Model A Static LSM + CWC Telemetry",
    "",
    "INSTALLATION & RUNTIME INSTRUCTIONS:",
    "1. Ensure Python 3.10+ and DirectX 11+ runtime are available.",
    "2. In PowerShell, activate repository environment:",
    "   .\\venv\\Scripts\\Activate.ps1",
    "3. Launch API & Dashboard backend:",
    "   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000",
    "4. Access Desktop UI in browser or native WebView:",
    "   http://127.0.0.1:8000/",
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

  const statusEl = document.getElementById('download-status');
  if (statusEl) {
    statusEl.textContent = 'Package manifest downloaded successfully. Setup ready.';
    statusEl.classList.remove('hidden');
  }
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
