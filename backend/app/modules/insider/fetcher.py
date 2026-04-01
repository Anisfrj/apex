"""Module 4: Traqueur d'Initiés — SEC Form 4 Insider Purchases & Sales.

Version : collecte complète (tous codes) + backfill long.

- EFTS essayé en premier, fallback RSS si 0 résultat
- Backfill via RSS avec paramètre dateb par tranches de 7 jours
- Ingestion de TOUTES les nonDerivativeTransaction (P, S, A, M, F, etc.)
"""

import re
from datetime import date, timedelta, datetime
from xml.etree import ElementTree
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

from ...core.config import get_settings
from ...core.http_client import http_get
from ...core.logging import get_logger
from ...models.insider import InsiderTransaction

logger = get_logger("insider_fetcher")

SEC_BASE = "https://www.sec.gov"
SEC_HEADERS = {
    "User-Agent": "APEX-Screener admin@apex-screener.dev",
    "Accept-Encoding": "gzip, deflate",
}


def parse_date_safe(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# RSS EDGAR
# ─────────────────────────────────────────────────────────────────────────────


async def _fetch_rss_page(dateb: str = "", start: int = 0) -> list[dict]:
    """Fetch une page RSS EDGAR browse-edgar (Form 4 récents)."""
    settings = get_settings()
    url = f"{SEC_BASE}/cgi-bin/browse-edgar"
    params = {
        "action": "getcurrent",
        "type": "4",
        "dateb": dateb,
        "owner": "only",
        "count": "100",
        "start": str(start),
        "search_text": "",
        "output": "atom",
    }
    try:
        response = await http_get(
            url,
            source="sec",
            rate_limit=settings.sec_rate_limit,
            params=params,
            headers={**SEC_HEADERS, "Accept": "application/atom+xml"},
        )
        root = ElementTree.fromstring(response.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        filings = []
        for entry in root.findall("atom:entry", ns):
            link_el = entry.find("atom:link", ns)
            updated = entry.findtext("atom:updated", "", ns)
            if link_el is not None:
                href = link_el.get("href", "")
                if href:
                    filings.append(
                        {
                            "index_url": href,
                            "title": entry.findtext("atom:title", "", ns),
                            "updated": updated,
                        }
                    )
        return filings
    except Exception as e:
        logger.warning("rss_page_failed", dateb=dateb, start=start, error=str(e))
        return []


async def fetch_recent_form4_index(days_back: int = 1) -> list[dict]:
    """Fetch les Form 4 récents depuis SEC EDGAR (index de filings)."""
    settings = get_settings()
    cutoff = date.today() - timedelta(days=days_back)

    # ── Tentative EFTS (bonus) ─────────────────────────────────────────────
    try:
        efts_url = "https://efts.sec.gov/LATEST/search-index"
        efts_params = {
            "q": '"<transactionCode>P</transactionCode>"',
            "forms": "4",
            "dateRange": "custom",
            "startdt": cutoff.isoformat(),
            "enddt": date.today().isoformat(),
        }
        response = await http_get(
            efts_url,
            source="sec",
            rate_limit=settings.sec_rate_limit,
            params=efts_params,
            headers={**SEC_HEADERS, "Accept": "application/json"},
        )
        data = response.json()
        hits = data.get("hits", {}).get("hits", [])

        if hits:
            filings = []
            for hit in hits:
                src = hit.get("_source", {})
                accession = hit.get("_id", "").replace(":", "-")
                entity_ids = src.get("entity_id", [])
                cik = entity_ids[0] if entity_ids else ""
                if accession and cik:
                    cik_padded = str(cik).zfill(10)
                    acc_nodash = accession.replace("-", "")
                    dir_url = f"{SEC_BASE}/Archives/edgar/data/{cik_padded}/{acc_nodash}"
                    filings.append(
                        {
                            "index_url": f"{dir_url}/{accession}-index.htm",
                            "dir_url": dir_url,
                            "accession": accession,
                        }
                    )
            logger.info("sec_efts_fetched", count=len(filings))
            return filings
        else:
            logger.info("sec_efts_empty_fallback_rss", days_back=days_back)

    except Exception as e:
        logger.warning("sec_efts_failed_fallback_rss", error=str(e))

    # ── RSS EDGAR (source principale) ─────────────────────────────────────
    if days_back <= 7:
        filings = await _fetch_rss_page()
        filtered = [
            f
            for f in filings
            if not parse_date_safe(f["updated"][:10] if f.get("updated") else "")
            or parse_date_safe(f["updated"][:10]) >= cutoff
        ]
        logger.info("sec_rss_fetched", count=len(filtered), days_back=days_back)
        return filtered

    # Backfill > 7 jours : tranches de 7 jours
    all_filings = []
    seen_urls: set[str] = set()
    cursor = date.today()
    weeks_needed = (days_back // 7) + 1

    logger.info("sec_rss_backfill_start", weeks=weeks_needed, days_back=days_back)

    for week_idx in range(weeks_needed):
        if cursor < cutoff:
            break
        dateb_str = cursor.strftime("%Y%m%d")
        page = await _fetch_rss_page(dateb=dateb_str)

        for f in page:
            if f["index_url"] in seen_urls:
                continue
            entry_date = parse_date_safe(
                f["updated"][:10] if f.get("updated") else ""
            )
            if entry_date and entry_date < cutoff:
                continue
            seen_urls.add(f["index_url"])
            all_filings.append(f)

        cursor -= timedelta(days=7)
        logger.debug(
            "sec_rss_backfill_week",
            week=week_idx + 1,
            dateb=dateb_str,
            cumul=len(all_filings),
        )

    logger.info("sec_rss_backfill_complete", total_filings=len(all_filings))
    return all_filings


# ─────────────────────────────────────────────────────────────────────────────
# Résolution index → XML
# ─────────────────────────────────────────────────────────────────────────────


async def find_xml_url_from_index(index_url: str) -> str | None:
    """Trouve l'URL du vrai XML Form 4."""
    settings = get_settings()
    dir_url = index_url.rsplit("/", 1)[0]
    json_url = f"{dir_url}/index.json"

    # JSON index
    try:
        response = await http_get(
            json_url,
            source="sec",
            rate_limit=settings.sec_rate_limit,
            headers=SEC_HEADERS,
        )
        items = response.json().get("directory", {}).get("item", [])
        for item in items:
            name = item.get("name", "")
            if (
                name.endswith(".xml")
                and not re.match(r"^R\d+\.xml$", name, re.IGNORECASE)
                and "xsl" not in name.lower()
                and name not in ("primary_doc.xml",)
            ):
                return f"{dir_url}/{name}"
        return None
    except Exception as e:
        logger.debug("index_json_failed", url=json_url, error=str(e))

    # Fallback HTML
    try:
        response = await http_get(
            index_url,
            source="sec",
            rate_limit=settings.sec_rate_limit,
            headers={**SEC_HEADERS, "Accept": "text/html"},
        )
        for match in re.finditer(r'href="([^"]+\.xml)"', response.text):
            xml_path = match.group(1)
            if "xsl" in xml_path.lower():
                continue
            if xml_path.startswith("/Archives"):
                return f"{SEC_BASE}{xml_path}"
            if xml_path.startswith("http"):
                return xml_path
            if "/" not in xml_path:
                return f"{dir_url}/{xml_path}"
    except Exception as e:
        logger.debug("index_html_failed", url=index_url, error=str(e))

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Parsing des XML Form 4 (toutes transactions)
# ─────────────────────────────────────────────────────────────────────────────


async def parse_form4_xml(xml_url: str) -> list[dict]:
    """Parse un Form 4 XML et extrait toutes les transactions non dérivées."""
    settings = get_settings()
    try:
        response = await http_get(
            xml_url,
            source="sec",
            rate_limit=settings.sec_rate_limit,
            headers=SEC_HEADERS,
        )
        content = response.text
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            m = re.search(
                r"<ownershipDocument>.*?</ownershipDocument>", content, re.DOTALL
            )
            if not m:
                logger.debug("ownership_document_not_found", url=xml_url)
                return []
            root = ElementTree.fromstring(m.group())

        issuer = root.find(".//issuer")
        company_cik = issuer.findtext("issuerCik", "") if issuer is not None else ""
        company_name = issuer.findtext("issuerName", "") if issuer is not None else ""
        symbol = issuer.findtext("issuerTradingSymbol", "") if issuer is not None else ""

        owner = root.find(".//reportingOwner/reportingOwnerId")
        insider_name = owner.findtext("rptOwnerName", "") if owner is not None else ""

        relationship = root.find(".//reportingOwner/reportingOwnerRelationship")
        insider_title = ""
        if relationship is not None:
            if relationship.findtext("isDirector") == "1":
                insider_title = "Director"
            if relationship.findtext("isOfficer") == "1":
                insider_title = relationship.findtext("officerTitle", "Officer")

        transactions: list[dict] = []
        for txn in root.findall(".//nonDerivativeTransaction"):
            code_elem = txn.find(".//transactionCoding/transactionCode")
            raw_code = code_elem.text.strip() if code_elem is not None and code_elem.text else ""
            txn_code = raw_code or "UNK"  # fallback explicite pour éviter NULL

            acq_disp_el = txn.find(
                ".//transactionAmounts/transactionAcquiredDisposedCode/value"
            )
            acq_disp = acq_disp_el.text if acq_disp_el is not None else None

            txn_date = txn.findtext(".//transactionDate/value", "")
            shares_el = txn.find(".//transactionAmounts/transactionShares/value")
            price_el = txn.find(".//transactionAmounts/transactionPricePerShare/value")
            owned_el = txn.find(
                ".//postTransactionAmounts/sharesOwnedFollowingTransaction/value"
            )

            shares = (
                float(shares_el.text)
                if shares_el is not None and shares_el.text
                else 0
            )
            price = (
                float(price_el.text)
                if price_el is not None and price_el.text
                else 0
            )
            owned_after = (
                float(owned_el.text)
                if owned_el is not None and owned_el.text
                else 0
            )

            transactions.append(
                {
                    "symbol": (symbol or "").upper().strip(),
                    "company_name": company_name,
                    "company_cik": company_cik,
                    "insider_name": insider_name,
                    "insider_title": insider_title,
                    "transaction_date": txn_date,
                    "transaction_code": txn_code,
                    "acquired_disposed": acq_disp,
                    "shares": shares,
                    "price_per_share": price,
                    "total_value": shares * price,
                    "shares_owned_after": owned_after,
                }
            )

        logger.info(
            "form4_parsed",
            url=xml_url,
            symbol=symbol,
            txn_count=len(transactions),
        )
        return transactions

    except Exception as e:
        logger.debug("form4_parse_error", url=xml_url, error=str(e))
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Sync principal appelé par Celery
# ─────────────────────────────────────────────────────────────────────────────


async def sync_insider_transactions(
    db: AsyncSession, days_back: int = 1
) -> list[dict]:
    """Fetch et parse les Form 4 récents depuis SEC EDGAR."""
    filings = await fetch_recent_form4_index(days_back=days_back)
    if not filings:
        logger.info("no_filings_from_edgar")
        return []

    cutoff = date.today() - timedelta(days=days_back)
    new_transactions: list[dict] = []

    for filing in filings:
        index_url = filing["index_url"]
        filing_id = index_url.split("/")[-2] if "/" in index_url else index_url

        existing = await db.execute(
            select(InsiderTransaction.id).where(
                InsiderTransaction.id.like(f"{filing_id}%")
            )
        )
        if existing.fetchone():
            continue

        xml_url = await find_xml_url_from_index(index_url)
        if not xml_url:
            logger.debug("xml_url_not_found", index_url=index_url)
            continue

        for txn in await parse_form4_xml(xml_url):
            if not txn["symbol"]:
                continue
            txn_date = parse_date_safe(txn["transaction_date"])

            record_id = (
                f"{filing_id}_{txn['symbol']}_{txn['transaction_date']}_"
                f"{txn.get('transaction_code') or ''}"
            )

            stmt = insert(InsiderTransaction).values(
                id=record_id,
                filing_date=date.today(),
                symbol=txn["symbol"],
                company_name=txn["company_name"],
                company_cik=txn["company_cik"],
                insider_name=txn["insider_name"],
                insider_title=txn["insider_title"],
                transaction_date=txn_date,
                transaction_code=txn["transaction_code"],
                acquired_disposed=txn["acquired_disposed"],
                shares=txn["shares"],
                price_per_share=txn["price_per_share"],
                total_value=txn["total_value"],
                shares_owned_after=txn["shares_owned_after"],
                alert_sent=False,
                passed_filters=None,
            ).on_conflict_do_nothing()
            await db.execute(stmt)
            new_transactions.append(txn)

    await db.commit()
    logger.info(
        "insider_sync_complete",
        filings_checked=len(filings),
        new_transactions=len(new_transactions),
    )
    return new_transactions
