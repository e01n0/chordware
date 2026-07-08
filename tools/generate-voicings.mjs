#!/usr/bin/env node
/**
 * CHORDWARE voicing generator.
 *
 * For every tuning in index.html's CHORD_LIBRARY, generates a playable
 * voicing for each (root × quality) combo that isn't already in the
 * library, and inserts the new entries into index.html in place.
 *
 * Usage:  node tools/generate-voicings.mjs          # dry run (prints what it would add)
 *         node tools/generate-voicings.mjs --write  # insert into index.html
 *
 * It never touches existing entries, so curated shapes, ornaments and
 * notes are safe — add a new quality below (or a new tuning in
 * index.html) and re-run. Voicing search: all four strings sounded,
 * every note in-chord, required tones present (the fifth is omittable
 * on four-note chords), span ≤ 4 frets so the shape fits the renderer's
 * five-fret window, no open strings in shifted (above-nut) positions.
 * Scoring prefers low positions, open strings, small spans and
 * barre-able shapes.
 */
import fs from 'fs';
import { fileURLToPath } from 'url';

const PATH = fileURLToPath(new URL('../index.html', import.meta.url));
const WRITE = process.argv.includes('--write');

const html = fs.readFileSync(PATH, 'utf8');
// several <script> blocks exist (theme restore in <head>, the app) — the app is the longest
const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).sort((a, b) => b.length - a.length)[0];
const head = js.slice(0, js.lastIndexOf('/*', js.indexOf('APP STATE')));
const ctx = {};
new Function('x', head + '; x.TUNINGS = TUNINGS; x.LIB = CHORD_LIBRARY;')(ctx);
const { TUNINGS, LIB } = ctx;

const ROOTS = ["C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"]; // index = pitch class

// suffix -> intervals, required intervals, categories, full-name
const QUALITIES = {
  "":     { iv:[0,4,7],    req:[0,4,7],    cats:["major"],             full:"major" },
  "m":    { iv:[0,3,7],    req:[0,3,7],    cats:["minor"],             full:"minor" },
  "7":    { iv:[0,4,7,10], req:[0,4,10],   cats:["seventh"],           full:"dominant 7" },
  "m7":   { iv:[0,3,7,10], req:[0,3,10],   cats:["minor","seventh"],   full:"minor 7" },
  "maj7": { iv:[0,4,7,11], req:[0,4,11],   cats:["seventh"],           full:"major 7" },
  "6":    { iv:[0,4,7,9],  req:[0,4,9],    cats:["major","colour"],    full:"major 6" },
  "m6":   { iv:[0,3,7,9],  req:[0,3,9],    cats:["minor","colour"],    full:"minor 6" },
  "sus2": { iv:[0,2,7],    req:[0,2,7],    cats:["colour"],            full:"suspended 2" },
  "sus4": { iv:[0,5,7],    req:[0,5,7],    cats:["colour"],            full:"suspended 4" },
  "add9": { iv:[0,2,4,7],  req:[0,2,4],    cats:["major","colour"],    full:"add 9" },
  "dim7": { iv:[0,3,6,9],  req:[0,3,6,9],  cats:["colour"],            full:"diminished 7" },
  "aug":  { iv:[0,4,8],    req:[0,4,8],    cats:["colour"],            full:"augmented" },
};
const MAXFRET = 9;

function* combos(n, max){
  const c = new Array(n).fill(0);
  while(true){
    yield [...c];
    let i = n - 1;
    while(i >= 0 && c[i] === max){ c[i] = 0; i--; }
    if(i < 0) return;
    c[i]++;
  }
}

function bestVoicing(tuning, rootPC, q){
  const chordPCs = q.iv.map(x => (x + rootPC) % 12);
  const reqPCs = q.req.map(x => (x + rootPC) % 12);
  let best = null, bestScore = Infinity;
  for(const frets of combos(tuning.pitches.length, MAXFRET)){
    const pcs = frets.map((f,i) => (tuning.pitches[i] + f) % 12);
    if(!pcs.every(p => chordPCs.includes(p))) continue;
    if(!reqPCs.every(p => pcs.includes(p))) continue;
    const fretted = frets.filter(f => f > 0);
    const maxF = Math.max(0, ...fretted);
    const minF = fretted.length ? Math.min(...fretted) : 0;
    const span = fretted.length ? maxF - minF : 0;
    if(span > 4) continue;
    if(maxF > 5 && frets.some(f => f === 0)) continue;
    const opens = frets.filter(f => f === 0).length;
    const distinct = new Set(fretted).size;
    const has5th = pcs.includes((rootPC + 7) % 12) || q.iv.length === 3;
    const score = span * 3 + maxF * 1.2 + minF - opens * 1.5
                + distinct * 0.7 + (has5th ? 0 : 1.5) + (maxF > 5 ? 3 : 0);
    if(score < bestScore){ bestScore = score; best = frets; }
  }
  if(!best) return null;
  const fretted = best.filter(f => f > 0);
  const minF = Math.min(...fretted);
  const fingers = best.map(f => f === 0 ? 0 : Math.min(4, f - minF + 1));
  return { frets: best, fingers };
}

const norm = s => s.toLowerCase().replace(/[()\s]/g, "");
const out = {}, skipped = [];
for(const tk of Object.keys(LIB)){
  const existing = new Set(LIB[tk].map(c => norm(c.name)));
  const lines = [];
  for(let r = 0; r < 12; r++){
    for(const [suf, q] of Object.entries(QUALITIES)){
      const name = ROOTS[r] + suf;
      if(existing.has(norm(name))) continue;
      const v = bestVoicing(TUNINGS[tk], r, q);
      if(!v){ skipped.push(`${tk}:${name}`); continue; }
      const full = ROOTS[r].replace("b","♭") + " " + q.full;
      lines.push(`    { name:${JSON.stringify(name)}, full:${JSON.stringify(full)}, frets:[${v.frets}], fingers:[${v.fingers}], cats:${JSON.stringify(q.cats)}, ornaments:[] },`);
    }
  }
  out[tk] = lines;
  console.log(`${tk}: +${lines.length} new voicings`);
  if(!WRITE) lines.forEach(l => console.log(l));
}
if(skipped.length) console.log('unvoiceable, skipped:', skipped.join(' '));

if(!WRITE){
  console.log('\nDry run — re-run with --write to insert into index.html');
  process.exit(0);
}
if(Object.values(out).every(l => l.length === 0)){
  console.log('nothing to add');
  process.exit(0);
}

// each tuning's array closes with "  ]," followed by the next tuning
// comment (or "};" for the last one) — insert just before the close
const keys = Object.keys(LIB);
let newHtml = html;
for(let i = 0; i < keys.length; i++){
  if(!out[keys[i]].length) continue;
  const anchor = i + 1 < keys.length
    ? new RegExp(`\\n  \\],(?=[\\s\\S]{0,200}?${keys[i+1]}: \\[)`)
    : /\n  \],\n\};/;
  if(!anchor.test(newHtml)) throw new Error('anchor not found for ' + keys[i]);
  newHtml = newHtml.replace(anchor, m => "\n" + out[keys[i]].join("\n") + m);
}
fs.writeFileSync(PATH, newHtml);
console.log('index.html updated');
