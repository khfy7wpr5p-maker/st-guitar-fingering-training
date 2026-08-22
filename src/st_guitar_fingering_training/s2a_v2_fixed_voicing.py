from __future__ import annotations

from hashlib import sha256
import html
import json
from typing import Iterable

from .finger_assignments import StandardFingering
from .finger_assignments_v2 import S1HC_V2_RULE_VERSION, generate_standard_fingerings_v2
from .guitarset_voicing_prereg import GUITARSET_VOICING_MAX_FRET
from .s2a_features import S2A_FEATURE_LIST_SHA256, assignment_feature_vector


S2A_V2_PROTOCOL_VERSION = "S2-A.v2-GUITARSET-FIXED-VOICING.v1"
S2A_V2_TARGET = "STATIC_STANDARD_FINGERING_NATURALNESS_GIVEN_FIXED_STRING_FRET_VOICING"
S2A_V2_TASK_SCHEMA = "st-guitar-s2a-v2-fixed-voicing-task-v1"
S2A_V2_MANIFEST_SCHEMA = "st-guitar-s2a-v2-single-session-manifest-v1"
S2A_V2_EXPORT_SCHEMA = "st-guitar-s2a-v2-single-session-export-v1"
S2A_V2_AUDIT_SCHEMA = "st-guitar-s2a-v2-single-session-audit-v1"

DECISION_SELECT = "SELECT_ASSIGNMENT"
DECISION_EQUAL = "EQUAL_OR_UNSURE"
DECISION_REJECT = "REJECT_TASK"
ALLOWED_DECISIONS = (DECISION_SELECT, DECISION_EQUAL, DECISION_REJECT)

BUCKET_DEVELOPMENT = "DEVELOPMENT"
BUCKET_FINAL = "FINAL"
STANDARD_TUNING_BY_STRING = (64, 59, 55, 50, 45, 40)


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def canonical_fixed_voicing(
    placements: Iterable[Iterable[int]],
    *,
    tuning: tuple[int, ...] = STANDARD_TUNING_BY_STRING,
) -> tuple[tuple[int, int, int], ...]:
    if len(tuning) != 6:
        raise ValueError("S2-A.v2 supports six-string standard tuning only")
    rows = tuple(sorted((int(p), int(s), int(f)) for p, s, f in placements))
    if len(rows) < 2 or len(rows) > 6:
        raise ValueError("S2-A.v2 fixed voicing must contain 2..6 notes")
    if len({s for _, s, _ in rows}) != len(rows):
        raise ValueError("S2-A.v2 fixed voicing reuses a string")
    for pitch, string, fret in rows:
        if not 1 <= string <= 6:
            raise ValueError("S2-A.v2 fixed voicing string outside 1..6")
        if not 0 <= fret <= GUITARSET_VOICING_MAX_FRET:
            raise ValueError("S2-A.v2 fixed voicing fret outside GuitarSet model domain")
        if int(tuning[string - 1]) + fret != pitch:
            raise ValueError("S2-A.v2 fixed voicing violates pitch/string/fret relation")
    return rows


def assignments_for_fixed_voicing(
    fixed_voicing: Iterable[Iterable[int]],
    *,
    tuning: tuple[int, ...] = STANDARD_TUNING_BY_STRING,
) -> tuple[StandardFingering, ...]:
    fixed = canonical_fixed_voicing(fixed_voicing, tuning=tuning)
    pitches = tuple(sorted(pitch for pitch, _, _ in fixed))
    generated = generate_standard_fingerings_v2(pitches, tuning)
    matches = [item for item in generated.candidates if item.candidate == fixed]
    if len(matches) != 1:
        if not matches:
            raise ValueError("fixed GuitarSet voicing is not retained by S1-H-A/B/H-C.v2")
        raise AssertionError("fixed voicing matched multiple H-C.v2 candidates")
    assignments = tuple(matches[0].assignments)
    if not assignments:
        raise ValueError("fixed GuitarSet voicing has no H-C.v2 assignments")
    if len({item.assignment_id for item in assignments}) != len(assignments):
        raise AssertionError("duplicate H-C.v2 assignment IDs for fixed voicing")
    for assignment in assignments:
        restored = tuple(sorted((p, s, f) for p, s, f, _ in assignment.placements))
        if restored != fixed:
            raise AssertionError("H-C.v2 assignment changed the fixed voicing")
        vector = assignment_feature_vector(assignment)
        if len(vector) != 30:
            raise AssertionError("S2-A.v2 assignment feature dimension drift")
    return tuple(sorted(assignments, key=lambda item: item.assignment_id))


def _assignment_payload(assignment: StandardFingering) -> dict:
    return {
        "assignment_id": assignment.assignment_id,
        "placements": [
            {"pitch_midi": p, "string": s, "fret": f, "finger": finger}
            for p, s, f, finger in assignment.placements
        ],
        "barres": [
            {
                "finger": finger,
                "fret": fret,
                "span_start_string": start,
                "span_end_string": end,
            }
            for finger, fret, start, end in assignment.barres
        ],
    }


def semantic_fingerprint(
    fixed_voicing: Iterable[Iterable[int]],
    *,
    tuning: tuple[int, ...] = STANDARD_TUNING_BY_STRING,
) -> str:
    fixed = canonical_fixed_voicing(fixed_voicing, tuning=tuning)
    assignments = assignments_for_fixed_voicing(fixed, tuning=tuning)
    payload = {
        "protocol_version": S2A_V2_PROTOCOL_VERSION,
        "hc_rule_version": S1HC_V2_RULE_VERSION,
        "feature_list_sha256": S2A_FEATURE_LIST_SHA256,
        "fixed_voicing": fixed,
        "assignment_ids": [item.assignment_id for item in assignments],
    }
    return "s2a-v2-semantic-sha256:" + canonical_sha256(payload)


def build_fixed_voicing_task(
    *,
    event_id: str,
    fixed_voicing: Iterable[Iterable[int]],
    export_bucket: str,
    presentation_nonce: str,
    tuning: tuple[int, ...] = STANDARD_TUNING_BY_STRING,
) -> dict:
    if export_bucket not in (BUCKET_DEVELOPMENT, BUCKET_FINAL):
        raise ValueError("S2-A.v2 task export bucket must be DEVELOPMENT or FINAL")
    if not event_id or not presentation_nonce:
        raise ValueError("S2-A.v2 event/presentation identity required")
    fixed = canonical_fixed_voicing(fixed_voicing, tuning=tuning)
    assignments = assignments_for_fixed_voicing(fixed, tuning=tuning)
    if len(assignments) < 2:
        raise ValueError("S2-A.v2 Teacher task requires at least two H-C.v2 assignments")
    semantic = semantic_fingerprint(fixed, tuning=tuning)
    task_id = "s2a-v2-task-sha256:" + canonical_sha256({
        "protocol_version": S2A_V2_PROTOCOL_VERSION,
        "event_id": event_id,
        "semantic_fingerprint": semantic,
        "presentation_nonce": presentation_nonce,
        "export_bucket": export_bucket,
    })
    ordered = sorted(
        assignments,
        key=lambda item: (
            sha256(
                f"{S2A_V2_PROTOCOL_VERSION}|ORDER|{task_id}|{item.assignment_id}".encode("utf-8")
            ).hexdigest(),
            item.assignment_id,
        ),
    )
    return {
        "schema": S2A_V2_TASK_SCHEMA,
        "protocol_version": S2A_V2_PROTOCOL_VERSION,
        "target": S2A_V2_TARGET,
        "task_id": task_id,
        "semantic_fingerprint": semantic,
        "export_bucket": export_bucket,
        "pitches_midi": sorted(p for p, _, _ in fixed),
        "tuning": list(tuning),
        "fixed_voicing": [
            {"pitch_midi": p, "string": s, "fret": f}
            for p, s, f in fixed
        ],
        "assignment_count": len(ordered),
        "options": [_assignment_payload(item) for item in ordered],
        "allowed_decisions": list(ALLOWED_DECISIONS),
        "source_identity_withheld": True,
        "guitarset_origin_withheld": True,
        "model_scores_withheld": True,
        "baseline_scores_withheld": True,
        "historical_teacher_answers_withheld": True,
    }


def build_single_session_manifest(
    *,
    batch_id: str,
    session_id: str,
    tasks: Iterable[dict],
) -> dict:
    rows = tuple(tasks)
    if not batch_id or not session_id or not rows:
        raise ValueError("S2-A.v2 manifest requires batch/session/tasks")
    if any(row.get("schema") != S2A_V2_TASK_SCHEMA for row in rows):
        raise ValueError("S2-A.v2 manifest contains wrong task schema")
    task_ids = [str(row["task_id"]) for row in rows]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("S2-A.v2 manifest contains duplicate task IDs")
    if not any(row["export_bucket"] == BUCKET_DEVELOPMENT for row in rows):
        raise ValueError("S2-A.v2 manifest has no development tasks")
    if not any(row["export_bucket"] == BUCKET_FINAL for row in rows):
        raise ValueError("S2-A.v2 manifest has no final tasks")
    manifest = {
        "schema": S2A_V2_MANIFEST_SCHEMA,
        "protocol_version": S2A_V2_PROTOCOL_VERSION,
        "target": S2A_V2_TARGET,
        "hc_rule_version": S1HC_V2_RULE_VERSION,
        "feature_list_sha256": S2A_FEATURE_LIST_SHA256,
        "status": "READY_FOR_SINGLE_SESSION_TEACHER_COLLECTION",
        "batch_id": batch_id,
        "session_id": session_id,
        "annotator_id": "teacher_001",
        "annotation_blinded": True,
        "task_count": len(rows),
        "development_presentation_count": sum(row["export_bucket"] == BUCKET_DEVELOPMENT for row in rows),
        "final_presentation_count": sum(row["export_bucket"] == BUCKET_FINAL for row in rows),
        "tasks": list(rows),
        "single_session_collection_authorized": True,
        "historical_s2a_v1_labels_trainable": False,
        "historical_teacher_correction_labels_trainable": False,
        "real_fit_authorized_before_gate": False,
        "final_labels_authorized_before_model_seal": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return manifest


def _decision_token(row: dict) -> str:
    decision = row["decision"]
    if decision == DECISION_SELECT:
        return "SELECT:" + str(row["selected_assignment_id"])
    return str(decision)


def validate_choice_export(payload: dict, manifest: dict, *, expected_bucket: str) -> dict[str, dict]:
    if expected_bucket not in (BUCKET_DEVELOPMENT, BUCKET_FINAL):
        raise ValueError("invalid S2-A.v2 expected export bucket")
    if payload.get("schema") != S2A_V2_EXPORT_SCHEMA:
        raise ValueError("unexpected S2-A.v2 export schema")
    if payload.get("protocol_version") != S2A_V2_PROTOCOL_VERSION:
        raise ValueError("S2-A.v2 export protocol drift")
    if payload.get("manifest_sha256") != manifest.get("manifest_sha256"):
        raise ValueError("S2-A.v2 export manifest mismatch")
    if payload.get("annotator_id") != manifest.get("annotator_id"):
        raise ValueError("S2-A.v2 export annotator mismatch")
    if payload.get("export_bucket") != expected_bucket:
        raise ValueError("S2-A.v2 export bucket mismatch")

    expected = {
        row["task_id"]: row
        for row in manifest.get("tasks", [])
        if row.get("export_bucket") == expected_bucket
    }
    decisions = payload.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(expected):
        raise ValueError("S2-A.v2 export must cover its bucket exactly once")
    out: dict[str, dict] = {}
    for row in decisions:
        if not isinstance(row, dict):
            raise ValueError("S2-A.v2 decision row must be an object")
        task_id = str(row.get("task_id", ""))
        if task_id not in expected or task_id in out:
            raise ValueError("S2-A.v2 export has unknown or duplicate task")
        task = expected[task_id]
        if row.get("semantic_fingerprint") != task.get("semantic_fingerprint"):
            raise ValueError("S2-A.v2 semantic fingerprint mismatch")
        decision = row.get("decision")
        if decision not in ALLOWED_DECISIONS:
            raise ValueError("S2-A.v2 decision is invalid")
        selected = row.get("selected_assignment_id")
        option_ids = {item["assignment_id"] for item in task["options"]}
        if decision == DECISION_SELECT:
            if selected not in option_ids:
                raise ValueError("S2-A.v2 selection references an out-of-set assignment")
        elif selected is not None:
            raise ValueError("non-selection S2-A.v2 decision cannot carry an assignment ID")
        out[task_id] = {
            "task_id": task_id,
            "semantic_fingerprint": task["semantic_fingerprint"],
            "decision": decision,
            "selected_assignment_id": selected,
        }
    if set(out) != set(expected):
        raise ValueError("S2-A.v2 export is incomplete")
    return out


def reliability_report(
    development_export: dict,
    manifest: dict,
    internal_audit: dict,
    *,
    minimum_repeat_pairs: int = 30,
) -> dict:
    decisions = validate_choice_export(development_export, manifest, expected_bucket=BUCKET_DEVELOPMENT)
    if internal_audit.get("schema") != S2A_V2_AUDIT_SCHEMA:
        raise ValueError("unexpected S2-A.v2 internal audit schema")
    pairs = internal_audit.get("repeat_pairs")
    if not isinstance(pairs, list) or len(pairs) < minimum_repeat_pairs:
        raise ValueError("S2-A.v2 reliability audit has too few hidden repeat pairs")
    agreements = 0
    for pair in pairs:
        original = str(pair.get("original_task_id", ""))
        repeat = str(pair.get("repeat_task_id", ""))
        if original not in decisions or repeat not in decisions or original == repeat:
            raise ValueError("S2-A.v2 reliability pair identity mismatch")
        if manifest_task(manifest, original)["semantic_fingerprint"] != manifest_task(manifest, repeat)["semantic_fingerprint"]:
            raise ValueError("S2-A.v2 hidden repeat semantic mismatch")
        agreements += _decision_token(decisions[original]) == _decision_token(decisions[repeat])
    exact = agreements / len(pairs)
    return {
        "status": "PASS" if exact >= 0.85 else "FAIL",
        "repeat_pairs": len(pairs),
        "exact_assignment_or_class_agreement": exact,
        "minimum_required_agreement": 0.85,
        "same_session_hidden_repeats": True,
        "old_answer_visible_during_repeat": False,
        "repeat_rows_trainable": False,
    }


def manifest_task(manifest: dict, task_id: str) -> dict:
    rows = [row for row in manifest.get("tasks", []) if row.get("task_id") == task_id]
    if len(rows) != 1:
        raise ValueError("S2-A.v2 task identity missing or duplicated")
    return rows[0]


def recompute_assignment_map(task: dict) -> dict[str, StandardFingering]:
    fixed = tuple(
        (int(row["pitch_midi"]), int(row["string"]), int(row["fret"]))
        for row in task.get("fixed_voicing", [])
    )
    tuning = tuple(int(value) for value in task.get("tuning", []))
    assignments = assignments_for_fixed_voicing(fixed, tuning=tuning)
    out = {item.assignment_id: item for item in assignments}
    stored = {item["assignment_id"] for item in task.get("options", [])}
    if stored != set(out):
        raise ValueError("S2-A.v2 stored option set drifted from fresh H-C.v2 output")
    return out


def render_single_session_html(manifest: dict) -> str:
    if manifest.get("schema") != S2A_V2_MANIFEST_SCHEMA:
        raise ValueError("unexpected S2-A.v2 manifest schema")
    if manifest.get("annotation_blinded") is not True:
        raise ValueError("S2-A.v2 HTML requires blinded manifest")
    embedded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(str(manifest.get("session_id", "ST Guitar Teacher Session")))
    template = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light}
*{box-sizing:border-box}body{margin:0;background:#f5f6f8;color:#15171a}header{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid #d9dde3;padding:11px}.wrap{max-width:980px;margin:auto}main{max-width:980px;margin:auto;padding:16px 12px}.card{background:#fff;border:1px solid #d9dde3;border-radius:14px;padding:16px}.fixed{padding:10px;border-radius:10px;background:#f0f3f7;margin:10px 0}.option{display:block;border:1px solid #ccd2da;border-radius:12px;padding:12px;margin:10px 0;cursor:pointer}.option:has(input:checked){outline:3px solid #222}.placements{display:flex;gap:8px;flex-wrap:wrap;margin-top:7px}.pill{background:#eef1f4;border-radius:999px;padding:5px 9px}.muted{color:#68717b;font-size:13px}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}button{font-size:15px;font-weight:700;border:1px solid #c5cbd3;border-radius:10px;background:#fff;padding:10px 14px}.primary{background:#171a1f;color:#fff}.danger{border-color:#9a2323}.ok{background:#e9f7ed;padding:9px;border-radius:9px;margin-top:10px}.hidden{display:none}@media(max-width:650px){.actions button{width:100%}}
</style></head><body><header><div class="wrap"><strong>ST Guitar · tek oturum Teacher Fingering</strong> · <span id="counter"></span></div></header>
<main><div class="card"><h1 id="heading"></h1><p>Tel/perde düzeni sabittir. Yalnızca bu düzen için en doğal sol-el parmaklamasını seç.</p><div id="fixed" class="fixed"></div><div id="options"></div><div class="actions"><button class="primary" onclick="selectAndNext()">SEÇ VE SONRAKİ</button><button onclick="markEqual()">EŞİT / EMİN DEĞİLİM</button><button class="danger" onclick="rejectTask()">ELE / REDDET</button></div><div id="message"></div><div class="actions"><button onclick="prevTask()">← Önceki</button><button onclick="nextOpen()">Sonraki cevapsız</button><button onclick="nextTask()">Sonraki →</button></div><div id="finish" class="hidden"><h2>Tamamlandı</h2><p>İki dosya oluşur. Önce <strong>DEVELOPMENT</strong> dosyasını kullan. <strong>FINAL</strong> dosyasını model mühürlenmeden açma veya analiz etme.</p><div class="actions"><button class="primary" onclick="downloadBucket('DEVELOPMENT')">DEVELOPMENT JSON indir</button><button onclick="downloadBucket('FINAL')">FINAL SEALED JSON indir</button></div></div></div></main>
<script>
const M=__MANIFEST__,tasks=M.tasks;let current=0,decisions={};const storage='s2a_v2_'+M.manifest_sha256;try{decisions=JSON.parse(localStorage.getItem(storage)||'{}')}catch(_){decisions={}}
function esc(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function save(){localStorage.setItem(storage,JSON.stringify(decisions))}function t(){return tasks[current]}function done(){return Object.keys(decisions).length}
function optionHtml(o,i){const ps=o.placements.map(p=>`<span class="pill">tel ${p.string} · perde ${p.fret} · <b>parmak ${p.finger}</b></span>`).join('');const bs=o.barres.length?o.barres.map(b=>`<span class="pill">barre p${b.finger} · perde ${b.fret} · tel ${b.span_start_string}–${b.span_end_string}</span>`).join(''):'<span class="muted">barre yok</span>';return `<label class="option"><input type="radio" name="choice" value="${esc(o.assignment_id)}"> <strong>Seçenek ${i+1}</strong><div class="placements">${ps}</div><div class="placements">${bs}</div></label>`}
function render(){const x=t();document.getElementById('counter').textContent=`${done()}/${tasks.length}`;document.getElementById('heading').textContent=`Görev ${current+1}/${tasks.length}`;document.getElementById('fixed').innerHTML='<strong>Sabit tel/perde:</strong><div class="placements">'+x.fixed_voicing.map(p=>`<span class="pill">MIDI ${p.pitch_midi} · tel ${p.string} · perde ${p.fret}</span>`).join('')+'</div>';document.getElementById('options').innerHTML=x.options.map(optionHtml).join('');const old=decisions[x.task_id];if(old&&old.decision==='SELECT_ASSIGNMENT'){const radio=document.querySelector(`input[value="${CSS.escape(old.selected_assignment_id)}"]`);if(radio)radio.checked=true}document.getElementById('message').innerHTML=old?`<div class="ok">Kaydedildi: ${esc(old.decision)}</div>`:'';document.getElementById('finish').classList.toggle('hidden',done()!==tasks.length)}
function put(decision,selected){const x=t();decisions[x.task_id]={task_id:x.task_id,semantic_fingerprint:x.semantic_fingerprint,decision:decision,selected_assignment_id:selected};save();nextOpen()}
function selectAndNext(){const chosen=document.querySelector('input[name="choice"]:checked');if(!chosen){document.getElementById('message').innerHTML='<div class="ok">Önce bir parmaklama seç.</div>';return}put('SELECT_ASSIGNMENT',chosen.value)}function markEqual(){put('EQUAL_OR_UNSURE',null)}function rejectTask(){put('REJECT_TASK',null)}
function prevTask(){current=(current-1+tasks.length)%tasks.length;render()}function nextTask(){current=(current+1)%tasks.length;render()}function nextOpen(){for(let k=1;k<=tasks.length;k++){const i=(current+k)%tasks.length;if(!decisions[tasks[i].task_id]){current=i;render();return}}render()}
function payload(bucket){const rows=tasks.filter(x=>x.export_bucket===bucket).map(x=>decisions[x.task_id]);if(rows.some(x=>!x))throw Error('Bu bölümde eksik cevap var.');return {schema:'st-guitar-s2a-v2-single-session-export-v1',protocol_version:M.protocol_version,manifest_sha256:M.manifest_sha256,annotator_id:M.annotator_id,export_bucket:bucket,decisions:rows}}
function downloadBucket(bucket){try{const data=JSON.stringify(payload(bucket),null,2),blob=new Blob([data],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=bucket==='FINAL'?'ST_Guitar_S2A_V2_FINAL_SEALED_choices.json':'ST_Guitar_S2A_V2_DEVELOPMENT_choices.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}catch(e){alert(e.message)}}render();
</script></body></html>'''
    return template.replace("__TITLE__", title).replace("__MANIFEST__", embedded)
