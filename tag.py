#!/usr/bin/env python3
"""
photo-tagger: Tag Google Drive photos with recognized people using local AI.

Usage:
    python3 tag.py --folder-id <DRIVE_FOLDER_ID>
    python3 tag.py --folder-id <DRIVE_FOLDER_ID> --reprocess   # ignore cache
    python3 tag.py --folder-id <DRIVE_FOLDER_ID> --dry-run     # don't write to Drive
"""

import argparse
import os
import re
import sys
import tempfile

import requests

from auth import get_drive_service
from db import get_conn, is_processed, mark_processed
from recognizer import FaceRecognizer

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/gif",
    "image/x-sony-arw",
}

DRIVE_PROPERTY_KEY = "tagged_people"


def list_images(service, folder_id: str) -> list[dict]:
    images = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed = false"
    while True:
        resp = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, thumbnailLink, description)",
            pageToken=page_token,
            pageSize=200,
        ).execute()
        for f in resp.get("files", []):
            if f["mimeType"] in IMAGE_MIME_TYPES:
                images.append(f)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return images


PREVIEW_SIZE = 1024  # px on longest side — enough for face detection, ~50-200KB vs 30MB+ RAW


def download_preview(service, file: dict, dest_path: str):
    thumbnail_url = file.get("thumbnailLink")
    if not thumbnail_url:
        raise ValueError(f"No thumbnail available for {file['name']} (Drive may not have generated one yet)")

    # Drive thumbnail URLs end in =s<size> — bump it up for better face detection accuracy
    url = re.sub(r"=s\d+$", f"=s{PREVIEW_SIZE}", thumbnail_url)
    if not url.endswith(f"=s{PREVIEW_SIZE}"):
        url = f"{thumbnail_url.rstrip('/')}&sz=s{PREVIEW_SIZE}"

    token = service._http.credentials.token
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    resp.raise_for_status()
    with open(dest_path, "wb") as fh:
        fh.write(resp.content)


def write_tag(service, file: dict, people: list[str], dry_run: bool):
    value = ",".join(people) if people else ""

    existing = (file.get("description") or "").strip()
    people_line = f"People: {value}" if value else "People: (none)"
    if existing:
        description = f"{existing}\n{people_line}"
    else:
        description = people_line

    if dry_run:
        print(f"    [dry-run] would set '{DRIVE_PROPERTY_KEY}' = '{value}'")
        print(f"    [dry-run] would set description = '{description}'")
        return
    service.files().update(
        fileId=file["id"],
        body={
            "properties": {DRIVE_PROPERTY_KEY: value},
            "description": description,
        },
    ).execute()


def run(folder_id: str, reprocess: bool, dry_run: bool):
    print("Authenticating with Google Drive...")
    service = get_drive_service()

    print("Loading face recognition model and known people...")
    recognizer = FaceRecognizer()
    if not recognizer.known_embeddings:
        print("\nNo known people found. Add reference photos to known_people/<name>/")
        print("Example: known_people/tyler/photo1.jpg")
        sys.exit(1)
    print(f"  Ready. Recognizing: {', '.join(recognizer.known_embeddings.keys())}\n")

    conn = get_conn()

    print(f"Listing images in folder {folder_id}...")
    images = list_images(service, folder_id)
    print(f"  Found {len(images)} image(s).\n")

    for i, file in enumerate(images, 1):
        fid = file["id"]
        fname = file["name"]
        prefix = f"[{i}/{len(images)}] {fname}"

        if not reprocess and is_processed(conn, fid):
            print(f"{prefix} — skipped (cached)")
            continue

        print(f"{prefix} — fetching preview...")
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            download_preview(service, file, tmp_path)
            people = recognizer.identify_people(tmp_path)
            label = ", ".join(people) if people else "(none)"
            print(f"  Found: {label}")
            write_tag(service, file, people, dry_run)
            if not dry_run:
                mark_processed(conn, fid, fname, people)
        except Exception as e:
            print(f"  Error: {e}")
        finally:
            os.unlink(tmp_path)

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(description="Tag Google Drive photos with recognized people.")
    parser.add_argument("--folder-id", required=True, help="Google Drive folder ID")
    parser.add_argument("--reprocess", action="store_true", help="Reprocess already-cached files")
    parser.add_argument("--dry-run", action="store_true", help="Don't write tags back to Drive")
    args = parser.parse_args()
    run(args.folder_id, args.reprocess, args.dry_run)


if __name__ == "__main__":
    main()
