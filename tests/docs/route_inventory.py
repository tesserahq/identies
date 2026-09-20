"""Builds the route inventory that docs/api_reference.md documents.

Run in a clean interpreter (the test suite replaces the SDK's ``authorize`` with a mock,
which hides the resource/action pair):

    poetry run python -m tests.docs.route_inventory            # print the table
    poetry run python -m tests.docs.route_inventory --write    # update docs/api_reference.md
    poetry run python -m tests.docs.route_inventory --check    # exit 1 if the doc is stale
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "api_reference.md"
BEGIN = "<!-- BEGIN GENERATED ROUTES (tests/docs/route_inventory.py) -->"
END = "<!-- END GENERATED ROUTES -->"


@dataclass(frozen=True)
class RouteRow:
    method: str
    path: str
    operation_id: str
    access: str
    rbac: str


def _rbac_of(dependant) -> str:
    """The Custos (resource, action) a route requires, read from its dependencies."""
    found: list[str] = []

    def walk(dep):
        for sub in dep.dependencies:
            call = sub.call
            if getattr(call, "__name__", "") == "authorization_dependency":
                cells = dict(
                    zip(
                        call.__code__.co_freevars,
                        (c.cell_contents for c in (call.__closure__ or ())),
                    )
                )
                found.append(f"`{cells['resource']}` : `{cells['action']}`")
            walk(sub)

    walk(dependant)
    return ", ".join(dict.fromkeys(found)) or "-"


def _iter_routes(app):
    """Yield (path, methods, route) for every API route, including included routers.

    FastAPI 0.14x wraps included routers; ``iter_route_contexts`` is the function its own
    OpenAPI generator uses. Older versions expose plain routes on ``app.routes``.
    """
    from fastapi import routing
    from fastapi.routing import APIRoute

    if hasattr(routing, "iter_route_contexts"):
        for ctx in routing.iter_route_contexts(app.routes):
            if isinstance(ctx.route, APIRoute):
                yield ctx.path, ctx.methods, ctx.route
    else:  # pragma: no cover - older FastAPI
        for route in app.routes:
            if isinstance(route, APIRoute):
                yield route.path, route.methods, route


def collect_rows() -> list[RouteRow]:
    from app.main import create_app
    from app.middleware.authentication_middleware import (
        M2M_AUTH_PATHS,
        SKIP_AUTH_PATHS,
    )

    app = create_app(testing=True)
    rows: list[RouteRow] = []
    for path, methods, route in _iter_routes(app):
        if not route.include_in_schema:
            continue
        if path in SKIP_AUTH_PATHS:
            access = "Public"
        elif any(path.startswith(p) for p in M2M_AUTH_PATHS):
            access = "Service only"
        else:
            access = "Authenticated"
        for method in sorted(set(methods) - {"HEAD", "OPTIONS"}):
            rows.append(
                RouteRow(
                    method=method,
                    path=path,
                    operation_id=route.operation_id or route.name,
                    access=access,
                    rbac=_rbac_of(route.dependant),
                )
            )
    return sorted(rows, key=lambda r: (r.path, r.method))


def render_table(rows: list[RouteRow]) -> str:
    lines = [
        "| Method | Path | Access | Custos permission | Operation |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.method} | `{r.path}` | {r.access} | {r.rbac} | `{r.operation_id}` |"
        )
    return "\n".join(lines)


def generated_block() -> str:
    return f"{BEGIN}\n\n{render_table(collect_rows())}\n\n{END}"


def current_block(text: str) -> str | None:
    if BEGIN not in text or END not in text:
        return None
    start = text.index(BEGIN)
    return text[start : text.index(END) + len(END)]


if __name__ == "__main__":
    block = generated_block()
    if "--write" in sys.argv:
        text = DOC.read_text()
        old = current_block(text)
        if old is None:
            sys.exit(f"{DOC} has no generated block markers")
        DOC.write_text(text.replace(old, block))
        print(f"updated {DOC}")
    elif "--check" in sys.argv:
        old = current_block(DOC.read_text())
        if old != block:
            sys.exit(
                "docs/api_reference.md is out of date. Run: "
                "poetry run python -m tests.docs.route_inventory --write"
            )
        print("api_reference.md is up to date")
    else:
        print(block)
