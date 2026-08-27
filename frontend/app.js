const COLORS = { Low: '#22c55e', Moderate: '#eab308', High: '#f97316', Critical: '#ef4444' };
let map, markers = {}, selected = null, latest = [];

/* ---------- tabs ---------- */
document.querySelectorAll('.tab').forEach(t => t.onclick = () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.view').forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  document.getElementById(t.dataset.view).classList.add('active');
  if (t.dataset.view === 'dashboard' && map) setTimeout(() => map.invalidateSize(), 60);
  if (t.dataset.view === 'alerts') loadAlerts();
  if (t.dataset.view === 'model') loadModel();
});

const clock = () => document.getElementById('clock').textContent =
  new Date().toLocaleTimeString('en-IN', { hour12: false });
setInterval(clock, 1000); clock();

/* ---------- map ---------- */
function initMap() {
  map = L.map('map', { zoomControl: true }).setView([25.8, 92.3], 6);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO', maxZoom: 18
  }).addTo(map);
}

function updateMap(sites) {
  sites.forEach(s => {
    const r = 8 + s.risk_score / 8;
    if (markers[s.id]) {
      markers[s.id].setStyle({ fillColor: s.color, color: s.color }).setRadius(r);
      markers[s.id].getPopup().setContent(popup(s));
    } else {
      const m = L.circleMarker([s.lat, s.lon], {
        radius: r, fillColor: s.color, color: s.color, weight: 2, fillOpacity: .55
      }).addTo(map).bindPopup(popup(s));
      m.on('click', () => selectSite(s.id));
      markers[s.id] = m;
    }
  });
}
const popup = s => `<b style="font-size:13px">${s.name}</b><br>
  <span style="color:#8fa3c4">${s.state}</span><br>
  <span style="color:${s.color};font-weight:700">${s.level} · ${s.risk_score}</span><br>
  <span style="font-size:11px">Rain 24h ${s.telemetry.rain_24h} mm · Disp ${s.telemetry.displacement_rate} mm/d</span>`;

/* ---------- dashboard ---------- */
async function tick() {
  try {
    const [sites, sum] = await Promise.all([
      fetch('/api/sites').then(r => r.json()),
      fetch('/api/summary').then(r => r.json())
    ]);
    latest = sites;
    renderStats(sum); updateMap(sites); renderList(sites);
    if (selected) renderDetail(selected);
    if (document.getElementById('alerts').classList.contains('active')) loadAlerts();
  } catch (e) { console.error(e); }
}

function renderStats(s) {
  const c = s.counts;
  const items = [
    ['Monitored Slopes', s.total_sites, 'across 8 NER states', '#38bdf8'],
    ['Active Alerts', s.active_alerts, 'High + Critical', s.active_alerts ? '#ef4444' : '#22c55e'],
    ['Average Risk', s.avg_risk, 'network-wide index', '#a78bfa'],
    ['Critical', c.Critical, 'evacuation advised', '#ef4444'],
    ['High', c.High, 'public warning', '#f97316'],
    ['Moderate', c.Moderate, 'heightened watch', '#eab308'],
    ['Low', c.Low, 'routine monitoring', '#22c55e'],
  ];
  document.getElementById('stats').innerHTML = items.map(([k, v, sub, col]) =>
    `<div class="stat" style="border-left-color:${col}">
      <div class="k">${k}</div><div class="v" style="color:${col}">${v}</div><div class="s">${sub}</div>
    </div>`).join('');
}

function renderList(sites) {
  const sorted = [...sites].sort((a, b) => b.risk_score - a.risk_score);
  document.getElementById('siteList').innerHTML = sorted.map(s => `
    <div class="site" style="border-left-color:${s.color}" onclick="selectSite('${s.id}')">
      <div><div class="nm">${s.name}</div><div class="st">${s.state} · ${s.id}</div></div>
      <div style="display:flex;align-items:center;gap:10px">
        <span class="badge" style="background:${s.color}22;color:${s.color}">${s.level}</span>
        <div class="score" style="color:${s.color}">${s.risk_score}<small>risk</small></div>
      </div>
    </div>`).join('');
}

window.selectSite = async (id) => {
  selected = id;
  renderDetail(id);
  document.getElementById('detailCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
};

async function renderDetail(id) {
  const d = await fetch('/api/site/' + id).then(r => r.json());
  const t = d.telemetry;
  document.getElementById('detailCard').style.display = 'block';
  document.getElementById('detailTitle').innerHTML =
    `${d.name}, ${d.state} — <span style="color:${d.color}">${d.level} (${d.risk_score})</span>
     <small style="color:var(--mut);font-weight:500"> confidence ${(d.confidence * 100).toFixed(1)}%</small>`;

  const met = [
    ['Rain 1h', t.rain_1h + ' mm'], ['Rain 24h', t.rain_24h + ' mm'], ['Rain 72h', t.rain_72h + ' mm'],
    ['API 14d', t.api_14d + ' mm'], ['Soil Moisture', t.soil_moisture + ' %'],
    ['Pore Pressure', t.pore_pressure + ' kPa'], ['Ground Tilt', t.ground_tilt + ' °'],
    ['Displacement', t.displacement_rate + ' mm/d'], ['Slope', t.slope + ' °'],
    ['NDVI', t.ndvi], ['Rock Strength', t.rock_strength + '/10'], ['Seismic Zone', t.seismic_zone],
  ];
  document.getElementById('detailBody').innerHTML = `
    <div class="detail-grid">${met.map(([k, v]) =>
      `<div class="metric"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('')}</div>
    <h3 class="sub">Forecast Outlook</h3>
    <div class="fc-row">${d.forecast.map(f =>
      `<div class="fc"><div class="h">+${f.horizon_h}h</div>
       <div class="l" style="color:${COLORS[f.level]}">${f.level}</div>
       <div class="h">${f.risk_score}</div></div>`).join('')}</div>
    <h3 class="sub">Contributing Factors (Explainability)</h3>
    <div class="factors">${d.factors.map(f =>
      `<div class="factor ${f.severity}"><span>${f.factor}</span><span>${f.value}</span></div>`).join('')}</div>
    <h3 class="sub">Risk Trend</h3>${spark(d.history)}
    <div class="action">📢 Recommended Action: ${d.action}</div>`;
}

function spark(h) {
  if (!h || h.length < 2) return '<div class="empty">collecting trend data…</div>';
  const w = 800, ht = 70, pts = h.slice(-60);
  const max = Math.max(100, ...pts.map(p => p.risk_score));
  const d = pts.map((p, i) =>
    `${(i / (pts.length - 1)) * w},${ht - (p.risk_score / max) * (ht - 6) - 3}`).join(' ');
  return `<svg class="spark" viewBox="0 0 ${w} ${ht}" preserveAspectRatio="none">
    <polyline points="${d}" fill="none" stroke="#38bdf8" stroke-width="2.5"/>
    <polyline points="0,${ht} ${d} ${w},${ht}" fill="#38bdf822" stroke="none"/></svg>`;
}

/* ---------- alerts ---------- */
async function loadAlerts() {
  const a = await fetch('/api/alerts').then(r => r.json());
  const el = document.getElementById('alertList');
  if (!a.length) { el.innerHTML = '<div class="empty">No escalation alerts yet. The system dispatches automatically when a slope escalates to High or Critical.</div>'; return; }
  el.innerHTML = a.map(x => `
    <div class="alert" style="border-left-color:${COLORS[x.level]}">
      <div class="hd">
        <span class="badge" style="background:${COLORS[x.level]}22;color:${COLORS[x.level]}">${x.level}</span>
        <b style="font-size:13px">${x.site}, ${x.state}</b>
        <span class="tm">${new Date(x.timestamp * 1000).toLocaleTimeString('en-IN', { hour12: false })}</span>
      </div>
      <div class="ms">${x.message}</div>
      <div class="tm" style="margin-top:5px">Escalated ${x.from_level} → ${x.level} · risk index ${x.risk_score}</div>
    </div>`).join('');
}

/* ---------- simulator ---------- */
const SIM = [
  ['rain_1h', 'Rainfall last 1h (mm)', 0, 80, 12, 1],
  ['rain_24h', 'Rainfall last 24h (mm)', 0, 400, 90, 1],
  ['rain_72h', 'Rainfall last 72h (mm)', 0, 800, 180, 1],
  ['api_14d', 'Antecedent Precip Index 14d (mm)', 0, 900, 220, 1],
  ['soil_moisture', 'Soil moisture (%)', 5, 100, 55, 1],
  ['pore_pressure', 'Pore-water pressure (kPa)', 0, 140, 55, 1],
  ['ground_tilt', 'Ground tilt (°)', 0, 6, 0.6, 0.05],
  ['displacement_rate', 'Displacement rate (mm/day)', 0, 20, 1.5, 0.1],
  ['slope', 'Slope angle (°)', 5, 60, 35, 1],
  ['soil_depth', 'Soil depth (m)', 0.5, 6.5, 3.4, 0.1],
  ['rock_strength', 'Rock strength (1-10)', 1, 9, 4.2, 0.1],
  ['ndvi', 'Vegetation index NDVI', 0.05, 0.95, 0.58, 0.01],
  ['drainage', 'Drainage density (km/km²)', 0.5, 4.5, 2.5, 0.1],
  ['road_cut', 'Road-cut density index', 0, 1, 0.7, 0.05],
  ['seismic_zone', 'Seismic zone', 2, 5, 5, 1],
];
const PRESETS = {
  monsoon: { rain_1h: 45, rain_24h: 310, rain_72h: 620, api_14d: 700, soil_moisture: 92, pore_pressure: 115, ground_tilt: 2.4, displacement_rate: 7.5 },
  dry: { rain_1h: 0, rain_24h: 3, rain_72h: 9, api_14d: 25, soil_moisture: 18, pore_pressure: 20, ground_tilt: 0.1, displacement_rate: 0.1 },
  quake: { rain_1h: 20, rain_24h: 140, rain_72h: 300, api_14d: 400, soil_moisture: 74, pore_pressure: 90, ground_tilt: 3.6, displacement_rate: 11, seismic_zone: 5, rock_strength: 2.5 },
};

function buildSliders() {
  document.getElementById('sliders').innerHTML = SIM.map(([k, l, mn, mx, dv, st]) =>
    `<div class="slider"><label for="s_${k}">${l}<b id="v_${k}">${dv}</b></label>
     <input type="range" id="s_${k}" min="${mn}" max="${mx}" step="${st}" value="${dv}"></div>`).join('');
  SIM.forEach(([k]) => document.getElementById('s_' + k).oninput = e => {
    document.getElementById('v_' + k).textContent = e.target.value; runSim();
  });
  document.querySelectorAll('[data-preset]').forEach(b => b.onclick = () => {
    const p = PRESETS[b.dataset.preset];
    Object.entries(p).forEach(([k, v]) => {
      const el = document.getElementById('s_' + k);
      if (el) { el.value = v; document.getElementById('v_' + k).textContent = v; }
    });
    runSim();
  });
}

let simTimer;
function runSim() { clearTimeout(simTimer); simTimer = setTimeout(doSim, 130); }
async function doSim() {
  const body = {};
  SIM.forEach(([k]) => body[k] = parseFloat(document.getElementById('s_' + k).value));
  const r = await fetch('/api/predict', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  }).then(x => x.json());
  document.getElementById('simResult').innerHTML = `
    <div class="ring" style="color:${r.color}">${r.risk_score}<small>${r.level} Risk</small></div>
    <div class="bars">${Object.entries(r.probabilities).map(([k, v]) =>
      `<div class="bar"><div class="t"><span>${k}</span><span>${(v * 100).toFixed(1)}%</span></div>
       <div class="tr"><div class="fl" style="width:${v * 100}%;background:${COLORS[k]}"></div></div></div>`).join('')}
    </div>
    <h3 class="sub">Forecast</h3>
    <div class="fc-row">${r.forecast.map(f =>
      `<div class="fc"><div class="h">+${f.horizon_h}h</div>
       <div class="l" style="color:${COLORS[f.level]}">${f.level}</div><div class="h">${f.risk_score}</div></div>`).join('')}</div>
    <h3 class="sub">Contributing Factors</h3>
    <div class="factors">${r.factors.map(f =>
      `<div class="factor ${f.severity}"><span>${f.factor}</span><span>${f.value}</span></div>`).join('')}</div>
    <div class="action">📢 ${r.action}</div>`;
}

/* ---------- model ---------- */
async function loadModel() {
  const m = await fetch('/api/metrics').then(r => r.json());
  document.getElementById('perf').innerHTML = `
    <div class="detail-grid">
      <div class="metric"><div class="k">Accuracy</div><div class="v">${(m.accuracy * 100).toFixed(1)}%</div></div>
      <div class="metric"><div class="k">ROC-AUC (OvR)</div><div class="v">${m.roc_auc_ovr}</div></div>
      <div class="metric"><div class="k">5-Fold CV</div><div class="v">${(m.cv_accuracy_mean * 100).toFixed(1)}%</div></div>
      <div class="metric"><div class="k">Train / Test</div><div class="v">${m.n_train} / ${m.n_test}</div></div>
    </div>
    <p style="font-size:12.5px;color:var(--mut);margin-top:10px;line-height:1.6">
      Algorithm: <b style="color:var(--tx)">${m.algorithm}</b> — a gradient-boosted decision-tree ensemble
      trained on 15 hydro-meteorological, geotechnical and terrain features to classify slope risk into
      four operational levels.</p>`;
  const mx = Math.max(...m.feature_importance.map(f => f.importance));
  document.getElementById('fimp').innerHTML = `<div class="bars">${m.feature_importance.map(f =>
    `<div class="bar"><div class="t"><span>${f.feature}</span><span>${f.importance.toFixed(4)}</span></div>
     <div class="tr"><div class="fl" style="width:${(f.importance / mx) * 100}%;background:#38bdf8"></div></div></div>`).join('')}</div>`;
  document.getElementById('cmat').innerHTML = `<table class="cm"><tr><th>Actual \\ Predicted</th>${m.labels.map(l => `<th style="text-align:center">${l}</th>`).join('')}</tr>
    ${m.confusion_matrix.map((row, i) => `<tr><th>${m.labels[i]}</th>${row.map((v, j) =>
      `<td style="background:rgba(56,189,248,${(v / Math.max(...row)) * 0.45});font-weight:${i === j ? 700 : 400}">${v}</td>`).join('')}</tr>`).join('')}</table>`;
}

/* ---------- boot ---------- */
initMap(); buildSliders(); runSim(); tick();
setInterval(tick, 4000);
