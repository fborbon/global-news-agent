/* ── Mobile nav toggle ───────────────────────────────────────────── */
const navToggle = document.getElementById('nav-toggle');
const mainNav   = document.getElementById('main-nav');
if (navToggle && mainNav) {
  navToggle.addEventListener('click', () => mainNav.classList.toggle('open'));
}

/* ── Category filter (region page) ──────────────────────────────── */
const filterBar = document.getElementById('filter-bar');
if (filterBar) {
  filterBar.addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;

    filterBar.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const cat = btn.dataset.cat;
    document.querySelectorAll('#stories-grid .story-card').forEach(card => {
      if (cat === 'all' || card.dataset.cat === cat) {
        card.classList.remove('hidden');
      } else {
        card.classList.add('hidden');
      }
    });
  });
}

/* ── Breaking page sidebar filter ───────────────────────────────── */
const catNav = document.querySelector('.cat-nav');
if (catNav) {
  catNav.addEventListener('click', (e) => {
    const link = e.target.closest('.cat-nav-link');
    if (!link) return;
    e.preventDefault();

    catNav.querySelectorAll('.cat-nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');

    const cat = link.dataset.cat;
    document.querySelectorAll('#breaking-feed .cat-section').forEach(section => {
      if (cat === 'all' || section.dataset.cat === cat) {
        section.style.display = '';
      } else {
        section.style.display = 'none';
      }
    });

    // Smooth scroll to section
    if (cat !== 'all') {
      const target = document.getElementById(cat);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
}

/* ── Date picker ─────────────────────────────────────────────────── */
const dateSelect = document.getElementById('date-select');
if (dateSelect) {
  fetch('data/available_dates.json')
    .then(r => r.json())
    .then(dates => {
      const current = dateSelect.dataset.current;
      dateSelect.innerHTML = '';
      dates.forEach(({ date, path }, i) => {
        const opt = document.createElement('option');
        opt.value = path;
        opt.textContent = i === 0 ? `${date} — latest` : date;
        if (date === current) opt.selected = true;
        dateSelect.appendChild(opt);
      });
      dateSelect.addEventListener('change', () => {
        if (dateSelect.value) window.location.href = dateSelect.value;
      });
    })
    .catch(() => {
      const wrap = dateSelect.closest('.date-selector');
      if (wrap) wrap.style.display = 'none';
    });
}

/* ── Breaking page sidebar drawer (mobile) ───────────────────────── */
const sidebarTab     = document.getElementById('sidebar-tab');
const sidebarOverlay = document.getElementById('sidebar-overlay');
const breakingSidebar = document.getElementById('breaking-sidebar');

function openSidebar() {
  if (!breakingSidebar) return;
  breakingSidebar.classList.add('open');
  if (sidebarOverlay) sidebarOverlay.classList.add('visible');
  if (sidebarTab) sidebarTab.setAttribute('aria-expanded', 'true');
}
function closeSidebar() {
  if (!breakingSidebar) return;
  breakingSidebar.classList.remove('open');
  if (sidebarOverlay) sidebarOverlay.classList.remove('visible');
  if (sidebarTab) sidebarTab.setAttribute('aria-expanded', 'false');
}

if (sidebarTab) sidebarTab.addEventListener('click', () => {
  breakingSidebar.classList.contains('open') ? closeSidebar() : openSidebar();
});
if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

// Auto-close drawer after picking a category on mobile
if (catNav && breakingSidebar) {
  catNav.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && e.target.closest('.cat-nav-link')) {
      setTimeout(closeSidebar, 250);
    }
  });
}

/* ── Duplicate ticker content to make loop seamless ─────────────── */
const ticker = document.querySelector('.ticker');
if (ticker) {
  ticker.innerHTML += ticker.innerHTML;
}

/* ── Tab switching ───────────────────────────────────────────────── */
const tabBtns = document.querySelectorAll('.tab-btn');
tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    tabBtns.forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'favorites') renderFavoritesTab();
  });
});

/* ── Favorites (localStorage) ────────────────────────────────────── */
const FAV_KEY = 'gnews_favorites';

function getFavs() {
  try { return JSON.parse(localStorage.getItem(FAV_KEY) || '{}'); } catch { return {}; }
}
function saveFavs(favs) { localStorage.setItem(FAV_KEY, JSON.stringify(favs)); }

function favId(url, headline) {
  const raw = (url || headline || '').trim();
  // Simple deterministic key from the URL/headline
  let h = 0;
  for (let i = 0; i < raw.length; i++) { h = (Math.imul(31, h) + raw.charCodeAt(i)) | 0; }
  return 'f' + Math.abs(h).toString(36);
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function syncFavBtn(btn, faved) {
  btn.textContent = faved ? '★' : '☆';
  btn.classList.toggle('faved', faved);
  btn.setAttribute('title', faved ? 'Remove from favorites' : 'Save to favorites');
}

function initFavBtns() {
  document.querySelectorAll('.fav-btn').forEach(btn => {
    const el = btn.closest('[data-headline]');
    if (!el) return;
    const id = favId(el.dataset.url, el.dataset.headline);
    syncFavBtn(btn, !!getFavs()[id]);

    btn.addEventListener('click', e => {
      e.preventDefault();
      e.stopPropagation();
      const favs = getFavs();
      if (favs[id]) {
        delete favs[id];
        saveFavs(favs);
        syncFavBtn(btn, false);
      } else {
        favs[id] = {
          headline:      el.dataset.headline || '',
          url:           el.dataset.url      || '',
          source:        el.dataset.source   || '',
          category:      el.dataset.cat      || '',
          country_key:   el.dataset.region   || '',
          country_label: el.dataset.label    || '',
          country_flag:  el.dataset.flag     || '',
          savedAt:       new Date().toISOString(),
        };
        saveFavs(favs);
        syncFavBtn(btn, true);
      }
      // Re-render tab if visible
      const favPane = document.getElementById('tab-favorites');
      if (favPane && favPane.classList.contains('active')) renderFavoritesTab();
    });
  });
}

function renderFavoritesTab() {
  const container = document.getElementById('tab-favorites');
  if (!container) return;

  const entries = Object.entries(getFavs());
  if (entries.length === 0) {
    container.innerHTML = '<p class="fav-empty">No favorites saved yet.<br>Click ☆ on any headline to save it here.</p>';
    return;
  }

  // Group by country
  const byCountry = {};
  entries.forEach(([id, f]) => {
    const k = f.country_key || '_';
    if (!byCountry[k]) byCountry[k] = { label: f.country_label || k, flag: f.country_flag || '', items: [] };
    byCountry[k].items.push({ id, ...f });
  });

  let html = '<section class="section"><h2 class="section-title">⭐ Saved Favorites</h2><div class="fav-groups">';
  Object.values(byCountry)
    .sort((a, b) => a.label.localeCompare(b.label))
    .forEach(group => {
      html += `<div class="fav-group">`;
      html += `<h3 class="fav-group-title">${escHtml(group.flag)} ${escHtml(group.label)}</h3>`;
      html += `<ul class="fav-list">`;
      group.items
        .sort((a, b) => b.savedAt.localeCompare(a.savedAt))
        .forEach(item => {
          html += `<li class="fav-item">`;
          html += `<div class="fav-item-main">`;
          if (item.url) {
            html += `<a href="${escHtml(item.url)}" target="_blank" rel="noopener" class="fav-headline">${escHtml(item.headline)}</a>`;
          } else {
            html += `<span class="fav-headline">${escHtml(item.headline)}</span>`;
          }
          if (item.source) html += `<span class="fav-source">${escHtml(item.source)}</span>`;
          html += `</div>`;
          html += `<button class="fav-remove" data-id="${escHtml(item.id)}" title="Remove">✕</button>`;
          html += `</li>`;
        });
      html += `</ul></div>`;
    });
  html += '</div></section>';
  container.innerHTML = html;

  container.querySelectorAll('.fav-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.id;
      const favs = getFavs();
      delete favs[id];
      saveFavs(favs);
      // Sync any matching fav-btn on the page
      document.querySelectorAll('.fav-btn').forEach(fb => {
        const el = fb.closest('[data-headline]');
        if (!el) return;
        if (favId(el.dataset.url, el.dataset.headline) === id) syncFavBtn(fb, false);
      });
      renderFavoritesTab();
    });
  });
}

initFavBtns();


/* ── Deep links: #tab-<name> opens that tab (e.g. old /social-pulse links) ── */
(function () {
  const m = location.hash.match(/^#tab-([a-z]+)$/);
  const btn = m && document.querySelector('.tab-btn[data-tab="' + m[1] + '"]');
  if (btn) btn.click();
})();

/* ── Social Pulse: topic filter and AI search ───────────────────── */
document.querySelectorAll('.sp-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.sp-chip').forEach(c => c.classList.toggle('active', c === chip));
    const t = chip.dataset.topic;
    document.querySelectorAll('.sp-post').forEach(p => p.classList.toggle('hidden', t !== 'all' && p.dataset.topic !== t));
  });
});

(function () {
  const form = document.getElementById('sp-search-form');
  if (!form) return;
  const box = document.getElementById('sp-answer');
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const q = document.getElementById('sp-q').value.trim();
    const endpoint = form.dataset.endpoint;
    if (!q || !endpoint) return;
    const btn = form.querySelector('button');
    btn.disabled = true; btn.textContent = 'Thinking…';
    box.hidden = false; box.innerHTML = '<p>Searching today\'s posts…</p>';
    try {
      const r = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q }) });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Search failed');
      let html = '<p>' + escHtml(data.answer).replace(/\[(\d+)\]/g, '<sup>[$1]</sup>') + '</p>';
      if (data.sources && data.sources.length) {
        html += '<ol>' + data.sources.map(s => '<li><a href="' + escHtml(s.url || '#') + '" target="_blank" rel="noopener">' + escHtml(s.title) + '</a></li>').join('') + '</ol>';
      }
      box.innerHTML = html;
    } catch (err) {
      box.innerHTML = '<p class="sp-error">' + escHtml(err.message || 'Search is temporarily unavailable.') + '</p>';
    } finally {
      btn.disabled = false; btn.textContent = 'Ask';
    }
  });
})();

/* ── AI News tab: month picker for the papers digest ───────────────────────
   The latest month is rendered server-side; older months load from data/ai_news_papers_*.json. */
(function () {
  const select = document.getElementById('ai-month-select');
  const list = document.getElementById('ai-papers-list');
  const title = document.getElementById('ai-papers-title');
  if (!select || !list || !title) return;
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  select.addEventListener('change', () => {
    fetch(select.value, { cache: 'no-store' }).then(r => r.json()).then(d => {
      title.textContent = `📄 Top ${d.papers.length} cited papers — ${d.month_label}`;
      list.innerHTML = d.papers.length ? d.papers.map((p, i) => `
        <article class="rank-card">
          <div class="rank-num">${i + 1}</div>
          <div class="rank-body">
            <div class="rank-header">
              <span class="rank-cat">${esc(p.venue || 'Preprint')} &middot; ${esc(p.publication_date)}</span>
              <span class="severity-badge">${p.citation_count} citations</span>
            </div>
            <h3 class="rank-title"><a class="headline-link" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a></h3>
            <p class="rank-summary">${esc(p.plain_summary)}</p>
            ${p.key_contribution ? `<p class="rank-summary"><strong>Key contribution:</strong> ${esc(p.key_contribution)}</p>` : ''}
            ${p.authors && p.authors.length ? `<p class="ai-authors">${esc(p.authors.join(', '))}${p.authors.length === 5 ? ' et al.' : ''}</p>` : ''}
          </div>
        </article>`).join('') : '<p class="empty-state">No papers found for this month yet.</p>';
    }).catch(() => { list.innerHTML = '<p class="empty-state">Could not load that month.</p>'; });
  });
})();
