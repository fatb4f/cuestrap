from __future__ import annotations

import os
import shutil
import sys
import unittest
from copy import deepcopy
from pathlib import Path

from hypothesis import given, settings
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuestrap.s04.fixtures import valid_judgement_bundle  # noqa: E402
from cuestrap.s04.models import SubjectRef  # noqa: E402
from cuestrap.s04.oracle import CueOracle  # noqa: E402
from cuestrap.s04.properties import (  # noqa: E402
    OBJECT_ASSERTIONS,
    mutate_case_coherence,
    mutate_contract,
    mutate_judgement,
    mutate_projection,
)
from cuestrap.s04.strategies import (  # noqa: E402
    case_coherence_mutations,
    contract_mutations,
    judgement_mutations,
    projection_mutations,
    valid_contract_bundles,
    valid_judgement_bundles,
    valid_projection_bundles,
)

PROPERTY_SETTINGS = settings(derandomize=True, deadline=None, max_examples=12)


class S04ObjectModelTests(unittest.TestCase):
    def test_assertion_catalog_has_unique_ids(self) -> None:
        ids = [item.assertion_id for item in OBJECT_ASSERTIONS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 12)

    def test_transport_models_are_closed(self) -> None:
        with self.assertRaises(ValidationError):
            SubjectRef.model_validate({"subjectID": "subject", "unknown": True})

    def test_valid_seed_models_round_trip_by_alias(self) -> None:
        bundle = valid_judgement_bundle("roundtrip")
        reparsed = type(bundle).model_validate(bundle.cue_data())
        self.assertEqual(bundle, reparsed)


class S04CuePropertyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        candidate = os.environ.get("CUESTRAP_CUE") or shutil.which("cue")
        if not candidate:
            raise unittest.SkipTest("CUESTRAP_CUE is not configured")
        cls.oracle = CueOracle(ROOT, candidate)

    def test_package_is_canonical_and_structurally_valid(self) -> None:
        self.oracle.assert_package_is_formatted_and_valid()

    @PROPERTY_SETTINGS
    @given(valid_judgement_bundles())
    def test_valid_judgements_are_publishable(self, bundle) -> None:
        result = self.oracle.evaluate("#JudgementDerivation", bundle.cue_data(), "judgement")
        self.assertTrue(result.published, result.stderr)

    @PROPERTY_SETTINGS
    @given(valid_judgement_bundles(), judgement_mutations)
    def test_judgement_publication_forces_hidden_relation_checks(self, bundle, mutation) -> None:
        result = self.oracle.evaluate("#JudgementDerivation", mutate_judgement(bundle.cue_data(), mutation), "judgement")
        self.assertFalse(result.published, f"{mutation} unexpectedly published: {result.stdout}")

    @PROPERTY_SETTINGS
    @given(valid_judgement_bundles(), case_coherence_mutations)
    def test_case_local_coherence_is_required_for_judgement(self, bundle, mutation) -> None:
        result = self.oracle.evaluate("#JudgementDerivation", mutate_case_coherence(bundle.cue_data(), mutation), "judgement")
        self.assertFalse(result.published, f"{mutation} unexpectedly published: {result.stdout}")

    @PROPERTY_SETTINGS
    @given(valid_judgement_bundles())
    def test_unrelated_subject_extension_does_not_change_outcome(self, bundle) -> None:
        baseline = self.oracle.evaluate("#JudgementDerivation", bundle.cue_data(), "judgement.outcome")
        self.assertTrue(baseline.published, baseline.stderr)
        extended = deepcopy(bundle.cue_data())
        extended["realization"]["subjects"]["unrelated-subject"] = {
            "subjectID": "unrelated-subject",
            "language": "cue",
            "source": {"kind": "inline", "expression": "string"},
            "mediaType": "application/cue",
        }
        result = self.oracle.evaluate("#JudgementDerivation", extended, "judgement.outcome")
        self.assertTrue(result.published, result.stderr)
        self.assertEqual(baseline.json_value(), result.json_value())

    @PROPERTY_SETTINGS
    @given(valid_projection_bundles())
    def test_valid_projections_are_publishable(self, bundle) -> None:
        result = self.oracle.evaluate("#S04PPFProjectionDerivation", bundle.cue_data(), "projection")
        self.assertTrue(result.published, result.stderr)

    @PROPERTY_SETTINGS
    @given(valid_projection_bundles(), projection_mutations)
    def test_projection_publication_forces_all_proofs(self, bundle, mutation) -> None:
        result = self.oracle.evaluate("#S04PPFProjectionDerivation", mutate_projection(bundle.cue_data(), mutation), "projection")
        self.assertFalse(result.published, f"{mutation} unexpectedly published: {result.stdout}")

    @PROPERTY_SETTINGS
    @given(valid_contract_bundles())
    def test_valid_contracts_are_publishable(self, bundle) -> None:
        result = self.oracle.evaluate("#QualifiedS04ConsumerProfileContract", bundle.cue_data(), "contract")
        self.assertTrue(result.published, result.stderr)

    @PROPERTY_SETTINGS
    @given(valid_contract_bundles(), contract_mutations)
    def test_contract_publication_forces_realization_and_projection_proofs(self, bundle, mutation) -> None:
        result = self.oracle.evaluate("#QualifiedS04ConsumerProfileContract", mutate_contract(bundle.cue_data(), mutation), "contract")
        self.assertFalse(result.published, f"{mutation} unexpectedly published: {result.stdout}")


if __name__ == "__main__":
    unittest.main()
