from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import html
import json
from typing import Mapping


S0C_PROTOCOL_SCHEMA = "st-guitar-stage7g-e3-s0c-teacher-repeat-reliability-protocol-v1"
S0C_TEACHER_MANIFEST_SCHEMA = "st-guitar-stage7g-e3-s0c-repeat-teacher-manifest-v1"
S0C_INTERNAL_AUDIT_SCHEMA = "st-guitar-stage7g-e3-s0c-repeat-internal-audit-v1"
S0C_CHOICE_EXPORT_SCHEMA = "st-guitar-stage7g-e3-s0c-repeat-choice-export-v1"
S0C_RESULT_SCHEMA = "st-guitar-stage7g-e3-s0c-repeat-reliability-result-v1"

EXPECTED_SOURCE_MANIFEST_SHA256 = "433bd01d1d8abee7e92ace335733570fb624bf17d70904c42bf9669b45fe9af2"
EXPECTED_SOURCE_CHOICES_SHA256 = "db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e"
EXPECTED_SOURCE_TASKS = 400
EXPECTED_DECISIVE_ROWS = 399
EXPECTED_SOURCE_PREFS = {"open_low": 311, "compact": 88, "EQUAL_OR_UNSURE": 1}

S0C_CONFIG = {
    "task_count": 60,
    "quotas": {
        "L1": {"OPEN_LOW": 6, "COMPACT": 6},
        "L2": {"OPEN_LOW": 9, "COMPACT": 9},
        "L3": {"OPEN_LOW": 7, "COMPACT": 7},
        "L4": {"OPEN_LOW": 8, "COMPACT": 8},
    },
    "family_cap": 2,
    "selection_salt": "stage7g-e3-s0c-repeat-selection-v1",
    "repeat_task_id_salt": "stage7g-e3-s0c-repeat-id-v1",
    "reblind_salt": "stage7g-e3-s0c-repeat-reblind-v1",
    "order_salt": "stage7g-e3-s0c-repeat-order-v1",
    "minimum_delay_hours": 24,
    "ultra_reliability_gate": {
        "exact_semantic_repeat_agreement_gte": 0.95,
        "open_low_repeat_agreement_gte": 0.90,
        "compact_repeat_agreement_gte": 0.90,
        "three_way_cohen_kappa_gte": 0.90,
        "repeat_equal_or_unsure_rate_lte": 0.05,
    },
}


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _rank(task_id: str, salt: str) -> str:
    return sha256((str(task_id) + "|" + salt).encode("utf-8")).hexdigest()


def extract_source_teacher_manifest_from_html(html_text: str) -> tuple[dict, str]:
    """Extract the exact blind 400-task manifest embedded in the original annotator HTML."""
    manifest_marker = "const MANIFEST = "
    sha_marker = 'const MANIFEST_SHA256 = "'
    start = html_text.find(manifest_marker)
    if start < 0:
        raise ValueError("source annotator HTML does not contain MANIFEST")
    start += len(manifest_marker)
    end = html_text.find(";\nconst MANIFEST_SHA256", start)
    if end < 0:
        end = html_text.find(";\r\nconst MANIFEST_SHA256", start)
    if end < 0:
        raise ValueError("source annotator HTML MANIFEST terminator not found")
    manifest = json.loads(html_text[start:end])

    sha_start = html_text.find(sha_marker, end)
    if sha_start < 0:
        raise ValueError("source annotator HTML does not contain MANIFEST_SHA256")
    sha_start += len(sha_marker)
    sha_end = html_text.find('"', sha_start)
    manifest_sha = html_text[sha_start:sha_end]
    if manifest_sha != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise ValueError("source teacher manifest SHA drift")
    return manifest, manifest_sha


def _validate_source_inputs(source_manifest: dict, validated: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    if source_manifest.get("schema") != "st-guitar-stage7g-e3-teacher-pairwise-manifest-v1":
        raise ValueError("unexpected source teacher manifest schema")
    if source_manifest.get("annotation_blinded") is not True:
        raise ValueError("source teacher manifest must remain blinded")
    tasks = source_manifest.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != EXPECTED_SOURCE_TASKS:
        raise ValueError("source teacher manifest must contain exactly 400 tasks")
    task_by_id: dict[str, dict] = {}
    for task in tasks:
        task_id = str(task.get("task_id", ""))
        if not task_id or task_id in task_by_id:
            raise ValueError("source teacher manifest task id invalid or duplicated")
        options = task.get("options")
        if not isinstance(options, list) or [row.get("option_id") for row in options] != ["A", "B"]:
            raise ValueError("source teacher task must contain ordered A/B options")
        task_by_id[task_id] = task

    if validated.get("schema") != "st-guitar-stage7g-e3-c-teacher-batch01-validated-v1":
        raise ValueError("unexpected validated Teacher-GOLD schema")
    if validated.get("status") != "VALIDATED_COMPLETE_TEACHER_GOLD_PAIRWISE":
        raise ValueError("validated Teacher-GOLD is not complete")
    if validated.get("input_choices_sha256") != EXPECTED_SOURCE_CHOICES_SHA256:
        raise ValueError("validated Teacher-GOLD choices SHA drift")
    if validated.get("manifest_sha256") != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise ValueError("validated Teacher-GOLD manifest SHA drift")
    rows = validated.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_SOURCE_TASKS:
        raise ValueError("validated Teacher-GOLD must contain exactly 400 rows")
    row_by_id: dict[str, dict] = {}
    prefs = Counter()
    for row in rows:
        task_id = str(row.get("task_id", ""))
        if not task_id or task_id in row_by_id:
            raise ValueError("validated Teacher-GOLD task id invalid or duplicated")
        pref = row.get("teacher_preference")
        prefs[str(pref)] += 1
        row_by_id[task_id] = row
    if set(row_by_id) != set(task_by_id):
        raise ValueError("source teacher manifest and validated Teacher-GOLD task sets differ")
    if dict(prefs) != EXPECTED_SOURCE_PREFS:
        raise ValueError("validated Teacher-GOLD preference counts drift")
    return task_by_id, row_by_id


def _select_repeat_rows(row_by_id: Mapping[str, dict]) -> list[dict]:
    decisive = [
        row for row in row_by_id.values()
        if row.get("teacher_preference") in ("open_low", "compact")
    ]
    if len(decisive) != EXPECTED_DECISIVE_ROWS:
        raise ValueError("S0-C requires exactly 399 decisive source labels")

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in decisive:
        level = str(row.get("curriculum_level", ""))
        pref = str(row.get("teacher_preference", "")).upper()
        key = (level, pref)
        if level not in S0C_CONFIG["quotas"] or pref not in ("OPEN_LOW", "COMPACT"):
            raise ValueError("unexpected S0-C source stratum")
        grouped[key].append(row)
    for key, rows in grouped.items():
        rows.sort(key=lambda row: _rank(row["task_id"], S0C_CONFIG["selection_salt"]))

    strata = [
        ("L1", "OPEN_LOW"), ("L1", "COMPACT"),
        ("L2", "OPEN_LOW"), ("L2", "COMPACT"),
        ("L3", "OPEN_LOW"), ("L3", "COMPACT"),
        ("L4", "OPEN_LOW"), ("L4", "COMPACT"),
    ]
    selected: list[dict] = []
    selected_per_stratum = Counter()
    family_counts = Counter()
    cursors = {key: 0 for key in strata}

    while len(selected) < S0C_CONFIG["task_count"]:
        progress = False
        for key in strata:
            level, pref = key
            quota = int(S0C_CONFIG["quotas"][level][pref])
            if selected_per_stratum[key] >= quota:
                continue
            candidates = grouped.get(key, [])
            cursor = cursors[key]
            picked = None
            while cursor < len(candidates):
                candidate = candidates[cursor]
                cursor += 1
                family_id = str(candidate.get("family_id", ""))
                if not family_id:
                    raise ValueError("S0-C source row missing family_id")
                if family_counts[family_id] >= S0C_CONFIG["family_cap"]:
                    continue
                picked = candidate
                break
            cursors[key] = cursor
            if picked is None:
                continue
            selected.append(picked)
            selected_per_stratum[key] += 1
            family_counts[str(picked["family_id"])] += 1
            progress = True
        if not progress:
            raise ValueError("S0-C frozen quotas cannot be satisfied under family cap")

    expected_quota_counts = {
        (level, pref): int(count)
        for level, prefs in S0C_CONFIG["quotas"].items()
        for pref, count in prefs.items()
    }
    if dict(selected_per_stratum) != expected_quota_counts:
        raise AssertionError("S0-C selected stratum quotas drift")
    if max(family_counts.values()) > S0C_CONFIG["family_cap"]:
        raise AssertionError("S0-C family cap violated")
    if len(selected) != S0C_CONFIG["task_count"]:
        raise AssertionError("S0-C selected task count drift")
    semantic_counts = Counter(str(row["teacher_preference"]) for row in selected)
    if semantic_counts != Counter({"open_low": 30, "compact": 30}):
        raise AssertionError("S0-C semantic class balance drift")
    return selected


def build_s0c_repeat_package(source_manifest: dict, validated: dict) -> tuple[dict, dict]:
    """Build a 60-task reblinded repeat batch and a separate non-teacher-facing audit."""
    task_by_id, row_by_id = _validate_source_inputs(source_manifest, validated)
    selected = _select_repeat_rows(row_by_id)

    teacher_rows: list[dict] = []
    audit_rows: list[dict] = []
    repeat_ids: set[str] = set()
    for row in selected:
        original_task_id = str(row["task_id"])
        source_task = task_by_id[original_task_id]
        option_by_id = {item["option_id"]: item for item in source_task["options"]}
        repeat_task_id = _rank(original_task_id, S0C_CONFIG["repeat_task_id_salt"])[:24]
        if repeat_task_id in repeat_ids:
            raise AssertionError("S0-C repeat task id collision")
        repeat_ids.add(repeat_task_id)

        reblind_digest = bytes.fromhex(_rank(original_task_id, S0C_CONFIG["reblind_salt"]))
        source_a, source_b = (("B", "A") if (reblind_digest[0] & 1) else ("A", "B"))
        teacher_rows.append({
            "task_id": repeat_task_id,
            "pitches_midi": list(source_task["pitches_midi"]),
            "tuning": list(source_task["tuning"]),
            "options": [
                {"option_id": "A", "placements": list(option_by_id[source_a]["placements"])},
                {"option_id": "B", "placements": list(option_by_id[source_b]["placements"])},
            ],
            "responses": ["A", "B", "EQUAL_OR_UNSURE"],
        })
        audit_rows.append({
            "repeat_task_id": repeat_task_id,
            "original_task_id": original_task_id,
            "family_id": str(row["family_id"]),
            "curriculum_level": str(row["curriculum_level"]),
            "original_blind_response": str(row["blind_response"]),
            "original_teacher_preference": str(row["teacher_preference"]).upper(),
            "repeat_A_source_option": source_a,
            "repeat_B_source_option": source_b,
        })

    teacher_rows.sort(key=lambda task: _rank(task["task_id"], S0C_CONFIG["order_salt"]))
    audit_by_repeat = {row["repeat_task_id"]: row for row in audit_rows}
    audit_rows = [audit_by_repeat[task["task_id"]] for task in teacher_rows]

    manifest_core = {
        "schema": S0C_TEACHER_MANIFEST_SCHEMA,
        "annotation_blinded": True,
        "choice_semantics": "repeat_pairwise_guitaristic_preference",
        "source_identity": "withheld",
        "family_identity": "withheld",
        "curriculum_level": "withheld",
        "original_task_identity": "withheld",
        "original_response": "withheld",
        "specialist_identity": "withheld",
        "old_answer_import_allowed": False,
        "task_count": len(teacher_rows),
        "tasks": teacher_rows,
    }
    manifest_sha256 = _canonical_sha256(manifest_core)
    teacher_manifest = {**manifest_core, "manifest_sha256": manifest_sha256}

    selected_counts = Counter(
        (row["curriculum_level"], row["original_teacher_preference"])
        for row in audit_rows
    )
    family_counts = Counter(row["family_id"] for row in audit_rows)
    internal_audit = {
        "schema": S0C_INTERNAL_AUDIT_SCHEMA,
        "teacher_facing": False,
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "source_choices_sha256": EXPECTED_SOURCE_CHOICES_SHA256,
        "repeat_manifest_sha256": manifest_sha256,
        "task_count": len(audit_rows),
        "selection_task_id_set_sha256": sha256(
            "\n".join(sorted(row["original_task_id"] for row in audit_rows)).encode("utf-8")
        ).hexdigest(),
        "selected_strata": {
            f"{level}:{pref}": int(count)
            for (level, pref), count in sorted(selected_counts.items())
        },
        "family_count": len(family_counts),
        "max_tasks_per_family": max(family_counts.values()),
        "rows": audit_rows,
        "scientific_boundary": {
            "original_labels_teacher_visible": False,
            "repeat_labels_for_training": False,
            "repeat_labels_for_tuning": False,
            "specialist_architecture_activated": False,
        },
    }
    return teacher_manifest, internal_audit


def _cohen_kappa(initial: list[str], repeat: list[str]) -> float:
    if len(initial) != len(repeat) or not initial:
        raise ValueError("kappa inputs must be aligned and non-empty")
    labels = ("OPEN_LOW", "COMPACT", "EQUAL_OR_UNSURE")
    n = len(initial)
    observed = sum(a == b for a, b in zip(initial, repeat)) / n
    initial_counts = Counter(initial)
    repeat_counts = Counter(repeat)
    expected = sum((initial_counts[label] / n) * (repeat_counts[label] / n) for label in labels)
    if expected >= 1.0:
        return 1.0 if observed >= 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def score_s0c_repeat_choices(payload: dict, teacher_manifest: dict, internal_audit: dict) -> dict:
    """Score the repeat labels only for reliability. They are never training/tuning labels."""
    if teacher_manifest.get("schema") != S0C_TEACHER_MANIFEST_SCHEMA:
        raise ValueError("unexpected S0-C repeat teacher manifest schema")
    manifest_sha = teacher_manifest.get("manifest_sha256")
    manifest_core = dict(teacher_manifest)
    manifest_core.pop("manifest_sha256", None)
    if manifest_sha != _canonical_sha256(manifest_core):
        raise ValueError("S0-C repeat teacher manifest SHA mismatch")
    if internal_audit.get("schema") != S0C_INTERNAL_AUDIT_SCHEMA:
        raise ValueError("unexpected S0-C internal audit schema")
    if internal_audit.get("repeat_manifest_sha256") != manifest_sha:
        raise ValueError("S0-C internal audit references wrong repeat manifest")
    if payload.get("schema") != S0C_CHOICE_EXPORT_SCHEMA:
        raise ValueError("unexpected S0-C repeat choice export schema")
    if payload.get("annotation_blinded") is not True:
        raise ValueError("S0-C repeat annotation must remain blinded")
    if payload.get("manifest_sha256") != manifest_sha:
        raise ValueError("S0-C repeat choice export references wrong manifest")
    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) != S0C_CONFIG["task_count"]:
        raise ValueError("S0-C requires exactly 60 repeat choices")

    known_ids = {task["task_id"] for task in teacher_manifest["tasks"]}
    choice_by_id: dict[str, str] = {}
    for row in choices:
        task_id = str(row.get("task_id", ""))
        response = str(row.get("response", ""))
        if task_id not in known_ids or task_id in choice_by_id:
            raise ValueError("S0-C repeat choice task id unknown or duplicated")
        if response not in ("A", "B", "EQUAL_OR_UNSURE"):
            raise ValueError("invalid S0-C repeat response")
        choice_by_id[task_id] = response
    if set(choice_by_id) != known_ids:
        raise ValueError("S0-C repeat choice set incomplete")

    audit_by_id = {row["repeat_task_id"]: row for row in internal_audit["rows"]}
    if set(audit_by_id) != known_ids:
        raise ValueError("S0-C audit task set mismatch")

    event_rows: list[dict] = []
    initial_labels: list[str] = []
    repeat_labels: list[str] = []
    per_level_total = Counter()
    per_level_same = Counter()
    repeat_equal = 0

    for task in teacher_manifest["tasks"]:
        task_id = task["task_id"]
        audit = audit_by_id[task_id]
        response = choice_by_id[task_id]
        initial_pref = audit["original_teacher_preference"]
        initial_labels.append(initial_pref)
        per_level_total[audit["curriculum_level"]] += 1

        if response == "EQUAL_OR_UNSURE":
            repeat_pref = "EQUAL_OR_UNSURE"
            same = False
            decoded_source_option = None
            repeat_equal += 1
        else:
            decoded_source_option = audit[f"repeat_{response}_source_option"]
            same = decoded_source_option == audit["original_blind_response"]
            if same:
                repeat_pref = initial_pref
            else:
                repeat_pref = "COMPACT" if initial_pref == "OPEN_LOW" else "OPEN_LOW"
        repeat_labels.append(repeat_pref)
        if same:
            per_level_same[audit["curriculum_level"]] += 1
        event_rows.append({
            "repeat_task_id": task_id,
            "curriculum_level": audit["curriculum_level"],
            "family_id": audit["family_id"],
            "initial_teacher_preference": initial_pref,
            "repeat_response_blind": response,
            "repeat_teacher_preference": repeat_pref,
            "same_semantic_preference": bool(same),
            "decoded_source_option": decoded_source_option,
        })

    total = len(event_rows)
    same_total = sum(row["same_semantic_preference"] for row in event_rows)
    open_rows = [row for row in event_rows if row["initial_teacher_preference"] == "OPEN_LOW"]
    compact_rows = [row for row in event_rows if row["initial_teacher_preference"] == "COMPACT"]
    if (len(open_rows), len(compact_rows)) != (30, 30):
        raise AssertionError("S0-C repeat semantic balance drift")

    exact_agreement = same_total / total
    open_agreement = sum(row["same_semantic_preference"] for row in open_rows) / len(open_rows)
    compact_agreement = sum(row["same_semantic_preference"] for row in compact_rows) / len(compact_rows)
    equal_rate = repeat_equal / total
    kappa = _cohen_kappa(initial_labels, repeat_labels)

    gate_cfg = S0C_CONFIG["ultra_reliability_gate"]
    gate_conditions = {
        "exact_semantic_repeat_agreement": exact_agreement >= gate_cfg["exact_semantic_repeat_agreement_gte"],
        "open_low_repeat_agreement": open_agreement >= gate_cfg["open_low_repeat_agreement_gte"],
        "compact_repeat_agreement": compact_agreement >= gate_cfg["compact_repeat_agreement_gte"],
        "three_way_cohen_kappa": kappa >= gate_cfg["three_way_cohen_kappa_gte"],
        "repeat_equal_or_unsure_rate": equal_rate <= gate_cfg["repeat_equal_or_unsure_rate_lte"],
    }
    gate_pass = all(gate_conditions.values())

    confusion = {
        initial: {repeat: 0 for repeat in ("OPEN_LOW", "COMPACT", "EQUAL_OR_UNSURE")}
        for initial in ("OPEN_LOW", "COMPACT")
    }
    for initial, repeat in zip(initial_labels, repeat_labels):
        confusion[initial][repeat] += 1

    return {
        "schema": S0C_RESULT_SCHEMA,
        "stage": "7G-E3-S0-C",
        "status": (
            "S0C_ULTRA_RELIABILITY_GATE_PASS_NO_ARCHITECTURE_ACTIVATION"
            if gate_pass
            else "S0C_RELIABILITY_GATE_FAIL_REVIEW_ANNOTATION_RUBRIC"
        ),
        "task_count": total,
        "metrics": {
            "exact_semantic_repeat_agreement_all_60": exact_agreement,
            "open_low_repeat_agreement_original_open_low_30": open_agreement,
            "compact_repeat_agreement_original_compact_30": compact_agreement,
            "three_way_cohen_kappa": kappa,
            "repeat_equal_or_unsure_rate": equal_rate,
            "repeat_equal_or_unsure_count": repeat_equal,
            "same_semantic_count": int(same_total),
        },
        "semantic_confusion": confusion,
        "by_curriculum_level": {
            level: {
                "tasks": int(per_level_total[level]),
                "same": int(per_level_same[level]),
                "agreement": per_level_same[level] / per_level_total[level],
            }
            for level in sorted(per_level_total)
        },
        "ultra_reliability_gate": {
            "thresholds": dict(gate_cfg),
            "conditions": gate_conditions,
            "pass": gate_pass,
        },
        "event_rows": event_rows,
        "scientific_boundary": {
            "repeat_labels_used_for_training": False,
            "repeat_labels_used_for_tuning": False,
            "repeat_labels_used_for_model_selection": False,
            "specialist_architecture_activated": False,
            "checkpoint_retained": False,
            "production_or_shadow_integration": False,
        },
    }


def render_s0c_repeat_annotator_html(teacher_manifest: dict) -> str:
    """Render the blind 60-task repeat annotator. No old-answer import is provided."""
    if teacher_manifest.get("schema") != S0C_TEACHER_MANIFEST_SCHEMA:
        raise ValueError("unexpected S0-C teacher manifest schema")
    if teacher_manifest.get("task_count") != S0C_CONFIG["task_count"]:
        raise ValueError("S0-C teacher manifest must contain exactly 60 tasks")
    manifest_json = json.dumps(teacher_manifest, ensure_ascii=False, separators=(",", ":"))
    manifest_sha = html.escape(str(teacher_manifest["manifest_sha256"]), quote=True)
    return f'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ST Guitar — Kör Tekrar Güvenilirlik Testi</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#f5f6f8;color:#16181b}}main{{max-width:1050px;margin:24px auto;padding:0 14px}}
.panel{{background:white;border:1px solid #d9dde3;border-radius:14px;padding:18px}}.options{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.option{{border:2px solid #d9dde3;border-radius:12px;padding:14px}}.option.active{{border-color:#20252b}}button{{padding:12px;border:1px solid #cbd0d6;border-radius:9px;background:white;font-weight:650}}
.answers{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:16px}}.controls{{display:flex;justify-content:space-between;gap:8px;margin-top:14px;flex-wrap:wrap}}
.placement{{padding:6px 0;border-top:1px solid #eef0f2}}.muted{{color:#68717c;font-size:13px}}@media(max-width:700px){{.options,.answers{{grid-template-columns:1fr}}}}
</style></head><body><main><div class="panel">
<h2>Kör tekrar testi — <span id="num"></span></h2><div class="muted">Yalnız gitar üzerinde daha doğal/rahat bulduğun seçeneği işaretle. Önceki cevapların gösterilmez.</div>
<p id="pitches"></p><div class="options"><div class="option" id="oa"><h3>A</h3><div id="pa"></div></div><div class="option" id="ob"><h3>B</h3><div id="pb"></div></div></div>
<div class="answers"><button onclick="choose('A')">A daha iyi</button><button onclick="choose('B')">B daha iyi</button><button onclick="choose('EQUAL_OR_UNSURE')">Eşit / Emin değilim</button></div>
<div class="controls"><div><button onclick="go(-1)">← Önceki</button> <button onclick="go(1)">Sonraki →</button></div><button onclick="exportAnswers()">Cevapları JSON olarak kaydet</button></div>
<p id="stats" class="muted"></p></div></main><script>
const MANIFEST={manifest_json}; const MANIFEST_SHA256="{manifest_sha}"; const tasks=MANIFEST.tasks; let current=0; let answers={{}};
function placements(id,opt){{document.getElementById(id).innerHTML=opt.placements.map(p=>`<div class="placement">MIDI ${{p.pitch_midi}} · Tel ${{p.string}} · Perde ${{p.fret}}</div>`).join('')}}
function render(){{const t=tasks[current];document.getElementById('num').textContent=`${{current+1}}/60`;document.getElementById('pitches').textContent='Sesler (MIDI): '+t.pitches_midi.join(', ');placements('pa',t.options[0]);placements('pb',t.options[1]);document.getElementById('oa').classList.toggle('active',answers[t.task_id]==='A');document.getElementById('ob').classList.toggle('active',answers[t.task_id]==='B');document.getElementById('stats').textContent=`${{Object.keys(answers).length}}/60 tamamlandı`;}}
function choose(v){{answers[tasks[current].task_id]=v;render();if(current<tasks.length-1){{current++;render();}}}} function go(d){{current=Math.max(0,Math.min(tasks.length-1,current+d));render();}}
function exportAnswers(){{const choices=tasks.filter(t=>answers[t.task_id]).map(t=>({{task_id:t.task_id,response:answers[t.task_id]}}));const payload={{schema:'{S0C_CHOICE_EXPORT_SCHEMA}',manifest_sha256:MANIFEST_SHA256,annotation_blinded:true,annotator_id:'teacher_001',selected_count:choices.length,task_count:tasks.length,choices}};const blob=new Blob([JSON.stringify(payload,null,2)+'\\n'],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`ST_Guitar_S0C_repeat_choices_${{choices.length}}of60.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}}
document.addEventListener('keydown',e=>{{const k=e.key.toLowerCase();if(k==='a')choose('A');else if(k==='b')choose('B');else if(k==='u')choose('EQUAL_OR_UNSURE');else if(e.key==='ArrowLeft')go(-1);else if(e.key==='ArrowRight')go(1);}});render();
</script></body></html>'''
