# Repository Guidelines

## Project Structure & Module Organization

Rental Desk manages association instrument rentals with a static EN/DE frontend, a Python Cloudflare Worker API, tenant-scoped KV storage, and Clerk authentication.

- `worker/`: domain rules, API handling, storage, and migration logic.
- `frontdoor/`: JavaScript authentication gateway and Clerk role mapping.
- `public/`: HTML, CSS, and browser JavaScript; no frontend build step.
- `tests/`: Python and Node.js tests; import fixtures live in `tests/fixtures/`.
- `scripts/`: local server, smoke checks, preflight, and migration utilities.
- `docs/`: architecture and Clerk setup/deployment guides.

## Build, Test, and Development Commands

Use Python 3.12+, Node.js 22+, and uv.

- `npm ci` and `uv sync --locked`: install locked dependencies.
- `npm run dev:mock -- --port 8794`: start offline mock sign-in with local JSON data.
- `npm run dev:python`: start the direct local-admin debugging server.
- `npm run dev:clerk:backend` and `npm run dev:clerk:frontdoor`: run in separate terminals for real Clerk development; open `http://localhost:8795`.
- `npm run check:js`: check JavaScript syntax.
- `npm test`: run Node.js tests and Python unittest discovery.
- `npm run smoke:signed`: exercise signed-context HTTP behavior.
- `python3 scripts/deploy_preflight.py --allow-placeholders --include-frontdoor`: validate both Worker configurations offline.

## Coding Style & Naming Conventions

Follow surrounding code: four-space Python indentation, snake_case functions, PascalCase classes, and uppercase constants. JavaScript uses two-space indentation, ES modules, camelCase functions, and semicolons. Preserve snake_case API fields. Keep domain logic in `worker/domain.py` and update both English and German UI text. No dedicated formatter or lint command is configured; `check:js` checks syntax only.

## Testing Guidelines

Use Python `unittest` in `tests/test_*.py` and Node's built-in test runner in `tests/test_*.mjs`. Add regression coverage for changed behavior, especially permissions, tenant isolation, imports, and domain rules. No numeric coverage threshold is configured. Run socket-dependent tests with local sockets available. Mock tests do not validate live Clerk sign-in or invitation acceptance.

## Commit & Pull Request Guidelines

History uses short descriptive subjects with occasional prefixes such as `refactor:`; no uniform convention is evident. Write focused, action-oriented commits. PRs should explain behavior changes, list validation performed, link relevant issues, and include screenshots for UI changes. Document configuration or migration steps when applicable.

## Security & Configuration

Keep credentials and local rental data private. Check tracked secret files before committing; ignore rules do not protect already tracked files. Never reuse local signing values in production. Follow `docs/clerk-migration.md` for deployment and live authentication checks.
