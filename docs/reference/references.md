# References

## `OntologyConfig` fields

One entry per item in `ontologies` under the `nomad_ontology_service:ontology_service` entry point in `nomad.yaml`.

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | yes | Identifier used in URLs: `/ontology_service/{name}/...`. |
| `owl_url` | `str` | yes | Where to load the OWL file from. A plain `http(s)://` URL, a local file path, or `nomad_tmp://<relative-path>` (resolved against `config.fs.tmp`). |
| `imports` | `list[str]` | no | Additional ontology URLs to merge in before serving. Only meaningful if whatever generates the file at `owl_url` actually merges them (this service itself does not follow `owl:imports`). |
| `PaNET_methods_class` | `str \| None` | no | Consumer-specific metadata, not read by this service. Used by `pynxtools` to intersect superclasses against PaNET's method taxonomy. |
| `NeXus_application_class` | `str \| None` | no | Same as above, for NeXus's own application-class root. |
| `excluded_root_class_iris` | `list[str]` | no | Full IRIs. For `/superclasses` and `/descendants`: excludes each listed root *and its ancestors* from results. |
| `included_iri_patterns` | `list[str]` | no | Substrings. A class is only ever returned (from any endpoint) if its IRI contains at least one of these. |
| `excluded_branch_root_iris` | `list[str]` | no | Full IRIs. For `/search` only: excludes each listed root *and all its descendants* from the searchable label index. |

## Endpoints

All mounted under `{api_base_path}/ontology_service` (typically `/nomad-oasis/ontology_service`). Interactive docs at `/ontology_service/docs`.

### `GET /{name}/search`

Fuzzy-match free text against class labels (and OBO-style synonym annotations: `hasExactSynonym`, `hasRelatedSynonym`, `hasNarrowSynonym`, `hasBroadSynonym`, `hasSynonym`), scored with `rapidfuzz`'s `WRatio`. Deprecated (`owl:deprecated true`) classes and anything under `excluded_branch_root_iris` are never candidates.

| Param | Type | Required | Description |
|---|---|---|---|
| `name` | path | yes | Which registered ontology to search. |
| `q` | query | yes | Free-text query. |
| `limit` | query | no, default 10 | Max results to return. |

Response:
```json
{"results": [{"label": "paprika (ground)", "iri": "http://purl.obolibrary.org/obo/FOODON_03301223", "score": 90.0}, ...]}
```
Results are ordered by descending `score` (0-100).

### `GET /{name}/superclasses/{class_name}`

Ancestors of a class, filtered by `included_iri_patterns` and `excluded_root_class_iris`.

| Param | Type | Required | Description |
|---|---|---|---|
| `name` | path | yes | Which registered ontology to query. |
| `class_name` | path | yes | Bare local name or full IRI; matched by IRI suffix. |

Response:
```json
{"superclasses": ["NXmpes_arpes", "NXmpes", "photoemission spectroscopy", ...]}
```
Entries are class labels (`rdfs:label`) where present, falling back to the class's local name.

### `GET /{name}/descendants/{class_name}`

Same shape as `/superclasses`, but walking subclasses instead of ancestors. Metaclass conflicts encountered while traversing (owlready2 can hit these on ontologies with complex `EquivalentClasses` axioms) are logged as warnings and that branch is skipped, rather than failing the whole request.

Response:
```json
{"descendants": [...]}
```

### Errors

- `404` -- unknown `name`, or `class_name` not found in that ontology.
- `500` -- unexpected failure loading or querying the ontology (network failure fetching `owl_url` or an `imports` URL, malformed OWL, etc.); check the server logs for the underlying exception.
