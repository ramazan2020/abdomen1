import json
import re
from pathlib import Path

import pandas as pd


BASE = Path(".")
OUT_DIR = BASE / "zotero_import"
OUT_DIR.mkdir(exist_ok=True)

FINAL_XLSX = BASE / "234_makale_nihai_dahil_ozet.xlsx"
MAPPING_JSON = BASE / "search_results" / "06_citations" / "citation_mapping_v3.json"


def clean_value(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    text = re.sub(r"\s+", " ", text)
    return fix_mojibake(text)


def fix_mojibake(text):
    markers = ("Ã", "Ä", "Å", "Î", "Ð", "Ĺ", "œ", "Ÿ", "Â", "â")
    if not any(marker in text for marker in markers):
        return text
    for encoding in ("cp1252", "cp1254"):
        try:
            fixed = text.encode(encoding).decode("utf-8")
        except UnicodeError:
            continue
        if score_mojibake(fixed) < score_mojibake(text):
            text = fixed
    return text


def score_mojibake(text):
    return sum(text.count(marker) for marker in ("Ã", "Ä", "Å", "Î", "Ð", "Ĺ", "œ", "Ÿ", "�"))


def ris_escape(text):
    return clean_value(text).replace("\n", " ").replace("\r", " ")


def bib_escape(text):
    text = clean_value(text)
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def make_key(raw_key, used, fallback_author, year, number):
    key = clean_value(raw_key)
    if not key:
        base_author = re.sub(r"[^A-Za-z0-9]+", "", clean_value(fallback_author).split()[0].lower())
        key = f"{base_author or 'study'}{year or 'nd'}_{number}"
    key = re.sub(r"[^A-Za-z0-9_:-]+", "_", key)
    original = key
    suffix = 2
    while key in used:
        key = f"{original}_{suffix}"
        suffix += 1
    used.add(key)
    return key


def split_authors_from_ieee(citation, title):
    citation = clean_value(citation)
    title = clean_value(title)
    if not citation:
        return []
    text = re.sub(r"^\[\d+\]\s*", "", citation)
    marker = f', "{title},"'
    if marker in text:
        authors_part = text.split(marker, 1)[0]
    elif ',"' in text:
        authors_part = text.split(',"', 1)[0]
    else:
        authors_part = text.split('",', 1)[0]
    authors_part = re.sub(r"\bet al\.?,?$", "", authors_part, flags=re.I).strip(" ,.")
    pieces = [p.strip(" ,.") for p in re.split(r",|\band\b", authors_part) if p.strip(" ,.")]
    return [a for a in pieces if a and a.lower() != "et al"]


def infer_ris_type(journal):
    j = clean_value(journal).lower()
    if any(word in j for word in ("conference", "proceedings", "symposium", "workshop", "spie", "ieee")):
        return "CONF"
    if any(word in j for word in ("lecture notes", "adv exp med biol", "book", "computational intelligence in healthcare")):
        return "CHAP"
    return "JOUR"


def load_records():
    final_df = pd.read_excel(FINAL_XLSX, sheet_name="234 nihai dahil")
    with MAPPING_JSON.open(encoding="utf-8") as f:
        mapping = json.load(f)
    mapping_by_num = {int(item["vancouver_num"]): item for item in mapping}

    records = []
    used_keys = set()
    for _, row in final_df.sort_values("vancouver_num").iterrows():
        number = int(row["vancouver_num"])
        mapped = mapping_by_num.get(number, {})
        title = clean_value(row.get("title")) or clean_value(mapped.get("title"))
        year = clean_value(row.get("year")) or clean_value(mapped.get("publication_year"))
        journal = clean_value(row.get("journal_or_conference"))
        doi = clean_value(row.get("doi")) or clean_value(mapped.get("doi"))
        pmid = clean_value(mapped.get("pmid"))
        authors = split_authors_from_ieee(mapped.get("ieee_citation"), title)
        if not authors:
            authors = [clean_value(row.get("first_author"))]
        abstract = clean_value(row.get("source_abstract_excerpt"))
        note_parts = [
            f"Vancouver no: {number}",
            f"Study ID: {clean_value(row.get('study_id'))}",
            f"Primary pathology: {clean_value(row.get('primary_pathology'))}",
            f"Task type: {clean_value(row.get('task_type'))}",
            f"Model family: {clean_value(row.get('model_family'))}",
            f"External validation: {clean_value(row.get('external_validation'))}",
        ]
        key = make_key(mapped.get("bibtex_key"), used_keys, row.get("first_author"), year, number)
        records.append(
            {
                "number": number,
                "key": key,
                "type": infer_ris_type(journal),
                "authors": authors,
                "title": title,
                "journal": journal,
                "year": year,
                "doi": doi,
                "pmid": pmid,
                "abstract": abstract,
                "keywords": [
                    clean_value(row.get("primary_pathology")),
                    clean_value(row.get("task_type")),
                    clean_value(row.get("model_family")),
                    clean_value(row.get("imaging_modality")),
                ],
                "note": "; ".join(part for part in note_parts if not part.endswith(": ")),
            }
        )
    return records


def write_ris(records):
    lines = []
    for rec in records:
        lines.append(f"TY  - {rec['type']}")
        lines.append(f"ID  - {rec['key']}")
        for author in rec["authors"]:
            lines.append(f"AU  - {ris_escape(author)}")
        lines.append(f"TI  - {ris_escape(rec['title'])}")
        if rec["journal"]:
            lines.append(f"T2  - {ris_escape(rec['journal'])}")
            lines.append(f"JO  - {ris_escape(rec['journal'])}")
        if rec["year"]:
            lines.append(f"PY  - {ris_escape(rec['year'])}")
        if rec["doi"]:
            lines.append(f"DO  - {ris_escape(rec['doi'])}")
            lines.append(f"UR  - https://doi.org/{ris_escape(rec['doi'])}")
        if rec["pmid"]:
            lines.append(f"AN  - {ris_escape(rec['pmid'])}")
        if rec["abstract"]:
            lines.append(f"AB  - {ris_escape(rec['abstract'])}")
        for keyword in rec["keywords"]:
            if keyword:
                lines.append(f"KW  - {ris_escape(keyword)}")
        lines.append(f"N1  - {ris_escape(rec['note'])}")
        lines.append("ER  -")
        lines.append("")
    path = OUT_DIR / "234_makale_zotero_import.ris"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_bibtex(records):
    chunks = []
    for rec in records:
        entry_type = "inproceedings" if rec["type"] == "CONF" else "article"
        fields = [
            ("author", " and ".join(rec["authors"])),
            ("title", rec["title"]),
            ("journal", rec["journal"]),
            ("year", rec["year"]),
            ("doi", rec["doi"]),
            ("url", f"https://doi.org/{rec['doi']}" if rec["doi"] else ""),
            ("abstract", rec["abstract"]),
            ("keywords", "; ".join(k for k in rec["keywords"] if k)),
            ("note", rec["note"]),
        ]
        body = [f"@{entry_type}{{{rec['key']},"]
        for name, value in fields:
            if clean_value(value):
                body.append(f"  {name} = {{{bib_escape(value)}}},")
        body.append("}")
        chunks.append("\n".join(body))
    path = OUT_DIR / "234_makale_zotero_import.bib"
    path.write_text("\n\n".join(chunks) + "\n", encoding="utf-8")
    return path


def write_checklist(records):
    rows = ["vancouver_num,key,year,title,doi,journal"]
    for rec in records:
        values = [
            rec["number"],
            rec["key"],
            rec["year"],
            rec["title"],
            rec["doi"],
            rec["journal"],
        ]
        rows.append(",".join('"' + str(v).replace('"', '""') + '"' for v in values))
    path = OUT_DIR / "234_makale_zotero_kontrol_listesi.csv"
    path.write_text("\n".join(rows), encoding="utf-8-sig")
    return path


def main():
    records = load_records()
    ris = write_ris(records)
    bib = write_bibtex(records)
    csv = write_checklist(records)
    print(f"records={len(records)}")
    print(ris.resolve())
    print(bib.resolve())
    print(csv.resolve())


if __name__ == "__main__":
    main()
