#!/usr/bin/env python3
"""
Match a control set of papers (CSV with 55 papers) against a second CSV export
(Scopus, IEEE, WoS, ACM, etc.).

Primary match: DOI (case-insensitive)
Fallback: normalised title

Usage:
    python match_control_papers.py control_55.csv target_export.csv
    python match_control_papers.py control_55.csv target_export.csv --rank-col "Relevance_Rank"
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd


def normalise_doi(doi: str) -> str:
    if pd.isna(doi) or not str(doi).strip():
        return ""
    doi = str(doi).strip().lower()
    # remove common prefixes
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = doi.rstrip(".,;")
    return doi


def normalise_title(title: str) -> str:
    if pd.isna(title) or not str(title).strip():
        return ""
    t = str(title).lower()
    t = re.sub(r"[^\w\s]", " ", t)          # remove punctuation
    t = re.sub(r"\s+", " ", t).strip()
    return t


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first column name that matches any of the candidates (case-insensitive)."""
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def main():
    parser = argparse.ArgumentParser(description="Match control papers against a target CSV")
    parser.add_argument("control_csv", help="CSV with the 55 control papers")
    parser.add_argument("target_csv", help="CSV to search in (Scopus/IEEE/WoS/...)")
    parser.add_argument("--rank-col", default=None,
                        help="Optional column name that contains ranking/order (e.g. Relevance_Rank)")
    parser.add_argument("--out", default="match_results.csv",
                        help="Output CSV with the matches (default: match_results.csv)")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # 1. Load control set
    # ------------------------------------------------------------------
    control = pd.read_csv(args.control_csv, low_memory=False)
    print(f"Control set: {len(control)} rows from {args.control_csv}")

    doi_col_c = find_column(control, ["DOI", "doi", "prism:doi", "Dc.Identifier"])
    title_col_c = find_column(control, ["Title", "title", "dc:title", "Article Title"])

    if not doi_col_c and not title_col_c:
        sys.exit("ERROR: Control CSV needs at least a DOI or Title column")

    control["_doi_norm"] = control[doi_col_c].apply(normalise_doi) if doi_col_c else ""
    control["_title_norm"] = control[title_col_c].apply(normalise_title) if title_col_c else ""

    # Build lookup dictionaries
    doi_to_idx = {}
    title_to_idx = {}
    for i, row in control.iterrows():
        if row["_doi_norm"]:
            doi_to_idx[row["_doi_norm"]] = i
        if row["_title_norm"]:
            title_to_idx[row["_title_norm"]] = i

    # ------------------------------------------------------------------
    # 2. Load target CSV
    # ------------------------------------------------------------------
    target = pd.read_csv(args.target_csv, low_memory=False)
    print(f"Target set : {len(target)} rows from {args.target_csv}")

    doi_col_t = find_column(target, ["DOI", "doi", "prism:doi", "Dc.Identifier"])
    title_col_t = find_column(target, ["Title", "title", "dc:title", "Article Title"])
    rank_col = args.rank_col or find_column(target, ["Relevance_Rank", "Rank", "rank", "Order"])

    if not doi_col_t and not title_col_t:
        sys.exit("ERROR: Target CSV needs at least a DOI or Title column")

    # ------------------------------------------------------------------
    # 3. Match
    # ------------------------------------------------------------------
    matches = []
    found_control_indices = set()

    for pos, row in target.iterrows():
        # 1-based rank / position in the target file
        rank = int(row[rank_col]) if rank_col and pd.notna(row[rank_col]) else pos + 1

        doi_norm = normalise_doi(row[doi_col_t]) if doi_col_t else ""
        title_norm = normalise_title(row[title_col_t]) if title_col_t else ""

        matched_idx = None
        match_type = None

        if doi_norm and doi_norm in doi_to_idx:
            matched_idx = doi_to_idx[doi_norm]
            match_type = "DOI"
        elif title_norm and title_norm in title_to_idx:
            matched_idx = title_to_idx[title_norm]
            match_type = "Title"

        if matched_idx is not None and matched_idx not in found_control_indices:
            found_control_indices.add(matched_idx)
            ctrl = control.loc[matched_idx]
            matches.append({
                "Control_Index": matched_idx,
                "Match_Type": match_type,
                "Rank_in_Target": rank,
                "DOI": ctrl.get(doi_col_c, ""),
                "Title": ctrl.get(title_col_c, ""),
                "Target_Title": row.get(title_col_t, ""),
                "Target_DOI": row.get(doi_col_t, ""),
            })

    # ------------------------------------------------------------------
    # 4. Report
    # ------------------------------------------------------------------
    matches_df = pd.DataFrame(matches).sort_values("Rank_in_Target")
    print(f"\nFound {len(matches_df)} / {len(control)} control papers\n")

    if not matches_df.empty:
        print(matches_df[["Rank_in_Target", "Match_Type", "Title"]].to_string(index=False))
        print()

    missing = control.drop(index=list(found_control_indices))
    if len(missing) > 0:
        print(f"Missing {len(missing)} papers:")
        for _, row in missing.iterrows():
            title = row.get(title_col_c, "")[:80] if title_col_c else ""
            doi = row.get(doi_col_c, "") if doi_col_c else ""
            print(f"  - {doi} | {title}")

    # Save full results
    matches_df.to_csv(args.out, index=False)
    print(f"\nDetailed results saved to: {args.out}")


if __name__ == "__main__":
    main()