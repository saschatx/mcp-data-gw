"""Strict transport models and bounded recursive filters."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

Limit = Annotated[int, Field(strict=True, ge=1, le=200)]


class StrictModel(BaseModel):
    """Reject unknown fields, coercion and non-finite numeric values."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Condition(StrictModel):
    """One comparison, NULL check or literal text search on an approved column."""

    column: str
    operator: Literal[
        "eq", "ne", "gt", "gte", "lt", "lte", "in", "is_null", "is_not_null", "contains"
    ]
    value: JsonValue = None

    @model_validator(mode="after")
    def validate_value(self) -> "Condition":
        """Require values only for value-bearing operators and bound in-lists."""
        if self.operator in {"is_null", "is_not_null"}:
            if "value" in self.model_fields_set:
                raise ValueError("NULL operators must omit value")
        elif self.value is None:
            raise ValueError("A non-null value is required")
        if self.operator == "in" and (
            not isinstance(self.value, list) or not 1 <= len(self.value) <= 100
        ):
            raise ValueError("in requires 1 to 100 values")
        return self


class FilterGroup(StrictModel):
    """A nonempty and/or group; total depth and size are checked before parsing."""

    logic: Literal["and", "or"]
    conditions: list["Condition | FilterGroup"] = Field(min_length=1, max_length=30)


Filter = Condition | FilterGroup


class Sort(StrictModel):
    """A column or aggregate output name with an explicit sort direction."""

    column: str
    direction: Literal["asc", "desc"] = "asc"


class Metric(StrictModel):
    """An aggregate function, optional source column and validated output alias."""

    function: Literal["count", "sum", "avg", "min", "max"]
    column: str | None = None
    alias: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$", max_length=64)


class RowsResult(StrictModel):
    """Native JSON row mappings and the count of this bounded response."""

    rows: list[dict[str, JsonValue]]
    returned_count: int


class TableEntry(StrictModel):
    """An existing approved table and its semantic description."""

    name: str
    description: str


class TablesResult(StrictModel):
    """Sorted catalog of existing approved tables."""

    tables: list[TableEntry]


class ColumnInfo(StrictModel):
    """Actual reflected column metadata with a separate semantic description."""

    name: str
    type: str
    nullable: bool
    primary_key: bool
    description: str


class Relationship(StrictModel):
    """A logical lookup relationship that does not imply a declared constraint."""

    from_column: str
    to_table: str
    to_column: str


class LookupValue(StrictModel):
    """A current lookup ID and label read from the database."""

    id: JsonValue
    label: JsonValue


class LookupInfo(StrictModel):
    """Lookup structure and its complete, bounded set of current values."""

    from_column: str
    table: str
    id_column: str
    label_column: str
    values: list[LookupValue]


class DescriptionResult(StrictModel):
    """Technical metadata, logical relationships and live lookup values for a table."""

    table: str
    description: str
    columns: list[ColumnInfo]
    declared_foreign_keys: list[dict[str, JsonValue]]
    logical_relationships: list[Relationship]
    lookup_values: list[LookupInfo]
