# Phase 3 – Anforderungen an die lesenden MCP-Tools

**Projekt:** `mcp-data-gw`
**Status:** zur Implementierung freigegeben
**Stand:** 31. Oktober 2026
**Geltungsbereich:** ausschließlich Phase 3

## 1. Ziel und Abgrenzung

Phase 3 liefert einen **ausführbaren und vorzeigbaren** MCP-Server: Vier lesende Tools bieten einen kontrollierten Zugriff auf die bestehende Titanic-SQLite-Datenbank über Streamable HTTP. Die Implementierung trennt MCP-Transport, Validierung, Anwendungslogik und Datenbankzugriff.

Diese Datei konkretisiert die Phase-1-Definitionen. Bei Abweichungen gelten die hier ausdrücklich getroffenen **neueren Phase-3-Entscheidungen**; im Übrigen bleiben Phase 1, Phase 2 und `AGENTS.md` maßgeblich. Die Abnahmekriterien stehen in [phase-3-acceptance.md](../requirements/phase-3-acceptance.md); der Arbeitsauftrag für Coding-Agenten in [phase-3-handover.md](../requirements/phase-3-handover.md). Die Compose-Konfiguration ist im [README](../../README.md) beschrieben.

### Verbindlich enthalten

- `list_tables`, `describe_table`, `select_rows`, `aggregate_rows`.
- SQLAlchemy Core, Pydantic 2 und das offizielle Python-MCP-SDK 2.x.
- Strukturierte Eingaben, parametrisierte Abfragen und begrenzte Ergebnisse.
- Ein kleiner Semantic Layer mit statischen Beschreibungen und **zur Laufzeit** aus der DB gelesenen Lookup-Werten.
- Startfähiger Streamable-HTTP-Server, minimale Konfiguration, sichere lokale Defaults.
- Unit-Tests, In-Memory-MCP-Tests mit gezielten Mocks und ein **manueller** Smoke-Test gegen die vorhandene Titanic-Datenbank.

### Ausdrücklich nicht enthalten

- Schreibende Tools.
- Pagination, `offset`, `has_more`, Joins, `HAVING`, frei ausführbares SQL und generische SQL-Ausdrücke.
- Eine temporäre SQLite-Testdatenbank, automatisch erzeugte DB-Fixtures oder automatisierte Tests gegen die echte Datenbank.

## 2. Architektur und feste Rahmenbedingungen

| ID | Verbindliche Anforderung |
| --- | --- |
| P3-ARC-01 | Ein einzelner modularer Python-Dienst im vorhandenen `src/mcp_data_gw/`-Paket. MCP-Handler, Validierung, Abfrageerzeugung, semantische Metadaten und DB-Zugriff sind sinnvoll voneinander getrennt. |
| P3-ARC-02 | SQLAlchemy **Core**; keine ORM-Klassen, keine Änderungen am Datenbankschema und keine implizite Schema-Erzeugung beim Serverstart. |
| P3-ARC-03 | Keine benutzerdefinierten SQL-Strings, SQL-Fragmente oder Tabellen-/Spaltennamen ohne Allowlist-Validierung. Abfragen werden mit SQLAlchemy-Ausdrücken und gebundenen Werten aufgebaut. |
| P3-ARC-04 | Die fachliche Abfragelogik ist ohne MCP-Transport testbar. Öffentliche Funktionen und Methoden haben sinnvolle Type Hints. |
| P3-ARC-05 | Die Anwendung setzt **keine** Primary-Key- oder Foreign-Key-Constraints voraus. Beziehungen sind nur logisch beschrieben und werden nicht als deklarierte Constraints ausgegeben. |
| P3-ARC-06 | Der Dienst nutzt die vorhandenen Paket- und Tooling-Vorgaben (`pyproject.toml`, Ruff, pytest, uv); keine neuen Laufzeit- oder Entwicklungsabhängigkeiten ohne Zustimmung. |

### Datenbankschema und Allowlist

Freigegeben sind genau die Tabellen `Alive`, `Class`, `Deck`, `EmbarkTown`, `Embarked`, `Observation`, `Sex`, `Who`. Die Spalten entsprechen der Phase-1-Spezifikation:

| Tabelle | Erlaubte Spalten |
| --- | --- |
| `Alive` | `alive_id`, `alive` |
| `Class` | `class_id`, `class` |
| `Deck` | `deck_id`, `deck` |
| `EmbarkTown` | `embark_town_id`, `embark_town` |
| `Embarked` | `embarked_id`, `embarked` |
| `Sex` | `sex_id`, `sex` |
| `Who` | `who_id`, `who` |
| `Observation` | `survived`, `pclass`, `age`, `sibsp`, `parch`, `fare`, `adult_male`, `alone`, `sex_id`, `embarked_id`, `class_id`, `who_id`, `deck_id`, `embark_town_id`, `alive_id` |

Die deklarierten Typen (`BIGINT`, `TEXT`, `FLOAT`, `BOOLEAN`) und tatsächlichen Metadaten werden über SQLAlchemy Reflection gelesen. `sqlite_master`, SQLite-`rowid`, interne Tabellen, SQL-Ausdrücke und nicht freigegebene Spalten sind keine gültigen Tool-Argumente. Die zulässigen Bezeichner werden aus der ausdrücklich definierten Struktur geprüft; Reflection allein erweitert die Allowlist nicht.

## 3. Gemeinsame Tool-Verträge

| ID | Verbindliche Anforderung |
| --- | --- |
| P3-COM-01 | Jeder Tool-Name, Parameter und jede öffentliche Rückgabe ist stabil und über eine verständliche englische MCP-Tool-Beschreibung mit Typinformationen dokumentiert. |
| P3-COM-02 | Eingaben werden durch das SDK/Pydantic typisiert und an der Service-Grenze fachlich validiert. Unbekannte Tabellen, Spalten und Operatoren werden abgelehnt. |
| P3-COM-03 | Erfolgreiche Tools geben JSON-kompatible, typisierte strukturierte Ergebnisse zurück. Zahlen, Strings, Booleans und `null` bleiben als native JSON-Typen erhalten; keine als JSON-String verpackten Ergebnisobjekte. |
| P3-COM-04 | Ergebnisse und Abfragekomplexität haben serverseitige Limits. Ein vom Client geliefertes Limit kann Obergrenzen niemals erhöhen. |
| P3-COM-05 | Leere Treffermengen sind erfolgreiche Ergebnisse mit `rows: []` und `returned_count: 0` (bzw. beim Tabellenkatalog `tables: []`, falls keine freigegebene Tabelle vorhanden ist), keine Fehler. |
| P3-COM-06 | Keine Versprechen über stabile Reihenfolge bei gleichwertigen Sortierschlüsseln: Die Referenztabellen besitzen keine eindeutigen Schlüssel. |

Bei `select_rows` und `aggregate_rows` gilt: `limit` ist optional, Standardwert **50**, erlaubter Bereich **1–200**. Beide liefern mindestens `rows: list[object]` und `returned_count: int`. `returned_count` ist die Anzahl **dieser Antwort**, nicht die Gesamtzahl aller Datenbanktreffer. Keine Pagination-Metadaten.

### Filter (`where`)

| ID | Verbindliche Anforderung |
| --- | --- |
| P3-FLT-01 | Optionaler rekursiver Filterbaum aus Bedingungen (`column`, `operator`, bei Bedarf `value`) und Gruppen (`logic`: `and`/`or`, nicht leere `conditions`). Verschachtelung ist erlaubt. |
| P3-FLT-02 | Operatoren: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `is_null`, `is_not_null`, `contains`. Keine anderen Operatoren. |
| P3-FLT-03 | `is_null`/`is_not_null` haben **kein** `value`; für `eq`/`ne` mit SQL-NULL ist stattdessen der jeweilige NULL-Operator zu verwenden. `in` verlangt eine nicht leere, begrenzte Liste typkompatibler Werte. |
| P3-FLT-04 | `contains` ist nur für Textspalten zulässig. `%`, `_` und Escape-Zeichen aus Clientwerten werden als **literaler Suchtext**, nicht als SQL-LIKE-Wildcards interpretiert. |
| P3-FLT-05 | Leere Gruppen, unpassende Werttypen, übermäßig tiefe/große Filter und widersprüchliche Eingabeformen werden mit einem kontrollierten Fehler abgewiesen. Implementierungsgrenzen: höchstens 5 Gruppenebenen, 30 Bedingungen insgesamt und 100 Werte je `in`-Liste. |
| P3-FLT-06 | Tabellen-/Spaltenbezeichner werden vor der SQL-Konstruktion geprüft; Nutzwerte werden gebunden und nicht per String-Konkatenation in SQL eingebaut. |

Beispiel eines gültigen Filters:

```json
{
  "logic": "or",
  "conditions": [
    {"column": "pclass", "operator": "eq", "value": 1},
    {
      "logic": "and",
      "conditions": [
        {"column": "age", "operator": "gte", "value": 18},
        {"column": "fare", "operator": "gt", "value": 100}
      ]
    }
  ]
}
```

## 4. Die vier Tools

### 4.1 `list_tables`

| ID | Vertrag |
| --- | --- |
| P3-TBL-01 | Keine Eingaben. Es werden ausschließlich freigegebene **vorhandene** Tabellen aufgelistet. |
| P3-TBL-02 | Antwort: `{ "tables": [{ "name": "Observation", "description": "..." }] }`. `description` ist die fachliche Kurzbeschreibung; eine leere Beschreibung ist zulässig. Die Namen sind alphabetisch sortiert. |

### 4.2 `describe_table`

| ID | Vertrag |
| --- | --- |
| P3-DES-01 | Erforderliche Eingabe: `table: str` (freigegebener Tabellenname, exakte Schreibweise). |
| P3-DES-02 | Antwort enthält `table`, `description`, `columns`, `declared_foreign_keys`, `logical_relationships`, `lookup_values`. Spalten enthalten mindestens `name`, `type`, `nullable`, `primary_key`, `description`. |
| P3-DES-03 | `declared_foreign_keys` dokumentiert ausschließlich wirklich deklarierte DB-Constraints (beim Referenzschema leer). `logical_relationships` enthält getrennt die semantisch bekannten Referenzen. |
| P3-DES-04 | `lookup_values` enthält je logischer Lookup-Beziehung die Schlüssel-/Label-Zuordnung und **aktuell aus der Datenbank** gelesene Werte; keine fest einkodierten Lookup-Daten. Sortierung anhand der Lookup-ID; JSON-geeignete Typen. |
| P3-DES-05 | Auch fachliche Spaltenbeschreibungen werden geliefert, mindestens für die Begriffe `survived`, `sibsp`, `parch`, `fare`, `pclass`, `adult_male`, `alone` sowie die Lookup-Referenzen. Technische und semantische Metadaten bleiben unterscheidbar. |

Vorgeschlagene innere Form (Feldnamen sind Teil des Vertrags):

```json
{
  "table": "Observation",
  "description": "Titanic passenger observations",
  "columns": [
    {"name": "survived", "type": "BIGINT", "nullable": true, "primary_key": false, "description": "Survival indicator (0 or 1)"}
  ],
  "declared_foreign_keys": [],
  "logical_relationships": [
    {"from_column": "sex_id", "to_table": "Sex", "to_column": "sex_id"}
  ],
  "lookup_values": [
    {"from_column": "sex_id", "table": "Sex", "id_column": "sex_id", "label_column": "sex", "values": [{"id": 0, "label": "male"}]}
  ]
}
```

*Das Beispiel illustriert die Struktur; dargestellte Lookup-IDs/-Labels sind keine Zusicherung über den tatsächlichen Datenbestand.* Der Beispielauszug zeigt nicht alle realen Spalten oder Beziehungen. Für die kleinen freigegebenen Lookup-Tabellen werden die vollständigen Werte zurückgegeben; falls eine Lookup-Tabelle unerwartet mehr als 200 Datensätze enthält, ist kontrolliert abzubrechen statt stillschweigend abzuschneiden.

### 4.3 `select_rows`

| ID | Vertrag |
| --- | --- |
| P3-SEL-01 | Erforderlich: `table: str`, `columns: list[str]` (nicht leer, ohne Duplikate, freigegeben). Optional: `where`, `order_by`, `limit`. |
| P3-SEL-02 | `order_by` ist eine Liste aus `{ "column": "age", "direction": "asc" }`; Richtung `asc`/`desc`, nur ausgewählte oder sonst erlaubte Tabellenspalten. |
| P3-SEL-03 | SQLAlchemy Core erstellt eine begrenzte SELECT-Abfrage. Es werden **nur** die angeforderten Spalten ausgegeben; `rows` enthält Objekte mit genau diesen Spaltennamen. |
| P3-SEL-04 | `limit`: Standard 50, maximal 200; `offset` wird nicht angeboten. Keine `has_more`-Berechnung und keine zusätzliche COUNT-Abfrage für Gesamtzahlen. |

Beispielantwort:

```json
{"rows": [{"pclass": 1, "survived": 1}], "returned_count": 1}
```

### 4.4 `aggregate_rows`

| ID | Vertrag |
| --- | --- |
| P3-AGG-01 | Erforderlich: `table: str`, `metrics: list[Metric]` (nicht leer). Optional: `where`, `group_by`, `order_by`, `limit`. |
| P3-AGG-02 | Eine Metrik enthält `function` (`count`, `sum`, `avg`, `min`, `max`), `column` (bei `count` optional, sonst erforderlich) und optional `alias`. `count` ohne Spalte bedeutet `COUNT(*)`, mit Spalte `COUNT(column)` und zählt Nicht-NULL-Werte. |
| P3-AGG-03 | `sum`/`avg` nur für numerische Spalten; `min`/`max` für geeignete, vergleichbare Spalten. Aggregationen werden mit SQLAlchemy Core erstellt. |
| P3-AGG-04 | `group_by` ist eine Liste erlaubter Spalten ohne Duplikate. `order_by` darf auf Gruppenspalten und Ergebnis-Metriknamen/Aliasse verweisen. Keine freien Ausdrücke, Joins oder `HAVING`. |
| P3-AGG-05 | Aliasse sind eindeutig und kollidieren nicht mit Gruppenspalten. Erlaubte Aliasform: `[A-Za-z_][A-Za-z0-9_]*`, maximal 64 Zeichen. Ohne Alias wird ein dokumentierter, stabiler Name generiert, beispielsweise `avg_survived` oder `count_all`. |
| P3-AGG-06 | Limit und Rückgabeformat entsprechen `select_rows`: `{ "rows": [...], "returned_count": n }`. Gruppenspalten und Metriken erscheinen als separate Felder. |

Beispielaufruf für Überlebensanteile nach Klasse:

```json
{
  "table": "Observation",
  "metrics": [{"function": "avg", "column": "survived", "alias": "survival_rate"}],
  "group_by": ["pclass"],
  "order_by": [{"column": "pclass", "direction": "asc"}]
}
```

## 5. Semantic Layer

| ID | Verbindliche Anforderung |
| --- | --- |
| P3-SEM-01 | Kleine statische, versionierte Metadatendefinition; JSON oder Python-Konstante ist zulässig, keine zusätzliche Bibliothek nötig. |
| P3-SEM-02 | Für `Observation` werden die logischen Beziehungen zu `Alive`, `Class`, `Deck`, `EmbarkTown`, `Embarked`, `Sex` und `Who` modelliert. Es handelt sich **nicht** um deklarierte Foreign Keys. |
| P3-SEM-03 | Lookup-Einträge werden bei `describe_table` dynamisch gelesen, nicht gecacht und nicht frei aus SQL-Strings zusammengesetzt. Ungültige oder fehlende Lookup-Strukturen werden nachvollziehbar gemeldet. |
| P3-SEM-04 | Fachliche Erläuterungen sind für einen KI-Client verständlich und eindeutig; insbesondere `survived` als 0/1-Indikator, `sibsp` als Geschwister/Ehepartner an Bord und `parch` als Eltern/Kinder an Bord. |

## 6. Fehler, Sicherheit und Konfiguration

| ID | Verbindliche Anforderung |
| --- | --- |
| P3-ERR-01 | Erwartete Tool-Ausführungsfehler werden nach dem offiziellen SDK-Muster als Tool-Fehler (`is_error=true`) und nicht als erfolgreiches Ergebnis mit Fehlertext gemeldet. Protokollfehler werden nur dort als MCP-/JSON-RPC-Fehler behandelt, wo dies fachlich passt. |
| P3-ERR-02 | Stabile fachliche Fehlercodes, mindestens `TABLE_NOT_FOUND`, `COLUMN_NOT_FOUND`, `INVALID_FILTER`, `INVALID_ARGUMENT`, `INVALID_AGGREGATION`, `DATABASE_UNAVAILABLE`. Sie sind im für den Client sichtbaren Fehlertext eindeutig enthalten (z. B. `[INVALID_FILTER] ...`). |
| P3-ERR-03 | Unerwartete technische Fehler werden gegenüber Clients sanitisiert; keine Stacktraces, SQL-Verbindungsinformationen oder vertraulichen Pfade/Werte. Serverseitige Logs dürfen Diagnoseinformationen enthalten, aber keine Secrets. |
| P3-SEC-01 | Ausschließlich lesende SQL-Operationen. Kein automatisches Anlegen, Migrieren, Zurücksetzen oder Verändern der Datenbank. Eine fehlende Datenbank darf nicht stillschweigend als neue SQLite-Datei erstellt werden. |
| P3-SEC-02 | Eingabe-/Ergebnislimits, Allowlist und Parametrisierung sind unabhängig von den Tool-Beschreibungen technisch durchgesetzt. |
| P3-SEC-03 | HTTP bindet standardmäßig nur an `127.0.0.1`; Host-/Origin-Schutz des SDKs wird nicht pauschal ausgeschaltet. Kein öffentlicher, unauthentifizierter Server als Phase-3-Standard. |
| P3-RUN-01 | Ein ausführbarer Einstiegspunkt entsprechend `[project.scripts]`: `mcp-data-gw = "mcp_data_gw:main"`, mit Streamable HTTP (Standardpfad `/mcp`). |
| P3-RUN-02 | Stateless HTTP mit JSON-Antworten wird bevorzugt. Keine serverseitig benötigte Session zur Ausführung einfacher Reads. |
| P3-RUN-03 | Minimale Umgebungsvariablen: `MCP_DATA_GW_DATABASE_URL` (erforderlich; SQLite-URL), `MCP_DATA_GW_HOST` (Default `127.0.0.1`), `MCP_DATA_GW_PORT` (Default `8000`). Ungültige Konfiguration führt zu einem verständlichen, sicheren Fehler. |
| P3-RUN-04 | Ressourcen (Connections/Engines) werden kontrolliert freigegeben. Bei Datenbankausfall werden Fehler begrenzt und ohne verdeckte Endlos-Retries gemeldet. |
| P3-RUN-05 | Ein kurzes README-Update dokumentiert Konfiguration, Start, Tool-Überblick, manuelle Smoke-Prüfung und die lokale Zugriffsgrenze. Eine `.env.example` ist optional und enthält niemals echte Secrets. |

Die Standardkonfiguration bindet an Loopback. Hinweise zum Sicherheitsmodell für externen Betrieb stehen im [README](../../README.md#anmerkungen).

## 7. Tests und Änderungsbefugnisse

| ID | Verbindliche Anforderung |
| --- | --- |
| P3-TST-01 | Unit-Tests prüfen Validierung, Allowlist, Filter-/Aggregationserzeugung, Parameterbindung, Limits, Semantic Layer und Fehlerzuordnung ohne Datenbankzugriff. Mocks nur an erforderlichen Grenzen. |
| P3-TST-02 | MCP-Vertragstests verwenden den offiziellen In-Memory-Client mit gemocktem Repository/Service. Die beigefügte `test_server.py` dient nur als **Testmuster**, nicht als kopierbare Projektdatenquelle. |
| P3-TST-03 | Keine temporäre Testdatenbank und kein automatisierter SQLite-Integrationstest. Ein manueller Smoke-Test gegen eine bereits vorbereitete Titanic-DB ist Abnahmekriterium; kein Reset vorhandener Daten ohne Erlaubnis. |
| P3-TST-04 | Ruff und pytest bestehen; `unit`- und `integration`-Marker entsprechen der `pyproject.toml`. Zusätzliche Testbibliotheken werden nicht ungefragt eingeführt. |
| P3-GOV-01 | Erlaubt: `uv sync --locked` und `uv run --locked ...` für Tests/Linting. Keine neue Abhängigkeit, kein `uv lock`, keine Änderung an `pyproject.toml` oder `uv.lock` ohne ausdrückliche Zustimmung. Der Coding-Agent aktualisiert die widersprechende Installationsregel in `AGENTS.md` entsprechend. |
| P3-GOV-02 | Kleine interne Code-/Dateientscheidungen sind delegiert. Änderungen an Tool-Anzahl/-Namen, Ein-/Ausgabeverträgen, Schema, Sicherheit, Teststrategie oder Phasenumfang benötigen vor Umsetzung Zustimmung. |
| P3-GOV-03 | Substanzielle KI-Beiträge werden in `AI_DISCLOSURE.md` korrekt nachgeführt. Keine ungeprüften Tests als bestanden oder unerprobte Abläufe als verifiziert darstellen. |

## 8. Referenzen

- Phase 1: allgemeine Architektur, vollständiges Referenzschema, Sicherheits- und Produktionsreifeprinzipien.
- Phase 2: Projektstruktur, uv-, Ruff-, pytest- und Dev-Container-Konventionen.
- `AGENTS.md` und `agents/AGENT_INSTRUCTIONS.md`: verbindliche Arbeitsregeln im tatsächlichen Repository.
- Offizielle SDK-Dokumentation: [Tools und strukturierte Ausgaben](https://py.sdk.modelcontextprotocol.io/servers/structured-output/), [Fehlerbehandlung](https://py.sdk.modelcontextprotocol.io/servers/handling-errors/), [Tests](https://py.sdk.modelcontextprotocol.io/get-started/testing/), [HTTP-Betrieb und Sicherheit](https://py.sdk.modelcontextprotocol.io/run/deploy/).
