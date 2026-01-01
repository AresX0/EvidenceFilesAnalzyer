# Compatibility shim: use case_agent.hash_inventory
from pathlib import Path
from case_agent.pipelines.hash_inventory import walk_and_hash, sha256_file
from config import EVIDENCE_DIR, DB_PATH

def run():
    walk_and_hash(Path(EVIDENCE_DIR), db_path=DB_PATH)

def sha256(path):
    return sha256_file(Path(path))

if __name__ == "__main__":
    run()
