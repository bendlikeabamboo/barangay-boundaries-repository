from __future__ import annotations

import re
import urllib.parse

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS, XSD

ORG = Namespace("http://www.w3.org/ns/org#")
PSGC = Namespace("https://psgc.gov.ph/")
DCT = Namespace("http://purl.org/dc/terms/")
PROV = Namespace("http://www.w3.org/ns/prov#")
TIME = Namespace("http://www.w3.org/2006/time#")
SCHEMA = Namespace("http://schema.org/")


def _entity_uri(code: str) -> URIRef:
    return PSGC[f"entity/{code}"]


def _slug(value: str) -> str:
    cleaned = re.sub(r"[*()]+", "", value).strip()
    return urllib.parse.quote(cleaned, safe="-")


def _concept_uri(scheme: str, value: str) -> URIRef:
    return PSGC[f"concept/{scheme}/{_slug(value)}"]


def _level_to_rdf_type(level: str) -> URIRef:
    mapping = {
        "Reg": ORG.FormalOrganization,
        "Prov": ORG.FormalOrganization,
        "City": ORG.FormalOrganization,
        "Mun": ORG.FormalOrganization,
        "Bgy": ORG.OrganizationalUnit,
        "SubMun": ORG.OrganizationalUnit,
    }
    return mapping.get(level, ORG.FormalOrganization)


def _determine_parent_code(code: str, level: str) -> str | None:
    code = code.ljust(10, "0")
    if level == "Reg":
        return None
    if level == "Prov":
        region_part = code[:2] + "00000000"
        return region_part
    if level in ("City", "Mun"):
        province_part = code[:6] + "00000"
        return province_part
    if level in ("Bgy", "SubMun"):
        parent_part = code[:9] + "0"
        return parent_part
    return None


class RdfBuilder:
    def __init__(self, snapshot_date: str) -> None:
        self.graph = Graph()
        self.snapshot_date = snapshot_date
        self._bind_namespaces()
        self._entity_levels: dict[str, str] = {}

    def _bind_namespaces(self) -> None:
        self.graph.bind("org", ORG)
        self.graph.bind("psgc", PSGC)
        self.graph.bind("dct", DCT)
        self.graph.bind("skos", SKOS)
        self.graph.bind("prov", PROV)
        self.graph.bind("time", TIME)
        self.graph.bind("xsd", XSD)
        self.graph.bind("schema", SCHEMA)

    def add_entity(
        self,
        code: str,
        name: str,
        level: str,
        correspondence_code: str = "",
        old_name: str | None = None,
        city_class: str | None = None,
        income_class: str | None = None,
        urban_rural: str | None = None,
        population: int | None = None,
        status: str | None = None,
    ) -> None:
        uri = _entity_uri(code)
        rdf_type = _level_to_rdf_type(level)

        self.graph.add((uri, RDF.type, rdf_type))
        self.graph.add((uri, SKOS.prefLabel, Literal(name, lang="en")))
        self.graph.add((uri, ORG.identifier, Literal(code, datatype=XSD.string)))
        self.graph.add((uri, DCT.date, Literal(self.snapshot_date, datatype=XSD.date)))

        self._entity_levels[code] = level

        if correspondence_code:
            self.graph.add((uri, ORG.identifier, Literal(correspondence_code, datatype=XSD.string)))
            self.graph.add((
                uri,
                ORG.identifier,
                Literal(correspondence_code, datatype=PSGC["correspondence-code"]),
            ))

        if old_name:
            self.graph.add((uri, SKOS.altLabel, Literal(old_name, lang="en")))

        if level in ("City", "Mun", "Prov"):
            if city_class:
                concept = _concept_uri("city-class", city_class)
                self.graph.add((concept, RDF.type, SKOS.Concept))
                self.graph.add((concept, SKOS.prefLabel, Literal(city_class, lang="en")))
                self.graph.add((uri, ORG.classification, concept))

            if income_class:
                concept = _concept_uri("income-class", income_class)
                self.graph.add((concept, RDF.type, SKOS.Concept))
                self.graph.add((concept, SKOS.prefLabel, Literal(f"Income Class {income_class}", lang="en")))
                self.graph.add((uri, ORG.classification, concept))

        if urban_rural:
            concept = _concept_uri("urban-rural", urban_rural)
            self.graph.add((concept, RDF.type, SKOS.Concept))
            label = "Urban" if urban_rural == "U" else "Rural"
            self.graph.add((concept, SKOS.prefLabel, Literal(label, lang="en")))
            self.graph.add((uri, ORG.classification, concept))

        if population is not None:
            self.graph.add((uri, SCHEMA.population, Literal(population, datatype=XSD.integer)))

        if status == "Capital":
            concept = _concept_uri("status", "capital")
            self.graph.add((concept, RDF.type, SKOS.Concept))
            self.graph.add((concept, SKOS.prefLabel, Literal("Capital", lang="en")))
            self.graph.add((uri, ORG.classification, concept))
        elif status == "Pob.":
            concept = _concept_uri("status", "poblacion")
            self.graph.add((concept, RDF.type, SKOS.Concept))
            self.graph.add((concept, SKOS.prefLabel, Literal("Poblacion", lang="en")))
            self.graph.add((uri, ORG.classification, concept))

        level_concept = _concept_uri("geographic-level", level)
        self.graph.add((level_concept, RDF.type, SKOS.Concept))
        self.graph.add((uri, ORG.classification, level_concept))

    def add_hierarchy(self, child_code: str, parent_code: str) -> None:
        child_uri = _entity_uri(child_code)
        parent_uri = _entity_uri(parent_code)
        child_level = self._entity_levels.get(child_code, "")
        if child_level in ("Bgy", "SubMun"):
            self.graph.add((parent_uri, ORG.hasUnit, child_uri))
        else:
            self.graph.add((parent_uri, ORG.hasSubOrganization, child_uri))

    def add_change_event(
        self,
        event_id: str,
        event_type: str,
        entity_code: str | None = None,
        old_code: str | None = None,
        entity_codes: list[str] | None = None,
        old_codes: list[str] | None = None,
        legal_basis: str | None = None,
        effective_date: str | None = None,
        description: str | None = None,
    ) -> URIRef:
        event_uri = PSGC[f"event/{self.snapshot_date}/{event_id}"]
        self.graph.add((event_uri, RDF.type, ORG.ChangeEvent))
        self.graph.add((event_uri, DCT.date, Literal(self.snapshot_date, datatype=XSD.date)))

        type_concept = _concept_uri("change-type", event_type)
        self.graph.add((type_concept, RDF.type, SKOS.Concept))
        self.graph.add((event_uri, ORG.classification, type_concept))

        final_entity_codes = entity_codes or ([entity_code] if entity_code else None)
        final_old_codes = old_codes or ([old_code] if old_code else None)

        if final_entity_codes:
            for code in final_entity_codes:
                self.graph.add((event_uri, ORG.resultingOrganization, _entity_uri(code)))
        if final_old_codes:
            for code in final_old_codes:
                self.graph.add((event_uri, ORG.originalOrganization, _entity_uri(code)))
        if legal_basis:
            self.graph.add((event_uri, DCT.source, Literal(legal_basis, lang="en")))
        if effective_date:
            self.graph.add((event_uri, PROV.generatedAtTime, Literal(effective_date, datatype=XSD.date)))
        if description:
            self.graph.add((event_uri, DCT.description, Literal(description, lang="en")))

        return event_uri

    def build_hierarchy_from_entities(self) -> None:
        for code, level in self._entity_levels.items():
            parent_code = _determine_parent_code(code, level)
            if parent_code and parent_code in self._entity_levels:
                self.add_hierarchy(code, parent_code)

    def serialize(self, path: str, format: str = "turtle") -> None:
        fmt_map = {
            "turtle": "turtle",
            "ttl": "turtle",
            "json-ld": "json-ld",
            "nt": "nt",
            "n-triples": "nt",
        }
        rdflib_format = fmt_map.get(format, format)
        self.graph.serialize(destination=path, format=rdflib_format)
