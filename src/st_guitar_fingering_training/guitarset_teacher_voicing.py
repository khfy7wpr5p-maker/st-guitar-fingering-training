from __future__ import annotations

from hashlib import sha256
import html
import json
from typing import Iterable

from .dataset import valid_chord_voicings
from .guitarset_split import ROLE_DEVELOPMENT, build_split_contract, source_role
from .guitarset_voicing_prereg import (
    GUITARSET_SOURCE_ARCHIVE_SHA256,
    GUITARSET_VOICING_MAX_FRET,
)

TEACHER_VOICING_PILOT_VERSION = "GUITARSET-TEACHER-VOICING-PILOT.v1"
TEACHER_VOICING_TASK_SCHEMA = "st-guitar-guitarset-teacher-voicing-task-v1"
TEACHER_VOICING_MANIFEST_SCHEMA = "st-guitar-guitarset-teacher-voicing-manifest-v1"
TEACHER_VOICING_EXPORT_SCHEMA = "st-guitar-guitarset-teacher-voicing-export-v1"
TEACHER_VOICING_AUDIT_SCHEMA = "st-guitar-guitarset-teacher-voicing-audit-v1"

DECISION_SELECT_OPTION = "SELECT_OPTION"
DECISION_EQUAL_OR_UNSURE = "EQUAL_OR_UNSURE"
DECISION_MANUAL_VOICING = "MANUAL_VOICING"
DECISION_REJECT_TASK = "REJECT_TASK"
ALLOWED_DECISIONS = (
    DECISION_SELECT_OPTION,
    DECISION_EQUAL_OR_UNSURE,
    DECISION_MANUAL_VOICING,
    DECISION_REJECT_TASK,
)

STANDARD_TUNING_BY_STRING = (64, 59, 55, 50, 45, 40)


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def canonical_candidate(placements: Iterable[Iterable[int]]) -> tuple[tuple[int, int, int], ...]:
    rows = tuple(sorted((int(pitch), int(string), int(fret)) for pitch, string, fret in placements))
    if len(rows) < 2:
        raise ValueError("teacher voicing candidate requires at least two notes")
    if len({string for _, string, _ in rows}) != len(rows):
        raise ValueError("teacher voicing candidate reuses a string")
    if any(not 1 <= string <= 6 for _, string, _ in rows):
        raise ValueError("teacher voicing candidate string out of range")
    if any(not 0 <= fret <= GUITARSET_VOICING_MAX_FRET for _, _, fret in rows):
        raise ValueError("teacher voicing candidate fret out of range")
    return rows


def candidate_id(placements: Iterable[Iterable[int]]) -> str:
    rows = canonical_candidate(placements)
    return "tvpv1-candidate-sha256:" + _canonical_sha256(rows)


def exact_candidates(
    pitches_midi: Iterable[int],
    tuning: tuple[int, ...] = STANDARD_TUNING_BY_STRING,
) -> tuple[tuple[tuple[int, int, int], ...], ...]:
    pitches = tuple(sorted(int(value) for value in pitches_midi))
    if len(tuning) != 6:
        raise ValueError("teacher voicing pilot supports six-string standard tuning only")
    candidates = tuple(
        candidate
        for candidate in valid_chord_voicings(pitches, tuple(int(value) for value in tuning))
        if candidate and max(fret for _, _, fret in candidate) <= GUITARSET_VOICING_MAX_FRET
    )
    return tuple(sorted(candidates))


def semantic_fingerprint(
    pitches_midi: Iterable[int],
    tuning: tuple[int, ...] = STANDARD_TUNING_BY_STRING,
) -> str:
    candidates = exact_candidates(pitches_midi, tuning)
    if len(candidates) < 2:
        raise ValueError("teacher voicing pilot requires an ambiguous physical event")
    payload = {
        "version": TEACHER_VOICING_PILOT_VERSION,
        "pitches_midi": sorted(int(value) for value in pitches_midi),
        "candidate_ids": sorted(candidate_id(item) for item in candidates),
    }
    return "tvpv1-semantic-sha256:" + _canonical_sha256(payload)


def build_teacher_voicing_task(
    *,
    event_id: str,
    pitches_midi: Iterable[int],
    observed_placements: Iterable[Iterable[int]],
    tuning: tuple[int, ...] = STANDARD_TUNING_BY_STRING,
    option_cap: int = 6,
) -> tuple[dict, dict]:
    if not event_id:
        raise ValueError("teacher voicing event_id is required")
    if not 2 <= option_cap <= 12:
        raise ValueError("teacher voicing option_cap must be in [2, 12]")

    pitches = tuple(sorted(int(value) for value in pitches_midi))
    candidates = exact_candidates(pitches, tuning)
    if len(candidates) < 2:
        raise ValueError("teacher voicing pilot requires at least two physical candidates")

    observed = canonical_candidate(observed_placements)
    if tuple(sorted(pitch for pitch, _, _ in observed)) != pitches:
        raise ValueError("observed voicing pitch multiset mismatch")
    if observed not in candidates:
        raise ValueError("observed voicing missing from exact physical candidate set")

    semantic_id = semantic_fingerprint(pitches, tuning)
    task_id = "tvpv1-task-sha256:" + _canonical_sha256(
        {
            "version": TEACHER_VOICING_PILOT_VERSION,
            "event_id": event_id,
            "semantic_fingerprint": semantic_id,
        }
    )

    alternatives = [item for item in candidates if item != observed]
    alternatives.sort(
        key=lambda item: (
            sha256(
                f"{TEACHER_VOICING_PILOT_VERSION}|ALT|{task_id}|{candidate_id(item)}".encode("utf-8")
            ).hexdigest(),
            item,
        )
    )
    shown = [observed, *alternatives[: max(0, option_cap - 1)]]
    shown.sort(
        key=lambda item: (
            sha256(
                f"{TEACHER_VOICING_PILOT_VERSION}|BLIND|{task_id}|{candidate_id(item)}".encode("utf-8")
            ).hexdigest(),
            item,
        )
    )

    options = [
        {
            "candidate_id": candidate_id(item),
            "placements": [
                {"pitch_midi": pitch, "string": string, "fret": fret}
                for pitch, string, fret in item
            ],
        }
        for item in shown
    ]

    task = {
        "schema": TEACHER_VOICING_TASK_SCHEMA,
        "protocol_version": TEACHER_VOICING_PILOT_VERSION,
        "task_id": task_id,
        "semantic_fingerprint": semantic_id,
        "pitches_midi": list(pitches),
        "option_count": len(options),
        "full_candidate_count": len(candidates),
        "options": options,
        "allowed_decisions": list(ALLOWED_DECISIONS),
        "manual_entry_format": "comma-separated string:fret pairs, e.g. 6:0,5:2,4:2,3:0",
        "source_identity_withheld": True,
        "observed_answer_withheld": True,
        "model_scores_withheld": True,
    }
    audit = {
        "task_id": task_id,
        "semantic_fingerprint": semantic_id,
        "event_id": event_id,
        "observed_candidate_id": candidate_id(observed),
        "observed_placements": [
            {"pitch_midi": pitch, "string": string, "fret": fret}
            for pitch, string, fret in observed
        ],
        "shown_candidate_ids": [row["candidate_id"] for row in options],
        "full_candidate_count": len(candidates),
    }
    return task, audit


def build_teacher_voicing_manifest(
    *,
    batch_id: str,
    session_id: str,
    tasks: Iterable[dict],
) -> dict:
    rows = tuple(tasks)
    if not batch_id or not session_id:
        raise ValueError("teacher voicing batch/session identity required")
    if not rows:
        raise ValueError("teacher voicing manifest cannot be empty")
    if any(row.get("schema") != TEACHER_VOICING_TASK_SCHEMA for row in rows):
        raise ValueError("teacher voicing manifest contains wrong task schema")
    task_ids = [str(row["task_id"]) for row in rows]
    semantic_ids = [str(row["semantic_fingerprint"]) for row in rows]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("teacher voicing manifest contains duplicate task IDs")
    if len(semantic_ids) != len(set(semantic_ids)):
        raise ValueError("teacher voicing manifest contains duplicate semantic tasks")

    manifest = {
        "schema": TEACHER_VOICING_MANIFEST_SCHEMA,
        "protocol_version": TEACHER_VOICING_PILOT_VERSION,
        "status": "READY_FOR_DIAGNOSTIC_TEACHER_VOICING_PILOT",
        "batch_id": batch_id,
        "session_id": session_id,
        "annotator_id": "teacher_001",
        "annotation_blinded": True,
        "source_identity": "withheld",
        "observed_guitarist_answer": "withheld",
        "model_output": "withheld",
        "baseline_output": "withheld",
        "task_count": len(rows),
        "tasks": list(rows),
        "diagnostic_only_never_training": True,
        "training_authorized": False,
        "validation_access_authorized": False,
        "final_access_authorized": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
    }
    manifest["manifest_sha256"] = _canonical_sha256(manifest)
    return manifest


def parse_manual_voicing(
    text: str,
    *,
    pitches_midi: Iterable[int],
    tuning: tuple[int, ...] = STANDARD_TUNING_BY_STRING,
) -> tuple[tuple[int, int, int], ...]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("manual voicing is empty")
    if len(tuning) != 6:
        raise ValueError("manual voicing requires six-string tuning")
    placements: list[tuple[int, int, int]] = []
    seen_strings: set[int] = set()
    for raw_token in text.split(","):
        token = raw_token.strip()
        if token.count(":") != 1:
            raise ValueError("manual voicing token must be string:fret")
        raw_string, raw_fret = token.split(":", 1)
        try:
            string = int(raw_string)
            fret = int(raw_fret)
        except ValueError as exc:
            raise ValueError("manual voicing string/fret must be integers") from exc
        if not 1 <= string <= 6:
            raise ValueError("manual voicing string out of range")
        if not 0 <= fret <= GUITARSET_VOICING_MAX_FRET:
            raise ValueError("manual voicing fret out of range")
        if string in seen_strings:
            raise ValueError("manual voicing reuses a string")
        seen_strings.add(string)
        midi = int(tuning[string - 1]) + fret
        placements.append((midi, string, fret))

    candidate = canonical_candidate(placements)
    pitches = tuple(sorted(int(value) for value in pitches_midi))
    if tuple(sorted(pitch for pitch, _, _ in candidate)) != pitches:
        raise ValueError("manual voicing does not preserve the task pitch multiset")
    if candidate not in exact_candidates(pitches, tuning):
        raise ValueError("manual voicing is not an exact physical candidate")
    return candidate


def validate_teacher_voicing_export(payload: dict, manifest: dict) -> dict:
    if payload.get("schema") != TEACHER_VOICING_EXPORT_SCHEMA:
        raise ValueError("unexpected teacher voicing export schema")
    if payload.get("protocol_version") != TEACHER_VOICING_PILOT_VERSION:
        raise ValueError("teacher voicing export protocol drift")
    if payload.get("manifest_sha256") != manifest.get("manifest_sha256"):
        raise ValueError("teacher voicing export manifest mismatch")
    if payload.get("annotator_id") != manifest.get("annotator_id"):
        raise ValueError("teacher voicing annotator mismatch")

    known = {row["task_id"]: row for row in manifest.get("tasks", [])}
    decisions = payload.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(known):
        raise ValueError("teacher voicing export must cover every task exactly once")

    seen: set[str] = set()
    counts = {decision: 0 for decision in ALLOWED_DECISIONS}
    manual_candidates: list[dict] = []
    for row in decisions:
        task_id = str(row.get("task_id", ""))
        if task_id not in known or task_id in seen:
            raise ValueError("teacher voicing export has unknown or duplicate task")
        seen.add(task_id)
        task = known[task_id]
        if row.get("semantic_fingerprint") != task.get("semantic_fingerprint"):
            raise ValueError("teacher voicing semantic fingerprint mismatch")

        decision = row.get("decision")
        if decision not in ALLOWED_DECISIONS:
            raise ValueError("teacher voicing decision is invalid")
        selected_id = row.get("selected_candidate_id")
        manual_text = row.get("manual_voicing")
        option_ids = {item["candidate_id"] for item in task["options"]}

        if decision == DECISION_SELECT_OPTION:
            if selected_id not in option_ids or manual_text not in (None, ""):
                raise ValueError("SELECT_OPTION must reference exactly one shown candidate")
        elif decision == DECISION_MANUAL_VOICING:
            if selected_id is not None:
                raise ValueError("MANUAL_VOICING cannot carry a shown candidate ID")
            manual = parse_manual_voicing(str(manual_text or ""), pitches_midi=task["pitches_midi"])
            manual_candidates.append(
                {"task_id": task_id, "candidate_id": candidate_id(manual)}
            )
        else:
            if selected_id is not None or manual_text not in (None, ""):
                raise ValueError(f"{decision} cannot carry a candidate/manual voicing")
        counts[decision] += 1

    if seen != set(known):
        raise ValueError("teacher voicing export is incomplete")
    return {
        "task_count": len(decisions),
        "decision_counts": counts,
        "manual_candidates": manual_candidates,
        "diagnostic_only_never_training": True,
        "training_authorized": False,
    }


def development_members_from_archive_metadata(
    source_members: Iterable[str],
    *,
    source_archive_sha256: str,
) -> tuple[str, ...]:
    if source_archive_sha256 != GUITARSET_SOURCE_ARCHIVE_SHA256:
        raise ValueError("teacher voicing pilot source archive SHA mismatch")
    members = tuple(sorted(source_members))
    contract = build_split_contract(members, source_archive_sha256=source_archive_sha256)
    selected = tuple(
        member for member in members
        if source_role(member, contract) == ROLE_DEVELOPMENT
    )
    if len(selected) != 120:
        raise AssertionError("teacher voicing pilot expected exactly 120 DEVELOPMENT recordings")
    return selected


def render_teacher_voicing_html(manifest: dict) -> str:
    if manifest.get("schema") != TEACHER_VOICING_MANIFEST_SCHEMA:
        raise ValueError("unexpected teacher voicing manifest schema")
    if manifest.get("annotation_blinded") is not True:
        raise ValueError("teacher voicing HTML requires blind manifest")
    if manifest.get("diagnostic_only_never_training") is not True:
        raise ValueError("teacher voicing HTML requires diagnostic-only manifest")

    embedded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(str(manifest.get("session_id", "Teacher Voicing Pilot")))
    template = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light}
*{box-sizing:border-box}body{margin:0;background:#f5f6f8;color:#15171a}
header{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid #d8dde5;padding:10px}
.wrap,main{max-width:980px;margin:auto}main{padding:16px 10px 40px}
.card{background:#fff;border:1px solid #d8dde5;border-radius:14px;padding:15px}
.muted{color:#68717d;font-size:13px}.options{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;margin-top:14px}
.option{border:2px solid #d8dde5;border-radius:12px;padding:10px;background:#fff}.option.selected{border-color:#111;background:#f0f2f4}
.optTitle{font-weight:800;font-size:18px;margin-bottom:7px}.strings{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:14px;line-height:1.55}
button,input,textarea{font:inherit;border:1px solid #bfc6cf;border-radius:10px;padding:10px;background:#fff}
button{font-weight:700}.primary{background:#171a1f;color:#fff}.danger{border-color:#a32929}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.manual{margin-top:12px;padding:10px;background:#f6f7f9;border-radius:10px}
.manual input{width:100%}.nav{display:flex;gap:8px;margin-top:14px}.nav button{flex:1}
.progress{height:7px;background:#e5e8ed;border-radius:8px;overflow:hidden;margin-top:6px}.bar{height:100%;background:#1b1f24;width:0}
.export{margin-top:16px}.export textarea{width:100%;min-height:180px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}
.hidden{display:none}@media(max-width:640px){.controls button,.nav button{width:100%}}
</style></head><body>
<header><div class="wrap"><strong id="session"></strong> · <span id="progressText"></span>
<div class="progress"><div class="bar" id="bar"></div></div></div></header>
<main><div class="card">
<h2 id="taskTitle"></h2><div id="pitches" class="muted"></div>
<p><strong>Bu sesleri gitarda sen hangi tel-perde düzeniyle çalardın?</strong> Gözlenen gitarist, model ve baseline cevabı gizlidir.</p>
<div id="options" class="options"></div>
<div class="controls">
<button onclick="markEqual()">Eşit / Emin değilim</button>
<button onclick="toggleManual()">Hiçbiri — elle gir</button>
<button class="danger" onclick="markReject()">Görev sorunlu — reddet</button>
</div>
<div id="manualBox" class="manual hidden">
<div class="muted">Örnek: <code>6:0,5:2,4:2,3:0</code></div>
<input id="manualInput" autocomplete="off" placeholder="6:0,5:2,4:2,3:0">
<button class="primary" style="margin-top:8px" onclick="saveManual()">Elle girdiğimi seç</button>
</div>
<div class="nav"><button onclick="move(-1)">← Önceki</button><button onclick="move(1)">Sonraki →</button></div>
<div id="exportBox" class="export hidden">
<h3>Cevaplar hazır</h3>
<p class="muted">Tarayıcı cevapları otomatik saklar. JSON'u kopyalayabilir veya dosya olarak indirebilirsin.</p>
<textarea id="exportText" readonly></textarea>
<div class="controls"><button onclick="copyExport()">JSON'u kopyala</button><button class="primary" onclick="downloadExport()">JSON dosyası indir</button></div>
</div>
</div></main>
<script>
const manifest=__MANIFEST__;
const storageKey="ST_GUITAR_TVPV1:"+manifest.manifest_sha256;
let index=0;
let decisions={};
try{decisions=JSON.parse(localStorage.getItem(storageKey)||"{}")||{}}catch(e){decisions={}}
const labels=["A","B","C","D","E","F","G","H","I","J","K","L"];
function fretMap(option){const map={1:"x",2:"x",3:"x",4:"x",5:"x",6:"x"};option.placements.forEach(p=>map[p.string]=String(p.fret));return map}
function renderOption(option,i,task){
 const d=decisions[task.task_id]||{};
 const selected=d.decision==="SELECT_OPTION"&&d.selected_candidate_id===option.candidate_id;
 const m=fretMap(option);
 return `<button class="option ${selected?"selected":""}" onclick="selectOption('${option.candidate_id}')">
 <div class="optTitle">${labels[i]||String(i+1)}</div><div class="strings">
 1(e): ${m[1]}<br>2(B): ${m[2]}<br>3(G): ${m[3]}<br>4(D): ${m[4]}<br>5(A): ${m[5]}<br>6(E): ${m[6]}
 </div></button>`;
}
function save(d){const task=manifest.tasks[index];decisions[task.task_id]={task_id:task.task_id,semantic_fingerprint:task.semantic_fingerprint,selected_candidate_id:null,manual_voicing:null,...d};localStorage.setItem(storageKey,JSON.stringify(decisions));render()}
function selectOption(id){save({decision:"SELECT_OPTION",selected_candidate_id:id})}
function markEqual(){save({decision:"EQUAL_OR_UNSURE"})}
function markReject(){save({decision:"REJECT_TASK"})}
function toggleManual(){document.getElementById("manualBox").classList.toggle("hidden")}
function saveManual(){const value=document.getElementById("manualInput").value.trim();if(!value){alert("Tel:perde girişi boş.");return}save({decision:"MANUAL_VOICING",manual_voicing:value})}
function move(delta){index=Math.max(0,Math.min(manifest.tasks.length-1,index+delta));render()}
function exportPayload(){
 return {schema:"st-guitar-guitarset-teacher-voicing-export-v1",protocol_version:"GUITARSET-TEACHER-VOICING-PILOT.v1",manifest_sha256:manifest.manifest_sha256,annotator_id:manifest.annotator_id,decisions:manifest.tasks.map(t=>decisions[t.task_id]).filter(Boolean)};
}
function updateExport(){
 const complete=manifest.tasks.every(t=>decisions[t.task_id]);
 const box=document.getElementById("exportBox");box.classList.toggle("hidden",!complete);
 if(complete)document.getElementById("exportText").value=JSON.stringify(exportPayload(),null,2);
}
async function copyExport(){const text=document.getElementById("exportText").value;try{await navigator.clipboard.writeText(text);alert("JSON kopyalandı.")}catch(e){document.getElementById("exportText").select();document.execCommand("copy");alert("JSON kopyalandı.")}}
function downloadExport(){const text=document.getElementById("exportText").value;const blob=new Blob([text],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=manifest.session_id+"_choices.json";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
function render(){
 const task=manifest.tasks[index];document.getElementById("session").textContent=manifest.session_id;
 const done=manifest.tasks.filter(t=>decisions[t.task_id]).length;
 document.getElementById("progressText").textContent=`${index+1}/${manifest.tasks.length} · cevaplanan ${done}`;
 document.getElementById("bar").style.width=(done/manifest.tasks.length*100)+"%";
 document.getElementById("taskTitle").textContent=`Görev ${index+1}`;
 document.getElementById("pitches").textContent=`MIDI sesleri: ${task.pitches_midi.join(", ")} · toplam fiziksel aday: ${task.full_candidate_count}`;
 document.getElementById("options").innerHTML=task.options.map((o,i)=>renderOption(o,i,task)).join("");
 const d=decisions[task.task_id]||{};document.getElementById("manualInput").value=d.manual_voicing||"";
 updateExport();
}
render();
</script></body></html>'''
    return template.replace("__TITLE__", title).replace("__MANIFEST__", embedded)
