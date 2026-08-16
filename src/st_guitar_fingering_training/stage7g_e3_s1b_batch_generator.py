from __future__ import annotations

from collections import Counter
from hashlib import sha256
import html
import json
from typing import Mapping

from .stage7g_e3_s0c_repeat_reliability import (
    EXPECTED_SOURCE_CHOICES_SHA256,
    EXPECTED_SOURCE_MANIFEST_SHA256,
    _select_repeat_rows as _select_s0c_repeat_rows,
    _validate_source_inputs,
    extract_source_teacher_manifest_from_html,
)

S1_FIRST_MANIFEST_SCHEMA = "st-guitar-stage7g-e3-s1-first-pass-component-manifest-v1"
S1_REPEAT_MANIFEST_SCHEMA = "st-guitar-stage7g-e3-s1-repeat-component-manifest-v1"
S1_FIRST_AUDIT_SCHEMA = "st-guitar-stage7g-e3-s1-first-pass-internal-audit-v1"
S1_REPEAT_AUDIT_SCHEMA = "st-guitar-stage7g-e3-s1-repeat-internal-audit-v1"
S1_FIRST_EXPORT_SCHEMA = "st-guitar-stage7g-e3-s1-first-pass-choice-export-v1"
S1_REPEAT_EXPORT_SCHEMA = "st-guitar-stage7g-e3-s1-repeat-choice-export-v1"

LEVELS = ("L1", "L2", "L3", "L4")
COMPONENTS = (
    "POSITION_COMFORT",
    "STRING_DISTRIBUTION",
    "FINGER_SPREAD",
    "OPEN_STRING_UTILITY",
)

S1_CONFIG = {
    "first_task_count": 120,
    "first_level_quota": {level: 30 for level in LEVELS},
    "first_family_cap": 4,
    "first_min_families": 32,
    "selection_salt": "stage7g-e3-s1a-component-corpus-selection-v1",
    "task_id_salt": "stage7g-e3-s1a-component-corpus-task-id-v1",
    "reblind_salt": "stage7g-e3-s1a-component-corpus-reblind-v1",
    "order_salt": "stage7g-e3-s1a-component-corpus-order-v1",
    "family_fold_salt": "stage7g-e3-s1a-family-fold-v1",
    "family_fold_count": 5,
    "sessions": 4,
    "tasks_per_session": 30,
    "repeat_task_count": 48,
    "repeat_level_quota": {level: 12 for level in LEVELS},
    "repeat_family_cap": 2,
    "repeat_selection_salt": "stage7g-e3-s1a-repeat-selection-v1",
    "repeat_task_id_salt": "stage7g-e3-s1a-repeat-task-id-v1",
    "repeat_reblind_salt": "stage7g-e3-s1a-repeat-reblind-v1",
    "repeat_order_salt": "stage7g-e3-s1a-repeat-order-v1",
    "minimum_delay_hours": 24,
}

S0DA_SELECTION_SALT = "stage7g-e3-s0d-rubric-calibration-selection-v1"
S0DB_SELECTION_SALT = "stage7g-e3-s0db-independent-score-selection-v1"

SCALE_ANCHORS_TR = {
    "POSITION_COMFORT": [
        "Çok rahatsız / pratikte kullanılamaz",
        "Rahatsız; belirgin pozisyon çabası",
        "Kabul edilebilir / nötr",
        "Rahat ve doğal",
        "Çok doğal, gevşek ve bütünlüklü",
    ],
    "STRING_DISTRIBUTION": [
        "Çok doğal olmayan tel dağılımı",
        "Rahatsız tel dağılımı",
        "Kabul edilebilir / nötr",
        "Doğal ve erişilebilir",
        "Çok doğal ve ekonomik",
    ],
    "FINGER_SPREAD": [
        "Aşırı / açıkça rahatsız el şekli",
        "Büyük veya gergin açıklık",
        "Yönetilebilir / nötr",
        "Rahat açıklık",
        "Çok kompakt / kolay el şekli",
    ],
    "OPEN_STRING_UTILITY": [
        "Açık tel açıkça zararlı / rahatsız",
        "Bir miktar dezavantajlı",
        "Nötr; açık tel yoksa 3",
        "Faydalı açık tel katkısı",
        "Belirgin ergonomi/rezonans/ekonomi avantajı",
    ],
}


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _rank(value: str, salt: str) -> str:
    return sha256((str(value) + "|" + salt).encode("utf-8")).hexdigest()


def _select_s0da_rows(row_by_id: Mapping[str, dict], s0c_ids: set[str]) -> list[dict]:
    selected: list[dict] = []
    for level in LEVELS:
        rows = [
            row for row in row_by_id.values()
            if row.get("teacher_preference") in ("open_low", "compact")
            and str(row.get("curriculum_level")) == level
            and str(row["task_id"]) not in s0c_ids
        ]
        rows.sort(key=lambda row: _rank(row["task_id"], S0DA_SELECTION_SALT))
        if len(rows) < 5:
            raise ValueError(f"S0-D-A frozen quota cannot be reconstructed for {level}")
        selected.extend(rows[:5])
    if len(selected) != 20:
        raise AssertionError("S0-D-A reconstruction drift")
    return selected


def _select_s0db_rows(row_by_id: Mapping[str, dict], excluded_ids: set[str]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for level in LEVELS:
        rows = [
            row for row in row_by_id.values()
            if row.get("teacher_preference") in ("open_low", "compact")
            and str(row.get("curriculum_level")) == level
            and str(row["task_id"]) not in excluded_ids
        ]
        rows.sort(key=lambda row: _rank(row["task_id"], S0DB_SELECTION_SALT))
        grouped[level] = rows

    selected: list[dict] = []
    level_counts = Counter()
    family_counts = Counter()
    cursors = {level: 0 for level in LEVELS}
    while len(selected) < 20:
        progress = False
        for level in LEVELS:
            if level_counts[level] >= 5:
                continue
            rows = grouped[level]
            cursor = cursors[level]
            picked = None
            while cursor < len(rows):
                row = rows[cursor]
                cursor += 1
                family = str(row.get("family_id", ""))
                if not family:
                    raise ValueError("S0-D-B source row missing family_id")
                if family_counts[family] >= 1:
                    continue
                picked = row
                break
            cursors[level] = cursor
            if picked is not None:
                selected.append(picked)
                level_counts[level] += 1
                family_counts[str(picked["family_id"])] += 1
                progress = True
        if not progress:
            raise ValueError("S0-D-B frozen quotas cannot be reconstructed")
    if level_counts != Counter({level: 5 for level in LEVELS}):
        raise AssertionError("S0-D-B level quota drift")
    if max(family_counts.values()) > 1:
        raise AssertionError("S0-D-B family cap drift")
    return selected


def reconstruct_prior_exclusion_task_ids(validated: dict) -> dict[str, set[str]]:
    rows = validated.get("rows")
    if not isinstance(rows, list) or len(rows) != 400:
        raise ValueError("validated Teacher-GOLD must contain exactly 400 rows")
    row_by_id = {str(row["task_id"]): row for row in rows}
    if len(row_by_id) != 400:
        raise ValueError("validated Teacher-GOLD task IDs must be unique")

    s0c_rows = _select_s0c_repeat_rows(row_by_id)
    s0c_ids = {str(row["task_id"]) for row in s0c_rows}
    s0da_rows = _select_s0da_rows(row_by_id, s0c_ids)
    s0da_ids = {str(row["task_id"]) for row in s0da_rows}
    s0db_rows = _select_s0db_rows(row_by_id, s0c_ids | s0da_ids)
    s0db_ids = {str(row["task_id"]) for row in s0db_rows}
    equal_ids = {
        str(row["task_id"]) for row in rows
        if row.get("teacher_preference") == "EQUAL_OR_UNSURE"
    }
    if len(equal_ids) != 1:
        raise ValueError("expected exactly one original equal/unsure row")
    all_ids = s0c_ids | s0da_ids | s0db_ids | equal_ids
    if len(all_ids) != 101:
        raise AssertionError("prior exclusion sets overlap or drift")
    return {
        "s0c": s0c_ids,
        "s0da": s0da_ids,
        "s0db": s0db_ids,
        "original_equal_or_unsure": equal_ids,
        "all": all_ids,
    }


def _select_with_family_cap(
    row_by_id: Mapping[str, dict],
    excluded_ids: set[str],
    *,
    per_level: int,
    family_cap: int,
    salt: str,
) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for level in LEVELS:
        rows = [
            row for row in row_by_id.values()
            if row.get("teacher_preference") in ("open_low", "compact")
            and str(row.get("curriculum_level")) == level
            and str(row["task_id"]) not in excluded_ids
        ]
        rows.sort(key=lambda row: _rank(row["task_id"], salt))
        grouped[level] = rows

    selected: list[dict] = []
    counts = Counter()
    family_counts = Counter()
    cursors = {level: 0 for level in LEVELS}
    target = per_level * len(LEVELS)
    while len(selected) < target:
        progress = False
        for level in LEVELS:
            if counts[level] >= per_level:
                continue
            rows = grouped[level]
            cursor = cursors[level]
            picked = None
            while cursor < len(rows):
                row = rows[cursor]
                cursor += 1
                family = str(row.get("family_id", ""))
                if not family:
                    raise ValueError("source row missing family_id")
                if family_counts[family] >= family_cap:
                    continue
                picked = row
                break
            cursors[level] = cursor
            if picked is not None:
                selected.append(picked)
                counts[level] += 1
                family_counts[str(picked["family_id"])] += 1
                progress = True
        if not progress:
            raise ValueError("frozen quotas cannot be satisfied under family cap")
    if counts != Counter({level: per_level for level in LEVELS}):
        raise AssertionError("level quota drift")
    if max(family_counts.values()) > family_cap:
        raise AssertionError("family cap drift")
    return selected


def _assign_family_folds(rows: list[dict]) -> dict[str, int]:
    families = sorted(
        {str(row["family_id"]) for row in rows},
        key=lambda family: _rank(family, S1_CONFIG["family_fold_salt"]),
    )
    return {
        family: index % int(S1_CONFIG["family_fold_count"])
        for index, family in enumerate(families)
    }


def _side_map(task_id: str, salt: str) -> tuple[str, str]:
    first_byte = bytes.fromhex(_rank(task_id, salt))[0]
    return ("B", "A") if (first_byte & 1) else ("A", "B")


def _teacher_task(
    source_task: dict,
    opaque_task_id: str,
    source_a: str,
    source_b: str,
    *,
    session: int | None = None,
) -> dict:
    option_by_id = {item["option_id"]: item for item in source_task["options"]}
    row = {
        "task_id": opaque_task_id,
        "pitches_midi": list(source_task["pitches_midi"]),
        "tuning": list(source_task["tuning"]),
        "options": [
            {"option_id": "A", "placements": [dict(x) for x in option_by_id[source_a]["placements"]]},
            {"option_id": "B", "placements": [dict(x) for x in option_by_id[source_b]["placements"]]},
        ],
        "component_dimensions": list(COMPONENTS),
        "component_scale": [1, 2, 3, 4, 5],
        "overall_responses": ["A", "B", "EQUAL_OR_UNSURE"],
    }
    if session is not None:
        row["session"] = session
    return row


def build_s1_packages(source_manifest: dict, validated: dict) -> tuple[dict, dict, dict, dict]:
    task_by_id, row_by_id = _validate_source_inputs(source_manifest, validated)
    exclusions = reconstruct_prior_exclusion_task_ids(validated)

    selected = _select_with_family_cap(
        row_by_id,
        exclusions["all"],
        per_level=30,
        family_cap=4,
        salt=S1_CONFIG["selection_salt"],
    )
    family_counts = Counter(str(row["family_id"]) for row in selected)
    if len(family_counts) < int(S1_CONFIG["first_min_families"]):
        raise ValueError("S1 first-pass corpus has fewer than 32 distinct families")
    folds = _assign_family_folds(selected)

    first_pairs: list[tuple[dict, dict]] = []
    for row in selected:
        original_id = str(row["task_id"])
        opaque_id = _rank(original_id, S1_CONFIG["task_id_salt"])[:24]
        source_a, source_b = _side_map(original_id, S1_CONFIG["reblind_salt"])
        first_pairs.append(({
            "task_id": opaque_id,
            "original_task_id": original_id,
            "family_id": str(row["family_id"]),
            "curriculum_level": str(row["curriculum_level"]),
            "family_fold": int(folds[str(row["family_id"])]),
            "A_source_option": source_a,
            "B_source_option": source_b,
        }, task_by_id[original_id]))

    if len({audit["task_id"] for audit, _ in first_pairs}) != 120:
        raise AssertionError("S1 first-pass opaque task ID collision")
    first_pairs.sort(key=lambda pair: _rank(pair[0]["task_id"], S1_CONFIG["order_salt"]))

    first_teacher_rows: list[dict] = []
    first_audit_rows: list[dict] = []
    for index, (audit, source_task) in enumerate(first_pairs):
        session = index // 30 + 1
        first_teacher_rows.append(_teacher_task(
            source_task,
            audit["task_id"],
            audit["A_source_option"],
            audit["B_source_option"],
            session=session,
        ))
        first_audit_rows.append({**audit, "session": session})

    first_core = {
        "schema": S1_FIRST_MANIFEST_SCHEMA,
        "annotation_blinded": True,
        "choice_semantics": "independent_component_scores_then_overall_preference",
        "source_identity": "withheld",
        "family_identity": "withheld",
        "curriculum_level": "withheld",
        "specialist_identity": "withheld",
        "historical_teacher_answers": "withheld",
        "task_count": 120,
        "session_count": 4,
        "tasks_per_session": 30,
        "tasks": first_teacher_rows,
    }
    first_sha = _canonical_sha256(first_core)
    first_manifest = {**first_core, "manifest_sha256": first_sha}

    first_level_counts = Counter(row["curriculum_level"] for row in first_audit_rows)
    first_family_counts = Counter(row["family_id"] for row in first_audit_rows)
    first_audit = {
        "schema": S1_FIRST_AUDIT_SCHEMA,
        "teacher_facing": False,
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "source_choices_sha256": EXPECTED_SOURCE_CHOICES_SHA256,
        "manifest_sha256": first_sha,
        "task_count": 120,
        "level_counts": dict(sorted(first_level_counts.items())),
        "distinct_families": len(first_family_counts),
        "max_tasks_per_family": max(first_family_counts.values()),
        "session_counts": dict(sorted(Counter(row["session"] for row in first_audit_rows).items())),
        "prior_exclusion_counts": {
            "s0c": len(exclusions["s0c"]),
            "s0da": len(exclusions["s0da"]),
            "s0db": len(exclusions["s0db"]),
            "original_equal_or_unsure": 1,
            "total_unique": len(exclusions["all"]),
        },
        "rows": first_audit_rows,
        "scientific_boundary": {
            "model_training": False,
            "specialist_training": False,
            "arbiter_training": False,
            "historical_preferences_used_for_s1_selection": False,
        },
    }

    repeat_selected = _select_with_family_cap(
        {str(row["task_id"]): row for row in selected},
        set(),
        per_level=12,
        family_cap=2,
        salt=S1_CONFIG["repeat_selection_salt"],
    )
    first_audit_by_original = {row["original_task_id"]: row for row in first_audit_rows}
    repeat_pairs: list[tuple[dict, dict]] = []
    for row in repeat_selected:
        original_id = str(row["task_id"])
        repeat_id = _rank(original_id, S1_CONFIG["repeat_task_id_salt"])[:24]
        source_a, source_b = _side_map(original_id, S1_CONFIG["repeat_reblind_salt"])
        first_row = first_audit_by_original[original_id]
        repeat_pairs.append(({
            "repeat_task_id": repeat_id,
            "original_task_id": original_id,
            "first_pass_task_id": first_row["task_id"],
            "family_id": str(row["family_id"]),
            "curriculum_level": str(row["curriculum_level"]),
            "family_fold": int(folds[str(row["family_id"])]),
            "A_source_option": source_a,
            "B_source_option": source_b,
        }, task_by_id[original_id]))

    if len({audit["repeat_task_id"] for audit, _ in repeat_pairs}) != 48:
        raise AssertionError("S1 repeat opaque task ID collision")
    repeat_pairs.sort(key=lambda pair: _rank(pair[0]["repeat_task_id"], S1_CONFIG["repeat_order_salt"]))
    repeat_teacher_rows = [
        _teacher_task(source_task, audit["repeat_task_id"], audit["A_source_option"], audit["B_source_option"])
        for audit, source_task in repeat_pairs
    ]
    repeat_audit_rows = [audit for audit, _ in repeat_pairs]
    repeat_core = {
        "schema": S1_REPEAT_MANIFEST_SCHEMA,
        "annotation_blinded": True,
        "choice_semantics": "blind_repeat_independent_component_scores_then_overall_preference",
        "source_identity": "withheld",
        "family_identity": "withheld",
        "curriculum_level": "withheld",
        "specialist_identity": "withheld",
        "first_pass_scores": "withheld",
        "task_count": 48,
        "minimum_delay_hours": 24,
        "tasks": repeat_teacher_rows,
    }
    repeat_sha = _canonical_sha256(repeat_core)
    repeat_manifest = {**repeat_core, "manifest_sha256": repeat_sha}
    repeat_family_counts = Counter(row["family_id"] for row in repeat_audit_rows)
    repeat_audit = {
        "schema": S1_REPEAT_AUDIT_SCHEMA,
        "teacher_facing": False,
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "source_choices_sha256": EXPECTED_SOURCE_CHOICES_SHA256,
        "first_pass_manifest_sha256": first_sha,
        "repeat_manifest_sha256": repeat_sha,
        "task_count": 48,
        "level_counts": dict(sorted(Counter(row["curriculum_level"] for row in repeat_audit_rows).items())),
        "distinct_families": len(repeat_family_counts),
        "max_tasks_per_family": max(repeat_family_counts.values()),
        "rows": repeat_audit_rows,
        "scientific_boundary": {
            "selected_before_first_pass_answers": True,
            "repeat_labels_for_training": False,
            "repeat_labels_for_tuning": False,
            "repeat_labels_for_model_selection": False,
        },
    }
    return first_manifest, first_audit, repeat_manifest, repeat_audit


def render_s1_component_annotator(manifest: dict, *, repeat: bool = False) -> str:
    expected_schema = S1_REPEAT_MANIFEST_SCHEMA if repeat else S1_FIRST_MANIFEST_SCHEMA
    export_schema = S1_REPEAT_EXPORT_SCHEMA if repeat else S1_FIRST_EXPORT_SCHEMA
    if manifest.get("schema") != expected_schema:
        raise ValueError("unexpected S1 manifest schema")
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("S1 manifest has no tasks")

    title = "S1 Kör Tekrar" if repeat else "S1 Bağımsız Component Teacher-GOLD"
    note = "Önceki puanlar gösterilmez." if repeat else "A ve B seçeneklerini birbirinden bağımsız puanla."
    filename = "ST_Guitar_S1_repeat_choices_48of48.json" if repeat else "ST_Guitar_S1_component_choices_120of120.json"
    manifest_json = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    anchors_json = json.dumps(SCALE_ANCHORS_TR, ensure_ascii=False, separators=(",", ":"))
    session_html = "" if repeat else '<div class="small" id="session"></div>'

    page = '''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f6f8;color:#17191c;font-family:system-ui,-apple-system,sans-serif}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 14px;z-index:3}.wrap{max-width:820px;margin:auto}.row{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}
.progress{height:7px;background:#e2e5e9;border-radius:10px;overflow:hidden;margin-top:8px}.bar{height:100%;background:#222;width:0}main{max-width:820px;margin:16px auto 60px;padding:0 12px}.card{background:#fff;border:1px solid #ddd;border-radius:14px;padding:16px}
h1{font-size:18px;margin:0}.small{font-size:13px;color:#606975}.taskno{font-size:23px;font-weight:800}.option{margin-top:14px;border:2px solid #dfe2e6;border-radius:12px;padding:14px}.hidden{display:none!important}.placement{padding:5px 0;border-bottom:1px solid #eef0f2}.placement:last-child{border-bottom:0}.scale{margin-top:14px}.scale h3{font-size:15px;margin:0 0 7px}.buttons{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}button{border:1px solid #cbd0d6;background:#fff;border-radius:9px;padding:10px;font-weight:650;font-size:14px}button.active,button.primary{background:#222;color:#fff;border-color:#222}.anchor{font-size:11px;color:#68717c;margin-top:5px;min-height:30px}.controls{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-top:16px}.overall{margin-top:18px;border-top:1px solid #ddd;padding-top:16px}.overall .buttons{grid-template-columns:1fr 1fr 1fr}.notice{background:#f5f6f8;padding:10px;border-radius:9px;margin:12px 0;font-size:13px}@media(max-width:600px){.overall .buttons{grid-template-columns:1fr}.taskno{font-size:20px}}
</style></head><body><header><div class="wrap"><div class="row"><div><h1>__TITLE__</h1><div class="small">__NOTE__</div></div><div class="small" id="stats"></div></div><div class="progress"><div class="bar" id="bar"></div></div></div></header>
<main><div class="card"><div class="row"><div><div class="taskno" id="taskno"></div><div class="small" id="pitches"></div>__SESSION__</div></div><div class="notice" id="instruction"></div><div class="option" id="optionBox"><h2 id="optionTitle"></h2><div id="placements"></div><div id="scales"></div></div><div class="overall hidden" id="overallBox"><h2>Genel tercih</h2><div class="small">Şimdi iki seçeneği birlikte düşün.</div><div id="bothOptions"></div><div class="buttons"><button onclick="chooseOverall('A')">A</button><button onclick="chooseOverall('B')">B</button><button onclick="chooseOverall('EQUAL_OR_UNSURE')">Eşit / Emin değilim</button></div></div><div class="controls"><button onclick="back()">← Geri</button><button class="primary" onclick="next()">Devam →</button><button id="exportBtn" class="hidden" onclick="exportAnswers()">JSON'u Kaydet</button></div></div></main>
<script>
const MANIFEST=__MANIFEST__;const ANCHORS=__ANCHORS__;const EXPORT_SCHEMA="__EXPORT_SCHEMA__";const FILE_NAME="__FILE__";const KEY="s1:"+MANIFEST.manifest_sha256;
let state=JSON.parse(localStorage.getItem(KEY)||'{"index":0,"phase":"A","answers":{},"started_at":null}');if(!state.started_at)state.started_at=new Date().toISOString();
function save(){localStorage.setItem(KEY,JSON.stringify(state))}function task(){return MANIFEST.tasks[state.index]}function answer(){let id=task().task_id;if(!state.answers[id])state.answers[id]={scores:{A:{},B:{}},overall_preference:null};return state.answers[id]}
function completeSide(side){return task().component_dimensions.every(c=>Number.isInteger(answer().scores[side][c]))}function renderPlacements(o){return o.placements.map(p=>`<div class="placement">MIDI ${p.pitch_midi} · Tel ${p.string} · Perde ${p.fret}</div>`).join('')}
function renderScales(side){let a=answer();return task().component_dimensions.map(c=>{let bs=[1,2,3,4,5].map(v=>`<button class="${a.scores[side][c]===v?'active':''}" onclick="score('${side}','${c}',${v})">${v}</button>`).join('');let idx=a.scores[side][c]?a.scores[side][c]-1:2;return `<div class="scale"><h3>${c}</h3><div class="buttons">${bs}</div><div class="anchor">${ANCHORS[c][idx]}</div></div>`}).join('')}
function render(){let t=task(),a=answer();document.getElementById('taskno').textContent=`Görev ${state.index+1} / ${MANIFEST.task_count}`;document.getElementById('pitches').textContent='Pitches: '+t.pitches_midi.join(', ');let s=document.getElementById('session');if(s)s.textContent='Oturum '+t.session;let done=MANIFEST.tasks.filter(x=>{let r=state.answers[x.task_id];return r&&r.overall_preference&&x.component_dimensions.every(c=>Number.isInteger(r.scores.A[c])&&Number.isInteger(r.scores.B[c]))}).length;document.getElementById('stats').textContent=`${done}/${MANIFEST.task_count}`;document.getElementById('bar').style.width=(done/MANIFEST.task_count*100)+'%';if(state.phase==='OVERALL'){document.getElementById('optionBox').classList.add('hidden');document.getElementById('overallBox').classList.remove('hidden');document.getElementById('bothOptions').innerHTML=t.options.map(o=>`<div class="option"><h3>${o.option_id}</h3>${renderPlacements(o)}</div>`).join('')}else{document.getElementById('overallBox').classList.add('hidden');document.getElementById('optionBox').classList.remove('hidden');let side=state.phase,o=t.options.find(x=>x.option_id===side);document.getElementById('optionTitle').textContent='Seçenek '+side;document.getElementById('placements').innerHTML=renderPlacements(o);document.getElementById('scales').innerHTML=renderScales(side);document.getElementById('instruction').textContent=side==='A'?'Yalnız A seçeneğini değerlendir. B henüz kararını etkilemesin.':'Yalnız B seçeneğini değerlendir. A puanları kilitli kalır.'}document.getElementById('exportBtn').classList.toggle('hidden',done!==MANIFEST.task_count);save()}
function score(side,c,v){answer().scores[side][c]=v;render()}function chooseOverall(v){answer().overall_preference=v;render()}function next(){if(state.phase==='A'){if(!completeSide('A'))return alert('A için dört puanı da ver.');state.phase='B'}else if(state.phase==='B'){if(!completeSide('B'))return alert('B için dört puanı da ver.');state.phase='OVERALL'}else{if(!answer().overall_preference)return alert('Genel tercihi seç.');if(state.index<MANIFEST.task_count-1){state.index++;state.phase='A'}}render()}function back(){if(state.phase==='OVERALL')state.phase='B';else if(state.phase==='B')state.phase='A';else if(state.index>0){state.index--;state.phase='OVERALL'}render()}
function exportAnswers(){let rows=MANIFEST.tasks.map(t=>({task_id:t.task_id,...state.answers[t.task_id]}));if(rows.some(r=>!r||!r.overall_preference))return alert('Tüm görevleri tamamla.');let payload={schema:EXPORT_SCHEMA,manifest_sha256:MANIFEST.manifest_sha256,annotator_id:'teacher_001',started_at:state.started_at,completed_at:new Date().toISOString(),rows};let blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=FILE_NAME;a.click();URL.revokeObjectURL(a.href)}render();
</script></body></html>'''
    return (page.replace("__TITLE__", html.escape(title)).replace("__NOTE__", html.escape(note)).replace("__SESSION__", session_html).replace("__MANIFEST__", manifest_json).replace("__ANCHORS__", anchors_json).replace("__EXPORT_SCHEMA__", export_schema).replace("__FILE__", filename))


__all__ = [
    "COMPONENTS",
    "S1_CONFIG",
    "S1_FIRST_EXPORT_SCHEMA",
    "S1_FIRST_MANIFEST_SCHEMA",
    "S1_REPEAT_EXPORT_SCHEMA",
    "S1_REPEAT_MANIFEST_SCHEMA",
    "build_s1_packages",
    "extract_source_teacher_manifest_from_html",
    "reconstruct_prior_exclusion_task_ids",
    "render_s1_component_annotator",
]
