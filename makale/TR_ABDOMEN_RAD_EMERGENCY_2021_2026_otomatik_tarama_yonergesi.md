# Otomatik Tarama Yönergesi v2  
## Karın Ağrısı için Bilgisayarlı Tomografide Yapay Zeka Uygulamaları: Çoklu Veritabanı Kapsam Belirleme İncelemesi (2021–2026)

---

## 1. Yönergenin Amacı

Bu yönerge, **2021–2026 yılları arasında** yayımlanan ve karın ağrısı bağlamında klinik olarak önemli altı abdominal acil patolojiye yönelik **BT tabanlı yapay zekâ, makine öğrenmesi ve derin öğrenme çalışmalarını** çoklu veritabanı üzerinden taramak için hazırlanmıştır.

Çalışma başlığı:

```text
Karın Ağrısı için Bilgisayarlı Tomografide Yapay Zeka Uygulamaları: Çoklu Veritabanı Kapsam Belirleme İncelemesi (2021–2026)
```

Bu yönerge, aşağıdaki beş veritabanında uygulanmak üzere düzenlenmiştir:

```text
1. PubMed/MEDLINE
2. arXiv
3. IEEE Xplore
4. Scopus
5. Web of Science
```

---

## 2. Temel Metodolojik Karar

Bu tarama yönergesinde **mimari adları ana sorguya dahil edilmeyecektir**.

Yani ana sorguda aşağıdaki mimari terimler zorunlu arama bileşeni olarak kullanılmayacaktır:

```text
U-Net
nnU-Net
3D CNN
Transformer
Vision Transformer
Swin Transformer
SAM
MedSAM
Mamba
Diffusion model
GAN
Federated learning
Vision-language model
Large language model
```

Bunun nedeni, birçok çalışmanın başlık, özet veya anahtar kelimelerinde spesifik model mimarisini açıkça yazmamasıdır. Bu terimler ana sorguya eklenirse uygun makaleler kaçabilir.

Bu nedenle çalışma stratejisi şu şekilde yapılandırılmıştır:

```text
1. Önce geniş ana tarama yapılır.
2. Ana taramada patoloji + BT + YZ/MÖ/DÖ + görev terimleri kullanılır.
3. Çıkan sonuçlardan model mimarileri sonradan veri çıkarım formunda kodlanır.
4. Mimari adları yalnızca isteğe bağlı duyarlılık kontrolü için kullanılabilir.
```

---

## 3. Kapsam Bildirimi

Bu kapsam belirleme incelemesi, karın ağrısının tüm nedenlerini değil, TEKNOFEST-2022 **TR_ABDOMEN_RAD_EMERGENCY** veri seti ile işlevsel olarak ilişkili altı abdominal acil patolojiyi kapsamaktadır.

Kapsama alınan patolojiler:

```text
1. Akut apandisit
2. Akut kolesistit
3. Akut pankreatit
4. Ürolitiyazis / nefrolitiyazis / böbrek-üreter taşları
5. Akut divertikülit
6. Abdominal aort anevrizması / abdominal aort diseksiyonu / akut aortik sendrom
```

Bu nedenle çalışma başlığında “karın ağrısı” ifadesi klinik bağlamı temsil eder; arama stratejisi ise seçilmiş altı patolojiye odaklanır.

---

## 4. Araştırma Hedefi

Bu kapsam belirleme incelemesinin hedefi, seçilmiş altı abdominal acil patoloji için BT görüntüleri üzerinde geliştirilen YZ/MÖ/DÖ uygulamalarını aşağıdaki boyutlarda haritalamaktır:

```text
- Patoloji türü
- Görüntüleme modalitesi
- Bilgisayarlı görme görevi
- Kullanılan model mimarisi
- Veri seti türü
- Hasta/görüntü sayısı
- Performans ölçütleri
- Harici doğrulama durumu
- Açık veri / açık kod durumu
- Klinik uygulanabilirlik düzeyi
```

---

## 5. Ana Araştırma Soruları

```text
1. 2021–2026 yılları arasında altı hedef abdominal acil patoloji için BT tabanlı YZ/MÖ/DÖ çalışmaları nasıl dağılmaktadır?

2. Çalışmalar en çok hangi patolojilerde yoğunlaşmaktadır?

3. Çalışmalar hangi bilgisayarlı görme görevlerine odaklanmaktadır?
   - Saptama
   - Sınıflandırma
   - Bölütleme
   - Lokalizasyon
   - Tanı desteği
   - Öngörü

4. Dahil edilen çalışmalarda hangi model mimarileri kullanılmıştır?

5. Çalışmalarda kullanılan veri setleri özel mi, halka açık mı, tek merkezli mi, çok merkezli midir?

6. Çalışmalarda hangi performans ölçütleri raporlanmıştır?

7. Harici doğrulama, açık kod, açık veri ve klinik uygulanabilirlik açısından literatürde hangi boşluklar bulunmaktadır?
```

---

## 6. PCC Çerçevesi

Kapsam belirleme incelemesi için PCC çerçevesi aşağıdaki şekilde tanımlanmıştır:

| PCC Bileşeni | Bu çalışmadaki karşılığı |
|---|---|
| Population / Participants | BT ile değerlendirilen abdominal acil patoloji olguları |
| Concept | YZ/MÖ/DÖ tabanlı bilgisayarlı görme uygulamaları |
| Context | Acil abdominal patolojiler, karın ağrısı, radyoloji, BT, 2021–2026 literatürü |

---

## 7. Dahil Etme ve Dışlama Ölçütleri

### 7.1. Dahil Etme Ölçütleri

Bir çalışma aşağıdaki koşulları sağlıyorsa dahil edilmeye adaydır:

```text
- 2021–2026 yılları arasında yayımlanmış olmalıdır.
- Hedef altı patolojiden en az biriyle ilişkili olmalıdır.
- BT, abdominal BT veya kontrastlı BT görüntüleme verisi kullanmalıdır.
- Yapay zekâ, makine öğrenmesi, derin öğrenme, radyomik veya bilgisayarlı görme yöntemi içermelidir.
- Saptama, sınıflandırma, bölütleme, lokalizasyon, tanı desteği veya öngörü görevlerinden en az birini içermelidir.
- Makale, konferans bildirisi, erken erişim makalesi, ön baskı veya sistematik/kapsam incelemesi olabilir.
```

### 7.2. Dışlama Ölçütleri

Aşağıdaki çalışmalar dışlanacaktır:

```text
- Hedef altı patoloji dışında kalan abdominal hastalıklara odaklanan çalışmalar
- Görüntüleme verisi kullanmayan çalışmalar
- Yalnızca laboratuvar, klinik skor, EHR veya metin verisi kullanan çalışmalar
- BT dışı modaliteye odaklanan ve BT verisi içermeyen çalışmalar
- YZ/MÖ/DÖ/radyomik/bilgisayarlı görme içermeyen çalışmalar
- Hayvan, fantom veya teknik simülasyon çalışmaları
- Editöryal, mektup, görüş yazısı, haber veya yorum niteliğindeki çalışmalar
- Tam metin aşamasında hedef kapsamla ilişkisi doğrulanamayan çalışmalar
```

---

## 8. Ana Arama Blokları

Ana taramada dört ana blok kullanılacaktır:

```text
Patoloji Bloğu
AND
BT / Görüntüleme Bloğu
AND
YZ / MÖ / DÖ Bloğu
AND
Görev Bloğu
AND
Yıl Filtresi
```

---

## 9. Ortak Anahtar Kelime Blokları

### 9.1. Patoloji Bloğu

```text
appendicitis OR "acute appendicitis"
OR cholecystitis OR "acute cholecystitis"
OR pancreatitis OR "acute pancreatitis"
OR urolithiasis OR nephrolithiasis OR "renal stone*" OR "kidney stone*" OR "ureteral stone*"
OR diverticulitis OR "acute diverticulitis"
OR "abdominal aortic aneurysm" OR "aortic aneurysm" OR "aortic dissection" OR "abdominal aortic dissection" OR "acute aortic syndrome"
```

### 9.2. BT / Görüntüleme Bloğu

```text
"computed tomography" OR "computerized tomography" OR CT OR "CT scan*" OR "abdominal CT" OR "contrast-enhanced CT" OR "medical imaging" OR radiology
```

### 9.3. YZ / MÖ / DÖ Bloğu

```text
"artificial intelligence" OR "machine learning" OR "deep learning" OR "computer vision"
OR "neural network*" OR "convolutional neural network*" OR CNN
OR "computer-aided diagnosis" OR "computer aided diagnosis"
OR "computer-aided detection" OR "computer aided detection"
OR radiomics OR "texture analysis"
```

### 9.4. Görev Bloğu

```text
detect* OR diagnos* OR classific* OR classification OR segment* OR segmentation OR localization OR prediction OR triage OR screening
```

---

# 10. Veritabanı Bazlı Ana Sorgular

---

## 10.1. PubMed / MEDLINE

PubMed taramasında MeSH terimleri ve başlık/özet alanı birlikte kullanılacaktır. MeSH terimleri indekslenmiş kayıtları yakalamak için, `[tiab]` terimleri ise yeni veya henüz indekslenmemiş kayıtları yakalamak için kullanılacaktır.

### 10.1.1. PubMed Ana Sorgu

```text
(
  "Appendicitis"[Mesh] OR appendicitis[tiab] OR "acute appendicitis"[tiab]
  OR "Cholecystitis, Acute"[Mesh] OR cholecystitis[tiab] OR "acute cholecystitis"[tiab]
  OR "Pancreatitis"[Mesh] OR pancreatitis[tiab] OR "acute pancreatitis"[tiab]
  OR "Urolithiasis"[Mesh] OR urolithiasis[tiab] OR nephrolithiasis[tiab] OR "renal stone*"[tiab] OR "kidney stone*"[tiab] OR "ureteral stone*"[tiab]
  OR "Diverticulitis"[Mesh] OR diverticulitis[tiab] OR "acute diverticulitis"[tiab]
  OR "Aortic Aneurysm, Abdominal"[Mesh] OR "Aortic Dissection"[Mesh]
  OR "abdominal aortic aneurysm"[tiab] OR "aortic aneurysm"[tiab] OR "aortic dissection"[tiab] OR "abdominal aortic dissection"[tiab] OR "acute aortic syndrome"[tiab]
)
AND
(
  "Tomography, X-Ray Computed"[Mesh]
  OR "computed tomography"[tiab] OR "computerized tomography"[tiab] OR CT[tiab] OR "CT scan*"[tiab] OR "abdominal CT"[tiab] OR "contrast-enhanced CT"[tiab]
  OR radiology[tiab] OR "medical imaging"[tiab]
)
AND
(
  "Artificial Intelligence"[Mesh] OR "Machine Learning"[Mesh] OR "Deep Learning"[Mesh] OR "Neural Networks, Computer"[Mesh]
  OR "artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "computer vision"[tiab]
  OR "neural network*"[tiab] OR "convolutional neural network*"[tiab] OR CNN[tiab]
  OR "computer-aided diagnosis"[tiab] OR "computer aided diagnosis"[tiab]
  OR "computer-aided detection"[tiab] OR "computer aided detection"[tiab]
  OR radiomics[tiab] OR "texture analysis"[tiab]
)
AND
(
  detect*[tiab] OR diagnos*[tiab] OR classific*[tiab] OR classification[tiab]
  OR segment*[tiab] OR segmentation[tiab] OR localization[tiab] OR prediction[tiab] OR triage[tiab] OR screening[tiab]
)
AND
(
  "2021/01/01"[Date - Publication] : "2026/12/31"[Date - Publication]
)
```

### 10.1.2. PubMed Daha Hassas Patoloji Bazlı Tarama

Eğer ana sorgu çok geniş veya yönetilemez sonuç verirse, patoloji bazlı alt sorgular kullanılabilir.

#### Akut apandisit

```text
(
  "Appendicitis"[Mesh] OR appendicitis[tiab] OR "acute appendicitis"[tiab]
)
AND
(
  "Tomography, X-Ray Computed"[Mesh] OR "computed tomography"[tiab] OR CT[tiab] OR "CT scan*"[tiab] OR "abdominal CT"[tiab]
)
AND
(
  "Artificial Intelligence"[Mesh] OR "Machine Learning"[Mesh] OR "Deep Learning"[Mesh]
  OR "artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab]
  OR "computer vision"[tiab] OR "neural network*"[tiab] OR "computer-aided diagnosis"[tiab]
  OR radiomics[tiab]
)
AND
(
  detect*[tiab] OR diagnos*[tiab] OR classific*[tiab] OR segment*[tiab] OR prediction[tiab]
)
AND
(
  "2021/01/01"[Date - Publication] : "2026/12/31"[Date - Publication]
)
```

Aynı kalıp aşağıdaki patoloji terimleriyle tekrarlanmalıdır:

```text
"Cholecystitis, Acute"[Mesh] OR cholecystitis[tiab] OR "acute cholecystitis"[tiab]

"Pancreatitis"[Mesh] OR pancreatitis[tiab] OR "acute pancreatitis"[tiab]

"Urolithiasis"[Mesh] OR urolithiasis[tiab] OR nephrolithiasis[tiab] OR "renal stone*"[tiab] OR "kidney stone*"[tiab] OR "ureteral stone*"[tiab]

"Diverticulitis"[Mesh] OR diverticulitis[tiab] OR "acute diverticulitis"[tiab]

"Aortic Aneurysm, Abdominal"[Mesh] OR "Aortic Dissection"[Mesh] OR "abdominal aortic aneurysm"[tiab] OR "aortic dissection"[tiab] OR "acute aortic syndrome"[tiab]
```

### 10.1.3. PubMed Dışa Aktarma

Önerilen dışa aktarma alanları:

```text
PMID
DOI
Title
Abstract
Authors
Journal
Year
Publication type
MeSH terms
Keywords
URL
```

---

## 10.2. arXiv

arXiv için arama özellikle aşağıdaki kategorilerle sınırlandırılabilir:

```text
cs.CV
eess.IV
cs.LG
cs.AI
stat.ML
```

arXiv’de tıbbi konu kapsamı PubMed kadar güçlü olmadığı için **patoloji bazlı sorgu** önerilir.

### 10.2.1. arXiv Patoloji Bazlı Sorgu Kalıbı

```text
(PATOLOJI_TERIMLERI)
AND
(ti:"computed tomography" OR abs:"computed tomography" OR ti:"CT scan" OR abs:"CT scan" OR ti:"abdominal CT" OR abs:"abdominal CT" OR ti:radiology OR abs:radiology OR ti:"medical imaging" OR abs:"medical imaging")
AND
(ti:"artificial intelligence" OR abs:"artificial intelligence" OR ti:"machine learning" OR abs:"machine learning" OR ti:"deep learning" OR abs:"deep learning" OR ti:"computer vision" OR abs:"computer vision" OR ti:"neural network" OR abs:"neural network" OR ti:radiomics OR abs:radiomics)
AND
(ti:detection OR abs:detection OR ti:classification OR abs:classification OR ti:segmentation OR abs:segmentation OR ti:diagnosis OR abs:diagnosis OR ti:prediction OR abs:prediction)
AND
(cat:cs.CV OR cat:eess.IV OR cat:cs.LG OR cat:cs.AI OR cat:stat.ML)
```

### 10.2.2. arXiv Patoloji Terimleri

Her patoloji için aşağıdaki terimler `PATOLOJI_TERIMLERI` alanına yerleştirilmelidir.

#### Akut apandisit

```text
ti:appendicitis OR abs:appendicitis OR ti:"acute appendicitis" OR abs:"acute appendicitis"
```

#### Akut kolesistit

```text
ti:cholecystitis OR abs:cholecystitis OR ti:"acute cholecystitis" OR abs:"acute cholecystitis"
```

#### Akut pankreatit

```text
ti:pancreatitis OR abs:pancreatitis OR ti:"acute pancreatitis" OR abs:"acute pancreatitis"
```

#### Ürolitiyazis / böbrek-üreter taşı

```text
ti:urolithiasis OR abs:urolithiasis OR ti:nephrolithiasis OR abs:nephrolithiasis OR ti:"renal stone" OR abs:"renal stone" OR ti:"kidney stone" OR abs:"kidney stone" OR ti:"ureteral stone" OR abs:"ureteral stone"
```

#### Akut divertikülit

```text
ti:diverticulitis OR abs:diverticulitis OR ti:"acute diverticulitis" OR abs:"acute diverticulitis"
```

#### AAA / diseksiyon

```text
ti:"abdominal aortic aneurysm" OR abs:"abdominal aortic aneurysm" OR ti:"aortic aneurysm" OR abs:"aortic aneurysm" OR ti:"aortic dissection" OR abs:"aortic dissection" OR ti:"acute aortic syndrome" OR abs:"acute aortic syndrome"
```

### 10.2.3. arXiv Tarih Filtresi

Arayüzde yıl filtresi uygulanmalıdır:

```text
From: 2021
To: 2026
```

API üzerinden çalışılıyorsa tarih aralığı şu şekilde kaydedilmelidir:

```text
submittedDate:[202101010000 TO 202612312359]
```

---

## 10.3. IEEE Xplore

IEEE Xplore için çok uzun birleşik sorgular yerine patoloji bazlı alt sorgular önerilir. Arama alanı ilk aşamada:

```text
All Metadata
```

olarak seçilmelidir. Çok fazla sonuç gelirse ikinci aşamada:

```text
Abstract
```

alanı kullanılabilir.

### 10.3.1. IEEE Xplore Ana Sorgu

```text
(
  "appendicitis" OR "acute appendicitis"
  OR "acute cholecystitis" OR "cholecystitis"
  OR "acute pancreatitis" OR "pancreatitis"
  OR "urolithiasis" OR "nephrolithiasis" OR "renal stone" OR "kidney stone" OR "ureteral stone"
  OR "acute diverticulitis" OR "diverticulitis"
  OR "abdominal aortic aneurysm" OR "aortic dissection" OR "acute aortic syndrome"
)
AND
(
  "computed tomography" OR "computerized tomography" OR "CT scan" OR "abdominal CT" OR "medical imaging" OR radiology
)
AND
(
  "artificial intelligence" OR "machine learning" OR "deep learning" OR "computer vision"
  OR "neural network" OR "convolutional neural network" OR CNN
  OR "computer-aided diagnosis" OR "computer aided diagnosis"
  OR radiomics
)
AND
(
  detection OR diagnosis OR classification OR segmentation OR localization OR prediction
)
```

### 10.3.2. IEEE Xplore Patoloji Bazlı Sorgu Kalıbı

```text
("PATOLOJI_TERIMLERI")
AND
("computed tomography" OR "computerized tomography" OR "CT scan" OR "abdominal CT" OR "medical imaging" OR radiology)
AND
("artificial intelligence" OR "machine learning" OR "deep learning" OR "computer vision" OR "neural network" OR "convolutional neural network" OR CNN OR "computer-aided diagnosis" OR radiomics)
AND
(detection OR diagnosis OR classification OR segmentation OR localization OR prediction)
```

Patoloji terimleri:

```text
"acute appendicitis" OR appendicitis

"acute cholecystitis" OR cholecystitis

"acute pancreatitis" OR pancreatitis

urolithiasis OR nephrolithiasis OR "renal stone" OR "kidney stone" OR "ureteral stone"

"acute diverticulitis" OR diverticulitis

"abdominal aortic aneurysm" OR "aortic dissection" OR "acute aortic syndrome"
```

### 10.3.3. IEEE Xplore Filtreleri

```text
Publication Year: 2021–2026
Content Type: Journals & Magazines, Conferences
Search in: All Metadata
Language: English
```

---

## 10.4. Scopus

Scopus için önerilen alan:

```text
TITLE-ABS-KEY
```

Yıl filtresi:

```text
PUBYEAR > 2020 AND PUBYEAR < 2027
```

### 10.4.1. Scopus Ana Sorgu

```text
TITLE-ABS-KEY(
  (
    appendicitis OR "acute appendicitis"
    OR cholecystitis OR "acute cholecystitis"
    OR pancreatitis OR "acute pancreatitis"
    OR urolithiasis OR nephrolithiasis OR "renal stone*" OR "kidney stone*" OR "ureteral stone*"
    OR diverticulitis OR "acute diverticulitis"
    OR "abdominal aortic aneurysm" OR "aortic aneurysm" OR "aortic dissection" OR "abdominal aortic dissection" OR "acute aortic syndrome"
  )
  AND
  (
    "computed tomography" OR "computerized tomography" OR "CT scan*" OR "abdominal CT" OR "contrast-enhanced CT" OR radiology OR "medical imaging"
  )
  AND
  (
    "artificial intelligence" OR "machine learning" OR "deep learning" OR "computer vision"
    OR "neural network*" OR "convolutional neural network*" OR CNN
    OR "computer-aided diagnosis" OR "computer aided diagnosis"
    OR "computer-aided detection" OR "computer aided detection"
    OR radiomics OR "texture analysis"
  )
  AND
  (
    detect* OR diagnos* OR classific* OR segment* OR localization OR prediction OR triage OR screening
  )
)
AND PUBYEAR > 2020
AND PUBYEAR < 2027
```

### 10.4.2. Scopus Opsiyonel Daraltmalar

Çok fazla sonuç gelirse alan daraltması yapılabilir:

```text
AND (
  LIMIT-TO(SUBJAREA, "MEDI")
  OR LIMIT-TO(SUBJAREA, "COMP")
  OR LIMIT-TO(SUBJAREA, "ENGI")
)
```

Belge türü daraltması:

```text
AND (
  LIMIT-TO(DOCTYPE, "ar")
  OR LIMIT-TO(DOCTYPE, "cp")
  OR LIMIT-TO(DOCTYPE, "re")
)
```

---

## 10.5. Web of Science

Web of Science Core Collection için önerilen alan:

```text
TS=
```

`TS` alanı başlık, özet, yazar anahtar kelimeleri ve Keywords Plus alanlarını tarar.

### 10.5.1. Web of Science Ana Sorgu

```text
TS=(
  (
    appendicitis OR "acute appendicitis"
    OR cholecystitis OR "acute cholecystitis"
    OR pancreatitis OR "acute pancreatitis"
    OR urolithiasis OR nephrolithiasis OR "renal stone*" OR "kidney stone*" OR "ureteral stone*"
    OR diverticulitis OR "acute diverticulitis"
    OR "abdominal aortic aneurysm" OR "aortic aneurysm" OR "aortic dissection" OR "abdominal aortic dissection" OR "acute aortic syndrome"
  )
  AND
  (
    "computed tomography" OR "computerized tomography" OR "CT scan*" OR "abdominal CT" OR "contrast-enhanced CT" OR radiology OR "medical imaging"
  )
  AND
  (
    "artificial intelligence" OR "machine learning" OR "deep learning" OR "computer vision"
    OR "neural network*" OR "convolutional neural network*" OR CNN
    OR "computer-aided diagnosis" OR "computer aided diagnosis"
    OR "computer-aided detection" OR "computer aided detection"
    OR radiomics OR "texture analysis"
  )
  AND
  (
    detect* OR diagnos* OR classific* OR segment* OR localization OR prediction OR triage OR screening
  )
)
```

### 10.5.2. Web of Science Filtreleri

```text
Timespan: 2021–2026
Indexes: SCI-EXPANDED, ESCI, CPCI-S
Document Types: Article, Review Article, Proceedings Paper, Early Access
Languages: English
```

---

# 11. İsteğe Bağlı Duyarlılık Kontrolü

Ana tarama tamamlandıktan sonra, literatürde güncel mimari kullanan ama ana sorguda yakalanmamış olabilecek kayıtları kontrol etmek için isteğe bağlı bir duyarlılık sorgusu yapılabilir.

Bu sorgu **ana tarama yerine geçmez** ve nihai kanıt haritalamasının temelini oluşturmaz.

## 11.1. Duyarlılık Kontrolü İçin Mimari Terimleri

```text
U-Net OR UNet OR nnU-Net
OR transformer OR "vision transformer" OR ViT OR "Swin Transformer"
OR "segment anything" OR SAM OR MedSAM
OR Mamba OR "state space model"
OR "diffusion model" OR GAN OR "generative adversarial network"
OR "federated learning"
OR multimodal OR "vision-language" OR "large language model"
```

## 11.2. Duyarlılık Kontrolünün Kullanım Kuralı

```text
- Ana tarama tamamlanmadan yapılmamalıdır.
- Ana sorguda kaçan güncel model çalışmalarını kontrol etmek için kullanılmalıdır.
- Bulunan ek kayıtlar ayrı etiketlenmelidir.
- query_type alanı "architecture_sensitivity_check" olarak kaydedilmelidir.
- Mimari terimleri nihai dahil etme ölçütü olarak kullanılmamalıdır.
```

---

# 12. Kayıt Yönetimi ve Dosya Yapısı

Önerilen klasör yapısı:

```text
search_results/
├── 01_raw/
│   ├── pubmed_main_2021_2026.csv
│   ├── arxiv_appendicitis_2021_2026.csv
│   ├── arxiv_cholecystitis_2021_2026.csv
│   ├── ieee_main_2021_2026.csv
│   ├── scopus_main_2021_2026.csv
│   └── wos_main_2021_2026.csv
├── 02_merged/
│   └── merged_all_databases_2021_2026.csv
├── 03_deduplicated/
│   └── deduplicated_records_2021_2026.csv
├── 04_screening/
│   ├── title_abstract_screening.csv
│   └── full_text_screening.csv
├── 05_extraction/
│   └── data_extraction_form.csv
└── 06_logs/
    └── search_log_2021_2026.md
```

---

# 13. Arama Günlüğü Şablonu

Her sorgu için aşağıdaki bilgiler kaydedilmelidir:

```text
database:
query_name:
query_type:
search_date:
searcher:
date_range:
search_field:
filters_used:
raw_result_count:
exported_record_count:
export_file_name:
notes:
```

Örnek:

```text
database: PubMed/MEDLINE
query_name: PubMed Main Search
query_type: main
search_date: 2026-05-14
searcher: Oğuzhan Polat
date_range: 2021-01-01 to 2026-12-31
search_field: MeSH + Title/Abstract
filters_used: Publication date
raw_result_count:
exported_record_count:
export_file_name: pubmed_main_2021_2026_20260514.csv
notes:
```

---

# 14. Birleştirme İçin Standart Alanlar

Tüm veritabanı çıktıları aşağıdaki ortak alanlara dönüştürülmelidir:

```text
record_id
database
query_type
pathology_search_group
title
abstract
authors
year
journal_or_source
doi
pmid
arxiv_id
ieee_id
scopus_eid
wos_accession_number
document_type
language
keywords
url
raw_source_file
```

---

# 15. Tekilleştirme Kuralları

Tekilleştirme aşağıdaki sırayla yapılmalıdır:

```text
1. DOI eşleşmesi
2. PMID eşleşmesi
3. arXiv ID eşleşmesi
4. IEEE article number eşleşmesi
5. Scopus EID eşleşmesi
6. Web of Science accession number eşleşmesi
7. Başlık benzerliği
8. Başlık + yıl + ilk yazar benzerliği
```

Başlık benzerliği için önerilen eşik:

```text
Benzerlik oranı ≥ 0.90
```

Tekilleştirme gerekçesi şu alanla kaydedilmelidir:

```text
duplicate_reason
```

Olası değerler:

```text
same_doi
same_pmid
same_arxiv_id
same_ieee_id
same_scopus_eid
same_wos_accession
title_similarity
title_year_first_author_match
```

---

# 16. Otomatik Başlık/Özet Tarama Mantığı

Başlık/özet aşamasında aşağıdaki ön karar mantığı uygulanabilir:

```text
IF year < 2021 OR year > 2026:
    decision = "exclude"
    reason = "outside_year_range"

ELSE IF no target pathology term in title/abstract:
    decision = "exclude"
    reason = "wrong_pathology"

ELSE IF no CT/radiology/imaging term in title/abstract:
    decision = "maybe"
    reason = "modality_unclear"

ELSE IF no AI/ML/DL/radiomics/computer vision term in title/abstract:
    decision = "exclude"
    reason = "no_ai_ml_dl"

ELSE IF no task-related term in title/abstract:
    decision = "maybe"
    reason = "task_unclear"

ELSE:
    decision = "include_for_screening"
    reason = "potentially_relevant"
```

Önemli kural:

```text
Kararsız kayıtlar otomatik dışlanmamalıdır.
```

---

# 17. Başlık/Özet Eleme Formu

Her kayıt için aşağıdaki alanlar doldurulmalıdır:

```text
screening_id
record_id
title
year
database
target_pathology_present
ct_or_radiology_present
ai_ml_dl_present
task_present
decision_title_abstract
exclusion_reason_title_abstract
reviewer_notes
```

Karar seçenekleri:

```text
include
exclude
maybe
```

---

# 18. Tam Metin Değerlendirme Formu

Tam metin aşamasında aşağıdaki alanlar doldurulmalıdır:

```text
fulltext_id
record_id
full_text_available
target_pathology_confirmed
ct_modality_confirmed
ai_ml_dl_confirmed
cv_task_confirmed
original_study_or_review
decision_full_text
exclusion_reason_full_text
reviewer_notes
```

Tam metin dışlama gerekçeleri:

```text
wrong_pathology
wrong_modality
no_ai_ml_dl
no_computer_vision_task
no_original_model_or_evaluation
not_accessible_full_text
not_relevant_after_full_text
duplicate_after_full_text
```

---

# 19. Veri Çıkarım Formu

Dahil edilen her çalışma için aşağıdaki alanlar çıkarılmalıdır:

```text
study_id
first_author
publication_year
title
database_source
doi
journal_or_conference
country
study_type
target_pathology
pathology_group
imaging_modality
ct_type
dataset_name
public_dataset_yes_no
single_center_or_multicenter
number_of_patients
number_of_ct_studies
number_of_images_or_slices
adult_or_pediatric
task_type
model_family
specific_architecture
architecture_extracted_from
baseline_model
training_strategy
augmentation_strategy
external_validation_yes_no
radiologist_comparison_yes_no
open_code_yes_no
open_data_yes_no
performance_metric_auc
performance_metric_accuracy
performance_metric_sensitivity
performance_metric_specificity
performance_metric_precision
performance_metric_recall
performance_metric_f1
performance_metric_dice
performance_metric_iou
performance_metric_map
clinical_use_case
main_findings
limitations_reported_by_authors
reviewer_notes
```

---

# 20. Model Mimarisini Sonradan Kodlama Kuralları

Model mimarisi, ana sorgudan değil, makalenin aşağıdaki bölümlerinden çıkarılmalıdır:

```text
- Başlık
- Özet
- Yöntem bölümü
- Model architecture bölümü
- Experiments / implementation details
- Şekil ve tablo açıklamaları
- Ek materyaller
```

Kodlama yapılırken şu iki alan ayrı tutulmalıdır:

```text
model_family
specific_architecture
```

Örnek:

| model_family | specific_architecture |
|---|---|
| CNN_2D | ResNet-50 |
| CNN_3D | 3D DenseNet |
| UNET | U-Net |
| NNUNET | nnU-Net |
| TRANSFORMER | Swin Transformer |
| DETECTION_MODEL | YOLOv5 |
| SEGMENTATION_FOUNDATION | MedSAM |
| CLASSICAL_ML | Random Forest |
| RADIOMICS_ML | LASSO + SVM |
| HYBRID | CNN + radiomics |
| UNCLEAR | Not clearly reported |

---

# 21. Patoloji Kodlama Şeması

```text
APP = Acute appendicitis
CHO = Acute cholecystitis
PAN = Acute pancreatitis
URO = Urolithiasis / nephrolithiasis / kidney or ureteral stones
DIV = Acute diverticulitis
AAA = Abdominal aortic aneurysm / aortic dissection / acute aortic syndrome
MIX = More than one target pathology
OTHER = Not in target pathology group
```

---

# 22. Görev Kodlama Şeması

```text
DET = Detection / saptama
CLS = Classification / sınıflandırma
SEG = Segmentation / bölütleme
LOC = Localization / lokalizasyon
CAD = Computer-aided diagnosis
PRED = Prediction / risk tahmini
TRIAGE = Triage / önceliklendirme
MULTI = Multiple task
UNCLEAR = Task unclear
```

---

# 23. Mimari Kodlama Şeması

```text
CLASSICAL_ML = Classical machine learning
RADIOMICS_ML = Radiomics + machine learning
CNN_2D = 2D CNN
CNN_3D = 3D CNN
UNET = U-Net family
NNUNET = nnU-Net
DETECTION_MODEL = YOLO / Faster R-CNN / RetinaNet etc.
TRANSFORMER = Transformer-based model
VIT = Vision Transformer
SWIN = Swin Transformer
SAM = Segment Anything / SAM
MEDSAM = MedSAM
MAMBA = Mamba / state-space model
DIFFUSION = Diffusion model
GAN = GAN-based model or GAN augmentation
FEDERATED = Federated learning
MULTIMODAL = Multimodal model
VLM = Vision-language model
LLM_ASSISTED = Large language model assisted workflow
HYBRID = Hybrid architecture
OTHER = Other
UNCLEAR = Not clearly reported
```

---

# 24. Veri Seti Kodlama Şeması

```text
PRIVATE_SINGLE_CENTER = Private single-center dataset
PRIVATE_MULTICENTER = Private multicenter dataset
PUBLIC_DATASET = Public dataset
MIXED_DATASET = Public + private data
SYNTHETIC_DATA = Synthetic or augmented dataset
NOT_REPORTED = Dataset source not reported
```

---

# 25. Performans Ölçütleri Kodlama Şeması

```text
Classification:
- AUC
- Accuracy
- Sensitivity
- Specificity
- Precision
- Recall
- F1-score

Segmentation:
- Dice coefficient
- IoU
- Hausdorff distance
- Volume similarity

Detection:
- mAP
- Precision
- Recall
- F1-score
- False positive rate

Clinical comparison:
- Radiologist comparison
- Reader study
- Time saving
- Triage performance
```

---

# 26. PRISMA-ScR Akış Günlüğü

Aşağıdaki sayılar ayrı ayrı kaydedilmelidir:

```text
records_pubmed
records_arxiv
records_ieee
records_scopus
records_wos
records_total_before_deduplication
duplicates_removed
records_after_deduplication
records_screened_title_abstract
records_excluded_title_abstract
records_for_full_text_assessment
full_texts_not_available
full_texts_excluded
studies_included_final
```

Örnek tablo:

| Aşama | Sayı |
|---|---:|
| PubMed kayıtları |  |
| arXiv kayıtları |  |
| IEEE Xplore kayıtları |  |
| Scopus kayıtları |  |
| Web of Science kayıtları |  |
| Toplam ham kayıt |  |
| Yinelenen kayıtlar |  |
| Tekilleştirme sonrası kayıt |  |
| Başlık/özet taranan kayıt |  |
| Başlık/özet aşamasında dışlanan |  |
| Tam metin incelenen |  |
| Tam metin aşamasında dışlanan |  |
| Nihai dahil edilen çalışma |  |

---

# 27. Kalite Kontrol Listesi

```text
[ ] Her veritabanında 2021–2026 tarih filtresi uygulandı.
[ ] Ana sorgularda mimari terimleri zorunlu bileşen olarak kullanılmadı.
[ ] Her veritabanı için kullanılan sorgu tam metin olarak kaydedildi.
[ ] Ham sonuç sayıları kaydedildi.
[ ] Dışa aktarılan kayıt sayıları kaydedildi.
[ ] Tüm kayıtlar ortak tabloya dönüştürüldü.
[ ] DOI, PMID, arXiv ID ve başlık benzerliği ile tekilleştirme yapıldı.
[ ] Kararsız kayıtlar otomatik dışlanmadı.
[ ] Başlık/özet elemesi tamamlandı.
[ ] Tam metin değerlendirmesi tamamlandı.
[ ] Her çalışma için model mimarisi yöntem bölümünden kodlandı.
[ ] Harici doğrulama durumu kodlandı.
[ ] Açık veri / açık kod durumu kodlandı.
[ ] PRISMA-ScR akış sayıları tamamlandı.
[ ] Veri çıkarım tablosu kontrol edildi.
```

---

# 28. Raporlama İçin Önerilen Bulgular Başlıkları

Makale bulguları aşağıdaki başlıklarla raporlanabilir:

```text
1. Arama sonuçları ve PRISMA-ScR akış süreci
2. Dahil edilen çalışmaların genel özellikleri
3. Yıllara göre yayın eğilimi
4. Patolojiye göre kanıt dağılımı
5. Bilgisayarlı görme görevlerine göre dağılım
6. Kullanılan model mimarileri
7. Veri seti özellikleri
8. Performans ölçütleri
9. Harici doğrulama ve klinik uygulanabilirlik
10. Açık veri, açık kod ve tekrarlanabilirlik
11. Literatürdeki boşluklar
```

---

# 29. Beklenen Ana Çıktılar

Bu tarama sonunda aşağıdaki çıktılar elde edilmelidir:

```text
- Veritabanı bazlı ham kayıt dosyaları
- Birleştirilmiş kayıt tablosu
- Tekilleştirilmiş kayıt tablosu
- Başlık/özet eleme tablosu
- Tam metin eleme tablosu
- Nihai dahil edilen çalışmalar tablosu
- Model mimarisi kodlama tablosu
- PRISMA-ScR akış sayıları
- Makale için bulgulara temel olacak veri çıkarım matrisi
```

---

# 30. Sürüm Bilgisi

```text
Yönerge adı: TR_ABDOMEN_RAD_EMERGENCY_2021_2026_Otomatik_Tarama_Yonergesi_v2
Makale başlığı: Karın Ağrısı için Bilgisayarlı Tomografide Yapay Zeka Uygulamaları: Çoklu Veritabanı Kapsam Belirleme İncelemesi (2021–2026)
Sürüm: v2.0
Hazırlanma tarihi: 2026-05-14
Temel metodolojik karar: Mimari terimleri ana sorguda kullanılmaz; çıkan çalışmalardan sonradan kodlanır.
Veritabanları: PubMed/MEDLINE, arXiv, IEEE Xplore, Scopus, Web of Science
Dil: Türkçe
```

---

# 31. Kaynak Notları

Bu yönergedeki alan kodları ve arama mantığı aşağıdaki veritabanı uygulamaları dikkate alınarak düzenlenmiştir:

```text
PubMed/MEDLINE:
- MeSH terimleri
- Title/Abstract alanı [tiab]
- Publication Date filtresi

arXiv:
- ti: başlık alanı
- abs: özet alanı
- cat: kategori alanı
- submittedDate tarih aralığı

IEEE Xplore:
- All Metadata
- Abstract
- Publication Year filtresi

Scopus:
- TITLE-ABS-KEY
- PUBYEAR

Web of Science:
- TS= Topic alanı
- Timespan filtresi
```
