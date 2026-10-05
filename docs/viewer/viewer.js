/* One projected viewport: two original displays and a precomputed unverified dB difference. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const status = $('ready-status');
  let ready = false, timer = null;
  const fail = (message) => {
    ready = false;
    if (timer !== null) clearInterval(timer);
    timer = null;
    status.textContent = message;
    $('map-wrap').hidden = true;
    document.querySelectorAll('.toolbar button').forEach(button => button.disabled = true);
    $('split').disabled = true;
    $('download-layers').disabled = true;
    $('fallback').hidden = false;
    document.body.dataset.ready = 'failed';
  };
  if (!window.L || !window.NEPAL_VIEWER) { fail('Viewer code or metadata could not load.'); return; }
  const data = window.NEPAL_VIEWER;
  const [west, south, east, north] = data.bounds;
  if (data.wkid !== 32645 || ![west,south,east,north].every(Number.isFinite) || east <= west || north <= south) {
    fail('Invalid projected render metadata.'); return;
  }
  // CRS.Simple supplies a planar meter grid here, not latitude/longitude.
  const crs = L.extend({}, L.CRS.Simple, {code:'EPSG:32645'});
  const bounds = L.latLngBounds([south,west],[north,east]);
  const map = L.map('map', {crs, minZoom:-9, maxZoom:-2, zoomSnap:0.25, zoomDelta:0.5,
    maxBounds:bounds.pad(0.2), maxBoundsViscosity:1, zoomAnimation:false, fadeAnimation:false,
    markerZoomAnimation:false, attributionControl:false});
  map.fitBounds(bounds, {padding:[22,30], animate:false});
  map.setZoom(map.getZoom() + 1, {animate:false});
  L.control.scale({imperial:false, metric:true, position:'bottomleft', maxWidth:120}).addTo(map);
  const after = L.imageOverlay(data.after.file, bounds, {alt:'28 August 2026 Sentinel-1D VV gamma0 display',interactive:false}).addTo(map);
  const before = L.imageOverlay(data.before.file, bounds, {alt:'16 August 2026 Sentinel-1D VV gamma0 display',interactive:false}).addTo(map);
  const difference = data.difference ? L.imageOverlay(data.difference.file, bounds,
    {alt:'Unverified radar brightness difference, 28 minus 16 August, blue decreased and orange increased',interactive:false,opacity:0}).addTo(map) : null;
  let differenceLoaded = false, differenceFailed = false;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let mode = 'swipe', split = 50, blinkDate = 'before';
  let pendingDifference = new URLSearchParams(location.hash.slice(1)).get('view') === 'difference';
  const loaded = new Set();
  const wrap = $('map-wrap');

  function hashState() {
    if (!ready || (pendingDifference && !differenceLoaded)) return;
    const center = map.getCenter();
    const view = mode === 'blink' ? blinkDate : mode;
    const hash = new URLSearchParams({view, split:String(split), z:map.getZoom().toFixed(2),
      x:center.lng.toFixed(2), y:center.lat.toFixed(2)}).toString();
    const url = new URL(location.href);
    url.hash = hash;
    history.replaceState(null,'',url.href);
  }

  function draw() {
    if (!ready) return;
    const image = before.getElement();
    const effective = mode === 'blink' ? blinkDate : mode;
    before.setOpacity(effective === 'after' || effective === 'difference' ? 0 : 1);
    after.setOpacity(effective === 'difference' ? 0 : 1);
    if (difference) difference.setOpacity(effective === 'difference' && differenceLoaded ? 1 : 0);
    if (effective === 'swipe') {
      const cut = map.containerPointToLayerPoint([map.getSize().x * split / 100,0]);
      const corner = map.latLngToLayerPoint(bounds.getNorthWest());
      const width = image.offsetWidth;
      const localCut = Math.max(0,Math.min(width,cut.x - corner.x));
      image.style.clipPath = `inset(0 ${width - localCut}px 0 0)`;
    } else image.style.clipPath = '';
    $('divider').hidden = effective !== 'swipe';
    $('divider').style.left = split + '%';
    $('split').disabled = effective !== 'swipe';
    $('split').value = split;
    $('split-value').textContent = split + '%';
    $('before-label').hidden = effective === 'after' || effective === 'difference';
    $('after-label').hidden = effective === 'before' || effective === 'difference';
    $('difference-label').hidden = effective !== 'difference';
    $('display-legend').hidden = effective === 'difference';
    $('difference-legend').hidden = effective !== 'difference';
    $('scene-status').textContent = effective === 'swipe'
      ? 'Swipe: before on the left, after on the right'
      : effective === 'difference' ? 'Unverified brightness difference · 28 Aug minus 16 Aug · blue ↓ / orange ↑'
      : `${mode === 'blink' ? 'Blink · ' : ''}${effective === 'before' ? '16 August 2026 · before' : '28 August 2026 · after'}`;
    document.querySelectorAll('[data-mode]').forEach(button => button.setAttribute('aria-pressed',String(button.dataset.mode === mode)));
    $('blink').setAttribute('aria-pressed',String(mode === 'blink'));
    $('blink').textContent = reduced.matches ? 'Toggle date' : mode === 'blink' ? 'Stop blinking' : 'Blink dates';
    wrap.dataset.mode = effective;
    wrap.dataset.split = String(split);
    wrap.dataset.zoom = String(map.getZoom());
  }

  function stopBlink() { if (timer !== null) clearInterval(timer); timer = null; }
  function setMode(next) {
    if (next === 'difference' && !differenceLoaded) return;
    pendingDifference = false;
    stopBlink(); mode = next; draw(); hashState();
  }
  function toggleBlink() {
    pendingDifference = false;
    if (reduced.matches) { setMode(mode === 'before' ? 'after' : 'before'); return; }
    if (mode === 'blink') { setMode('swipe'); return; }
    stopBlink(); mode = 'blink'; blinkDate = 'before'; draw();
    timer = setInterval(() => {blinkDate = blinkDate === 'before' ? 'after' : 'before'; draw();},800);
  }

  function restoreHash() {
    const parameters = new URLSearchParams(location.hash.slice(1));
    const v = parameters.get('view');
    if (['swipe','before','after'].includes(v)) { mode = v; pendingDifference = false; }
    if (v === 'difference' && differenceLoaded) mode = v;
    else if (v === 'difference' && !differenceFailed) pendingDifference = true;
    if (parameters.has('split')) { const n = Number(parameters.get('split')); if (Number.isFinite(n)) split = Math.round(Math.max(0,Math.min(100,n))); }
    if (['x','y','z'].every(k => parameters.has(k))) {
      const [x,y,z] = ['x','y','z'].map(k => Number(parameters.get(k)));
      if ([x,y,z].every(Number.isFinite) && bounds.pad(0.2).contains([y,x]) && z >= -9 && z <= -2) map.setView([y,x],z,{animate:false});
    }
  }
  function didLoad(key) {
    loaded.add(key);
    if (loaded.size !== 2) return;
    ready = true;
    restoreHash();
    document.body.dataset.ready = 'true';
    document.querySelectorAll('.toolbar button').forEach(button => button.disabled = false);
    $('mode-difference').disabled = !differenceLoaded;
    $('download-layers').disabled = !window.NEPAL_EXPORT || !window.crypto?.subtle;
    if ($('download-layers').disabled) $('export-status').textContent = 'Download unavailable here; use the local-server instructions in the viewer guide.';
    draw(); hashState();
    status.textContent = `Two date displays loaded · ${data.before.size[0]} × ${data.before.size[1]} px each${differenceFailed ? ' · difference unavailable' : differenceLoaded ? ' · unverified difference available' : ' · loading difference…'}`;
  }
  before.on('load',() => didLoad('before'));
  after.on('load',() => didLoad('after'));
  before.on('error',() => fail('The before render could not load.'));
  after.on('error',() => fail('The after render could not load.'));
  if (difference) {
    const differenceReady = () => {
      differenceLoaded = true;
      if (!ready) return;
      $('mode-difference').disabled = false;
      if (pendingDifference) mode = 'difference';
      pendingDifference = false;
      draw(); hashState();
      status.textContent = 'Two date displays and unverified brightness difference loaded · same projected display grid';
    };
    difference.on('load', differenceReady);
    difference.on('error', () => {
      differenceFailed = true; differenceLoaded = false;
      pendingDifference = false;
      $('mode-difference').disabled = true;
      if (mode === 'difference') setMode('swipe');
      status.textContent = 'Difference render unavailable. Both original date displays remain available.';
    });
    if (difference.getElement().complete && difference.getElement().naturalWidth) differenceReady();
  } else differenceFailed = true;
  for (const [key,layer] of [['before',before],['after',after]]) {
    layer.getElement().dataset.sourceId = data[key].source_id;
    if (layer.getElement().complete && layer.getElement().naturalWidth) didLoad(key);
  }
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click',() => setMode(button.dataset.mode)));
  $('blink').addEventListener('click',toggleBlink);
  $('download-layers').addEventListener('click',async () => {
    if (!ready || !window.NEPAL_EXPORT || !window.crypto?.subtle) return;
    const button = $('download-layers'), message = $('export-status');
    button.disabled = true;
    message.textContent = 'Packaging the two existing local display layers…';
    let url = null;
    try {
      const bytes = await window.NEPAL_EXPORT.displayBundle(data);
      url = URL.createObjectURL(new Blob([bytes], {type:'application/zip'}));
      const link = document.createElement('a');
      link.href = url; link.download = 'Nepal_unverified_display_layers.zip';
      document.body.append(link); link.click(); link.remove();
      message.textContent = 'Download requested. Extract the ZIP, keep sidecars together, then add both PNGs in ArcGIS.';
    } catch {
      message.textContent = 'Could not package the local display files. The viewer and existing ArcGIS handoff are still available.';
    } finally {
      if (url) setTimeout(() => URL.revokeObjectURL(url), 60000);
      button.disabled = !ready;
    }
  });
  $('fit').addEventListener('click',() => {map.fitBounds(bounds,{padding:[22,30],animate:false}); hashState();});
  $('closer').addEventListener('click',() => {map.fitBounds(bounds,{padding:[22,30],animate:false}); map.setZoom(map.getZoom() + 1,{animate:false}); hashState();});
  $('split').addEventListener('input',() => {split = Number($('split').value); draw(); hashState();});
  $('drag-handle').addEventListener('pointerdown',event => {
    if (!ready || mode !== 'swipe') return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
  });
  $('drag-handle').addEventListener('pointermove',event => {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
    const rect = wrap.getBoundingClientRect();
    split = Math.round(Math.max(0,Math.min(100,(event.clientX - rect.left) / rect.width * 100)));
    draw(); hashState();
  });
  $('drag-handle').addEventListener('pointerup',event => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  });
  map.on('move zoom resize',draw);
  map.on('moveend zoomend',hashState);
  map.on('mousemove click',event => {$('coordinates').textContent = `E ${Math.round(event.latlng.lng).toLocaleString()} · N ${Math.round(event.latlng.lat).toLocaleString()} m`;});
  window.addEventListener('hashchange',() => {stopBlink(); restoreHash(); draw();});
  document.addEventListener('visibilitychange',() => {if (document.hidden && mode === 'blink') setMode('swipe');});
  reduced.addEventListener('change',() => {if (mode === 'blink') setMode('swipe'); else draw();});
  new ResizeObserver(() => map.invalidateSize({animate:false})).observe(wrap);
})();
