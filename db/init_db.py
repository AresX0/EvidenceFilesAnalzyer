# Compatibility shim — delegate DB initialization to case_agent.db.init_db
from case_agent.db.init_db import init_db, get_session

__all__ = ["init_db", "get_session"]
