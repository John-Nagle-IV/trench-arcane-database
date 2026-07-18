# Trench Arcane Database Assets

Versioned portable database assets for Trench Arcane: reference card corpus, database-operation schemas, migration-derived vocabulary snapshots, and validation tooling.

## Ownership and release boundary

| Asset | Owner | Rule |
| --- | --- | --- |
| Django models, migrations, `migrate`, and executable seed data | `trench-arcane-backend` | The only migration authority. Never copy a Django migration here. |
| OpenAPI and the executable `/api/v1/schemas/effect/` generator | `trench-arcane-backend` | The only API-schema authority. |
| Portable reference data and validation tooling | this repository | Versioned with a backend contract/migration compatibility gate. |

`fixtures/reference/migration-vocabularies.json` is a checked reference snapshot of `cards.0001_initial`; it is not a Django `loaddata` file. The original audited Django fixture used conflicting primary keys/names and could not be loaded after the migration's own idempotent seeding. Keeping it as an executable fixture would create a second seed authority. The compatibility script instead proves that a clean backend migration contains every referenced vocabulary value.

`schemas/card-effect.schema.json` is a canonicalized generated snapshot of the backend's dynamic effect schema. Its contract pin is in `contracts/backend-contract-pin.json`. It is not an OpenAPI replacement or authoring source. `fixtures/reference/legacy-card-effect.schema.json` is retained only as an audited legacy authoring corpus.

## Layout

- `fixtures/canonical/`: portable Alpha card/reference corpus.
- `fixtures/reference/`: non-executable reference inputs, including migration vocabulary data and legacy effect examples.
- `schemas/`: standalone JSON Schema assets. The effect snapshot maps to the approved `GET /api/v1/schemas/effect/` endpoint.
- `contracts/`: backend contract version/hash pin, not a copied OpenAPI document.
- `scripts/`: asset and clean-backend compatibility checks.

## Local validation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run python scripts/validate_assets.py
```

Expected output:

```text
validated 8 JSON assets; schemas, fixture identities, and canonical corpus are valid
```

## Clean backend consumption and compatibility

No files are copied into the backend checkout. Clone the repositories side-by-side, then pass the database checkout as a script path:

```bash
git clone git@github.com:John-Nagle-IV/trench-arcane-database.git
# Clone the backend release pinned for this database release.
git clone git@github.com:John-Nagle-IV/trench-arcane-backend.git

cd trench-arcane-backend
uv sync
uv run python ../trench-arcane-database/scripts/validate_backend_compatibility.py \
  --backend-root "$PWD"
```

The compatibility check creates a temporary SQLite database, applies the backend migrations from zero, verifies the migration-derived vocabulary snapshot, and compares the backend-generated dynamic effect schema with this repository's canonicalized snapshot. It does not write to either checkout or require PostgreSQL credentials.

For the audited monorepo layout, use the same command with its repository root as `--backend-root`; the tool locates either `manage.py` at the backend root or `services/backend/trench_backend/manage.py` during the transition.

## Updating a database release

1. Release/commit backend migrations and OpenAPI changes first.
2. Regenerate the migration vocabulary reference and dynamic effect-schema snapshot from that backend revision.
3. Update `contracts/backend-contract-pin.json` with the approved backend API version/hash.
4. Run both validation commands above against that exact backend revision.
5. Tag the database repository release with the compatible backend revision in the release notes.

Do not add `cards/migrations/**`, `manage.py`, a backend image, or an OpenAPI source document to this repository.
