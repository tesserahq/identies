"""The documentation is checked against the code so it cannot silently go stale.

If one of these fails, the message says what to fix. See docs/development.md.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

# Settings that are defined by the shared SDK (or read directly from the environment)
# rather than by Identies' Settings class, but are documented because they change behaviour.
EXTERNAL_ENV_VARS = {
    "TEST_DATABASE_URL",
    "CUSTOS_API_URL",
    "AUTHORIZATION_CACHE_ENABLED",
    "AUTHORIZATION_CACHE_TTL",
    "NATS_ENABLED",
    "NATS_URL",
    "EVENT_TYPE_PREFIX",
}


def doc_pages() -> list[Path]:
    return sorted(DOCS.glob("*.md"))


# ---------------------------------------------------------------- API reference


def test_api_reference_route_table_matches_the_code():
    """Run in a clean interpreter: the test suite mocks the SDK's `authorize`, which would
    hide each route's Custos permission."""
    result = subprocess.run(
        [sys.executable, "-m", "tests.docs.route_inventory", "--check"],
        cwd=ROOT,
        env={**os.environ, "ENV": "test", "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        "docs/api_reference.md is out of date. Regenerate it with:\n"
        "  poetry run python -m tests.docs.route_inventory --write\n\n"
        + result.stderr[-2000:]
    )


# ---------------------------------------------------------------- configuration


def _settings_env_names() -> dict[str, list[str]]:
    from app.config import Settings

    names: dict[str, list[str]] = {}
    for field_name, field in Settings.model_fields.items():
        alias = field.validation_alias
        extra = field.json_schema_extra
        if alias is not None and hasattr(alias, "choices"):
            env = [str(c).upper() for c in alias.choices]
        elif isinstance(extra, dict) and "env" in extra:
            env = [str(extra["env"])]
        else:
            env = [field_name.upper()]
        names[field_name] = env
    return names


def _configuration_rows() -> list[tuple[list[str], str]]:
    """(variables in the first cell, second cell) for every table row that starts with a
    backticked ALL_CAPS name."""
    rows = []
    for line in (DOCS / "configuration.md").read_text().splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        first = re.findall(r"`([A-Z][A-Z0-9_]+)`", cells[0])
        if first:
            rows.append((first, cells[1] if len(cells) > 1 else ""))
    return rows


def test_every_setting_is_documented():
    text = (DOCS / "configuration.md").read_text()
    missing = [
        env
        for names in _settings_env_names().values()
        for env in names
        if f"`{env}`" not in text
    ]
    assert (
        not missing
    ), f"Add these settings to docs/configuration.md: {sorted(set(missing))}"


def test_configuration_lists_no_setting_that_does_not_exist():
    known = {e for names in _settings_env_names().values() for e in names}
    known |= EXTERNAL_ENV_VARS
    documented = {v for names, _ in _configuration_rows() for v in names}
    unknown = sorted(documented - known)
    assert not unknown, (
        f"docs/configuration.md lists variables that are not settings: {unknown}. "
        "Remove them, or add them to EXTERNAL_ENV_VARS if the shared SDK defines them."
    )


def test_documented_defaults_match_the_code():
    from app.config import Settings

    by_env = {
        env: field
        for name, field in Settings.model_fields.items()
        for env in _settings_env_names()[name]
    }
    wrong = []
    for names, default_cell in _configuration_rows():
        match = re.fullmatch(r"`([^`]+)`", default_cell)
        if not match:
            continue  # "none", "empty", "derived ..." and so on are not checked
        for env in names:
            field = by_env.get(env)
            if field is None or field.default in (None, ""):
                continue
            if str(field.default).lower() != match.group(1).lower():
                wrong.append((env, match.group(1), field.default))
    assert not wrong, f"Documented defaults differ from the code: {wrong}"


# ---------------------------------------------------------------- events


def _event_names() -> set[str]:
    import app.events as events_pkg

    names = set()
    for module in pkgutil.iter_modules(events_pkg.__path__):
        mod = importlib.import_module(f"app.events.{module.name}")
        for attr, value in vars(mod).items():
            if (
                attr.isupper()
                and isinstance(value, str)
                and re.fullmatch(r"[a-z_]+\.[a-z_]+", value)
            ):
                names.add(value)
    return names


def test_every_event_is_documented():
    text = (DOCS / "events.md").read_text()
    names = _event_names()
    assert names, "no event constants found; the discovery in this test is broken"
    missing = sorted(n for n in names if f"`{n}`" not in text)
    assert not missing, f"Add these events to docs/events.md: {missing}"


# ---------------------------------------------------------------- pages and links


def _nav_pages() -> set[str]:
    return set(
        re.findall(r":\s*([\w./-]+\.md)\s*$", (DOCS / "mkdocs.yml").read_text(), re.M)
    )


def test_navigation_matches_the_pages():
    nav = _nav_pages()
    pages = {p.name for p in doc_pages()}
    assert (
        nav - pages == set()
    ), f"mkdocs.yml links to pages that do not exist: {nav - pages}"
    assert (
        pages - nav == set()
    ), f"Pages missing from the mkdocs.yml navigation: {pages - nav}"


def _slug(text: str) -> str:
    """Python-Markdown's default heading slug (what MkDocs uses for anchors)."""
    text = re.sub(r"`", "", text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def _anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    in_fence = False
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if not match:
            continue
        slug = _slug(match.group(2))
        if slug in seen:
            seen[slug] += 1
            slug = f"{slug}_{seen[slug]}"
        else:
            seen[slug] = 0
        anchors.add(slug)
    return anchors


def _links(path: Path) -> list[str]:
    in_fence = False
    links = []
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = re.sub(r"`[^`]*`", "", line)
        links += re.findall(r"\]\(([^)\s]+)\)", line)
    return links


@pytest.mark.parametrize("page", doc_pages(), ids=lambda p: p.name)
def test_relative_links_and_anchors_resolve(page):
    broken = []
    for target in _links(page):
        if re.match(r"[a-z]+:", target):  # http:, https:, mailto:
            continue
        file_part, _, anchor = target.partition("#")
        dest = page if not file_part else (page.parent / file_part).resolve()
        if not dest.exists():
            broken.append(f"{target} (no such file)")
        elif anchor and dest.suffix == ".md" and anchor not in _anchors(dest):
            broken.append(f"{target} (no such heading in {dest.name})")
    assert not broken, f"Broken links in docs/{page.name}: {broken}"


# ---------------------------------------------------------------- hygiene


REAL_LOOKING_SECRETS = [
    (r"\bak_[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{16,}", "an API key"),
    (r"\bcs_[A-Za-z0-9_-]{8,}\b", "a client id"),
    (r"\bac_[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{16,}", "a claim code"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----\s*[A-Za-z0-9+/=]{20,}", "a private key"),
]


@pytest.mark.parametrize("page", doc_pages(), ids=lambda p: p.name)
def test_docs_contain_no_real_looking_credentials(page):
    text = page.read_text()
    found = [
        label for pattern, label in REAL_LOOKING_SECRETS if re.search(pattern, text)
    ]
    assert not found, (
        f"docs/{page.name} contains what looks like {found}. Use a placeholder such as "
        "`ak_...` or `cs_...`, and never paste a real credential into documentation."
    )
