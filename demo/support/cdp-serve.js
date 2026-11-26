// CDP Fetch interception: serve /tmp/www over http://127.0.0.1:8000/ without
// a real localhost connection (this Chrome build blocks loopback navigations).
const http = require('http');
const fs = require('fs');
function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (r) => { let d = ''; r.on('data', (c) => d += c); r.on('end', () => resolve(JSON.parse(d))); }).on('error', reject);
  });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const targets = await getJson('http://127.0.0.1:9222/json/list');
  const page = targets.find((t) => t.type === 'page');
  if (!page) { console.error('no page target'); process.exit(1); }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0; const pending = {};
  const send = (method, params = {}) => new Promise((resolve) => {
    const mid = ++id; pending[mid] = resolve;
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  async function handleFetch(p) {
    try {
      const url = new URL(p.request.url);
      const file = url.pathname === '/' ? '/tmp/www/index.html' : '/tmp/www' + decodeURIComponent(url.pathname);
      const data = fs.readFileSync(file);
      const ct = file.endsWith('.html') ? 'text/html;charset=utf-8' : 'text/plain;charset=utf-8';
      await send('Fetch.fulfillRequest', { requestId: p.requestId, responseCode: 200,
        responseHeaders: [{ name: 'Content-Type', value: ct }], body: data.toString('base64') });
    } catch (e) {
      await send('Fetch.fulfillRequest', { requestId: p.requestId, responseCode: 404,
        responseHeaders: [{ name: 'Content-Type', value: 'text/plain' }], body: Buffer.from('not found').toString('base64') });
    }
  }
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending[m.id]) { pending[m.id](m.result); delete pending[m.id]; }
    else if (m.method === 'Fetch.requestPaused') { handleFetch(m.params); }
  };
  ws.onopen = async () => {
    await send('Fetch.enable', { patterns: [{ urlPattern: 'http://127.0.0.1:8000/*', requestStage: 'Request' }] });
    await send('Page.enable');
    await send('Page.navigate', { url: 'http://127.0.0.1:8000/' });
    console.log('CDP fetch interception ON, navigated');
  };
  ws.onerror = (e) => { console.error('ws error', e.message); };
})();
