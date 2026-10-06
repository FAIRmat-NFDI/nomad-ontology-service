# Explanation

## Why a separate, generic plugin

Semantic enrichment (resolving free-text or formal identifiers to an ontology class, then walking its class hierarchy) is a need that shows up in unrelated NOMAD plugins for unrelated domains -- experimental techniques for `pynxtools`, food classification for `nomad-tajine-plugin`, potentially materials, instruments, or anything else with a published OWL ontology. None of that logic (loading an OWL file, fuzzy label search, ancestor/descendant traversal) is domain-specific. Rather than every plugin reimplementing `owlready2` handling, this service does it once, generically, and each domain plugin just registers its own ontology and calls the same three endpoints.

## Mounting

Like any NOMAD API plugin, this is an [`APIEntryPoint`](https://nomad-lab.eu/prod/v1/docs/reference/config.html#apientrypoint) (`OntologyServiceEntryPoint`, entry point id `ontology_service`). Its `load()` returns a FastAPI app, which NOMAD mounts automatically at `{api_base_path}/{prefix}` (`prefix="/ontology_service"`) alongside every other API plugin -- no bespoke wiring, this is the same generic mechanism any NOMAD API plugin uses.

## What "ontology" means here

Each entry in `ontologies` (an `OntologyConfig`) is independent: its own `name`, its own `owl_url`, its own filtering rules. There's no assumption that different registered ontologies relate to each other at all.

Two config fields -- `PaNET_methods_class` and `NeXus_application_class` -- are metadata this service stores but never reads itself; they exist purely because `pynxtools` needs to read them back out of its own config to do NeXus-specific intersection logic in its own `normalize()`. They're optional precisely so other ontologies (like `food`) aren't forced to invent meaningless values for NeXus-specific fields.

## Loading and caching

Endpoints load the OWL file fresh on every request (`get_ontology(resolved_url).load()`). This sounds wasteful, but `owlready2` itself caches by IRI/path within a process: the first request that touches a given ontology parses and loads it; every later request in the same process reuses the already-loaded object at effectively zero cost. The practical consequence is that only the *first* request after each process (re)start pays the parsing cost -- worth knowing if you're debugging a slow first call versus fast subsequent ones.

The label index used by `/search` is built once per process per ontology (a plain `label -> iri` dict, cached in `_label_index_cache`), for the same reason: building it means iterating every class in the ontology, which isn't something worth repeating on every request.

## Where the OWL file comes from

`owl_url` can be a plain network URL (as `food` uses for FoodOn -- a single, already-published, self-contained ontology, no local build step needed), or `nomad_tmp://<relative-path>` (resolved against `config.fs.tmp`), which is what `pynxtools` uses. NeXus's case is more involved than FoodOn's: the NeXus ontology needs to be merged with PaNET/ESRFET and reasoned over *before* it's useful, and `pynxtools` itself carries NeXus definitions that aren't part of the official standard yet (so a pre-built, officially-released ontology artifact wouldn't include them). `pynxtools` handles that entire generate-merge-reason pipeline itself (`ensure_ontology_initialization`, called from its own `normalize()`), and simply writes the result to `config.fs.tmp` for this service to serve -- this service has no opinion on how the file got there, only on how to query it.

## Filtering: `included_iri_patterns`, `excluded_root_class_iris`, `excluded_branch_root_iris`

Ontologies typically mix domain classes with unrelated scaffolding (OWL/RDF built-ins, imported vocabulary internals, annotation-only classes). Three independent filters keep results meaningful:

- `included_iri_patterns`: only classes whose IRI contains one of these substrings are ever considered, for any endpoint. This is the primary noise filter.
- `excluded_root_class_iris`: used by `/superclasses` and `/descendants` -- excludes a given root class *and its ancestors* (e.g. cutting off generic `owl:Thing`-level scaffolding above a domain's real roots).
- `excluded_branch_root_iris`: used by `/search` only -- excludes a given root class *and all its descendants* (the opposite direction). This exists because some ontologies model non-domain concepts as their own class branch rather than as annotation-only classes -- FoodOn, for example, has a "quality" branch (`fresh`, `raw`, `thawed`) that would otherwise be indistinguishable from real food classes in a label search, and excluding it by branch (not by pattern, since its IRIs look identical to real food classes) is the only way to keep it out of search results.

## A caveat worth knowing: `/search`'s fuzzy matching

`/search` uses `rapidfuzz`'s `WRatio` scorer, which is a general-purpose string similarity measure -- it has no notion of what a class actually *means*. In practice this means short, generic labels can occasionally out-score the semantically correct match purely on substring overlap (e.g. a class named `Aves` scoring as high as the correct match for a query containing "leaves", since "Aves" is a near-exact substring of "l**eaves**"). Consumers should look at more than just the top-1 result and/or apply a sensible score threshold rather than trusting rank-1 blindly.
