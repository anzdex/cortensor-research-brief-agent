const http = require('http');
const url = process.argv[2];
function getJson(u){return new Promise((res,rej)=>{http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)));}).on('error',rej);});}
(async()=>{
  const targets = await getJson('http://127.0.0.1:9222/json/list');
  const page = targets.find(t=>t.type==='page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id=0; const pending={};
  const send=(m,p={})=>new Promise((resolve)=>{const i=++id;pending[i]=resolve;ws.send(JSON.stringify({id:i,method:m,params:p}));});
  ws.onmessage=(ev)=>{const m=JSON.parse(ev.data); if(m.id&&pending[m.id]){pending[m.id](m.result);delete pending[m.id];}};
  ws.onopen=async()=>{ await send('Page.navigate',{url}); console.log('navigated to', url); process.exit(0); };
})();
