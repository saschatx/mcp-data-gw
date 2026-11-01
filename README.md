# mcp-data-gw

Python-basierter [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)-Server für einen kontrollierten, ausschließlich lesenden Zugriff auf eine SQLite-Datenbank mit Titanic-Daten.

Das Projekt entstand im Rahmen einer Coding Challenge als Teil eines Bewerbungsprozesses. Der aktuelle Implementierungs- und Teststand sowie offene Punkte sind nachfolgend dokumentiert.

## Implementierungsstand

- Vier lesende MCP-Tools über **Streamable HTTP** mit JSON-Antworten und zustandslosem Serverbetrieb.
- SQLAlchemy Core, tabellenbasierte Allowlist sowie Validierung von Projektionen, Filtern, Sortierungen und Aggregationen.
- Automatisierte Unit-, Integrations- und MCP-Vertragstests mit Mocks an der Datenbankgrenze.
- Docker-Compose-Setup für die Anbindung an ChatGPT über OpenAI Secure MCP Tunnel.

## Voraussetzungen und Start

- Python-Umgebung und [`uv`](https://docs.astral.sh/uv/)
- Bereits vorhandene, zum erwarteten Schema passende SQLite-Datei. Mit dem Skript [`scripts/generate_titanic_db.py`](scripts/generate_titanic_db.py) lässt sich eine neue Datenbank erzeugen. Die benötigte CSV-Datei ist [im Seaborn-Repository](https://github.com/mwaskom/seaborn-data/blob/master/titanic.csv) verfügbar.

```bash
uv sync --locked

export MCP_DATA_GW_DATABASE_URL='sqlite:////absoluter/pfad/titanic.db'
uv run --locked mcp-data-gw
```

Der MCP-Endpunkt ist bei Standardkonfiguration `http://127.0.0.1:8000/mcp`. Ein kompatibler MCP-Client kann darüber die verfügbaren Tools ermitteln und aufrufen. Der Server erstellt oder importiert keine Datenbank. Er öffnet SQLite im Modus `mode=ro` und bietet keine schreibenden Tools an. Auch relative SQLite-Dateipfade sind möglich. Beim CLI-Start wird `.env` geladen; bereits gesetzte Umgebungsvariablen haben Vorrang.

| Variable | Bedeutung | Standard |
| --- | --- | --- |
| `MCP_DATA_GW_DATABASE_URL` | Erforderliche SQLite-Datei-URL; keine Queryparameter oder In-Memory-Datenbank | keiner |
| `MCP_DATA_GW_HOST` | Bind-Adresse: `127.0.0.1`, `localhost`, `::1` oder `0.0.0.0` (alle IPv4-Schnittstellen; für Compose verwendet) | `127.0.0.1` |
| `MCP_DATA_GW_PORT` | TCP-Port (1–65535) | `8000` |

In `pyproject.toml` unterbindet `no-build = true` den Quellbau von Abhängigkeiten. Die Ausnahme `no-binary-package = ["mcp-data-gw"]` erlaubt den Bau des eigenen Projekts. Wird später eine Abhängigkeit ohne passendes Wheel benötigt, müssen diese Einstellungen erneut bewertet werden.

## MCP-Tools

| Tool | Funktion |
| --- | --- |
| `list_tables` | Freigegebene Tabellen alphabetisch auflisten |
| `describe_table` | Spalten, tatsächliche Constraints, separat ausgewiesene logische Beziehungen und aktuelle Lookup-Werte beschreiben |
| `select_rows` | Datensätze mit Spaltenauswahl, Filtern und Sortierung lesen |
| `aggregate_rows` | `count`, `sum`, `avg`, `min`, `max` mit optionaler Gruppierung berechnen |

Abfragen sind auf 1–200 Ergebniszeilen begrenzt (Standard: 50). Bei Aggregationen werden ohne expliziten Alias Namen wie `count_all` oder `avg_survived` erzeugt. Die Eingabeschemas beschreiben auch rekursive AND-/OR-Filter; erlaubt sind maximal fünf Gruppenebenen, 30 Bedingungen und 100 Werte je `in`-Liste. `contains` interpretiert `%`, `_` und Escape-Zeichen als Literale.

Tabellen und Spalten werden über Metadaten validiert und nur aus der Allowlist zugelassen. SQLAlchemy Core baut die Abfragen; künstliche Primär- oder Fremdschlüssel werden nicht vorausgesetzt. Bei `describe_table` werden Lookup-Werte frisch aus der Datenbank gelesen; über 200 Einträge führen zu einem Fehler. Die vollständigen Tool-Verträge sind in [Phase 3](docs/structure/phase-3.md) beschrieben.

## Architektur und technische Entscheidungen

| Modul | Verantwortung |
| --- | --- |
| `cli.py`, `__init__.py` | CLI-Einstieg und Export des Konsolenbefehls |
| `server.py` | MCP-Integration und Fehlerübersetzung |
| `service.py` | Anwendungslogik |
| `queries.py` | Abfragekonstruktion und Validierung |
| `metadata.py` | Tabellen-Allowlist und fachliche Semantik |
| `database.py` | Schema-Reflection und Datenbankzugriffe |

Die Trennung ermöglicht eine isolierte Testbarkeit der einzelnen Komponenten. Datenbankverbindungen werden freigegeben. SQLite verwendet fünf Sekunden Wartezeit bei Sperren; zusätzlich gilt ein kooperatives Ausführungslimit von fünf Sekunden pro DB-Zugriffsblock. Automatische Retries sind nicht implementiert.

### Stateful MCP-Clients, Sessions und Skalierbarkeit

Frühere MCP-Protokollversionen verwendeten sitzungsorientierte Kommunikation. Dazu gehörten unter anderem die Aushandlung von Protokollversion und Fähigkeiten, serverinitiierte Anfragen und Benachrichtigungen sowie die Wiederaufnahme unterbrochener Streams. Stateful Server mussten dazu Sitzungsinformationen vorhalten. Mit der [MCP-Spezifikation vom Juli 2026](https://blog.modelcontextprotocol.io/posts/2026-07-28/) wurde ein zustandsloser Protokollkern eingeführt.

Für dieses Projekt genügt der **stateless JSON-Request/Response-Betrieb**: Alle vier Tools lesen Daten und liefern innerhalb desselben Aufrufs ein Ergebnis. Es gibt keine Sitzungsdaten, abonnierbaren Ressourcen, serverinitiierten Nachrichten oder langlaufenden interaktiven Abläufe, die einen dauerhaften Clientkontext benötigen. Eine Kompatibilität mit dem älteren HTTP+SSE-Transport ist nicht Teil des aktuellen Umfangs.

| Aspekt | Stateful Serverbetrieb | Aktueller stateless Ansatz |
| --- | --- | --- |
| **Horizontale Skalierung** | Sitzungsbindung (*sticky sessions*) oder geteilter Session-Store kann erforderlich sein; Reconnects und Instanzausfälle müssen berücksichtigt werden. | Unabhängige Requests lassen sich prinzipiell auf mehrere Instanzen verteilen; keine MCP-Session-Affinität nötig. |
| **Vertikale Skalierung** | Speicherbedarf und Verbindungen wachsen zusätzlich mit aktiven Sessions und Streams. | Ressourcenbedarf entsteht primär pro laufendem Request und DB-Zugriff; mehr CPU/RAM können Parallelität verbessern. |
| **Grenzen in diesem Projekt** | Hier nicht implementiert bzw. benötigt. | SQLite-Dateizugriff, I/O, Prozess-/Worker-Modell, Verbindungspools und Abfragekosten begrenzen den realen Durchsatz weiterhin. |

Die Architektur erleichtert eine spätere horizontale Skalierung des MCP-Layers.

## Anmerkungen

Im weiteren Projektverlauf sollten folgende Punkte beachtet werden:

1. **Authentifizierung und Autorisierung:** Vor einem externen Betrieb ist das Sicherheitsmodell festzulegen. Insbesondere muss geklärt werden, welche Aufgaben ein Reverse Proxy bzw. API-Gateway übernimmt und welche Authentifizierungs- und Autorisierungsfunktionen durch das MCP-Framework bereitgestellt werden. Das eingesetzte SDK bietet entsprechende Möglichkeiten, die evaluiert werden sollten.
2. **Diagnosecode:** `logging.py` enthält Debug-Hilfen, insbesondere den Decorator `@keep_mcp_response`, der MCP-Antworten zu Debugging- und Präsentationszwecken speichert. Vor einem Produktivbetrieb sollten diese Hilfen entfernt werden.
3. **Testabdeckung:** Für einen Produktivbetrieb mit nicht öffentlichen Daten wären ergänzende SQL-Integrationstests mit einer isolierten Testdatenbank sowie gegebenenfalls End-to-End-Tests sinnvoll.

## Sprachkonventionen und KI-Unterstützung

Die allgemeine Projektdokumentation ist auf Deutsch, entsprechend der Aufgabenstellung. Code, Kommentare, Docstrings und Tests sind auf Englisch. `AGENTS.md`, `agents/AGENT_INSTRUCTIONS.md` und `AI_DISCLOSURE.md` sind als technische Agenten- und Offenlegungsdateien ebenfalls auf Englisch.

Der Code ist KI-generiert oder KI-unterstützt; das Datenbankgenerierungsskript ist vollständig KI-generiert. Die fachliche Logik wurde vom Projektinhaber entworfen, Code und Dokumentation wurden von ihm geprüft. Die Dokumentation ist überwiegend KI-generiert. Weitere Angaben stehen in [AI_DISCLOSURE.md](AI_DISCLOSURE.md).
