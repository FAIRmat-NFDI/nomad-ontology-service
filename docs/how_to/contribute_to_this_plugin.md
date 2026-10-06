# Contribute to This Plugin

See the [README](https://github.com/Tanmay2028/nomad-ontology-service#development) for the full local dev setup (virtualenv, `uv pip install -e '.[dev]'`, running tests, linting with Ruff, debugging).

A few things specific to working on this plugin:

- The service is deliberately domain-agnostic -- new features should stay generic (configurable via `OntologyConfig`) rather than assume anything about a specific ontology's structure.
- Test changes against at least two differently-shaped ontologies if possible (e.g. NeXus's merged/reasoned pipeline and FoodOn's single-file case) -- the two consumers currently using this service exercise quite different parts of it.
- If you change `OntologyConfig`, check whether the field should be required or optional: existing consumers (`pynxtools`) shouldn't have to supply values for fields another consumer doesn't need.

