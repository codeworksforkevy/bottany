from __future__ import annotations
import time
import requests
from lxml import etree
from typing import Dict, Iterable, List, Optional

NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
}

def _get_texts(node, xpath: str) -> List[str]:
    out = []
    for el in node.xpath(xpath, namespaces=NS):
        if isinstance(el, etree._Element):
            t = (el.text or "").strip()
        else:
            t = str(el).strip()
        if t:
            out.append(t)
    return out

def harvest_oai_dc(base_url: str, metadata_prefix: str = "oai_dc", set_spec: Optional[str] = None,
                   max_records: int = 500, sleep_s: float = 0.2, timeout_s: int = 30) -> List[Dict]:
    items: List[Dict] = []
    session = requests.Session()

    params = {"verb": "ListRecords", "metadataPrefix": metadata_prefix}
    if set_spec:
        params["set"] = set_spec

    resumption_token = None
    while True:
        if resumption_token:
            params = {"verb": "ListRecords", "resumptionToken": resumption_token}
        r = session.get(base_url, params=params, timeout=timeout_s)
        r.raise_for_status()
        xml = etree.fromstring(r.content)

        records = xml.xpath("//oai:ListRecords/oai:record", namespaces=NS)
        for rec in records:
            header = rec.find("oai:header", namespaces=NS)
            if header is None or header.get("status") == "deleted":
                continue
            meta = rec.find("oai:metadata", namespaces=NS)
            if meta is None:
                continue
            dc = meta.find("oai_dc:dc", namespaces=NS)
            if dc is None:
                continue

            title = _get_texts(dc, ".//dc:title")
            desc = _get_texts(dc, ".//dc:description")
            rights = _get_texts(dc, ".//dc:rights")
            identifiers = _get_texts(dc, ".//dc:identifier")

            items.append({
                "title": title[0] if title else "",
                "description": " ".join(desc)[:5000] if desc else "",
                "rights": " ".join(rights)[:2000] if rights else "",
                "identifiers": identifiers[:10],
                "source_url": identifiers[0] if identifiers else ""
            })
            if len(items) >= max_records:
                return items

        token_el = xml.xpath("//oai:ListRecords/oai:resumptionToken", namespaces=NS)
        if not token_el:
            break
        resumption_token = (token_el[0].text or "").strip()
        if not resumption_token:
            break
        time.sleep(sleep_s)

    return items
