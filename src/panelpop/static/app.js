'use strict';
const admin = document.body.dataset.page === 'admin';
const $ = id => document.getElementById(id);
const key = admin ? 'panelpop-admin-token' : 'panelpop-viewer-token';
const fragment = new URLSearchParams(location.hash.slice(1));
const suppliedToken = fragment.get('token');
if (suppliedToken) sessionStorage.setItem(key, suppliedToken);
const token = suppliedToken || sessionStorage.getItem(key) || '';
if (location.hash) history.replaceState(null, '', location.pathname);
let busy = false;
async function api(path, data, blob = false) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 3500);
  try {
    const options = {headers: {'X-PanelPop-Token': token}, credentials: 'omit', signal: controller.signal};
    // Keep fetch's default CORS mode: it sends Origin for same-origin mutations,
    // including under the server's no-referrer policy. Never set mode:same-origin.
    if (data !== undefined) {
      options.method = 'POST'; options.headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(data);
    }
    const response = await fetch(path, options);
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.error || `HTTP ${response.status}`);
    }
    if (blob) return {blob: await response.blob(), response};
    return response.json();
  } finally { clearTimeout(timer); }
}
function displayStatus(status) {
  $('demo').hidden = !status.demo;
  $('status').textContent = status.paused ? `停止中 — ${status.reason}` : !status.configured ? 'PCで対象ウィンドウと領域を設定してください。' : status.control ? '接続中 · スマホ操作を許可しています' : '接続中 · 閲覧専用';
  if (admin) {
    $('control').checked = status.control;
    $('control').disabled = status.paused || !status.configured || busy;
    $('resume').disabled = !status.configured || busy;
  }
}
function showError(error) { $('error').textContent = error?.message || String(error || ''); }
function replaceImage(image, blob) {
  const previous = image.dataset.objectUrl;
  const url = URL.createObjectURL(blob); image.dataset.objectUrl = url; image.src = url;
  if (previous) URL.revokeObjectURL(previous);
}
if (!token) showError('接続トークンがありません。PC起動時のURLまたはQRから開いてください。');

if (admin) {
  let hwnd = null, regions = [], width = 0, height = 0, drag = null, previewActive = false, generation = 0;
  function draw() {
    const canvas = $('selection'), context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.lineWidth = Math.max(2, canvas.width / 350); context.font = `${Math.max(16, canvas.width / 50)}px sans-serif`;
    const items = regions.slice(); if (drag) items.push(rectangle(drag.start, drag.end));
    items.forEach(([x, y, w, h], i) => {
      context.strokeStyle = '#80f4de'; context.fillStyle = '#80f4de22'; context.fillRect(x, y, w, h); context.strokeRect(x, y, w, h);
      context.fillStyle = '#ffffff'; context.fillText(`${i + 1}`, x + 5, y + 22);
    });
    $('regions').textContent = `選択領域: ${regions.length} / 4 · ${regions.map(r => r.join(', ')).join(' / ')}`;
  }
  function point(event) {
    const rect = $('selection').getBoundingClientRect();
    return [Math.max(0, Math.min(width, Math.floor((event.clientX - rect.left) / rect.width * width))), Math.max(0, Math.min(height, Math.floor((event.clientY - rect.top) / rect.height * height)))];
  }
  function rectangle(a, b) { return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1])]; }
  $('selection').addEventListener('pointerdown', event => {
    if (!width || regions.length >= 4 || event.button !== 0) return;
    $('selection').setPointerCapture(event.pointerId); drag = {start: point(event), end: point(event)}; draw();
  });
  $('selection').addEventListener('pointermove', event => { if (drag) { drag.end = point(event); draw(); } });
  $('selection').addEventListener('pointerup', event => {
    if (!drag) return;
    const region = rectangle(drag.start, point(event)); drag = null;
    if (region[2] > 0 && region[3] > 0) regions.push(region); draw();
  });
  $('selection').addEventListener('pointercancel', () => { drag = null; draw(); });
  async function windows() {
    const result = await api('/api/admin/windows'); displayStatus(result.status);
    const select = $('windows'), previous = select.value; select.replaceChildren();
    for (const item of result.windows) {
      const option = document.createElement('option'); option.value = String(item.hwnd); option.textContent = `${item.title} (PID ${item.pid})`; select.append(option);
    }
    if ([...select.options].some(option => option.value === previous)) select.value = previous;
    if (!result.windows.length) { const option = document.createElement('option'); option.value = ''; option.textContent = '対象が見つかりません'; select.append(option); }
  }
  async function preview() {
    const thisGeneration = generation;
    try {
      const result = await api(`/api/admin/preview?hwnd=${hwnd}`, undefined, true);
      if (thisGeneration !== generation) return;
      const w = Number(result.response.headers.get('X-Image-Width')), h = Number(result.response.headers.get('X-Image-Height'));
      if (width !== w || height !== h) { regions = []; width = w; height = h; $('selection').width = w; $('selection').height = h; }
      replaceImage($('preview'), result.blob); $('preview-wrap').hidden = false; draw(); showError('');
    } catch (error) { if (thisGeneration === generation) { showError(error); $('preview-wrap').hidden = true; } }
    if (previewActive && thisGeneration === generation) setTimeout(preview, 650);
  }
  async function action(path, data) {
    if (busy) return; busy = true;
    try { const result = await api(path, data); displayStatus(result.status); showError(''); }
    catch (error) { showError(error); }
    finally { busy = false; await api('/api/admin/status').then(r => displayStatus(r.status)).catch(showError); }
  }
  $('refresh').onclick = () => windows().catch(showError);
  $('preview-load').onclick = () => { hwnd = Number($('windows').value); if (!hwnd) return; generation++; regions = []; width = 0; height = 0; previewActive = true; preview(); };
  $('windows').onchange = () => { previewActive = false; generation++; hwnd = null; regions = []; width = 0; $('preview-wrap').hidden = true; draw(); };
  $('clear').onclick = () => { regions = []; draw(); };
  $('configure').onclick = () => action('/api/admin/configure', {hwnd, regions});
  $('control').onchange = () => action('/api/admin/mode', {control: $('control').checked});
  $('stop').onclick = async () => {
    // Stop is always available even while another UI request is pending.
    try { const result = await api('/api/admin/stop', {}); displayStatus(result.status); showError(''); }
    catch (error) { showError(error); }
  };
  $('resume').onclick = () => action('/api/admin/resume', {});
  async function init() {
    await windows();
    const connection = await api('/api/admin/connect'); $('connect-url').value = connection.url;
    const qr = await api('/api/admin/qr', undefined, true); replaceImage($('qr'), qr.blob);
  }
  init().catch(showError);
  async function pollStatus() {
    try { const result = await api('/api/admin/status'); displayStatus(result.status); }
    catch (error) { $('status').textContent = '切断 · PCホストへの接続に失敗しました'; showError(error); $('control').disabled = true; }
    setTimeout(pollStatus, 700);
  }
  pollStatus();
} else {
  let rendered = null, panelUrls = [], sending = false;
  function clearPanels() {
    rendered = null; $('panels').replaceChildren(); panelUrls.forEach(url => URL.revokeObjectURL(url)); panelUrls = [];
  }
  async function tap(event, panel, image, shownFrame) {
    if (sending) return;
    if (!rendered || rendered !== shownFrame || !shownFrame.control || performance.now() >= shownFrame.expires) {
      showError('閲覧専用、または表示期限が切れています。表示の更新を待ってください。'); return;
    }
    const bounds = image.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width, y = (event.clientY - bounds.top) / bounds.height;
    sending = true;
    try { await api('/api/click', {id: shownFrame.id, panel, x, y}); showError(''); }
    catch (error) { showError(error); clearPanels(); }
    finally { sending = false; }
  }
  async function poll() {
    const started = performance.now();
    try {
      const result = await api('/api/state'); displayStatus(result.status);
      if (!result.frame) { clearPanels(); if (result.error) showError(result.error); }
      else {
        const frame = result.frame;
        const images = await Promise.all(frame.panels.map((_, i) => api(`/api/frame?id=${encodeURIComponent(frame.id)}&panel=${i}`, undefined, true)));
        if (performance.now() - started >= result.status.ttl * 1000) throw new Error('フレームの受信期限が切れました。');
        // Atomic DOM swap only after every image arrives; old identities never label new pixels.
        const shownFrame = {id: frame.id, control: result.status.control, expires: started + result.status.ttl * 1000};
        const fragment = document.createDocumentFragment(), urls = [];
        images.forEach((result, i) => {
          const section = document.createElement('section'); section.className = 'panel';
          const title = document.createElement('h2'); title.textContent = `領域 ${i + 1}`;
          const image = document.createElement('img'); image.alt = `領域 ${i + 1} のライブ画面`;
          const url = URL.createObjectURL(result.blob); urls.push(url); image.src = url;
          if (shownFrame.control) image.className = 'actionable';
          image.onclick = event => tap(event, i, image, shownFrame);
          section.append(title, image); fragment.append(section);
        });
        clearPanels(); $('panels').append(fragment); panelUrls = urls; rendered = shownFrame; showError('');
      }
    } catch (error) { clearPanels(); $('status').textContent = '切断・表示停止 · PCとネットワークを確認してください'; showError(error); }
    setTimeout(poll, 350);
  }
  setInterval(() => { if (rendered && performance.now() >= rendered.expires) { clearPanels(); $('status').textContent = '表示期限切れ · 更新を待っています'; } }, 100);
  poll();
}
