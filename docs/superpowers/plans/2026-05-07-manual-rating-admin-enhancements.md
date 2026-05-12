# Manual Rating Admin Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the manual-rating module with optional dataset labels, folder import, richer admin progress views, and per-image multi-review details with average/weighted aggregates.

**Architecture:** Keep the existing FastAPI + SQLite + React structure. Extend the manual-rating repository and API payloads in place, add one admin image-detail endpoint, and rebuild the manual-rating admin screen around those richer payloads. Preserve reviewer blind-review behavior.

**Tech Stack:** FastAPI, sqlite3, pytest, React 19, TypeScript, Vitest, plain CSS

---

## File Structure

- Modify: `backend/app/manual_rating_repository.py`
  Responsibility: dataset optional labels, task reviewer progress, per-image aggregate queries
- Modify: `backend/app/main.py`
  Responsibility: dataset upload metadata, task summary enrichment, admin image-detail endpoint
- Modify: `backend/tests/test_manual_rating_api.py`
  Responsibility: API regression coverage for folder upload metadata, admin progress, admin image detail
- Modify: `frontend/src/manualRatingTypes.ts`
  Responsibility: richer dataset/task/admin-detail types
- Modify: `frontend/src/manualRatingApi.ts`
  Responsibility: upload metadata, summary/admin-detail fetchers
- Modify: `frontend/src/manualRatingApi.test.ts`
  Responsibility: request coverage for folder upload metadata
- Modify: `frontend/src/ManualRatingApp.tsx`
  Responsibility: Chinese admin workspace rewrite with folder import, optional labels, reviewer progress, image detail panel
- Modify: `frontend/src/ManualRatingApp.test.tsx`
  Responsibility: UI regression coverage for the new admin panels
- Modify: `frontend/src/styles.css`
  Responsibility: admin dataset cards, progress tables, image detail layout

## Tasks

### Task 1: Lock backend behavior with failing tests

- [ ] Add API tests for optional dataset labels + folder upload payload.
- [ ] Add API tests for admin task summary including reviewer progress rows.
- [ ] Add API tests for admin single-image detail including multi-review records, averages, and weighted averages.
- [ ] Run targeted pytest and confirm the new tests fail for the expected missing fields/routes.

### Task 2: Extend repository and backend endpoints

- [ ] Add backward-compatible dataset metadata columns with defaults for existing databases.
- [ ] Extend dataset creation/upload flows to persist optional labels and folder-derived source identifiers.
- [ ] Extend task summary output with reviewer progress and per-image aggregate rows.
- [ ] Add admin image-detail endpoint returning filename, image URL, all reviewer scores, and average/weighted aggregates.
- [ ] Run targeted pytest until green.

### Task 3: Lock frontend behavior with failing tests

- [ ] Add API-client test for multipart upload including optional metadata fields.
- [ ] Add ManualRatingApp tests for folder import hints and admin detail panels.
- [ ] Run targeted Vitest and confirm the new assertions fail before implementation.

### Task 4: Rebuild the admin UI around the richer payloads

- [ ] Rewrite `ManualRatingApp.tsx` admin view in clean Chinese text.
- [ ] Add dataset create form fields: dataset name required; source label, batch label, note label optional; file/folder import supported.
- [ ] Add dataset list cards showing image count, created time, and only the labels that were actually filled.
- [ ] Add task status panel with per-reviewer progress.
- [ ] Add image detail inspector showing multi-review scores, average scores, and weighted scores.
- [ ] Run targeted Vitest until green.

### Task 5: Final verification

- [ ] Run `python -m pytest backend/tests -v`.
- [ ] Run `npm test --prefix frontend`.
- [ ] Run `npm run build --prefix frontend`.
- [ ] Restart or verify local dev services and report the updated usage flow in Chinese.
