# Transfer Learning Pipeline: Kaggle RSNA → Local Fine-tuning

## 🎯 Tam Akış

```
┌─────────────────────┐
│  Kaggle Notebook    │ ← RSNA Pretraining (50 epoch)
│ 08_Kaggle_RSNA...   │ → best.pt + results.csv
└──────────┬──────────┘
           │ (download)
           ↓
┌─────────────────────┐
│  Local Machine      │ ← Pretrained weights kopyala
│  09_Transfer...     │ → Fine-tuning (100 epoch)
│                     │ → Validation + Comparison
└─────────────────────┘
```

---

## 📋 Step by Step

### **STEP 1: Kaggle'da RSNA Pretraining**

1. Kaggle'a git: https://www.kaggle.com/
2. "New Notebook" → Python seç
3. "Add Data" → "rsna-2023-abdominal-trauma-detection" search ve ekle
4. Şu dosyayı kopyala: `08_Kaggle_RSNA_Pretraining.py`
5. Tüm hücreleri sırayla çalıştır (HÜCRE 1 → 7)
6. Tamamlandığında (1-2 saat):
   - Outputs klasöründe `rsna_pretrain` klasörü görür
   - İçinde `weights/best.pt` var

**Çıktı:**
- ✅ `best.pt` (YOLOv8m pretrained weights)
- ✅ `results.csv` (training metrics)
- ✅ `confusion_matrix.png`

---

### **STEP 2: Local'e Best.pt Kopyala**

1. Kaggle Notebook → "Output" → "rsna_pretrain" klasörünü indir (ZIP)
2. ZIP'i extract et
3. İçinden şu dosyayı kopyala:
   ```
   rsna_pretrain/weights/best.pt
   ```
4. Local'de şu yere kopyala:
   ```
   outputs/runs/pretraining/best.pt
   ```
   
   Klasör yoksa oluştur:
   ```bash
   mkdir -p outputs/runs/pretraining/
   cp ~/Downloads/best.pt outputs/runs/pretraining/
   ```

---

### **STEP 3: Local Fine-tuning & Validation**

```bash
# Venv'i activate et
source .venv/bin/activate

# Fine-tuning başlat (100 epoch)
python 09_Transfer_Learning_Pipeline.py
```

**Ne yapacak:**
- ✅ Pretrained ağı yükle (`best.pt`)
- ✅ Kendi veri seti ile fine-tune et (100 epoch)
- ✅ Validation seti üzerinde test et
- ✅ Kaggle Pretraining vs Local Fine-tuning karşılaştır
- ✅ Metrikleri save et

**Çıktı Dizini:** `transfer_learning_results/`
- `finetuned_yolov8m/weights/best.pt` → Final model
- `validation_results.csv` → Test tahminleri
- `comparison.csv` → Pretraining vs Fine-tuning metrikler
- `comparison.png` → Görselleştirme
- `pipeline.log` → Tüm loglar

---

## 📊 Beklenen Sonuçlar

```
RSNA Pretraining (Kaggle, 50 epoch):
  mAP50: 0.65-0.70
  mAP50-95: 0.45-0.50
  → Genel abdominal patoloji öğrendi

Local Fine-tuning (100 epoch):
  mAP50: 0.75-0.80 (↑ 10-15%)
  mAP50-95: 0.55-0.60 (↑ 15-20%)
  F1_diverticulitis: 0.45+ (baseline 0.18'den çok daha iyi!)
  → Domain-specific, weak classes iyileşti
```

---

## ⏱️ Zaman Tahmini

| Aşama | Süre | Nerede |
|-------|------|--------|
| **Kaggle Pretraining** | 1-2 saat | Kaggle GPU |
| **Download** | 5-10 dakika | - |
| **Local Fine-tuning** | 6-8 saat | Mac M5 MPS |
| **Total** | ~12 saat | - |

---

## 🔧 Konfigürasyon

Şu parametreleri değiştirebilirsin (09_Transfer_Learning_Pipeline.py içinde):

```python
class Config:
    EPOCHS_FINETUNE = 100      # ← Epoch sayısı
    BATCH_SIZE = 16            # ← Batch size
    LR0 = 0.001               # ← Learning rate (pretrained için düşük)
    IMG_SIZE = 640            # ← Image size
    
    # Class weights (zayıf sınıflara daha yüksek)
    CLASS_WEIGHTS = {
        'acute_diverticulitis': 5.0,  # ← En zayıf sınıf
        'acute_appendicitis': 2.0,
        ...
    }
```

---

## 📝 Workflow Özet

```
1. Kaggle: RSNA Pretraining
   ↓ İndir best.pt
2. Local: Kopyala outputs/runs/pretraining/
   ↓ Çalıştır 09_Transfer_Learning_Pipeline.py
3. Local: Fine-tuning + Validation
   ↓ Sonuçları karşılaştır
4. Result: transfer_learning_results/best.pt
   ↓ Production Model Hazır!
```

---

## ✅ Checklist

- [ ] Kaggle API kuruluşu (`kaggle.json`)
- [ ] Kaggle'da RSNA veri seti ekle
- [ ] `08_Kaggle_RSNA_Pretraining.py` çalıştır
- [ ] `best.pt` indir
- [ ] `outputs/runs/pretraining/best.pt` kopyala
- [ ] `04_prepare_yolo.py` çalıştır (kendi veri seti için)
- [ ] `python 09_Transfer_Learning_Pipeline.py` çalıştır
- [ ] Sonuçları `transfer_learning_results/` klasöründe kontrol et

---

## 🆘 Troubleshooting

### Problem: "Pretrained weights bulunamadı"
**Çözüm:** `outputs/runs/pretraining/best.pt` kontrol et
```bash
ls -la outputs/runs/pretraining/
```

### Problem: "dataset.yaml bulunamadı"
**Çözüm:** Önce `04_prepare_yolo.py` çalıştır
```bash
python src/detection.py
```

### Problem: Kaggle download timeout
**Çözüm:** Terminal'de manuel indir
```bash
kaggle notebooks list --limit 100
kaggle notebooks output -p <notebook-id> -p outputs.zip
```

---

## 📚 Files Reference

| File | Amaç | Çalıştırılacak Yer |
|------|------|----------------|
| `08_Kaggle_RSNA_Pretraining.py` | RSNA Pretraining script | Kaggle Notebook |
| `09_Transfer_Learning_Pipeline.py` | Fine-tuning + Validation | Local Terminal |
| `04_prepare_yolo.py` | Kendi veri seti hazırla | Local (gerekli) |
| `src/detection.py` | Yardımcı modüller | Import |

---

**İyi çalışmalar! 🚀**
