import aiohttp

async def _fetch_from_api():

    payload = {
        "q": {
            "_and": [
                {"inventor_first_name": "Nikola"},
                {"inventor_last_name": "Tesla"}
            ]
        },
        "f": [
            "patent_number",
            "patent_title",
            "patent_date",
            "patent_abstract"
        ],
        "o": {"per_page": 200}
    }

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(PATENTSVIEW_URL, json=payload) as resp:
            resp.raise_for_status()
            data = await resp.json()

    patents = data.get("patents", [])
    items = []

    for p in patents:
        items.append({
            "patent_number": p.get("patent_number"),
            "title": p.get("patent_title"),
            "year": (p.get("patent_date") or "")[:4],
            "category": _classify(p.get("patent_title")),
            "abstract": p.get("patent_abstract"),
            "source_url": f"https://ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{p.get('patent_number')}"
        })

    return items

