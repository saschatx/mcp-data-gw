"""Rebuild the Titanic SQLite database from the original Titanic CSV.

The SQLite schema and lookup ID mappings are embedded directly in this
script. No external schema or lookup-table exports are required.

Usage:
    python generate_titanic_db.py titanic.csv titanic.db
    python generate_titanic_db.py titanic.csv titanic.db --overwrite
"""

import argparse
import csv
import os
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

# Exact ID-to-value mappings from the original lookup-table exports.
# The -1 rows contain the literal text "null".
LOOKUPS = {
    "Sex": ("sex", "sex_id", {0: "female", 1: "male"}),
    "Embarked": ("embarked", "embarked_id", {-1: "null", 0: "C", 1: "Q", 2: "S"}),
    "Class": ("class", "class_id", {0: "First", 1: "Second", 2: "Third"}),
    "Who": ("who", "who_id", {0: "child", 1: "man", 2: "woman"}),
    "Deck": (
        "deck",
        "deck_id",
        {-1: "null", 0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G"},
    ),
    "EmbarkTown": (
        "embark_town",
        "embark_town_id",
        {-1: "null", 0: "Cherbourg", 1: "Queenstown", 2: "Southampton"},
    ),
    "Alive": ("alive", "alive_id", {0: "no", 1: "yes"}),
}


OBSERVATION_COLUMNS = (
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
)

SOURCE_COLUMNS = {
    "survived",
    "pclass",
    "sex",
    "age",
    "sibsp",
    "parch",
    "fare",
    "embarked",
    "class",
    "who",
    "adult_male",
    "deck",
    "embark_town",
    "alive",
    "alone",
}

BOOL_VALUES = {"True": 1, "False": 0}


def create_tables(connection: sqlite3.Connection) -> None:
    """Create all eight tables using the embedded SQLite schema.

    The table definitions reproduce the supplied schema export,
    including column names, types, order, and CHECK constraints.

    Args:
        connection (sqlite3.Connection): Connection to a new staging database.
    """

    # Main observation table.
    connection.execute("""
        CREATE TABLE "Observation" (
            survived BIGINT,
            pclass BIGINT,
            age FLOAT,
            sibsp BIGINT,
            parch BIGINT,
            fare FLOAT,
            adult_male BOOLEAN,
            alone BOOLEAN,
            sex_id BIGINT,
            embarked_id BIGINT,
            class_id BIGINT,
            who_id BIGINT,
            deck_id BIGINT,
            embark_town_id BIGINT,
            alive_id BIGINT,
            CHECK (adult_male IN (0, 1)),
            CHECK (alone IN (0, 1))
        )
    """)

    # Seven lookup tables, generated from the fixed mappings.
    for table, (source_col, id_col, _) in LOOKUPS.items():
        connection.execute(f'''
            CREATE TABLE "{table}" (
                "{id_col}" BIGINT,
                "{source_col}" TEXT
            )
        ''')


def populate(connection: sqlite3.Connection, input_csv: Path) -> int:
    """Import source observations and the embedded lookup mappings.

    Args:
        connection (sqlite3.Connection): Staging database with the tables.
        input_csv (Path): Original Titanic CSV with the expected columns.

    Returns:
        int: Number of imported passenger observations.

    Raises:
        ValueError: If CSV columns, row shapes, or values are invalid.
    """

    # Populate lookup tables with the exact original IDs.
    category_ids = {}

    for table, (source_col, id_col, values) in LOOKUPS.items():
        connection.executemany(
            f'INSERT INTO "{table}" ("{id_col}", "{source_col}") VALUES (?, ?)',
            values.items(),
        )

        category_ids[source_col] = {value: id_value for id_value, value in values.items()}

    # Prepare observation insertion statement.
    placeholders = ", ".join("?" for _ in OBSERVATION_COLUMNS)
    columns_sql = ", ".join(f'"{column}"' for column in OBSERVATION_COLUMNS)

    insert_sql = f'INSERT INTO "Observation" ({columns_sql}) VALUES ({placeholders})'

    count = 0

    with input_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)

        # Verify the original CSV contains the expected columns.
        if set(reader.fieldnames or ()) != SOURCE_COLUMNS:
            raise ValueError(f"Unexpected input columns: {reader.fieldnames!r}")

        for line_number, row in enumerate(reader, start=2):
            try:
                # Detect malformed CSV rows.
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("Inconsistent number of CSV fields")

                # Convert the original observation values.
                data = {
                    "survived": int(row["survived"]),
                    "pclass": int(row["pclass"]),
                    "age": float(row["age"]) if row["age"] else None,
                    "sibsp": int(row["sibsp"]),
                    "parch": int(row["parch"]),
                    "fare": float(row["fare"]),
                    "adult_male": BOOL_VALUES[row["adult_male"]],
                    "alone": BOOL_VALUES[row["alone"]],
                }

                # Replace categorical values with lookup IDs.
                for source_col, id_col, _ in LOOKUPS.values():
                    original = row[source_col]

                    # Empty categories map to the -1 lookup row.
                    lookup_value = "null" if original == "" else original

                    data[id_col] = category_ids[source_col][lookup_value]

                # Insert the completed observation.
                connection.execute(
                    insert_sql,
                    [data[column] for column in OBSERVATION_COLUMNS],
                )

            except (KeyError, ValueError) as error:
                raise ValueError(f"Invalid value at CSV line {line_number}: {error}") from error

            count += 1

    return count


def main() -> None:
    """Generate the Titanic database safely.

    Creates the database in a temporary directory before moving it
    to the requested output path.

    An existing database is only replaced when --overwrite is used.
    """

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "input_csv",
        type=Path,
        help="Path to the original Titanic CSV file",
    )

    parser.add_argument(
        "output_db",
        type=Path,
        help="Path to the SQLite database to create",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output database",
    )

    args = parser.parse_args()

    # Prevent overwriting the source CSV.
    if args.output_db.resolve() == args.input_csv.resolve():
        parser.error("Output database must not overwrite the input CSV")

    # Require explicit permission before replacing an existing file.
    if args.output_db.exists() and not args.overwrite:
        parser.error(f"Database already exists: {args.output_db} (use --overwrite)")

    # Build the complete database before replacing the output.
    with TemporaryDirectory(dir=args.output_db.resolve().parent) as directory:
        staged_db = Path(directory) / "titanic.db"

        with sqlite3.connect(staged_db) as connection:
            create_tables(connection)
            count = populate(connection, args.input_csv)

        # Atomically replace the output after successful creation.
        os.replace(staged_db, args.output_db)

    print(f"Created {args.output_db}: {count} observations and {len(LOOKUPS)} lookup tables")


if __name__ == "__main__":
    main()
