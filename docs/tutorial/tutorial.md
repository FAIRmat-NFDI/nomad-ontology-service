# Tutorial

This walks through registering a new ontology with `nomad-ontology-service` and querying it, using [FoodOn](https://foodon.org/) as a real, minimal example (a single self-contained OWL file, no cross-ontology merging or reasoning needed -- the simplest case to start with).

## 1. Register the ontology in `nomad.yaml`

Add an entry under the `nomad_ontology_service:ontology_service` entry point's `ontologies` list:

```yaml
plugins:
  entry_points:
    options:
      nomad_ontology_service:ontology_service:
        ontologies:
          - name: food
            owl_url: "https://raw.githubusercontent.com/FoodOntology/foodon/v2025-02-01/foodon-base.owl"
            included_iri_patterns: ["obolibrary.org/obo/FOODON"]
```

- `name` is how you'll refer to this ontology in URLs (`/food/...`).
- `owl_url` can be a plain `http(s)://` URL, a local file path, or `nomad_tmp://<relative-path>` (resolved against `config.fs.tmp` -- see [explanation](../explanation/explanation.md) for why a plugin might generate its ontology file locally instead of pointing at a static URL).
- `included_iri_patterns` filters which classes are ever returned: only classes whose IRI contains one of these substrings are considered. Without it, results would include NOMAD/OWL-internal classes that aren't part of the domain ontology at all.

## 2. Start NOMAD and check it loaded

Once your NOMAD (Oasis) instance is running with this config, confirm the entry point mounted:

```
http://localhost:8000/nomad-oasis/ontology_service/docs
```

This should show the interactive Swagger UI with three endpoints: `/search`, `/{name}/superclasses/{class_name}`, `/{name}/descendants/{class_name}`.

## 3. Resolve free text to a class

Real-world names rarely match an ontology's formal class names exactly. Use `/search` to fuzzy-match:

```bash
curl "http://localhost:8000/nomad-oasis/ontology_service/food/search?q=paprika&limit=5"
```

```json
{"results": [
  {"label": "paprika (ground)", "iri": "http://purl.obolibrary.org/obo/FOODON_03301223", "score": 90.0},
  {"label": "paprika bloom seasoning", "iri": "http://purl.obolibrary.org/obo/FOODON_03306674", "score": 90.0},
  ...
]}
```

Take the top-scoring result's `iri` (or apply your own score threshold) as the resolved class for that piece of text.

## 4. Look up its place in the hierarchy

Once you have a class name (or IRI), fetch its ancestors:

```bash
curl "http://localhost:8000/nomad-oasis/ontology_service/food/superclasses/FOODON_03301223"
```

```json
{"superclasses": ["paprika (ground)", "spice", "food product", ...]}
```

Or its descendants (e.g. to find sibling/substitute classes):

```bash
curl "http://localhost:8000/nomad-oasis/ontology_service/food/descendants/spice"
```

## 5. Wire it into a plugin's `normalize()`

This is exactly the pattern both `pynxtools` and `nomad-tajine-plugin` use: call the service over HTTP from inside a schema's `normalize()` method, and store the result on the entry. See `nomad_tajine_plugin.schema_packages.foodon_lookup.foodon_lookup.get_foodon_match()` for a small, complete example of this pattern (search, take the top match above a score threshold, store `iri`/`label` on the entry).

## Next steps

- If your ontology needs classes merged in from other ontologies before it's useful (like `pynxtools` does for NeXus + PaNET + ESRFET), see [Explanation](../explanation/explanation.md) for how that's handled outside this service, in the consuming plugin.
- For the full config schema and endpoint reference, see [Reference](../reference/references.md).
