
"""
Princeton Data Commons (PDC) ingest module.
Uses OAI-PMH with license whitelist.
"""
import requests
import xml.etree.ElementTree as ET

PDC_OAI = "https://dataspace.princeton.edu/oai/request"

ALLOWED_LICENSES = [
    "cc0",
    "creative commons",
    "cc by",
    "cc-by",
]

def fetch_records(metadata_prefix="oai_dc", max_records=500):
    params = {
        "verb": "ListRecords",
        "metadataPrefix": metadata_prefix,
    }
    records = []
    while True:
        r = requests.get(PDC_OAI, params=params, timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.text)

        for rec in root.findall(".//{http://www.openarchives.org/OAI/2.0/}record"):
            meta = rec.find(".//{http://www.openarchives.org/OAI/2.0/oai_dc/}dc")
            if meta is None:
                continue
            texts = []
            license_ok = False
            for el in meta:
                tag = el.tag.lower()
                text = (el.text or "").strip()
                if not text:
                    continue
                if "rights" in tag or "license" in tag:
                    for l in ALLOWED_LICENSES:
                        if l in text.lower():
                            license_ok = True
                if "description" in tag:
                    texts.append(text)
            if license_ok:
                records.extend(texts)
            if len(records) >= max_records:
                return records
        token = root.find(".//{http://www.openarchives.org/OAI/2.0/}resumptionToken")
        if token is None or not token.text:
            break
        params = {"verb": "ListRecords", "resumptionToken": token.text}
    return records
