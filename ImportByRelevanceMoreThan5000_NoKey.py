import requests
import pandas as pd
import time

API_KEY = ""  #Create your API key in https://dev.elsevier.com/
QUERY = (
    'TITLE-ABS-KEY ( "energy communit*" OR "virtual power plant*" OR microgrid* '
    'OR "distributed energy resource*" OR ( energy AND ( communit* OR REC OR CER ) ) ) '
    'AND TITLE-ABS-KEY ( cyber* OR attack* OR threat* OR vulnerabilit* OR intrusion '
    'OR spoofing OR malware OR ransomware OR security ) '
    'AND PUBYEAR > 2018 AND PUBYEAR < 2027 '
    'AND ( LIMIT-TO ( DOCTYPE , "ar" ) OR LIMIT-TO ( DOCTYPE , "cp" ) OR LIMIT-TO ( DOCTYPE , "bk" ) ) '
    'AND ( LIMIT-TO ( LANGUAGE , "English" ) )'
)

url = "https://api.elsevier.com/content/search/scopus"
headers = {"X-ELS-APIKey": API_KEY, "Accept": "application/json"}

all_papers = []
cursor = "*"  # initial cursor
seen = set()

print("Fetching ALL results via cursor pagination...")

while cursor:
    params = {
        "query": QUERY,
        "count": 25,
        "cursor": cursor,       # replaces the start parameter entirely
        "sort": "relevancy",
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Stopped: HTTP {response.status_code} - {response.text[:300]}")
        break

    data = response.json()
    results = data.get("search-results", {})
    entries = results.get("entry", [])

    if not entries:
        print("No more results.")
        break

    for entry in entries:
        eid = entry.get("dc:identifier") or entry.get("eid")
        if eid in seen:
            continue
        seen.add(eid)
        all_papers.append({
            "Relevance_Rank": len(all_papers) + 1,
            "Title": entry.get("dc:title"),
            "Author": entry.get("dc:creator", "Unknown"),
            "Journal": entry.get("prism:publicationName"),
            "Year": (entry.get("prism:coverDate") or "")[:4],
            "DOI": entry.get("prism:doi", ""),
        })

    print(f"Fetched up to rank {len(all_papers)}...")
    cursor = results.get("cursor", {}).get("@next")
    time.sleep(0.5)

df = pd.DataFrame(all_papers)
df.to_csv("scopus_true_relevance_order_more_than_5000.csv", index=False)
print(f"\nDone. {len(all_papers)} papers saved.")