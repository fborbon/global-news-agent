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

/* ── Duplicate ticker content to make loop seamless ─────────────── */
const ticker = document.querySelector('.ticker');
if (ticker) {
  ticker.innerHTML += ticker.innerHTML;
}
