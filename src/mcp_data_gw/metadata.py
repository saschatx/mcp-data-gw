"""Explicit schema allowlist and semantic descriptions, without invented keys."""

from .errors import GatewayError

LOOKUPS = {
    "Alive": ("alive_id", "alive"),
    "Class": ("class_id", "class"),
    "Deck": ("deck_id", "deck"),
    "EmbarkTown": ("embark_town_id", "embark_town"),
    "Embarked": ("embarked_id", "embarked"),
    "Sex": ("sex_id", "sex"),
    "Who": ("who_id", "who"),
}
SCHEMA = {
    **LOOKUPS,
    "Observation": (
        "survived",
        "pclass",
        "age",
        "sibsp",
        "parch",
        "fare",
        "adult_male",
        "alone",
        "sex_id",
        "embarked_id",
        "class_id",
        "who_id",
        "deck_id",
        "embark_town_id",
        "alive_id",
    ),
}
DESCRIPTIONS = {
    "Observation": "Titanic passenger observations",
    **{
        name: f"Lookup values for {label.replace('_', ' ')}" for name, (_, label) in LOOKUPS.items()
    },
}
COLUMN_DESCRIPTIONS = {
    "survived": "Survival indicator (0 or 1)",
    "pclass": "Passenger ticket class (1, 2 or 3); distinct from the Class lookup ID",
    "age": "Passenger age in years; may be missing",
    "sibsp": "Number of siblings and spouses aboard",
    "parch": "Number of parents and children aboard",
    "fare": "Passenger fare in the source dataset's monetary units",
    "adult_male": "Whether the passenger is classified as an adult male",
    "alone": "Whether the passenger travelled without siblings, spouse, parents or children",
    **{
        key: f"Logical reference to {name}.{key}; not a declared foreign key"
        for name, (key, _) in LOOKUPS.items()
    },
}


def validate_table(name: str) -> None:
    """Reject table identifiers outside the explicit allowlist.

    Args:
        name (str): Exact case-sensitive table name.

    Raises:
        GatewayError: With TABLE_NOT_FOUND for an unapproved name.
    """
    if name not in SCHEMA:
        raise GatewayError("TABLE_NOT_FOUND", "Table is not approved or does not exist.")


def validate_column(table: str, column: str) -> None:
    """Reject unapproved table or column identifiers before SQL construction.

    Args:
        table (str): Exact case-sensitive table name.
        column (str): Exact column name within that table's allowlist.

    Raises:
        GatewayError: With TABLE_NOT_FOUND or COLUMN_NOT_FOUND for unknown identifiers.
    """
    validate_table(table)
    if column not in SCHEMA[table]:
        raise GatewayError("COLUMN_NOT_FOUND", "Column is not approved or does not exist.")
