#!/usr/bin/env python3
"""Match each seed record to a PDF text file: DOI first (locked), then global
one-to-one greedy title/author/year assignment."""
import json, re, os, glob
from difflib import SequenceMatcher

PDFDIR = "/sessions/sweet-sharp-gauss/mnt/outputs/pdftext"
REC = "db/_tools/seed_records.json"
OUT = "db/_tools/match_map.json"

records = json.load(open(REC, encoding="utf-8"))
pdf_files = sorted(glob.glob(os.path.join(PDFDIR, "*.txt")))

STOP = set("the a an of for and to in on with using based study deep learning model "
           "network ct computed tomography image images detection segmentation "
           "classification from via approach framework using analysis".split())

def toks(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return [w for w in s.split() if len(w) > 2 and w not in STOP]

def norm_doi(s):
    if not s: return None
    m = re.search(r"10\.\d{4,9}/[^\s\"'<>)\]]+", s)
    return m.group(0).lower().rstrip(".,;)") if m else None

# preload pdf data
pdf_dois, pdf_titletoks, pdf_head = {}, {}, {}
for p in pdf_files:
    txt = open(p, encoding="utf-8", errors="ignore").read()
    pdf_head[p] = txt[:6000].lower()
    dois = set(m.group(0).lower().rstrip(".,;)")
               for m in re.finditer(r"10\.\d{4,9}/[^\s\"'<>)\]]+", txt))
    pdf_dois[p] = dois
    # title source: filename after NNN_YYYY_ prefix + first 1500 chars
    fn = os.path.basename(p)
    fn_title = re.sub(r"^\d+_\d{4}_", "", fn).replace(".txt","")
    pdf_titletoks[p] = set(toks(fn_title)) | set(toks(txt[:1200]))

def jacc(a, b):
    if not a or not b: return 0.0
    a, b = set(a), set(b)
    return len(a & b) / len(a | b)

matches = {r["ref_no"]: {"pdf": None, "how": "NONE", "score": 0} for r in records}
assigned_pdf = set()

# Pass 1: DOI lock
for r in records:
    doi = norm_doi(r.get("doi_url"))
    if not doi: continue
    for p in pdf_files:
        if p in assigned_pdf: continue
        if doi in pdf_dois[p] or any(pd.startswith(doi) or doi.startswith(pd) for pd in pdf_dois[p]):
            matches[r["ref_no"]] = {"pdf": os.path.basename(p), "how": "doi", "score": 1.0}
            assigned_pdf.add(p); break

# Pass 2: global greedy on remaining
rem_refs = [r for r in records if matches[r["ref_no"]]["pdf"] is None]
pairs = []
for r in rem_refs:
    ttoks = toks(r.get("title"))
    surname = (r.get("first_author") or "").split()[0].lower().strip(",.") if r.get("first_author") else ""
    yr = str(r.get("year") or "")
    for p in pdf_files:
        if p in assigned_pdf: continue
        s = jacc(ttoks, pdf_titletoks[p])
        bonus = 0
        if surname and len(surname) > 2 and surname in pdf_head[p]: bonus += 0.15
        if yr and yr in os.path.basename(p): bonus += 0.05
        pairs.append((s + bonus, s, r["ref_no"], p))
pairs.sort(reverse=True)
done_refs = set()
for total, base, ref, p in pairs:
    if ref in done_refs or p in assigned_pdf: continue
    if total < 0.30: continue
    matches[ref] = {"pdf": os.path.basename(p), "how": "title", "score": round(total,3)}
    done_refs.add(ref); assigned_pdf.add(p)

json.dump(matches, open(OUT,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
matched = sum(1 for v in matches.values() if v["pdf"])
print("records:", len(records), "matched:", matched)
print("by doi:", sum(1 for v in matches.values() if v["how"]=="doi"),
      "by title:", sum(1 for v in matches.values() if v["how"]=="title"))
from collections import Counter
c = Counter(v["pdf"] for v in matches.values() if v["pdf"])
print("dups:", {k:n for k,n in c.items() if n>1})
un = [ref for ref,v in matches.items() if not v["pdf"]]
print("unmatched:", un)
# show low-confidence title matches for review
low = [(ref,v["score"],v["pdf"]) for ref,v in matches.items() if v["how"]=="title" and v["score"]<0.45]
print("low-conf title matches:", len(low))
for ref,s,p in sorted(low):
    print("  ref",ref,s,p[:70])
