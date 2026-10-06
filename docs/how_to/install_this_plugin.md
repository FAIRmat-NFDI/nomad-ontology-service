# Install This Plugin

Add `nomad-ontology-service` as a dependency of your NOMAD distribution (e.g. in `pyproject.toml`):

```toml
dependencies = [
    "nomad-ontology-service",
]
```

That's the whole installation step -- it's a standard `nomad.plugin` entry point (`ontology_service = "nomad_ontology_service:ontology_service"`), so NOMAD discovers and mounts it automatically at startup, at `{api_base_path}/ontology_service` (typically `/nomad-oasis/ontology_service`). No further registration is needed.

By itself it does nothing until you register at least one ontology under it -- see the [tutorial](../tutorial/tutorial.md) for that.

For the general mechanics of adding any plugin to a NOMAD Oasis, see the [NOMAD plugin documentation](https://nomad-lab.eu/prod/v1/staging/docs/plugins/plugins.html#add-a-plugin-to-your-nomad).
