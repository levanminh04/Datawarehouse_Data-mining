# Design — `hm_mining_app` B1 Refactor

**Date:** 2026-05-02
**Author:** [thành viên Nhóm 01 — KDL & KPDL, mã sinh viên B22DCCN]
**Scope:** Single member's deliverable — restructure the FastAPI continuous-learning app only.

## 1. Context

`hm_mining_app/` is the personal deliverable of one team member, satisfying the
two extension requirements set by the lecturer (Ch.5.3 of the group report):

1. **Continuous data collection** — `POST /ingest/*` endpoints
2. **Continuous learning** — APScheduler retrain + `model_registry` versioning

The app currently lives at `Datawarehouse_Data-mining/files/hm_mining_app/`,
nested one level too deep, alongside artifacts that belong to other team
members (Olist iterations, old web app, Jupyter notebooks). The wrapping
`files/` directory adds no semantic value and contains a duplicate README
(`files/README.md` is byte-identical to `files/hm_mining_app/README.md`,
verified 2026-05-02 with `diff -q`).

The owner (single member) is in charge of this app only — does **not** load
H&M data into Postgres (that work is done by another team member, who imported
`customers`, `articles`, `transactions` from the H&M CSV files). The owner runs
the app via local Python, not Docker.

## 2. Goals

- Move the app to top-level: `Datawarehouse_Data-mining/hm_mining_app/`
- Remove artifacts unused by the owner's workflow: Docker config, demo seeder
- Rewrite `README.md` and `.env.example` to reflect the actual single-member,
  local-Python, existing-DB scope
- **Preserve all Python logic unchanged** — this is a B1-tier (minimal)
  cleanup; module structure, ML algorithms, API contracts, and SQL files are
  not modified

## 3. Non-Goals

- No edits to any module under `app/` (`api/`, `ml/`, `sql/`, `main.py`, etc.)
- No splitting of `app/sql/schema.sql` into app-owned vs DB-team-owned tables
  (deferred — was the B2 option; rejected to minimise risk)
- No changes to other team members' work: notebooks under `data-mining/`,
  `datamining-version2/`, `datamining-version3/`, `new-datamining/`,
  `datamining-hm/`, the legacy `web/` app, Olist datasets, `output/` SQL,
  root-level `survey_*.py` files, `etl_olist_to_sql.py`, `generate_notebook.py`
- No new features, no dependency upgrades, no CI/CD setup

## 4. Final Folder Layout

```text
Datawarehouse_Data-mining/
├── hm_mining_app/                ← MOVED from files/hm_mining_app/
│   ├── app/                      (unchanged)
│   │   ├── main.py, config.py, db.py, schemas.py, scheduler.py, __init__.py
│   │   ├── api/                  (ingest.py, predict.py, retrain.py, metrics.py, __init__.py)
│   │   ├── ml/                   (features.py, layer1_kmeans.py, layer2_apriori.py,
│   │   │                          layer3_rf.py, registry.py, __init__.py)
│   │   └── sql/                  (schema.sql, feature_queries.sql)
│   ├── frontend/index.html       (unchanged)
│   ├── scripts/init_db.py        (unchanged; seed_demo.py removed)
│   ├── models_store/             (runtime artefacts; .gitkeep added so empty dir survives)
│   ├── requirements.txt          (unchanged)
│   ├── .env.example              (rewritten — single DSN, no Docker vars)
│   ├── .gitignore                (extended to ignore models_store/* except .gitkeep)
│   └── README.md                 (rewritten — single-member, no Docker, no seed)
│
├── (other team members' directories — untouched)
│   data-mining/, datamining-hm/, datamining-version2/, datamining-version3/,
│   new-datamining/, web/, output/, data/,
│   etl_olist_to_sql.py, generate_notebook.py, survey_*.py
│
└── files/                        ← DELETED (was an empty wrapper after move)
```

## 5. Action List (9 atomic ops)

**Pre-condition:** As of 2026-05-02, the entire `files/` subtree is **untracked**
in git (verified with `git status --short`). The latest commit (`35824d85
H&M dataset`) does not contain the app. Therefore the refactor commit is the
**first** commit that introduces this app to the repo. All file ops below use
plain `mv` / `rm` rather than `git mv` / `git rm` because there is no tracked
history to preserve. The final `git add hm_mining_app/` stages everything in
the new location.

| # | Op | Path | Notes |
|---|----|------|-------|
| 1 | `mv` | `files/hm_mining_app/` → `hm_mining_app/` | source untracked; plain `mv` |
| 2 | `rm` | `files/README.md` | byte-identical duplicate of `hm_mining_app/README.md` (verified) |
| 3 | `rm` | `files/.DS_Store` | macOS noise |
| 4 | `rmdir` | `files/` | now empty |
| 5 | `rm` | `hm_mining_app/Dockerfile` | owner runs local Python only |
| 6 | `rm` | `hm_mining_app/docker-compose.yml` | owner runs local Python only |
| 7 | `rm` | `hm_mining_app/scripts/seed_demo.py` | DB H&M is loaded by another member |
| 8 | rewrite | `hm_mining_app/README.md` | scope to single-member workflow |
| 9 | edit | `hm_mining_app/.gitignore` (replace `models_store/` with `models_store/*` + `!models_store/.gitkeep`) and create `hm_mining_app/models_store/.gitkeep` | preserve empty runtime dir under version control |
| — | `git add hm_mining_app/` | (final staging step — not numbered as a refactor op) | brings the new layout under version control |

These ops are independent and applied in a single commit.

## 6. README Rewrite Outline

The new README is structured for the single-member, local-Python scope:

1. **Title & owner line** — "phần code thành viên ___ (B22DCCN), Nhóm 01"
2. **Phạm vi của module này** — explicit list of what is and isn't included
   (notebooks, ETL belong to other members)
3. **Tiền đề** — H&M tables (`customers`, `articles`, `transactions`) are
   pre-loaded by the DB team member; expected schema bullet list
4. **Cài đặt local** — venv + pip + `cp .env.example .env` + `init_db` +
   `uvicorn` + first-time `retrain/all`. No Docker, no seed.
5. **API table** — kept verbatim from current README (single source of truth
   for the endpoints)
6. **Đáp ứng yêu cầu thầy** — the two-pillar argument (collection + learning)
   tied to Ch.5.3 of the report. Same content, no trim.
7. **Test nhanh** — curl examples, kept verbatim.

**Removed from current README:**

- `Chạy nhanh (Docker)` section
- `Nạp dữ liệu H&M thật` section (H&M is already loaded; this advice is for
  the DB team member, not this app's owner)
- `Phân công đề xuất` table (single member; no team partition needed here)
- `Cấu trúc thư mục` ASCII tree (now lives in this design doc)

## 7. `.env.example` — No Change

The current `.env.example` (verified 2026-05-02 by reading both
`hm_mining_app/.env.example` and `app/config.py`) contains exactly the 11
variables that `pydantic_settings` consumes in `app/config.py`:

- `DATABASE_URL`
- `MODEL_STORE`
- `KMEANS_N_CLUSTERS`, `KMEANS_SAMPLE_SIZE`
- `APRIORI_MIN_SUPPORT`, `APRIORI_MIN_CONFIDENCE`
- `RF_PREDICTION_WINDOW_DAYS`, `RF_SAMPLE_SIZE`
- `RETRAIN_L1_CRON`, `RETRAIN_L2_CRON`, `RETRAIN_L3_CRON`
- `ENABLE_SCHEDULER`

There are **no** `POSTGRES_USER` / `POSTGRES_PASSWORD` / Docker-specific
variables in this file (those would have lived in `docker-compose.yml`
environment section, which is being removed in op 6). The file is correct
as-is and stays untouched. Earlier drafts of this spec (commit a9121d57)
incorrectly proposed reducing to 3 variables; that proposal is rescinded
because it would lose legitimate ML hyperparameter knobs.

## 8. Verification Plan

After applying the 9 ops, run from the repo root:

| # | Check | Pass criterion |
|---|-------|----------------|
| V1 | `find hm_mining_app -name "*.py" \| xargs python -m py_compile` | exit 0, all files compile |
| V2 | `grep -rn "seed_demo\|docker\|Dockerfile\|docker-compose" hm_mining_app/` | no matches |
| V3 | `git status --short` (post-mv, pre-add) | only `hm_mining_app/` appears as untracked; `files/` no longer present; no other surprise diffs |
| V4 | `[ ! -d files ]` | `files/` directory is gone |
| V5 | `[ ! -f hm_mining_app/scripts/seed_demo.py ] && [ ! -f hm_mining_app/Dockerfile ] && [ ! -f hm_mining_app/docker-compose.yml ]` | all three absent |
| V6 | `cat hm_mining_app/.env.example` | only the 3 variables in section 7 |
| V7 | manual: open new README, confirm sections from section 6 are present and removed sections are gone | reviewer agreement |

**Out of scope for verification:** running `uvicorn` against the real DB.
That requires the owner's `.env` and live Postgres credentials, which the
refactor doesn't touch.

## 9. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Hidden import path `from files.hm_mining_app...` somewhere in the repo | very low | verified 2026-05-02 with `grep -rn "^import\|^from" hm_mining_app/{app,scripts}` filtered for `files\.` / `hm_mining_app\.` — no matches |
| Another team member is editing `files/hm_mining_app/` on a separate clone right now | low | the directory is untracked, so no remote can have authoritative changes; coordinate over group chat before running the refactor |
| README rewrite drops content the lecturer expects | low | new README keeps every section that ties to the report (Ch.5.3 mapping, API list, continuous-learning argument); only Docker/seed/team-partition sections are removed, none of which the report mentions |
| Refactor commit is large (introduces all app code at once because the app was previously untracked) | accepted | inherent to clean-slate state; the commit message will describe both the introduction and the refactor in one |

## 10. Out-of-Scope (explicitly deferred)

- **B2 schema split** (separating app-owned tables from H&M tables in
  `app/sql/schema.sql`) — rejected this round to minimise risk; can be
  revisited if the lecturer asks "ai sở hữu bảng nào?" during the demo
- **Tests** — the app has no test suite today; adding one is its own project
- **Drift detection / scheduled accuracy reconciliation** — listed as future
  work in the current README; remains future work
- **Frontend upgrade** — `frontend/index.html` (Alpine.js + Chart.js) is
  intentionally minimal; production-grade UI is out of scope for a course
  deliverable

## 11. Done When

- All 9 ops are applied in a single commit on the repo's working branch
- All 7 verification checks pass
- The owner has read the new README end-to-end and confirmed it represents
  their work accurately
