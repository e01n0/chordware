// node tools/shoot-ui.mjs [outdir]: sized screenshots of the live page (127.0.0.1:8092) through Chrome DevTools Protocol:
// device emulation (real CSS px + DPR 2), one target per shot, <size>-<skin>-<view>.png
import { spawn } from "child_process";
import { writeFileSync, mkdirSync } from "fs";

const PORT = 9333, OUT = (process.argv[2] || "shots") + "/";
mkdirSync(OUT, { recursive: true });
const chrome = spawn("google-chrome", ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=/tmp/chordware-shoot-profile`, "about:blank"], { stdio: "ignore" });
const sleep = ms => new Promise(r => setTimeout(r, ms));
for(let i = 0; i < 50; i++){ try{ await fetch(`http://127.0.0.1:${PORT}/json/version`); break; }catch(e){ await sleep(200); } }

async function shot(size, skin, view, hash){
  const [w, h] = size.split("x").map(Number);
  const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map(); const loaded = new Promise(r => { ws.addEventListener("message", e => { const m = JSON.parse(e.data); if(m.method === "Page.loadEventFired") r(); }); });
  ws.addEventListener("message", e => { const m = JSON.parse(e.data); if(m.id && pending.has(m.id)){ pending.get(m.id)(m.result); pending.delete(m.id); } });
  const rpc = (method, params = {}) => new Promise(r => { pending.set(++id, r); ws.send(JSON.stringify({ id, method, params })); });
  await rpc("Page.enable");
  await rpc("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 2, mobile: w < 900 });
  const skinQ = skin === "night" ? "" : skin;
  await rpc("Page.navigate", { url: `http://127.0.0.1:8092/?nocache=${Date.now()}&skin=${skinQ}#${hash}` });
  await loaded; await sleep(1800);                       // fonts + the route's overlay draw
  const { data } = await rpc("Page.captureScreenshot", { format: "png" });
  writeFileSync(`${OUT}${size}-${skin}-${view}.png`, Buffer.from(data, "base64"));
  ws.close();
  await fetch(`http://127.0.0.1:${PORT}/json/close/${t.id}`);
  console.log(`${size}-${skin}-${view}.png`);
}

const VIEWS = [["chords", "chords"], ["rolls", "learn/rolls"], ["song", "learn/song"], ["map", "chords/map"], ["practice", "practice"]];
for(const skin of ["paper", "night"]) for(const size of ["390x844", "1280x800"]) for(const [v, h] of VIEWS) await shot(size, skin, v, h);
for(const size of ["370x900", "820x710"]) for(const [v, h] of VIEWS.slice(0, 2)) await shot(size, "paper", v, h);
chrome.kill();
