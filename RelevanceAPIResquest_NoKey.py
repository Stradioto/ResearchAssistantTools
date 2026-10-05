import requests
import pandas as pd
import time

# 1. Paste your API Key
API_KEY = "" #Create your API key in https://dev.elsevier.com/


QUERY = (
    'TITLE-ABS-KEY ( "energy communit*" OR "virtual power plant*" OR microgrid* '
    'OR "distributed energy resource*" OR ( energy AND ( communit* OR REC OR CER ) ) ) '
    'AND TITLE-ABS-KEY ( cyber* OR attack* OR threat* OR vulnerabilit* OR intrusion '
    'OR spoofing OR malware OR ransomware OR security ) '
    'AND PUBYEAR > 2018 AND PUBYEAR < 2027 '
    'AND ( LIMIT-TO ( DOCTYPE , "ar" ) OR LIMIT-TO ( DOCTYPE , "cp" ) OR LIMIT-TO ( DOCTYPE , "bk" ) ) '
    'AND ( LIMIT-TO ( LANGUAGE , "English" ) )'
)

# Correct Scopus Search API endpoint (the original script had this wrong)
url = "https://api.elsevier.com/content/search/scopus"
headers = {"X-ELS-APIKey": API_KEY, "Accept": "application/json"}

params = {
    "query": QUERY,
    "count": 25,       # max per request for standard API keys
    "start": 0,
    "sort": "relevancy",  # Scopus API's actual relevance sort field name (not "relevance")
}

all_papers = []
# Hard ceiling confirmed by Elsevier's own API behavior: start-offset pagination
# fails for start >= 5000, regardless of sort. This is NOT fixable by code.
max_results = 5000

print("Starting extraction in true API relevance order (capped at 5000, hard platform limit)...")

while params["start"] < max_results:
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Stopped at row {params['start']}: HTTP {response.status_code} - {response.text[:300]}")
        break

    data = response.json()
    entries = data.get("search-results", {}).get("entry", [])

    if not entries:
        print("No more results returned.")
        break

    for entry in entries:
        all_papers.append({
            "Relevance_Rank": len(all_papers) + 1,
            "Title": entry.get("dc:title"),
            "Author": entry.get("dc:creator", "Unknown"),
            "Journal": entry.get("prism:publicationName"),
            "Year": (entry.get("prism:coverDate") or "")[:4],
            "DOI": entry.get("prism:doi", ""),
        })

    print(f"Fetched up to rank {len(all_papers)}...")
    params["start"] += 25
    time.sleep(0.5)  # respect rate limits

df = pd.DataFrame(all_papers)
df.to_csv("scopus_true_relevance_order.csv", index=False)
print(f"\nDone. {len(all_papers)} papers saved to scopus_true_relevance_order.csv")
print("This is the maximum depth obtainable in verified relevance order via the Scopus API.")