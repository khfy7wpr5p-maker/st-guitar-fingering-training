from __future__ import annotations

from hashlib import sha256
import html
import json
from typing import Iterable

from .finger_assignments_v2 import S1HC_V2_RULE_VERSION, generate_standard_fingerings_v2


MANUAL_REGRESSION_SCHEMA = "st-guitar-teacher-correction-v1-manual-regression"
MANUAL_TASK_SCHEMA = "st-guitar-teacher-correction-v1-manual-task"


def _canonical_sha(value: object) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _all_v2_assignments(pitches_midi: Iterable[int], tuning: tuple[int, ...]):
    result = generate_standard_fingerings_v2(pitches_midi, tuning)
    assignments = {}
    for candidate in result.candidates:
        for assignment in candidate.assignments:
            old = assignments.get(assignment.assignment_id)
            if old is not None and old != assignment:
                raise AssertionError("manual Teacher validator assignment ID collision")
            assignments[assignment.assignment_id] = assignment
    if not assignments:
        raise ValueError("manual Teacher task has no S1-H-C.v2 assignments")
    return tuple(sorted(assignments.values(), key=lambda item: item.assignment_id))


def validate_manual_teacher_solution(
    *,
    pitches_midi: Iterable[int],
    tuning: tuple[int, ...],
    rows: Iterable[dict],
) -> dict:
    """Validate a human-entered string/fret/finger solution against exact H-C.v2 output.

    This function never invents or repairs a Teacher answer. It either matches one
    authoritative S1-H-C.v2 assignment exactly or fails closed with ValueError.
    """

    pitches = tuple(sorted(int(value) for value in pitches_midi))
    tuning = tuple(int(value) for value in tuning)
    if len(tuning) != 6:
        raise ValueError("manual Teacher validator requires six-string tuning")
    raw_rows = tuple(dict(row) for row in rows)
    if len(raw_rows) != len(pitches):
        raise ValueError("manual solution row count must equal chord note count")

    normalized = []
    used_strings = set()
    for row in raw_rows:
        try:
            pitch = int(row["pitch_midi"])
            string = int(row["string"])
            fret = int(row["fret"])
            finger = int(row["finger"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("manual solution row is malformed") from exc
        if not 1 <= string <= 6:
            raise ValueError("manual solution string must be 1..6")
        if string in used_strings:
            raise ValueError("manual solution cannot use one string twice")
        used_strings.add(string)
        if fret < 0:
            raise ValueError("manual solution fret must be non-negative")
        if tuning[string - 1] + fret != pitch:
            raise ValueError("manual solution string/fret does not produce the required MIDI pitch")
        if fret == 0 and finger != 0:
            raise ValueError("open string must use finger 0")
        if fret > 0 and finger not in (1, 2, 3, 4):
            raise ValueError("fretted note must use finger 1..4")
        normalized.append((pitch, string, fret, finger))

    frozen = tuple(sorted(normalized))
    if tuple(sorted(pitch for pitch, _, _, _ in frozen)) != pitches:
        raise ValueError("manual solution changed the chord pitch multiset")

    matches = [assignment for assignment in _all_v2_assignments(pitches, tuning) if assignment.placements == frozen]
    if len(matches) != 1:
        if not matches:
            raise ValueError("manual solution is not an exact S1-H-C.v2 assignment")
        raise AssertionError("manual solution matched more than one H-C.v2 assignment")
    assignment = matches[0]
    return {
        "status": "VALID_EXACT_S1HC_V2",
        "hc_rule_version": S1HC_V2_RULE_VERSION,
        "assignment_id": assignment.assignment_id,
        "placements": [
            {"pitch_midi": p, "string": s, "fret": f, "finger": g}
            for p, s, f, g in assignment.placements
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


def build_manual_task(*, task_name: str, pitches_midi: Iterable[int], tuning: tuple[int, ...]) -> dict:
    pitches = tuple(sorted(int(value) for value in pitches_midi))
    tuning = tuple(int(value) for value in tuning)
    assignments = _all_v2_assignments(pitches, tuning)
    # The suggestion is deliberately deterministic, not a Teacher label or learned score.
    proposal = min(
        assignments,
        key=lambda item: (
            max((fret for _, _, fret, _ in item.placements), default=0)
            - min((fret for _, _, fret, _ in item.placements if fret > 0), default=0),
            sum(fret for _, _, fret, _ in item.placements),
            item.assignment_id,
        ),
    )
    valid = []
    for assignment in assignments:
        valid.append({
            "assignment_id": assignment.assignment_id,
            "placements": [
                {"pitch_midi": p, "string": s, "fret": f, "finger": g}
                for p, s, f, g in assignment.placements
            ],
            "barres": [
                {"finger": g, "fret": f, "span_start_string": a, "span_end_string": b}
                for g, f, a, b in assignment.barres
            ],
        })
    semantic_payload = {
        "hc_rule_version": S1HC_V2_RULE_VERSION,
        "pitches_midi": pitches,
        "tuning": tuning,
    }
    fingerprint = "sha256:" + _canonical_sha(semantic_payload)
    return {
        "schema": MANUAL_TASK_SCHEMA,
        "task_name": task_name,
        "task_id": "tcv1-manual-task-sha256:" + _canonical_sha({"name": task_name, **semantic_payload}),
        "task_fingerprint": fingerprint,
        "hc_rule_version": S1HC_V2_RULE_VERSION,
        "pitches_midi": list(pitches),
        "tuning": list(tuning),
        "proposal_assignment_id": proposal.assignment_id,
        "proposal": next(row for row in valid if row["assignment_id"] == proposal.assignment_id),
        "valid_solutions": valid,
    }


def build_manual_regression_manifest(tasks: Iterable[dict]) -> dict:
    rows = tuple(tasks)
    if not rows:
        raise ValueError("manual regression manifest cannot be empty")
    if any(row.get("schema") != MANUAL_TASK_SCHEMA for row in rows):
        raise ValueError("manual regression manifest contains wrong task schema")
    manifest = {
        "schema": MANUAL_REGRESSION_SCHEMA,
        "protocol_version": "TEACHER_CORRECTION.v1",
        "hc_rule_version": S1HC_V2_RULE_VERSION,
        "status": "REGRESSION_ONLY_NOT_TRAINING_AUTHORIZED",
        "training_authorized": False,
        "task_count": len(rows),
        "tasks": list(rows),
    }
    manifest["manifest_sha256"] = _canonical_sha(manifest)
    return manifest


def render_manual_regression_html(manifest: dict) -> str:
    if manifest.get("schema") != MANUAL_REGRESSION_SCHEMA:
        raise ValueError("unexpected manual regression schema")
    embedded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape("Teacher Correction v1 — Manual Regression")
    template = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;background:#f4f6f8;color:#17191c}header{position:sticky;top:0;background:white;padding:12px;border-bottom:1px solid #ddd;z-index:3}.wrap{max-width:900px;margin:auto}main{max-width:900px;margin:auto;padding:18px 12px}.card{background:white;border:1px solid #d8dde3;border-radius:14px;padding:16px}.row{display:grid;grid-template-columns:1.2fr .8fr .8fr .8fr;gap:8px;align-items:center;margin:7px 0}.sol{border:1px solid #d8dde3;border-radius:10px;padding:10px;margin:12px 0}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}button,input{font-size:15px;border:1px solid #c9cfd7;border-radius:9px;padding:9px}button{font-weight:700;background:white}.primary{background:#20252b;color:white}.reject{border-color:#a11}.ok{background:#e9f8ec;padding:10px;border-radius:9px}.err{background:#fdecec;padding:10px;border-radius:9px}.hidden{display:none}.muted{color:#66707a;font-size:13px}@media(max-width:650px){.row{grid-template-columns:1fr 1fr}.actions button{width:100%}}</style></head><body>
<header><div class="wrap"><strong>Teacher Correction v1 — kısa regresyon</strong> · <span id="counter"></span> · REDDET <span id="rejectCount"></span></div></header>
<main><div class="card"><h1 id="name"></h1><div id="pitches" class="muted"></div><p>Öneriyi kabul edebilir, <strong>ELLE DÜZELT</strong> ile tel/perde/parmak yazabilir veya görevi <strong>ELE / REDDET</strong> yapabilirsin.</p>
<div id="proposal" class="sol"></div><div class="actions"><button class="primary" onclick="acceptProposal()">ÖNERİYİ KABUL ET</button><button onclick="openManual()">ELLE DÜZELT</button><button class="reject" onclick="rejectTask()">ELE / REDDET</button></div>
<div id="manual" class="hidden"><h3>Elle düzeltme</h3><div class="muted">Her MIDI satırı için tel, perde ve sol-el parmağını gir. Açık tel = parmak 0.</div><div id="manualRows"></div><div class="actions"><button class="primary" onclick="validateManual()">DOĞRULA + KAYDET</button><button onclick="closeManual()">Kapat</button></div></div>
<div id="message"></div><div class="actions"><button onclick="prevTask()">← Önceki</button><button onclick="nextOpen()">Sonraki cevapsız</button><button onclick="nextTask()">Sonraki →</button></div>
<div id="finish" class="hidden"><h3>Tamamlandı</h3><button class="primary" onclick="saveJson()">Regresyon JSON kaydet</button></div></div></main>
<script>
const M=__MANIFEST__,tasks=M.tasks;let current=0,decisions={};const storage='tcv1_manual_reg_'+M.manifest_sha256;try{decisions=JSON.parse(localStorage.getItem(storage)||'{}')}catch(_){decisions={}}
function esc(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function save(){localStorage.setItem(storage,JSON.stringify(decisions))}function t(){return tasks[current]}function done(){return Object.keys(decisions).length}function rejs(){return Object.values(decisions).filter(x=>x.decision==='REJECTED_PERMANENT').length}
function placementHtml(sol){return sol.placements.map(p=>`<div>MIDI ${p.pitch_midi} · tel ${p.string} · perde ${p.fret} · <strong>parmak ${p.finger}</strong></div>`).join('')+(sol.barres.length?sol.barres.map(b=>`<div class="muted">Barre: parmak ${b.finger}, perde ${b.fret}, tel ${b.span_start_string}–${b.span_end_string}</div>`).join(''):'<div class="muted">Barre yok</div>')}
function render(){const x=t();document.getElementById('counter').textContent=`${done()}/${tasks.length}`;document.getElementById('rejectCount').textContent=rejs();document.getElementById('name').textContent=`Görev ${current+1}/${tasks.length} — ${x.task_name}`;document.getElementById('pitches').textContent='Sesler (MIDI): '+x.pitches_midi.join(', ');document.getElementById('proposal').innerHTML='<strong>Sistem önerisi</strong>'+placementHtml(x.proposal);document.getElementById('manual').classList.add('hidden');document.getElementById('message').innerHTML=decisions[x.task_id]?`<div class="ok">Kaydedildi: ${esc(decisions[x.task_id].decision)}</div>`:'';document.getElementById('finish').classList.toggle('hidden',done()!==tasks.length)}
function acceptProposal(){const x=t();decisions[x.task_id]={task_id:x.task_id,task_fingerprint:x.task_fingerprint,decision:'ACCEPTED_PROPOSAL',selected_assignment_id:x.proposal_assignment_id};save();nextOpen()}
function rejectTask(){const x=t();decisions[x.task_id]={task_id:x.task_id,task_fingerprint:x.task_fingerprint,decision:'REJECTED_PERMANENT',selected_assignment_id:null};save();nextOpen()}
function openManual(){const x=t();const box=document.getElementById('manualRows');box.innerHTML=x.pitches_midi.map((p,i)=>`<div class="row"><strong>MIDI ${p}</strong><label>Tel <input id="s${i}" type="number" min="1" max="6"></label><label>Perde <input id="f${i}" type="number" min="0" max="24"></label><label>Parmak <input id="g${i}" type="number" min="0" max="4"></label></div>`).join('');document.getElementById('manual').classList.remove('hidden');document.getElementById('message').innerHTML=''}
function closeManual(){document.getElementById('manual').classList.add('hidden')}
function normalizedManual(){const x=t(),rows=[];for(let i=0;i<x.pitches_midi.length;i++){const p=x.pitches_midi[i],s=Number(document.getElementById('s'+i).value),f=Number(document.getElementById('f'+i).value),g=Number(document.getElementById('g'+i).value);if(!Number.isInteger(s)||s<1||s>6)throw Error('Tel 1..6 olmalı.');if(!Number.isInteger(f)||f<0||f>24)throw Error('Perde 0..24 olmalı.');if(!Number.isInteger(g)||g<0||g>4)throw Error('Parmak 0..4 olmalı.');if(x.tuning[s-1]+f!==p)throw Error(`MIDI ${p}: tel ${s} / perde ${f} bu sesi üretmiyor.`);if(f===0&&g!==0)throw Error('Açık telde parmak 0 olmalı.');if(f>0&&(g<1||g>4))throw Error('Basılı perdede parmak 1..4 olmalı.');rows.push({pitch_midi:p,string:s,fret:f,finger:g})}if(new Set(rows.map(r=>r.string)).size!==rows.length)throw Error('Aynı tel iki kez kullanılamaz.');rows.sort((a,b)=>a.pitch_midi-b.pitch_midi||a.string-b.string||a.fret-b.fret||a.finger-b.finger);return rows}
function key(rows){return JSON.stringify(rows)}function validateManual(){try{const x=t(),rows=normalizedManual(),target=key(rows);const matches=x.valid_solutions.filter(sol=>key(sol.placements.slice().sort((a,b)=>a.pitch_midi-b.pitch_midi||a.string-b.string||a.fret-b.fret||a.finger-b.finger))===target);if(matches.length!==1)throw Error('Bu çözüm exact S1-H-C.v2 doğrulamasından geçmedi.');const sol=matches[0];decisions[x.task_id]={task_id:x.task_id,task_fingerprint:x.task_fingerprint,decision:sol.assignment_id===x.proposal_assignment_id?'ACCEPTED_PROPOSAL':'CORRECTED_MANUAL',selected_assignment_id:sol.assignment_id,manual_rows:rows};save();document.getElementById('message').innerHTML='<div class="ok">PASS — exact S1-H-C.v2 çözümü doğrulandı.</div>';setTimeout(nextOpen,350)}catch(e){document.getElementById('message').innerHTML='<div class="err">FAIL — '+esc(e.message)+'</div>'}}
function nextOpen(){for(let k=1;k<=tasks.length;k++){const i=(current+k)%tasks.length;if(!decisions[tasks[i].task_id]){current=i;render();return}}render()}function nextTask(){current=Math.min(tasks.length-1,current+1);render()}function prevTask(){current=Math.max(0,current-1);render()}
function saveJson(){if(done()!==tasks.length){alert('Önce tüm görevleri tamamla.');return}const out={schema:'st-guitar-teacher-correction-v1-manual-regression-export',manifest_sha256:M.manifest_sha256,hc_rule_version:M.hc_rule_version,training_authorized:false,collected_at_utc:new Date().toISOString(),decisions:tasks.map(x=>decisions[x.task_id])};const blob=new Blob([JSON.stringify(out,null,2)+'\n'],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='ST_Guitar_TeacherCorrectionV1_ManualRegression_choices.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}render();
</script></body></html>'''
    return template.replace("__TITLE__", title).replace("__MANIFEST__", embedded)
