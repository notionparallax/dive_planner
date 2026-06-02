'use strict';

const form      = document.getElementById('plan-form');
const submitBtn = document.getElementById('submit-btn');
const optimiseBtn = document.getElementById('optimise-btn');
const fullOptBtn = document.getElementById('full-opt-btn');
const loading   = document.getElementById('loading');
const loadingMsg = document.getElementById('loading-msg');
const errorBox  = document.getElementById('error-box');
const results   = document.getElementById('results');
const optResults = document.getElementById('opt-results');
const fullOptResults = document.getElementById('full-opt-results');

let profileChart = null;
let optProfileChart = null;
let fullOptProfileChart = null;

// ── Tab switching ────────────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    // Hide results when switching tabs
    results.classList.add('hidden');
    optResults.classList.add('hidden');
    fullOptResults.classList.add('hidden');
    errorBox.classList.add('hidden');
    // Show/hide plan-only rows
    const isPlan = btn.dataset.tab === 'plan';
    document.querySelectorAll('.plan-only').forEach(el => {
      el.style.display = isPlan ? '' : 'none';
    });
  });
});

// ── Gas enable/disable toggles ───────────────────────────────────────────────

function setupGasToggle(checkboxId, fieldsetId) {
  const cb = document.getElementById(checkboxId);
  const fs = document.getElementById(fieldsetId);
  function update() {
    const enabled = cb.checked;
    fs.classList.toggle('gas-disabled', !enabled);
    fs.querySelectorAll('input:not([type=checkbox]), select').forEach(el => {
      el.disabled = !enabled;
    });
  }
  cb.addEventListener('change', update);
  update();
}

setupGasToggle('deco1_enabled', 'fs-deco1');
setupGasToggle('deco2_enabled', 'fs-deco2');

// ── END target helper ────────────────────────────────────────────────────────

function updateEndHelper() {
  const endInput = document.getElementById('full_end_target');
  const depthInput = document.getElementById('depth');
  const heInput   = document.getElementById('back_gas_he');
  const o2Input   = document.getElementById('back_gas_o2');
  const preview   = document.getElementById('full-backgas-preview');
  const maxPpo2Input = document.getElementById('max_ppo2_bottom');

  if (!endInput || !endInput.value) {
    if (preview) preview.textContent = '—';
    return;
  }
  const end   = parseFloat(endInput.value);
  const depth = parseFloat(depthInput.value) || 45;
  const maxPpo2 = parseFloat(maxPpo2Input.value) || 1.4;
  const absPressure = depth / 10 + 1;

  const heFrac = 1 - (end + 10) / (depth + 10);
  const hePct  = Math.max(0, Math.round(heFrac * 100 / 5) * 5);
  const o2Pct  = Math.min(40, Math.floor(maxPpo2 / absPressure * 100));

  heInput.value = hePct;
  o2Input.value = o2Pct;
  if (preview) preview.textContent = hePct > 0 ? `Tx ${o2Pct}/${hePct}` : `EAN${o2Pct}`;
}

document.addEventListener('DOMContentLoaded', () => {
  const endInput = document.getElementById('full_end_target');
  const depthInput = document.getElementById('depth');
  if (endInput) endInput.addEventListener('input', updateEndHelper);
  if (depthInput) depthInput.addEventListener('input', updateEndHelper);
});

// ── Plan submit ──────────────────────────────────────────────────────────────

async function submitPlan() {
  setLoading(true, 'Calculating decompression…');
  clearResults();

  const body = buildRequest();

  try {
    const resp = await fetch('/api/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`Server error ${resp.status}: ${txt}`);
    }
    const data = await resp.json();
    renderResults(data);
  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
}

// ── Optimise submit ──────────────────────────────────────────────────────────

async function submitOptimise() {
  setLoading(true, 'Optimising… this may take ~10 seconds');
  clearResults();

  const body = buildOptimiseRequest();

  try {
    const resp = await fetch('/api/optimise/bottom-time', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`Server error ${resp.status}: ${txt}`);
    }
    const data = await resp.json();
    renderOptResults(data);
  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
}

// ── Build request from form ──────────────────────────────────────────────────

function buildRequest() {
  const f = form;
  const get  = id => f.querySelector(`#${id}`);
  const num  = id => { const v = parseFloat(get(id).value); return isNaN(v) ? null : v; };
  const int  = id => { const v = parseInt(get(id).value, 10); return isNaN(v) ? null : v; };
  const bool = id => get(id).checked;

  const decoGasesLostRaw = get('deco_gases_lost').value;
  const decoGasesLost = decoGasesLostRaw === 'true'  ? true
                      : decoGasesLostRaw === 'false' ? false
                      : decoGasesLostRaw;

  const d1Switch = get('deco1_switch_depth_m').value;
  const d2Switch = get('deco2_switch_depth_m').value;

  return {
    depth:                num('depth'),
    bottom_time:          num('bottom_time'),
    gf_low:               num('gf_low') / 100,
    gf_high:              num('gf_high') / 100,
    dive_mode:            get('dive_mode').value,
    back_gas_o2:          int('back_gas_o2'),
    back_gas_he:          int('back_gas_he'),
    back_gas_volume_l:    num('back_gas_volume_l'),
    back_gas_fill_bar:    int('back_gas_fill_bar'),
    deco1_enabled:        bool('deco1_enabled'),
    deco1_o2:             int('deco1_o2'),
    deco1_he:             int('deco1_he'),
    deco1_volume_l:       num('deco1_volume_l'),
    deco1_fill_bar:       int('deco1_fill_bar'),
    deco1_switch_depth_m: d1Switch ? parseFloat(d1Switch) : null,
    deco2_enabled:        bool('deco2_enabled'),
    deco2_o2:             int('deco2_o2'),
    deco2_he:             int('deco2_he'),
    deco2_volume_l:       num('deco2_volume_l'),
    deco2_fill_bar:       int('deco2_fill_bar'),
    deco2_switch_depth_m: d2Switch ? parseFloat(d2Switch) : null,
    sac_bottom:           num('sac_bottom'),
    sac_deco:             num('sac_deco'),
    sac_emergency:        num('sac_emergency'),
    contingency:          num('contingency'),
    practical_empty_bar:  num('practical_empty_bar'),
    max_ppo2_bottom:      num('max_ppo2_bottom'),
    max_ppo2_deco:        num('max_ppo2_deco'),
    deco_gases_lost:      decoGasesLost,
  };
}

function buildOptimiseRequest() {
  const f = form;
  const get  = id => f.querySelector(`#${id}`);
  const num  = id => { const v = parseFloat(get(id).value); return isNaN(v) ? null : v; };
  const int  = id => { const v = parseInt(get(id).value, 10); return isNaN(v) ? null : v; };
  const bool = id => get(id).checked;

  const d1Switch = get('deco1_switch_depth_m').value;
  const d2Switch = get('deco2_switch_depth_m').value;
  const maxRtRaw = get('max_runtime').value;

  return {
    depth:                num('depth'),
    gf_low:               num('gf_low') / 100,
    gf_high:              num('gf_high') / 100,
    dive_mode:            get('dive_mode').value,
    back_gas_o2:          int('back_gas_o2'),
    back_gas_he:          int('back_gas_he'),
    back_gas_volume_l:    num('back_gas_volume_l'),
    back_gas_fill_bar:    int('back_gas_fill_bar'),
    deco1_enabled:        bool('deco1_enabled'),
    deco1_o2:             int('deco1_o2'),
    deco1_he:             int('deco1_he'),
    deco1_volume_l:       num('deco1_volume_l'),
    deco1_fill_bar:       int('deco1_fill_bar'),
    deco1_switch_depth_m: d1Switch ? parseFloat(d1Switch) : null,
    deco2_enabled:        bool('deco2_enabled'),
    deco2_o2:             int('deco2_o2'),
    deco2_he:             int('deco2_he'),
    deco2_volume_l:       num('deco2_volume_l'),
    deco2_fill_bar:       int('deco2_fill_bar'),
    deco2_switch_depth_m: d2Switch ? parseFloat(d2Switch) : null,
    sac_bottom:           num('sac_bottom'),
    sac_deco:             num('sac_deco'),
    sac_emergency:        num('sac_emergency'),
    contingency:          num('contingency'),
    practical_empty_bar:  num('practical_empty_bar'),
    max_ppo2_bottom:      num('max_ppo2_bottom'),
    max_ppo2_deco:        num('max_ppo2_deco'),
    max_cns:              num('max_cns'),
    max_otu:              num('max_otu'),
    max_runtime:          maxRtRaw ? parseFloat(maxRtRaw) : null,
    min_bottom_time:      int('min_bottom_time'),
    max_bottom_time:      int('max_bottom_time'),
  };
}

// ── Render plan results ──────────────────────────────────────────────────────

function renderResults(d) {
  renderSummary(d);
  renderToxicity(d);
  renderDecoSchedule(d, 'profile-chart', 'deco-content');
  renderGasUsage(d, 'gas-content');
  renderGasPlan(d, 'mingas-content');
  results.classList.remove('hidden');
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Render optimiser results ─────────────────────────────────────────────────

function renderOptResults(data) {
  document.getElementById('opt-max-bt').textContent =
    data.feasible ? data.max_bottom_time : '0';

  const bindingHeader = document.getElementById('opt-binding-header');
  const bindingEl = document.getElementById('opt-binding');
  if (data.binding_constraints && data.binding_constraints.length > 0) {
    bindingHeader.textContent =
      `Adding 1 more minute of bottom time (${data.max_bottom_time + 1} min) would violate:`;
    bindingEl.innerHTML = data.binding_constraints
      .map(c => `<li>${c}</li>`).join('');
  } else {
    bindingHeader.textContent = data.feasible
      ? 'Search limit reached — no constraint violated within the search range.'
      : '';
    bindingEl.innerHTML = '';
  }

  document.getElementById('opt-steps').textContent =
    `${data.steps_checked} deco calculation${data.steps_checked !== 1 ? 's' : ''} performed`;

  const sc = data.scenario;
  if (sc) {
    // Attach gas_plan and dive_mode to scenario for render functions
    sc.gas_plan  = data.gas_plan;
    sc.dive_mode = data.dive_mode;
    sc.gf_low    = data.gf_low;
    sc.gf_high   = data.gf_high;

    renderSummaryInto(sc, 'opt-summary-content');
    renderToxicityInto(sc, 'opt-toxicity-content');
    renderDecoSchedule(sc, 'opt-profile-chart', 'opt-deco-content');
    renderGasUsage(sc, 'opt-gas-content');
    renderGasPlan(sc, 'opt-mingas-content');
  }

  optResults.classList.remove('hidden');
  optResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderSummary(d) { renderSummaryInto(d, 'summary-content'); }

function renderSummaryInto(d, elId) {
  const el = document.getElementById(elId);
  const modeLabel = d.dive_mode === 'cave' ? 'Cave' : 'Open Water';
  el.innerHTML = `
    <div class="kv-grid">
      <div class="kv"><span class="kv-label">Depth</span><span class="kv-value">${d.depth} m</span></div>
      <div class="kv"><span class="kv-label">Bottom Time</span><span class="kv-value">${d.bottom_time} min</span></div>
      <div class="kv"><span class="kv-label">Total Deco</span><span class="kv-value">${fmt1(d.total_deco)} min</span></div>
      <div class="kv"><span class="kv-label">Total Runtime</span><span class="kv-value">${fmt1(d.total_time)} min</span></div>
      <div class="kv"><span class="kv-label">Mode</span><span class="kv-value">${modeLabel}</span></div>
      <div class="kv"><span class="kv-label">GF</span><span class="kv-value">${pct(d.gf_low ?? 0.50)}/${pct(d.gf_high ?? 0.70)}</span></div>
    </div>`;
}

function renderToxicity(d) { renderToxicityInto(d, 'toxicity-content'); }

function renderToxicityInto(d, elId) {
  const el = document.getElementById(elId);
  const cnsBadge = badge(d.cns < 50 ? 'ok' : d.cns < 80 ? 'warn' : 'bad', `CNS ${fmt1(d.cns)}%`);
  const otuBadge = badge(d.otu < 200 ? 'ok' : d.otu < 300 ? 'warn' : 'bad', `OTU ${fmt1(d.otu)}`);
  el.innerHTML = `
    <div style="display:flex;gap:1rem;flex-wrap:wrap">
      ${cnsBadge}
      ${otuBadge}
    </div>
    <p class="text-muted" style="font-size:0.8rem;margin-top:0.8rem">
      CNS limit 80% per dive · OTU limit 300 per day
    </p>`;
}

function gasColorForCyl(cyl) {
  if (!cyl) return '#ffffff';
  const o2 = cyl.gas ? cyl.gas.o2 : 21;
  const he = cyl.gas ? cyl.gas.he : 0;
  if (he > 0)      return '#ff6b6b';   // trimix: red
  if (o2 === 100)  return '#51cf66';   // O₂: green
  if (o2 > 21)     return '#ffd43b';   // nitrox: yellow
  return '#ffffff';                    // air/back-gas default: white
}

function classifyGasKey(t, depth, d) {
  const sd1 = d.switch_depths && d.switch_depths.deco1;
  const sd2 = d.switch_depths && d.switch_depths.deco2;
  if (!d.bottom_time || t <= d.bottom_time) return 'back';
  if (sd2 && depth <= sd2) return 'deco2';
  if (sd1 && depth <= sd1) return 'deco1';
  return 'back';
}

function renderDecoSchedule(d, chartId, tableId) {
  const tableEl = document.getElementById(tableId);
  const sched   = d.deco_schedule || [];
  const switchDepths = d.switch_depths || {};

  const times  = d.times  || [];
  const depths = d.depths || [];

  if (chartId === 'profile-chart') {
    if (profileChart) { profileChart.destroy(); profileChart = null; }
  } else if (chartId === 'opt-profile-chart') {
    if (optProfileChart) { optProfileChart.destroy(); optProfileChart = null; }
  } else {
    if (fullOptProfileChart) { fullOptProfileChart.destroy(); fullOptProfileChart = null; }
  }

  if (times.length > 1) {
    const ctx = document.getElementById(chartId).getContext('2d');
    const totalTime = times[times.length - 1];
    const xMax = Math.ceil(Math.max(totalTime, 10) / 10) * 10;

    // Build cylinder lookup: key → cylinder object
    const cyls = d.cylinders || [];
    const cylMap = {};
    cyls.forEach(c => {
      const name = (c.name || '').toLowerCase();
      if (name.includes('back'))       cylMap['back']  = c;
      else if (name.includes('deco 1') || name.includes('deco1')) cylMap['deco1'] = c;
      else if (name.includes('deco 2') || name.includes('deco2')) cylMap['deco2'] = c;
    });
    // Fall back: if only one deco gas, treat it as deco1
    if (!cylMap['deco1'] && !cylMap['deco2']) {
      const decoCyls = cyls.filter(c => !(c.name || '').toLowerCase().includes('back'));
      if (decoCyls.length >= 1) cylMap['deco1'] = decoCyls[0];
      if (decoCyls.length >= 2) cylMap['deco2'] = decoCyls[1];
    }

    // Classify each point
    const gasKeys = times.map((t, i) => classifyGasKey(t, depths[i], d));

    // Build runs of contiguous same-gas segments
    const runs = [];
    let i = 0;
    while (i < times.length) {
      const gas = gasKeys[i];
      let j = i + 1;
      while (j < times.length && gasKeys[j] === gas) j++;
      runs.push({ gas, start: i, end: j - 1 });
      i = j;
    }

    // One fill dataset (all points, light blue fill, transparent line)
    const fillDataset = {
      data: times.map((t, i) => ({ x: t, y: -depths[i] })),
      borderColor: 'transparent',
      backgroundColor: 'rgba(31,111,235,0.08)',
      borderWidth: 0,
      pointRadius: 0,
      fill: true,
      tension: 0.1,
      order: 10,
    };

    // One dataset per run (with 1 overlap point on each side for seamless joins)
    const segmentDatasets = runs.map(run => {
      const lo = Math.max(0, run.start - 1);
      const hi = Math.min(times.length - 1, run.end + 1);
      const data = times.map((t, idx) => {
        if (idx >= lo && idx <= hi) return { x: t, y: -depths[idx] };
        return null;
      });
      const color = gasColorForCyl(cylMap[run.gas]);
      return {
        data,
        borderColor: color,
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        fill: false,
        tension: 0.1,
        spanGaps: false,
        order: 1,
        gasKey: run.gas,
      };
    });

    const chart = new Chart(ctx, {
      type: 'line',
      data: { datasets: [fillDataset, ...segmentDatasets] },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 3,
        animation: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => `${Math.abs(ctx.parsed.y).toFixed(1)} m`,
              title: ctx => `${Math.round(ctx[0].parsed.x)} min`,
            },
          },
        },
        scales: {
          x: {
            type: 'linear',
            min: 0,
            max: xMax,
            title: { display: true, text: 'Time (min)', color: '#8b949e' },
            ticks: {
              color: '#8b949e',
              stepSize: xMax <= 40 ? 5 : xMax <= 80 ? 10 : 20,
              callback: v => Math.round(v),
            },
            grid: { color: 'rgba(48,54,61,0.6)' },
          },
          y: {
            title: { display: true, text: 'Depth (m)', color: '#8b949e' },
            ticks: { color: '#8b949e', callback: v => `${Math.abs(v)} m` },
            grid:  { color: 'rgba(48,54,61,0.6)' },
          },
        },
      },
    });

    if (chartId === 'profile-chart') profileChart = chart;
    else if (chartId === 'opt-profile-chart') optProfileChart = chart;
    else fullOptProfileChart = chart;

    // Gas legend
    const legendGases = [...new Set(runs.map(r => r.gas))];
    const legendItems = legendGases.map(key => {
      const cyl = cylMap[key];
      const color = gasColorForCyl(cyl);
      const label = cyl ? (cyl.name || key) : key;
      return `<span class="legend-item"><span class="legend-swatch" style="background:${color}"></span>${label}</span>`;
    }).join('');
    const chartEl = document.getElementById(chartId);
    let legendEl = chartEl.parentElement.querySelector('.chart-legend');
    if (!legendEl) {
      legendEl = document.createElement('div');
      legendEl.className = 'chart-legend';
      chartEl.parentElement.appendChild(legendEl);
    }
    legendEl.innerHTML = legendItems;
  }

  // Switch depth badges
  let switchInfo = '';
  if (switchDepths.deco1) switchInfo += `<span class="badge badge-ok">Deco 1 @ ${switchDepths.deco1} m</span> `;
  if (switchDepths.deco2) switchInfo += `<span class="badge badge-ok">Deco 2 @ ${switchDepths.deco2} m</span>`;

  if (sched.length === 0) {
    tableEl.innerHTML = '<p class="text-muted">No decompression stops required.</p>';
    return;
  }

  const rows = sched.map(s => `
    <tr>
      <td>${fmt1(s.depth)} m</td>
      <td class="num">${fmt1(s.stop_time)} min</td>
      <td class="num">${s.runtime != null ? fmt1(s.runtime) + ' min' : '—'}</td>
      <td class="gas-cell">${s.gas || '—'}</td>
    </tr>`).join('');

  tableEl.innerHTML = `
    ${switchInfo ? `<div style="margin-bottom:0.8rem">${switchInfo}</div>` : ''}
    <table>
      <thead><tr><th>Depth</th><th>Stop</th><th>Runtime</th><th>Gas</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderGasUsage(d, elId) {
  const el = document.getElementById(elId);
  const cyls = d.cylinders || [];
  if (cyls.length === 0) {
    el.innerHTML = '<p class="text-muted">No cylinder data.</p>';
    return;
  }

  const rows = cyls.map(c => {
    const remainCls = c.remaining_bar > 80 ? 'bar-ok' : c.remaining_bar > 40 ? 'bar-warn' : 'bar-bad';
    return `<tr>
      <td>${c.name}</td>
      <td>${c.gas.o2}/${c.gas.he}</td>
      <td class="num">${fmt0(c.fill_bar)} bar</td>
      <td class="num">${fmt0(c.used_bar)} bar</td>
      <td class="num ${remainCls}">${fmt0(c.remaining_bar)} bar</td>
    </tr>`;
  }).join('');

  el.innerHTML = `
    <table>
      <thead><tr><th>Cylinder</th><th>Gas</th><th>Fill</th><th>Used</th><th>Remaining</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderGasPlan(d, elId) {
  const el = document.getElementById(elId);
  const gp = d.gas_plan;
  if (!gp) { el.innerHTML = '<p class="text-muted">No gas plan data.</p>'; return; }

  let html = '';

  // Back gas
  const bg = gp.back_gas || {};
  html += `<h4 style="margin-bottom:0.6rem;color:var(--text-muted);font-size:0.85rem">${bg.name || 'Back Gas'}</h4>`;

  if (bg.cave_turn) {
    const ct = bg.cave_turn;
    html += minGasRow('Fill pressure', `${fmt0(ct.fill)} bar`);
    html += minGasRow('Practical empty', `${fmt0(ct.practical_empty)} bar`);
    html += minGasRow('Usable gas', `${fmt0(ct.usable)} bar`);
    html += minGasRow('Rounded usable (÷30)', `${fmt0(ct.rounded_usable)} bar`);
    html += minGasRow('One third', `${fmt0(ct.third)} bar`);
    html += minGasRow('Turn pressure', `${fmt0(ct.turn_pressure)} bar`, true);
  } else if (bg.ow_min_gas) {
    const mg = bg.ow_min_gas;
    const ok = mg.has_enough_gas;
    html += minGasRow('Min gas (2 divers)', `${fmt0(mg.min_litres)} L`);
    html += minGasRow('Practical empty', `${fmt0(mg.practical_empty)} bar`);
    html += minGasRow('Turn pressure required', `${fmt0(mg.turn_pressure_bar)} bar`);
    html += minGasRow('Bar at turn (actual)', `${fmt0(mg.bar_at_turn)} bar`);
    html += minGasRow('Status', ok
      ? '<span class="badge badge-ok">✓ Sufficient</span>'
      : '<span class="badge badge-bad">✗ Insufficient — reduce bottom time</span>');
  }

  // Deco gases
  const decoGases = gp.deco_gases || [];
  decoGases.forEach(dg => {
    html += `<h4 style="margin:1rem 0 0.6rem;color:var(--text-muted);font-size:0.85rem">${dg.name}</h4>`;
    html += minGasRow('Gas', `${dg.gas.o2}% O₂ / ${dg.gas.he}% He`);
    if (dg.switch_depth_m != null)
      html += minGasRow('Switch depth', `${dg.switch_depth_m} m`);
    if (dg.min_gas) {
      const mg = dg.min_gas;
      const ok = mg.sufficient;
      html += minGasRow('Practical empty', `${fmt0(mg.practical_empty)} bar`);
      html += minGasRow('Min gas needed', `${fmt0(mg.min_litres)} L / ${fmt0(mg.min_bar)} bar`);
      html += minGasRow('Available (usable)', `${fmt0(mg.available_litres)} L`);
      html += minGasRow('Status', ok
        ? '<span class="badge badge-ok">✓ Sufficient</span>'
        : '<span class="badge badge-bad">✗ Insufficient</span>');
    }
  });

  el.innerHTML = html;
}

// ── Utilities ────────────────────────────────────────────────────────────────

function minGasRow(label, value, highlight = false) {
  return `<div class="mingas-row">
    <span class="mingas-label">${label}</span>
    <span class="mingas-value${highlight ? ' text-green' : ''}">${value}</span>
  </div>`;
}

function badge(type, text) {
  return `<span class="badge badge-${type}">${text}</span>`;
}

function fmt0(n) { return n != null ? Math.round(n).toString() : '—'; }
function fmt1(n) { return n != null ? n.toFixed(1) : '—'; }
function pct(n)  { return n != null ? Math.round(n * 100).toString() : '—'; }

function setLoading(on, msg) {
  if (submitBtn) submitBtn.disabled = on;
  if (optimiseBtn) optimiseBtn.disabled = on;
  if (fullOptBtn) fullOptBtn.disabled = on;
  if (msg) loadingMsg.textContent = msg;
  loading.classList.toggle('hidden', !on);
}

function clearResults() {
  results.classList.add('hidden');
  optResults.classList.add('hidden');
  fullOptResults.classList.add('hidden');
  errorBox.classList.add('hidden');
  errorBox.textContent = '';
}

function showError(msg) {
  errorBox.textContent = `Error: ${msg}`;
  errorBox.classList.remove('hidden');
}

// ── Full optimise (mix optimiser) ────────────────────────────────────────────

function buildFullOptimiseRequest() {
  const f = form;
  const get  = id => f.querySelector(`#${id}`);
  const num  = id => { const v = parseFloat(get(id).value); return isNaN(v) ? null : v; };
  const int  = id => { const v = parseInt(get(id).value, 10); return isNaN(v) ? null : v; };

  const maxRtRaw = get('full_max_runtime').value;

  return {
    depth:                num('depth'),
    gf_low:               num('gf_low') / 100,
    gf_high:              num('gf_high') / 100,
    dive_mode:            get('dive_mode').value,
    back_gas_o2:          int('back_gas_o2'),
    back_gas_he:          int('back_gas_he'),
    back_gas_volume_l:    num('back_gas_volume_l'),
    back_gas_fill_bar:    int('back_gas_fill_bar'),
    deco1_volume_l:       num('deco1_volume_l'),
    deco1_fill_bar:       int('deco1_fill_bar'),
    deco1_o2_min:         int('deco1_o2_min'),
    deco1_o2_max:         int('deco1_o2_max'),
    deco2_volume_l:       num('deco2_volume_l'),
    deco2_fill_bar:       int('deco2_fill_bar'),
    deco2_o2_min:         int('deco2_o2_min'),
    deco2_o2_max:         int('deco2_o2_max'),
    sac_bottom:           num('sac_bottom'),
    sac_deco:             num('sac_deco'),
    sac_emergency:        num('sac_emergency'),
    contingency:          num('contingency'),
    practical_empty_bar:  num('practical_empty_bar'),
    max_ppo2_bottom:      num('max_ppo2_bottom'),
    max_ppo2_deco:        num('max_ppo2_deco'),
    max_cns:              num('full_max_cns'),
    max_otu:              num('full_max_otu'),
    max_runtime:          maxRtRaw ? parseFloat(maxRtRaw) : null,
    min_bottom_time:      int('full_min_bottom_time'),
    max_bottom_time:      int('full_max_bottom_time'),
  };
}

async function submitFullOptimise() {
  setLoading(true, 'Optimising deco gas… evaluating mixes, this may take 30–60 seconds');
  clearResults();
  const body = buildFullOptimiseRequest();
  try {
    const resp = await fetch('/api/optimise/full', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    if (!resp.ok) { const txt = await resp.text(); throw new Error(`Server error ${resp.status}: ${txt}`); }
    const data = await resp.json();
    renderFullOptResults(data);
  } catch(err) { showError(err.message); }
  finally { setLoading(false); }
}

function renderFullOptResults(data) {
  const bestMixEl = document.getElementById('full-opt-mix');
  const btLabelEl = document.getElementById('full-opt-bt-label');
  const bg = data.back_gas || {};
  const backGasLabel = bg.he > 0 ? `Tx ${bg.o2}/${bg.he}` : (bg.o2 === 21 ? 'Air' : `EAN${bg.o2}`);

  if (data.best_deco1_o2 != null && data.best_deco2_o2 != null) {
    const d1 = `EAN${data.best_deco1_o2}`;
    const d2 = data.best_deco2_o2 === 100 ? 'O₂' : `EAN${data.best_deco2_o2}`;
    bestMixEl.textContent = `${d1} + ${d2}`;
    btLabelEl.textContent =
      `${data.best_bottom_time} min bottom time · ${d1} @${fmt0(data.best_deco1_switch_depth)}m → ${d2} @${fmt0(data.best_deco2_switch_depth)}m · back gas ${backGasLabel}`;
  } else {
    bestMixEl.textContent = '—';
    btLabelEl.textContent = 'No feasible deco gas pair found';
  }

  document.getElementById('full-opt-steps').textContent =
    `${data.mixes_evaluated} deco gas pairs evaluated · ${data.total_steps_checked} deco calculations`;

  const tableContainer = document.getElementById('full-opt-mix-table');
  if (tableContainer && data.all_results && data.all_results.length > 0) {
    const rows = data.all_results.slice(0, 40).map((r, i) => {
      const isBest = i === 0 && r.feasible;
      const d1Name = `EAN${r.deco1_o2}`;
      const d2Name = r.deco2_o2 === 100 ? 'O₂' : `EAN${r.deco2_o2}`;
      const btVal = r.feasible ? `${r.max_bottom_time} min` : '—';
      const decoVal = r.total_deco != null ? `${fmt1(r.total_deco)} min` : '—';
      const cnsVal = r.cns != null ? `${fmt1(r.cns)}%` : '—';
      const otuVal = r.otu != null ? fmt0(r.otu) : '—';
      return `<tr${isBest ? ' class="best-row"' : ''}>
        <td>${d1Name}${isBest ? ' ★' : ''}</td>
        <td class="num">${fmt0(r.deco1_switch_depth)} m</td>
        <td>${d2Name}</td>
        <td class="num">${fmt0(r.deco2_switch_depth)} m</td>
        <td class="num">${btVal}</td>
        <td class="num">${decoVal}</td>
        <td class="num">${cnsVal}</td>
        <td class="num">${otuVal}</td>
      </tr>`;
    }).join('');

    tableContainer.innerHTML = `
      <table class="mix-table">
        <thead><tr>
          <th>Deco Gas 1</th><th>@Depth</th><th>Deco Gas 2</th><th>@Depth</th><th>Max BT</th><th>Total Deco</th><th>CNS%</th><th>OTU</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  const sc = data.scenario;
  if (sc) {
    sc.gas_plan  = data.gas_plan;
    sc.dive_mode = data.dive_mode;
    sc.gf_low    = data.gf_low;
    sc.gf_high   = data.gf_high;

    renderSummaryInto(sc, 'full-opt-summary-content');
    renderToxicityInto(sc, 'full-opt-toxicity-content');
    renderDecoSchedule(sc, 'full-opt-profile-chart', 'full-opt-deco-content');
    renderGasUsage(sc, 'full-opt-gas-content');
    renderGasPlan(sc, 'full-opt-mingas-content');
  }

  fullOptResults.classList.remove('hidden');
  fullOptResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
