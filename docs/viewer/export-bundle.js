/* Small, deterministic ZIP writer for the existing display files. No pixel work. */
((root) => {
  'use strict';
  const MAX_BYTES = 32 * 1024 * 1024;
  const encoder = new TextEncoder();
  const table = Uint32Array.from({length:256}, (_, value) => {
    for (let i = 0; i < 8; i++) value = (value >>> 1) ^ ((value & 1) ? 0xedb88320 : 0);
    return value >>> 0;
  });
  function crc32(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) crc = (crc >>> 8) ^ table[(crc ^ byte) & 255];
    return (crc ^ 0xffffffff) >>> 0;
  }
  function zip(entries) {
    if (!Array.isArray(entries) || !entries.length || entries.length > 16) throw new Error('Invalid bundle entries');
    const names = new Set();
    let offset = 0, directorySize = 0;
    const locals = [], directory = [];
    for (const entry of entries) {
      if (!entry || typeof entry.name !== 'string' || !/^[A-Za-z0-9_.-]{1,120}$/.test(entry.name) ||
          entry.name === '.' || entry.name === '..' || names.has(entry.name)) {
        throw new Error('Invalid or duplicate bundle name');
      }
      names.add(entry.name);
      if (!(entry.bytes instanceof Uint8Array)) throw new Error('Invalid bundle bytes');
      const name = encoder.encode(entry.name), size = entry.bytes.length;
      if (offset + directorySize + size + name.length * 2 + 98 > MAX_BYTES) throw new Error('Bundle exceeds 32 MiB');
      const crc = crc32(entry.bytes);
      const local = new Uint8Array(30 + name.length), lv = new DataView(local.buffer);
      lv.setUint32(0, 0x04034b50, true); lv.setUint16(4, 20, true);
      lv.setUint16(12, 33, true); // Stable DOS date: 1980-01-01, not acquisition time.
      lv.setUint32(14, crc, true); lv.setUint32(18, size, true); lv.setUint32(22, size, true);
      lv.setUint16(26, name.length, true); local.set(name, 30);
      const central = new Uint8Array(46 + name.length), cv = new DataView(central.buffer);
      cv.setUint32(0, 0x02014b50, true); cv.setUint16(4, 20, true); cv.setUint16(6, 20, true);
      cv.setUint16(14, 33, true); cv.setUint32(16, crc, true);
      cv.setUint32(20, size, true); cv.setUint32(24, size, true);
      cv.setUint16(28, name.length, true); cv.setUint32(42, offset, true); central.set(name, 46);
      locals.push(local, entry.bytes); directory.push(central);
      offset += local.length + size; directorySize += central.length;
    }
    const end = new Uint8Array(22), ev = new DataView(end.buffer);
    ev.setUint32(0, 0x06054b50, true);
    ev.setUint16(8, entries.length, true); ev.setUint16(10, entries.length, true);
    ev.setUint32(12, directorySize, true); ev.setUint32(16, offset, true);
    const result = new Uint8Array(offset + directorySize + end.length);
    let position = 0;
    for (const part of [...locals, ...directory, end]) { result.set(part, position); position += part.length; }
    return result;
  }
  async function checkedFile(path, expectedHash, expectedSize) {
    const response = await fetch(path);
    if (!response.ok || Number(response.headers.get('content-length')) > MAX_BYTES) throw new Error('Local file unavailable');
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.length > MAX_BYTES || (expectedSize !== undefined && bytes.length !== expectedSize)) throw new Error('Local file size mismatch');
    if (expectedHash) {
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      const actual = Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, '0')).join('');
      if (actual !== expectedHash) throw new Error('Local display file mismatch');
    }
    return bytes;
  }
  async function displayBundle(data) {
    const sourceBytes = await checkedFile('renders/SOURCE.json');
    const source = JSON.parse(new TextDecoder().decode(sourceBytes));
    if (source.wkid !== 32645 || source.renders.length !== 2) throw new Error('Invalid display metadata');
    const entries = [];
    for (const key of ['before', 'after']) {
      const render = source.renders.find(item => item.key === key);
      const scene = data[key];
      if (!render || render.file !== key + '.png' || render.world_file !== key + '.pgw' ||
          render.source_id !== scene.source_id || render.date !== scene.date || render.sha256 !== scene.sha256 ||
          JSON.stringify(render.bounds_easting_northing) !== JSON.stringify(data.bounds)) throw new Error('Display identity mismatch');
      entries.push({name:render.file, bytes:await checkedFile('renders/' + render.file, render.sha256, render.bytes)});
      entries.push({name:render.world_file, bytes:await checkedFile('renders/' + render.world_file, render.world_file_sha256)});
      entries.push({name:render.file + '.aux.xml', bytes:await checkedFile('renders/' + render.file + '.aux.xml')});
    }
    entries.push({name:'SOURCE.json', bytes:sourceBytes});
    entries.push({name:'README.txt', bytes:await checkedFile('ARCGIS_DISPLAY_README.txt')});
    return zip(entries);
  }
  const api = Object.freeze({zip, crc32, displayBundle});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.NEPAL_EXPORT = api;
})(typeof window !== 'undefined' ? window : globalThis);
