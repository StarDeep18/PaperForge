"""
PaperForge — Database Migration CLI Helper.

Executes Alembic migrations programmatically.
Usage:
    python migrate.py [upgrade|downgrade|current|history]
"""

import sys
import os
from alembic.config import Config
from alembic import command

def run_migrations():
    server_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_ini_path = os.path.join(server_dir, "alembic.ini")
    
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(server_dir, "alembic"))
    
    action = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    target = sys.argv[2] if len(sys.argv) > 2 else "head"
    
    print(f"Executing database migration action: '{action}' with target: '{target}'...")
    
    if action == "upgrade":
        command.upgrade(alembic_cfg, target)
        print("Database schema successfully upgraded to latest migration head.")
    elif action == "downgrade":
        command.downgrade(alembic_cfg, target)
        print("Database schema downgraded successfully.")
    elif action == "stamp":
        command.stamp(alembic_cfg, target)
        print(f"Database stamped with revision: '{target}'.")
    elif action == "current":
        command.current(alembic_cfg)
    elif action == "history":
        command.history(alembic_cfg)
    else:
        print(f"Unknown migration action '{action}'. Options: upgrade, downgrade, stamp, current, history")

if __name__ == "__main__":
    run_migrations()
