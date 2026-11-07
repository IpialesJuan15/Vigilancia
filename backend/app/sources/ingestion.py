"""OA source resolution; no paywall bypass or invented metadata."""

import ipaddress
import socket
from urllib.parse import quote, urljoin, urlsplit

import httpx

from app.config import get_settings
from app.services.documents import IngestionError


def public_url(url: str):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
    ):
        raise IngestionError(
            "unsafe_url", "La fuente devolvió una dirección de descarga no permitida"
        )
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError()
    except (OSError, ValueError):
        raise IngestionError(
            "unsafe_url", "No pudimos comprobar la dirección de la fuente"
        ) from None


def fetch(url: str, *, maximum: int | None = None) -> bytes:
    maximum = maximum or get_settings().max_pdf_bytes
    headers = {"User-Agent": f"LiveSRL/0.2 ({get_settings().project_contact})"}
    with httpx.Client(
        timeout=httpx.Timeout(60, connect=15), headers=headers, follow_redirects=False
    ) as client:
        for _ in range(5):
            public_url(url)
            with client.stream("GET", url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > maximum:
                        raise IngestionError(
                            "document_too_large", "El documento supera los 20 MB permitidos"
                        )
                return bytes(body)
    raise IngestionError("redirect_limit", "La fuente devolvió demasiadas redirecciones")


def json_get(url: str) -> dict:
    import json

    return json.loads(fetch(url, maximum=5 * 1024 * 1024))


def resolve(doi: str) -> dict:
    # Europe PMC is preferred for complete, licensed JATS and biomedical metadata.
    result = json_get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
        + quote(f'DOI:"{doi}"')
        + "&format=json&resultType=core"
    )
    records = result.get("resultList", {}).get("result", [])
    record = next((x for x in records if str(x.get("doi", "")).lower() == doi), None)
    if record and record.get("isOpenAccess") == "Y" and record.get("pmcid"):
        return {
            "title": record["title"],
            "authors": record.get("authorList", {}).get("author", []),
            "journal": record.get("journalInfo", {}).get("journal", {}).get("title"),
            "year": int(record["pubYear"]) if record.get("pubYear") else None,
            "license": record.get("license"),
            "format": "xml",
            "url": f"https://www.ebi.ac.uk/europepmc/webservices/rest/{record['pmcid']}/fullTextXML",
            "provider": "europepmc",
        }
    # Broader subject coverage via OpenAlex. Keys are optional configuration; never invented.
    key = get_settings().openalex_api_key
    work = json_get(
        "https://api.openalex.org/works/https://doi.org/"
        + quote(doi, safe="")
        + ("?api_key=" + quote(key) if key else "")
    )
    location = work.get("best_oa_location") or {}
    if not work.get("open_access", {}).get("is_oa") or not location.get("pdf_url"):
        raise IngestionError(
            "not_open_access", "No encontramos texto completo de acceso abierto para este DOI"
        )
    return {
        "title": work["title"],
        "authors": [
            {"fullName": x["author"]["display_name"], "orcid": x["author"].get("orcid")}
            for x in work.get("authorships", [])
        ],
        "journal": (location.get("source") or {}).get("display_name"),
        "year": work.get("publication_year"),
        "license": location.get("license"),
        "format": "pdf",
        "url": location["pdf_url"],
        "provider": "openalex",
    }
