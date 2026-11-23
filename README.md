# Coforge resume automation

Run from the repository root with Python 3.12. Install the dependencies and set `ANTHROPIC_API_KEY` in the process environment before running the batch.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python batch_run.py
```

The batch reads PDF, DOCX, PNG and JPEG files from `Inputs`. It sends PDFs and images to Claude as documents or images, and sends extracted Word text including table cells. The default model is `claude-sonnet-4-6` because Anthropic retired the blueprint's Sonnet 3.7 model. Set `ANTHROPIC_MODEL` to select a deployment that supports forced tools and temperature zero.

Each completed resume has its own directory under `output`. Its filename uses the first available project role and candidate name. Missing facts stay empty. Use `--workers` to set concurrency, or `--inputs`, `--output` and `--template` to select other paths.

## Review a flagged resume

The batch prints a review ID when confidence is below 0.90, a section is missing, or local source checks flag a claim. Text matching checks quoted values and project boundaries. A reviewer must inspect scans and resolve ambiguous project attribution against the original. The SQLite checkpoint database in the output directory contains extracted candidate data and pending reviews.

```powershell
.\.venv\Scripts\python batch_run.py --show THREAD_ID
.\.venv\Scripts\python batch_run.py --approve THREAD_ID
```

To edit before approving, save the complete `payload` object from `--show` as UTF-8 JSON, correct it against the source, and run the following command.

```powershell
.\.venv\Scripts\python batch_run.py --approve THREAD_ID --corrected reviewed.json
```

Reuse the same output directory for review and subsequent batch runs. An unchanged input retains its checkpoint. Individual failures are reported at the end of each file's processing and give the batch a nonzero exit code. A later run retries those files.

## Verification

```powershell
.\.venv\Scripts\python -m unittest -v
```

The tests use a synthetic resume, the supplied master template, and a mocked Claude response. They exercise XML styling, the confidence threshold, source grounding, checkpoint recovery, review edits, and forced tool extraction.
