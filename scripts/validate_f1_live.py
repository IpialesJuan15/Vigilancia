"""Live acceptance against local Compose. Creates one explicit technical curator fixture.

Runs real HTTP, Celery, Europe PMC and S3. No mocked articles or provider responses.
Credentials are generated per execution, never printed or written to the report.
"""

import argparse
import hashlib
import json
import secrets
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx

DOIS = [
    "10.3390/ijms262412164",
    "10.3389/fspor.2025.1694648",
    "10.1016/j.fochx.2025.103378",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:3000")
    parser.add_argument("--project", default="livesrl")
    parser.add_argument("--output", default="docs/evidence/f1-live.json")
    parser.add_argument(
        "--pdf",
        type=Path,
        help="Optional real PDF for DOI 10.1371/journal.pone.0337516",
    )
    parser.add_argument(
        "--reparse",
        action="store_true",
        help="Reprocess only the dedicated technical account fixtures",
    )
    args = parser.parse_args()
    if urlsplit(args.base_url).hostname not in {"localhost", "127.0.0.1"}:
        parser.error(
            "This acceptance script is restricted to the local development instance"
        )
    password = secrets.token_urlsafe(32)
    email = "f1-validation@tests.example.org"
    setup = f"""from sqlalchemy import select
from app.db import SessionLocal
from app.models import User
from app.security import hasher
with SessionLocal() as db:
    user = db.scalar(select(User).where(User.email == {email!r}))
    if user and user.name != "Validación técnica F1":
        raise RuntimeError("Fixture account collision")
    if not user:
        user = User(name="Validación técnica F1", email={email!r}, role="curator", email_verified=True)
        db.add(user)
    user.password_hash = hasher.hash({password!r})
    user.session_version = (user.session_version or 0) + 1
    db.flush()
    if {args.reparse!r}:
        from app.models import LivingReview
        for review in db.scalars(select(LivingReview).where(LivingReview.owner_curator_id==user.id)):
            review.status="failed"
            review.error_code="acceptance_reparse"
    db.commit()
"""
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            args.project,
            "exec",
            "-T",
            "api",
            "sh",
            "/app/entrypoint.sh",
            "python",
            "-",
        ],
        check=False,
        input=setup,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(
            "Could not prepare technical test account; inspect service availability"
        )
    report = {
        "checked_at": datetime.now(ZoneInfo("America/Guayaquil")).isoformat(),
        "scope": "Real DOI/PDF -> API -> Celery -> licensed full text -> JATS or GROBID/PyMuPDF -> MinIO",
        "articles": [],
    }
    with httpx.Client(base_url=args.base_url, timeout=90, trust_env=False) as client:

        def post(path, **kwargs):
            csrf = client.get("/api/auth/csrf")
            csrf.raise_for_status()
            response = client.post(
                "/api" + path,
                headers={"Origin": args.base_url, "X-CSRF-Token": csrf.json()["token"]},
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

        post("/auth/login", json={"email": email, "password": password})
        cases = [(doi, None) for doi in DOIS]
        if args.pdf:
            cases.append(("10.1371/journal.pone.0337516", args.pdf.read_bytes()))
        for doi, pdf in cases:
            listing = client.get("/api/reviews")
            listing.raise_for_status()
            created = next(
                (r for r in listing.json()["items"] if r["original_doi"] == doi), None
            )
            if created is None:
                created = post(
                    "/reviews",
                    data={"doi": doi},
                    files={"pdf": ("review.pdf", pdf, "application/pdf")}
                    if pdf
                    else None,
                )
            rid = created["id"]
            if created["status"] == "failed":
                post(f"/reviews/{rid}/retry", json={})
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline:
                response = client.get(f"/api/reviews/{rid}")
                response.raise_for_status()
                review = response.json()
                if review["status"] == "parsed":
                    break
                if review["status"] in {"failed", "license_review"}:
                    raise RuntimeError(
                        f"{doi}: {review['status']} / {review.get('error_code')}"
                    )
                time.sleep(2)
            else:
                raise TimeoutError(f"{doi}: background ingestion did not complete")
            doc = review["document"]
            assert review["license"] == "CC BY"
            assert doc["sections"] and doc["references"] and doc["tables"]
            assert all(section["paragraphs"] for section in doc["sections"])
            assert all(
                table["rows"] and any(c["text"] for row in table["rows"] for c in row)
                for table in doc["tables"]
            )
            original = client.get(f"/api/reviews/{rid}/source")
            original.raise_for_status()
            digest = hashlib.sha256(original.content).hexdigest()
            assert digest == doc["provenance"]["sha256"]
            report["articles"].append(
                {
                    "doi": doi,
                    "review_id": rid,
                    "title": review["original_title"],
                    "license": review["license"],
                    "source": doc["provenance"]["url"],
                    "sha256": digest,
                    "format": "pdf" if original.content.startswith(b"%PDF-") else "xml",
                    "parser": doc["parser"],
                    "verification_url": doc["provenance"].get(
                        "verification_url", doc["provenance"]["url"]
                    ),
                    "warnings": review["warnings"],
                    "sections": len(doc["sections"]),
                    "references": len(doc["references"]),
                    "tables": len(doc["tables"]),
                    "rows": sum(len(t["rows"]) for t in doc["tables"]),
                    "sample_cell": next(
                        c["text"]
                        for t in doc["tables"]
                        for row in t["rows"]
                        for c in row
                        if c["text"]
                    )[:160],
                }
            )
            print(doi, "parsed", report["articles"][-1]["tables"], "tables", flush=True)
        post("/auth/logout", json={})
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("Verified", len(report["articles"]), "real OA reviews; evidence:", output)


if __name__ == "__main__":
    main()
