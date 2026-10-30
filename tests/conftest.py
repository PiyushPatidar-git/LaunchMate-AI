import os, tempfile, pathlib
_tmp = pathlib.Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.as_posix()}"
for k in ("NEBIUS_API_KEY", "TAVILY_API_KEY"):
    os.environ[k] = ""
