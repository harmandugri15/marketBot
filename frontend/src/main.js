import './style.css';
import { auth } from './api.js';

// Page components
import { renderDashboard } from './pages/dashboard.js';
import { renderScanner } from './pages/scanner.js';
import { renderBacktest } from './pages/backtest.js';
import { renderForwardTest } from './pages/forward_test.js';
import { renderTrades } from './pages/trades.js';
import { renderSettings } from './pages/settings.js';
import { renderSandbox } from './pages/sandbox.js';
import { renderLandingPage } from './pages/landing.js';

const app = document.getElementById('app');

// Simple Router
const initTheme = () => {
  const savedTheme = localStorage.getItem('mb_theme') || 'dark';
  if (savedTheme === 'light') {
    document.body.classList.add('theme-light');
  } else {
    document.body.classList.remove('theme-light');
  }
};
initTheme();

window.toggleTheme = () => {
  const isLight = document.body.classList.toggle('theme-light');
  localStorage.setItem('mb_theme', isLight ? 'light' : 'dark');
  // Dispatch a custom event so charts can re-render if needed
  window.dispatchEvent(new Event('themeChanged'));
};

const routes = {
  '/': { title: 'Dashboard', render: renderDashboard },
  '/scanner': { title: 'Scanner', render: renderScanner },
  '/sandbox': { title: 'Student Sandbox', render: renderSandbox },
  '/backtest': { title: 'Backtest Engine', render: renderBacktest },
  '/forward-test': { title: 'Forward Testing', render: renderForwardTest },
  '/trades': { title: 'Trades & Portfolio', render: renderTrades },
  '/settings': { title: 'Settings', render: renderSettings }
};

async function initApp() {
  try {
    const user = await auth.me();
    renderLayout(user);
    navigate(window.location.pathname);
  } catch (err) {
    // Unauthenticated -> Show landing page
    renderLandingPage(app, (mode) => {
      renderAuthModal(mode);
    });
  }
}

function renderAuthModal(initialMode = 'login') {
  // Remove existing modal if any
  const existing = document.getElementById('auth-modal-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'auth-modal-overlay';
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="auth-card" style="position:relative;">
      <button id="auth-close-btn" class="modal-close">✕</button>
      
      <div class="auth-logo">
        <img src="/logo.png" alt="MarketBot Logo" width="48" height="48" style="border-radius: 8px; margin-bottom: 0.5rem;">
        <h1>MARKET_BOT_OS</h1>
        <p class="text-muted" style="font-size: 0.85rem;">System Authentication</p>
      </div>
      
      <div class="auth-tabs">
        <div id="auth-tab-bg" class="auth-tab-bg"></div>
        <button id="tab-login" class="auth-tab">Log In</button>
        <button id="tab-register" class="auth-tab">Sign Up</button>
      </div>

      <form id="auth-form">
        <div class="form-group">
          <label class="form-label">Username</label>
          <div style="position:relative;">
            <input type="text" id="username" class="form-control" required minlength="3" placeholder="Enter username" />
            <div id="username-status" class="username-check" style="position:absolute; right:10px; top:50%; transform:translateY(-50%);"></div>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Password</label>
          <div class="password-wrapper">
            <input type="password" id="password" class="form-control" required minlength="8" placeholder="Enter password" />
            <button type="button" id="toggle-pw" class="password-toggle">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
            </button>
          </div>
          <div id="pw-strength-container" style="display:none;">
            <div class="strength-bar-track">
              <div id="pw-bar-fill" class="strength-bar-fill"></div>
            </div>
            <div id="pw-text" class="strength-text"></div>
          </div>
        </div>
        <div class="form-group" id="confirm-pw-group" style="display:none;">
          <label class="form-label">Confirm Password</label>
          <input type="password" id="confirm-password" class="form-control" minlength="8" placeholder="Confirm password" />
        </div>
        <button type="submit" id="submit-btn" class="btn btn-primary" style="width:100%; margin-top: 1rem; position:relative;">
          <span id="submit-text">Log In</span>
          <span id="submit-spinner" style="display:none;">Processing...</span>
        </button>
        <div id="auth-error" class="auth-error error"></div>
      </form>
    </div>
  `;
  document.body.appendChild(overlay);

  let mode = initialMode;
  let checkTimeout = null;

  const tabLogin = document.getElementById('tab-login');
  const tabRegister = document.getElementById('tab-register');
  const tabBg = document.getElementById('auth-tab-bg');
  const submitBtn = document.getElementById('submit-btn');
  const submitText = document.getElementById('submit-text');
  const submitSpinner = document.getElementById('submit-spinner');
  const errDiv = document.getElementById('auth-error');
  const usernameInput = document.getElementById('username');
  const usernameStatus = document.getElementById('username-status');
  const passwordInput = document.getElementById('password');
  const togglePw = document.getElementById('toggle-pw');
  const pwStrengthContainer = document.getElementById('pw-strength-container');
  const pwBarFill = document.getElementById('pw-bar-fill');
  const confirmPwGroup = document.getElementById('confirm-pw-group');
  const confirmPwInput = document.getElementById('confirm-password');

  document.getElementById('auth-close-btn').addEventListener('click', () => {
    overlay.remove();
  });

  // Show/Hide password
  togglePw.addEventListener('click', () => {
    const isPw = passwordInput.type === 'password';
    passwordInput.type = isPw ? 'text' : 'password';
    confirmPwInput.type = isPw ? 'text' : 'password';
  });

  function setMode(newMode) {
    mode = newMode;
    errDiv.classList.remove('show');
    
    if (mode === 'login') {
      tabLogin.classList.add('active');
      tabRegister.classList.remove('active');
      tabBg.style.transform = 'translateX(0)';
      submitText.textContent = 'Log In';
      pwStrengthContainer.style.display = 'none';
      confirmPwGroup.style.display = 'none';
      confirmPwInput.required = false;
      usernameStatus.className = 'username-check';
      usernameStatus.textContent = '';
    } else {
      tabRegister.classList.add('active');
      tabLogin.classList.remove('active');
      tabBg.style.transform = 'translateX(100%)';
      submitText.textContent = 'Sign Up';
      pwStrengthContainer.style.display = 'block';
      confirmPwGroup.style.display = 'block';
      confirmPwInput.required = true;
      checkUsernameAvailability();
    }
  }

  tabLogin.addEventListener('click', () => setMode('login'));
  tabRegister.addEventListener('click', () => setMode('register'));
  setMode(initialMode);

  // Username check
  function checkUsernameAvailability() {
    if (mode !== 'register') return;
    const val = usernameInput.value.trim();
    if (val.length < 3) {
      usernameStatus.className = 'username-check';
      usernameStatus.textContent = '';
      return;
    }
    
    if (checkTimeout) clearTimeout(checkTimeout);
    checkTimeout = setTimeout(async () => {
      try {
        usernameStatus.className = 'username-check checking';
        usernameStatus.textContent = '...';
        const res = await auth.checkUsername(val);
        if (res.available) {
          usernameStatus.className = 'username-check available';
          usernameStatus.textContent = '✓ Available';
        } else {
          usernameStatus.className = 'username-check taken';
          usernameStatus.textContent = '✗ Taken';
        }
      } catch (e) {
        usernameStatus.className = 'username-check';
        usernameStatus.textContent = '';
      }
    }, 500);
  }
  
  usernameInput.addEventListener('input', checkUsernameAvailability);

  // Password strength meter
  passwordInput.addEventListener('input', () => {
    if (mode !== 'register') return;
    const val = passwordInput.value;
    const txt = document.getElementById('pw-text');
    
    let strength = 0;
    if (val.length >= 8) strength += 1;
    if (/[a-zA-Z]/.test(val)) strength += 1;
    if (/[0-9]/.test(val) && val.length >= 8) strength += 1;
    
    if (strength === 0) {
      pwBarFill.style.width = '0%';
      txt.textContent = '';
    } else if (strength === 1) {
      pwBarFill.style.width = '33%';
      pwBarFill.style.background = 'var(--danger-color)';
      txt.textContent = 'Weak';
      txt.style.color = 'var(--danger-color)';
    } else if (strength === 2) {
      pwBarFill.style.width = '66%';
      pwBarFill.style.background = 'var(--warning-color)';
      txt.textContent = 'Medium (needs numbers)';
      txt.style.color = 'var(--warning-color)';
    } else if (strength === 3) {
      pwBarFill.style.width = '100%';
      pwBarFill.style.background = 'var(--accent-color)';
      txt.textContent = 'Strong';
      txt.style.color = 'var(--accent-color)';
    }
  });

  // Form submit
  document.getElementById('auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const u = usernameInput.value;
    const p = passwordInput.value;
    
    if (mode === 'register') {
      if (p !== confirmPwInput.value) {
        errDiv.classList.add('show');
        errDiv.textContent = 'Passwords do not match';
        return;
      }
      if (p.length < 8 || !/[a-zA-Z]/.test(p) || !/[0-9]/.test(p)) {
        errDiv.classList.add('show');
        errDiv.textContent = 'Password must be at least 8 chars and contain letters & numbers';
        return;
      }
    }
    
    errDiv.classList.remove('show');
    submitBtn.disabled = true;
    submitText.style.display = 'none';
    submitSpinner.style.display = 'inline-block';
    
    try {
      let res;
      if (mode === 'login') {
        res = await auth.login(u, p);
      } else {
        res = await auth.register(u, p);
      }
      localStorage.setItem('mb_token', res.access_token);
      window.location.reload();
    } catch (err) {
      errDiv.classList.add('show');
      errDiv.textContent = err.message;
      submitBtn.disabled = false;
      submitText.style.display = 'inline-block';
      submitSpinner.style.display = 'none';
    }
  });
}

function renderLayout(user) {
  const userInitials = user.username.substring(0, 2).toUpperCase();
  
  app.innerHTML = `
    <aside class="sidebar">
      <div class="sidebar-logo" style="display:flex; align-items:center; gap:0.5rem; font-family:var(--font-mono); font-size:1.1rem; padding: 1.5rem 1rem;">
        <img src="/logo.png" alt="MarketBot Logo" width="28" height="28" style="border-radius: 6px;">
        MARKET_BOT_OS
      </div>
      <nav id="nav-links">
        <a href="/" class="nav-link" data-route="/"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg> Dashboard</a>
        <a href="/sandbox" class="nav-link" data-route="/sandbox"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg> Student Sandbox</a>
        <a href="/scanner" class="nav-link" data-route="/scanner"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> Scanner</a>
        <a href="/trades" class="nav-link" data-route="/trades"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg> Trades</a>
        <a href="/forward-test" class="nav-link" data-route="/forward-test"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg> Forward Test</a>
        <a href="/backtest" class="nav-link" data-route="/backtest"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Backtest</a>
        <a href="/settings" class="nav-link" data-route="/settings"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg> Settings</a>
      </nav>
      <div style="margin-top: auto; padding: 1rem 0;">
        <button id="logout-btn" class="btn btn-outline" style="width:100%; border-color: rgba(255,255,255,0.2); color: white;">Logout</button>
      </div>
    </aside>
    <main class="main-content">
      <header class="topbar">
        <h2 id="page-title" style="margin:0; font-size:1.25rem;">Dashboard</h2>
        <div class="topbar-actions">
          <span class="badge ${user.trading_mode === 'live' ? 'badge-danger' : 'badge-info'}">Mode: ${user.trading_mode.toUpperCase()}</span>
          <button class="theme-toggle-btn" onclick="window.toggleTheme()" title="Toggle Theme">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
          </button>
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <div class="user-avatar" title="${user.username}">
              ${userInitials}
            </div>
            <span style="font-size: 0.875rem; font-weight:500;">${user.username}</span>
          </div>
        </div>
      </header>
      <div id="page-container" class="page-container">
        <!-- Content gets injected here -->
      </div>
    </main>
  `;

  document.getElementById('logout-btn').addEventListener('click', () => {
    localStorage.removeItem('mb_token');
    window.location.reload();
  });

  // Handle SPA navigation
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      navigate(e.currentTarget.getAttribute('data-route'));
    });
  });
}

const routeContainers = {};

function navigate(path) {
  // Update URL without reload
  if (window.location.pathname !== path) {
    window.history.pushState({}, '', path);
  }
  
  const route = routes[path] || routes['/'];
  document.getElementById('page-title').textContent = route.title;
  
  // Update active state in sidebar
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const activeLink = document.querySelector(`.nav-link[data-route="${path}"]`);
  if (activeLink) activeLink.classList.add('active');

  // Render page content
  const container = document.getElementById('page-container');
  
  // Hide all cached children
  Array.from(container.children).forEach(c => {
    c.style.display = 'none';
  });

  if (!routeContainers[path]) {
    const pageContainer = document.createElement('div');
    container.appendChild(pageContainer);
    routeContainers[path] = pageContainer;
    
    pageContainer.innerHTML = '<div style="text-align:center; padding: 2rem;">Loading...</div>';
    route.render(pageContainer).catch(err => {
      pageContainer.innerHTML = `<div class="card negative">Error loading page: ${err.message}</div>`;
    });
  } else {
    routeContainers[path].style.display = 'block';
  }
}

// Handle browser back/forward buttons
window.addEventListener('popstate', () => {
  navigate(window.location.pathname);
});

window.addEventListener('auth:expired', () => {
  renderLandingPage(app, (mode) => renderAuthModal(mode));
});

// Boot
initApp();
