from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class GeographicLevel(str, Enum):
    REG = "Reg"
    PROV = "Prov"
    CITY = "City"
    MUN = "Mun"
    BGY = "Bgy"
    SUBMUN = "SubMun"


class CityClass(str, Enum):
    HUC = "HUC"
    CC = "CC"
    ICC = "ICC"


class ChangeEventType(str, Enum):
    CREATION = "creation"
    DELETION = "deletion"
    TRANSFER = "transfer"
    RENAMING = "renaming"
    MERGER = "merger"
    SPLIT = "split"
    RECLASSIFICATION = "reclassification"
    CODE_CHANGE = "code_change"
    REENLISTMENT = "reenlistment"
    UNKNOWN = "unknown"


class RdfLiteralType(str, Enum):
    URI = "uri"
    STRING = "string"
    INTEGER = "integer"
    DATE = "date"
    BOOLEAN = "boolean"
    LANGSTRING = "langstring"


class GeographicEntity(BaseModel):
    code: str = Field(pattern=r"^\d{10}$")
    name: str
    correspondence_code: str = ""
    geographic_level: str
    old_name: str | None = None
    city_class: str | None = None
    income_class: str | None = None
    urban_rural: str | None = None
    population: int | None = None
    status: str | None = None
    is_capital: bool = False
    is_poblacion: bool = False


class ChangeEvent(BaseModel):
    event_type: str
    entity_name: str
    new_code: str | None = None
    old_code: str | None = None
    old_name: str | None = None
    legal_basis: str | None = None
    effective_date: str | None = None
    plebiscite_date: str | None = None
    mother_unit: str | None = None
    description: str | None = None


class RdfTriple(BaseModel):
    subject_uri: str
    predicate_uri: str
    object_value: str
    datatype: str | None = None
    lang: str | None = None


class BatchExtractionResult(BaseModel):
    entities: list[GeographicEntity] = []
    change_events: list[ChangeEvent] = []
