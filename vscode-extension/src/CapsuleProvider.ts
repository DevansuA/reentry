/**
 * Sidebar webview provider that renders the Re-entry Capsule.
 *
 * The webview fetches from the FastAPI server using the same /api/* endpoints
 * as the Next.js web app. Approve and Reject calls go through the same server
 * validation path as the CLI, so the allow-list fires at execution time.
 *
 * No capsule logic is duplicated here; this is a thin display client.
 */

import * as vscode from "vscode";

export class CapsuleProvider implements vscode.WebviewViewProvider {
  private _view?: vscode.WebviewView;
  private readonly _context: vscode.ExtensionContext;

  constructor(context: vscode.ExtensionContext) {
    this._context = context;
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _ctx: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ): void {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this._getHtml(webviewView.webview);

    // Messages from the webview (approve/reject) are already proxied through
    // the server endpoints, so no additional validation is needed here.
    webviewView.webview.onDidReceiveMessage(
      (msg) => {
        if (msg.type === "error") {
          vscode.window.showErrorMessage(`ReEntry: ${msg.text}`);
        }
      },
      undefined,
      this._context.subscriptions,
    );
  }

  refresh(): void {
    if (this._view) {
      this._view.webview.postMessage({ type: "refresh" });
    }
  }

  private _getHtml(webview: vscode.Webview): string {
    const cfg = vscode.workspace.getConfiguration("reentry");
    const serverUrl = cfg.get<string>("serverUrl", "http://localhost:8000");

    // The webview fetches from the server using the CSP-allowed origin.
    // All visual identity constants are inlined to avoid external resources.
    return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy"
  content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src ${serverUrl};">
<title>ReEntry</title>
<style>
:root{
  --ground:#11151c; --panel:#171d27; --line:#2a3342;
  --ink:#dde3ec; --ink-dim:#8b95a7;
  --amber:#e8a33d; --cyan:#5fd3c4; --ok:#7fb069; --bad:#d1604f;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--ground);color:var(--ink);font:13px/1.5 system-ui,sans-serif;padding:12px}
h2{font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:var(--ink-dim);
   margin:12px 0 6px;font-weight:500}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:4px;
       padding:10px 12px;margin-bottom:10px}
.entropy-label{font-size:12px;font-weight:600}
.entropy-low{color:var(--ok)} .entropy-moderate{color:var(--amber)} .entropy-high{color:var(--bad)}
.tape{height:8px;border-radius:2px;background:var(--line);margin:6px 0}
.tape-fill{height:100%;background:linear-gradient(90deg,var(--ok),var(--amber) 60%,var(--bad));
           border-radius:2px;transition:width .6s ease}
@media(prefers-reduced-motion:reduce){.tape-fill{transition:none}}
.item{padding:5px 0;border-top:1px dotted var(--line);font-size:12px;display:flex;
      flex-direction:column;gap:3px}
.item:first-child{border-top:none}
.item-row{display:flex;gap:5px;flex-wrap:wrap;align-items:baseline}
.icon{color:var(--ink-dim);font-size:10px;flex-shrink:0}
.blocker{color:var(--amber)}
.rationale{color:var(--ink-dim);font-size:11px;padding-left:14px}
.badge{font:10px var(--mono);color:var(--ink-dim);border:1px solid var(--line);
       border-radius:2px;padding:0 4px}
.chip{font:10px var(--mono);color:var(--cyan);border:1px solid var(--cyan);
      border-radius:2px;padding:0 4px;cursor:pointer;background:transparent}
.chip:hover{background:rgba(95,211,196,.1)}
.action-box{border-left:3px solid var(--ok);padding-left:10px}
.action-title{font-weight:500;font-size:12px;margin-bottom:4px}
.action-cmd{font:11px var(--mono);color:var(--cyan);display:block;margin-bottom:6px}
.btn{font:12px system-ui,sans-serif;border-radius:3px;padding:4px 10px;cursor:pointer;
     border:1px solid transparent}
.btn-approve{background:var(--ok);color:var(--ground);border-color:var(--ok)}
.btn-reject{background:transparent;color:var(--bad);border-color:var(--bad)}
.btn:disabled{opacity:.4;cursor:default}
.dim{color:var(--ink-dim);font-size:11px}
.error{color:var(--bad);font-size:12px;padding:12px}
.loading{color:var(--ink-dim);font-size:12px;padding:12px}
.server-hint{color:var(--ink-dim);font-size:11px;margin-top:6px}
</style>
</head>
<body>
<div id="root"><div class="loading">Loading capsule...</div></div>
<script>
const SERVER = ${JSON.stringify(serverUrl)};
const vscode = acquireVsCodeApi();

const ICON = {observed:"●",inferred:"○",user_corrected:"◆"};

function esc(s){
  return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function chip(id){
  return \`<button class="chip" onclick="showEvidence('\${esc(id)}')" title="Show ledger event">\${esc(id.slice(0,10))}</button>\`;
}

function renderItem(it,cls=""){
  const icon = ICON[it.inference]||"●";
  const chips = (it.evidence_ids||[]).slice(0,3).map(chip).join(" ");
  const rat = it.rationale ? \`<div class="rationale">why: \${esc(it.rationale)}</div>\` : "";
  const cl = it.classification ? \`<span class="badge">\${esc(it.classification)}</span>\` : "";
  const due = it.due_at ? \`<span class="badge">due \${esc(it.due_at.slice(0,10))}</span>\` : "";
  return \`<div class="item">
    <div class="item-row">
      <span class="icon">\${icon}</span>
      <span class="\${cls}">\${esc(it.text)}</span>
      \${chips}
    </div>
    \${rat}\${cl||due?"<div style='padding-left:14px'>"+cl+due+"</div>":""}
  </div>\`;
}

function renderSection(title,items,cls=""){
  if(!items||!items.length)return "";
  return \`<h2>\${esc(title)}</h2><div class="panel">\${items.map(i=>renderItem(i,cls)).join("")}</div>\`;
}

async function load(){
  try{
    const r=await fetch(SERVER+"/api/capsule");
    if(!r.ok){
      const e=await r.json().catch(()=>({detail:r.statusText}));
      if(r.status===404){
        document.getElementById("root").innerHTML=\`
          <div class="error">No project registered here.</div>
          <div class="server-hint">Run <code>reentry init</code> in your project directory, then <code>make server</code>.</div>\`;
        return;
      }
      throw new Error(e.detail||r.statusText);
    }
    const cap=await r.json();
    render(cap);
  }catch(e){
    document.getElementById("root").innerHTML=\`
      <div class="error">Cannot reach server: \${esc(e.message)}</div>
      <div class="server-hint">Start with: <code>make server</code></div>\`;
  }
}

function render(cap){
  const ent=cap.entropy;
  const lbl=ent.label;
  const html=\`
    <div class="panel">
      <div class="item-row">
        <span class="entropy-label entropy-\${esc(lbl)}">\${ent.score}/100 (\${esc(lbl)})</span>
      </div>
      <div class="tape"><div class="tape-fill" style="width:\${ent.score}%"></div></div>
    </div>
    \${cap.objective?renderSection("Objective",[cap.objective]):""}
    \${renderSection("Where things stand",cap.where_things_stand)}
    \${renderSection("Decisions",cap.decisions)}
    \${renderSection("Blockers",cap.blockers,"blocker")}
    \${renderSection("Contradictions",cap.contradictions)}
    \${renderSection("Deadlines",cap.deadlines)}
    \${renderActionPanel(cap)}
    <div class="dim" style="margin-top:8px">
      ● observed &nbsp; ○ inferred &nbsp; ◆ user-corrected
    </div>
  \`;
  document.getElementById("root").innerHTML=html;
}

function renderActionPanel(cap){
  if(!cap.pending_actions||!cap.pending_actions.length)return "";
  const btns=cap.pending_actions.map(a=>\`
    <div class="action-box" id="act-\${a.id}">
      <div class="action-title">\${esc(a.title)}</div>
      <code class="action-cmd">\${esc(a.command)}</code>
      <span class="badge">\${esc(a.risk)}</span>
      <div style="margin-top:6px;display:flex;gap:6px">
        <button class="btn btn-approve" onclick="approve('\${a.id}',true)">Approve and run</button>
        <button class="btn btn-reject"  onclick="approve('\${a.id}',false)">Reject</button>
      </div>
    </div>
  \`).join("");
  return \`<h2>Pending action</h2><div class="panel">\${btns}</div>\`;
}

async function approve(id,run){
  const box=document.getElementById("act-"+id);
  if(box)box.querySelectorAll("button").forEach(b=>b.disabled=true);
  try{
    const url=SERVER+"/api/actions/"+id+(run?"/approve?run=true":"/reject");
    const r=await fetch(url,{method:"POST"});
    if(!r.ok){
      const e=await r.json().catch(()=>({detail:r.statusText}));
      vscode.postMessage({type:"error",text:e.detail||r.statusText});
      if(box)box.querySelectorAll("button").forEach(b=>b.disabled=false);
      return;
    }
    const a=await r.json();
    if(box){
      box.innerHTML=\`<span class="\${a.status==="verified"?"dim":"" }" style="color:\${a.status==="verified"?"var(--ok)":"var(--bad)"}">\${esc(a.status)}</span>\`;
    }
    setTimeout(load,1000);
  }catch(e){
    vscode.postMessage({type:"error",text:String(e)});
  }
}

async function showEvidence(id){
  try{
    const r=await fetch(SERVER+"/api/evidence/"+id);
    if(!r.ok)throw new Error(r.statusText);
    const ev=await r.json();
    let payload;
    try{payload=JSON.parse(ev.payload);}catch{payload=ev.payload;}
    vscode.window.showInformationMessage
    // Fallback: show in output channel concept via postMessage
    vscode.postMessage({type:"evidence",id,data:JSON.stringify(payload,null,2)});
  }catch(e){
    vscode.postMessage({type:"error",text:String(e)});
  }
}

// Listen for refresh messages from the extension host.
window.addEventListener("message",e=>{
  if(e.data&&e.data.type==="refresh")load();
  if(e.data&&e.data.type==="evidence"){
    // Display raw JSON in a simple modal overlay.
    const overlay=document.createElement("div");
    overlay.style="position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:1000;padding:16px;overflow:auto";
    overlay.innerHTML=\`<button onclick="this.parentNode.remove()" style="float:right;background:transparent;border:none;color:var(--ink-dim);font-size:18px;cursor:pointer">&times;</button>
      <pre style="font:11px var(--mono);color:var(--cyan);white-space:pre-wrap;word-break:break-all;margin-top:24px">\${esc(e.data.data)}</pre>\`;
    document.body.appendChild(overlay);
  }
});

load();
setInterval(load,30000);
</script>
</body>
</html>`;
  }
}
