from nomad.config.models.plugins import APIEntryPoint
from pydantic import BaseModel, Field

class OntologyConfig(BaseModel):
    name: str
    owl_url: str
    imports: list[str] = []
    # Only read by pynxtools, not by this service.
    PaNET_methods_class: str | None = None
    NeXus_application_class: str | None = None
    excluded_root_class_iris: list[str] = []
    included_iri_patterns: list[str] = []
    # Hidden from /search together with all their descendants.
    excluded_branch_root_iris: list[str] = []

class OntologyServiceEntryPoint(APIEntryPoint):
    ontologies: list[OntologyConfig] = Field(default=[])

    def load(self):
        from nomad_ontology_service.apis.app import app

        return app


ontology_service = OntologyServiceEntryPoint(
    name="ontology_service",
    description="Generic ontology querying service for NOMAD plugins.",
    prefix="/ontology_service",
)