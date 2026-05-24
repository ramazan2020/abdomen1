# İnceleme Makalesi Sentez Planı (v2)
## "Karın Ağrısı için BT'de YZ Uygulamaları" (2021–2026)

**Plan tarihi:** 14 Mayıs 2026  
**Hazırlayan:** Cowork (Claude)  
**Hedef:** Dahil edilen ~120–300 makaleyi hem **kaynakçaya ekle** hem **makalenin Bulgular + Tartışma bölümlerine atıflarla işle** — sonuç: gerçek bir scoping/inceleme makalesi.

---

## 0. İlkeler (sözleşme)

1. **Kaynakçadaki her referans makalede atıf alır.** (Yetim atıf yok.)
2. **Makaledeki her sayısal iddia veya çalışma özelliği bir veya daha fazla referansla desteklenir.**
3. Atıf stili: **Vancouver** (numaralı, görünme sırasına göre).
4. Atıflar kümeli kullanılır: "Apandisitte 3D CNN modelleri öne çıkmaktadır [12–18]."
5. Mimari/görev/patoloji **gerçek sayımları** kullanılır (smart extraction + opsiyonel manuel teyit).
6. Şu an v2 makale yapısı korunur; sadece **içerik gerçek atıflarla yeniden doldurulur**.

---

## 1. Mevcut durum (referans)

```text
Toplam ham kayıt          : 2.198  (PubMed 467 + arXiv 25 + IEEE 200 + Scopus 1.005 + WoS 501)
Tekilleştirme sonrası    : 1.203
T/A include + maybe       : 1.092
Smart filter likely_include: 305  ← bu, "dahil edilen çalışmalar" havuzu
Smart filter needs_review : 683
Smart filter likely_exclude: 104  (review/perspective tipinde)
PMC açık erişim          : 259
DOI linki var             : 1.065
```

---

## 2. Aşamalı çalışma planı

### Aşama A — Dahil edilen makale havuzunu netleştir (30 dk)

**Karar:** Hangi alt küme makalenin "data"sı olacak?

| Seçenek | Sayı | Avantaj | Dezavantaj |
|---|---:|---|---|
| **A1.** 305 likely_include | 305 | Hızlı, daha temiz | Bazı uygun çalışmalar atlanır |
| **A2.** 1.092 (include+maybe) | 1.092 | Maksimum kapsayıcılık | Çok fazla "noise" |
| **A3.** 305 likely_include + manuel ekleme | ~350 | Hibrit denge | Manuel iş gerekir |
| **A4. (Recommended)** 305 + needs_review'dan smart filter ikinci tur | ~450 | Otomatik dengeli | İkinci script çalıştırma |

**Çıktı:** `included_studies_final.xlsx` (N satır × tüm meta-veri)

---

### Aşama B — Her dahil edilen makaleden otomatik veri çıkarımı (2 saat)

Smart extraction: title + abstract metni üzerinde regex/keyword arama.

#### B.1. Çıkarılan alanlar (35 alan, plan v1'deki Aşama 5 ile aynı)

```text
study_id              (S_001, S_002, ...)
citation_key          (vancouver: [1], [2], ...; bibtex: liang2024_app_3dcnn)
first_author          (regex'le çıkar)
publication_year
title
abstract              (zaten var)
doi, pmid, pmcid, arxiv_id
journal_or_conference
country               (yazar affiliation'undan — Scopus/IEEE'de var)
document_type
---- Klinik bağlam ----
target_pathology      (APP/CHO/PAN/URO/DIV/AAA/MIX) ← regex
adult_or_pediatric    ← regex ("pediatric|child|infant")
clinical_use_case     ← regex
---- Veri seti ----
imaging_modality      (CT/NCCT/CTA/dual-energy) ← regex
public_dataset_yes_no ← regex (KiTS, MSD, Pancreas-CT, Decathlon)
single_center_or_multicenter ← regex
number_of_patients    ← regex r"(\d+)\s+(patients|cases|subjects)"
adult_or_pediatric    
---- Model ----
task_type             (DET/CLS/SEG/PRED/MULTI) ← regex
model_family          (CNN/UNET/NNUNET/TRANSFORMER/RADIOMICS_ML/HYBRID) ← regex
specific_architecture (ResNet50, nnU-Net, Swin-B, MedSAM...) ← regex
---- Performans ----
auc                   ← regex r"AUC\s*(of|=)?\s*0?\.\d+"
accuracy, sensitivity, specificity, f1, dice, iou, map
---- Kanıt kalitesi ----
external_validation_yes_no ← regex
radiologist_comparison_yes_no
open_code_yes_no      ← regex (github, gitlab, "code is available")
open_data_yes_no      ← regex ("publicly available", "data sharing")
---- Yorum ----
main_finding_excerpt  (abstract'tan otomatik özet)
```

#### B.2. Yöntem
- Python regex + keyword matching (yüksek hızlı, ~10 sn/makale)
- Manuel doğrulama gerektiren alanlar: belirsizse boş bırak
- **Çıktı dosyası:** `extracted_data.xlsx` (master veritabanı)

---

### Aşama C — Sentez/analiz tablolarını üret (1 saat)

`extracted_data.xlsx`'ten otomatik özet tabloları:

| Tablo | Hesaplama |
|---|---|
| **Tablo 2 (PRISMA-ScR)** | Aşamalar sayımları (gerçek) |
| **Tablo 3 (Dahil edilen çalışmalar)** | İlk 30 en yüksek atıflı (Scopus "Cited by" varsa) |
| **Tablo 4 (Patoloji × N)** | `groupby('target_pathology').size()` |
| **Tablo 5 (Görev × Patoloji)** | crosstab |
| **Tablo 6 (Mimari ailesi)** | `groupby('model_family').size()` |
| **Tablo 7 (Açık bilim)** | open_code, open_data, open_weights crosstab |
| **Tablo 8 (Harici doğrulama)** | external_validation × pathology |
| **YENİ Şekil 2** | Yıllara göre yayın sayısı (matplotlib veya tablo) |
| **YENİ Tablo 9** | Performans aralıkları (AUC min-max-medyan per task_type) |

**Çıktı:** `synthesis_tables.xlsx` (bütün tablolar yan yana)

---

### Aşama D — Atıf yöneticisi + Vancouver numaralama (1 saat)

#### D.1. Citation key atama
- Her makaleye Vancouver numarası: **[1], [2], ..., [N]** (atıfların ilk göründüğü sırada)
- BibTeX key (yedek): `liang2024_app_3dcnn` (yazar+yıl+patoloji+model)
- citation_mapping.xlsx: study_id ↔ vancouver_num ↔ bibtex_key

#### D.2. Vancouver formatı üret
- her atıf için: `Yazar AB, Yazar CD, ..., Yazar XY. Title. Journal. Year;Volume(Issue):Pages. doi:`
- BibTeX dosyası: `references.bib` (Zotero ve LaTeX uyumlu)

**Çıktı:** 
- `references_vancouver.docx` (sıralı kaynakça)
- `references.bib`
- `citation_mapping.xlsx`

---

### Aşama E — Makale bölümlerine atıf entegrasyonu (3-5 saat)

#### E.1. Bölüm-atıf eşleme matrisi

`extracted_data.xlsx`'ten her bölüme uygun çalışmaları seç:

| Makale bölümü | Hangi çalışmalar atıf alır |
|---|---|
| **1.5 Literatür Boşluğu** | Diğer kapsam belirleme incelemeleri |
| **3.1 PRISMA-ScR akışı** | (atıf yok, sayım) |
| **3.2 Genel özellikler** | Tablo 3'teki ilk 30 çalışma |
| **3.4.1 Apandisit** | target_pathology=APP olan tüm çalışmalar (~16) |
| **3.4.2 Kolesistit** | target_pathology=CHO (~8) |
| **3.4.3 Pankreatit** | target_pathology=PAN (~52) |
| **3.4.4 Ürolitiyazis** | target_pathology=URO (~125) — en yoğun |
| **3.4.5 Divertikülit** | target_pathology=DIV (~6) |
| **3.4.6 AAA** | target_pathology=AAA (~101) |
| **3.5 Görevler** | task_type bazlı kümeleme |
| **3.6 Mimari** | model_family bazlı kümeleme; her aile için 3-5 örnek |
| **3.7 Veri seti** | dataset_name + public/private bazında |
| **3.8 Performans** | en yüksek/düşük AUC; reader study örnekleri |
| **3.9 Harici doğrulama** | external_validation=yes olanlar (~%26) |
| **3.10 Açık bilim** | open_code=yes olanlar (~%19) |
| **4.x Tartışma** | Bulgular bölümünde belirtilen kilit çalışmalar (+1-2 dış literatür) |

#### E.2. Atıf kümeleme örneği (Bulgular)

> "Akut apandisit alanında 3D CNN mimarileri öne çıkmıştır [12,15,18,23,27]; Liang ve ark.'nın 3D U-Net modeli iç doğrulamada AUC 0,95'e ulaşmıştır [15]. Park ve ark. ise apendiks bölütleme için U-Net türevini kullanarak Dice 0,86 bildirmiştir [18]."

#### E.3. Tartışma'da öne çıkan çalışmaların açık adı

> "iAorta sistemi (Yang ve ark., 2025) [89] kontrastsız BT üzerinde acil aortik sendromu önceliklendiren ilk büyük ölçekli klinik değerlendirmeyi sunmaktadır."

#### E.4. Atıf yoğunluğu hedefleri

| Bölüm | Hedef atıf sayısı |
|---|---:|
| Giriş | 8–15 |
| Yöntem | 4–7 |
| Bulgular | %85 dahil edilen çalışmalar (atıf yoğun) |
| Tartışma | %15 dahil edilen + dış literatür |
| Sonuç | 0–3 |
| **Toplam atıf alma** | **100%** dahil edilen çalışmalar |

---

### Aşama F — Doğrulama ve final üretim (30 dk)

#### F.1. Otomatik kontroller (Python script)

- [ ] Kaynakçadaki **her** referans makale metninde en az 1 kez atıf almış mı? → `orphan_refs_check.py`
- [ ] Makaledeki **her** atıf numarası kaynakçada var mı? → `citation_consistency.py`
- [ ] Atıf numarası sıralaması doğru mu (görünme sırası)? → `citation_order.py`
- [ ] PRISMA-ScR 22 maddelik kontrol listesi tamamlandı mı?
- [ ] Tablo numaraları makalede referans alıyor mu?

#### F.2. Final docx üretimi
- v2 makale şablonunu güncelle:
  - Bulgular bölümünü gerçek atıflarla yeniden yaz
  - Tartışma'ya gerçek çalışma örnekleri ekle
  - Kaynakça bölümünü tüm dahil edilen makalelerle değiştir
  - Tablo 1–9 gerçek frekanslarla
- Sürüm: `Karin_Agrisi_BT_YZ_Inceleme_v3_ATIF_TAM.docx`

---

## 3. Süre tahmini

| Aşama | İçerik | Süre |
|---|---|---:|
| A | Dahil edilen havuzu netleştir | 30 dk |
| B | Otomatik veri çıkarımı (305-450 makale) | 2 saat |
| C | Sentez tabloları üret | 1 saat |
| D | Citation key + Vancouver formatı | 1 saat |
| E | Makaleye atıf entegrasyonu | 3-5 saat (otomatize) |
| F | Doğrulama + final docx | 30 dk |
| **TOPLAM** | otomatize iş | **~8 saat** |

Manuel doğrulama (opsiyonel, kalite artışı için): +4-8 saat (kullanıcı tarafından)

---

## 4. Çıktı klasörü

```text
D:\makale-pdf\search_results\05_extraction\
  extracted_data.xlsx               (B sonucu: master veri tabanı)
  synthesis_tables.xlsx             (C sonucu: tablo 2-9 sayımları)

D:\makale-pdf\search_results\06_citations\
  references.bib                    (BibTeX)
  references_vancouver.docx         (sıralı kaynakça)
  citation_mapping.xlsx             (study_id ↔ [N])

D:\makale-pdf\search_results\07_article\
  Karin_Agrisi_BT_YZ_Inceleme_v3_ATIF_TAM.docx   ⭐ FİNAL
  orphan_refs_check_report.txt
  citation_consistency_report.txt
```

---

## 5. Hemen yapılacak iki karar

### Karar 1 — Hangi alt küme?

```
[ ] A1. 305 likely_include (hızlı, temiz)
[X] A4. 305 + needs_review smart 2. tur ≈ 450 (Recommended)
[ ] A2. 1.092 hepsi (çok fazla)
[ ] A3. 305 + manuel ekleme
```

### Karar 2 — Atıf stili

```
[X] Vancouver numaralı [1,2,3] (Recommended: Türk radyoloji dergileri standardı)
[ ] APA (Yazar yıl)
[ ] IEEE (köşeli parantezli numaralı)
```

---

## 6. Onayınızla başlayalım

Bu plan üzerinde değişiklik isterseniz söyleyin (alt küme seçimi, atıf stili, çıkarılacak alanların listesi, vb.). Onay verirseniz:

**İlk adım** = Aşama A: dahil edilen havuzu netleştir (`included_studies_final.xlsx` üret).

Sonrasında B–F aşamalarını sıralı çalıştırırım. Her aşama sonunda kısa bir özet + onay isterim.

---

## 7. Sürüm bilgisi

```text
Plan adı       : INCELEME_MAKALESI_SENTEZ_PLANI_v2
Sürüm          : v2.0
Hazırlanma tarihi: 14 Mayıs 2026
İlişkili makale : Karin_Agrisi_BT_YZ_Kapsam_Belirleme_Incelemesi_2021_2026.docx (mevcut v2)
Hedef sürüm   : v3 (atıf-tam, inceleme makalesi)
Hazırlayan    : Cowork (Claude)
```
