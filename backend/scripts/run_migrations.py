"""Run Alembic migrations programmatically."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alembic import command
from alembic.config import Config


def run():
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")
    print("Migrations complete.")


if __name__ == "__main__":
    run()
