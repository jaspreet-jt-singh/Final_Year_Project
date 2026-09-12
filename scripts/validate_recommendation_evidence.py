"""Offline, synthetic recommendation evidence; never calls a live provider.

Run from the repository root. New receipts are exclusive-created; old evidence is
not replaced. A structural pass is deliberately separate from clinical review.
"""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import re
import sys
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.api.schemas import RecommendationRequest, RecommendationResponse  # noqa: E402
from backend.domain.policy import CONDITIONS, GOALS  # noqa: E402
from backend.services.providers import GroqProvider  # noqa: E402
from backend.services.recommendation_service import RecommendationBusy, RecommendationService  # noqa: E402
from backend.settings import Settings  # noqa: E402

FIXTURE_VERSION = "synthetic-recommendations-v1"
RUNTIME_PATHS = [
    "backend/api/schemas.py", "backend/api/recommendations.py",
    "backend/domain/nutrition_policy.json", "backend/domain/policy.py",
    "backend/domain/rules.py", "backend/domain/recommendations.py",
    "backend/services/providers.py", "backend/services/recommendation_service.py",
    "backend/settings.py", "backend/observability.py", "pyproject.toml", "uv.lock",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def fixture_scenarios():
    """Deliberately invented foods/macros, not nutritional reference standards."""
    known = {"food_label": "Synthetic_A", "display_name": "Synthetic A", "macros": {
        "calories": 123.0, "protein_g": 4.0, "carbs_g": 20.0, "fat_g": 3.0,
    }}
    second = {"food_label": "Synthetic_B", "display_name": "Synthetic B", "macros": {
        "calories": 205.0, "protein_g": 10.0, "carbs_g": 30.0, "fat_g": 5.0,
    }}
    unknown = {"food_label": "Synthetic_Unknown", "display_name": "Synthetic Unknown", "macros": None}
    return [
        {"id": "known_single", "foods": [known]},
        {"id": "known_multiple", "foods": [known, second, {**second, "food_label": "Synthetic_C", "display_name": "Synthetic C"}]},
        {"id": "unknown_only", "foods": [unknown]},
        {"id": "mixed_known_unknown", "foods": [known, unknown]},
        {"id": "same_name_boundary_macros", "foods": [{**known, "macros": {"calories": 10000.0, "protein_g": 0.0, "carbs_g": 10000.0, "fat_g": 0.0}}]},
        {"id": "nullable_display_name", "foods": [{**known, "display_name": None}]},
    ]


def canonical_request(foods, goal="maintenance", condition="none"):
    request = RecommendationRequest.model_validate({
        "detected_foods": foods, "user_goal": goal, "health_condition": condition,
    })
    # Match the public router, rather than bypass its null-name sanitation.
    return [food.model_dump(exclude_none=True) for food in request.detected_foods], request.user_goal, request.health_condition


def triage_text(recommendations, condition, unknown):
    """Lexical review prompts only: not a medical safety or correctness score."""
    joined = " ".join(recommendations).lower()
    flags = []
    if any(token in joined for token in ("after having", "after your", "after synthetic")):
        flags.append("scan_may_be_worded_as_consumption")
    if any(token in joined for token in (" is fine", " is good", "fits well in a balanced diet")):
        flags.append("food_suitability_reassurance_without_assessment")
    if condition != "none":
        flags.append("condition_specific_advice_requires_qualified_review")
    if unknown and not any(token in joined for token in ("unknown", "unavailable", "missing nutrition")):
        flags.append("missing_nutrition_not_explicitly_acknowledged")
    # Avoid counting the synthetic food name "Unknown" as an uncertainty warning.
    if unknown and "Synthetic Unknown" in " ".join(recommendations):
        stripped = joined.replace("synthetic unknown", "synthetic food")
        if not any(token in stripped for token in ("unknown", "unavailable", "missing nutrition")):
            flags.append("missing_nutrition_not_explicitly_acknowledged")
    return sorted(set(flags))


async def run_matrix():
    service = RecommendationService(Settings(production=True), providers=[])
    rows = []
    started = time.perf_counter()
    try:
        for goal in GOALS:
            for condition in CONDITIONS:
                for scenario in fixture_scenarios():
                    tick = time.perf_counter()
                    foods, normalized_goal, normalized_condition = canonical_request(scenario["foods"], goal, condition)
                    response = await service.get_recommendations(foods, normalized_goal, normalized_condition)
                    wire = RecommendationResponse.model_validate(response).model_dump(mode="json")
                    prompt = service._build_prompt(foods, GOALS[goal]["name"], condition)
                    has_unknown = any(not food.get("macros") for food in foods)
                    checks = {
                        "exactly_three_nonempty_strings": len(wire["recommendations"]) == 3 and all(text.strip() for text in wire["recommendations"]),
                        "matching_context": wire["health_condition"] == condition,
                        "fallback_source": wire["source"] == "fallback",
                        "per_100g_prompt_boundary": "per 100 g, NOT the amount eaten" in prompt,
                        "no_consumption_inference_prompt": "A scan does not establish consumption" in prompt,
                        "unknown_prompt_boundary": not has_unknown or "Nutrition unavailable; do not treat as zero" in prompt,
                        "all_foods_in_prompt": all((food.get("display_name") or food["food_label"]) in prompt for food in foods),
                    }
                    rows.append({
                        "id": f"{goal}/{condition}/{scenario['id']}", "goal": goal, "condition": condition,
                        "scenario": scenario["id"], "response": wire, "checks": checks,
                        "status": "pass" if all(checks.values()) else "fail",
                        "review_flags": triage_text(wire["recommendations"], condition, has_unknown),
                        "duration_seconds": round(time.perf_counter() - tick, 6),
                    })
    finally:
        await service.close()
    indexes = {(row["goal"], row["condition"], row["scenario"]): row["response"]["recommendations"] for row in rows}
    return {
        "dimensions": {"goals": 4, "contexts": 9, "synthetic_scenarios": 6}, "cases": rows,
        "passed": sum(row["status"] == "pass" for row in rows), "total": len(rows),
        "duration_seconds": round(time.perf_counter() - started, 6),
        "lexical_flag_counts": dict(Counter(flag for row in rows for flag in row["review_flags"])),
        "observations": {
            "same_named_food_different_macros_produces_identical_fallback": all(indexes[goal, condition, "known_single"] == indexes[goal, condition, "same_name_boundary_macros"] for goal in GOALS for condition in CONDITIONS),
            "non_general_context_fallback_is_identical_across_goals": all(len({json.dumps(indexes[goal, condition, "known_single"]) for goal in GOALS}) == 1 for condition in CONDITIONS if condition != "none"),
            "interpretation": "Template behavior, not evidence of individualized nutrient balancing or clinical suitability.",
        },
    }


def completion(content="- Synthetic first\n- Synthetic second\n- Synthetic third"):
    return {"id": "synthetic-completion", "object": "chat.completion", "created": 0, "model": "synthetic-model", "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}]}


@contextmanager
def offline_provider(handler):
    """Real SDK and adapter; only its network transport is replaced."""
    import groq
    import httpx
    from pydantic import SecretStr

    real_client = groq.AsyncGroq
    configuration = {}

    def factory(**kwargs):
        configuration.update(timeout=kwargs["timeout"], max_retries=kwargs["max_retries"])
        return real_client(**kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with patch("groq.AsyncGroq", side_effect=factory):
        provider = GroqProvider(Settings(production=True, groq_key=SecretStr("synthetic-key-not-a-credential")))
    try:
        yield provider, configuration
    finally:
        # The async caller owns closure; an assertion catches a missing finally.
        assert provider.client.is_closed(), "Mock provider client was not closed"


async def run_adapter_case(case):
    import httpx

    attempts = []
    cleanup = []
    requested_timeouts = []
    original_wait_for = asyncio.wait_for

    async def handler(request):
        body = json.loads(request.content)
        # Do not retain headers, prompts, or request/response secrets in receipts.
        attempts.append({"method": request.method, "path": request.url.path, "model": body.get("model"), "message_roles": [entry["role"] for entry in body.get("messages", [])]})
        if case == "transport_timeout":
            raise httpx.ReadTimeout("Synthetic timeout", request=request)
        if case == "outer_timeout":
            try:
                await asyncio.Event().wait()
            finally:
                cleanup.append("transport_cancelled")
        status = {"quota_429": 429, "server_500": 500, "auth_401": 401}.get(case, 200)
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "Synthetic provider error", "type": "synthetic"}}, headers={"retry-after": "0"})
        if case == "invalid_json":
            return httpx.Response(200, content=b"not json", headers={"content-type": "application/json"})
        payload = completion({
            "empty_content": "", "null_content": None, "two_bullets": "- Synthetic first\n- Synthetic second",
            "four_bullets": "- Synthetic first\n- Synthetic second\n- Synthetic third\n- Synthetic discarded fourth",
            "prose_only": "Synthetic unstructured prose.", "numbered_only": "1. Synthetic first\n2. Synthetic second\n3. Synthetic third",
        }.get(case, "- Synthetic first\n- Synthetic second\n- Synthetic third"))
        if case == "empty_choices":
            payload["choices"] = []
        if case == "missing_choices":
            del payload["choices"]
        return httpx.Response(200, json=payload)

    async def accelerated_timeout(awaitable, timeout):
        requested_timeouts.append(timeout)
        return await original_wait_for(awaitable, timeout=0.02)

    tick = time.perf_counter()
    with offline_provider(handler) as (provider, configuration):
        service = RecommendationService(Settings(production=True), providers=[provider])
        try:
            if case == "outer_timeout":
                # Check the real configured duration, without spending 20 s in a fixture.
                with patch("backend.services.providers.asyncio.wait_for", side_effect=accelerated_timeout):
                    result = await service.get_recommendations(*canonical_request(fixture_scenarios()[0]["foods"], condition="diabetic"))
            else:
                result = await service.get_recommendations(*canonical_request(fixture_scenarios()[0]["foods"], condition="diabetic"))
        finally:
            await service.close()
        expected_source = "groq" if case in ("success", "four_bullets") else "fallback"
        checks = {
            "real_sdk_timeout_20": configuration["timeout"] == 20,
            "sdk_retries_disabled": configuration["max_retries"] == 0,
            "exactly_one_transport_attempt": len(attempts) == 1,
            "expected_source": result["source"] == expected_source,
            "canonical_context_retained": result["health_condition"] == "diabetic",
            "valid_response": bool(RecommendationResponse.model_validate(result)),
            "client_closed": provider.client.is_closed(),
        }
        if case == "outer_timeout":
            checks["outer_timeout_20_and_cancel_cleanup"] = requested_timeouts == [20.0] and cleanup == ["transport_cancelled"]
        if case == "four_bullets":
            checks["extra_bullet_truncated_not_rejected"] = result["recommendations"] == ["Synthetic first", "Synthetic second", "Synthetic third"]
        return {"id": case, "status": "pass" if all(checks.values()) else "fail", "checks": checks,
                "observed_source": result["source"], "attempts": attempts, "configuration": configuration,
                "duration_seconds": round(time.perf_counter() - tick, 6),
                "timeout_test_method": "Recorded real 20-second argument; accelerated outer deadline to 0.02 seconds" if case == "outer_timeout" else None}


async def run_capacity_case():
    import httpx

    attempts = []
    started_two = asyncio.Event()
    cancelled = []
    hold = True

    async def handler(request):
        attempts.append(request.url.path)
        if hold:
            if len(attempts) == 2:
                started_two.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append("cancelled")
        return httpx.Response(200, json=completion())

    tick = time.perf_counter()
    tasks = []
    with offline_provider(handler) as (provider, configuration):
        service = RecommendationService(Settings(production=True), providers=[provider])
        try:
            args = canonical_request(fixture_scenarios()[0]["foods"])
            tasks = [asyncio.create_task(service.get_recommendations(*args)) for _ in range(2)]
            await asyncio.wait_for(started_two.wait(), timeout=3)
            busy = False
            try:
                await service.get_recommendations(*args)
            except RecommendationBusy:
                busy = True
            before_cancel = len(attempts)
            for task in tasks:
                task.cancel()
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            hold = False
            recovered = await service.get_recommendations(*args)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await service.close()
        checks = {"third_request_busy_without_transport_attempt": busy and before_cancel == 2,
                  "both_cancellations_propagated": all(isinstance(value, asyncio.CancelledError) for value in outcomes),
                  "both_transport_handlers_cleaned": len(cancelled) == 2,
                  "capacity_reusable_after_cancel": recovered["source"] == "groq" and len(attempts) == 3,
                  "client_closed": provider.client.is_closed()}
        return {"id": "capacity_two_no_queue_cancel_recovery", "status": "pass" if all(checks.values()) else "fail",
                "checks": checks, "configuration": configuration, "total_transport_attempts": len(attempts),
                "duration_seconds": round(time.perf_counter() - tick, 6)}


async def run_adapter_suite():
    cases = ["success", "quota_429", "server_500", "auth_401", "transport_timeout", "outer_timeout",
             "invalid_json", "empty_choices", "missing_choices", "empty_content", "null_content",
             "two_bullets", "four_bullets", "prose_only", "numbered_only"]
    rows = []
    for case in cases:
        try:
            rows.append(await run_adapter_case(case))
        except Exception as exc:
            rows.append({"id": case, "status": "fail", "error_type": type(exc).__name__})
    try:
        rows.append(await run_capacity_case())
    except Exception as exc:
        rows.append({"id": "capacity_two_no_queue_cancel_recovery", "status": "fail", "error_type": type(exc).__name__})
    return {"cases": rows, "total": len(rows), "passed": sum(row["status"] == "pass" for row in rows),
            "boundary": "Actual adapter and installed SDK with HTTPX MockTransport; no live provider or production latency/availability claim."}


def review_rubric():
    return {
        "status": "pending_qualified_expert", "clinical_validation_performed": False,
        "scope": "All 12 distinct fallback templates (4 general goals, 8 condition overrides), canonical policy modifiers, and representative provider outputs if later authorized.",
        "reviewer_requirements": "Named qualified dietitian/clinician; disclose expertise, conflicts, review date and policy/template hashes. Software reviewers cannot approve clinical suitability.",
        "required_dimensions": [
            "Whether a scan is incorrectly described as food consumed or a food is assured suitable without assessment.",
            "Whether unavailable nutrition, approximate mappings, missing portion/meal history and unobserved nutrients are acknowledged.",
            "Condition terminology and heterogeneity; avoid extrapolating one disease subtype/stage to all users.",
            "Contraindications and interactions, including overlapping conditions, medication, renal status, fluid/protein/potassium and iodine advice.",
            "Evidence traceability and dose specificity of every nutrient/physiology claim; distinguish general education from treatment.",
            "Consistency between prompt restrictions, fallback text, health badge, source label and visible disclaimer.",
            "Whether a safe abstention/referral is needed; inherited rules and a disclaimer do not establish safety.",
        ],
        "disposition_per_item": ["acceptable within stated scope", "revision required", "exclude pending evidence", "outside reviewer expertise"],
        "release_gate": "No clinical efficacy/safety or individualized dietary-management claim without appropriate independent evidence and qualified approval. Changes require separately authorized runtime edits and a new evidence run.",
    }


def input_identity(baseline):
    recorded = {entry["path"]: entry["sha256"] for entry in baseline["files"]}
    rows = []
    for name in RUNTIME_PATHS:
        path = ROOT / name
        sha = digest(path.read_bytes())
        rows.append({"path": name, "sha256": sha, "baseline_sha256": recorded.get(name), "matches_baseline": recorded.get(name) == sha})
    return rows


async def generate_report(run_id, command):
    if not re.fullmatch(r"validation-[a-z0-9-]+", run_id):
        raise ValueError("Run ID must start with validation- and contain only lower-case letters, digits and hyphens")
    report_dir = ROOT / "research/evidence" / run_id
    local_dir = ROOT / ".deployment/research" / run_id
    baseline_path = report_dir / "baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("run_id") != run_id or not local_dir.is_dir():
        raise ValueError("Matching frozen baseline/local evidence directory required")
    targets = [report_dir / "recommendations.json", local_dir / "recommendations.json"]
    if any(path.exists() for path in targets):
        raise FileExistsError("Recommendation receipt already exists; refusing overwrite")
    started = time.perf_counter()
    report = {
        "schema_version": 1, "run_id": run_id, "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": command, "baseline_sha256": digest(baseline_path.read_bytes()),
        "source_commit": baseline["source_commit"], "runtime_inputs": input_identity(baseline),
        "validator": {"path": "scripts/validate_recommendation_evidence.py", "sha256": digest(Path(__file__).read_bytes())},
        "fixture_identity": {"version": FIXTURE_VERSION, "sha256": digest(canonical_bytes(fixture_scenarios())), "scenarios": fixture_scenarios(), "provenance": "Invented deterministic unit fixtures; not images, patients, nutrient standards, clinical cases, or an independent evaluation dataset."},
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "packages": {name: importlib.metadata.version(name) for name in ("groq", "httpx", "pydantic", "fastapi")}},
        "boundaries": {"live_provider_calls": 0, "real_credentials_loaded": False, "runtime_files_edited": False,
                       "clinical_validity_established": False, "production_timing_established": False},
    }
    report["matrix"] = await run_matrix()
    report["provider_adapter"] = await run_adapter_suite()
    report["qualified_review"] = review_rubric()
    report["duration_seconds"] = round(time.perf_counter() - started, 6)
    report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["structural_status"] = "pass" if all([
        report["matrix"]["passed"] == report["matrix"]["total"] == 216,
        report["provider_adapter"]["passed"] == report["provider_adapter"]["total"],
        all(row["matches_baseline"] for row in report["runtime_inputs"]),
    ]) else "fail"
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    for path in targets:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    report = asyncio.run(generate_report(args.run_id, [sys.executable, *sys.argv]))
    print(json.dumps({"status": report["structural_status"], "matrix": f"{report['matrix']['passed']}/216", "provider_cases": f"{report['provider_adapter']['passed']}/{report['provider_adapter']['total']}", "clinical_review": "pending_qualified_expert", "report": f"research/evidence/{args.run_id}/recommendations.json"}))
    return 0 if report["structural_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
