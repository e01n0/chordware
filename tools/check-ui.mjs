#!/usr/bin/env node
/* UI invariants for index.html:
   1. every text token in every skin reads at >= 4.5:1 against every
      background it can sit on (bg, bg2, panel)
   Exit 0 = clean. */
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const html = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", "index.html"), "utf8");
const css = html.slice(html.indexOf("<style>"), html.indexOf("</style>"));

/* skin blocks: the bare :root is NIGHT CITY, each html[data-theme=X] overrides it */
const vars = block => Object.fromEntries([...block.matchAll(/--([a-z0-9]+):\s*(#[0-9a-f]{6})/gi)].map(m => [m[1], m[2].toLowerCase()]));
const root = vars(css.slice(css.indexOf(":root{"), css.indexOf("}", css.indexOf(":root{"))));
const skins = { night: root };
for(const m of css.matchAll(/html\[data-theme="([a-z]+)"\]\{([^}]*)\}/g)) skins[m[1]] = { ...root, ...vars(m[2]) };

const lum = h => {
  const [r, g, b] = h.match(/\w\w/g).map(x => parseInt(x, 16) / 255)
    .map(c => c <= .03928 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4);
  return .2126 * r + .7152 * g + .0722 * b;
};
const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((p, q) => q - p); return (hi + .05) / (lo + .05); };

const TEXT = ["text", "dim", "yellow", "cyan", "red"], GROUNDS = ["bg", "bg2", "panel"], MIN = 4.5;
let bad = 0;
for(const [name, s] of Object.entries(skins)){
  for(const t of TEXT) for(const g of GROUNDS){
    const r = ratio(s[t], s[g]);
    if(r < MIN){ console.error(`${name}: --${t} ${s[t]} on --${g} ${s[g]} = ${r.toFixed(2)}:1 (< ${MIN})`); bad++; }
  }
}
console.log(bad ? `${bad} contrast failure(s)` : `contrast: ${Object.keys(skins).length} skins clean`);
process.exit(bad ? 1 : 0);
