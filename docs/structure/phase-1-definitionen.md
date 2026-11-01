# Coding Challenge – Phase 1: Definitionen

**Status:** abgeschlossen
**Stand:** 31. Oktober 2026
**Gegenstand:** MCP-Server als kontrolliertes Gateway zu einer relationalen Datenbank

Dieses Dokument beschreibt Architektur und Funktionsumfang des MVP. Der MVP umfasst vier lesende Tools; der aktuelle Implementierungsstand und die Einschränkungen stehen im [README](../../README.md). Produktionsreife ist hier ein Qualitätsziel, kein nachgewiesener Ist-Zustand.

## 1. Ziel und Rahmen

Ziel ist die Entwicklung eines **produktionsreifen, grundsätzlich deploybaren MCP-Servers**, mit dem KI-Assistenten eine Datenbank über klar definierte Tools lesen können. Produktionsreife bezeichnet hier die Qualität und Absicherung der Software, nicht den Aufbau produktiver Infrastruktur.

Die Challenge soll einen verständlichen Architekturansatz, zuverlässige Implementierung, Tests, nachvollziehbare Entscheidungen und einen transparent dokumentierten KI-Einsatz zeigen. Eine reproduzierbare Offline-Demonstration ist vorgesehen; eine Live-Demo mit ChatGPT über einen bereits vorhandenen Secure MCP Tunnel ist optional. Die Tunnelkonfiguration wird nicht im Detail spezifiziert.

### Im Scope

- MCP-Server mit vier lesenden Tools.
- Strukturierte Datenbankoperationen ohne frei übergebenen SQL-Code.
- Ein kleiner Semantic Layer mit fachlichen Beschreibungen und dynamischen Lookup-Werten.
- SQLite und Titanic-Datensatz als reproduzierbare Demo-Umgebung.
- Validierung, Fehlerbehandlung, Logging, Tests, Sicherheitsmaßnahmen und Konfiguration.
- Lokaler Betrieb mit Docker Compose und Streamable HTTP.
- Deutsche Projektdokumentation; `AI_DISCLOSURE.md` und Agentenanweisungen auf Englisch.

### Außerhalb des Scopes

- Cloud- oder Hochverfügbarkeitsinfrastruktur.
- Eigene grafische Oberfläche.
- Ein frei verwendbares SQL-Tool beziehungsweise eigener SQL-Syntaxparser.
- Vollständiges Semantic-Layer-Framework oder umfangreiche fachliche Business-Schicht.
- Mehrere gleichzeitig unterstützte Datenbanksysteme als Implementierungsziel.
- Komplexe Microservice-Architektur, Kubernetes oder umfassende Observability-Plattform.

## 2. Phasen der Implementierung

Die bisherige Implementierung wurde in folgende Phasen unterteilt:

| Phase | Inhalt | Ergebnis |
| --- | --- | --- |
| 1 | Definitionen, Tools, Architektur, Qualitätsziele | Dieses Konzept |
| 2 | Minimaler Projekt- und Git-Setup; Verzeichnisse nur bei Bedarf | Lauffähiges Grundgerüst, Konfiguration, Demo-Datenbankaufbau |
| 3 | Lesende Tools | Absolutes Minimum eines vorzeigbaren Projekts |

Die Phasen sollen jeweils einen funktionsfähigen Zwischenstand hinterlassen. Es werden keine großen Strukturen aus leeren Ordnern angelegt.

## 3. Architekturprinzipien

**Ein einzelner, modularer Dienst.** Die MCP-Schnittstelle wird von Validierung, Anwendungslogik, semantischen Metadaten und Datenbankzugriff getrennt. Die Fach- und Abfragelogik muss ohne MCP-Client testbar sein.

```text
MCP-Client (optional ChatGPT)
    → Streamable HTTP (ggf. über Secure MCP Tunnel)
    → MCP-Tools
    → Eingabevalidierung / Anwendungslogik
    ├── Semantic Layer (Beschreibungen + Lookup-Auflösung)
    └── SQLAlchemy Core → SQLite (Demo)
```

Die Tools nehmen **keine SQL-Strings** entgegen. Sie erhalten strukturierte Parameter. SQLAlchemy Core erzeugt parametrisierte Datenbankabfragen; Tabellen und Spalten werden gegen die erlaubte Datenbankstruktur geprüft. Ein selbst entwickelter SQL-Parser ist nicht vorgesehen.

## 4. Datenquelle und Demo-Datenbank

### Datenherkunft

- Titanic-CSV aus [`mwaskom/seaborn-data`](https://github.com/mwaskom/seaborn-data/blob/master/titanic.csv), in der Aufgabenstellung empfohlen.
- Tabellen-/Spaltentypen aus [`davidjamesknight/SQLite_databases_for_learning_data_science`](https://github.com/davidjamesknight/SQLite_databases_for_learning_data_science).
- [Referenz-`titanic.db`](https://github.com/davidjamesknight/SQLite_databases_for_learning_data_science/raw/refs/heads/main/titanic.db) dient nur als Vergleichsobjekt; die Binärdatei wird nicht übernommen, sondern aus Gründen der Reproduzierbarkeit neu erzeugt.

Der Datensatz wird im Projekt mit Quellenverweis dokumentiert. Das Referenz-Repository bezeichnet die verwendeten Daten allgemein als Open Source beziehungsweise Public Domain; eine bestimmte Lizenz für die einzelne Seaborn-CSV wird nicht behauptet.

### Referenzschema

Tabellen, Spalten und deklarierte Typen werden als Vorgabe übernommen:

| Tabelle | Spalten (Typ) |
| --- | --- |
| `Alive` | `alive_id BIGINT`, `alive TEXT` |
| `Class` | `class_id BIGINT`, `class TEXT` |
| `Deck` | `deck_id BIGINT`, `deck TEXT` |
| `EmbarkTown` | `embark_town_id BIGINT`, `embark_town TEXT` |
| `Embarked` | `embarked_id BIGINT`, `embarked TEXT` |
| `Observation` | `survived BIGINT`, `pclass BIGINT`, `age FLOAT`, `sibsp BIGINT`, `parch BIGINT`, `fare FLOAT`, `adult_male BOOLEAN`, `alone BOOLEAN`, `sex_id BIGINT`, `embarked_id BIGINT`, `class_id BIGINT`, `who_id BIGINT`, `deck_id BIGINT`, `embark_town_id BIGINT`, `alive_id BIGINT` |
| `Sex` | `sex_id BIGINT`, `sex TEXT` |
| `Who` | `who_id BIGINT`, `who TEXT` |

**Wichtige Einschränkung:** Die Referenzdatenbank deklariert **keine Primary-Key- oder Foreign-Key-Constraints**. Das Schema wird deshalb nicht um solche Constraints oder eine zusätzliche `observation_id` verändert. Die `_id`-Namen und die Beziehungen zwischen Tabellen sind fachliche Konventionen, keine durch SQLite erzwungenen Garantien.

Konsequenzen:

- Der Semantic Layer beschreibt logische Beziehungen ausdrücklich; `describe_table` darf sie nicht als tatsächlich deklarierte Foreign Keys ausgeben.
- Beim Import werden referenzierte Werte und Eindeutigkeit der Lookup-IDs geprüft.
- Ohne Primary Key können mehrere Zeilen dieselben Werte besitzen; die Reihenfolge bei gleichen Sortierschlüsseln ist nicht garantiert.

### Reproduzierbare Erzeugung und Reset

`scripts/generate_titanic_db.py` erzeugt die SQLite-Datenbank aus einer lokal bereitgestellten CSV mithilfe der Python-Standardbibliothek `sqlite3`. Schema und Lookup-Zuordnungen sind im Skript enthalten; Spalten und Eingabewerte werden beim Import geprüft.

- **Keine** SQLite-Binärdatei und **keine** Titanic-CSV im Git-Repository.
- Generierte Dateien werden ignoriert; Herkunft und Prüfsumme werden dokumentiert.
- Der Reset ist ein **bewusster lokaler Wartungsbefehl**, kein MCP-Tool.
- Ein Reset verwirft Demo-Änderungen und erzeugt die Datenbank erneut.
- Für vollständigen Offline-Betrieb werden CSV beziehungsweise fertige Datenbank vorab lokal vorbereitet; ohne lokale CSV ist ein erneuter Aufbau gegebenenfalls netzabhängig.

## 5. MCP-Tool-Katalog

**Variante A1:** Strukturierte Operationen über bekannte Tabellen und Spalten. Keine unbeschränkte SQL-Ausführung. Tool-Namen und technische Bezeichner sind englisch.

| Tool | Phase | Funktion | Zentrale Eingaben |
| --- | --- | --- | --- |
| `list_tables` | 3 | Freigegebene Tabellen auflisten | keine |
| `describe_table` | 3 | Technisches Schema und semantische Informationen | `table` |
| `select_rows` | 3 | Zeilen auswählen und filtern | `table`, `columns`; optional `where`, `order_by`, `limit` |
| `aggregate_rows` | 3 | Aggregieren und gruppieren | `table`, `metrics`; optional `where`, `group_by`, `order_by`, `limit` |

### Gemeinsame Filterstruktur

`where` ist ein rekursiver Ausdruck aus einzelnen Bedingungen und Gruppen:

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

Unterstützt werden `and` und `or`, einschließlich Kombinationen. Vergleichsoperatoren: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `is_null`, `is_not_null`, `contains`. Der Textoperator `contains` interpretiert Client-Eingaben als wörtlichen Suchtext und behandelt SQL-Wildcards sicher. Bei NULL-Operatoren entfällt `value`; bei `in` ist eine begrenzte Liste erforderlich. Leere Gruppen und übermäßig tiefe oder große Filterbäume werden abgelehnt. Der genaue Grenzwert ist Implementierungsdetail.

### `select_rows`

- `table`: erlaubter Tabellenname, erforderlich.
- `columns`: nicht leere Liste erlaubter Spalten, erforderlich.
- `where`: optionaler strukturierter Filter.
- `order_by`: Liste aus Spalte und Richtung (`asc`/`desc`), optional.
- `limit`: Standard **50**, maximal **200**.

Rückgabe als strukturiertes JSON mit `rows` und `returned_count`; das Limit begrenzt die Ergebniszeilen.

### `aggregate_rows`

- `metrics`: nicht leere Liste aus `function`, optional `column`, optional `alias`.
- Funktionen: `count`, `sum`, `avg`, `min`, `max`; `sum` und `avg` nur für passende numerische Spalten.
- `group_by`: Liste erlaubter Spalten, optional.
- `where`, `order_by`, `limit`: analoge kontrollierte Parameter.
- Keine freien SQL-Ausdrücke, kein `HAVING`, kein Join in Version 1.

Zum Beispiel lässt sich die Überlebensrate pro Klasse mit `avg(survived)` gruppiert nach `pclass` bestimmen, da `survived` als 0/1 kodiert ist.

### Ergebnisse und Fehler

Alle Tools liefern konsistente, strukturierte Ergebnisse. Fehler besitzen stabile Codes, zum Beispiel `TABLE_NOT_FOUND`, `COLUMN_NOT_FOUND`, `INVALID_FILTER`, `INVALID_ARGUMENT`, `INVALID_AGGREGATION` und `DATABASE_UNAVAILABLE`. Interne Stacktraces oder Zugangsdaten werden niemals an MCP-Clients ausgegeben. Protokoll- und Toolausführungsfehler werden passend zum MCP-SDK behandelt.

## 6. Semantic Layer

Der Semantic Layer ist **keine zusätzliche SQL-Abfrageschicht** und zunächst kein eigenes MCP-Tool. Er erweitert `describe_table`:

1. Statische fachliche Beschreibung von Tabellen und Spalten, besonders `Observation` (etwa `sibsp`, `parch`, `survived`, `fare`).
2. Statische Beschreibung **logischer** Lookup-Beziehungen wie `Observation.sex_id` → `Sex.sex_id`.
3. Dynamisches Nachladen der aktuellen Lookup-Werte und Labels aus der Datenbank.
4. Strukturierte Einbettung der Lookup-Mappings in der Tool-Antwort, um unnötige weitere MCP-Abfragen zu vermeiden.

Die statischen Angaben liegen in `metadata.py`. Dynamische Lookup-Werte werden bei jedem Aufruf neu gelesen und als strukturierte JSON-Daten eingebettet. Lookup-Tabellen mit mehr als 200 Einträgen werden kontrolliert abgewiesen.

Technische Metadaten aus SQLAlchemy Reflection und **ergänzte semantische Beziehungen** werden in der Ausgabe klar getrennt.

## 7. Technologie-Stack

| Bereich | Entscheidung |
| --- | --- |
| Sprache | Python |
| MCP | Offizielles Python MCP SDK |
| Transport | Streamable HTTP |
| Datenbankzugriff | SQLAlchemy Core, ohne ORM-Mappingklassen |
| Validierung | Pydantic; durch das MCP SDK ohnehin im Abhängigkeitsgraphen vorhanden |
| Demo-Datenbank | SQLite und Python-Standardbibliothek für CSV-/Dateiverarbeitung |
| Tests | pytest (Unit und Integration) |
| Lint/Format | Ruff |
| Containerbetrieb | Ein Dienst über Docker Compose |

Die direkten Abhängigkeiten und Versionen sind in `pyproject.toml` und `uv.lock` dokumentiert.

## 8. Sicherheits- und Betriebsregeln

### Sicherheit und Validierung

- Typisierte Tool-Eingaben und Ausgaben, ergänzende fachliche Validierung.
- Allowlist für zugängliche Tabellen, Spalten und Vergleichsoperatoren.
- Ausschließlich durch SQLAlchemy Core erzeugte parametrisierte Abfragen.
- Limits für Ergebnisse, Filterkomplexität und Laufzeiten.
- Sicherer Umgang mit fehlenden oder ungültigen Lookup-Beziehungen.
- Lesender Datenbankzugriff, kontrollierte Fehlermeldungen und strukturierte Fehlerprotokolle ohne vertrauliche Ausnahmemeldungen.

### Zugriffsgrenze

Der Server bindet standardmäßig an Loopback und öffnet SQLite ausschließlich lesend. Hinweise zum Sicherheitsmodell für externen Betrieb und zur lokalen Antwortprotokollierung stehen im [README](../../README.md#anmerkungen).

### Lokaler Betrieb

- Ein Container, Streamable-HTTP-Endpunkt, konfigurierbare Host-/Port-/Datenbankeinstellungen.
- Portfreigabe lokal begrenzt, sofern kein ausdrücklich konfigurierter Tunnel verwendet wird.
- Persistente SQLite-Datei; kein automatischer Reset bei jedem Start.
- Sauberer Start und Stopp, Ressourcenfreigabe und eindeutige Konfigurationsfehler.

## 9. Qualität und Betriebseigenschaften

| Eigenschaft | Umsetzung im MVP |
| --- | --- |
| Zuverlässigkeit | Kontrollierte Fehler, kooperative Abfragezeitgrenzen und Ressourcenfreigabe |
| Sicherheit | Lesender SQLite-Zugriff, lokale Defaults, Allowlist, Parametrisierung und Eingabe-/Ergebnislimits |
| Diagnose | Strukturierte Fehlerereignisse und lokale Aufruf-/Antwortprotokolle |
| Skalierbarkeit | Zustandslose MCP-Anwendungslogik und Trennung vom Datenbankzugriff; SQLite und Abfragekosten bestimmen den tatsächlichen Durchsatz mit |
| Wiederanlauf | Neustart und unveränderte Datenbank im manuellen Smoke-Test geprüft |
| Wartbarkeit | Modulgrenzen, typisierte Verträge, Ruff und pytest |

Die konkreten Prüfergebnisse stehen im [Implementierungsbericht](../requirements/phase-3-implementation.md).

## 10. Qualität und Teststrategie

### Unit Tests

- Pydantic-Validierung, erlaubte Tabellen/Spalten, Filteroperatoren und `and`/`or`-Bäume.
- Erstellung der SQLAlchemy-Ausdrücke und sichere Parameterbindung.
- Aggregationen, Limits, Sortierung, Textsuche und NULL-Verhalten.
- Semantic-Layer-Metadaten, Lookup-Auflösung, Fehlercode-Zuordnung.

### Integration Tests

- In-Memory-Aufrufe der MCP-Tools einschließlich strukturierter Antworten mit Mocks an der Datenbankgrenze.
- Validierung und kontrollierte Fehler bei Datenbankausfällen.
- Separater manueller Smoke-Test über lokales HTTP gegen SQLite, einschließlich Vergleich der Abfrageergebnisse, Neustart und unveränderter Datenbankdatei.

Die optionale ChatGPT-Live-Demo ist ein zusätzlicher manueller End-to-End-Nachweis, kein Ersatz für automatisierte Tests.

## 11. Dokumentation und KI-Einsatz

**Projektdokumentation, Architekturentscheidungen und Erläuterungen: Deutsch.** Quellcode, Bezeichner, Kommentare im Code und Testnamen: **Englisch**. Technische Tool-Namen und maschinenlesbare Fehlercodes sind englisch.

Erwartete Dokumentation:

- `README.md`: Ziel, Installation, Konfiguration, Demo, bekannte Einschränkungen.
- Tool- und Architekturreferenz: Verträge, Semantic Layer, Entscheidungen und Sicherheitsprinzipien (kann kompakt im README oder in bedarfsgerecht angelegten Dateien erfolgen).
- **`AI_DISCLOSURE.md` im Git-Repository:** zusammenfassende Angaben zur KI-Unterstützung nach Projektbereich. Prüfergebnisse und offene Prüfungen stehen im Implementierungsbericht.

Die Projektdokumentation wurde überwiegend mit generativer KI erstellt und anschließend bearbeitet. Durchgeführte Prüfungen und noch offene Nachweise sind im Implementierungsbericht dokumentiert.

## 12. Projektstand

Die Phasen 1–3 sind abgeschlossen. Setup, Tool-Verträge und Prüfergebnisse stehen in den zugehörigen Dokumenten; der aktuelle Überblick im [README](../../README.md).
