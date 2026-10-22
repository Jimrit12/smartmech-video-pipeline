"""Tests for VariationMemory concept novelty enforcement."""

import pytest

from smartmech.application.variation import ConceptTooSimilarError, VariationMemory
from smartmech.domain.concept import Concept


def test_variation_memory_allows_novel_concepts() -> None:
    vm = VariationMemory(db_path=":memory:", window_size=3, max_similarity_threshold=0.60)
    c1 = Concept(
        title="Skyscraper Alpha",
        premise="Building a gleaming skyscraper in Tokyo with modular cranes.",
        building_type="Office",
    )
    c2 = Concept(
        title="Subterranean Metro Hub",
        premise="Excavating an underground transit terminal in London with heavy boring machines.",
        building_type="Infrastructure",
    )

    vm.check_and_record(c1)
    vm.check_and_record(c2)
    assert len(vm.history()) == 2


def test_variation_memory_rejects_overly_similar_concept() -> None:
    vm = VariationMemory(db_path=":memory:", window_size=3, max_similarity_threshold=0.70)
    c1 = Concept(
        title="The Skyscraper Build",
        premise="Witness the construction of a gleaming steel and glass modular tower.",
        building_type="Skyscraper",
    )
    # Almost identical wording and keywords
    c2 = Concept(
        title="The Skyscraper Build",
        premise="Witness the construction of a gleaming steel and glass modular tower.",
        building_type="Skyscraper",
    )

    vm.check_and_record(c1)
    with pytest.raises(ConceptTooSimilarError, match="too similar"):
        vm.check_and_record(c2)


def test_variation_memory_window_eviction() -> None:
    vm = VariationMemory(db_path=":memory:", window_size=2)
    unique_data = [
        (
            "Excavation Pit",
            "Digging earth with massive diesel excavators in desert quarry",
            "Earthworks",
        ),
        ("Concrete Dam", "Pouring hydraulic gravity wall over raging alpine river gorge", "Dam"),
        (
            "Steel Suspension Bridge",
            "Spinning high-tensile cables between granite towers over ocean strait",
            "Bridge",
        ),
        ("Timber Dome", "Erecting glulam arch trusses inside geothermal bio-sanctuary", "Pavilion"),
    ]
    for title, premise, b_type in unique_data:
        vm.check_and_record(Concept(title=title, premise=premise, building_type=b_type))

    # Memory should be bounded to window size
    assert len(vm.history()) == 2
    assert vm.history()[-1].title == "Timber Dome"
