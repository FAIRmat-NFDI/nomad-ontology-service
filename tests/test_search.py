from pathlib import Path

import owlready2
import pytest

from nomad_ontology_service import OntologyConfig
from nomad_ontology_service.apis.app import (
    _fetch_class_info,
    _label_index,
    _search_by_label,
)

DATA = Path(__file__).parent / 'data'


@pytest.fixture
def ontology():
    # Own World so tests don't share owlready2's global state.
    world = owlready2.World()
    return world.get_ontology(str(DATA / 'food_sample.owl')).load()


@pytest.fixture
def cfg(request):
    # Unique name per test: the label index is cached by config name.
    return OntologyConfig(
        name=f'test-{request.node.name}',
        owl_url=str(DATA / 'food_sample.owl'),
        included_iri_patterns=['example.org/food'],
    )


def test_search_matches_synonym(ontology, cfg):
    top = _search_by_label(ontology, 'jeera', cfg, limit=1)[0]
    assert top['label'] == 'jeera'
    assert top['iri'].endswith('FOOD_0003')


def test_short_labels_are_not_indexed(ontology, cfg):
    assert 'an' not in _label_index(ontology, cfg)
    labels = [r['label'] for r in _search_by_label(ontology, 'Ground Coriander', cfg, 5)]
    assert 'an' not in labels


@pytest.mark.parametrize(
    'query, expected', [('Ground Cumin', 'cumin'), ('Ground Coriander', 'coriander')]
)
def test_tie_prefers_head_noun(ontology, cfg, query, expected):
    results = _search_by_label(ontology, query, cfg, limit=5)
    assert results[0]['label'] == expected


def test_class_info_returns_direct_parent(ontology, cfg):
    info = _fetch_class_info(ontology, 'FOOD_0003', cfg)
    assert info['label'] == 'cumin'
    assert info['alt_labels'] == ['jeera']
    assert info['parents'] == [{'label': 'spice', 'name': 'FOOD_0002'}]


def test_class_info_unknown_class_raises(ontology, cfg):
    with pytest.raises(ValueError):
        _fetch_class_info(ontology, 'DOES_NOT_EXIST', cfg)
