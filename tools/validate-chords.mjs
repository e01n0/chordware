#!/usr/bin/env node
/* Validate every chord and ornament in index.html against chord theory:
   - each voicing's pitch classes must spell exactly the named chord
     (fifth may be omitted in 4-note qualities; documented rootless
     shapes may omit the root)
   - each ornament's `from` must match the chord's fret on that string,
     hammers must ascend, pulls must descend, and the label must name
     the interval the target note actually is.
   Exit code 0 = library clean. */
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const html = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", "index.html"), "utf8");

function extract(name){
  const start = html.indexOf(`const ${name} = {`);
  if(start < 0) throw new Error(name + " not found");
  let i = html.indexOf("{", start), depth = 0, end = -1;
  for(; i < html.length; i++){
    const c = html[i];
    if(c === "{") depth++;
    else if(c === "}"){ depth--; if(depth === 0){ end = i; break; } }
  }
  return eval("(" + html.slice(html.indexOf("{", start), end + 1) + ")");
}

const TUNINGS = extract("TUNINGS");
const LIB = extract("CHORD_LIBRARY");
const NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];

const ROOT_RE = /^([A-G])(#|b)?(.*)$/;
const ROOT_PC = { C:0, D:2, E:4, F:5, G:7, A:9, B:11 };
const QUALITIES = {
  "":        [0,4,7],
  "m":       [0,3,7],
  "7":       [0,4,7,10],
  "m7":      [0,3,7,10],
  "maj7":    [0,4,7,11],
  "6":       [0,4,7,9],
  "m6":      [0,3,7,9],
  "sus2":    [0,2,7],
  "sus4":    [0,5,7],
  "add9":    [0,2,4,7],
  "dim7":    [0,3,6,9],
  "aug":     [0,4,8],
  "m(add9)": [0,2,3,7],
};
// the fifth may be dropped when four different tones compete for the strings
const OPTIONAL = { "7":[7], "m7":[7], "maj7":[7], "6":[7], "m6":[7], "add9":[7], "m(add9)":[7] };

// ornament label → semitones above the root
const LABEL_IVL = {
  "add9":2, "sus2":2, "9th":2,
  "min3":3, "b3":3, "maj3":4, "3rd":4,
  "sus4":5, "add11":5, "4th":5, "11th":5,
  "b5":6, "#11":6, "5th":7,
  "b6":8, "#5":8,
  "6th":9, "maj6":9, "13th":9, "dim7":9,
  "7th":10, "min7":10, "b7":10,
  "maj7":11,
};

let problems = 0;
const fail = msg => { console.log(msg); problems++; };

for(const [tkey, chords] of Object.entries(LIB)){
  const t = TUNINGS[tkey];
  const seen = new Set();
  for(const ch of chords){
    const ctx = `${tkey} ${ch.name} [${ch.frets.join(",")}]`;
    const m = ch.name.match(ROOT_RE);
    if(!m){ fail(`PARSE  ${ctx}: cannot parse name`); continue; }
    let root = ROOT_PC[m[1]];
    if(m[2] === "#") root = (root + 1) % 12;
    if(m[2] === "b") root = (root + 11) % 12;
    const qual = m[3];
    if(!(qual in QUALITIES)){ fail(`QUAL   ${ctx}: unknown quality "${qual}"`); continue; }
    if(seen.has(ch.name)) fail(`DUP    ${ctx}: duplicate chord name`);
    seen.add(ch.name);

    if(ch.frets.length !== t.pitches.length || ch.fingers.length !== t.pitches.length){
      fail(`LEN    ${ctx}: frets/fingers length != ${t.pitches.length}`); continue;
    }
    ch.frets.forEach((f, i) => {
      if(f <= 0 && ch.fingers[i] !== 0) fail(`FING   ${ctx}: string ${i} fret ${f} but finger ${ch.fingers[i]}`);
      if(f > 0 && ch.fingers[i] === 0)  fail(`FING   ${ctx}: string ${i} fret ${f} but finger 0`);
    });

    const pcs = new Set(ch.frets.map((f, i) => f < 0 ? null : (t.pitches[i] + f) % 12).filter(x => x !== null));
    const expected = new Set(QUALITIES[qual].map(iv => (root + iv) % 12));
    const opt = new Set((OPTIONAL[qual] || []).map(iv => (root + iv) % 12));
    const rootless = /rootless|stands in/i.test(ch.notes || "");
    const extra = [...pcs].filter(p => !expected.has(p));
    const missing = [...expected].filter(p => !pcs.has(p) && !opt.has(p) && !(rootless && p === root));
    if(extra.length || missing.length)
      fail(`NOTES  ${ctx}: got {${[...pcs].map(p => NOTE_NAMES[p]).join(",")}}` +
        (missing.length ? ` missing {${missing.map(p => NOTE_NAMES[p]).join(",")}}` : "") +
        (extra.length ? ` extra {${extra.map(p => NOTE_NAMES[p]).join(",")}}` : ""));

    for(const o of (ch.ornaments || [])){
      const octx = `${ctx} orn(s:${o.s} ${o.from}->${o.to} ${o.type} "${o.label}")`;
      if(o.s < 0 || o.s >= t.pitches.length){ fail(`ORN    ${octx}: bad string index`); continue; }
      if(ch.frets[o.s] !== o.from) fail(`ORN    ${octx}: 'from' != chord fret ${ch.frets[o.s]}`);
      if(o.type === "hammer" && !(o.to > o.from)) fail(`ORN    ${octx}: hammer must ascend`);
      if(o.type === "pull"   && !(o.to < o.from)) fail(`ORN    ${octx}: pull must descend`);
      const ivl = ((t.pitches[o.s] + o.to) % 12 - root + 12) % 12;
      if(!(o.label in LABEL_IVL)) fail(`ORN    ${octx}: unknown label`);
      else if(LABEL_IVL[o.label] !== ivl)
        fail(`ORN    ${octx}: target is ${ivl} semitones from root, "${o.label}" means ${LABEL_IVL[o.label]}`);
    }
  }
  console.log(`-- ${tkey}: ${chords.length} chords checked`);
}
console.log(problems ? `\n${problems} problem(s) found` : "\nAll clean");
process.exit(problems ? 1 : 0);
