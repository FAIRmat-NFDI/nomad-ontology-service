from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from nomad.config import config
from owlready2 import ThingClass, get_ontology, Ontology, Restriction, And, Or
from owlready2.base import rdf_type, owl_class
from nomad_ontology_service import OntologyConfig
from pathlib import Path
from rapidfuzz import fuzz, process, utils as rf_utils
import logging

from nomad_ontology_service.apis import app

logger = logging.getLogger(__name__)
entry_point = config.get_plugin_entry_point("nomad_ontology_service:ontology_service")

app = FastAPI(
    root_path=f"{config.services.api_base_path}/{entry_point.prefix}",
    title="Ontology Service",
    description="Generic ontology querying service.",
)

def _resolve(owl_url: str) -> str:
    if owl_url.startswith("nomad_tmp://"):
        rel = owl_url.removeprefix("nomad_tmp://")
        return str(Path(config.fs.tmp) / rel)
    return owl_url  

def _fetch_superclasses(ontology: Ontology, class_name: str, cfg: OntologyConfig) -> list[str]:
    """Generic ancestor traversal, filtered by the provided ontology config."""
    cls = ontology.search_one(iri="*" + class_name)
    if cls is None:
        raise ValueError(f"Class '{class_name}' not found in the ontology.")

    unwanted: set[str] = set()
    for root_iri in cfg.excluded_root_class_iris:
        root_cls = ontology.search_one(iri=root_iri)
        if root_cls is not None:
            unwanted |= {sc.iri for sc in root_cls.ancestors() if hasattr(sc, "iri")}
            unwanted.add(root_iri)

    return [
        sc.label.first() if (hasattr(sc, 'label') and sc.label) else sc.name
        for sc in cls.ancestors()
        if hasattr(sc, "iri")
        and sc.iri not in unwanted
        and any(pat in sc.iri for pat in cfg.included_iri_patterns)
        and isinstance(sc, ThingClass)
    ]

def _safe_descendants(start_cls) -> set:
    """Safely traverse descendants, catching owlready2 metaclass conflicts."""
    seen = set()
    queue = [start_cls]
    while queue:
        current = queue.pop(0)
        if current not in seen:
            seen.add(current)
            try:
                subs = current.subclasses()
                for sub in subs:
                    if hasattr(sub, "iri") and sub not in seen:
                        queue.append(sub)
            except TypeError as e:
                logger.warning(f"Metaclass conflict while fetching subclasses for {current}: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error fetching subclasses for {current}: {e}")
    return seen

def _fetch_descendants(ontology: Ontology, class_name: str, cfg: OntologyConfig) -> list[str]:
    """Generic descendant traversal, filtered by the provided ontology config."""
    cls = ontology.search_one(iri="*" + class_name)
    if cls is None:
        raise ValueError(f"Class '{class_name}' not found in the ontology.")

    return [
        sc.label.first() if (hasattr(sc, 'label') and sc.label) else sc.name
        for sc in _safe_descendants(cls)
        if hasattr(sc, "iri")
        and any(pat in sc.iri for pat in cfg.included_iri_patterns)
        and isinstance(sc, ThingClass)
    ]

_label_index_cache: dict[str, dict[str, str]] = {}

# Many ontologies keep common names only as synonyms (FoodOn's "cilantro").
_SYNONYM_PROPERTY_NAMES = [
    "hasExactSynonym",
    "hasRelatedSynonym",
    "hasNarrowSynonym",
    "hasBroadSynonym",
    "hasSynonym",
    "altLabel",
    "prefLabel",
]

def _safe_classes(ontology: Ontology):
    """All classes in the world, including imported ones (ontology.classes()
    misses those). Classes owlready2 can't build are skipped individually."""
    for storid in ontology.world._get_obj_triples_po_s(rdf_type, owl_class):
        if storid < 0:
            continue
        try:
            yield ontology.world._get_by_storid(storid)
        except Exception as e:
            logger.warning(f"Skipping class at storid {storid}: {e}")

def _excluded_branches(ontology: Ontology, cfg: OntologyConfig) -> set[str]:
    """IRIs of classes under (and including) any configured excluded_branch_root_iris."""
    excluded: set[str] = set()
    for root_iri in cfg.excluded_branch_root_iris:
        root_cls = ontology.search_one(iri=root_iri)
        if root_cls is not None:
            excluded |= {sc.iri for sc in root_cls.descendants() if hasattr(sc, "iri")}
            excluded.add(root_iri)
    return excluded

# Shorter labels fuzzy-match almost anything, e.g. "an" vs "Ground Coriander".
_MIN_LABEL_LENGTH = 4

def _label_index(ontology: Ontology, cfg: OntologyConfig) -> dict[str, str]:
    """Build (once per process) a label/synonym -> iri map for the given ontology config."""
    cached = _label_index_cache.get(cfg.name)
    if cached is not None:
        return cached

    synonym_props = [
        p for name in _SYNONYM_PROPERTY_NAMES
        if (p := ontology.world.search_one(iri="*" + name)) is not None
    ]
    excluded = _excluded_branches(ontology, cfg)

    index: dict[str, str] = {}
    for cls in _safe_classes(ontology):
        if not hasattr(cls, "iri") or not any(pat in cls.iri for pat in cfg.included_iri_patterns):
            continue
        if cls.iri in excluded:
            continue
        if getattr(cls, "deprecated", None) == [True]:
            continue

        names = list(cls.label) if hasattr(cls, "label") and cls.label else []
        for prop in synonym_props:
            names.extend(prop[cls])

        for name in names:
            if name and len(name) >= _MIN_LABEL_LENGTH and name not in index:
                index[name] = cls.iri

    _label_index_cache[cfg.name] = index
    return index

_MIN_PLURAL_LENGTH = 4

def _head_noun_forms(query: str) -> set[str]:
    """The query's last word, plus its naive singular ("olives" -> "olive")."""
    words = query.strip().lower().split()
    if not words:
        return set()
    last = words[-1]
    if last.endswith("s") and len(last) >= _MIN_PLURAL_LENGTH:
        return {last, last[:-1]}
    return {last}

def _search_by_label(ontology: Ontology, query: str, cfg: OntologyConfig, limit: int) -> list[dict]:
    """Fuzzy-match free text against ontology class labels, filtered by the provided config."""
    index = _label_index(ontology, cfg)
    matches = process.extract(
        query, index.keys(), scorer=fuzz.WRatio, processor=rf_utils.default_process, limit=limit
    )

    # On a tie, prefer the head noun: "Ground Cumin" -> "cumin", not "ground".
    if len(matches) > 1 and matches[0][1] == matches[1][1]:
        top_score = matches[0][1]
        heads = _head_noun_forms(query)
        tied = [m for m in matches if m[1] == top_score]
        head_match = next((m for m in tied if m[0].strip().lower() in heads), None)
        if head_match is not None:
            matches = [head_match] + [m for m in matches if m is not head_match]

    return [
        {"label": label, "iri": index[label], "score": round(score, 1)}
        for label, score, _ in matches
    ]

def _entity_label(entity) -> str:
    if hasattr(entity, "label") and entity.label:
        return entity.label.first()
    return getattr(entity, "name", str(entity))

def _flatten_class_expression(expr):
    """Yield leaf expressions out of And/Or nesting, e.g. ESRFET's
    EquivalentClasses(X, ObjectIntersectionOf(...)) axioms."""
    if isinstance(expr, (And, Or)):
        for sub in expr.Classes:
            yield from _flatten_class_expression(sub)
    else:
        yield expr

def _fetch_properties(cls, cfg: OntologyConfig) -> dict[str, list[str]]:
    """Object-property restrictions on a class, filtered by included_iri_patterns."""
    properties: dict[str, set[str]] = {}
    sources = list(cls.is_a) + list(getattr(cls, "equivalent_to", []))
    for source in sources:
        for leaf in _flatten_class_expression(source):
            if not isinstance(leaf, Restriction):
                continue
            prop, value = leaf.property, leaf.value
            if not hasattr(prop, "iri") or not any(pat in prop.iri for pat in cfg.included_iri_patterns):
                continue
            if not hasattr(value, "iri") or not any(pat in value.iri for pat in cfg.included_iri_patterns):
                continue
            properties.setdefault(prop.name, set()).add(_entity_label(value))
    return {k: sorted(v) for k, v in properties.items()}

def _fetch_class_info(ontology: Ontology, class_name: str, cfg: OntologyConfig) -> dict:
    """Label, synonyms, comment, see-also, properties and direct parents of a class."""
    cls = ontology.search_one(iri="*" + class_name)
    if cls is None:
        raise ValueError(f"Class '{class_name}' not found in the ontology.")

    synonym_props = [
        p for name in _SYNONYM_PROPERTY_NAMES
        if (p := ontology.world.search_one(iri="*" + name)) is not None
    ]
    alt_labels = sorted({v for p in synonym_props for v in p[cls]})

    # "name" is what the other endpoints accept; they match by IRI, not label.
    parents = [
        {"label": _entity_label(p), "name": p.name}
        for p in cls.is_a
        if isinstance(p, ThingClass)
        and hasattr(p, "iri")
        and any(pat in p.iri for pat in cfg.included_iri_patterns)
    ]

    return {
        "label": _entity_label(cls),
        "alt_labels": alt_labels,
        "comment": cls.comment.first() if hasattr(cls, "comment") and cls.comment else None,
        "see_also": cls.seeAlso.first() if hasattr(cls, "seeAlso") and cls.seeAlso else None,
        "properties": _fetch_properties(cls, cfg),
        "parents": parents,
    }

@app.get("/")
def root():
    return RedirectResponse(url="/docs")

@app.get("/{name}/superclasses/{class_name}")
def get_superclasses(name: str, class_name: str):
    cfg = next((c for c in entry_point.ontologies if c.name == name), None)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"No ontology named '{name}' configured.")
    try:
        resolved_url = _resolve(cfg.owl_url)
        logger.info(f"Loading ontology from: {resolved_url}")
        ontology = get_ontology(resolved_url).load()
        superclasses = _fetch_superclasses(ontology, class_name, cfg)
        return {"superclasses": superclasses}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error fetching superclasses for {class_name}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
@app.get("/{name}/search")
def search(name: str, q: str, limit: int = 10):
    cfg = next((c for c in entry_point.ontologies if c.name == name), None)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"No ontology named '{name}' configured.")
    try:
        resolved_url = _resolve(cfg.owl_url)
        logger.info(f"Loading ontology from: {resolved_url}")
        ontology = get_ontology(resolved_url).load()
        results = _search_by_label(ontology, q, cfg, limit=limit)
        return {"results": results}
    except Exception as e:
        logger.exception(f"Error searching for '{q}' in ontology '{name}'")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/{name}/class/{class_name}")
def get_class_info(name: str, class_name: str):
    cfg = next((c for c in entry_point.ontologies if c.name == name), None)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"No ontology named '{name}' configured.")
    try:
        resolved_url = _resolve(cfg.owl_url)
        logger.info(f"Loading ontology from: {resolved_url}")
        ontology = get_ontology(resolved_url).load()
        return _fetch_class_info(ontology, class_name, cfg)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error fetching class info for {class_name}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/{name}/descendants/{class_name}")
def get_descendants(name: str, class_name: str):
    cfg = next((c for c in entry_point.ontologies if c.name == name), None)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"No ontology named '{name}' configured.")
    try:
        resolved_url = _resolve(cfg.owl_url)
        logger.info(f"Loading ontology from: {resolved_url}")
        ontology = get_ontology(resolved_url).load()
        descendants = _fetch_descendants(ontology, class_name, cfg)
        return {"descendants": descendants}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error fetching descendants for {class_name}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")