# Phase 3 – Implementierungsstand und Prüfung

## Aktuelle Prüfung vor Veröffentlichung

Am 1. November 2026 ausgeführt:
`uv run --locked pytest -q` ergab
**101 bestandene Tests**. `uv run --locked ruff check .`,
`uv run --locked ruff format --check .` und `git diff --check` waren erfolgreich.
Die Tests prüfen nun die erlaubte Compose-Bind-Adresse `0.0.0.0` sowie die
Ablehnung eines nicht erlaubten Hostnamens. Die nachfolgenden Ergebnisse
dokumentieren frühere Prüfläufe.

`.dockerignore` schließt lokale Umgebungsdateien, Git-Historie, Datenbanken,
Logs, virtuelle Umgebungen und Build-/Testartefakte aus dem Build-Kontext aus.

Die folgenden Phasenangaben beziehen sich auf den ursprünglichen Phase-3-Umfang.
Die Compose-Konfiguration ist im [README](../../README.md) beschrieben.

**Stand:** 1. November 2026
**Status:** Implementierung abgeschlossen; automatisierte Prüfungen erfolgreich,
SM-01–SM-07 erfolgreich; Docker-Compose-Betrieb geprüft; MVP freigegeben.

## Implementierte Bestandteile

| Dateien | Inhalt |
| --- | --- |
| `cli.py`, `__init__.py`, `config.py` | CLI-Einstieg, kompatibler Export, Umgebungsvariablen, lokale Defaults und Ressourcenfreigabe |
| `database.py` | Lesender SQLite-Zugriff mit `mode=ro`, Reflection ohne ORM und begrenzte Ausführungszeit |
| `metadata.py`, `models.py`, `errors.py` | Tabellen-/Spalten-Allowlist, semantische Beschreibungen, strikte Modelle und kontrollierte Fehler |
| `queries.py` | Validierung, Filterübersetzung sowie SELECT- und Aggregationsstatements |
| `service.py` | Tabellenkatalog, technische Metadaten, getrennte logische Beziehungen und aktuelle Lookup-Werte |
| `server.py` | Vier MCP-Tools mit strukturierten Ergebnissen und sicheren Fehlermeldungen |
| `tests/` | Unit-Tests, In-Memory-MCP-Vertragstests und ASGI-Sicherheitsprüfung |

Die Abfrageprüfung umfasst gefilterte `COUNT(*)`-Abfragen sowie die Sortierung nach
Metriknamen und Aliassen. Alle In-Memory-MCP-Testclients verwenden
`raise_exceptions=True`. Öffentliche APIs und Tools haben Google-Docstrings.
Die Verbindungsverwaltung nutzt `@contextmanager` mit `Generator[Connection]`
als Rückgabeannotation.

Die KI-Unterstützung ist zusammenfassend in [AI_DISCLOSURE.md](../../AI_DISCLOSURE.md)
dokumentiert.

## Dokumentierte Prüfergebnisse

Die folgenden Ergebnisse stammen aus den zuletzt dokumentierten Prüfläufen.
Umgebung: CPython 3.14.7; Python 3.13 wurde nicht separat geprüft.

| Befehl | Ergebnis |
| --- | --- |
| `uv sync --locked` | Erfolgreich |
| `uv run --locked ruff check .` | Erfolgreich |
| `uv run --locked ruff format --check .` | Erfolgreich |
| `uv run --locked pytest -q` | 92 bestanden |
| `uv run --locked pytest -m unit -q` | 82 bestanden, 10 abgewählt |
| `uv run --locked pytest -m integration -q` | 10 bestanden, 82 abgewählt |
| `uv run --locked pytest tests/test_runtime.py -q` | 13 bestanden nach Anpassung der Generator-Annotation |
| `git diff --check` | Erfolgreich |

Automatisierte Tests verwenden Metadaten und Mocks an der Datenbankgrenze. Sie
belegen keine tatsächliche SQL-Ausführung gegen SQLite. Die Prüfung umfasste
keine Datenbank-/Schemaänderungen, neuen Abhängigkeiten oder Lockfile-Änderungen.

## Abnahmestand

| Kriterien | Stand |
| --- | --- |
| AC-01–AC-06 | Tool-Katalog, Metadaten, SELECTs, Aggregationen und strukturierte Ergebnisse automatisiert geprüft |
| AC-07–AC-11 | Validierung, Filter, Parameterbindung, Grenzen und Aggregationsregeln automatisiert geprüft |
| AC-12 | Lesender Zugriff und verzögerte Dateiverbindung durch Codeprüfung und Mock-Tests geprüft |
| AC-13–AC-14 | Dynamische Lookups, Beschreibungen und kontrollierte Fehlermeldungen automatisiert geprüft |
| AC-15–AC-16 | CLI-Anbindung, lokale Defaults, Host-/Origin-Schutz und Tests ohne SQLite-Fixture geprüft |
| SM-01–SM-07 | Erfolgreich am 31. Oktober 2026; HTTP-Nachweis unten |

Das ursprüngliche Prüfverfahren: den HTTP-Server mit einer vorhandenen Datenbank
starten, die vier Tools prüfen und nach einem Neustart die Unverändertheit von
Datei und Schema bestätigen. Ergebnisse mit Datum, Startbefehl, Beispielargumenten
und Pass/Fail je Prüfschritt hier ergänzen. Die vollständigen Kriterien stehen in
[phase-3-acceptance.md](phase-3-acceptance.md).

Falls noch keine Datenbank vorliegt, erzeugt das folgende Kommando eine neue Datei
aus der lokal bereitgestellten Titanic-CSV; das Schema ist im Skript enthalten:

```bash
uv run --locked python scripts/generate_titanic_db.py /path/to/titanic.csv /path/to/titanic.db
```

Eine vorhandene Datenbank wird dabei nicht überschrieben. Für die manuelle
HTTP-Prüfung ist ein MCP-Client erforderlich; das Laden einer Browserseite allein
ist kein Nachweis eines erfolgreichen Tool-Aufrufs.

Anwendungsauthentifizierung und Docker-Laufzeitartefakte
gehören nicht zum Phase-3-Umfang. Die unten dokumentierte Smoke-Prüfung bestätigt das reale
Reflection-, Abfrage- und Wiederanlaufverhalten einschließlich der konfigurierten
SQLite-Zugriffe. Die Einhaltung der Zeitgrenzen bei langlaufenden oder gesperrten Abfragen wurde damit nicht separat nachgewiesen.

## Nachprüfung: explizite Filterschemas

Die Tool-Signaturen von `select_rows` und `aggregate_rows` verwenden nun die
vorhandenen Modelle `Condition` und `FilterGroup`. Die veröffentlichten
JSON-Eingabeschemas enthalten damit Pflichtfelder, Operatoren, AND/OR-Gruppen,
rekursive Referenzen und lokale Gruppengrößen. Spaltentypabhängige Regeln und
die Gesamtgrenzen für Tiefe und Bedingungszahl bleiben Laufzeitvalidierungen.
Die JSON-Aufrufform bleibt erhalten. Strukturfehler werden bereits durch die
SDK-Modellvalidierung als Tool-Fehler gemeldet; fachliche Fehler werden weiterhin
in der Anwendung geprüft.

Nach dieser Änderung ausgeführt: `uv run --locked ruff check .`,
`uv run --locked ruff format --check .`, `uv run --locked pytest -q`
(**95 bestanden**) und `git diff --check`; alle erfolgreich.
Die neuen MCP-Vertragstests prüfen die veröffentlichten rekursiven Schemas sowie
verschachtelte Filter und NULL-Wert-Auslassung für beide Abfragetools.
Die damals offene Datenbankprüfung ist durch den unten dokumentierten Smoke-Test abgeschlossen. Die KI-Unterstützung fällt unter die
bestehende Zuordnung für Quellcode, Tests und Dokumentation in `AI_DISCLOSURE.md`.

## Nachprüfung: Antwortprotokollierung und Tool-Annotationen

`keep_mcp_response` erhält synchrone bzw. asynchrone Handler und deren Signaturen.
Pydantic-Ergebnisse werden als JSON-Objekte in `logs/mcp_responses.jsonl`
geschrieben. Schreibfehler verhindern keine Tool-Antwort; Fehlerdatensätze enthalten
nur den Ausnahmetyp, keine möglicherweise vertraulichen Ausnahmemeldungen.
Die Datei enthält Aufrufargumente und Ergebnisse und ist entsprechend zu behandeln.
Automatisierte Tests schreiben ausschließlich in temporäre Verzeichnisse.

Alle vier Tools veröffentlichen einen Titel sowie `readOnlyHint=true`,
`destructiveHint=false`, `openWorldHint=false` und `idempotentHint=true`.
Die installierte offizielle SDK-Version akzeptiert bei `ToolAnnotations` sowohl
snake_case als auch camelCase. Der Code verwendet entsprechend der offiziellen
Dokumentation snake_case; das Protokoll verwendet camelCase. Die Annotationen beschreiben
die Datenbankoperationen; lokale Diagnoseprotokolle werden weiterhin ergänzt.

Nach dieser Änderung: `uv run --locked pytest -q` (**100 bestanden**),
`uv run --locked ruff check .`, `uv run --locked ruff format --check .`
und `git diff --check` erfolgreich. KI-Unterstützung ist durch die bestehenden
Einträge für Quellcode, Tests und Dokumentation in `AI_DISCLOSURE.md` erfasst.


## Smoke-Test mit der bereitgestellten Datenbank

**Datum:** 31. Oktober 2026. **Ergebnis:** SM-01–SM-07 bestanden.
Vorhandene Datei `data/titanic.db`, ohne Import, Reset oder Schemaänderung.
CPython 3.14.7, offizieller MCP-Client und reales lokales Streamable HTTP;
keine gemockte Datenbankgrenze.

Ein einmaliges temporäres Prüfskript wurde mit
`uv run --locked python /tmp/mcp-gw-smoke.py` ausgeführt. Es gehört nicht zur
automatisierten Testsuite und ist kein dauerhaftes Projektartefakt. Es startete
den installierten CLI-Einstieg zweimal mit folgenden Einstellungen:

```bash
MCP_DATA_GW_DATABASE_URL=sqlite:////work/repo/data/titanic.db \
MCP_DATA_GW_HOST=127.0.0.1 MCP_DATA_GW_PORT=49387 \
/work/repo/.venv/bin/mcp-data-gw
```

Arbeitsverzeichnis war ein temporäres Verzeichnis; Client-Endpunkt:
`http://127.0.0.1:49387/mcp`. Der freie Port wurde vor dem Start lokal ermittelt.
Beide Prozesse wurden per SIGTERM beendet; beide Serverlogs bestätigten
`Application shutdown complete`. Der Signal-Exitcode `-15` ist dabei erwartet.

| Prüfung | Verifizierter Nachweis | Ergebnis |
| --- | --- | --- |
| SM-01 | HTTP-Tool-Katalog enthält genau vier Tools; alle vier Verhaltenshinweise pro Tool geprüft | Bestanden |
| SM-02 | `list_tables()` und `describe_table(table="Observation")`: acht Tabellen, 15 Spalten, keine PK/FK, sieben logische Beziehungen und sieben vollständige Lookup-Zuordnungen; mit lesenden SQLite-Abfragen verglichen | Bestanden |
| SM-03 | `select_rows(table="Observation", columns=["pclass","survived"], limit=5)`: fünf Zeilen, exakte Projektion, native Integer und passender Zähler; identisch mit SQLite | Bestanden |
| SM-04 | Filter `age >= 18 AND (pclass = 1 OR survived = 1)`, Projektion und aufsteigende Sortierung `age,pclass,survived`, Limit 20: identisch mit SQLite. `survived = -999`: leere Zeilen und Zähler 0 | Bestanden |
| SM-05 | `count(*) = 891`; Filter `survived = 1`: `342`. `avg(survived)` als `survival_rate`, gruppiert nach `pclass`, absteigend nach Alias: Klasse 1 ca. 0,62963, Klasse 2 ca. 0,47283, Klasse 3 ca. 0,24236; identisch mit SQLite | Bestanden |
| SM-06 | Unbekannte Tabelle, unbekannte Spalte, Operator `invalid`, Limit 0: jeweils MCP-Tool-Fehler ohne SQL-Abfrage, Traceback oder Datenbankpfad im Clientfehler | Bestanden |
| SM-07 | Nach Stop und Neustart gleiche Projektion `pclass,survived`, sortiert nach beiden Spalten, Limit 5: identisch. Nach beiden Stopps vollständiges Schema und SHA-256 unverändert | Bestanden |

SHA-256 vor und nach dem Lauf:
`9b4275c80cf2101fb775a8ac7b92c0cf7664094719ce3dd6a32cf65ddb36e633`.
Schemavergleich: `type,name,tbl_name,sql` aller `sqlite_master`-Einträge,
sortiert nach Typ und Name. Alle Vergleichsabfragen verwendeten SQLite `mode=ro`.

Zusätzlich geprüft: zwölf gültige JSONL-Protokollzeilen im temporären
Server-Arbeitsverzeichnis, alle vier Tool-Namen sowie Erfolgs- und Fehlerdatensätze.
Schemafehler, die das SDK vor dem Handler zurückweist, erreichen den Decorator
nicht und werden daher nicht von ihm protokolliert.

Erneut ausgeführt: Ruff-Lint und Formatprüfung erfolgreich; `pytest -q`:
**100 bestanden**; Unit-Tests: **87 bestanden**, 13 abgewählt;
Integrationstests: **13 bestanden**, 87 abgewählt. `git diff --check` erfolgreich.
Automatisierte Integrationstests bleiben In-Memory-Tests mit gemockter DB-Grenze.
