# Contributing Guidelines

## Development & Coding Standards

### Tools & Workflow

- **Linter:**  
  - Gebruik [`ruff`](https://github.com/astral-sh/ruff) als linter en formatter (geschreven in Rust, supersnel).
  - **Formatter:** `ruff format` is de standaard formatter. Laat je editor automatisch formatteren bij opslaan.
- **Type Checking:**  
  - Gebruik [`mypy`](https://mypy-lang.org/) voor type checking.
  - **Let op:** De mypy-daemon is traag; gebruik de CLI (`mypy .`) in CI/CD of handmatig.
- **Docstrings & Documentatie:**  
  - Gebruik Sphinx-style docstrings voor alle publieke functies, klassen en modules.
  - Genereer documentatie met Sphinx indien gewenst.
- **Package Management:**  
  - Gebruik [`uv`](https://github.com/astral-sh/uv) als package manager voor dependency management en virtuele omgevingen.
  - Alle tools en dependencies worden beheerd via `pyproject.toml`.
- **Testing:**  
  - Gebruik [`pytest`](https://docs.pytest.org/) voor alle unittests en integratietests.
  - Tests staan in de `tests/`-directory en dekken zowel de engine als de API.
- **CI/CD:**  
  - Linting, type checking en tests worden automatisch uitgevoerd in de CI/CD pipeline.
  - Gebruik `mypy` via de CLI in CI, niet als daemon.
- **Git:**
  - Run `scripts/precommit.sh` voor commit hooks (ruff + mypy).
  - Houd duidelijke commit messages aan, bij voorkeur in de vorm van `feat: [description]` of `fix: [description]`.

### Best Practices

- **Code moet altijd ruff-clean zijn** (geen linter errors/warnings).
- **Alle publieke functies en klassen hebben een duidelijke docstring.**
- **Type hints zijn verplicht** voor alle functie-argumenten en return types.
- **Elke nieuwe feature of bugfix krijgt een of meer pytest-tests.**
- **Voeg dependencies alleen toe via `pyproject.toml` en installeer met `uv`.**
- **Gebruik geen print-debugging in productiecode; gebruik logging indien nodig.**
- **Houd de codebase Python 3.12+ compatible.**

---

## Branching strategy

Gebruik consistente, betekenisvolle branchnamen. Richtlijnen:

- `feature/<onderwerp>` – nieuwe functionaliteit
- `fix/<issue-of-bug>` – bugfixes (niet-urgent)
- `hotfix/<korte-omschrijving>-YYYY-MM-DD` – urgente productiefix (infra/helm e.d.)
- `docs/<onderwerp>` – documentatie-updates
- `tests/<onderwerp>` – test(s) en testinfrastructuur
- `release/vX.Y.Z` – release-voorbereiding

PR-regels:

- PR’s naar `main` alleen vanuit `development` of `staging` (of een expliciete `hotfix/*` indien noodzakelijk).
- Vereist: groene CI (lint, typecheck, tests) vóór merge.
- Infra/Helm wijzigingen altijd via een aparte `hotfix/*` of `fix/*` branch met duidelijke titel en beschrijving.

---

**Voorbeeld workflow voor contributors:**

1. Fork & clone de repo.
2. Installeer dependencies met `uv venv && uv sync` of direct via `uv pip install [package]`
3. Codeer je feature/fix, commit met duidelijke boodschap.
4. Run lokaal:  
   - `ruff check .`  
   - `ruff format .`  
   - `mypy .`  
   - `pytest`
5. Voeg docstrings toe waar nodig, en hanteer de Google-stijl voor Docstrings.
6. Maak een pull request.
