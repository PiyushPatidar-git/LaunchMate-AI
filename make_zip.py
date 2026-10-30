"""Recreate LaunchMate-AI.zip (no secrets, venv, database or caches)."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".git"}
SKIP_NAMES = {".env", "LaunchMate-AI.zip"}
SKIP_EXT = {".db", ".sqlite", ".pyc", ".zip"}

def main():
    out = ROOT.parent / "LaunchMate-AI.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob("*")):
            rel = p.relative_to(ROOT)
            if p.is_dir() or SKIP_DIRS & set(rel.parts) or p.name in SKIP_NAMES or p.suffix in SKIP_EXT:
                continue
            z.write(p, Path("LaunchMate-AI") / rel)
    print("Created", out)

if __name__ == "__main__":
    main()
