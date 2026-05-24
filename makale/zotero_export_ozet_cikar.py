import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import pandas as pd


BASE = Path("Zotero Export")
RDF = BASE / "Abdomen2.rdf"
OUT_XLSX = Path("Zotero_Export_makale_uygun_tek_tek_ozet.xlsx")
OUT_MD = Path("Zotero_Export_kontrol_ve_ozet_raporu.md")

NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "z": "http://www.zotero.org/namespaces/export#",
    "dcterms": "http://purl.org/dc/terms/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "bib": "http://purl.org/net/biblio#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "link": "http://purl.org/rss/1.0/modules/link/",
}


PATHOLOGY_PATTERNS = [
    ("Abdominal aort patolojisi", r"\baortic\b|aneurysm|dissection|aaa|tbad|endoleak|ev ar|aorta"),
    ("Ürolitiyazis/Nefrolitiyazis", r"urolithiasis|nephrolithiasis|kidney stone|renal calcul|ureteral calcul|urinary stone|stone"),
    ("Akut pankreatit", r"pancreatitis|pancreatic necrosis|peripancreatic|pancreas"),
    ("Akut apandisit", r"appendicitis|appendix"),
    ("Akut kolesistit/safra kesesi", r"cholecystitis|gallbladder|gallstone"),
    ("Akut divertikülit", r"diverticulitis|sigmoid colon|colon carcinoma"),
]

TASK_PATTERNS = [
    ("Bölütleme", r"segmentation|segment|delineation|contour|lumen|volume"),
    ("Saptama", r"detection|detect|screening|triage|localization|localisation"),
    ("Sınıflandırma/Tanı", r"classification|classify|diagnos|differentiat|distinguish"),
    ("Öngörü/Prognoz", r"predict|prediction|prognos|severity|progression|outcome|risk|recurrence|success"),
    ("Ölçüm/Nicel analiz", r"measurement|quantification|diameter|apposition|geometry|scoring"),
]

MODEL_PATTERNS = [
    ("Transformer/Vision Transformer", r"transformer|vit|swin"),
    ("U-Net/nnU-Net", r"u-net|unet|nnu-net|nnU-Net"),
    ("CNN/Derin öğrenme", r"cnn|convolution|deep learning|neural network|yolo|densenet|efficientnet|ghostnet"),
    ("Radyomik + MÖ", r"radiomic|random forest|support vector|xgboost|logistic|nomogram|machine learning"),
    ("SAM/Temel model", r"\bSAM\b|MedSAM|foundation model|segment anything"),
    ("GAN", r"generative adversarial|gan"),
]

MODALITY_PATTERNS = [
    ("BT/CT", r"\bct\b|computed tomography|tomography"),
    ("BT anjiyografi/CTA", r"\bcta\b|computed tomography angiography"),
    ("Kontrastsız BT/NCCT", r"non-contrast|noncontrast|unenhanced|ncct"),
    ("Kontrastlı BT/CECT", r"contrast-enhanced|enhanced ct|cect"),
    ("MRI + BT", r"\bmri\b|magnetic resonance"),
]

PATHOLOGY_CODES = {
    "AAA": "Abdominal aort patolojisi",
    "URO": "Ürolitiyazis/Nefrolitiyazis",
    "PANC": "Akut pankreatit",
    "PAN": "Akut pankreatit",
    "APP": "Akut apandisit",
    "CHOLE": "Akut kolesistit/safra kesesi",
    "CHO": "Akut kolesistit/safra kesesi",
    "DIV": "Akut divertikülit",
    "MIX": "Birden fazla hedef patoloji",
}

TASK_CODES = {
    "DET": "Saptama",
    "CLS": "Sınıflandırma/Tanı",
    "SEG": "Bölütleme",
    "LOC": "Lokalizasyon",
    "PRED": "Öngörü/Prognoz",
    "CAD": "Karar desteği",
    "TRIAGE": "Triyaj",
}

MODEL_CODES = {
    "CNN_2D": "2B CNN",
    "CNN_3D": "3B CNN",
    "CNN_GENERIC": "CNN/Derin öğrenme",
    "DETECTION_MODEL": "Saptama modeli",
    "SEGMENTATION_MODEL": "Bölütleme modeli",
    "CLASSICAL_ML": "Klasik makine öğrenmesi",
    "RADIOMICS": "Radyomik",
    "RADIOMICS_ML": "Radyomik + makine öğrenmesi",
    "TRANSFORMER": "Transformer",
    "VIT": "Vision Transformer",
    "UNET": "U-Net",
    "NNUNET": "nnU-Net",
    "SAM_FAMILY": "SAM/MedSAM ailesi",
    "MULTIMODAL_LLM": "Çok modlu model/LLM",
    "UNCLEAR": "Belirsiz",
    "HYBRID": "Hibrit model",
    "DL": "Derin öğrenme",
}

MANUAL_OVERRIDES = {
    "10.3390/ai7020057": {
        "Görev türü": "Sınıflandırma/Tanı; Öngörü/Prognoz",
        "Model/yöntem ailesi": "3B CNN/ResNet",
        "Görüntüleme": "BT anjiyografi/CTA",
        "Makaleye uygun kısa özet": (
            "Bu çalışma, EVAR sonrası tip II endoleak gelişimi ve klinik şiddetini "
            "preoperatif CTA hacimlerinden öngörmek için uçtan uca 3B CNN/ResNet tabanlı "
            "bir sınıflandırma modeli geliştirmiştir. 277 hastalık tek merkezli retrospektif "
            "kohortta model, bağımsız 30 hastalık test setinde üç sınıfı (T2EL yok, benign T2EL, "
            "malign T2EL) ayırmış; genel doğruluk %76,7, makro F1 0,77 ve makro AUC 0,93 olarak "
            "bildirilmiştir. Makalenin sentezinde AAA/EVAR alt başlığı altında CTA tabanlı "
            "3B derin öğrenme ile risk sınıflandırması/öngörü örneği olarak kodlanmalıdır."
        ),
        "Kontrol notu": (
            "Başlıktaki 'distinguish' ve yöntem-sonuç bölümleri sınıflandırma/öngörü görevini "
            "gösterir; çalışma manuel bölütleme veya segmentasyon çıktısı üretmez."
        ),
    }
}


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def first_match(text, patterns, default="Belirtilmemiş/karma"):
    for label, pattern in patterns:
        if re.search(pattern, text, flags=re.I):
            return label
    return default


def all_matches(text, patterns):
    return "; ".join(label for label, pattern in patterns if re.search(pattern, text, flags=re.I)) or "Belirtilmemiş"


def first_sentences(text, n=2):
    parts = re.split(r"(?<=[.!?])\s+", clean(text))
    return " ".join(parts[:n])


def authors(elem):
    out = []
    for li in elem.findall(".//bib:authors/rdf:Seq/rdf:li", NS):
        surname = clean(li.findtext(".//foaf:surname", default="", namespaces=NS))
        given = clean(li.findtext(".//foaf:givenName", default="", namespaces=NS))
        name = clean(f"{surname} {given}")
        if name:
            out.append(name)
    return out


def identifiers(elem):
    vals = []
    about = elem.attrib.get(f"{{{NS['rdf']}}}about", "")
    if about:
        vals.append(about)
    for ident in elem.findall("dc:identifier", NS):
        vals.append(clean("".join(ident.itertext())))
    joined = " | ".join(v for v in vals if v)
    doi = ""
    doi_match = re.search(r"10\.\d{4,9}/[^\s|]+", joined, flags=re.I)
    if doi_match:
        doi = doi_match.group(0).rstrip(".,;")
    return joined, doi


def likely_attachment(title, attachment_paths):
    title_words = set(re.findall(r"[a-z0-9]{4,}", title.lower()))
    if not title_words:
        return ""
    best = ("", 0)
    for path in attachment_paths:
        words = set(re.findall(r"[a-z0-9]{4,}", path.name.lower()))
        score = len(title_words & words)
        if score > best[1]:
            best = (str(path), score)
    return best[0] if best[1] >= 3 else ""


def relevance_note(pathology, task, model):
    bits = []
    if pathology != "Belirtilmemiş/karma":
        bits.append(f"{pathology} alt başlığı")
    if task != "Belirtilmemiş/karma":
        bits.append(f"{task.lower()} görevi")
    if model != "Belirtilmemiş/karma":
        bits.append(f"{model} yaklaşımı")
    return ", ".join(bits) + " için sentezde kullanılabilir." if bits else "Kapsam uygunluğu manuel tam metinle kontrol edilmeli."


def parse_note(text):
    note = clean(re.sub(r"<[^>]+>", " ", text or ""))
    fields = {}
    for part in note.split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            fields[clean(key).lower()] = clean(value)
    return fields


def decode_list(value, mapping):
    codes = [clean(x) for x in re.split(r"[,/]", value or "") if clean(x)]
    labels = [mapping.get(code, code) for code in codes]
    return "; ".join(labels)


def main():
    root = ET.parse(RDF).getroot()
    attachment_paths = [p for p in (BASE / "files").rglob("*") if p.is_file()]
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
        memo_text = ""
        memo_ref = elem.find("dcterms:isReferencedBy", NS)
        if memo_ref is not None:
            memo_elem = by_about.get(memo_ref.attrib.get(f"{{{NS['rdf']}}}resource", ""))
            if memo_elem is not None:
                memo_text = clean(" ".join(memo_elem.itertext()))
        note_fields = parse_note(memo_text)

        date = clean(elem.findtext("dc:date", default="", namespaces=NS))
        year = re.search(r"\d{4}", date)
        auth = authors(elem)
        ident, doi = identifiers(elem)
        haystack = f"{title} {abstract}"
        coded_pathology = PATHOLOGY_CODES.get(note_fields.get("primary pathology", ""))
        coded_tasks = decode_list(note_fields.get("task type", ""), TASK_CODES)
        coded_models = decode_list(note_fields.get("model family", ""), MODEL_CODES)
        pathology = coded_pathology or first_match(haystack, PATHOLOGY_PATTERNS)
        tasks = coded_tasks or all_matches(haystack, TASK_PATTERNS)
        primary_task = tasks.split("; ")[0] if tasks and tasks != "Belirtilmemiş" else first_match(haystack, TASK_PATTERNS)
        models = coded_models or all_matches(haystack, MODEL_PATTERNS)
        primary_model = models.split("; ")[0] if models and models != "Belirtilmemiş" else first_match(haystack, MODEL_PATTERNS)
        modalities = all_matches(haystack, MODALITY_PATTERNS)
        link_paths = []
        for link_elem in elem.findall("link:link", NS):
            ref = link_elem.attrib.get(f"{{{NS['rdf']}}}resource", "")
            attach_elem = by_about.get(ref)
            if attach_elem is not None:
                path_elem = attach_elem.find("z:path", NS)
                if path_elem is not None:
                    rel_path = path_elem.attrib.get(f"{{{NS['rdf']}}}resource", "")
                    if rel_path:
                        link_paths.append(str(BASE / rel_path))
        attachment = "; ".join(link_paths)

        records.append(
            {
                "No": len(records) + 1,
                "Yıl": year.group(0) if year else date,
                "Yazar": auth[0] if auth else "",
                "Yazarlar": "; ".join(auth),
                "Başlık": title,
                "Yayın türü": item_type,
                "DOI": doi,
                "Patoloji": pathology,
                "Görev türü": tasks,
                "Model/yöntem ailesi": models,
                "Görüntüleme": modalities,
                "Study ID": note_fields.get("study id", ""),
                "Vancouver no": note_fields.get("vancouver no", ""),
                "Harici doğrulama": note_fields.get("external validation", ""),
                "Makaleye uygun kısa özet": (
                    f"Bu çalışma {pathology} bağlamında {modalities.lower()} verileriyle "
                    f"{primary_task.lower()} odaklı {primary_model.lower()} yaklaşımını değerlendirir. "
                    f"{relevance_note(pathology, primary_task, primary_model)}"
                ),
                "Zotero özetinden ana bilgi": first_sentences(abstract, 2),
                "Tam Zotero özeti": abstract,
                "RDF ek dosya": attachment,
                "Muhtemel ek dosya (dosya adına göre)": "" if attachment else likely_attachment(title, attachment_paths),
                "Zotero notu": memo_text,
                "Kontrol notu": "",
                "Tanımlayıcılar": ident,
            }
        )

        override = MANUAL_OVERRIDES.get(doi)
        if override:
            records[-1].update(override)

    df = pd.DataFrame(records)
    out_xlsx = OUT_XLSX
    try:
        test_handle = out_xlsx.open("ab")
        test_handle.close()
    except PermissionError:
        out_xlsx = OUT_XLSX.with_name(OUT_XLSX.stem + "_v2.xlsx")

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Tek tek ozet")
        summary = pd.DataFrame(
            {
                "Ölçüt": [
                    "Ana kayıt sayısı",
                    "Ek dosya sayısı",
                    "PDF sayısı",
                    "HTML sayısı",
                    "Özet alanı dolu kayıt",
                    "DOI bulunan kayıt",
                ],
                "Değer": [
                    len(df),
                    len(attachment_paths),
                    sum(p.suffix.lower() == ".pdf" for p in attachment_paths),
                    sum(p.suffix.lower() == ".html" for p in attachment_paths),
                    int(df["Tam Zotero özeti"].astype(bool).sum()),
                    int(df["DOI"].astype(bool).sum()),
                ],
            }
        )
        summary.to_excel(writer, index=False, sheet_name="Kontrol")
        pd.DataFrame(Counter(df["Patoloji"]).most_common(), columns=["Patoloji", "Sayı"]).to_excel(
            writer, index=False, sheet_name="Patoloji dağılımı"
        )

    pathology_counts = Counter(df["Patoloji"])
    year_counts = Counter(df["Yıl"])
    lines = [
        "# Zotero Export Kontrol ve Tek Tek Özet Raporu",
        "",
        f"- Ana bibliyografik kayıt: {len(df)}",
        f"- Ek dosya: {len(attachment_paths)} ({sum(p.suffix.lower() == '.pdf' for p in attachment_paths)} PDF, {sum(p.suffix.lower() == '.html' for p in attachment_paths)} HTML)",
        f"- Özeti dolu kayıt: {int(df['Tam Zotero özeti'].astype(bool).sum())}",
        f"- DOI bulunan kayıt: {int(df['DOI'].astype(bool).sum())}",
        "",
        "## Yıllara Göre Dağılım",
        "",
    ]
    for year, count in sorted(year_counts.items(), reverse=True):
        lines.append(f"- {year}: {count}")
    lines += ["", "## Patolojiye Göre Dağılım", ""]
    for pathology, count in pathology_counts.most_common():
        lines.append(f"- {pathology}: {count}")
    lines += ["", "## İlk 20 Kayıt İçin Örnek Özet", ""]
    for _, row in df.head(20).iterrows():
        lines.append(f"### {row['No']}. {row['Başlık']}")
        lines.append(f"- Yıl/Yazar: {row['Yıl']} / {row['Yazar']}")
        lines.append(f"- Sınıflama: {row['Patoloji']} | {row['Görev türü']} | {row['Model/yöntem ailesi']}")
        lines.append(f"- Makaleye uygun özet: {row['Makaleye uygun kısa özet']}")
        lines.append(f"- Ana bilgi: {row['Zotero özetinden ana bilgi']}")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Yazıldı: {out_xlsx.resolve()}")
    print(f"Yazıldı: {OUT_MD.resolve()}")


if __name__ == "__main__":
    main()
