"""S04 problem-package execution over the existing raw native probe transports."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from models import ProbeObservation, ProbeRequest, _digest_bytes, _json_bytes, parse_probe_request
from native import (
    CUE_MODULE_VERSION,
    CUE_REVISION,
    GOPY_REVISION,
    NativeBindingUnavailable,
    binding_identity,
    import_bindings,
    verify_extension_artifact,
)
from native_backend import (
    _gopy_string_slice,
    compare_native_backends,
    observe_cueprobe,
    observe_gopy_worker,
)
from runtime import run_process

PACKAGE_PROFILE = "s04-kattis-ppf-v0"
JUDGEMENT_SCHEMA = "cuestrap.s04-package-judgement/v0"
RUN_SCHEMA = "cuestrap.s04-package-run/v0"
ADAPTER_ID = "cuestrap-native-probe/v0"


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class SourceRef(_ClosedModel):
    path: str = Field(min_length=1)


class CandidateMaterialization(_ClosedModel):
    module_root: str = Field(alias="moduleRoot", min_length=1)
    package: str = Field(min_length=1)
    files: tuple[SourceRef, ...] = Field(min_length=1)
    subject_expression: str = Field(alias="subjectExpression", min_length=1)
    candidate_expression: str = Field(alias="candidateExpression", min_length=1)


class CandidateFixture(_ClosedModel):
    id: str = Field(min_length=1)
    case_id: str = Field(alias="caseID", min_length=1)
    polarity: Literal["accepted", "rejected"]
    required_verdict: Literal[
        "accepted",
        "rejected",
        "indeterminate",
        "infrastructureFailure",
        "unsupported",
        "invalidPackage",
    ] = Field(alias="requiredVerdict")
    materialization: CandidateMaterialization


class JudgeEntrypoint(_ClosedModel):
    module_root: str = Field(alias="moduleRoot", min_length=1)
    package: str = Field(min_length=1)
    files: tuple[SourceRef, ...] = Field(min_length=1)
    expression: Literal["#PackageJudgement"]


class ProblemMetadata(_ClosedModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    version: str = Field(min_length=1)
    family: Literal["LT-01"]


class ProblemPackage(_ClosedModel):
    profile: Literal[PACKAGE_PROFILE]
    metadata: ProblemMetadata
    authorities: dict[str, dict[str, object]]
    authorization: dict[str, object]
    realization: dict[str, object]
    capabilities: tuple[dict[str, object], ...] = Field(min_length=1)
    candidates: dict[str, CandidateFixture]
    limits: dict[str, object]
    evidence: tuple[dict[str, object], ...] = Field(min_length=1)
    judge: JudgeEntrypoint
    verdict_policy: dict[str, object] = Field(alias="verdictPolicy")

    @model_validator(mode="after")
    def candidate_keys_match(self) -> "ProblemPackage":
        for key, candidate in self.candidates.items():
            if key != candidate.id:
                raise ValueError(f"candidate key does not match id: {key}")
        return self


class ExecuteRealizationInput(_ClosedModel):
    package_path: str = Field(alias="packagePath", min_length=1)

    @model_validator(mode="after")
    def repository_relative(self) -> "ExecuteRealizationInput":
        path = Path(self.package_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("packagePath must be repository-relative")
        return self


def _safe_path(root: Path, relative: str, *, require_file: bool = True) -> Path:
    root = root.resolve(strict=True)
    candidate = (root / relative).resolve(strict=require_file)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"path escapes repository: {relative}") from error
    if require_file and not candidate.is_file():
        raise ValueError(f"expected file: {relative}")
    return candidate


def load_problem_package(root: Path, package_path: str | Path) -> tuple[ProblemPackage, dict[str, object]]:
    relative = str(package_path)
    path = _safe_path(root, relative)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("problem package must be a JSON object")
    try:
        package = ProblemPackage.model_validate(raw)
    except ValidationError as error:
        raise ValueError(f"invalid S04 problem package: {error}") from error
    return package, raw


def package_digest(raw: dict[str, object]) -> str:
    return _digest_bytes(_json_bytes(raw))


def candidate_probe_request(package: ProblemPackage, candidate: CandidateFixture) -> ProbeRequest:
    materialization = candidate.materialization
    return parse_probe_request(
        {
            "schema": "cuestrap.probe-request.v0",
            "probeID": f"{package.metadata.id}.{candidate.id}",
            "moduleRoot": materialization.module_root,
            "package": materialization.package,
            "files": [item.model_dump(by_alias=True) for item in materialization.files],
            "operation": "subsumes",
            "subjectExpression": materialization.subject_expression,
            "candidateExpression": materialization.candidate_expression,
            "concreteInput": None,
            "extensions": {
                "s04PackageID": package.metadata.id,
                "s04CandidateID": candidate.id,
                "s04CaseID": candidate.case_id,
            },
        }
    )


def _observation_document(observation: ProbeObservation) -> dict[str, object]:
    return observation.model_dump(by_alias=True, mode="json", exclude_none=True)


def _raw_digest(observation: ProbeObservation) -> str:
    return _digest_bytes(_json_bytes(_observation_document(observation)))


def _pair_digest(left: ProbeObservation, right: ProbeObservation) -> str:
    return _digest_bytes(_json_bytes([_observation_document(left), _observation_document(right)]))


def _fact(
    *,
    candidate: CandidateFixture,
    operation_plan_id: str,
    subject_digest: str,
    raw_digests: list[str],
    comparison_digest: str,
    kind: str,
    state: Literal["observed", "unavailable", "indeterminate"],
    value: bool | None = None,
) -> dict[str, object]:
    document: dict[str, object] = {
        "source": "observation",
        "id": f"{candidate.id}.{kind}",
        "caseID": candidate.case_id,
        "kind": kind,
        "status": state,
        "provenance": {
            "adapter": ADAPTER_ID,
            "backend": "qualified-native-pair",
            "operationPlanID": operation_plan_id,
            "subjectDigest": subject_digest,
            "rawObservationDigests": raw_digests,
            "backendComparisonDigest": comparison_digest,
        },
    }
    if value is not None:
        document["value"] = value
    return document


def normalize_native_observations(
    candidate: CandidateFixture,
    operation_plan_id: str,
    gopy: ProbeObservation,
    cueprobe: ProbeObservation,
    comparison: dict[str, object],
) -> list[dict[str, object]]:
    """Map qualified raw observations into S04 facts without consulting expectations."""

    raw_digests = [_raw_digest(gopy), _raw_digest(cueprobe)]
    comparison_digest = _digest_bytes(_json_bytes(comparison))
    subject_digest = gopy.subject_digest

    if comparison.get("state") == "capability-gap":
        return [
            _fact(
                candidate=candidate,
                operation_plan_id=operation_plan_id,
                subject_digest=subject_digest,
                raw_digests=raw_digests,
                comparison_digest=comparison_digest,
                kind="backendCapabilityAbsent",
                state="unavailable",
                value=False,
            )
        ]

    if comparison.get("state") in {
        "subject-identity-mismatch",
        "engine-identity-mismatch",
        "incomparable",
        "shared-facts-differ",
    }:
        return [
            _fact(
                candidate=candidate,
                operation_plan_id=operation_plan_id,
                subject_digest=subject_digest,
                raw_digests=raw_digests,
                comparison_digest=comparison_digest,
                kind="invalidObservation",
                state="indeterminate",
            )
        ]

    values = (gopy.facts.get("subsumes"), cueprobe.facts.get("subsumes"))
    exact = (
        comparison.get("state") == "shared-facts-equal"
        and comparison.get("equivalentSubjects") is True
        and comparison.get("equivalentEngines") is True
        and gopy.state == "compare"
        and cueprobe.state == "compare"
        and values[0] is values[1]
        and isinstance(values[0], bool)
    )
    if exact:
        kind = "orderingHolds" if values[0] else "orderingDoesNotHold"
        return [
            _fact(
                candidate=candidate,
                operation_plan_id=operation_plan_id,
                subject_digest=subject_digest,
                raw_digests=raw_digests,
                comparison_digest=comparison_digest,
                kind=kind,
                state="observed",
                value=True,
            )
        ]

    return [
        _fact(
            candidate=candidate,
            operation_plan_id=operation_plan_id,
            subject_digest=subject_digest,
            raw_digests=raw_digests,
            comparison_digest=comparison_digest,
            kind="runnerFailure",
            state="indeterminate",
        )
    ]


def _gopy_module_root(root: Path) -> Path:
    configured = os.environ.get("CUESTRAP_GOPY_MODULE_DIR")
    return Path(configured).resolve() if configured else root / "src" / "cue-workbook" / "cue_native"


def _gopy_environment(root: Path, module_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    workbook_root = root / "src" / "cue-workbook"
    import_roots = [module_root.parent, workbook_root] if os.environ.get("CUESTRAP_GOPY_MODULE_DIR") else [workbook_root]
    pythonpath = list(dict.fromkeys(str(path) for path in import_roots))
    if environment.get("PYTHONPATH"):
        pythonpath.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(pythonpath)
    return environment


def _judge_payload(
    raw_package: dict[str, object],
    digest: str,
    candidate_id: str,
    observations: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "cuestrap.s04-judgement-request/v0",
        "request": {
            "package": raw_package,
            "packageDigest": digest,
            "candidateID": candidate_id,
            "observations": observations,
        },
    }


def _run_judge_worker(
    root: Path,
    package: ProblemPackage,
    raw_package: dict[str, object],
    digest: str,
    candidate_id: str,
    observations: list[dict[str, object]],
) -> dict[str, object]:
    module_root = _gopy_module_root(root)
    if not module_root.exists():
        raise NativeBindingUnavailable(f"generated extension missing: {module_root}")
    process = run_process(
        (
            sys.executable,
            str((root / "src" / "cue-workbook" / "workbook_cli.py").resolve()),
            "--s04-judge-worker",
        ),
        cwd=root,
        env=_gopy_environment(root, module_root),
        input_bytes=_json_bytes(_judge_payload(raw_package, digest, candidate_id, observations)),
        timeout=int(package.limits.get("timeoutSeconds", 60)),
    )
    if process.state != "exited" or process.exit_code != 0:
        raise RuntimeError(process.stderr or f"S04 judge worker failed: {process.state}")
    value = json.loads(process.stdout)
    if not isinstance(value, dict) or value.get("schema") != JUDGEMENT_SCHEMA:
        raise RuntimeError("S04 judge worker returned an invalid envelope")
    if value.get("packageDigest") != digest or value.get("candidateID") != candidate_id:
        raise RuntimeError("S04 judge worker changed package or candidate identity")
    return value


def _lookup(value: Any, path: str) -> Any:
    return value.Lookup(path)


def s04_judge_worker_main() -> int:
    """Execute the CUE-owned package judge in an isolated gopy worker process."""

    try:
        payload = json.load(sys.stdin)
        if payload.get("schema") != "cuestrap.s04-judgement-request/v0":
            raise ValueError("invalid S04 judgement request schema")
        request = payload.get("request")
        if not isinstance(request, dict):
            raise ValueError("S04 judgement request is not an object")
        raw_package = request.get("package")
        if not isinstance(raw_package, dict):
            raise ValueError("S04 judgement request has no problem package")
        package = ProblemPackage.model_validate(raw_package)
        digest = package_digest(raw_package)
        if request.get("packageDigest") != digest:
            raise ValueError("S04 package digest mismatch")
        candidate_id = request.get("candidateID")
        if not isinstance(candidate_id, str) or candidate_id not in package.candidates:
            raise ValueError("unknown S04 candidate")

        repository_root = Path.cwd().resolve(strict=True)
        module = _safe_path(repository_root, package.judge.module_root, require_file=False)
        if not module.is_dir():
            raise ValueError("S04 judge module root is not a directory")
        files = [
            str(_safe_path(repository_root, item.path).relative_to(module))
            for item in package.judge.files
        ]

        bindings = import_bindings()
        identity = binding_identity(bindings)
        context = bindings.NewContext()
        loader = context.OpenLoader(str(module))
        root = loader.LoadFiles(_gopy_string_slice(bindings, files), package.judge.package)
        if root.IsBottom():
            raise RuntimeError(root.Error())
        judge = _lookup(root, package.judge.expression)
        if judge.IsBottom():
            raise RuntimeError(judge.Error())
        concrete = context.CompileString(
            json.dumps({"request": request}, sort_keys=True, separators=(",", ":")),
            "s04-judgement-input.json",
        )
        evaluated = judge.Unify(concrete)
        if evaluated.IsBottom():
            raise RuntimeError(evaluated.Error())
        projection = json.loads(evaluated.ProjectJSON().JSON())
        if not projection.get("ok"):
            raise RuntimeError(json.dumps(projection.get("diagnostics", []), sort_keys=True))
        projected = json.loads(projection["json_value"])
        judgement = projected.get("judgement")
        if not isinstance(judgement, dict):
            raise RuntimeError("CUE judge did not project a judgement")

        module_root = _gopy_module_root(repository_root)
        artifact = verify_extension_artifact(repository_root, module_root)
        print(
            json.dumps(
                {
                    "schema": JUDGEMENT_SCHEMA,
                    "packageID": package.metadata.id,
                    "packageDigest": digest,
                    "candidateID": candidate_id,
                    "judgement": judgement,
                    "engine": {
                        "cueRevision": CUE_REVISION,
                        "cueModuleVersion": CUE_MODULE_VERSION,
                        "observedCUEModuleVersion": identity.get("observed_cue_module_version"),
                        "gopyRevision": GOPY_REVISION,
                        **artifact,
                    },
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except Exception as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}), file=sys.stderr)
        return 2


def _git_private_root(root: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    directory = Path(result.stdout.strip())
    if not directory.is_absolute():
        directory = root / directory
    return directory.resolve() / "cuestrap-s04"


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _manifest(directory: Path) -> dict[str, object]:
    files = []
    for path in sorted(item for item in directory.rglob("*.json") if item.name != "manifest.json"):
        files.append(
            {
                "path": path.relative_to(directory).as_posix(),
                "digest": _digest_bytes(path.read_bytes()),
            }
        )
    return {"schema": "cuestrap.s04-evidence-manifest/v0", "files": files}


def execute_s04_package(
    root: Path,
    package_path: str | Path,
    *,
    evidence_root: Path | None = None,
) -> dict[str, object]:
    """Execute one bounded S04 package and persist its independent judgement evidence."""

    root = root.resolve(strict=True)
    package, raw_package = load_problem_package(root, package_path)
    digest = package_digest(raw_package)
    run_id = f"{time.time_ns()}"
    directory = (evidence_root or _git_private_root(root)) / digest.removeprefix("sha256:") / run_id
    _atomic_json(directory / "package.snapshot.json", raw_package)
    _atomic_json(
        directory / "package.identity.json",
        {"packageID": package.metadata.id, "packageDigest": digest, "runID": run_id},
    )

    candidate_results: list[dict[str, object]] = []
    for candidate_id in sorted(package.candidates):
        candidate = package.candidates[candidate_id]
        request = candidate_probe_request(package, candidate)
        case = package.realization["cases"][candidate.case_id]
        operation_plan_id = str(case["operation"]["id"])
        gopy = observe_gopy_worker(root, request)
        cueprobe = observe_cueprobe(root, request)
        comparison = compare_native_backends(gopy, cueprobe)
        facts = normalize_native_observations(
            candidate,
            operation_plan_id,
            gopy,
            cueprobe,
            comparison,
        )
        raw = {
            "request": request.model_dump(by_alias=True, mode="json", exclude_none=True),
            "gopyWorker": _observation_document(gopy),
            "cueprobe": _observation_document(cueprobe),
            "backendComparison": comparison,
        }
        _atomic_json(directory / "candidates" / candidate.id / "raw-observations.json", raw)
        _atomic_json(directory / "candidates" / candidate.id / "normalized-facts.json", facts)
        judgement = _run_judge_worker(
            root,
            package,
            raw_package,
            digest,
            candidate.id,
            facts,
        )
        _atomic_json(directory / "candidates" / candidate.id / "judgement.json", judgement)
        _atomic_json(
            directory / "candidates" / candidate.id / "comparison-trace.json",
            judgement["judgement"].get("comparisonTrace", []),
        )
        candidate_results.append(
            {
                "candidateID": candidate.id,
                "caseID": candidate.case_id,
                "rawObservationDigest": _pair_digest(gopy, cueprobe),
                "normalizedFactIDs": [str(item["id"]) for item in facts],
                "judgement": judgement["judgement"],
            }
        )

    manifest = _manifest(directory)
    _atomic_json(directory / "manifest.json", manifest)
    return {
        "schema": RUN_SCHEMA,
        "runID": run_id,
        "packageID": package.metadata.id,
        "packageDigest": digest,
        "evidenceDirectory": str(directory),
        "candidates": candidate_results,
        "manifestDigest": _digest_bytes(_json_bytes(manifest)),
    }
