import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

__all__ = ["load_config", "ENGINE", "test_db_connection"]


def load_config() -> str:
    """Load environment variables from the project's .env file and return DATABASE_URL.

    This will look for a `.env` file in the project root (same folder as this file).
    If DATABASE_URL is missing after attempting to load environment variables, the
    function prints a clear error message and exits the program with non-zero status.
    """
    project_root = Path(__file__).resolve().parent
    env_path = project_root / ".env"

    # Prefer an explicit .env file in the project root. If it doesn't exist, fall
    # back to default loader (which may read from environment or parent paths).
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print(
            "[config.py] ERROR: DATABASE_URL is not set.\n"
            "Please create a .env file in the project root with a line like:\n"
            "    DATABASE_URL=postgresql://user:pass@host:port/dbname\n"
            "Or set the DATABASE_URL environment variable before running the app.\n"
        )
        sys.exit(1)

    return database_url


## Initialize global ENGINE variable so other modules can `from config import ENGINE`
ENGINE: Optional[object] = None

# Attempt to create an engine from DATABASE_URL. If the URL is present but
# unreachable (for example because the .env contains placeholders like [HOST]),
# fall back to a local SQLite file so the app can run in development mode.
DATABASE_URL = None
try:
    DATABASE_URL = load_config()
except SystemExit:
    # load_config will sys.exit if DATABASE_URL is missing; re-raise so the
    # caller sees the original message. However, if you'd prefer automatic
    # fallback when DATABASE_URL is absent, change load_config behavior.
    raise

# Detect obvious placeholder values and treat them as "unconfigured"
if DATABASE_URL and ("[HOST]" in DATABASE_URL or "HOST" == DATABASE_URL or "[USER]" in DATABASE_URL):
    print("[config.py] WARNING: DATABASE_URL appears to contain placeholder values. Falling back to local SQLite for development.")
    DATABASE_URL = None

if DATABASE_URL:
    try:
        ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
        # Try a quick connection to fail fast if credentials/host are wrong
        try:
            with ENGINE.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as conn_err:
            print(f"[config.py] WARNING: Unable to connect to DATABASE_URL: {conn_err}\nFalling back to local SQLite database for development.")
            ENGINE = None
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"[config.py] ERROR: Failed to create SQLAlchemy engine from DATABASE_URL: {exc}")
        ENGINE = None

# If we didn't successfully create an ENGINE from DATABASE_URL, use local SQLite
if ENGINE is None:
    try:
        project_root = Path(__file__).resolve().parent
        sqlite_path = project_root / "test_realestate.db"
        sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"
        ENGINE = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        print(f"[config.py] Using local SQLite database at: {sqlite_path}")
    except Exception as exc:  # pragma: no cover - fallback failure
        print(f"[config.py] FATAL: Failed to create fallback SQLite engine: {exc}")
        ENGINE = None


def test_db_connection() -> bool:
    """Attempt a simple connection using ENGINE.connect().

    Returns True if successful, False otherwise. Errors are printed for debugging.
    """
    global ENGINE
    if ENGINE is None:
        print("[config.py] ERROR: ENGINE is not initialized. Cannot test connection.")
        return False

    try:
        with ENGINE.connect() as conn:
            # Lightweight sanity check query
            conn.execute(text("SELECT 1"))
        print("[config.py] SUCCESS: Database connection established.")
        return True
    except OperationalError as op_err:
        print(f"[config.py] ERROR: OperationalError connecting to database: {op_err}")
        return False
    except Exception as exc:  # pragma: no cover - runtime diagnostics
        print(f"[config.py] ERROR: Unexpected error during DB connection test: {exc}")
        return False


if __name__ == "__main__":
    # Allow quick verification by running `python config.py` directly
    load_config()
    test_db_connection()
