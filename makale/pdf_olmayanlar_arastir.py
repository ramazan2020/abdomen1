import re
import time
from pathlib import Path

import pandas as pd
import requests


IN_XLSX = Path("Zotero_Export_makale_uygun_tek_tek_ozet.xlsx")
OUT_XLSX = Path("PDF_olmayanlar_arastirma.xlsx")
OUT_MD = Path("PDF_olmayanlar_arastirma_raporu.md")

OPEN_DOMAINS = [
    "mdpi.com",
    "frontiersin.org",
    "nature.com",
    "springeropen.com",
    "biomedcentral.com",
    "bmc",
    "jmIR".lower(),
    "plos.org",
    "scielo",
    "hindawi.com",
    "wiley.com",
]


def clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def crossref(doi):
    if not doi or str(doi).lower() == "nan":
        return {}
    url = f"https://api.crossref.org/works/{doi}"
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "makale-pdf-audit/1.0 (mailto:example@example.com)"})
        if r.status_code != 200:
            return {"crossref_status": r.status_code}
        msg = r.json().get("message", {})
        links = msg.get("link", []) or []
        fulltext_links = []
        pdf_links = []
        for link in links:
            u = link.get("URL", "")
            if not u:
                continue
            fulltext_links.append(u)
            if "pdf" in (link.get("content-type", "") + " " + u).lower():
                pdf_links.append(u)
        return {
            "crossref_status": 200,
            "publisher": clean(msg.get("publisher", "")),
            "container": "; ".join(msg.get("container-title", []) or []),
            "type": clean(msg.get("type", "")),
            "is_referenced_by_count": msg.get("is-referenced-by-count", ""),
            "license": "; ".join(x.get("URL", "") for x in msg.get("license", []) or []),
            "resource_url": (msg.get("resource") or {}).get("primary", {}).get("URL", ""),
            "fulltext_links": "; ".join(fulltext_links),
            "pdf_links": "; ".join(pdf_links),
        }
    except Exception as exc:
        return {"crossref_status": f"ERR {type(exc).__name__}: {exc}"}


def doi_url(doi):
    return f"https://doi.org/{doi}" if doi and str(doi).lower() != "nan" else ""


def access_guess(row):
    text = " ".join(
        str(row.get(c, "")) for c in ["DOI URL", "Yayıncı", "Dergi/Kitap", "Crossref kaynak URL", "Crossref fulltext link", "Crossref PDF link"]
    ).lower()
    if row.get("Crossref PDF link"):
        return "PDF linki Crossref'te var"
    if any(domain in text for domain in OPEN_DOMAINS):
        return "Açık erişim olası; yayıncı sayfası kontrol edilmeli"
    if "springer" in text or "elsevier" in text or "wiley" in text or "ieee" in text:
        return "Yayıncı sayfası/paywall olası; özet metadata ile kodlanabilir"
    return "DOI sayfası manuel kontrol edilmeli"


def priority(row):
    title = str(row["Başlık"]).lower()
    item_type = str(row["Yayın türü"]).lower()
    notes = []
    if "review" in title or "progress in the application" in title or "modern approaches" in title:
        notes.append("Derleme/uygunluk dışı olabilir")
    if "ultrasound" in title or "endoscopic ultrasound" in title or "mri and ct" in title or "ct-radiography" in title:
        notes.append("BT ana modalitesi kontrol edilmeli")
    if item_type in ["booksection", "book section", "conferencepaper", "conference paper"]:
        notes.append("Konferans/kitap bölümü tam metin türü kontrol edilmeli")
    if str(row["Harici doğrulama"]).lower() == "yes":
        notes.append("Harici doğrulama tam metinle doğrulanmalı")
    return "; ".join(notes) or "Düşük/orta öncelik"


def main():
    df = pd.read_excel(IN_XLSX, sheet_name="Tek tek ozet")
    missing = df[df["RDF ek dosya"].isna()].copy()
    rows = []
    for i, (_, row) in enumerate(missing.iterrows(), 1):
        doi = clean(row["DOI"])
        print(f"[{i}/{len(missing)}] {doi} {str(row['Başlık'])[:80]}")
        meta = crossref(doi)
        out = {
            "No": row["No"],
            "Vancouver no": row["Vancouver no"],
            "Study ID": row["Study ID"],
            "Yıl": row["Yıl"],
            "Yazar": row["Yazar"],
            "Başlık": row["Başlık"],
            "DOI": doi,
            "DOI URL": doi_url(doi),
            "Patoloji": row["Patoloji"],
            "Görev türü": row["Görev türü"],
            "Model/yöntem ailesi": row["Model/yöntem ailesi"],
            "Harici doğrulama": row["Harici doğrulama"],
            "Makaleye uygun kısa özet": row["Makaleye uygun kısa özet"],
            "Zotero özetinden ana bilgi": row["Zotero özetinden ana bilgi"],
            "Tam Zotero özeti": row["Tam Zotero özeti"],
            "Öncelikli kontrol notu": priority(row),
            "Crossref durum": meta.get("crossref_status", ""),
            "Yayıncı": meta.get("publisher", ""),
            "Dergi/Kitap": meta.get("container", ""),
            "Crossref tür": meta.get("type", ""),
            "Atıf sayısı Crossref": meta.get("is_referenced_by_count", ""),
            "Lisans": meta.get("license", ""),
            "Crossref kaynak URL": meta.get("resource_url", ""),
            "Crossref fulltext link": meta.get("fulltext_links", ""),
            "Crossref PDF link": meta.get("pdf_links", ""),
        }
        out["Erişim tahmini"] = access_guess(out)
        rows.append(out)
        time.sleep(0.05)

    out_df = pd.DataFrame(rows)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        out_df.to_excel(writer, index=False, sheet_name="PDF olmayanlar")
        out_df[out_df["Öncelikli kontrol notu"] != "Düşük/orta öncelik"].to_excel(
            writer, index=False, sheet_name="Oncelikli kontrol"
        )
        summary = pd.DataFrame(
            {
                "Ölçüt": [
                    "PDF olmayan kayıt",
                    "DOI bulunan",
                    "Crossref 200",
                    "Crossref PDF linki bulunan",
                    "Öncelikli manuel kontrol",
                ],
                "Değer": [
                    len(out_df),
                    int(out_df["DOI"].astype(bool).sum()),
                    int((out_df["Crossref durum"] == 200).sum()),
                    int(out_df["Crossref PDF link"].astype(bool).sum()),
                    int((out_df["Öncelikli kontrol notu"] != "Düşük/orta öncelik").sum()),
                ],
            }
        )
        summary.to_excel(writer, index=False, sheet_name="Özet")

    lines = [
        "# PDF Olmayanlar Araştırma Raporu",
        "",
        f"- PDF eki olmayan ana kayıt: {len(out_df)}",
        f"- DOI bulunan: {int(out_df['DOI'].astype(bool).sum())}",
        f"- Crossref metadata bulunan: {int((out_df['Crossref durum'] == 200).sum())}",
        f"- Crossref PDF linki bulunan: {int(out_df['Crossref PDF link'].astype(bool).sum())}",
        f"- Öncelikli manuel kontrol adayı: {int((out_df['Öncelikli kontrol notu'] != 'Düşük/orta öncelik').sum())}",
        "",
        "## Makale Açısından Öncelikli Kontrol Adayları",
        "",
    ]
    for _, r in out_df[out_df["Öncelikli kontrol notu"] != "Düşük/orta öncelik"].head(80).iterrows():
        lines.append(
            f"- V{r['Vancouver no']} / {r['Study ID']}: {r['Başlık']} -- {r['Öncelikli kontrol notu']}"
        )
    lines += [
        "",
        "## Not",
        "",
        "Bu tablo PDF eki olmayan çalışmalar için DOI/Crossref metadata ve Zotero özetlerinden hazırlanmıştır. Tam metin erişimi olmayan kayıtlarda nihai karar için yayıncı sayfası veya kurumsal erişimle tam metin kontrolü gerekir.",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Yazıldı: {OUT_XLSX.resolve()}")
    print(f"Yazıldı: {OUT_MD.resolve()}")


if __name__ == "__main__":
    main()
