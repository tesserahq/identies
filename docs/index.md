# What is Identies

Identies is the identity service of the platform. It owns **who and what can act** — people,
service accounts and AI agents — and the **credentials** they use to prove it. Other services
(Linden, Custos, Conversa, Sendly, ...) keep a local copy of the users they need and stay in
sync through events.

Identies deliberately does **not** decide what a principal is allowed to do (that is Custos) or
how principals relate to each other inside a product (for example, which human is responsible
for an agent — that is the product's data). See [Concepts](concepts.md).

## Core responsibilities

- **Principals**: humans, service accounts and agents, told apart by [`kind`](concepts.md#principal-kinds).
- **Credentials**: OIDC logins, OAuth client credentials that mint short-lived JWTs, API keys, one-time claim codes, and delegated tokens ([Credentials](credentials.md), [Token Exchange](token_exchange.md)).
- **Agents**: an invite-and-claim flow that gives an AI agent its own identity and credentials ([Agents](agents.md)).
- **Access control at the door**: invite-only access rules, and per-route permissions enforced through Custos ([Authentication](authentication.md)).
- **Identity events**: every change to a user is published so other services can keep a projection ([Events](events.md)).
- **External accounts**: linking a person to accounts on outside platforms with one-time link tokens.

## Where to start

| I want to... | Read |
|---|---|
| Run it locally | [Quick Setup](quick_setup.md), then [Development](development.md) |
| Understand the model | [Concepts](concepts.md) |
| Know how a request is authenticated and who may call what | [Authentication](authentication.md), [API Reference](api_reference.md) |
| Give a service or an agent credentials | [Credentials](credentials.md), [Agents](agents.md) |
| Consume user changes from another service | [User Events](user_events.md), [Events](events.md) |
| Understand deletion and data retention | [Data Lifecycle](data_lifecycle.md) |
| Configure or deploy it | [Configuration](configuration.md), [Operations](operations.md) |
| Know why it works this way | [Design Decisions](decisions.md), [Architecture](architecture.md) |

## Documentation conventions

Some pages are checked by tests so they cannot silently go stale: the route table in the
[API Reference](api_reference.md) is generated from the code, and every setting and event must
appear in [Configuration](configuration.md) and [Events](events.md). See
[Development](development.md#keeping-the-docs-honest).
