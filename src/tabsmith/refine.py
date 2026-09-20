"""Optional local-LLM pass: section labels, roll choice per section, validated ornaments. Never geometry."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, replace

import requests

from .arrange import ROLLS, Arrangement, arrange
from .leadsheet import PC_NAMES, LeadSheet

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = os.environ.get("TABSMITH_LLM", "qwen3.6:27b")


@dataclass
class Refinement:
    sections: list[dict]
    patterns: dict[str, str]
    ornaments: list[dict]
    notes: str


def _note_name(p: int) -> str:
    return PC_NAMES[p % 12] + str(p // 12 - 1)


def build_prompt(sheet: LeadSheet, tab_txt: str, instrument: str, style: str) -> str:
    bars = []
    for b in range(sheet.bars):
        mel = " ".join(_note_name(m.p) for m in sheet.melody if sheet.bar_of(m.t) == b)
        bars.append(f"bar {b}: chord {sheet.chord_at(b * sheet.bpb)} | melody {mel or '-'}")
    nl = "\n"
    return (
        f'You are a {instrument} arranger ({style} style). Song "{sheet.title}", key {sheet.key} {sheet.mode}, '
        f"{sheet.meter[0]}/{sheet.meter[1]}, {sheet.tempo} bpm.\nLead sheet:\n{nl.join(bars)}\n\n"
        f"Current arrangement (ASCII tab, {instrument} string 1 on top):\n{tab_txt}\n\n"
        "Tasks: 1) label song sections (A, B, ...) by bar. "
        f"2) pick one roll pattern per section from: {', '.join(ROLLS)}. "
        "3) suggest ornaments between a melody note and the next note on the same string: kind \"h\" hammer-on, "
        "\"p\" pull-off, \"s\" slide, giving the bar, beat (0-based within the bar), from-fret and to-fret. "
        "Only suggest ornaments you are confident are idiomatic. 4) one sentence of notes.\n"
        'Reply with JSON only: {"sections":[{"bar":0,"label":"A"}],"pattern_by_section":{"A":"forward"},'
        '"ornaments":[{"bar":0,"beat":0.0,"kind":"h","from":0,"to":2}],"notes":"..."}'
    )


def parse_reply(text: str) -> Refinement | None:
    try:
        d = json.loads(text)
        pats = {str(k): str(v) for k, v in dict(d.get("pattern_by_section", {})).items()}
        if any(p not in ROLLS for p in pats.values()):
            return None
        secs = [{"bar": int(s["bar"]), "label": str(s["label"])} for s in d.get("sections", [])]
        orns = [{"bar": int(o["bar"]), "beat": float(o["beat"]), "kind": str(o["kind"]),
                 "from": int(o["from"]), "to": int(o["to"])}
                for o in d.get("ornaments", []) if str(o.get("kind")) in ("h", "p", "s")]
        return Refinement(secs, pats, orns, str(d.get("notes", "")))
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def refine(sheet: LeadSheet, tab_txt: str, instrument: str, style: str,
           url: str = OLLAMA_URL, model: str = MODEL) -> Refinement | None:
    try:
        r = requests.post(f"{url}/api/generate",
                          json={"model": model, "prompt": build_prompt(sheet, tab_txt, instrument, style),
                                "format": "json", "stream": False, "options": {"temperature": 0.3}},
                          timeout=600)
        r.raise_for_status()
        ref = parse_reply(r.json().get("response", ""))
        if ref is None:
            print("refine: LLM reply unusable, keeping the plain arrangement", file=sys.stderr)
        return ref
    except requests.RequestException as e:
        print(f"refine: Ollama unavailable ({e.__class__.__name__}), keeping the plain arrangement", file=sys.stderr)
        return None


def apply_refinement(arr: Arrangement, ref: Refinement) -> Arrangement:
    sheet = replace(arr.sheet, sections=sorted(ref.sections, key=lambda s: s["bar"]))
    out = arrange(sheet, arr.instrument, arr.style, ref.patterns)
    bpb = sheet.bpb
    for o in ref.ornaments:
        t = o["bar"] * bpb + o["beat"]
        cur = next((n for n in out.notes if abs(n.t - t) < 1e-6 and n.melody and n.fret == o["from"]), None)
        if cur is None:
            continue
        nxt = next((n for n in out.notes if n.t > cur.t and n.string == cur.string), None)
        if nxt is None or nxt.fret != o["to"] or abs(o["to"] - o["from"]) > 4 or not out.tuning.ok(cur.string, o["to"]):
            continue
        if (o["kind"] == "h" and o["to"] <= o["from"]) or (o["kind"] == "p" and o["to"] >= o["from"]):
            continue
        cur.tech = o["kind"]
    return out
