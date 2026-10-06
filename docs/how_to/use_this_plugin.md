# How to Use This Plugin

This plugin can be used in a NOMAD Oasis installation.

## Add This Plugin to Your NOMAD installation

Read the [NOMAD plugin documentation](https://nomad-lab.eu/prod/v1/staging/docs/plugins/plugins.html#add-a-plugin-to-your-nomad) for all details on how to deploy the plugin on your NOMAD instance.

## Configure an ontology

Register each ontology you want queryable under `nomad_ontology_service:ontology_service`'s `ontologies` list in `nomad.yaml`:

```yaml
plugins:
  entry_points:
    options:
      nomad_ontology_service:ontology_service:
        ontologies:
          - name: nexus
            owl_url: "nomad_tmp://pynxtools/NeXusOntology_inferred.owl"
            imports:
              - "https://raw.githubusercontent.com/pan-ontologies/esrf-ontologies/refs/heads/oscars-deliverable-2/ontologies/esrfet/ESRFET.owl"
              - "http://purl.org/pan-science/PaNET/PaNET.owl"
            PaNET_methods_class: "PaNET00003"
            NeXus_application_class: "NeXusApplicationClass"
            excluded_root_class_iris:
              - "https://w3id.org/PaN/NeXus/definitions#NeXusApplicationClass"
            included_iri_patterns: [PaNET, nexusformat, ESRFET, "PaN/NeXus"]
          - name: food
            owl_url: "https://raw.githubusercontent.com/FoodOntology/foodon/v2025-02-01/foodon-base.owl"
            included_iri_patterns: ["obolibrary.org/obo/FOODON"]
```

`ontologies` is a list, so any number of independent, unrelated ontologies can be registered side by side under their own `name`.

Full field reference: [Reference](../reference/references.md).

## Query it

Three endpoints, all under `/ontology_service/{name}/...`:

- `GET /{name}/search?q=<text>&limit=<n>` -- fuzzy-match free text against class labels (and synonyms, if the ontology declares OBO-style `hasSynonym`/`hasExactSynonym` annotations). Use this when you have a human-written string (an ingredient name, an instrument name, ...) and need to resolve it to a formal class.
- `GET /{name}/superclasses/{class_name}` -- ancestors of a class, filtered by `included_iri_patterns`/`excluded_root_class_iris`.
- `GET /{name}/descendants/{class_name}` -- descendants of a class, same filtering.

`class_name` is matched by IRI suffix (`*class_name`), so it works with either a bare local name (`NXmpes_arpes`, `FOODON_03301223`) or a full IRI.

```bash
curl "http://localhost:8000/nomad-oasis/ontology_service/nexus/superclasses/NXmpes_arpes"
curl "http://localhost:8000/nomad-oasis/ontology_service/food/search?q=cilantro&limit=5"
```

## Use it from a plugin's `normalize()`

The intended usage pattern is an HTTP call from inside a schema's `normalize()` method, guarded so the plugin still works if the ontology-service isn't installed/configured:

```python
def get_ontology_match(name: str) -> dict | None:
    try:
        from nomad.config import config
        entry_point = config.get_plugin_entry_point("nomad_ontology_service:ontology_service")
    except Exception:
        return None  # ontology-service not installed/configured

    base = config.services.api_base_path.rstrip("/")
    prefix = entry_point.prefix.strip("/")
    url = f"http://localhost:8000{base}/{prefix}/<your-ontology-name>/search"

    import requests
    response = requests.get(url, params={"q": name, "limit": 1}, timeout=30)
    response.raise_for_status()
    results = response.json().get("results", [])
    return results[0] if results else None
```

See `nomad_tajine_plugin.schema_packages.foodon_lookup.foodon_lookup.get_foodon_match()` for the real version of this (with a score threshold and error handling), and `pynxtools.nomad.schema_packages.schema.NexusMeasurement.normalize()` for a more involved example that also intersects results against two different class roots.
