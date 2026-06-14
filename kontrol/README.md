# TR_ABDOMEN_RAD_EMERGENCY — Deney Çerçevesi

Koç U. ve ark. 2024 (TEKNOFEST-2022 acil abdomen BT veri seti) üzerinde
**6-sınıf patoloji tespiti**, **multi-label sınıflandırma** ve **6-organ yarı-denetimli segmentasyonu** için uçtan uca, tekrar üretilebilir pipeline.

## Dizin yapısı

```
abdomen_project/
├── src/
│   ├── config.py            # Yollar, sınıf haritası, pencere ayarları, hiperparametreler
│   ├── dicom_utils.py       # DICOM I/O, HU, windowing, resampling, bbox parse
│   ├── splits.py            # Vaka bazlı GroupKFold + hold-out
│   ├── preprocessing.py     # Manifest üretimi + NPZ kesit dışa aktarımı
│   ├── datasets.py          # PyTorch Dataset (multi-label)
│   ├── losses.py            # Focal BCE + class-balanced alpha
│   ├── train_cls.py         # ConvNeXt multi-label eğitimi (tek fold)
│   ├── detection.py         # YOLOv8 dataset + eğitim + 3B post-processing
│   ├── evaluation.py        # F1 @ IoU top-5 metriği (makale protokolüne uygun)
│   └── segmentation.py      # TotalSegmentator → nnU-Net self-training
├── scripts/
│   ├── 01_split.py
│   ├── 02_preprocess.py
│   ├── 03_train_cls.py
│   ├── 04_prepare_yolo.py
│   ├── 05_train_yolo.py
│   ├── 06_prepare_seg.py
│   └── 07_train_seg.py
├── paper/outline.md         # Makale iskeleti & özgün katkı planı
├── configs/                 # (YAML override dosyaları buraya)
└── requirements.txt
```

## Hızlı Başlangıç

```bash
cd abdomen_project
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 1) Split + manifest
```bash
python scripts/01_split.py
python scripts/02_preprocess.py --only manifest
```

### 2) Sınıflandırma için NPZ kesitlerini dışa aktar
```bash
python scripts/02_preprocess.py --only export --negatives 10
# (her vakadan 10 rastgele annotasyonsuz kesit eklenir → hard-negative)
```

### 3) ConvNeXt eğitimi (fold 0)
```bash
python scripts/03_train_cls.py --fold 0 --epochs 40 --batch 32
```

### 4) YOLOv8 tespiti
```bash
python abdomen_project/scripts/04_prepare_yolo.py --fold 0
python abdomen_project/scripts/05_train_yolo.py --fold 0
```

### 5) Yarı-denetimli segmentasyon
Önkoşul: `nnUNetv2_*` komut satırı araçlarının path'te olması; nnU-Net
ortam değişkenleri `nnUNet_raw`, `nnUNet_preprocessed`, `nnUNet_results`.

```bash
export nnUNet_raw=$PWD/outputs/seg_data/nnUNet_raw
export nnUNet_preprocessed=$PWD/outputs/seg_data/nnUNet_preprocessed
export nnUNet_results=$PWD/outputs/seg_data/nnUNet_results

python scripts/06_prepare_seg.py            # Tüm vakalar için pseudo-label
python scripts/07_train_seg.py --iters 2    # nnU-Net self-training
```

## Önemli tasarım kararları

| Konu | Karar | Gerekçe |
|---|---|---|
| Split | Vaka bazlı GroupKFold | Bilgi.xlsx'te eğitim/yarışma sayfaları %99.7 vaka örtüşmesine sahip → sayfa bazlı split **data leakage** üretir. |
| Sınıf uzayı | 16 ham → 6 üst | Test setinde `Gallbladder stone`, `ureteral stone`, `Aortic dissection`, `Calcified diverticulum` yok; makaledeki 6 üst sınıfa uyum. |
| Pencereleme | 3 kanal (abdomen/pankreas/kemik) | Küçük kalsifikasyon ve taşlar kemik, pankreatit yumuşak doku penceresinde belirgin. |
| Loss | Class-balanced Focal BCE | Aort anevrizması + pankreatit hakim; divertikülit/apandisit nadir. |
| Detection post-processing | 3 kesit süreklilik kuralı | 2B YOLO tek-kesit false-positive'lerini yarıya indirir. |
| Segmentasyon | TS + boundary-slice kırpma + nnU-Net self-training | Boundary Slice etiketleri piksel maskesi değildir; TotalSegmentator'un güçlü ön-bilgisi boundary-slice ile kısıtlanarak öğretilir. |

## Değerlendirme

Makaleye (Koç 2024) uygun F1 @ IoU ∈ {0.1, 0.2, 0.3, 0.4, 0.5}, en yüksek 5 F1
ortalaması. `src/evaluation.py` → `top5_f1_mean()`.

## Atıf

Bu veri setini veya bu iskeleti kullanıyorsanız **Koç U. ve ark., *Elevating
healthcare through artificial intelligence: analyzing the abdominal emergencies
data set (TR_ABDOMEN_RAD_EMERGENCY) at TEKNOFEST-2022*, European Radiology
34:3588–3597 (2024).** DOI: [10.1007/s00330-023-10391-y](https://doi.org/10.1007/s00330-023-10391-y) makalesine atıf yapmanız gereklidir.

## Lisans ve veri sorumluluğu

Veri seti T.C. Sağlık Bakanlığı açık veri portalından (http://acikveri.saglik.gov.tr)
sağlanmıştır; kullanım koşulları veri paylaşım protokolüne tabidir. Bu kod
MIT lisansı ile sağlanır; veri seti için ayrı şartlar geçerlidir.
