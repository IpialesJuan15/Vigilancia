import socket
from contextlib import contextmanager

import httpx
import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import AuditLog, LivingReview, User
from app.services.documents import (
    IngestionError,
    enrich_pdf,
    license_policy,
    normalize_doi,
    parse_jats,
    parse_pdf,
    validate_pdf,
)
from app.services.storage import ObjectStore
from app.sources.ingestion import public_url, resolve
from app.tasks.ingest import ingest_review
from app.tests.conftest import post, register_verified

JATS = b"""<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta>
<permissions><license xlink:href="https://creativecommons.org/licenses/by/4.0/"/></permissions>
</article-meta></front><body><sec><title>Methods</title><p>We searched three sources.</p></sec>
<sec><title>Results</title><p>Two studies were included.</p><table-wrap><label>Table 1</label>
<caption>Included studies</caption><table><thead><tr><th>Study</th><th>Finding</th></tr></thead>
<tbody><tr><td>Author 2020</td><td>Measured value</td></tr></tbody></table></table-wrap>
</sec></body>
<back><ref-list><ref><mixed-citation>Author. Study.<pub-id pub-id-type="doi">10.1234/study</pub-id>
</mixed-citation></ref></ref-list></back></article>"""


@pytest.mark.parametrize("value", ["10.1234/ABC", "https://doi.org/10.1234/ABC", "doi:10.1234/ABC"])
def test_doi_normalization(value):
    assert normalize_doi(value) == "10.1234/abc"


@pytest.mark.parametrize("value", ["bad", "https://localhost/x", "10.1234/a?x=y", "10.1234/a b"])
def test_bad_doi(value):
    with pytest.raises(IngestionError):
        normalize_doi(value)


@pytest.mark.parametrize(
    "value,restricted",
    [
        ("cc-by", False),
        ("CC0", False),
        ("https://creativecommons.org/licenses/by-sa/4.0/", False),
        ("cc-by-nc-nd", True),
    ],
)
def test_license_policy(value, restricted):
    assert license_policy(value)[1] is restricted


def test_unknown_license():
    with pytest.raises(IngestionError):
        license_policy("all rights reserved")


def test_jats_preserves_literal_cells_and_provenance():
    doc = parse_jats(JATS)
    assert doc["sections"][0]["paragraphs"][0]["text"] == "We searched three sources."
    assert doc["tables"][0]["rows"][0][1]["text"] == "Measured value"
    assert doc["references"][0]["doi"] == "10.1234/study"
    assert all(p["location"] for s in doc["sections"] for p in s["paragraphs"])
    with pytest.raises(Exception):
        parse_jats(b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><article>&e;</article>')
    with pytest.raises(IngestionError):
        parse_jats(b"<error/>")


def pdf_bytes():
    import pymupdf

    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 50), "Systematic review 10.1234/test")
        page.insert_text((50, 80), "Methods: We searched databases.")
        return pdf.tobytes()


def test_pdf_validation_and_reading():
    data = pdf_bytes()
    validate_pdf(data)
    doc = parse_pdf(data)
    assert "10.1234/test" in doc["sections"][0]["paragraphs"][0]["text"]
    assert doc["sections"][0]["paragraphs"][0]["page"] == 1
    for invalid in [b"html", b"%PDF-broken"]:
        with pytest.raises(IngestionError):
            validate_pdf(invalid)
    import pymupdf

    with pymupdf.open() as pdf:
        pdf.new_page()
        with pytest.raises(IngestionError):
            parse_pdf(pdf.tobytes())


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/a",
        "https://localhost/a",
        "https://127.0.0.1/a",
        "https://user:pass@example.org/a",
        "https://example.org:22/a",
    ],
)
def test_private_downloads_rejected(url, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(IngestionError):
        public_url(url)


def test_public_download_and_redirect_limits(monkeypatch):
    from app.sources.ingestion import fetch

    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))]
    )
    public_url("https://example.org/article")

    class Client:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        @contextmanager
        def stream(self, method, url):
            yield httpx.Response(200, content=b"hello", request=httpx.Request(method, url))

    monkeypatch.setattr("app.sources.ingestion.httpx.Client", Client)
    assert fetch("https://example.org/article") == b"hello"
    with pytest.raises(IngestionError):
        fetch("https://example.org/article", maximum=2)


def test_sources_resolve_oa_and_refuse_closed(monkeypatch):
    monkeypatch.setattr(
        "app.sources.ingestion.json_get",
        lambda url: {
            "resultList": {
                "result": [
                    {
                        "doi": "10.1234/test",
                        "isOpenAccess": "Y",
                        "pmcid": "PMC123",
                        "title": "Systematic review",
                        "pubYear": "2024",
                        "license": "cc-by",
                    }
                ]
            }
        },
    )
    assert resolve("10.1234/test")["format"] == "xml"

    def openalex(url):
        if "europepmc" in url:
            return {}
        return {
            "title": "Systematic review",
            "open_access": {"is_oa": True},
            "best_oa_location": {"pdf_url": "https://example.org/a.pdf", "license": "cc-by"},
        }

    monkeypatch.setattr("app.sources.ingestion.json_get", openalex)
    assert resolve("10.1234/test")["format"] == "pdf"
    monkeypatch.setattr("app.sources.ingestion.json_get", lambda url: {})
    with pytest.raises(IngestionError):
        resolve("10.1234/test")


def test_grobid_sections_references_and_fallback(monkeypatch):
    tei = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div><head>Methods</head>
<p>Literal method</p></div></body><back><listBibl><biblStruct>Reference
<idno type="DOI">10.1234/a</idno></biblStruct></listBibl></back></text></TEI>"""

    class Client:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def post(self, *a, **kw):
            return httpx.Response(200, content=tei, request=httpx.Request("POST", "http://grobid"))

    monkeypatch.setattr(httpx, "Client", Client)
    doc = enrich_pdf(b"pdf", {"warnings": []})
    assert doc["references"][0]["doi"] == "10.1234/a"
    assert doc["sections"][0]["paragraphs"][0]["text"] == "Literal method"

    def fail(*a, **k):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(Client, "post", fail)
    assert enrich_pdf(b"pdf", {"warnings": []})["warnings"]


@pytest.fixture
def curator(client, mail, db, monkeypatch, tmp_path):
    register_verified(client, mail)
    post(client, "/auth/login", {"email": "user@example.org", "password": "a-secure-password-123"})
    user = db.scalar(select(User))
    user.role = "curator"
    db.commit()
    monkeypatch.setattr(get_settings(), "storage_backend", "local")
    monkeypatch.setattr(get_settings(), "storage_dir", str(tmp_path))
    monkeypatch.setattr("app.api.routes.reviews.ingest.delay", lambda rid: None)
    return user


def multipart(client, doi="10.1234/test", files=None):
    token = client.get("/auth/csrf").json()["token"]
    return client.post(
        "/reviews",
        data={"doi": doi},
        files=files,
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": token},
    )


def test_create_duplicate_ownership_retry_and_storage(client, curator, db):
    response = multipart(client, files={"pdf": ("anything.pdf", pdf_bytes(), "application/pdf")})
    assert response.status_code == 202
    rid = response.json()["id"]
    assert multipart(client).json()["duplicate"] is True
    assert client.get("/reviews").json()["total"] == 1
    review = db.get(LivingReview, rid)
    assert ObjectStore().get(review.uploaded_key).startswith(b"%PDF-")
    assert client.get(f"/reviews/{rid}/source").status_code == 404
    assert post(client, f"/reviews/{rid}/retry", {}).status_code == 409
    review.status = "failed"
    db.commit()
    assert post(client, f"/reviews/{rid}/retry", {}).status_code == 202
    assert post(client, f"/reviews/{rid}/confirm-license", {}).status_code == 409
    other = User(name="Other", email="other@example.org")
    db.add(other)
    db.flush()
    review.owner_curator_id = other.id
    db.commit()
    assert client.get(f"/reviews/{rid}").status_code == 404
    assert multipart(client).status_code == 409


def test_subscriber_cannot_ingest(client, curator, db):
    curator.role = "subscriber"
    db.commit()
    assert multipart(client).status_code == 403
    assert client.get("/reviews").json()["ingestion_available"] is False


@pytest.mark.parametrize("data,mime", [(b"not pdf", "application/pdf"), (b"%PDF-", "text/plain")])
def test_bad_upload(client, curator, data, mime):
    assert multipart(client, files={"pdf": ("file.pdf", data, mime)}).status_code == 422


def test_invalid_doi_api(client, curator):
    assert multipart(client, "bad").status_code == 422


@pytest.fixture
def worker(db, curator, monkeypatch):
    @contextmanager
    def session():
        yield db

    monkeypatch.setattr("app.tasks.ingest.SessionLocal", session)
    monkeypatch.setattr(
        "app.tasks.ingest.resolve",
        lambda doi: {
            "title": "Systematic review",
            "authors": [{"fullName": "Author"}],
            "journal": "Journal",
            "year": 2024,
            "license": "cc-by",
            "format": "xml",
            "url": "https://example.org/article",
            "provider": "test",
        },
    )
    monkeypatch.setattr("app.tasks.ingest.fetch", lambda url: JATS)
    review = LivingReview(original_doi="10.1234/test", owner_curator_id=curator.id)
    db.add(review)
    db.commit()
    return review


def test_complete_ingestion_preserves_original_and_audits(client, worker, db):
    ingest_review(worker.id)
    assert worker.status == "parsed" and worker.progress == 100
    assert worker.document["tables"][0]["rows"][0][1]["text"] == "Measured value"
    assert worker.source_sha256 == worker.document["provenance"]["sha256"]
    assert db.scalar(select(AuditLog).where(AuditLog.action == "review_parsed"))
    assert client.get(f"/reviews/{worker.id}/source").content == JATS
    assert client.get(f"/reviews/{worker.id}").json()["document"]["references"]
    ingest_review(worker.id)  # completed tasks are idempotent


def test_restricted_license_requires_explicit_confirmation(client, worker, monkeypatch, db):
    restricted = JATS.replace(b"/licenses/by/", b"/licenses/by-nc-nd/")
    monkeypatch.setattr("app.tasks.ingest.fetch", lambda url: restricted)
    ingest_review(worker.id)
    assert worker.status == "license_review" and worker.document is None
    assert post(client, f"/reviews/{worker.id}/confirm-license", {}).status_code == 202
    ingest_review(worker.id)
    assert worker.status == "parsed" and worker.license == "CC BY-NC-ND"


def test_worker_failure_is_visible_and_retryable(worker, monkeypatch):
    def fail(doi):
        raise IngestionError("not_open_access", "No es OA")

    monkeypatch.setattr("app.tasks.ingest.resolve", fail)
    ingest_review(worker.id)
    assert worker.status == "failed" and worker.error_code == "not_open_access"

    def broken(doi):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.tasks.ingest.resolve", broken)
    ingest_review(worker.id)
    assert worker.error_code == "source_unavailable"


def test_request_body_limit_before_multipart_spooling(client):
    response = client.post(
        "/reviews", content=b"x", headers={"Content-Length": str(22 * 1024 * 1024)}
    )
    assert response.status_code == 413
    assert response.json()["code"] == "upload_too_large"


def test_streamed_body_limit_cannot_be_bypassed(client):
    response = client.post(
        "/reviews",
        data={"doi": "10.1234/test"},
        files={"pdf": ("big.pdf", b"x" * (22 * 1024 * 1024), "application/pdf")},
        headers={"Content-Length": "0"},
    )
    assert response.status_code == 413


def test_jats_publisher_license_locations_and_merged_headers():
    from app.services.documents import jats_license

    for fragment in [
        (
            '<license><license-p><ext-link xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xlink:href="https://creativecommons.org/licenses/by/4.0/">'
            "CC BY</ext-link></license-p></license>"
        ),
        '<license><license_ref xmlns="http://www.niso.org/schemas/ali/1.0/">https://creativecommons.org/licenses/by/4.0/</license_ref></license>',
    ]:
        xml = (
            "<article><front><permissions>" + fragment + "</permissions></front></article>"
        ).encode()
        assert license_policy(jats_license(xml)) == ("CC BY", False)
    xml = JATS.replace(b"<th>Study</th>", b'<th colspan="2">Study</th>')
    assert parse_jats(xml)["tables"][0]["header_cells"][0][0]["colspan"] == "2"
    assert (
        jats_license(
            b"<article><permissions><license>All rights reserved</license></permissions></article>"
        )
        == "All rights reserved"
    )


@pytest.mark.parametrize(
    "status,retry_after,expected", [(503, "1", 2), (429, "120", 1), (403, "1", 1)]
)
def test_source_retries_only_transient_errors_and_honors_limits(
    monkeypatch, status, retry_after, expected
):
    from app.sources.ingestion import fetch

    monkeypatch.setattr("app.sources.ingestion.public_url", lambda url: None)
    waits = []
    monkeypatch.setattr("app.sources.ingestion.time.sleep", lambda seconds: waits.append(seconds))
    attempts = []

    class Client:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        @contextmanager
        def stream(self, method, url):
            attempts.append(url)
            yield httpx.Response(
                status if len(attempts) == 1 else 200,
                content=b"source",
                headers={"Retry-After": retry_after},
                request=httpx.Request(method, url),
            )

    monkeypatch.setattr("app.sources.ingestion.httpx.Client", Client)
    if expected == 2:
        assert fetch("https://example.org/document") == b"source"
        assert waits == [1]
    else:
        with pytest.raises(httpx.HTTPStatusError):
            fetch("https://example.org/document")
        assert waits == []
    assert len(attempts) == expected


def test_block_boundaries_are_readable_without_changing_inline_names():
    from defusedxml import ElementTree as ET

    from app.services.documents import text

    assert (
        text(ET.fromstring("<td><p>Case-control</p><p>PD patients</p></td>"))
        == "Case-control PD patients"
    )
    assert text(ET.fromstring("<p>miR<sub>21</sub>-5p</p>")) == "miR21-5p"
