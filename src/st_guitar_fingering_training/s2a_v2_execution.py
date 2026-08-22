from __future__ import annotations

from collections.abc import Callable

from .s2a_v2_fixed_voicing import canonical_sha256
from .s2a_v2_ranker import evaluate_untouched_final, fit_and_seal_development_model


EXECUTION_SCHEMA = "st-guitar-s2a-v2-post-session-execution-v1"


def execute_after_teacher_session(
    *,
    manifest: dict,
    internal_audit: dict,
    development_export: dict,
    final_loader: Callable[[], dict],
) -> tuple[dict, dict, dict]:
    """Run DEVELOPMENT first; do not call final_loader until the model is sealed.

    The caller may point final_loader at the sealed FINAL file. This function is
    intentionally ordered so a failed reliability/corpus/CV gate cannot even read
    that file's JSON payload.
    """

    model_artifact = fit_and_seal_development_model(
        manifest,
        internal_audit,
        development_export,
    )
    if model_artifact.get("model_sealed") is not True:
        raise RuntimeError("S2-A.v2 development model did not seal")
    if model_artifact.get("final_access_authorized") is not True:
        raise RuntimeError("S2-A.v2 final access remains closed")

    final_export = final_loader()
    if not isinstance(final_export, dict):
        raise ValueError("S2-A.v2 FINAL loader must return a JSON object")
    final_result = evaluate_untouched_final(
        manifest,
        internal_audit,
        final_export,
        model_artifact,
    )
    execution = {
        "schema": EXECUTION_SCHEMA,
        "status": (
            "TEACHER_FIT_AND_FINAL_PASS"
            if final_result.get("status") == "PASS"
            else "TEACHER_FIT_PASS_FINAL_FAIL"
        ),
        "manifest_sha256": manifest.get("manifest_sha256"),
        "internal_audit_sha256": canonical_sha256(internal_audit),
        "development_export_sha256": canonical_sha256(development_export),
        "development_model_artifact_sha256": model_artifact.get("artifact_sha256"),
        "final_export_sha256": canonical_sha256(final_export),
        "final_result_sha256": final_result.get("result_sha256"),
        "final_file_opened_only_after_development_model_seal": True,
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    execution["execution_sha256"] = canonical_sha256(execution)
    return model_artifact, final_result, execution
