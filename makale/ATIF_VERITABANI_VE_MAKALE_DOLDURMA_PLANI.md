# Atıf Veritabanı Oluşturma ve Makale Doldurma Planı
## "Karın Ağrısı için Bilgisayarlı Tomografide Yapay Zeka Uygulamaları" (2021–2026)

**Plan tarihi:** 14 Mayıs 2026  
**Hazırlayan:** Cowork (Claude)  
**Hedef:** 5 veritabanı taraması → tek bir master atıf/veri tabanı → makalenin her bölümünün gerçek atıflarla doldurulması

---

## 0. Genel Mantık

Şu an makale, yapı ve örnek 17 atıfla hazır; ama bulgular "referans dağılım" düzeyinde. Bu plan, makaleyi **kanıt-temelli** hâle getirmek için aşağıdaki zinciri kuruyor:

```text
Ham CSV exportları
  → Master kayıt tablosu (dedup'lanmış)
  → Eleme tabloları (T/A + Tam metin)
  → Dahil edilen çalışmalar listesi (~90 makale)
  → Veri çıkarım matrisi (her çalışma için 30+ alan)
  → Atıf yöneticisi (BibTeX/RIS) + citation key
  → Makaledeki her cümleye doğru atıf
```

Her aşamanın ürünü bir sonraki aşamanın girdisi. Aşama sırasını atlamayacağız.

---

## 1. Aşama 1 — Ham Kayıt Toplama (Export)

### 1.1. Hedef
Ek 1'deki tam sorguları 5 veritabanında çalıştırıp ham kayıtları CSV/RIS formatında indirmek.

### 1.2. Veritabanı bazlı export rehberi

| Veritabanı | Sorgu | Export formatı | Maks. seferde | Notlar |
|---|---|---|---|---|
| PubMed/MEDLINE | Ek 1.1 | CSV (ya da .nbib) | 10.000 | "Save → All results → CSV" |
| arXiv | Ek 1.2 (6 patoloji × 1) | API XML / sayfadan kopya | 200/sorgu | Sandbox IP bloklu; kullanıcı tarayıcı |
| IEEE Xplore | Ek 1.3 | CSV | 2.000 | "Export → Citation and Abstract → CSV" |
| Scopus | Ek 1.4 | CSV | 2.000 | **Kurumsal SSO** zorunlu (Preview ≠ Full) |
| Web of Science | Ek 1.5 | Excel | 1.000/seferde | "Export → Excel → Custom Selection: Full Record" |

### 1.3. İndirilen alanlar (her dosyada en az)
PMID/DOI/arxiv_id/eid/wos_an, title, abstract, authors, year, journal/source, document_type, language, keywords, URL, raw record (orijinal kayıt).

### 1.4. Çıktılar (`search_results/01_raw/`)
```text
pubmed_main_2021_2026_YYYYMMDD.csv
arxiv_appendicitis_2021_2026.xml
arxiv_cholecystitis_2021_2026.xml
arxiv_pancreatitis_2021_2026.xml
arxiv_urolithiasis_2021_2026.xml
arxiv_diverticulitis_2021_2026.xml
arxiv_aaa_2021_2026.xml
ieee_main_2021_2026.csv
scopus_main_2021_2026.csv
wos_main_2021_2026.xls
```

### 1.5. Kalite kontrol
- Her dosyanın **satır sayısı** Tablo 2'deki ham sayı ile eşleşmeli (PubMed=467, IEEE=161, WoS=501; arXiv ve Scopus son sayım gerekiyor).
- Her dosya `search_log_2021_2026.md`'a tarih + sorgu metni + sayım ile kaydedilmeli.

---

## 2. Aşama 2 — Birleştirme ve Tekilleştirme

### 2.1. Hedef
5 veritabanı dosyasını **tek master tabloya** standart alanlarla birleştirmek; tekilleri kaldırmak.

### 2.2. Master tablo şeması (`search_results/02_merged/master_records.xlsx`)
| Alan | Açıklama |
|---|---|
| record_id | RR_0001 … RR_NNNN (auto increment) |
| database | pubmed / arxiv / ieee / scopus / wos |
| query_type | main / pathology_specific / sensitivity |
| pathology_search_group | APP/CHO/PAN/URO/DIV/AAA/MULTI |
| title | başlık |
| abstract | özet |
| authors | "Soyad A, Soyad B..." |
| year | 2021–2026 |
| journal_or_source | dergi/konferans/preprint |
| doi | DOI |
| pmid | PubMed ID |
| arxiv_id | arXiv ID |
| ieee_id | IEEE article number |
| scopus_eid | Scopus EID |
| wos_accession_number | WoS UT |
| document_type | article / conference / preprint / review |
| language | en / tr / other |
| keywords | virgülle ayrı |
| url | erişim bağlantısı |
| raw_source_file | hangi CSV'den geldi |

### 2.3. Tekilleştirme sırası (kayıt eşleşmesi)
1. DOI eşit → duplicate
2. PMID eşit → duplicate
3. arxiv_id / ieee_id / scopus_eid / wos_an eşit → duplicate
4. Başlık benzerliği ≥ 0,90 (Levenshtein veya RapidFuzz) → duplicate
5. Başlık + yıl + ilk yazar tam eşleşme → duplicate

Her duplicate için `duplicate_reason` alanı + `kept_record_id` ile orijinal işaretlenir.

### 2.4. Çıktılar
```text
02_merged/master_records.xlsx           (yaklaşık 1.369 satır)
03_deduplicated/deduplicated_records.xlsx  (yaklaşık 740 satır)
03_deduplicated/duplicates_log.xlsx     (kaldırılan kayıtlar + gerekçe)
```

### 2.5. Karar noktası ⏸️
Kullanıcı `deduplicated_records.xlsx`'i gözden geçirir, edge-case duplicate'leri onaylar/reddeder.

---

## 3. Aşama 3 — Başlık/Özet Eleme

### 3.1. Hedef
~740 kayıttan ~210'una indirgemek (tam metin değerlendirmesi için).

### 3.2. Otomatik ön karar mantığı (script ile)
```text
IF year < 2021 OR year > 2026 → exclude (outside_year_range)
IF no target pathology term → exclude (wrong_pathology)
IF no CT/imaging term → maybe (modality_unclear)
IF no AI/ML/DL/radiomics term → exclude (no_ai_ml_dl)
IF no task term → maybe (task_unclear)
ELSE → include_for_screening
```

### 3.3. Manuel teyit
Otomatik karar her kayda atanır, sonra kullanıcı (veya tek değerlendirici) `decision_title_abstract` alanını **include / exclude / maybe** olarak günceller. Maybe → tam metne aktarılır (asla otomatik dışlanmaz).

### 3.4. Çıktılar (`search_results/04_screening/`)
```text
title_abstract_screening.xlsx
  alanlar: screening_id, record_id, title, year, database,
           target_pathology_present, ct_or_radiology_present,
           ai_ml_dl_present, task_present,
           decision_title_abstract, exclusion_reason_title_abstract, reviewer_notes
exclusions_ta_summary.xlsx (gerekçe başına sayım)
```

### 3.5. Karar noktası ⏸️
Kullanıcı, ~530 dışlanan kaydın gerekçe dağılımını kontrol eder.

---

## 4. Aşama 4 — Tam Metin Değerlendirme

### 4.1. Hedef
~210 kayıttan ~90 nihai dahil edilen çalışmaya inmek.

### 4.2. Tam metin temini
- Açık erişim: PMC, arXiv PDF, dergi açık erişim
- Kurumsal: Mersin EZproxy üzerinden Elsevier/Springer/IEEE/Wiley
- Erişilemeyen: `not_accessible_full_text` ile dışlanır (~18 makale beklenen)

### 4.3. Eligibility teyidi (her PDF için)
```text
- Hedef patoloji onaylandı mı?
- BT modalitesi içeriyor mu? (US/MR ayrı modalite ise dışla)
- YZ/MÖ/DÖ/radyomik bileşeni var mı?
- En az bir CV görevi (DET/CLS/SEG/LOC/CAD/PRED) var mı?
- Orijinal model/değerlendirme mi yoksa derleme mi?
```

### 4.4. Çıktılar (`search_results/04_screening/`)
```text
full_text_screening.xlsx
  alanlar: fulltext_id, record_id, full_text_available,
           target_pathology_confirmed, ct_modality_confirmed,
           ai_ml_dl_confirmed, cv_task_confirmed,
           original_study_or_review, decision_full_text,
           exclusion_reason_full_text, reviewer_notes
included_studies_list.xlsx (~90 satır, sadece include)
```

### 4.5. Karar noktası ⏸️
**Nihai dahil edilen çalışma listesi onayı.** Bu liste, makalenin her tablosuna kaynak olacak.

---

## 5. Aşama 5 — Veri Çıkarımı (en kritik aşama) ⭐

### 5.1. Hedef
Her dahil edilen çalışmadan **standart 35 alanın** çıkarılması — bu, makaledeki her atıfın arkasındaki gerçek bilgi tabanı.

### 5.2. Veri çıkarım formu — alanlar (`search_results/05_extraction/extracted_data.xlsx`)

#### Bibliyografik
- study_id (örn. APP_001, AAA_005)
- citation_key (örn. liang2024_app_3dcnn — BibTeX uyumlu)
- first_author, all_authors
- publication_year
- title
- doi, pmid, arxiv_id
- journal_or_conference
- country (yazışma yazarı kurumuna göre)
- document_type

#### Klinik bağlam
- target_pathology (APP/CHO/PAN/URO/DIV/AAA/MIX)
- pathology_subgroup (örn. acute appendicitis vs. complicated)
- adult_or_pediatric (ADULT/PED/MIX)
- clinical_use_case (acil saptama / şiddet öngörüsü / triyaj / tanı desteği)

#### Veri seti
- imaging_modality (CT / CTA / NCCT / dual-energy)
- ct_type (kontrastlı / kontrastsız / hem)
- dataset_name (varsa)
- public_dataset_yes_no
- single_center_or_multicenter
- number_of_patients
- number_of_ct_studies
- number_of_images_or_slices
- annotation_protocol (kim, kaç okuyucu)

#### Model
- task_type (DET/CLS/SEG/LOC/CAD/PRED/TRIAGE/MULTI)
- model_family (CNN_2D/CNN_3D/UNET/NNUNET/TRANSFORMER/SAM/RADIOMICS_ML/HYBRID/...)
- specific_architecture (ResNet-50, nnU-Net, Swin-B, MedSAM, ...)
- architecture_extracted_from (başlık/özet/yöntem/şekil)
- baseline_model (karşılaştırılan referans model)
- training_strategy (transfer / scratch / fine-tune)
- augmentation_strategy

#### Performans
- performance_metric_auc, accuracy, sensitivity, specificity
- precision, recall, f1_score
- dice, iou, hausdorff
- mAP
- 95_CI_reported_yes_no

#### Kanıt kalitesi
- external_validation_yes_no
- external_dataset_name
- radiologist_comparison_yes_no
- reader_study_yes_no
- prospective_evaluation_yes_no
- open_code_yes_no (ve URL)
- open_data_yes_no
- open_weights_yes_no

#### Yorum
- main_findings (tek cümle)
- limitations_reported_by_authors
- reviewer_notes
- claim_tags (makaledeki hangi iddialara kaynak — bkz. Aşama 6)

### 5.3. Süreç önerisi
1. Pilot: önce 5 makaleyi bu form ile çıkar (kalibrasyon).
2. Form üzerinde gerekli düzeltme.
3. Geri kalan ~85 makale tek tek (her biri ortalama 25–35 dk → toplam ≈45 saat).
4. Mümkünse 2. değerlendirici sample %10–20'yi kontrol etsin (Cohen κ ile uyumluluk).

### 5.4. Çıktılar
```text
05_extraction/extracted_data.xlsx       (master citation database — 90 satır)
05_extraction/extraction_pilot_5.xlsx   (kalibrasyon)
05_extraction/disagreements.xlsx        (varsa 2 değerlendirici uyumsuzlukları)
```

### 5.5. Karar noktası ⏸️
Pilot sonrası kullanıcı formu onaylar, sonra tam çıkarım başlar.

---

## 6. Aşama 6 — Atıf Yönetimi (Citation Manager)

### 6.1. Hedef
Her çalışmaya **tek bir citation_key** vermek ve bunu tüm araçlarda (Word, BibTeX, Vancouver) kullanmak.

### 6.2. Citation key kuralı
```text
{ilk_yazar_soyadı}{yıl}_{patoloji_kodu}_{model_kısa}
örnekler:
  liang2024_app_3dcnn
  yang2025_cho_unet
  zhao2025_pan_nnunet
  mukherjee2023_uro_3dunet
  schwarz2023_div_3dcnn
  hahn2025_aaa_nnunet
  yang2025_aas_dlworkflow
```

### 6.3. Atıf yöneticisi seçimi (öneri)
| Araç | Avantaj | Dezavantaj |
|---|---|---|
| **Zotero** (Recommended) | Ücretsiz, Word eklentisi, BibTeX dışa aktarım, web import | — |
| Mendeley | PDF organizasyon iyi | Word sürüm uyumluluğu zaman zaman sorun |
| EndNote | Gelenek | Lisans gerekir |

### 6.4. Süreç
1. Tüm 90 dahil edilen makalenin DOI/PMID'sini Zotero'ya import et (CSV → Zotero).
2. Citation key'leri Better BibTeX eklentisiyle otomatik üret.
3. PDF'leri Zotero'ya bağla.
4. `citations.bib` dosyası dışa aktar (BibTeX).
5. Word'de Zotero plugin → Vancouver style ile inline atıf.

### 6.5. Çıktılar
```text
zotero_library/                   (Zotero koleksiyonu)
citations.bib                     (BibTeX, Vancouver/IEEE'ye dönüştürülebilir)
citation_keys_master.xlsx         (study_id ↔ citation_key eşlemesi)
```

---

## 7. Aşama 7 — Makaleye Entegrasyon (claim → citation eşlemesi)

### 7.1. Hedef
Makaledeki **her bulgu/iddia satırı** için extracted_data'dan ilgili çalışmaları çekip atıf eklemek. "Sıfır atıfsız bulgu" ilkesi.

### 7.2. Yöntem — claim_tags sistemi
Aşama 5'te her çalışmaya bir veya daha fazla `claim_tag` atanır. Bu tag'ler makalenin hangi cümle/iddia için kaynak olacağını gösterir. Örnek tag listesi:

```text
- BUL.3.1.akış          → PRISMA-ScR akış sayıları (Tablo 2)
- BUL.3.4.PAN.yoğunluk  → "Akut pankreatit kanıt yoğunluğu en yüksek..."
- BUL.3.4.APP.3dcnn     → "APP'de 3D CNN yaklaşımları öne çıkıyor..."
- BUL.3.6.unet_baskın   → "Bölütlemede U-Net ailesi baskın..."
- BUL.3.6.transformer_yükseliş → "2024 sonrasında transformer artışı..."
- BUL.3.7.tek_merkez    → "Çalışmaların ~%62'si tek merkezli..."
- BUL.3.9.harici_doğrulama → "Harici doğrulama oranı %26..."
- BUL.3.10.açık_kod     → "Açık kod paylaşımı %19..."
- TAR.4.4.transformer_temel_model → tartışmada transformer/SAM yorumu
- TAR.4.7.boşluk_pediatrik → pediatrik kanıt eksikliği
- ... (her bulgu için bir tag)
```

### 7.3. Eşleme tablosu (`07_article/claim_to_citations.xlsx`)
| claim_tag | makale_bölümü | ilgili_study_id_listesi | atıf_sayısı |
|---|---|---|---|
| BUL.3.4.PAN.yoğunluk | 3.4 + Tablo 4 | PAN_001, PAN_005, ... PAN_029 | 29 |
| BUL.3.6.unet_baskın | 3.6 + Tablo 6 | APP_007, AAA_002, ... | 24 |

### 7.4. Bölümlere otomatik atıf yerleştirme
Her makale bölümü için "kaynaklar burada" yer tutucusu varsa, script `claim_to_citations.xlsx`'i okuyup Vancouver formatında atıfları yerleştirir:

```text
"Bu çerçevede, akut pankreatit kanıt yoğunluğunun en yüksek olduğu alandır
 (n=29) [3,7,9,12,18,...]."
```

Numaralandırma `citations.bib` sırasına göre yapılır.

### 7.5. Word'e import
- Yöntem A: Zotero plugin → Insert citation tek tek (kontrollü)
- Yöntem B: Pandoc + pandoc-citeproc ile markdown'dan docx'e dönüştürme (toplu)

### 7.6. Bölümlere göre atıf yoğunluğu (hedef)
| Bölüm | Atıf adedi (hedef) |
|---|---:|
| 1. Giriş | 8–15 (alan literatürü) |
| 2. Yöntem | 4–7 (PRISMA-ScR, JBI, kaynak çerçeveler) |
| 3. Bulgular | 60–90 (dahil edilen tüm çalışmalar) |
| 4. Tartışma | 20–30 (yorum + dış literatürle karşılaştırma) |
| 5. Sonuç | 0–3 |
| **Toplam** | **~95–145** |

### 7.7. Çıktılar
```text
07_article/claim_to_citations.xlsx
07_article/Karin_Agrisi_BT_YZ_v3_with_citations.docx
07_article/Karin_Agrisi_BT_YZ_v3.bib
```

---

## 8. Tablolara Etkisi (Tablo 1–8 yeniden üretim)

| Tablo | Ne ile dolacak |
|---|---|
| Tablo 2 (PRISMA-ScR akışı) | Kesin sayılar (Aşama 1–4 sonrası) |
| Tablo 3 (Genel özellikler) | included_studies_list örneği değil, **tüm 90 satır** veya filtrelenmiş alt küme |
| Tablo 4 (Patoloji dağılımı) | extracted_data'dan groupby pathology |
| Tablo 5 (Görev × patoloji) | extracted_data'dan crosstab |
| Tablo 6 (Mimari aileleri) | extracted_data'dan model_family sayım |
| Tablo 7 (Açık bilim) | extracted_data'dan open_code/data/weights |
| Tablo 8 (Harici doğrulama) | extracted_data'dan external_validation crosstab |
| **YENİ Tablo 9** (öneri) | her dahil edilen çalışma için tek satırlı veri çıkarım özeti (ek dosya olarak) |

---

## 9. Öngörülen Klasör Yapısı

```text
D:\makale-pdf\
├── ATIF_VERITABANI_VE_MAKALE_DOLDURMA_PLANI.md      (bu dosya)
├── Karin_Agrisi_BT_YZ_Kapsam_Belirleme_Incelemesi_2021_2026.docx  (mevcut v2)
├── search_results\
│   ├── 01_raw\
│   │   ├── pubmed_main_2021_2026_20260514.csv
│   │   ├── arxiv_*.xml
│   │   ├── ieee_main_2021_2026.csv
│   │   ├── scopus_main_2021_2026.csv
│   │   └── wos_main_2021_2026.xls
│   ├── 02_merged\
│   │   └── master_records.xlsx
│   ├── 03_deduplicated\
│   │   ├── deduplicated_records.xlsx
│   │   └── duplicates_log.xlsx
│   ├── 04_screening\
│   │   ├── title_abstract_screening.xlsx
│   │   └── full_text_screening.xlsx
│   ├── 05_extraction\
│   │   ├── extraction_pilot_5.xlsx
│   │   ├── extracted_data.xlsx          ⭐ MASTER VERİTABANI
│   │   └── disagreements.xlsx
│   ├── 06_logs\
│   │   └── search_log_2021_2026.md
│   └── 07_article\
│       ├── claim_to_citations.xlsx
│       ├── citations.bib
│       └── Karin_Agrisi_BT_YZ_v3_with_citations.docx
├── full_texts\
│   └── PDFs (yaklaşık 90 dosya)
└── zotero_library\
```

---

## 10. Kalite Kontrol ve PRISMA-ScR Uyum

- [ ] Her aşamada `search_log` güncellendi
- [ ] Tekilleştirme gerekçeleri kayıtlı
- [ ] Eleme dışlama gerekçeleri kayıtlı
- [ ] Veri çıkarımında 2. değerlendirici sample (κ ≥ 0,80 hedef)
- [ ] Mimari kodlama yöntem bölümünden alındı (başlık/özetten değil)
- [ ] Tüm tablolar extracted_data'dan üretildi (manuel "tahmin" yok)
- [ ] Açık bilim göstergeleri (kod/veri/ağırlık paylaşımı) raporlandı
- [ ] PRISMA-ScR 22 maddelik kontrol listesi tamamlandı
- [ ] Atıf yoğunluğu hedef bölümlerde (60–90 atıf bulgularda)
- [ ] Vancouver format tutarlı

---

## 11. Risk ve Mitigasyonlar

| Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|
| Scopus full erişim yok | Yüksek | Orta | Kurumsal SSO + EZproxy; alternatif: Dimensions, Lens.org |
| arXiv API rate limit | Yüksek | Düşük | Kullanıcı tarayıcısı, patoloji başına 6 ayrı sorgu, manuel sayım |
| Tam metin erişimi (~%10) | Orta | Düşük | EZproxy + ResearchGate yazara talep |
| Mimari yanlış kodlama | Orta | Yüksek | 2. değerlendirici, pilot 5 makale kalibrasyonu |
| Atıf-iddia eşlemesi tutarsız | Orta | Yüksek | claim_tag sistemi + claim_to_citations.xlsx kontrolü |
| Tek değerlendirici bias | Yüksek | Orta | %10–20 sample 2. okuyucu |
| Süre baskısı (yaklaşık 60 saat toplam) | Yüksek | Orta | Aşama 5'i 2 haftaya yayma |

---

## 12. Süre Tahmini

| Aşama | Süre tahmini | Kim yapar |
|---|---:|---|
| 1. Export | 2 saat | Kullanıcı (5 indirme) |
| 2. Birleştirme + dedup | 1–2 saat | Cowork (script) |
| 3. T/A eleme | 4–6 saat | Cowork ön karar + kullanıcı teyit |
| 4. Tam metin | 8–10 saat | Kullanıcı (PDF temini) + birlikte değerlendirme |
| 5. Veri çıkarımı (90 makale × ~30 dk) | 40–50 saat | Kullanıcı + Cowork (yarı otomatik) |
| 6. Atıf yöneticisi kurulumu | 2 saat | Kullanıcı (Zotero) |
| 7. Makaleye entegrasyon | 8–12 saat | Cowork (script) + kullanıcı kontrol |
| **TOPLAM** | **~65–85 saat** | |

---

## 13. İlk Adım için Öneri (Hemen başlanacak iş)

Aşağıdaki **iki şey** başlangıç noktası:

1. **5 veritabanından ham CSV indir.** (Aşama 1)  
   PubMed=467, IEEE=161, WoS=501 sayıları zaten doğrulu. Eksik olan arXiv ve Scopus için kullanıcı kurumsal hesabıyla manuel.

2. **Bana gönder** — `search_results/01_raw/` klasörüne koy. Ben Aşama 2'nin (master tablo + dedup) Python scriptini yazıp çalıştırırım.

Aşama 2 sonrası ilk karar noktası: dedup'lanmış kayıt sayısını teyit edip Aşama 3'e geçeceğiz.

---

## 14. Onay & Karar Noktaları (Özet)

```text
✅ Aşama 1 sonrası → ham sayılar Tablo 2 ile uyumlu mu?
✅ Aşama 2 sonrası → dedup sayısı makul mu (~%45 düşüş bekleniyor)?
✅ Aşama 3 sonrası → T/A eleme oranı (~%70 dışlama)
✅ Aşama 4 sonrası → ⭐ NİHAİ DAHİL EDİLEN ÇALIŞMA LİSTESİ ONAYI
✅ Aşama 5 pilot (5 makale) → ⭐ VERİ ÇIKARIM FORMU ONAYI
✅ Aşama 5 tamamlandığında → veritabanı kalite kontrol
✅ Aşama 7 öncesi → claim_tag sistemi onayı
✅ Aşama 7 sonrası → tam metin atıf yoğunluğu kontrol
```

---

## 15. Ek: Kullanıcı için Hazırlık Listesi

- [ ] Zotero indir + Better BibTeX eklentisi
- [ ] Mersin Üniversitesi EZproxy login bilgileri hazırla
- [ ] Scopus tam erişim için kurumsal SSO test et
- [ ] arXiv aramaları için kişisel arXiv hesabı (gerekmez ama önerilir)
- [ ] PDF saklama klasörü hazırla (`D:\makale-pdf\full_texts\`)
- [ ] Word'de Zotero eklentisi kurulu mu kontrol et
- [ ] (İdeal) ikinci değerlendirici (öğrenci, asistan veya meslektaş)

---

## 16. Sürüm Bilgisi

```text
Plan adı: ATIF_VERITABANI_VE_MAKALE_DOLDURMA_PLANI
Sürüm: v1.0
Hazırlanma tarihi: 14 Mayıs 2026
Hazırlayan: Cowork (Claude)
İlişkili makale sürümü: v2 (PubMed=467, IEEE=161, WoS=501 ile)
Sonraki güncelleme: Aşama 1 tamamlandığında v1.1
```
