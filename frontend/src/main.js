import './style.css';
import { auth } from './api.js';

// Page components
import { renderDashboard } from './pages/dashboard.js';
import { renderScanner } from './pages/scanner.js';
import { renderBacktest } from './pages/backtest.js';
import { renderForwardTest } from './pages/forward_test.js';
import { renderTrades } from './pages/trades.js';
import { renderSettings } from './pages/settings.js';

const app = document.getElementById('app');

// Simple Router
const routes = {
  '/': { title: 'Dashboard', render: renderDashboard },
  '/scanner': { title: 'Scanner', render: renderScanner },
  '/backtest': { title: 'Backtest Engine', render: renderBacktest },
  '/forward-test': { title: 'Forward Testing', render: renderForwardTest },
  '/trades': { title: 'Trades & Portfolio', render: renderTrades },
  '/settings': { title: 'Settings', render: renderSettings }
};

async function initApp() {
  // Bypass auth as requested
  const user = { app: "MarketBot", trading_mode: "paper" };
  renderLayout(user);
  navigate(window.location.pathname);
}

function renderLogin() {
  app.innerHTML = `
    <div style="display:flex; height:100vh; align-items:center; justify-content:center; background:var(--bg-color);">
      <div class="card" style="width: 400px;">
        <h2 style="text-align:center; margin-bottom: 1.5rem;" class="text-gradient">MarketBot Login</h2>
        <form id="login-form">
          <div class="form-group">
            <label class="form-label">Username</label>
            <input type="text" id="username" class="form-control" required value="admin" />
          </div>
          <div class="form-group">
            <label class="form-label">Password</label>
            <input type="password" id="password" class="form-control" required />
          </div>
          <button type="submit" class="btn btn-primary" style="width:100%;">Login</button>
          <div id="login-error" class="negative mt-4" style="text-align:center; font-size:0.875rem;"></div>
        </form>
      </div>
    </div>
  `;

  document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;
    const errDiv = document.getElementById('login-error');
    
    try {
      errDiv.textContent = 'Authenticating...';
      const res = await auth.login(u, p);
      localStorage.setItem('mb_token', res.access_token);
      window.location.reload();
    } catch (err) {
      errDiv.textContent = err.message;
    }
  });
}

function renderLayout(user) {
  app.innerHTML = `
    <aside class="sidebar">
      <div class="sidebar-logo">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--primary-color)"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
        MarketBot
      </div>
      <nav id="nav-links">
        <a href="/" class="nav-link" data-route="/"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg> Dashboard</a>
        <a href="/scanner" class="nav-link" data-route="/scanner"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> Scanner</a>
        <a href="/trades" class="nav-link" data-route="/trades"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg> Trades</a>
        <a href="/forward-test" class="nav-link" data-route="/forward-test"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg> Forward Test</a>
        <a href="/backtest" class="nav-link" data-route="/backtest"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Backtest</a>
        <a href="/settings" class="nav-link" data-route="/settings"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg> Settings</a>
      </nav>
      <div style="margin-top: auto;">
        <button id="logout-btn" class="btn btn-outline" style="width:100%;">Logout</button>
      </div>
    </aside>
    <main class="main-content">
      <header class="topbar">
        <h2 id="page-title" style="margin:0; font-size:1.25rem;">Dashboard</h2>
        <div class="flex items-center gap-4">
          <span class="badge ${user.trading_mode === 'live' ? 'badge-danger' : 'badge-info'}">Mode: ${user.trading_mode.toUpperCase()}</span>
          <span style="font-size: 0.875rem; color: var(--text-muted);">${user.app}</span>
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
  container.innerHTML = '<div style="text-align:center; padding: 2rem;">Loading...</div>';
  route.render(container).catch(err => {
    container.innerHTML = `<div class="card negative">Error loading page: ${err.message}</div>`;
  });
}

// Handle browser back/forward buttons
window.addEventListener('popstate', () => {
  navigate(window.location.pathname);
});

window.addEventListener('auth:expired', () => {
  renderLogin();
});

// Boot
initApp();
