# Rass Derb Cup Discord Bot

Modular Discord bot foundation for Rass Derb Cup and Esports PUBG MOBILE MEA, starting with a JSON-driven `/embed` command.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `python -m rass_derb_bot` — run the Discord bot (requires the `TOKEN` Replit Secret)
- `python -m unittest discover -s tests -v` — run bot payload parser tests
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required bot secret: `TOKEN` — Discord bot token stored in Replit Secrets
- Required bot secret: `DATABASE_URL` — shared PostgreSQL connection
- Optional bot env: `GUILD_ID` — sync slash commands to one server for immediate development updates
- Temporary bot env: `LEGACY_GUILD_ID` — remove a stale server-only `/embed` command once
- Existing API server env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Bot: Python 3.11, `discord.py`
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `rass_derb_bot/` — Discord client, command cogs, form UI, and reusable services
- `tests/` — Python unit tests
- `artifacts/api-server/` — shared API service
- `lib/api-spec/openapi.yaml` — API contract source of truth
- `lib/db/src/schema/discord-forms.ts` — PostgreSQL schema for sections, questions, and persistent buttons

## Architecture decisions

- Discord bot credentials are loaded only from environment variables; never commit a token.
- Slash commands sync globally unless `GUILD_ID` is set for rapid single-server development.
- Form sections, questions, and persistent button metadata live in PostgreSQL; answer content is delivered to staff but not stored.
- Feature commands are isolated as `discord.py` extensions; payload conversion and validation live in services.
- Bot content mentions are disabled by default to prevent accidental pings.

## Product

- Admins can post validated Discord messages and custom embeds through `/embed`.
- Admins can create and edit form sections/questions, set up a private staff channel, and attach persistent form buttons to embeds.
- Members can submit answers privately through a modal; staff receive an embed with the member's avatar, ID, and answers.
- Mentioning the bot returns its current gateway latency.

## User preferences

- Build the Rass Derb Cup Discord bot one modular step at a time.

## Gotchas

- The bot requests Discord's privileged Message Content Intent; enable it in the Discord Developer Portal.
- Discord global slash-command changes can take time to appear. Set `GUILD_ID` while developing in one server.
- Discord modals support at most five questions per form section.
- Discord buttons only support preset styles; custom hex color applies to the submission embed.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
