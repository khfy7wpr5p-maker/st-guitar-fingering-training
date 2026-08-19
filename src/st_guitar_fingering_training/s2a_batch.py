from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
import html
import json
from typing import Iterable

from .s2a_features import S2A_PROTOCOL_VERSION
from .s2a_teacher import (
    S2A_FIRST_PASS_PROVENANCE,
    S2A_INTERNAL_AUDIT_SCHEMA,
    S2A_TEACHER_MANIFEST_SCHEMA,
    build_s2a_teacher_package,
)
from .target_free_musicxml import TargetFreeSource


S2A_BATCH_SCHEMA = "st-guitar-s2a-teacher-batch-v1"
S2A_BATCH_TARGET_PER_CELL = 120
S2A_BATCH_SESSION_COUNT = 6
S2A_BATCH_MIN_EVENTS_PER_FAMILY = 5
S2A_BATCH_MAX_TASKS_PER_EVENT = 4
S2A_BATCH_MAX_TASKS_PER_FAMILY = 24
S2A_BATCH_EXPECTED_FAMILIES = 40

_PAIR_TYPES = ("FINGER_ONLY", "MIXED")
_DISTANCE_STRATA = ("NEAR", "MID", "FAR")
_CELLS = tuple((pair_type, stratum) for pair_type in _PAIR_TYPES for stratum in _DISTANCE_STRATA)


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _canonical_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _digest(payload)


def _event_id(source: TargetFreeSource, event) -> str:
    payload = "|".join(
        (
            S2A_PROTOCOL_VERSION,
            source.family_id,
            source.source_sha256,
            str(event.measure),
            str(event.onset),
            str(event.voice),
            ",".join(str(value) for value in event.pitches_midi),
        )
    )
    return f"s2a-event-sha256:{_digest(payload)}"


@dataclass(frozen=True)
class S2AEventPackage:
    family_id: str
    event_id: str
    teacher_tasks: tuple[dict, ...]
    audit_rows: tuple[dict, ...]

    def __post_init__(self) -> None:
        if not self.family_id or not self.event_id:
            raise ValueError("S2-A event package requires family_id and event_id")
        teacher_ids = {str(row.get("task_id", "")) for row in self.teacher_tasks}
        audit_ids = {str(row.get("task_id", "")) for row in self.audit_rows}
        if not teacher_ids or "" in teacher_ids or teacher_ids != audit_ids:
            raise ValueError("S2-A event package teacher/audit task sets must match and be non-empty")
        if len(teacher_ids) != len(self.teacher_tasks) or len(audit_ids) != len(self.audit_rows):
            raise ValueError("S2-A event package contains duplicate task IDs")
        for row in self.audit_rows:
            if row.get("family_id") != self.family_id or row.get("event_id") != self.event_id:
                raise ValueError("S2-A event package lineage mismatch")
            if (row.get("pair_type"), row.get("distance_stratum")) not in _CELLS:
                raise ValueError("S2-A event package contains an unknown sampling cell")


@dataclass(frozen=True)
class S2ASelectedTask:
    family_id: str
    event_id: str
    task: dict
    audit: dict

    @property
    def task_id(self) -> str:
        return str(self.task["task_id"])

    @property
    def cell(self) -> tuple[str, str]:
        return (str(self.audit["pair_type"]), str(self.audit["distance_stratum"]))


def build_event_packages(sources: Iterable[TargetFreeSource]) -> tuple[S2AEventPackage, ...]:
    """Regenerate H-C and produce label-free S2-A tasks from target-free real events."""

    packages: list[S2AEventPackage] = []
    seen_event_ids: set[str] = set()
    for source in sorted(tuple(sources), key=lambda item: item.family_id):
        for event in source.events:
            if not event.is_chord or len(event.pitches_midi) > 6:
                continue
            event_id = _event_id(source, event)
            if event_id in seen_event_ids:
                raise ValueError("duplicate S2-A event identity")
            seen_event_ids.add(event_id)
            try:
                teacher_manifest, audit = build_s2a_teacher_package(
                    family_id=source.family_id,
                    event_id=event_id,
                    pitches_midi=event.pitches_midi,
                    tuning=event.tuning,
                    provenance=S2A_FIRST_PASS_PROVENANCE,
                )
            except ValueError as exc:
                # A chord with fewer than two surviving H-C assignments cannot teach a ranker.
                if "at least two distinct H-C assignments" in str(exc):
                    continue
                raise
            packages.append(
                S2AEventPackage(
                    family_id=source.family_id,
                    event_id=event_id,
                    teacher_tasks=tuple(teacher_manifest["tasks"]),
                    audit_rows=tuple(audit["rows"]),
                )
            )
    packages.sort(key=lambda item: (item.family_id, item.event_id))
    return tuple(packages)


def _flatten(packages: Iterable[S2AEventPackage]) -> tuple[S2ASelectedTask, ...]:
    flattened: list[S2ASelectedTask] = []
    seen: set[str] = set()
    for package in packages:
        audit_by_id = {str(row["task_id"]): row for row in package.audit_rows}
        for task in package.teacher_tasks:
            task_id = str(task["task_id"])
            if task_id in seen:
                raise ValueError("duplicate S2-A task ID across event packages")
            seen.add(task_id)
            flattened.append(
                S2ASelectedTask(
                    family_id=package.family_id,
                    event_id=package.event_id,
                    task=task,
                    audit=audit_by_id[task_id],
                )
            )
    return tuple(flattened)


def select_balanced_batch(
    packages: Iterable[S2AEventPackage],
    *,
    target_per_cell: int = S2A_BATCH_TARGET_PER_CELL,
    expected_families: int = S2A_BATCH_EXPECTED_FAMILIES,
    min_events_per_family: int = S2A_BATCH_MIN_EVENTS_PER_FAMILY,
    max_tasks_per_event: int = S2A_BATCH_MAX_TASKS_PER_EVENT,
    max_tasks_per_family: int = S2A_BATCH_MAX_TASKS_PER_FAMILY,
) -> tuple[S2ASelectedTask, ...]:
    """Select an exact, balanced FIRST_PASS batch without consulting any human labels."""

    if target_per_cell <= 0 or expected_families <= 0 or min_events_per_family <= 0:
        raise ValueError("S2-A batch quotas must be positive")
    pool = _flatten(packages)
    if not pool:
        raise ValueError("S2-A batch pool is empty")
    families = sorted({row.family_id for row in pool})
    if len(families) != expected_families:
        raise ValueError(f"S2-A batch requires exactly {expected_families} source families")

    by_family_event: dict[str, dict[str, list[S2ASelectedTask]]] = defaultdict(lambda: defaultdict(list))
    for row in pool:
        by_family_event[row.family_id][row.event_id].append(row)
    for family_id in families:
        if len(by_family_event[family_id]) < min_events_per_family:
            raise ValueError(f"S2-A family {family_id} lacks {min_events_per_family} eligible H-C events")

    selected: dict[str, S2ASelectedTask] = {}
    cell_counts: Counter[tuple[str, str]] = Counter()
    family_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    selected_events_by_family: dict[str, set[str]] = defaultdict(set)

    def can_add(row: S2ASelectedTask) -> bool:
        return (
            row.task_id not in selected
            and cell_counts[row.cell] < target_per_cell
            and family_counts[row.family_id] < max_tasks_per_family
            and event_counts[row.event_id] < max_tasks_per_event
        )

    def add(row: S2ASelectedTask) -> None:
        if not can_add(row):
            raise AssertionError("attempted to add an ineligible S2-A batch row")
        selected[row.task_id] = row
        cell_counts[row.cell] += 1
        family_counts[row.family_id] += 1
        event_counts[row.event_id] += 1
        selected_events_by_family[row.family_id].add(row.event_id)

    # Phase A: force broad event coverage first. This guarantees >=200 distinct events
    # for the frozen 40-family v1 corpus before extra tasks are used to fill strata.
    for family_id in families:
        ranked_events = sorted(
            by_family_event[family_id],
            key=lambda event_id: _digest(f"{S2A_PROTOCOL_VERSION}|coverage-event|{family_id}|{event_id}"),
        )
        for event_id in ranked_events:
            if len(selected_events_by_family[family_id]) >= min_events_per_family:
                break
            candidates = [row for row in by_family_event[family_id][event_id] if can_add(row)]
            if not candidates:
                continue
            candidates.sort(
                key=lambda row: (
                    cell_counts[row.cell],
                    _digest(f"{S2A_PROTOCOL_VERSION}|coverage-task|{row.task_id}"),
                )
            )
            add(candidates[0])
        if len(selected_events_by_family[family_id]) < min_events_per_family:
            raise ValueError(f"S2-A could not satisfy event coverage for {family_id}")

    # Phase B: fill each pair-type x distance cell to the exact frozen quota while
    # minimizing family and event concentration. Old Teacher responses are absent.
    while any(cell_counts[cell] < target_per_cell for cell in _CELLS):
        cell = min(
            (cell for cell in _CELLS if cell_counts[cell] < target_per_cell),
            key=lambda item: (cell_counts[item] / target_per_cell, item),
        )
        candidates = [row for row in pool if row.cell == cell and can_add(row)]
        if not candidates:
            raise ValueError(f"S2-A cannot fill frozen batch cell {cell}")
        candidates.sort(
            key=lambda row: (
                family_counts[row.family_id],
                event_counts[row.event_id],
                _digest(f"{S2A_PROTOCOL_VERSION}|fill|{row.task_id}"),
            )
        )
        add(candidates[0])

    out = tuple(sorted(selected.values(), key=lambda row: row.task_id))
    expected_total = target_per_cell * len(_CELLS)
    if len(out) != expected_total:
        raise AssertionError("S2-A selected batch size mismatch")
    if any(cell_counts[cell] != target_per_cell for cell in _CELLS):
        raise AssertionError("S2-A selected batch cell quota mismatch")
    if len({row.event_id for row in out}) < expected_families * min_events_per_family:
        raise AssertionError("S2-A selected batch event coverage below frozen minimum")
    if len({row.family_id for row in out}) != expected_families:
        raise AssertionError("S2-A selected batch lost a source family")
    return out


def _manifest_for_rows(rows: tuple[S2ASelectedTask, ...], session_id: str) -> dict:
    manifest = {
        "schema": S2A_TEACHER_MANIFEST_SCHEMA,
        "protocol_version": S2A_PROTOCOL_VERSION,
        "provenance": S2A_FIRST_PASS_PROVENANCE,
        "target": "STATIC_STANDARD_FINGERING_NATURALNESS",
        "annotation_blinded": True,
        "source_identity": "withheld",
        "family_identity": "withheld",
        "model_identity": "withheld",
        "model_scores": "withheld",
        "feature_values": "withheld",
        "observed_source_fingering": "withheld",
        "pair_selection_stratum": "withheld",
        "prior_responses": "withheld",
        "session_id": session_id,
        "task_count": len(rows),
        "tasks": [row.task for row in rows],
    }
    manifest["manifest_sha256"] = _canonical_sha(manifest)
    return manifest


def _audit_for_rows(rows: tuple[S2ASelectedTask, ...], session_id: str) -> dict:
    return {
        "schema": S2A_INTERNAL_AUDIT_SCHEMA,
        "protocol_version": S2A_PROTOCOL_VERSION,
        "provenance": S2A_FIRST_PASS_PROVENANCE,
        "teacher_facing": False,
        "label_used_for_pair_sampling": False,
        "observed_source_fingering_used": False,
        "historical_teacher_response_used": False,
        "session_id": session_id,
        "task_count": len(rows),
        "rows": [row.audit for row in rows],
    }


def split_sessions(
    selected: Iterable[S2ASelectedTask],
    *,
    session_count: int = S2A_BATCH_SESSION_COUNT,
) -> tuple[tuple[dict, dict], ...]:
    rows = tuple(selected)
    if session_count <= 0:
        raise ValueError("session_count must be positive")
    by_cell: dict[tuple[str, str], list[S2ASelectedTask]] = defaultdict(list)
    for row in rows:
        by_cell[row.cell].append(row)
    counts = {cell: len(by_cell[cell]) for cell in _CELLS}
    if len(set(counts.values())) != 1:
        raise ValueError("S2-A session splitter requires an exactly cell-balanced batch")
    per_cell = next(iter(counts.values()))
    if per_cell % session_count:
        raise ValueError("S2-A per-cell batch size must divide evenly across sessions")

    sessions: list[list[S2ASelectedTask]] = [[] for _ in range(session_count)]
    for cell in _CELLS:
        ordered = sorted(
            by_cell[cell],
            key=lambda row: _digest(f"{S2A_PROTOCOL_VERSION}|session-order|{row.task_id}"),
        )
        for index, row in enumerate(ordered):
            sessions[index % session_count].append(row)

    output: list[tuple[dict, dict]] = []
    for index, session_rows in enumerate(sessions, start=1):
        frozen = tuple(sorted(session_rows, key=lambda row: _digest(f"session-task|{row.task_id}")))
        session_id = f"S2A_BATCH01_SESSION_{index:02d}"
        manifest = _manifest_for_rows(frozen, session_id)
        audit = _audit_for_rows(frozen, session_id)
        if set(row["task_id"] for row in manifest["tasks"]) != set(row["task_id"] for row in audit["rows"]):
            raise AssertionError("S2-A session manifest/audit mismatch")
        output.append((manifest, audit))
    return tuple(output)


def batch_summary(selected: Iterable[S2ASelectedTask], sessions: Iterable[tuple[dict, dict]]) -> dict:
    rows = tuple(selected)
    session_rows = tuple(sessions)
    cell_counts = Counter(row.cell for row in rows)
    pair_counts = Counter(row.cell[0] for row in rows)
    distance_counts = Counter(row.cell[1] for row in rows)
    family_counts = Counter(row.family_id for row in rows)
    return {
        "schema": S2A_BATCH_SCHEMA,
        "protocol_version": S2A_PROTOCOL_VERSION,
        "provenance": S2A_FIRST_PASS_PROVENANCE,
        "status": "READY_FOR_BLIND_FIRST_PASS_COLLECTION",
        "historical_teacher_responses_reused": False,
        "source_family_identities_reused_as_label_free_music_sources": True,
        "task_count": len(rows),
        "family_count": len(family_counts),
        "event_count": len({row.event_id for row in rows}),
        "pair_type_counts": dict(sorted(pair_counts.items())),
        "distance_stratum_counts": dict(sorted(distance_counts.items())),
        "cell_counts": {f"{key[0]}|{key[1]}": cell_counts[key] for key in _CELLS},
        "min_tasks_per_family": min(family_counts.values()),
        "max_tasks_per_family": max(family_counts.values()),
        "session_count": len(session_rows),
        "session_task_counts": [manifest["task_count"] for manifest, _ in session_rows],
        "session_manifest_sha256": [manifest["manifest_sha256"] for manifest, _ in session_rows],
        "checkpoint_retention_authorized": False,
        "shadow_or_production_authorized": False,
    }


def render_teacher_html(manifest: dict) -> str:
    """Render a self-contained local annotation page without internal audit metadata."""

    if manifest.get("schema") != S2A_TEACHER_MANIFEST_SCHEMA:
        raise ValueError("unexpected S2-A teacher manifest schema")
    if manifest.get("annotation_blinded") is not True:
        raise ValueError("S2-A HTML requires a blind teacher manifest")
    if "family_id" in json.dumps(manifest, sort_keys=True):
        raise ValueError("S2-A teacher manifest leaked family identity")

    embedded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(str(manifest.get("session_id", "S2-A Teacher Session")))
    template = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f5f6f8;color:#15171a}header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:12px;z-index:5}.wrap{max-width:900px;margin:auto}.progress{height:8px;background:#e4e7eb;border-radius:8px;overflow:hidden;margin-top:8px}.bar{height:100%;background:#222;width:0}main{max-width:900px;margin:20px auto;padding:0 12px}.card{background:#fff;border:1px solid #d9dde3;border-radius:14px;padding:16px}.options{display:grid;grid-template-columns:1fr 1fr;gap:12px}.option{border:2px solid #ddd;border-radius:12px;padding:12px}.option h2{margin-top:0}.placement{padding:5px 0;border-top:1px solid #eee}.barre{font-size:13px;margin-top:8px;color:#505866}.buttons{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:16px}button{border:1px solid #cbd0d6;background:#fff;border-radius:10px;padding:12px;font-size:15px;font-weight:650}button.active,button.primary{background:#20252b;color:#fff}.nav{display:flex;justify-content:space-between;gap:8px;margin-top:14px;flex-wrap:wrap}.note{font-size:13px;color:#626b76}.finish{margin-top:18px;padding-top:14px;border-top:1px solid #eee}.hidden{display:none}@media(max-width:720px){.options,.buttons{grid-template-columns:1fr}}
</style></head><body><header><div class="wrap"><strong id="session"></strong> · <span id="count"></span><div class="progress"><div class="bar" id="bar"></div></div></div></header>
<main><div class="card"><h1 id="taskNo"></h1><div id="pitches" class="note"></div><p><strong>Yalnız sol el açısından, normal gitar tekniğinde hangi tam parmaklama daha doğal/rahat?</strong></p><div class="options"><div class="option"><h2>A</h2><div id="A"></div></div><div class="option"><h2>B</h2><div id="B"></div></div></div><div class="buttons"><button id="btnA" onclick="choose('A')">A daha rahat</button><button id="btnB" onclick="choose('B')">B daha rahat</button><button id="btnU" onclick="choose('EQUAL_OR_UNSURE')">Eşit / Emin değilim</button></div><div class="nav"><button onclick="move(-1)">← Önceki</button><button onclick="nextMissing()">Sonraki cevapsız</button><button onclick="move(1)">Sonraki →</button></div><div id="finish" class="finish hidden"><strong>Tamamlandı.</strong><p class="note">JSON'u kaydet ve ChatGPT'ye yükle. Bu dosya yalnız bu oturumun yeni S2-A cevaplarını içerir.</p><button class="primary" onclick="saveJson()">Cevap JSON'unu kaydet</button></div></div></main>
<script>const MANIFEST=__MANIFEST__;const tasks=MANIFEST.tasks;const storageKey='st_guitar_s2a_'+MANIFEST.manifest_sha256;let current=0;let answers={};try{answers=JSON.parse(localStorage.getItem(storageKey)||'{}')}catch(_){answers={}}
function esc(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function optHtml(o){let s=o.placements.map(p=>`<div class="placement">MIDI ${p.pitch_midi} · tel ${p.string} · perde ${p.fret} · <strong>parmak ${p.finger}</strong></div>`).join('');if(o.barres&&o.barres.length)s+=o.barres.map(b=>`<div class="barre"><strong>Barre:</strong> parmak ${b.finger}, perde ${b.fret}, tel ${b.span_start_string}–${b.span_end_string}</div>`).join('');return s}
function save(){localStorage.setItem(storageKey,JSON.stringify(answers))}function done(){return Object.keys(answers).length}function render(){const t=tasks[current];document.getElementById('session').textContent=MANIFEST.session_id;document.getElementById('count').textContent=`${done()}/${tasks.length}`;document.getElementById('bar').style.width=`${100*done()/tasks.length}%`;document.getElementById('taskNo').textContent=`Görev ${current+1} / ${tasks.length}`;document.getElementById('pitches').textContent='Sesler (MIDI): '+t.pitches_midi.join(', ');for(const o of t.options)document.getElementById(o.option_id).innerHTML=optHtml(o);for(const [id,v] of [['btnA','A'],['btnB','B'],['btnU','EQUAL_OR_UNSURE']])document.getElementById(id).classList.toggle('active',answers[t.task_id]===v);document.getElementById('finish').classList.toggle('hidden',done()!==tasks.length)}function choose(v){answers[tasks[current].task_id]=v;save();if(current<tasks.length-1)current++;render()}function move(d){current=Math.max(0,Math.min(tasks.length-1,current+d));render()}function nextMissing(){for(let k=1;k<=tasks.length;k++){const i=(current+k)%tasks.length;if(!answers[tasks[i].task_id]){current=i;render();return}}render()}function saveJson(){if(done()!==tasks.length){alert('Önce tüm görevleri cevapla.');return}const payload={schema:'st-guitar-s2a-choice-export-v1',provenance:MANIFEST.provenance,annotation_blinded:true,annotator_id:'teacher_001',collected_at_utc:new Date().toISOString(),session_id:MANIFEST.session_id,manifest_sha256:MANIFEST.manifest_sha256,choices:tasks.map(t=>({task_id:t.task_id,response:answers[t.task_id]}))};const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`ST_Guitar_${MANIFEST.session_id}_choices.json`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}document.addEventListener('keydown',e=>{const k=e.key.toLowerCase();if(k==='a')choose('A');else if(k==='b')choose('B');else if(k==='u')choose('EQUAL_OR_UNSURE');else if(e.key==='ArrowLeft')move(-1);else if(e.key==='ArrowRight')move(1)});render();</script></body></html>'''
    return template.replace("__TITLE__", title).replace("__MANIFEST__", embedded)
