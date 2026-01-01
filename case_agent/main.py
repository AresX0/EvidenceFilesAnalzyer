"""CLI entrypoint to run the pipeline steps in order.
"""
import argparse
import logging
from pathlib import Path
from .db.init_db import init_db
from .pipelines.hash_inventory import walk_and_hash
from .pipelines.text_extract import extract_for_file
from .pipelines.entity_extract import extract_entities_for_file
from .pipelines.timeline_builder import build_timeline

from .logging_config import setup_logging

setup_logging()
logger = logging.getLogger("case_agent.main")


def main():
    parser = argparse.ArgumentParser(description="Case agent pipeline runner")
    parser.add_argument("evidence_dir", nargs="?", default=None)
    parser.add_argument("--db", default=None)
    parser.add_argument("--report", default=None, help="Write extended audit report to this path (JSON)")
    parser.add_argument("--report-csv", default=None, help="Write CSV summary to this path")
    args = parser.parse_args()
    evidence_dir = Path(args.evidence_dir) if args.evidence_dir else None
    if evidence_dir is None:
        from .config import DEFAULT_EVIDENCE_DIR
        evidence_dir = Path(DEFAULT_EVIDENCE_DIR)
    init_db(args.db)
    files = walk_and_hash(evidence_dir, db_path=args.db)
    for f in files:
        p = Path(f["path"])
        extract_for_file(p, db_path=args.db)
        extract_entities_for_file(p, db_path=args.db)
    build_timeline(db_path=args.db)
    logger.info("Pipeline run complete")

    if args.report:
        from .reports import generate_extended_report, write_report_json, write_report_csv
        report = generate_extended_report(args.db)
        write_report_json(report, args.report)
        logger.info("Wrote JSON report to %s", args.report)
        if args.report_csv:
            write_report_csv(report, args.report_csv)
            logger.info("Wrote CSV report to %s", args.report_csv)


if __name__ == "__main__":
    main()
