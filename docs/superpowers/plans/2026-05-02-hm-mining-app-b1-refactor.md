# `hm_mining_app` B1 Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the FastAPI continuous-learning app from `files/hm_mining_app/` to top-level `hm_mining_app/`, drop Docker / seed scaffolding, scope the README to a single-member deliverable, and land it as the first git-tracked version of the app.

**Architecture:** Pure file-system refactor — no Python module under `app/` is modified. Everything ships in **one commit** because (a) the source tree is currently untracked and there is no history to bisect, and (b) the spec (committed at `9cba0800`) treats the 9 ops as a single atomic landing.

**Tech Stack:** Bash (`mv`, `rm`, `rmdir`, `find`, `grep`), git, Python 3 (only for `py_compile` smoke check). No new dependencies.

**Spec reference:** [docs/superpowers/specs/2026-05-02-hm-mining-app-b1-refactor-design.md](../specs/2026-05-02-hm-mining-app-b1-refactor-design.md)

---

## File Map

**Sources (read for verification only):**

- `files/hm_mining_app/**` — current untracked tree (~28 files)
- `files/README.md` — duplicate of `files/hm_mining_app/README.md` (verified byte-identical 2026-05-02)
- `files/.DS_Store` — macOS noise

**Modified during refactor:**

- `hm_mining_app/.gitignore` — replace `models_store/` with `models_store/*` + `!models_store/.gitkeep`
- `hm_mining_app/README.md` — full rewrite (single-member scope, no Docker, no seed)

**Created:**

- `hm_mining_app/models_store/.gitkeep` — empty, lets the runtime dir survive in git

**Deleted:**

- `files/README.md`, `files/.DS_Store`, `files/` (the wrapper itself)
- `hm_mining_app/Dockerfile`
- `hm_mining_app/docker-compose.yml`
- `hm_mining_app/scripts/seed_demo.py`

**Untouched (explicit non-goals):**

- Every file under `hm_mining_app/app/` (api, ml, sql, main.py, config.py, …)
- `hm_mining_app/scripts/init_db.py`
- `hm_mining_app/.env.example`
- `hm_mining_app/requirements.txt`
- `hm_mining_app/frontend/index.html`
- The rest of the parent repo: `data-mining/`, `datamining-*/`, `new-datamining/`, `web/`, `output/`, `data/`, `survey_*.py`, `etl_olist_to_sql.py`, `generate_notebook.py`

---

## Task 1: Pre-flight verification

**Files:** none modified. Pure read-only sanity checks.

**Why:** The plan assumes a specific starting state (spec section 5 pre-condition). If anything has shifted since the spec was written, abort and re-plan.

- [ ] **Step 1.1: Confirm source state**

Run from repo root (`/Users/mac/Documents/mining/Datawarehouse_Data-mining`):

```bash
[ -d files/hm_mining_app ] && echo OK_source_present || echo FAIL_source_missing
[ ! -d hm_mining_app ] && echo OK_no_collision || echo FAIL_target_exists
diff -q files/README.md files/hm_mining_app/README.md && echo OK_readmes_identical || echo FAIL_readmes_diverged
git status --porcelain files/ | head -1 | grep -q '^??' && echo OK_files_untracked || echo CHECK_files_tracked
```

Expected output: four lines, all starting `OK_`.

- [ ] **Step 1.2: Confirm no hidden imports referencing `files.`**

```bash
grep -rn "from files\.\|import files\." files/hm_mining_app/ 2>/dev/null | head -5
```

Expected: empty output (no matches).

- [ ] **Step 1.3: Capture current file count for later reconciliation**

```bash
find files/hm_mining_app -type f | wc -l
```

Note the number (expected 29). Task 6 will check the new tree against this minus 3 deletions plus 1 addition = 27.

---

## Task 2: Move directory + remove `files/` wrapper

**Files:**

- Move: `files/hm_mining_app/` → `hm_mining_app/`
- Delete: `files/README.md`, `files/.DS_Store`, `files/` (wrapper)

- [ ] **Step 2.1: Move the app to top-level**

```bash
mv files/hm_mining_app hm_mining_app
```

- [ ] **Step 2.2: Remove the duplicate README**

```bash
rm files/README.md
```

- [ ] **Step 2.3: Remove the macOS noise file**

```bash
rm files/.DS_Store
```

- [ ] **Step 2.4: Remove the now-empty wrapper**

```bash
rmdir files
```

`rmdir` will fail if `files/` isn't empty — that's the intended safeguard. If it fails, run `ls -la files/` to find leftover content and stop to investigate; do NOT use `rm -rf`.

- [ ] **Step 2.5: Confirm move**

```bash
[ -d hm_mining_app/app ] && [ -d hm_mining_app/scripts ] && [ ! -d files ] && echo OK || echo FAIL
```

Expected: `OK`.

---

## Task 3: Delete unwanted files inside `hm_mining_app/`

**Files:**

- Delete: `hm_mining_app/Dockerfile`
- Delete: `hm_mining_app/docker-compose.yml`
- Delete: `hm_mining_app/scripts/seed_demo.py`

- [ ] **Step 3.1: Remove Dockerfile**

```bash
rm hm_mining_app/Dockerfile
```

- [ ] **Step 3.2: Remove docker-compose.yml**

```bash
rm hm_mining_app/docker-compose.yml
```

- [ ] **Step 3.3: Remove seed_demo.py**

```bash
rm hm_mining_app/scripts/seed_demo.py
```

- [ ] **Step 3.4: Confirm deletions**

```bash
[ ! -f hm_mining_app/Dockerfile ] && \
[ ! -f hm_mining_app/docker-compose.yml ] && \
[ ! -f hm_mining_app/scripts/seed_demo.py ] && echo OK || echo FAIL
```

Expected: `OK`.

---

## Task 4: Update `.gitignore` and add `models_store/.gitkeep`

**Files:**

- Modify: `hm_mining_app/.gitignore`
- Create: `hm_mining_app/models_store/.gitkeep`

**Why:** The current `.gitignore` excludes the entire `models_store/` directory, which means an empty `.gitkeep` placed inside it would also be ignored — the directory would not exist after `git clone`, and `app/config.py`'s `model_store_path` would silently `mkdir` it on first import. That works, but it's nicer for the directory to exist out-of-the-box for newcomers reading the repo.

- [ ] **Step 4.1: Replace the `models_store/` line in `.gitignore`**

The current `hm_mining_app/.gitignore` contains 12 lines. Line 7 is `models_store/`. Replace it with two lines so the placeholder is exempted.

Edit `hm_mining_app/.gitignore`:

```diff
 __pycache__/
 *.py[cod]
 *.egg-info/
 .venv/
 venv/
 .env
-models_store/
+models_store/*
+!models_store/.gitkeep
 *.joblib
 .DS_Store
 .pytest_cache/
 .idea/
 .vscode/
```

After the edit, the file should be 13 lines and contain both `models_store/*` and `!models_store/.gitkeep` (in that order — the negation must come AFTER the broad pattern).

- [ ] **Step 4.2: Verify the .gitignore is well-formed**

```bash
grep -n "models_store" hm_mining_app/.gitignore
```

Expected output (exact line numbers may vary by 1 if there's a trailing newline difference):

```text
7:models_store/*
8:!models_store/.gitkeep
```

- [ ] **Step 4.3: Create the placeholder file**

```bash
mkdir -p hm_mining_app/models_store
: > hm_mining_app/models_store/.gitkeep
```

(`: > <file>` is the POSIX way to create an empty file without printing anything.)

- [ ] **Step 4.4: Confirm the placeholder is NOT ignored by git**

```bash
git check-ignore -v hm_mining_app/models_store/.gitkeep || echo OK_not_ignored
git check-ignore -v hm_mining_app/models_store/anything_else.joblib && echo OK_other_files_ignored
```

Expected:

- First command exits non-zero (no rule ignores it) and prints `OK_not_ignored`.
- Second command exits 0 (the `*.joblib` rule matches) and prints `OK_other_files_ignored`.

---

## Task 5: Rewrite `hm_mining_app/README.md`

**Files:**

- Modify: `hm_mining_app/README.md` (full replacement, ~100 lines down from 174)

**Why:** Strip Docker, seed, and team-partition sections; insert an explicit scope statement that maps the module to the single member's deliverable and to Chương 5.3 of the group report. All sections that the report actually references (API list, continuous-learning argument, Chương 4 model interpretation) are kept verbatim.

- [ ] **Step 5.1: Replace the file with the new content below**

Overwrite `hm_mining_app/README.md` with:

````markdown
# H&M Mining App

Phần code do **một thành viên Nhóm 01 — KDL & KPDL** phụ trách trong bài tập lớn môn _Kho dữ liệu và Khai phá dữ liệu_ (giảng viên: ThS. Nguyễn Quỳnh Chi, năm học 2025–2026).

Module này đáp ứng 2 yêu cầu mở rộng của thầy được nêu ở **Chương 5.3** báo cáo nhóm:

1. **Hệ thống thu thập dữ liệu liên tục** — endpoint `POST /ingest/*` nhận khách hàng & giao dịch mới qua HTTP, ghi thẳng vào bảng `transactions`.
2. **Hệ thống học liên tục** — `APScheduler` retrain định kỳ; mỗi phiên bản mô hình được lưu vào bảng `model_registry` với chỉ số đánh giá; phục vụ bằng phiên bản `is_active=TRUE` (zero-downtime swap).

## Phạm vi của module

- ✅ **Trong scope:** FastAPI app + 3 lớp ML (K-Means / Apriori / Random Forest theo Chương 4 báo cáo) + scheduler + dashboard tối giản (Alpine.js + Chart.js).
- ❌ **Ngoài scope (việc của thành viên khác):** notebook EDA H&M (Chương 3), ETL từ CSV `customers.csv` / `articles.csv` / `transactions_train.csv` vào Postgres, slide demo, file Word báo cáo.

## Tiền đề

DB Postgres đã được thành viên khác load sẵn 3 bảng H&M. Yêu cầu schema:

- `customers` — `customer_id` VARCHAR PK
- `articles` — `article_id` VARCHAR PK; phải có cột `index_group_name` và `product_group_name`
- `transactions(t_dat, customer_id, article_id, price, sales_channel_id)` — có index trên `(customer_id, t_dat)`

App này **không** tạo / chạm DDL của 3 bảng trên. Khi chạy `python -m scripts.init_db`, app chỉ tạo 2 bảng nội bộ (`model_registry`, `prediction_log`) bằng `CREATE TABLE IF NOT EXISTS` — idempotent.

## Kiến trúc

```text
Client (web/curl) ──► FastAPI ──► PostgreSQL (do thành viên khác load)
                        │
                        ├─► Layer 1 KMeans      (Fashion DNA)
                        ├─► Layer 2 Apriori     (per-cluster rules)
                        └─► Layer 3 RandomForest (will_buy_7d)
                        ▲
                        │ APScheduler cron retrain
```

Tất cả tính toán nặng (JOIN, AGG) đẩy xuống PostgreSQL bằng SQL — đúng tinh thần báo cáo mục 3.3 (chống OOM khi >1 triệu khách hàng).

## Cài đặt local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Sửa DATABASE_URL trong .env trỏ vào Postgres của nhóm

python -m scripts.init_db          # tạo model_registry + prediction_log
uvicorn app.main:app --reload --port 8000

# Lần đầu phải train cả 3 lớp
curl -X POST http://localhost:8000/retrain/all
```

App chạy tại <http://localhost:8000> (Dashboard) và <http://localhost:8000/docs> (Swagger).

## API chính

| Method | Path | Mô tả |
|---|---|---|
| POST | `/ingest/customer` | Tạo / update khách hàng |
| POST | `/ingest/transactions` | Nhận lô giao dịch (≤10k) |
| GET  | `/predict/cluster/{customer_id}` | Cụm phong cách |
| GET  | `/predict/recommend/{customer_id}?top_k=5` | Cross-sell theo luật của cụm |
| GET  | `/predict/will-buy/{customer_id}` | Xác suất mua trong 7 ngày |
| POST | `/retrain/layer1` \| `/layer2` \| `/layer3` \| `/all` | Trigger retrain (background) |
| GET  | `/metrics/summary` | Overview + mô hình active |
| GET  | `/metrics/models/{layer}` | Lịch sử các phiên bản |
| GET  | `/metrics/cluster-distribution` | Số KH theo từng cụm |

## Học liên tục — đáp ứng yêu cầu thầy

1. **Thu thập:** `POST /ingest/transactions` ghi thẳng vào bảng `transactions`. Mọi giao dịch mới đều hiện diện ở lần huấn luyện kế tiếp.
2. **Versioning:** mỗi lần `train_*` thành công sẽ:
   - Lưu file `models_store/{layer}/v{ts}.joblib`
   - INSERT 1 dòng vào `model_registry` (metrics, n_samples, cutoff_date)
   - Đánh dấu `is_active=TRUE` cho phiên bản mới, FALSE cho các phiên bản cũ
3. **Cron retrain:** `APScheduler` chạy ngầm trong process `uvicorn`. Mặc định:
   - L1 KMeans: Chủ nhật 02:00 UTC
   - L2 Apriori: Chủ nhật 03:00 UTC (sau L1)
   - L3 Random Forest: Hằng ngày 01:00 UTC
4. **Logging dự đoán:** mọi response `/predict/*` đều được ghi vào `prediction_log` — sau N ngày có thể join với `transactions` thực tế để tính accuracy drift, từ đó trigger retrain ngoài lịch nếu cần.
5. **Zero-downtime:** predict luôn nạp `is_active=TRUE`. Train mới không gián đoạn traffic.

## Diễn giải mô hình

- **Layer 1** dùng đúng 7 đặc trưng của báo cáo (mục 4.1.1) — KHÔNG đưa `age` và `total_items` vào K-Means.
- **Layer 2** chạy theo mô hình **Segment-then-Mine**: mỗi cụm có bộ luật riêng, tránh sinh luật chung chung vô giá trị.
- **Layer 3** dùng `class_weight='balanced'`, `max_samples=0.4`, `max_depth=8` — khớp đúng tham số trong báo cáo (mục 4.3.2.b). Mục tiêu là Recall cao ở lớp 1 (như báo cáo mục 4.3.2: "Tại sao Recall cao 0.75 là chiến thắng").

## Test nhanh

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Predict cho 1 khách hàng (sau khi đã train)
curl http://localhost:8000/predict/cluster/cust_000001
curl http://localhost:8000/predict/recommend/cust_000001
curl http://localhost:8000/predict/will-buy/cust_000001

# 3. Xem chỉ số
curl http://localhost:8000/metrics/summary | jq

# 4. Nạp giao dịch mới
curl -X POST http://localhost:8000/ingest/transactions \
     -H 'Content-Type: application/json' \
     -d '{"transactions":[
            {"t_dat":"2024-01-15","customer_id":"cust_000001",
             "article_id":"0000000001","price":0.025,"sales_channel_id":2}
         ]}'
```

## Hạn chế & hướng phát triển

- Hiện chưa lập lịch tự động "đối chiếu" `prediction_log.actual_value` từ `transactions` — có thể bổ sung 1 cron job nữa.
- Drift detection (PSI / KS test trên feature distribution) chưa có — đây là next step nếu muốn retrain "có điều kiện" thay vì cố định lịch.
- Frontend tối giản — đủ để demo. Production nên thay bằng React + thư viện chart đầy đủ.
````

- [ ] **Step 5.2: Verify the rewrite**

```bash
wc -l hm_mining_app/README.md
grep -c "Docker\|docker-compose\|seed_demo\|Phân công đề xuất\|Nạp dữ liệu H&M" hm_mining_app/README.md
```

Expected:

- Line count between 90 and 110
- Grep count: `0` (none of the removed-section keywords survive)

---

## Task 6: Run all 7 verification checks (V1–V7 from spec section 8)

**Files:** none modified. Final correctness gate before staging.

- [ ] **Step 6.1: V1 — Python files compile**

```bash
find hm_mining_app -name "*.py" | xargs python -m py_compile && echo V1_OK
```

Expected: `V1_OK`. If any file fails, fix before proceeding.

- [ ] **Step 6.2: V2 — No surviving Docker / seed references**

```bash
grep -rn "seed_demo\|Dockerfile\|docker-compose\|docker compose" hm_mining_app/ \
  --exclude-dir=__pycache__ \
  | grep -v 'README.md:.*Hạn chế' \
  || echo V2_OK
```

Expected: `V2_OK` (no matches). The `--exclude-dir=__pycache__` skips bytecode noise.

- [ ] **Step 6.3: V3 — git status shows expected untracked tree**

```bash
git status --porcelain
```

Expected output (order may vary):

```text
?? .DS_Store
?? hm_mining_app/
```

`files/` must NOT appear. `.DS_Store` is a leftover from earlier sessions and not in scope to remove here.

- [ ] **Step 6.4: V4 — `files/` is gone**

```bash
[ ! -d files ] && echo V4_OK || echo V4_FAIL
```

Expected: `V4_OK`.

- [ ] **Step 6.5: V5 — All three deleted files are absent**

```bash
[ ! -f hm_mining_app/scripts/seed_demo.py ] && \
[ ! -f hm_mining_app/Dockerfile ] && \
[ ! -f hm_mining_app/docker-compose.yml ] && echo V5_OK || echo V5_FAIL
```

Expected: `V5_OK`.

- [ ] **Step 6.6: V6 — `.env.example` is unchanged (still 11 vars)**

```bash
grep -cE '^[A-Z_]+=' hm_mining_app/.env.example
```

Expected: `11`.

- [ ] **Step 6.7: V7 — Manual README walkthrough**

Open `hm_mining_app/README.md` in your editor. Confirm by eyeball:

- [ ] Title still reads `# H&M Mining App`
- [ ] Section "Phạm vi của module" is present and lists in-scope vs out-of-scope items
- [ ] Section "Tiền đề" lists the 3 H&M tables
- [ ] Section "Cài đặt local" exists; Docker section does NOT
- [ ] Section "Học liên tục — đáp ứng yêu cầu thầy" present (5-numbered list)
- [ ] Section "Diễn giải mô hình" mentions all three layers with the report's mục numbers (4.1.1, 4.3.2.b)
- [ ] No "Phân công đề xuất" table at the end
- [ ] No "Nạp dữ liệu H&M thật" section

If anything is off, edit and re-run V2 / step 5.2 grep.

---

## Task 7: Stage and commit

**Files:** none modified — purely git operations.

- [ ] **Step 7.1: Stage the new tree**

```bash
git add hm_mining_app/
```

Note: do NOT use `git add -A`; that would also stage the existing untracked `.DS_Store` at the repo root, which is not part of this refactor.

- [ ] **Step 7.2: Sanity check the staged diff**

```bash
git status --short
git diff --cached --stat | tail -5
```

Expected:

- Status shows `A  hm_mining_app/...` lines for every file in the new tree (about 27 of them).
- Status still shows `?? .DS_Store` (untracked, intentionally not staged).
- The diff stat's last line shows ~27 files changed.

If `git status` shows any `M` (modified) lines for files outside `hm_mining_app/`, stop and investigate; the refactor should not touch anything else.

- [ ] **Step 7.3: Commit**

```bash
git commit -m "$(cat <<'EOF'
refactor: introduce hm_mining_app at top level (B1 refactor)

First-time introduction of the FastAPI continuous-learning app to the
repo, satisfying Chương 5.3 of the group report (continuous data
collection + continuous learning with model_registry versioning).

Changes vs. the untracked draft under files/hm_mining_app/:
- moved out of files/ wrapper to top-level hm_mining_app/
- removed Dockerfile + docker-compose.yml (local Python only)
- removed scripts/seed_demo.py (DB H&M is loaded by another team member)
- README rewritten to scope down to single-member deliverable
- .gitignore updated to keep models_store/.gitkeep tracked

See docs/superpowers/specs/2026-05-02-hm-mining-app-b1-refactor-design.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7.4: Verify the commit**

```bash
git log --oneline -3
git show --stat HEAD | head -5
```

Expected:

- Latest commit subject is `refactor: introduce hm_mining_app at top level (B1 refactor)`.
- The previous 2 commits are `9cba0800 spec: amend op 8/9 + section 7` and `a9121d57 spec: hm_mining_app B1 refactor design`.
- The diff stat shows ~27 new files, all under `hm_mining_app/`.

- [ ] **Step 7.5: Final clean status**

```bash
git status
```

Expected: only the pre-existing untracked `.DS_Store` (and possibly `docs/superpowers/plans/...` if this plan file itself wasn't committed yet) remains. Working tree is otherwise clean.

---

## Done

The refactor is complete when:

- `git log --oneline -1` shows the refactor commit
- All 7 verification checks (V1–V7) pass
- The owner has read the new README and confirmed it represents their deliverable

**Out of scope, deferred:** B2 schema split (separating `model_registry` + `prediction_log` from the H&M tables in `app/sql/schema.sql`), tests, drift detection, frontend rewrite — see spec section 10.
