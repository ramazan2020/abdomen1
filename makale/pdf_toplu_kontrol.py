import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from zotero_export_ozet_cikar import (
    BASE,
    NS,
    PATHOLOGY_CODES,
    TASK_CODES,
    MODEL_CODES,
    PATHOLOGY_PATTERNS,
    TASK_PATTERNS,
    MODEL_PATTERNS,
    MODALITY_PATTERNS,
    clean,
    parse_note,
    decode_list,
    first_match,
    all_matches,
    authors,
    identifiers,
)


OUT_XLSX = Path("PDF_toplu_kontrol_sonuclari.xlsx")
OUT_MD = Path("PDF_toplu_kontrol_raporu.md")
TEXT_DIR = Path("pdf_text_cache")

EXTRA_PDFS = [
    Path(r"C:\Users\ramazan.polat3\Desktop\ai-07-00057-v2.pdf"),
]


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def short(s, n=800):
    s = clean(s)
    return s[:n] + ("..." if len(s) > n else "")


def excel_safe(value):
    if isinstance(value, str):
        return ILLEGAL_CHARACTERS_RE.sub("", value)
    return value


def extract_pdf_text(path):
    cache_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem)[:120] + ".txt"
    cache_path = TEXT_DIR / cache_name
    if cache_path.exists():
        try:
            text = cache_path.read_text(encoding="utf-8", errors="ignore")
            return text, -1, ""
        except Exception:
            pass
    try:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
        return "\n".join(pages), len(reader.pages), ""
    except Exception as exc:
        return "", 0, f"{type(exc).__name__}: {exc}"


def abstract_from_text(text):
    m = re.search(r"\bAbstract\b[:\s]*(.*?)(?:\bKeywords?\b|\b1\.?\s+Introduction\b|\bIntroduction\b)", text, re.I | re.S)
    return clean(m.group(1)) if m else ""


def snippet_around(text, patterns, window=700):
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            start = max(0, m.start() - 120)
            end = min(len(text), m.end() + window)
            return clean(text[start:end])
    return ""


def detect_external_validation(text):
    t = norm(text)
    strong = [
        "external validation",
        "external test",
        "external cohort",
        "external dataset",
        "independent external",
        "multi center external",
        "multicenter external",
        "multi institution validation",
        "multi institutional validation",
    ]
    if any(x in t for x in strong):
        return "yes"
    if re.search(r"\bindependent (test|validation) (set|cohort|dataset)\b", t):
        return "independent_internal_or_unclear"
    return "no_or_not_reported"


def detect_open_science(text):
    t = norm(text)
    code_yes = any(x in t for x in ["github com", "source code", "code is available", "codes are available"])
    data_yes = any(x in t for x in ["publicly available", "data are available", "dataset is available", "zenodo", "figshare"])
    on_request = any(x in t for x in ["reasonable request", "upon request", "available on request"])
    return code_yes, data_yes, on_request


def build_records():
    root = ET.parse(BASE / "Abdomen2.rdf").getroot()
    by_about = {elem.attrib.get(f"{{{NS['rdf']}}}about", ""): elem for elem in root}
    records = []
    for elem in root:
        item_type = clean(elem.findtext("z:itemType", default="", namespaces=NS))
        if not item_type or item_type == "attachment":
            continue
        title = clean(elem.findtext("dc:title", default="", namespaces=NS))
        abstract = clean(
            elem.findtext("dcterms:abstract", default="", namespaces=NS)
            or elem.findtext("dc:description", default="", namespaces=NS)
        )
        date = clean(elem.findtext("dc:date", default="", namespaces=NS))
        year = re.search(r"\d{4}", date)
        ident, doi = identifiers(elem)
        memo_text = ""
        memo_ref = elem.find("dcterms:isReferencedBy", NS)
        if memo_ref is not None:
            memo_elem = by_about.get(memo_ref.attrib.get(f"{{{NS['rdf']}}}resource", ""))
            if memo_elem is not None:
                memo_text = clean(" ".join(memo_elem.itertext()))
        note_fields = parse_note(memo_text)

        link_paths = []
        for link_elem in elem.findall("link:link", NS):
            ref = link_elem.attrib.get(f"{{{NS['rdf']}}}resource", "")
            attach_elem = by_about.get(ref)
            if attach_elem is not None:
                path_elem = attach_elem.find("z:path", NS)
                if path_elem is not None:
                    rel_path = path_elem.attrib.get(f"{{{NS['rdf']}}}resource", "")
                    if rel_path:
                        link_paths.append(str((BASE / rel_path).resolve()))

        records.append(
            {
                "title": title,
                "title_norm": norm(title),
                "year": year.group(0) if year else date,
                "authors": "; ".join(authors(elem)),
                "doi": doi.lower(),
                "abstract": abstract,
                "study_id": note_fields.get("study id", ""),
                "vancouver_no": note_fields.get("vancouver no", ""),
                "z_pathology": PATHOLOGY_CODES.get(note_fields.get("primary pathology", ""), note_fields.get("primary pathology", "")),
                "z_tasks": decode_list(note_fields.get("task type", ""), TASK_CODES),
                "z_models": decode_list(note_fields.get("model family", ""), MODEL_CODES),
                "z_external": note_fields.get("external validation", ""),
                "attachments": link_paths,
                "memo": memo_text,
            }
        )
    return records


def match_record(pdf_path, text, records):
    abs_path = str(pdf_path.resolve())
    for rec in records:
        if abs_path in rec["attachments"]:
            return rec, 1.0, "RDF attachment"

    text_l = text.lower()
    for rec in records:
        if rec["doi"] and rec["doi"] in text_l:
            return rec, 0.98, "DOI in PDF"

    best = (None, 0.0, "")
    file_norm = norm(pdf_path.stem)
    first = norm(text[:6000])
    for rec in records:
        title_norm = rec["title_norm"]
        score_file = SequenceMatcher(None, title_norm, file_norm).ratio()
        score_text = 0.0
        if title_norm and title_norm[:80] in first:
            score_text = 0.95
        else:
            score_text = SequenceMatcher(None, title_norm[:180], first[:500]).ratio()
        score = max(score_file, score_text)
        if score > best[1]:
            best = (rec, score, "title/file fuzzy")
    if best[1] >= 0.52:
        return best
    return None, best[1], "unmatched"


def compare_sets(z_value, pdf_value):
    if not z_value or not pdf_value:
        return ""
    z = set(x.strip().lower() for x in str(z_value).split(";") if x.strip())
    p = set(x.strip().lower() for x in str(pdf_value).split(";") if x.strip())
    if not z or not p:
        return ""
    if z & p:
        return "uyumlu"
    return "uyumsuz"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    TEXT_DIR.mkdir(exist_ok=True)
    records = build_records()
    pdfs = sorted([p for p in (BASE / "files").rglob("*.pdf") if p.is_file()])
    for extra in EXTRA_PDFS:
        if extra.exists() and extra not in pdfs:
            pdfs.append(extra)

    rows = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] {pdf}")
        text, pages, error = extract_pdf_text(pdf)
        cache_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", pdf.stem)[:120] + ".txt"
        if text:
            (TEXT_DIR / cache_name).write_text(text, encoding="utf-8", errors="ignore")
        rec, score, method = match_record(pdf, text, records)
        pdf_abs = abstract_from_text(text)
        focused_hay = f"{rec['title'] if rec else ''} {rec['abstract'] if rec else ''} {pdf_abs}"
        full_hay = f"{text[:160000]} {rec['abstract'] if rec else ''}"
        pdf_pathology = first_match(focused_hay, PATHOLOGY_PATTERNS)
        pdf_tasks = all_matches(focused_hay, TASK_PATTERNS)
        pdf_models = all_matches(focused_hay, MODEL_PATTERNS)
        pdf_modality = all_matches(focused_hay, MODALITY_PATTERNS)
        pdf_external = detect_external_validation(full_hay)
        code_yes, data_yes, request_only = detect_open_science(full_hay)

        issue = []
        if error:
            issue.append("PDF metni çıkarılamadı")
        if rec is None:
            issue.append("Zotero kaydıyla eşleşmedi")
        else:
            if compare_sets(rec["z_pathology"], pdf_pathology) == "uyumsuz":
                issue.append("Patoloji kodu kontrol edilmeli")
            if compare_sets(rec["z_tasks"], pdf_tasks) == "uyumsuz":
                issue.append("Görev türü kontrol edilmeli")
            if rec["z_external"] == "yes" and pdf_external != "yes":
                issue.append("Harici doğrulama yes kodu şüpheli")
            if rec["doi"] == "10.3390/ai7020057":
                issue.append("NornirNet: SEG kaldırılmalı; harici doğrulama tek merkezli bağımsız test olarak yeniden kodlanmalı")

        rows.append(
            {
                "PDF": str(pdf),
                "Sayfa": pages,
                "Metin karakteri": len(text),
                "Eşleşme yöntemi": method,
                "Eşleşme skoru": round(score, 3),
                "Study ID": rec["study_id"] if rec else "",
                "Vancouver no": rec["vancouver_no"] if rec else "",
                "Başlık": rec["title"] if rec else "",
                "DOI": rec["doi"] if rec else "",
                "Zotero patoloji": rec["z_pathology"] if rec else "",
                "PDF patoloji sinyali": pdf_pathology,
                "Zotero görev": rec["z_tasks"] if rec else "",
                "PDF görev sinyali": pdf_tasks,
                "Zotero model": rec["z_models"] if rec else "",
                "PDF model sinyali": pdf_models,
                "PDF görüntüleme sinyali": pdf_modality,
                "Zotero harici doğrulama": rec["z_external"] if rec else "",
                "PDF harici doğrulama sinyali": pdf_external,
                "Kod paylaşımı sinyali": "yes" if code_yes else "no",
                "Veri paylaşımı sinyali": "yes" if data_yes else "no",
                "Talep üzerine paylaşım sinyali": "yes" if request_only else "no",
                "PDF abstract": short(pdf_abs, 1200),
                "Methods snippet": short(snippet_around(text, [r"\bMethods\b", r"\bMaterials and Methods\b", r"\bPatients\b"]), 1200),
                "Results snippet": short(snippet_around(text, [r"\bResults\b", r"\bPerformance\b", r"\bAUC\b"]), 1200),
                "Sorun/Not": "; ".join(issue),
                "Çıkarma hatası": error,
                "Metin cache": str((TEXT_DIR / cache_name).resolve()) if text else "",
            }
        )

    df = pd.DataFrame(rows)
    df = df.applymap(excel_safe)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="PDF kontrol")
        flagged = df[df["Sorun/Not"].astype(str).str.len() > 0]
        flagged.to_excel(writer, index=False, sheet_name="Hata adaylari")
        summary = pd.DataFrame(
            {
                "Ölçüt": [
                    "Taranan PDF",
                    "Metin çıkarılan PDF",
                    "Zotero ile eşleşen PDF",
                    "RDF attachment ile eşleşen",
                    "DOI ile eşleşen",
                    "Başlık/dosya adı ile eşleşen",
                    "Hata adayı satır",
                ],
                "Değer": [
                    len(df),
                    int((df["Metin karakteri"] > 0).sum()),
                    int(df["Study ID"].astype(bool).sum()),
                    int((df["Eşleşme yöntemi"] == "RDF attachment").sum()),
                    int((df["Eşleşme yöntemi"] == "DOI in PDF").sum()),
                    int((df["Eşleşme yöntemi"] == "title/file fuzzy").sum()),
                    len(flagged),
                ],
            }
        )
        summary.to_excel(writer, index=False, sheet_name="Özet")

    article_expected = {
        "Ürolitiyazis/Nefrolitiyazis": 95,
        "Abdominal aort patolojisi": 79,
        "Akut pankreatit": 33,
        "Akut apandisit": 14,
        "Akut kolesistit/safra kesesi": 5,
        "Akut divertikülit": 4,
        "Birden fazla hedef patoloji": 4,
    }
    zotero_counts = Counter(r["z_pathology"] for r in records)
    lines = [
        "# PDF Toplu Kontrol Raporu",
        "",
        f"- Taranan PDF: {len(df)}",
        f"- Metin çıkarılan PDF: {int((df['Metin karakteri'] > 0).sum())}",
        f"- Zotero kaydıyla eşleşen PDF: {int(df['Study ID'].astype(bool).sum())}",
        f"- Hata/uyarı adayı: {len(df[df['Sorun/Not'].astype(str).str.len() > 0])}",
        "",
        "## Makale Metniyle Sayı Karşılaştırması",
        "",
        "| Patoloji | Makaledeki sayı | Zotero kodlarından sayı | Fark |",
        "|---|---:|---:|---:|",
    ]
    for key, expected in article_expected.items():
        observed = zotero_counts.get(key, 0)
        lines.append(f"| {key} | {expected} | {observed} | {observed - expected:+d} |")

    lines += [
        "",
        "## Öncelikli Hata Adayları",
        "",
    ]
    flagged = df[df["Sorun/Not"].astype(str).str.len() > 0]
    for _, row in flagged.head(50).iterrows():
        lines.append(f"- V{row['Vancouver no']} / {row['Study ID']}: {row['Başlık'][:140]} -- {row['Sorun/Not']}")
    lines += [
        "",
        "## Genel Not",
        "",
        "Bu kontrol PDF metni ve Zotero notlarını otomatik karşılaştırır. Kesin revizyon gereken satırlar için tam metin manuel okunmalıdır; özellikle 'external validation' ifadesi bağımsız iç test seti ile gerçek dış/çok merkezli validasyon arasında ayrılmalıdır.",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Yazıldı: {OUT_XLSX.resolve()}")
    print(f"Yazıldı: {OUT_MD.resolve()}")


if __name__ == "__main__":
    main()
