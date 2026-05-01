# MMW Imaging Quality Assessment

## Project Status

This repository is a local mmWave image quality assessment tool with a FastAPI backend and a React/Vite frontend.
The current default branch is `main`.

Recent delivered work already merged into `main`:

- Unified the left-side import/ranking area into a single sample list.
- Moved weight controls into the top-right settings panel.
- Switched the main viewer to a portrait-first layout with a vertical histogram rail.
- Restyled histograms to a Lightroom-like dark card style.
- Fixed metric tooltip clipping by rendering popovers through a portal.
- Preserved full sample filenames in the list.
- Added row-level selection for sample actions such as calculate, select all, clear, and delete.
- Added streamed batch import progress in the UI.
- Reduced import latency by downscaling images for analysis and downscaling reference images for view classification.

## Repo Layout

- `backend/app/main.py`: FastAPI entrypoint and API routes.
- `backend/app/storage.py`: persistent image records, import pipeline, overlay and mask persistence.
- `backend/app/processing.py`: ROI extraction and raw metric computation.
- `backend/app/view_classifier.py`: front/back view classification using prototype embeddings from `example_pic/`.
- `frontend/src/App.tsx`: main operator UI.
- `frontend/src/api.ts`: frontend API client, including streamed import progress handling.
- `frontend/src/styles.css`: UI styling.
- `backend/tests/`: backend tests.
- `frontend/src/*.test.ts*`: frontend tests.
- `data/`: runtime state, uploaded files, masks, overlays, and `state.json`.

## Runtime

Install dependencies:

```powershell
python -m pip install -r backend/requirements.txt
npm install --prefix frontend
```

Start backend:

```powershell
.\scripts\start-backend.ps1
```

Start frontend:

```powershell
.\scripts\start-frontend.ps1
```

App URLs:

- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/api/health`

## Verification

```powershell
python -m pytest
npm test --prefix frontend
npm run build --prefix frontend
```

## Current UI Shape

- Left rail: import area, streamed progress panel, sample list, row actions.
- Center: portrait viewer with overlay switching.
- Right rail: feature histograms, radar chart, raw metric table.
- Export actions remain in the top bar.

## Current Import Behavior

- Batch calculation uses `/api/import/progress` and streams newline-delimited JSON events.
- The frontend shows `计算进度`, `completed / total`, and the current filename while processing.
- Backend import analysis uses a reduced analysis size to lower latency, then resizes the generated mask and overlays back to original image dimensions for display and storage.

## Known Input Caveat

- Images with strong white borders can confuse AOI extraction.
- If the AOI expands to nearly the full frame, downstream metrics such as CNR become unreliable.
- Current preferred workflow is to remove obvious white borders before import rather than applying in-repo heuristics.

## Git Notes

- `main` already contains the streamed import progress and import-latency improvements.
- There may be untracked local files such as `DESIGN.md`, `stitch_exports/`, `plugins/`, `docs/superpowers/plans/`, and files under `tmp/`. Treat them as user-owned unless explicitly asked to modify them.
