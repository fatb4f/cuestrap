"""Hypothesis strategies for valid S04 graphs and controlled mutations."""
from __future__ import annotations

from hypothesis import strategies as st

from .fixtures import valid_judgement_bundle, valid_projection_bundle, valid_qualified_contract_bundle
from .models import JudgementBundle, ProjectionBundle, QualifiedContractBundle
from .properties import CaseCoherenceMutation, ContractMutation, JudgementMutation, ProjectionMutation


@st.composite
def safe_prefixes(draw: st.DrawFn) -> str:
    stem = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6))
    suffix = draw(st.integers(min_value=0, max_value=999))
    return f"{stem}-{suffix}"


@st.composite
def valid_judgement_bundles(draw: st.DrawFn) -> JudgementBundle:
    return valid_judgement_bundle(draw(safe_prefixes()), observed_value=draw(st.booleans()))


@st.composite
def valid_projection_bundles(draw: st.DrawFn) -> ProjectionBundle:
    return valid_projection_bundle(draw(safe_prefixes()))


@st.composite
def valid_contract_bundles(draw: st.DrawFn) -> QualifiedContractBundle:
    return valid_qualified_contract_bundle(draw(safe_prefixes()))


judgement_mutations = st.sampled_from(list(JudgementMutation))
case_coherence_mutations = st.sampled_from(list(CaseCoherenceMutation))
projection_mutations = st.sampled_from(list(ProjectionMutation))
contract_mutations = st.sampled_from(list(ContractMutation))
