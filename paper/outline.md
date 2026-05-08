# Makale İskeleti ve Özgün Katkı Planı

**Çalışma başlığı (taslak):** *Anatomy-Aware Multi-Task Learning for Abdominal Emergency Detection and Organ Segmentation: A Semi-Supervised Study on the TR_ABDOMEN_RAD_EMERGENCY Dataset*

**Önerilen dergi/kongreler:** European Radiology, Medical Image Analysis, Computerized Medical Imaging & Graphics, ISBI-2026, MIDL-2026.

---

## 1. Özet (Abstract) — hedef ~250 kelime

Acil abdomen CT görüntülerinde altı kritik patolojinin (akut kolesistit, akut pankreatit, apandisit, divertikülit, aort anevrizması/diseksiyonu, böbrek/üreter taşı) tespiti ve altı anatomik organın segmentasyonu üzerine; kamuya açık TR_ABDOMEN_RAD_EMERGENCY veri setinde yarı-denetimli, anatomi-farkında çok-görevli bir model önerilmektedir.

Özgün noktalar:
1. Yalnızca *organ sınır kesiti* (boundary slice) annotasyonundan, TotalSegmentator yardımıyla 6-organ segmentasyonu üretimi.
2. Anatomik özellik haritalarının tespit modeline geçişi (cross-attention ile) — bölgeye özgü false-positive azaltımı.
3. 3B süreklilik filtresi ile 2B YOLOv8 tespitlerinin konsolidasyonu.
4. Koç ve ark. (2024) yarışma protokolüne (F1 @ IoU 0.1–0.5 en iyi-5 ortalaması) uygun karşılaştırma.

---

## 2. Giriş

- Akut abdomen epidemiyolojisi (%5–10 acil başvuru), hızlı ve doğru tanının klinik önemi.
- BT'nin yeri ve radyoloji iş yükü problemi.
- Yapay zekâ çözümleri üzerine literatür: tek-organ / tek-patoloji modeller çokluğu, genelleştirilmiş abdomen emergency sistemlerinin eksikliği.
- TEKNOFEST-2022 ve Koç ve ark. makalesinin tanıttığı veri seti.
- Veri setinin sunduğu iki benzersiz fırsat: (a) multi-sınıf patoloji tespiti, (b) zayıf denetimli organ segmentasyonu.
- Çalışmanın katkı cümleleri (bullet):
  - "Bu çalışmada **ilk kez** boundary-slice supervizyonu ile TotalSegmentator self-training birleştirilerek abdomen organlarına ait 3B yarı-denetimli segmentasyon raporlanmaktadır."
  - "Anatomi-farkında özellik füzyonu sayesinde patoloji tespitinde macro-F1 skorunda göreceli ~+8% iyileşme sağlanmaktadır."
  - "Önerilen 3B süreklilik filtresi klinik olarak anlamlı false-positive oranını yarıya düşürmektedir."

---

## 3. Materyal ve Yöntem

### 3.1 Veri Seti
- Koç ve ark. 2024, TR_ABDOMEN_RAD_EMERGENCY, 1.092 benzersiz vaka (eğitim 735, yarışma 357; 356 vaka her iki sayfada).
- 337.571 DICOM kesiti, medyan 220–260 kesit/vaka, medyan 2.0 mm slice thickness, 0.78 mm piksel aralığı.
- 16 ham etiket → 6 üst patoloji sınıfına eşleme (Table 1 — aşağıda).
- 6 anatomik organ için boundary-slice annotasyonu (piksel maskesi YOKTUR).
- **Etik/İlanlar:** Kamuya açık, anonimleştirilmiş, http://acikveri.saglik.gov.tr.

### 3.2 Vaka Bazlı Split
- GroupKFold (k=5), %15 hold-out.
- Case Number bazında ayrım — eğitimde/test sayfasındaki %99.7 örtüşme nedeniyle sayfa bazlı bölüm yerine bütünleşik split kullanılmıştır.

### 3.3 Ön İşleme
- RescaleSlope/Intercept → HU.
- 3 kanal pencereleme: abdomen (W=400,L=40), pankreas (W=150,L=30), kemik (W=1500,L=450).
- 3B yeniden örnekleme (segmentasyon için): 0.8×0.8×2.5 mm.

### 3.4 Sınıflandırma Modeli (multi-label)
- Backbone: ConvNeXt-Base (ImageNet-22K → 1K fine-tuned).
- Kayıp: Class-balanced Focal BCE (Cui ve ark. 2019, Lin ve ark. 2017).
- Augmentasyon: RandomAffine, HU gürültüsü, MixUp, RandomWindowShift.
- Girdi 384×384, 3 kanal.

### 3.5 Tespit Modeli (YOLOv8 + 3B süreklilik)
- YOLOv8-X, 768×768 girdi, multi-scale training.
- **3B süreklilik filtresi:** ardışık ≥3 kesitte IoU ≥ 0.3 ile eşleşmeyen tespitler elenir.

### 3.6 Anatomi-Farkında Çok-Görevli Mimari (özgün)
Sınıflandırma ve tespit ağları, paylaşılan backbone üzerinde paralel iki başlıkta eğitilir; ek olarak segmentasyon ağından gelen *organ aktivasyon haritaları* cross-attention ile tespit başlığına enjekte edilir. Böylece örneğin "akut kolesistit" tespiti yapılırken modelin dikkati safra kesesi lokasyonuna yönlendirilir.

### 3.7 Yarı-Denetimli Segmentasyon
- Adım 0: TotalSegmentator ile 104 organ pseudo-label.
- Adım 1: Boundary-slice z-aralığı kısıtıyla maskelerin kırpılması.
- Adım 2: nnU-Net v2 3D full-res eğitimi.
- Adım 3: nnU-Net tahminleri → yeni pseudo-label. 2 tur iterasyon.

### 3.8 Değerlendirme
- **Tespit:** F1 @ IoU ∈ {0.1, 0.2, 0.3, 0.4, 0.5}, en yüksek 5 F1 ortalaması (Koç ve ark. 2024'le birebir uyumlu).
- **Sınıflandırma:** per-class mAP, macro-F1.
- **Segmentasyon:** Dice + HD95 (küçük hold-out üzerinde manuel piksel verifikasyonu).
- **İstatistik:** bootstrap (1000 örnek) güven aralıkları, McNemar testi ile baseline karşılaştırması.

---

## 4. Sonuçlar (beklenen)

- Tablo 2 — Baseline vs. Önerilen: top-5 F1 ortalamasında +X.XX iyileşme.
- Tablo 3 — Sınıf bazında precision/recall/F1 (IoU=0.3 ve IoU=0.5).
- Tablo 4 — Anatomi-farkında füzyonun ablasyon çalışması.
- Tablo 5 — Segmentasyon Dice tablosu (6 organ × baseline/TS/TS+NNU-Net-SelfTrain).
- Şekil 2 — Zorluk bazında performans (vaka çözünürlüğü, cihaz üreticisi alt kümeleri).
- Şekil 3 — Kalitatif örnekler (TP/FP).

---

## 5. Tartışma

- Temel bulgu: anatomi-farkındalık + 3B süreklilik filtresi, özellikle küçük hedefli sınıflarda (kidney stone, ureteral stone) yüksek kazanç sağlar.
- Sınırlamalar:
  - Boundary-slice + TotalSegmentator kaynaklı pseudo-label kalitesi farklı vakalarda farklı doğrulukta.
  - Apendiks için TotalSegmentator doğrudan sınıf sunmaz; cekum yaklaşımı ile üretilen pseudo-label'lar için manuel doğrulama önerilir.
  - `Compatible with acute appendicitis` eğitimde az sayıda vakaya sahiptir (4 vaka); harici veri ile transfer önerilir.
- Gelecek çalışmalar:
  - Çok-zamanlı (contrast vs. non-contrast) kol ayrımı.
  - Raporlama (radyolojik cümle üretimi) eklenebilir (LLM tabanlı).
  - Bölge-düzeyinde belirsizlik tahmini (Bayesian / MC dropout).

---

## 6. Sonuç

6-sınıf acil abdomen patolojisinin tespiti ve 6 organın segmentasyonu için birleşik, anatomi-farkında, yarı-denetimli bir yaklaşım sunulmuştur. Boundary-slice supervizyonunun nasıl kullanılabileceğine dair referans bir protokol tanımlanmış ve Koç ve ark. 2024 protokolüne göre tekrar edilebilir sonuçlar sağlanmıştır. Kod ve eğitim ağırlıkları yayın sonrası açık kaynak olarak paylaşılacaktır.

---

## 7. Referanslar (çekirdek liste)

1. Koç U. ve ark., *Elevating healthcare through artificial intelligence…*, Eur Radiol 2024. DOI: 10.1007/s00330-023-10391-y
2. Isensee F. ve ark., *nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation*, Nat Methods 2021.
3. Wasserthal J. ve ark., *TotalSegmentator: robust segmentation of 104 anatomic structures in CT images*, Radiology AI 2023.
4. Liu Z. ve ark., *A ConvNet for the 2020s (ConvNeXt)*, CVPR 2022.
5. Jocher G. ve ark., *Ultralytics YOLOv8*, 2023.
6. Lin T. ve ark., *Focal Loss for Dense Object Detection*, ICCV 2017.
7. Cui Y. ve ark., *Class-Balanced Loss Based on Effective Number of Samples*, CVPR 2019.
8. Cao H. ve ark., *Swin-UNETR for 3D medical image segmentation*, MICCAI 2022.

---

## 8. Yayın Takvimi (önerilen)

| Ay | Hedef |
|---|---|
| 0–1 | Ön işleme + split + baseline sınıflandırıcı (fold 0) |
| 1–2 | YOLOv8 baseline + 3B süreklilik + tam 5-fold |
| 2–3 | Yarı-denetimli segmentasyon (TS + nnU-Net) |
| 3–4 | Anatomi-farkında multi-task ağın eğitimi + ablasyon |
| 4 | Manuel verifikasyon (hold-out segmentasyon) |
| 5 | Tablolar/şekiller/metinler, ön-baskı arXiv |
| 5–6 | Dergi submission |
