import re
import shutil
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urljoin

import pandas as pd
import requests


ROOT = Path(".")
SOURCE_XLSX = ROOT / "Zotero_Export_makale_uygun_tek_tek_ozet.xlsx"
MISSING_XLSX = ROOT / "PDF_olmayanlar_arastirma.xlsx"
OUT_DIR = ROOT / "Makaleler_PDF_Atif_Numarasina_Gore"
REPORT_XLSX = ROOT / "Makaleler_PDF_Atif_Numarasina_Gore_rapor.xlsx"
REPORT_MD = ROOT / "Makaleler_PDF_Atif_Numarasina_Gore_rapor.md"

KNOWN_LOCAL = {
    "10.3390/ai7020057": Path(r"C:\Users\ramazan.polat3\Desktop\ai-07-00057-v2.pdf"),
}


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def safe_name(value, max_len=150):
    value = clean_text(value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1F]', " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:max_len].rstrip(" .") or "baslik_yok"


def first_url(value):
    if isinstance(value, pd.Series):
        value = value.dropna().iloc[0] if not value.dropna().empty else ""
    text = clean_text(value)
    if not text or text.lower() == "nan":
        return ""
    return text.split(";")[0].strip()


def doi_url(doi):
    doi = clean_text(doi)
    return f"https://doi.org/{doi}" if doi and doi.lower() != "nan" else ""


def destination_name(row):
    vancouver = int(row["Vancouver no"]) if not pd.isna(row["Vancouver no"]) else int(row["No"])
    year = clean_text(row["Yıl"])
    author = safe_name(row["Yazar"], 35)
    title = safe_name(row["Başlık"], 115)
    return f"{vancouver:03d}_{year}_{author}_{title}.pdf"


def is_pdf(path):
    try:
        with open(path, "rb") as handle:
            return handle.read(5) == b"%PDF-"
    except Exception:
        return False


def copy_pdf(src, dst):
    src = Path(src)
    if not src.exists():
        return False, "kaynak dosya yok"
    if src.suffix.lower() != ".pdf":
        return False, "kaynak PDF değil"
    if not is_pdf(src):
        return False, "kaynak dosya PDF imzası taşımıyor"
    shutil.copy2(src, dst)
    return True, "yerel kopyalandı"


def download_pdf(url, dst):
    if not url:
        return False, "PDF linki yok"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; makale-pdf-archive/1.0)",
            "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
        }
        with requests.get(url, headers=headers, timeout=45, allow_redirects=True, stream=True) as response:
            if response.status_code >= 400:
                return False, f"HTTP {response.status_code}"
            content_type = response.headers.get("content-type", "").lower()
            data = response.content
            final_url = response.url
        if not data.startswith(b"%PDF-"):
            if "application/pdf" not in content_type:
                html = data.decode("utf-8", errors="ignore")
                discovered = discover_pdf_url(html, final_url)
                if discovered and discovered != url:
                    return download_pdf(discovered, dst)
                return False, f"PDF olmayan yanıt ({content_type or 'content-type yok'})"
        dst.write_bytes(data)
        if not is_pdf(dst):
            dst.unlink(missing_ok=True)
            return False, "indirilen dosya PDF değil"
        return True, "indirildi"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def discover_pdf_url(html, base_url):
    patterns = [
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
        r'href=["\']([^"\']+/pdf(?:\?[^"\']*)?)["\']',
        r'href=["\']([^"\']+/pdf/)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I)
        if match:
            return urljoin(base_url, unquote(match.group(1).replace("&amp;", "&")))
    return ""


def main():
    OUT_DIR.mkdir(exist_ok=True)
    df = pd.read_excel(SOURCE_XLSX, sheet_name="Tek tek ozet")
    missing_meta = pd.DataFrame()
    if MISSING_XLSX.exists():
        missing_meta = pd.read_excel(MISSING_XLSX, sheet_name="PDF olmayanlar")
        missing_meta["DOI_key"] = missing_meta["DOI"].astype(str).str.lower()
        missing_meta = missing_meta.set_index("DOI_key", drop=False)

    rows = []
    for _, row in df.iterrows():
        doi = clean_text(row["DOI"]).lower()
        dst = OUT_DIR / destination_name(row)
        status = "eksik"
        source = ""
        note = ""

        local_candidates = []
        rdf_path = clean_text(row.get("RDF ek dosya", ""))
        if rdf_path and rdf_path.lower() != "nan":
            local_candidates.append(Path(rdf_path))
        known = KNOWN_LOCAL.get(doi)
        if known:
            local_candidates.append(known)

        for candidate in local_candidates:
            ok, msg = copy_pdf(candidate, dst)
            source = str(candidate)
            note = msg
            if ok:
                status = "kopyalandı"
                break

        if status == "eksik" and doi in missing_meta.index:
            meta_row = missing_meta.loc[doi]
            if isinstance(meta_row, pd.DataFrame):
                meta_row = meta_row.iloc[0]
            pdf_url = first_url(meta_row.get("Crossref PDF link", ""))
            if not pdf_url:
                pdf_url = first_url(meta_row.get("Crossref fulltext link", ""))
            if not pdf_url:
                pdf_url = doi_url(row["DOI"])
            if pdf_url:
                ok, msg = download_pdf(pdf_url, dst)
                source = pdf_url
                note = msg
                if ok:
                    status = "indirildi"

        rows.append(
            {
                "Vancouver no": row["Vancouver no"],
                "Study ID": row["Study ID"],
                "Başlık": row["Başlık"],
                "DOI": row["DOI"],
                "Durum": status,
                "Kaynak": source,
                "Not": note,
                "Hedef dosya": str(dst.resolve()) if dst.exists() else "",
            }
        )

    report = pd.DataFrame(rows)
    with pd.ExcelWriter(REPORT_XLSX, engine="openpyxl") as writer:
        report.to_excel(writer, index=False, sheet_name="Arsiv raporu")
        report[report["Durum"] == "eksik"].to_excel(writer, index=False, sheet_name="Eksik kalanlar")
        report["Durum"].value_counts().rename_axis("Durum").reset_index(name="Sayı").to_excel(
            writer, index=False, sheet_name="Ozet"
        )

    counts = report["Durum"].value_counts()
    lines = [
        "# Atıf Numarasına Göre PDF Arşivi Raporu",
        "",
        f"- Hedef klasör: `{OUT_DIR.resolve()}`",
        f"- Toplam makale kaydı: {len(report)}",
        f"- Yerelden kopyalanan: {int(counts.get('kopyalandı', 0))}",
        f"- İnternetten indirilen: {int(counts.get('indirildi', 0))}",
        f"- Eksik kalan: {int(counts.get('eksik', 0))}",
        "",
        "## Eksik Kalanlar",
        "",
    ]
    missing = report[report["Durum"] == "eksik"]
    if missing.empty:
        lines.append("- Eksik PDF kalmadı.")
    else:
        for _, item in missing.iterrows():
            lines.append(
                f"- V{item['Vancouver no']} / {item['Study ID']}: {item['Başlık']} | DOI: {item['DOI']} | Not: {item['Not']}"
            )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Klasör: {OUT_DIR.resolve()}")
    print(f"Rapor: {REPORT_XLSX.resolve()}")
    print(f"Rapor: {REPORT_MD.resolve()}")
    print(counts.to_string())


if __name__ == "__main__":
    main()
