# Phase 2 – Projektsetup

**Projekt:** `mcp-data-gw`
**Stand:** 31. Oktober 2026
**Status:** Setup und Prüfungen abgeschlossen.

## 1. Ziel und Abgrenzung

Phase 2 dokumentiert die Projektstruktur und das verwendete Tooling. Verzeichnisse werden nur angelegt, wenn sie bereits eine konkrete Datei enthalten; reine Platzhalter wie `.gitkeep` werden nicht verwendet.

## 2. Projektstruktur

```text
mcp-data-gw/
├── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile
├── src/
│   └── mcp_data_gw/
│       └── __init__.py
├── tests/
│   └── __init__.py
├── docs/
│   ├── structure/
│   └── requirements/
├── agents/
│   └── AGENT_INSTRUCTIONS.md
├── AGENTS.md
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

Die Struktur zeigt die wesentlichen Projektbereiche. Anwendungsmodule sind im [README](../../README.md#architektur-und-technische-entscheidungen) aufgeführt; Testmodule liegen direkt unter `tests/`.

### Verantwortlichkeiten

| Pfad | Aufgabe |
| --- | --- |
| `src/mcp_data_gw/` | Python-Anwendungspaket |
| `tests/` | Automatisierte Tests |
| `docs/` | Anforderungen, technische Dokumentation, Architekturentscheidungen |
| `agents/` | Ergänzende Arbeitskonventionen und Kontext für Coding-Agenten |
| `AGENTS.md` | Kompakter, agentenübergreifender Einstiegspunkt mit Verweisen |
| `README.md` | Überblick, Setup, Ausführung und Entwicklerhinweise |
| `.devcontainer/` | Reproduzierbare lokale Entwicklungsumgebung |

**Single Source of Truth:** Anforderungen und Architekturentscheidungen werden in `docs/` gepflegt. Agentenhinweise verweisen darauf, statt Inhalte zu duplizieren. `AGENTS.md` ist die gemeinsame Basiskonvention.

## 3. Sprache und Konventionen

- Projektdokumentation und Kommunikation: **Deutsch**.
- Quellcode, Bezeichner, Code-Kommentare und Testnamen: **Englisch**.
- Öffentliche Funktionen und Methoden erhalten Type Hints einschließlich Rückgabetypen.
- `Any` wird nur begründet eingesetzt.
- Kein verpflichtendes mypy oder Pyright in Phase 2.

## 4. Git und ignorierte Dateien

Das Git-Repository verwendet `main` als Hauptbranch. Die `.gitignore` schließt insbesondere Python-Caches, virtuelle Umgebungen, Build- und Coverage-Artefakte, lokale `.env`-Dateien, IDE-Einstellungen und Logdateien aus. Eine `.env.example` darf versioniert werden, jedoch ohne Secrets. Auch lokale Compose-Overrides werden ignoriert.

`uv.lock` gehört ausdrücklich ins Repository, damit Abhängigkeiten reproduzierbar aufgelöst werden.

## 5. Python-Paket und Abhängigkeiten

| Entscheidung | Festlegung |
| --- | --- |
| Projektname | `mcp-data-gw` |
| Import-Paket | `mcp_data_gw` |
| Python | Mindestens 3.13; dokumentierte Prüfläufe auf Python 3.14.7 |
| Layout | `src`-Layout |
| Build-Backend | `uv_build` |
| Dependency-Manager | `uv` |
| MCP-SDK | `mcp[cli]` |
| Datenbankzugriff | SQLAlchemy 2.x |
| Datenmodelle/Validierung | Pydantic 2.x |
| Lokale Konfiguration | `python-dotenv` |

Die konkrete `pyproject.toml` bleibt maßgeblich für Versionsuntergrenzen, Dependency-Gruppen und weitere uv-Einstellungen.

### Supply-Chain-Sicherheit

- `exclude-newer = "7 days"`: Neue Releases werden bei der Auflösung zunächst zurückgestellt.
- `no-build = true`: Source-Builds von Abhängigkeiten werden unterbunden.
- `preview-features = ["malware-check"]` und `[tool.uv.audit] malware-check = true`: Malware-Checks nach uv-Unterstützung aktivieren.
- `no-binary-package = ["mcp-data-gw"]` erlaubt den Build des eigenen Projekts.
- `uv lock` erzeugt bzw. aktualisiert die Lockdatei, ohne die Projektabhängigkeiten zu installieren.
- `uv audit --locked` prüft die gelockten Abhängigkeiten einschließlich Entwicklungsabhängigkeiten; Netzwerkzugriff ist hierfür erforderlich.
- `uv tree --locked` dient bei Bedarf zur Einsicht in den Dependency-Baum.

`uv sync --locked` und `uv run --locked ...` installieren bei Bedarf die bestehenden gelockten Abhängigkeiten. Änderungen an Abhängigkeiten und Lockdatei benötigen ausdrückliche Freigabe.

## 6. Dev Container

Für die lokale Entwicklung ist ein Dev Container mit Python 3.14 und uv konfiguriert:

- Basis: `mcr.microsoft.com/devcontainers/python:3-3.14-trixie`.
- uv-Binärdateien aus dem offiziellen Astral-uv-Image.
- VS-Code-Erweiterungen: Python und Pylance.
- `remoteUser`: `vscode`.
- Kein `postCreateCommand` zum Installieren der Projektabhängigkeiten.
- Keine PostgreSQL-Instanz im Dev Container.

Das uv-Image ist auf `0.13.6` festgelegt. Der Dev Container ist die **Entwicklungsumgebung** und unabhängig von der lokalen Docker-Compose-Laufzeitkonfiguration des MCP-Servers.

## 7. Codequalität: Ruff

Ruff wird zugleich für Linting, Import-Sortierung und Formatting eingesetzt.

```toml
[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "B", "UP", "SIM", "RUF"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

Lint- und Formatprüfung erfolgen mit den unten aufgeführten Ruff-Kommandos.

## 8. Tests: pytest

pytest 9 wird mit nativer TOML-Konfiguration verwendet:

```toml
[tool.pytest]
minversion = "9.0"
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--import-mode=importlib",
]
xfail_strict = true

markers = [
    "unit: Unit tests without external dependencies",
    "integration: Integration tests involving external components",
]
```

Die Testmodule liegen direkt unter `tests/`. Unit-Tests prüfen isolierte Logik; Integrationstests prüfen das Zusammenwirken der MCP-Schichten in Memory mit Mocks an der Datenbankgrenze. Die echte SQLite-Ausführung wurde separat im manuellen Smoke-Test geprüft.

### Prüfkommandos

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv run --locked pytest -m unit
uv run --locked pytest -m integration
```

Die gelockten Abhängigkeiten werden bei Bedarf synchronisiert.

## 9. Abschluss

**Phase 2 ist abgeschlossen.** Folgende Punkte sind geprüft:

- [x] `pyproject.toml` enthält die abgestimmten Abhängigkeiten und Ruff-/pytest-Konfiguration.
- [x] `uv lock` und `uv audit --locked` sind erfolgreich gelaufen; `uv.lock` ist versioniert.
- [x] Der Dev Container lässt sich starten; Python, uv und Git sind verfügbar.
- [x] `README.md`, `docs/`, `agents/AGENT_INSTRUCTIONS.md` und `AGENTS.md` enthalten ihre vorgesehenen Mindestinformationen, soweit sie bereits erstellt wurden.
- [x] Git-Status ist geprüft; notwendige Dateien sind versioniert.

Die **lesenden MCP-Tools** und ihre Unit- und Integrationstests sind in [Phase 3](phase-3.md) dokumentiert. Die bestehende Datenbankstruktur ohne deklarierte Primär- oder Fremdschlüssel wird dabei respektiert; künstliche Datenbankschlüssel werden nicht vorausgesetzt.
