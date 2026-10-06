# Welcome to the `nomad-ontology-service` documentation

NOMAD plugin for registering ontology service and exposing domain-specific ontological information

## Introduction

`nomad-ontology-service` mounts a generic FastAPI service into a NOMAD (Oasis) instance for querying OWL ontologies: fuzzy label search, superclass lookup, and descendant lookup, all filtered by a configurable set of rules. Each domain plugin registers its own ontology (an OWL file plus a few filtering rules) under its own name in `nomad.yaml`, and queries it over HTTP during entry normalization to attach semantic metadata to its own data.

Two plugins currently use it as worked examples of very different domains:

- [`pynxtools`](https://github.com/FAIRmat-NFDI/pynxtools) registers the NeXus ontology (merged with the PaNET and ESRFET technique ontologies) to tag processed NeXus entries with standardized experimental-technique labels.
- [`nomad-tajine-plugin`](https://github.com/FAIRmat-NFDI/nomad-tajine-plugin) registers [FoodOn](https://foodon.org/) to resolve free-text ingredient names to a formal food-classification hierarchy.

Adding a third ontology for a new domain requires no code changes to this service -- just a new entry under `ontologies` in `nomad.yaml`. See the [tutorial](tutorial/tutorial.md) for a worked example, and the [explanation](explanation/explanation.md) page for how it all fits together.

<div markdown="block" class="home-grid">
<div markdown="block">

### Tutorial

Walks through registering a new ontology and querying it end to end.

- [Tutorial](tutorial/tutorial.md)

</div>
<div markdown="block">

### How-to guides

How-to guides provide step-by-step instructions for a wide range of tasks, with the overarching topics:

- [Install this plugin](how_to/install_this_plugin.md)
- [Use this plugin](how_to/use_this_plugin.md)
- [Contribute to this plugin](how_to/contribute_to_this_plugin.md)
- [Contribute to the documentation](how_to/contribute_to_the_documentation.md)

</div>

<div markdown="block">

### Explanation

The explanation [section](explanation/explanation.md) provides background knowledge on this plugin.

</div>
<div markdown="block">

### Reference

The reference [section](reference/references.md) includes all CLI commands and arguments, all configuration options,
the possible schema annotations and their arguments, and a glossary of used terms.

</div>
</div>
