#!/usr/bin/env python3
"""Parse seed.sql INSERT rows into structured JSON records."""
import json, re, sys, os

SEED = sys.argv[1] if len(sys.argv) > 1 else "db/seed.sql"
OUT = sys.argv[2] if len(sys.argv) > 2 else "db/_tools/seed_records.json"

COLS = ["ref_no","first_author","authors_full","year","title","venue","country",
        "pathology","pathology_code","modality","dataset_name","dataset_access",
        "patient_count","image_count","task","model","method_detail","summary",
        "performance","ext_validation","radiologist_comparison","open_code",
        "open_data","code_url","depth","limitations","doi_url"]

def split_values_with_types(s):
    out, i, n = [], 0, len(s)
    while i < n:
        while i < n and s[i] in " \t": i += 1
        if i >= n: break
        if s[i] == "'":
            i += 1; buf = []
            while i < n:
                if s[i] == "'":
                    if i+1 < n and s[i+1] == "'":
                        buf.append("'"); i += 2; continue
                    i += 1; break
                buf.append(s[i]); i += 1
            out.append("".join(buf))
        else:
            buf = []
            while i < n and s[i] != ",":
                buf.append(s[i]); i += 1
            tok = "".join(buf).strip()
            if tok.upper() == "NULL": out.append(None)
            elif re.fullmatch(r"-?\d+", tok): out.append(int(tok))
            else: out.append(tok)
        while i < n and s[i] in " \t": i += 1
        if i < n and s[i] == ",": i += 1
    return out

records = []
with open(SEED, encoding="utf-8") as fh:
    for line in fh:
        m = re.search(r"VALUES\s*\((.*)\);\s*$", line.rstrip("\n"))
        if not m: continue
        vals = split_values_with_types(m.group(1))
        if len(vals) != len(COLS):
            sys.stderr.write(f"COUNT {len(vals)} :: ref {vals[0] if vals else '?'}\n")
        rec = {k: (vals[idx] if idx < len(vals) else None) for idx, k in enumerate(COLS)}
        records.append(rec)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(records, fh, ensure_ascii=False, indent=1)
print(f"parsed {len(records)} records -> {OUT}")
print("ref range:", records[0]["ref_no"], "..", records[-1]["ref_no"])
refs = [r["ref_no"] for r in records]
print("unique refs:", len(set(refs)), "dupes:", [x for x in set(refs) if refs.count(x)>1])
