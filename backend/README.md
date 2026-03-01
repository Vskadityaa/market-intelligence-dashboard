# Backend – Market Intelligence Dashboard

## Fix for "pydantic-core / Rust" and "uvicorn not recognized" errors

Your terminal failed because **Python 3.14** was used. `pydantic-core` has no pre-built wheel for 3.14, so pip tries to build it and needs Rust. **Use Python 3.11 or 3.12** instead.

### Option A: Use the venv we created (Python 3.11)

A new venv was created with Python 3.11 and dependencies are already installed. In PowerShell, run:

```powershell
cd c:\Users\Admin\OneDrive\Desktop\abhishek\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Or run the script (same thing):

```powershell
.\run.ps1
```

**If the server kept restarting with "WatchFiles detected changes in venv\...":** that happens when using `--reload` because the watcher sees changes inside `venv`. Use the commands above **without** `--reload` (restart the server manually after code changes), or run `.\run.ps1`.

### Option B: Recreate the venv yourself

If the venv was removed or you want a fresh one:

```powershell
cd c:\Users\Admin\OneDrive\Desktop\abhishek\backend
# Remove old venv if it exists (it was created with 3.14)
if (Test-Path venv) { Remove-Item -Recurse -Force venv }
# Create venv with Python 3.11 (you have it as py -3.11)
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Optional: API keys

Copy `.env.example` to `.env` and add your keys for full features:

- `OPENAI_API_KEY` – for AI summaries and AI Score
- `FMP_API_KEY` – for earnings call transcripts

The app works without them (quotes and fundamentals come from Yahoo Finance).
