from __future__ import annotations

from collections import Counter
from hashlib import sha256
import html
import json
from typing import Iterable

from .finger_assignments import StandardFingering, generate_standard_fingerings


TCV1_PROTOCOL_VERSION = "TEACHER_CORRECTION.v1"
TCV1_TASK_SCHEMA = "st-guitar-teacher-correction-v1-task"
TCV1_MANIFEST_SCHEMA = "st-guitar-teacher-correction-v1-manifest"
TCV1_EXPORT_SCHEMA = "st-guitar-teacher-correction-v1-export-v1"
TCV1_QUARANTINE_SCHEMA = "st-guitar-teacher-correction-v1-permanent-quarantine"

TCV1_DECISIONS = ("ACCEPTED_PROPOSAL", "CORRECTED", "REJECTED_PERMANENT")


def _canonical_sha(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def _assignment_payload(assignment: StandardFingering) -> dict:
    return {
        "assignment_id": assignment.assignment_id,
        "placements": [
            {
                "pitch_midi": int(pitch),
                "string": int(string),
                "fret": int(fret),
                "finger": int(finger),
            }
            for pitch, string, fret, finger in assignment.placements
        ],
        "barres": [
            {
                "finger": int(finger),
                "fret": int(fret),
                "span_start_string": int(span_start),
                "span_end_string": int(span_end),
            }
            for finger, fret, span_start, span_end in assignment.barres
        ],
    }


def _display_order_key(assignment: StandardFingering) -> tuple:
    fretted = [fret for _, _, fret, _ in assignment.placements if fret > 0]
    min_fret = min(fretted) if fretted else 0
    max_fret = max(fretted) if fretted else 0
    span = max_fret - min_fret if fretted else 0
    open_count = sum(1 for _, _, fret, _ in assignment.placements if fret == 0)
    distinct_fingers = len({finger for _, _, fret, finger in assignment.placements if fret > 0})
    placements = tuple((string, fret, finger, pitch) for pitch, string, fret, finger in assignment.placements)
    return (span, min_fret, max_fret, -open_count, distinct_fingers, placements, assignment.assignment_id)


def _event_assignment_set(pitches_midi: tuple[int, ...], tuning: tuple[int, ...]) -> tuple[StandardFingering, ...]:
    generated = generate_standard_fingerings(pitches_midi, tuning)
    assignments: dict[str, StandardFingering] = {}
    for candidate in generated.candidates:
        for assignment in candidate.assignments:
            existing = assignments.get(assignment.assignment_id)
            if existing is not None and existing != assignment:
                raise AssertionError("Teacher Correction assignment ID collision")
            assignments[assignment.assignment_id] = assignment
    ordered = tuple(sorted(assignments.values(), key=_display_order_key))
    if len(ordered) < 2:
        raise ValueError("Teacher Correction event needs at least two H-C assignments")
    return ordered


def task_fingerprint(*, event_id: str, assignment_ids: Iterable[str]) -> str:
    ids = tuple(sorted(str(value) for value in assignment_ids))
    if not event_id or len(ids) < 2 or len(ids) != len(set(ids)):
        raise ValueError("Teacher Correction fingerprint requires one event and unique assignments")
    return "sha256:" + sha256(
        f"{TCV1_PROTOCOL_VERSION}|{event_id}|{'|'.join(ids)}".encode("utf-8")
    ).hexdigest()


def build_teacher_correction_task(
    *,
    event_id: str,
    pitches_midi: tuple[int, ...],
    tuning: tuple[int, ...],
) -> dict:
    pitches = tuple(sorted(int(value) for value in pitches_midi))
    tuning = tuple(int(value) for value in tuning)
    assignments = _event_assignment_set(pitches, tuning)
    assignment_ids = tuple(item.assignment_id for item in assignments)
    fingerprint = task_fingerprint(event_id=event_id, assignment_ids=assignment_ids)
    task_id = "tcv1-task-sha256:" + sha256(
        f"{TCV1_PROTOCOL_VERSION}|{fingerprint}".encode("utf-8")
    ).hexdigest()
    return {
        "schema": TCV1_TASK_SCHEMA,
        "protocol_version": TCV1_PROTOCOL_VERSION,
        "task_id": task_id,
        "task_fingerprint": fingerprint,
        "pitches_midi": list(pitches),
        "tuning": list(tuning),
        "solution_count": len(assignments),
        "display_order_policy": "UI_ONLY_COMPACT_GEOMETRY_ORDER_NOT_A_LABEL",
        "initial_assignment_id": assignments[0].assignment_id,
        "solutions": [_assignment_payload(item) for item in assignments],
        "allowed_decisions": list(TCV1_DECISIONS),
    }


def _verify_quarantine(quarantine: dict) -> str:
    if quarantine.get("schema") != TCV1_QUARANTINE_SCHEMA:
        raise ValueError("unexpected Teacher Correction quarantine schema")
    if quarantine.get("protocol_version") != TCV1_PROTOCOL_VERSION:
        raise ValueError("Teacher Correction quarantine protocol drift")
    if quarantine.get("status") != "ACTIVE":
        raise ValueError("Teacher Correction quarantine must be ACTIVE")
    stored = str(quarantine.get("manifest_sha256", ""))
    body = dict(quarantine)
    body.pop("manifest_sha256", None)
    if _canonical_sha(body) != stored:
        raise ValueError("Teacher Correction quarantine manifest SHA mismatch")
    task_ids = quarantine.get("rejected_task_ids")
    fingerprints = quarantine.get("rejected_task_fingerprints")
    if not isinstance(task_ids, list) or not isinstance(fingerprints, list):
        raise ValueError("Teacher Correction quarantine lists are missing")
    if len(task_ids) != len(set(task_ids)) or len(fingerprints) != len(set(fingerprints)):
        raise ValueError("Teacher Correction quarantine contains duplicates")
    return stored


def filter_quarantined_tasks(tasks: Iterable[dict], quarantine: dict) -> tuple[dict, ...]:
    _verify_quarantine(quarantine)
    rejected_ids = set(quarantine["rejected_task_ids"])
    rejected_fingerprints = set(quarantine["rejected_task_fingerprints"])
    clean = []
    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()
    for task in tasks:
        task_id = str(task.get("task_id", ""))
        fingerprint = str(task.get("task_fingerprint", ""))
        if not task_id or not fingerprint:
            raise ValueError("Teacher Correction task identity missing")
        if task_id in rejected_ids or fingerprint in rejected_fingerprints:
            continue
        if task_id in seen_ids or fingerprint in seen_fingerprints:
            raise ValueError("Teacher Correction duplicate task or fingerprint")
        seen_ids.add(task_id)
        seen_fingerprints.add(fingerprint)
        clean.append(task)
    return tuple(clean)


def build_teacher_correction_manifest(
    *,
    batch_id: str,
    session_id: str,
    tasks: Iterable[dict],
    quarantine: dict,
) -> dict:
    quarantine_sha = _verify_quarantine(quarantine)
    rows = tuple(tasks)
    if not rows:
        raise ValueError("Teacher Correction manifest cannot be empty")
    if any(row.get("schema") != TCV1_TASK_SCHEMA for row in rows):
        raise ValueError("Teacher Correction manifest contains wrong task schema")
    manifest = {
        "schema": TCV1_MANIFEST_SCHEMA,
        "protocol_version": TCV1_PROTOCOL_VERSION,
        "batch_id": batch_id,
        "session_id": session_id,
        "status": "READY_FOR_TEACHER_CORRECTION",
        "annotation_blinded": True,
        "source_identity": "withheld",
        "family_identity": "withheld",
        "historical_teacher_responses_used": False,
        "model_scores_used": False,
        "quarantine_manifest_sha256": quarantine_sha,
        "task_count": len(rows),
        "tasks": list(rows),
    }
    manifest["manifest_sha256"] = _canonical_sha(manifest)
    return manifest


def validate_teacher_correction_export(payload: dict, manifest: dict) -> dict:
    if payload.get("schema") != TCV1_EXPORT_SCHEMA:
        raise ValueError("unexpected Teacher Correction export schema")
    if payload.get("protocol_version") != TCV1_PROTOCOL_VERSION:
        raise ValueError("Teacher Correction export protocol drift")
    if payload.get("manifest_sha256") != manifest.get("manifest_sha256"):
        raise ValueError("Teacher Correction export manifest mismatch")
    if payload.get("annotator_id") != "teacher_001":
        raise ValueError("Teacher Correction annotator mismatch")
    known = {row["task_id"]: row for row in manifest.get("tasks", [])}
    decisions = payload.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(known):
        raise ValueError("Teacher Correction export must cover every task exactly once")
    seen = set()
    rejected = []
    accepted = []
    for row in decisions:
        task_id = row.get("task_id")
        if task_id not in known or task_id in seen:
            raise ValueError("Teacher Correction export has unknown or duplicate task")
        seen.add(task_id)
        task = known[task_id]
        if row.get("task_fingerprint") != task.get("task_fingerprint"):
            raise ValueError("Teacher Correction task fingerprint mismatch")
        decision = row.get("decision")
        if decision not in TCV1_DECISIONS:
            raise ValueError("Teacher Correction decision is invalid")
        selected = row.get("selected_assignment_id")
        solution_ids = {item["assignment_id"] for item in task["solutions"]}
        if decision == "REJECTED_PERMANENT":
            if selected is not None:
                raise ValueError("Rejected Teacher Correction task cannot carry selected assignment")
            rejected.append(row)
        else:
            if selected not in solution_ids:
                raise ValueError("Teacher Correction selected assignment is not exact H-C")
            expected = "ACCEPTED_PROPOSAL" if selected == task["initial_assignment_id"] else "CORRECTED"
            if decision != expected:
                raise ValueError("Teacher Correction decision does not match selected assignment")
            accepted.append(row)
    if seen != set(known):
        raise ValueError("Teacher Correction export is incomplete")
    return {
        "task_count": len(decisions),
        "accepted_or_corrected_count": len(accepted),
        "rejected_permanent_count": len(rejected),
        "rejected_task_ids": [row["task_id"] for row in rejected],
        "rejected_task_fingerprints": [row["task_fingerprint"] for row in rejected],
    }


def merge_rejections_into_quarantine(quarantine: dict, export_payload: dict, manifest: dict) -> dict:
    _verify_quarantine(quarantine)
    summary = validate_teacher_correction_export(export_payload, manifest)
    task_ids = set(quarantine["rejected_task_ids"])
    fingerprints = set(quarantine["rejected_task_fingerprints"])
    task_ids.update(summary["rejected_task_ids"])
    fingerprints.update(summary["rejected_task_fingerprints"])
    reasons = Counter(quarantine.get("reason_counts", {}))
    reasons["TEACHER_REJECTED_TASK"] += summary["rejected_permanent_count"]
    source_exports = list(quarantine.get("source_exports", []))
    source_exports.append({
        "batch_id": manifest["batch_id"],
        "session_id": manifest["session_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "rejected_count": summary["rejected_permanent_count"],
    })
    updated = {
        "schema": TCV1_QUARANTINE_SCHEMA,
        "protocol_version": TCV1_PROTOCOL_VERSION,
        "status": "ACTIVE",
        "rejected_task_ids": sorted(task_ids),
        "rejected_task_fingerprints": sorted(fingerprints),
        "reason_counts": dict(sorted(reasons.items())),
        "source_exports": source_exports,
        "policy": dict(quarantine["policy"]),
    }
    updated["manifest_sha256"] = _canonical_sha(updated)
    return updated


def render_teacher_correction_html(manifest: dict) -> str:
    if manifest.get("schema") != TCV1_MANIFEST_SCHEMA:
        raise ValueError("unexpected Teacher Correction manifest schema")
    if manifest.get("annotation_blinded") is not True:
        raise ValueError("Teacher Correction HTML requires blind manifest")
    embedded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(str(manifest.get("session_id", "Teacher Correction v1")))
    template = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light}*{box-sizing:border-box}
body{margin:0;background:#f4f6f8;color:#16181b}header{position:sticky;top:0;background:#fff;border-bottom:1px solid #d9dde3;padding:12px;z-index:5}
.wrap,main{max-width:940px;margin:auto}.progress{height:8px;background:#e1e5ea;border-radius:8px;overflow:hidden;margin-top:8px}.bar{height:100%;background:#20252b;width:0}
main{padding:18px 12px}.card{background:#fff;border:1px solid #d9dde3;border-radius:14px;padding:16px}.muted{color:#69727d;font-size:13px}
.solution{margin-top:14px;border:2px solid #d9dde3;border-radius:12px;padding:12px}.placement{padding:6px 0;border-top:1px solid #eee}.placement:first-child{border-top:0}
.barre{margin-top:8px;font-size:13px}.controls,.decisions,.nav{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}button,select{border:1px solid #c9cfd7;background:#fff;border-radius:10px;padding:11px 13px;font-size:15px;font-weight:650}
button.primary{background:#20252b;color:#fff}.reject{border-color:#9b1c1c}.locked{padding:10px;border-radius:10px;background:#eef1f4;margin-top:12px}
.hidden{display:none}@media(max-width:720px){button,select{width:100%}}
</style></head><body><header><div class="wrap"><strong id="session"></strong> · <span id="count"></span> · REDDET <span id="rej"></span>
<div class="progress"><div class="bar" id="bar"></div></div></div></header>
<main><div class="card"><h1 id="taskNo"></h1><div id="pitches" class="muted"></div>
<p><strong>Bu akor için sana en doğal gelen fiziksel çözümü seç.</strong> Alternatiflerle perde/tel/parmaklamayı düzeltebilirsin. Hiçbiri mantıklı değilse ELE / REDDET.</p>
<div id="locked" class="locked hidden"></div>
<div id="active">
<div class="controls"><button onclick="moveSolution(-1)">← Alternatif</button><select id="solutionSelect" onchange="selectSolution(this.value)"></select><button onclick="moveSolution(1)">Alternatif →</button></div>
<div class="solution"><div id="solution"></div><div id="barres" class="barre"></div></div>
<div class="decisions"><button class="primary" onclick="acceptCurrent()">BU ÇÖZÜMÜ KABUL ET</button><button class="reject" onclick="rejectTask()">ELE / REDDET</button></div>
</div>
<div class="nav"><button onclick="moveTask(-1)">← Önceki</button><button onclick="nextUnanswered()">Sonraki cevapsız</button><button onclick="moveTask(1)">Sonraki →</button></div>
<div id="finish" class="hidden" style="margin-top:16px"><strong>Tamamlandı.</strong><p class="muted">Tek JSON dosyasını kaydet ve ChatGPT'ye yükle.</p><button class="primary" onclick="saveJson()">Teacher Correction JSON kaydet</button></div>
</div></main>
<script>
const MANIFEST=__MANIFEST__;const tasks=MANIFEST.tasks;const storageKey='st_guitar_tcv1_'+MANIFEST.manifest_sha256;
const globalQKey='st_guitar_tcv1_permanent_quarantine';let current=0;let decisions={};let selected={};
try{decisions=JSON.parse(localStorage.getItem(storageKey+'_decisions')||'{}')}catch(_){decisions={}}
try{selected=JSON.parse(localStorage.getItem(storageKey+'_selected')||'{}')}catch(_){selected={}}
let globalQ={ids:{},fps:{}};try{globalQ=JSON.parse(localStorage.getItem(globalQKey)||'{"ids":{},"fps":{}}')}catch(_){globalQ={ids:{},fps:{}}}
for(const t of tasks){if((globalQ.ids&&globalQ.ids[t.task_id])||(globalQ.fps&&globalQ.fps[t.task_fingerprint]))decisions[t.task_id]={task_id:t.task_id,task_fingerprint:t.task_fingerprint,decision:'REJECTED_PERMANENT',selected_assignment_id:null,carried_from_local_quarantine:true}}
function save(){localStorage.setItem(storageKey+'_decisions',JSON.stringify(decisions));localStorage.setItem(storageKey+'_selected',JSON.stringify(selected));localStorage.setItem(globalQKey,JSON.stringify(globalQ))}
function done(){return Object.keys(decisions).length}function rejected(){return Object.values(decisions).filter(x=>x.decision==='REJECTED_PERMANENT').length}
function task(){return tasks[current]}function solutions(t){return t.solutions}
function selectedId(t){return selected[t.task_id]||t.initial_assignment_id}function selectedIndex(t){const id=selectedId(t);const i=solutions(t).findIndex(x=>x.assignment_id===id);return i<0?0:i}
function esc(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function renderSolution(t){const s=solutions(t)[selectedIndex(t)];document.getElementById('solutionSelect').value=s.assignment_id;
document.getElementById('solution').innerHTML=s.placements.map(p=>`<div class="placement">MIDI ${p.pitch_midi} · tel ${p.string} · perde ${p.fret} · <strong>parmak ${p.finger}</strong></div>`).join('');
document.getElementById('barres').innerHTML=s.barres.length?s.barres.map(b=>`<div><strong>Barre:</strong> parmak ${b.finger}, perde ${b.fret}, tel ${b.span_start_string}–${b.span_end_string}</div>`).join(''):'<span class="muted">Barre yok</span>'}
function render(){const t=task();document.getElementById('session').textContent=MANIFEST.session_id;document.getElementById('count').textContent=`${done()}/${tasks.length}`;document.getElementById('rej').textContent=rejected();document.getElementById('bar').style.width=`${100*done()/tasks.length}%`;document.getElementById('taskNo').textContent=`Görev ${current+1} / ${tasks.length}`;document.getElementById('pitches').textContent='Sesler (MIDI): '+t.pitches_midi.join(', ');
const locked=decisions[t.task_id];document.getElementById('locked').classList.toggle('hidden',!locked);document.getElementById('active').classList.toggle('hidden',!!locked);
if(locked){document.getElementById('locked').textContent=locked.decision==='REJECTED_PERMANENT'?'ELENDİ / REDDEDİLDİ — bu görev artık cevapsız kuyruğuna dönmez.':'KAYDEDİLDİ — '+locked.decision}else{
const sel=document.getElementById('solutionSelect');sel.innerHTML=solutions(t).map((s,i)=>`<option value="${esc(s.assignment_id)}">Çözüm ${i+1} / ${solutions(t).length}</option>`).join('');renderSolution(t)}
document.getElementById('finish').classList.toggle('hidden',done()!==tasks.length)}
function selectSolution(id){selected[task().task_id]=id;save();renderSolution(task())}
function moveSolution(d){const t=task();let i=selectedIndex(t);i=Math.max(0,Math.min(solutions(t).length-1,i+d));selected[t.task_id]=solutions(t)[i].assignment_id;save();renderSolution(t)}
function gotoNextOpen(){for(let k=1;k<=tasks.length;k++){const i=(current+k)%tasks.length;if(!decisions[tasks[i].task_id]){current=i;render();return}}render()}
function acceptCurrent(){const t=task();const id=selectedId(t);decisions[t.task_id]={task_id:t.task_id,task_fingerprint:t.task_fingerprint,decision:id===t.initial_assignment_id?'ACCEPTED_PROPOSAL':'CORRECTED',selected_assignment_id:id,initial_assignment_id:t.initial_assignment_id};save();gotoNextOpen()}
function rejectTask(){const t=task();if(!confirm('Bu görevi kalıcı ELE / REDDET yapmak istiyor musun? Bu exportta tekrar cevapsız kuyruğuna dönmeyecek.'))return;
decisions[t.task_id]={task_id:t.task_id,task_fingerprint:t.task_fingerprint,decision:'REJECTED_PERMANENT',selected_assignment_id:null,initial_assignment_id:t.initial_assignment_id};globalQ.ids=globalQ.ids||{};globalQ.fps=globalQ.fps||{};globalQ.ids[t.task_id]=true;globalQ.fps[t.task_fingerprint]=true;save();gotoNextOpen()}
function moveTask(d){current=Math.max(0,Math.min(tasks.length-1,current+d));render()}function nextUnanswered(){gotoNextOpen()}
function saveJson(){if(done()!==tasks.length){alert('Önce tüm görevleri KABUL/DÜZELT veya ELE/REDDET ile tamamla.');return}
const payload={schema:'st-guitar-teacher-correction-v1-export-v1',protocol_version:'TEACHER_CORRECTION.v1',batch_id:MANIFEST.batch_id,session_id:MANIFEST.session_id,manifest_sha256:MANIFEST.manifest_sha256,quarantine_manifest_sha256:MANIFEST.quarantine_manifest_sha256,annotator_id:'teacher_001',collected_at_utc:new Date().toISOString(),decisions:tasks.map(t=>decisions[t.task_id])};
const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`ST_Guitar_${MANIFEST.session_id}_TeacherCorrection.json`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
render();
</script></body></html>'''
    return template.replace("__TITLE__", title).replace("__MANIFEST__", embedded)
