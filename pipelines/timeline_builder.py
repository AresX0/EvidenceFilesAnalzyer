# Compatibility shim: delegate timeline building to case_agent implementation
from case_agent.pipelines.timeline_builder import build_timeline
from config import DB_PATH

def run():
    build_timeline(db_path=DB_PATH)

if __name__ == "__main__":
    run()
