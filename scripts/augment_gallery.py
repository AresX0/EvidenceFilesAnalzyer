"""Augment labeled gallery folders by downloading images from different providers.

Usage examples:
  BING_SEARCH_KEY=<key> BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0 python scripts/augment_gallery.py --gallery Images --per 75 --provider bing
  GOOGLE_API_KEY=<key> GOOGLE_CSE_CX=<cx> python scripts/augment_gallery.py --gallery Images --per 50 --provider google
  UNSPLASH_ACCESS_KEY=<key> python scripts/augment_gallery.py --gallery Images --per 30 --provider unsplash

This script iterates each subject folder under `gallery_dir` and attempts to download up to `per` images using the subject name as the query. It is opt-in and requires a provider-specific API key when using remote providers.
"""

import argparse
import os
import shutil
import time
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

import requests

# agent feed helper (writes per-download events)
from scripts.agent_feed import write_event

# Provider environment variables
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CX = os.environ.get("GOOGLE_CSE_CX")
UNSPLASH_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")


def _safe_ext_from_url(url, resp=None):
    # Try content-type first, else fallback to url extension
    if resp is not None:
        ct = resp.headers.get("content-type", "")
        if ct.startswith("image/"):
            mapping = {"jpeg": ".jpg", "png": ".png", "gif": ".gif", "webp": ".webp"}
            t = ct.split("/")[1].split(";")[0]
            return mapping.get(t, "." + t)
    path = urlsplit(url).path
    ext = Path(unquote(path)).suffix
    return ext if ext else ".jpg"


# Bing provider removed — using Google or Unsplash instead

DEFAULT_RETRIES = 3
BACKOFF_BASE = 1  # seconds


def _download_and_save(
    url,
    dest_dir: Path,
    subject: str,
    idx: int,
    retries=DEFAULT_RETRIES,
    backoff_base=BACKOFF_BASE,
):
    """Download `url` into `dest_dir` with a filename based on `subject` and `idx`.
    Retries with exponential backoff on transient errors and returns a dict with status.
    """
    attempts = 0
    last_err = None
    while attempts < retries:
        attempts += 1
        try:
            resp = requests.get(url, stream=True, timeout=30)
            if resp.status_code == 200:
                ext = _safe_ext_from_url(url, resp)
                fname = dest_dir / f"{subject.replace(' ', '_')}_{idx}{ext}"
                with open(fname, "wb") as fh:
                    resp.raw.decode_content = True
                    shutil.copyfileobj(resp.raw, fh)
                return {
                    "file": str(fname),
                    "url": url,
                    "attempts": attempts,
                    "status": "ok",
                }
            else:
                last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = str(e)
        sleep_time = backoff_base * (2 ** (attempts - 1))
        print(
            f"Retry {attempts}/{retries} for {url} (sleep {sleep_time}s) due to {last_err}"
        )
        time.sleep(sleep_time)
    return {
        "file": None,
        "url": url,
        "attempts": attempts,
        "status": "failed",
        "error": last_err,
    }


# Provider: Google Custom Search Engine (CSE)
def download_images_google(
    subject, dest_dir: Path, per=75, retries=DEFAULT_RETRIES, backoff_base=BACKOFF_BASE
):
    dest_dir.mkdir(parents=True, exist_ok=True)
    # evaluate env vars at call time to respect test env changes
    google_key = os.environ.get("GOOGLE_API_KEY") or GOOGLE_KEY
    google_cx = os.environ.get("GOOGLE_CSE_CX") or GOOGLE_CX
    if not google_key or not google_cx:
        print("Google API key or CSE CX not found; skipping augmentation for", subject)
        return []
    endpoint = "https://www.googleapis.com/customsearch/v1"
    downloaded = 0
    per_items = []
    start = 1
    per_page = 10  # Google CSE max per page
    while downloaded < per:
        params = {
            "key": google_key,
            "cx": google_cx,
            "searchType": "image",
            "q": subject,
            "num": min(per_page, per - downloaded),
            "start": start,
        }
        try:
            r = requests.get(endpoint, params=params, timeout=30)
            if r.status_code != 200:
                print("Google CSE failed", r.status_code, r.text)
                break
            data = r.json()
            items = data.get("items", [])
            if not items:
                break
            for item in items:
                if downloaded >= per:
                    break
                url = item.get("link")
                result = _download_and_save(
                    url,
                    dest_dir,
                    subject,
                    downloaded + 1,
                    retries=retries,
                    backoff_base=backoff_base,
                )
                per_items.append(result)
                # Publish per-download event to agent feed
                ev = {
                    "timestamp": None,
                    "source_path": result.get("file") or url,
                    "content_type": "image",
                    "operation": "augment_download",
                    "status": "success" if result.get("status") == "ok" else "error",
                    "summary": f"Augmented gallery download for {subject}",
                    "metrics": {"attempts": result.get("attempts")},
                    "artifacts": [result.get("file")] if result.get("file") else [],
                    "errors": [result.get("error")] if result.get("error") else [],
                }
                try:
                    write_event(ev)
                except Exception:
                    print("Warning: failed to write agent event for", url)
                if result.get("status") == "ok":
                    # Register as EvidenceFile and run face search + persist results
                    try:
                        from case_agent.pipelines import face_search  # noqa: E402
                        from scripts.evidence_utils import (  # noqa: E402
                            register_evidence_file,
                        )

                        fp = Path(result.get("file"))
                        register_evidence_file(fp)
                        try:
                            res = face_search.search_labeled_gallery_for_image(
                                fp, dest_dir.parent, threshold=0.9, top_k=5
                            )
                            face_search._persist_results(None, res, aggregate=True)
                        except Exception as e:
                            print("Face search failed for", fp, e)
                    except Exception as e:
                        print("Failed to register or search downloaded image", e)
                    downloaded += 1
                    print("Downloaded", result["file"])
            start += len(items)
            if len(items) < per_page:
                break
            # respect API limits
            time.sleep(1)
        except Exception as e:
            print("Google CSE error", e)
            break
    return per_items


# Provider: Unsplash
def download_images_unsplash(
    subject, dest_dir: Path, per=75, retries=DEFAULT_RETRIES, backoff_base=BACKOFF_BASE
):
    dest_dir.mkdir(parents=True, exist_ok=True)
    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY") or UNSPLASH_KEY
    if not unsplash_key:
        print("Unsplash API key not found; skipping augmentation for", subject)
        return []
    headers = {"Authorization": f"Client-ID {unsplash_key}"}
    endpoint = "https://api.unsplash.com/search/photos"
    downloaded = 0
    per_items = []
    page = 1
    per_page = 30
    while downloaded < per:
        params = {
            "query": subject,
            "per_page": min(per_page, per - downloaded),
            "page": page,
        }
        try:
            r = requests.get(endpoint, headers=headers, params=params, timeout=30)
            if r.status_code != 200:
                print("Unsplash search failed", r.status_code, r.text)
                break
            data = r.json()
            items = data.get("results", [])
            if not items:
                break
            for item in items:
                if downloaded >= per:
                    break
                url = (
                    item.get("urls", {}).get("raw")
                    or item.get("urls", {}).get("full")
                    or item.get("urls", {}).get("regular")
                )
                result = _download_and_save(
                    url,
                    dest_dir,
                    subject,
                    downloaded + 1,
                    retries=retries,
                    backoff_base=backoff_base,
                )
                per_items.append(result)
                # Publish per-download event to agent feed
                ev = {
                    "timestamp": None,
                    "source_path": result.get("file") or url,
                    "content_type": "image",
                    "operation": "augment_download",
                    "status": "success" if result.get("status") == "ok" else "error",
                    "summary": f"Augmented gallery download for {subject}",
                    "metrics": {"attempts": result.get("attempts")},
                    "artifacts": [result.get("file")] if result.get("file") else [],
                    "errors": [result.get("error")] if result.get("error") else [],
                }
                try:
                    write_event(ev)
                except Exception:
                    print("Warning: failed to write agent event for", url)
                if result.get("status") == "ok":
                    # Register as EvidenceFile and run face search + persist results
                    try:
                        from case_agent.pipelines import face_search  # noqa: E402
                        from scripts.evidence_utils import (  # noqa: E402
                            register_evidence_file,
                        )

                        fp = Path(result.get("file"))
                        register_evidence_file(fp)
                        try:
                            res = face_search.search_labeled_gallery_for_image(
                                fp, dest_dir.parent, threshold=0.9, top_k=5
                            )
                            face_search._persist_results(None, res, aggregate=True)
                        except Exception as e:
                            print("Face search failed for", fp, e)
                    except Exception as e:
                        print("Failed to register or search downloaded image", e)
                    downloaded += 1
                    print("Downloaded", result["file"])
            if len(items) < per_page:
                break
            page += 1
            time.sleep(0.5)
        except Exception as e:
            print("Unsplash error", e)
            break
    return per_items


def augment_gallery(
    gallery_dir: Path,
    per=75,
    provider: Optional[str] = "google",
    retries=DEFAULT_RETRIES,
    backoff_base=BACKOFF_BASE,
):
    if provider is None:
        print("No provider specified; skipping augmentation")
        return 0
    gallery_dir = Path(gallery_dir)
    # re-evaluate provider keys so tests that modify env are respected
    google_key = os.environ.get("GOOGLE_API_KEY") or GOOGLE_KEY
    google_cx = os.environ.get("GOOGLE_CSE_CX") or GOOGLE_CX
    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY") or UNSPLASH_KEY
    if provider == "google" and (not google_key or not google_cx):
        print("Google provider keys missing; skipping augmentation")
        return 0
    if provider == "unsplash" and not unsplash_key:
        print("Unsplash provider key missing; skipping augmentation")
        return 0

    manifest = {
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "provider": provider,
        "per": per,
        "retries": retries,
        "backoff_base": backoff_base,
        "subjects": {},
    }
    total = 0
    for sub in sorted(gallery_dir.iterdir()):
        if not sub.is_dir():
            continue
        subject = sub.name
        print("Augmenting", subject, "using", provider)
        items = []
        if provider == "google":
            items = download_images_google(
                subject, sub, per=per, retries=retries, backoff_base=backoff_base
            )
        elif provider == "unsplash":
            items = download_images_unsplash(
                subject, sub, per=per, retries=retries, backoff_base=backoff_base
            )
        else:
            print("Unknown provider", provider)
            items = []
        manifest["subjects"][subject] = items
        total += len(items)
    artifacts_dir = gallery_dir.parent / "artifacts" / "manifests"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = artifacts_dir / f'augment_manifest_{manifest["timestamp"]}.json'
    try:
        with open(manifest_path, "w", encoding="utf-8") as fh:
            import json

            json.dump(manifest, fh, indent=2)
        # keep a copy at project root for backward-compatibility
        try:
            copy_path = (
                gallery_dir.parent / f'augment_manifest_{manifest["timestamp"]}.json'
            )
            shutil.copy(manifest_path, copy_path)
            print("Wrote manifest to", manifest_path, "and copy to", copy_path)
        except Exception:
            print("Wrote manifest to", manifest_path)
    except Exception as e:
        print("Failed to write manifest", e)
    print(f"Downloaded {total} images in total")
    return total


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--gallery", default="Images")
    p.add_argument("--per", type=int, default=75)
    p.add_argument(
        "--provider",
        choices=["google", "unsplash"],
        default="google",
        help="Image provider to use for augmentation (default: google)",
    )
    p.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Number of attempts per URL (default: 3)",
    )
    p.add_argument(
        "--backoff-base",
        type=float,
        default=BACKOFF_BASE,
        help="Base seconds used for exponential backoff (default: 1)",
    )
    args = p.parse_args()
    augment_gallery(
        Path(args.gallery),
        per=args.per,
        provider=args.provider,
        retries=args.retries,
        backoff_base=args.backoff_base,
    )
