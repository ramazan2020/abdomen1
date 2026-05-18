"""
KAGGLE NOTEBOOK SCRIPT - RSNA YOLOV8 PRETRAINING
================================================

Kaggle'da yeni notebook oluştur ve tüm hücreleri aşağıdaki sırayla çalıştır.
Bu script RSNA veri setinden YOLOv8 pretraining yapacak.

Çıktılar:
  - best.pt (pretrained weights)
  - results.csv (training metrics)
  - confusion_matrix.png

Kullanım:
  1. Kaggle'da "New Notebook" → "Add Data" → RSNA veri seti seç
  2. Bu dosyayı Kaggle notebook'a kopyala
  3. Her hücreyi sırayla çalıştır
  4. best.pt'yi indir → local'e kopyala
"""

# ============================================================================
# HÜCRE 1: SETUP & IMPORTS
# ============================================================================

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import torch
from ultralytics import YOLO
import yaml
from tqdm import tqdm
import shutil
import pydicom
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
from sklearn.model_selection import train_test_split

print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Device: {'GPU' if torch.cuda.is_available() else 'CPU'}")

# Kaggle paths
BASE = Path("/kaggle/input")
RSNA_DIR = BASE / "rsna-2023-abdominal-trauma-detection"
OUTPUT_DIR = Path("/kaggle/working/rsna_pretrain_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"\nInput:  {RSNA_DIR}")
print(f"Output: {OUTPUT_DIR}")

# ============================================================================
# HÜCRE 2: RSNA CSV ANALIZ
# ============================================================================

rsna_csv = RSNA_DIR / "train.csv"
rsna_images = RSNA_DIR / "train_images"

print(f"\n{'='*80}")
print("CSV ANALİZ")
print(f"{'='*80}")

print(f"CSV exists: {rsna_csv.exists()}")
print(f"Images dir exists: {rsna_images.exists()}")

if rsna_csv.exists():
    df = pd.read_csv(rsna_csv)
    print(f"\nRSNA Dataset:")
    print(f"  Satırlar: {len(df)}")
    print(f"  Sütunlar: {list(df.columns)}")
    print(f"\nİlk 5 satır:")
    print(df.head())
    print(f"\nİstatistik:")
    print(df[['liver_injury', 'kidney_injury', 'spleen_injury']].describe())

# ============================================================================
# HÜCRE 3: SINIF MAPPING
# ============================================================================

print(f"\n{'='*80}")
print("SINIF MAPPING: RSNA → 6 SINIF")
print(f"{'='*80}")

def map_rsna_to_classes(row):
    """RSNA injury severity → 6 sınıf mapping"""
    liver = row.get('liver_injury', 0)
    kidney = row.get('kidney_injury', 0)
    spleen = row.get('spleen_injury', 0)
    bowel = row.get('bowel_injury', 0)
    extravasation = row.get('extravasation_injury', 0)
    
    max_sev = max([liver, kidney, spleen, bowel, extravasation])
    
    # Yüksek severity → zayıf sınıflara
    if max_sev >= 4:
        return 'acute_appendicitis'
    elif max_sev == 3:
        return 'acute_diverticulitis'
    elif max_sev == 2:
        return 'kidney_ureter_stone'
    elif kidney > 0 or spleen > 0:
        return 'acute_pancreatitis'
    elif liver > 0:
        return 'acute_cholecystitis'
    else:
        return 'aortic_aneurysm_dissection'

df['class'] = df.apply(map_rsna_to_classes, axis=1)

print("Sınıf dağılımı:")
print(df['class'].value_counts())
print(f"\nEn az veri: {df['class'].value_counts().min()} veri/sınıf")
print(f"En çok veri: {df['class'].value_counts().max()} veri/sınıf")

# ============================================================================
# HÜCRE 4: DICOM → PNG + YOLO LABEL
# ============================================================================

print(f"\n{'='*80}")
print("DICOM → YOLO FORMAT DÖNÜŞÜMÜ")
print(f"{'='*80}")

def process_dicom(args):
    """DICOM'u PNG'ye dönüştür ve etiketlendir"""
    dcm_path, target_class, out_dir = args
    
    try:
        # DICOM oku
        dcm = pydicom.dcmread(dcm_path)
        img = dcm.pixel_array.astype(np.float32)
        
        # HU conversion
        if hasattr(dcm, 'RescaleIntercept') and hasattr(dcm, 'RescaleSlope'):
            img = img * dcm.RescaleSlope + dcm.RescaleIntercept
        
        # 3-channel windowing
        windowing = {
            'soft_tissue': (40, 400),
            'liver': (30, 150),
            'calcified': (450, 1500)
        }
        
        channels = []
        for name, (level, width) in windowing.items():
            windowed = np.clip((img - level) / width * 255 + 127, 0, 255).astype(np.uint8)
            channels.append(windowed)
        
        # HWC format
        img_3ch = np.transpose(np.stack(channels, axis=0), (1, 2, 0))
        
        # PNG kaydet
        cls_dir = out_dir / 'images' / 'train'
        cls_dir.mkdir(parents=True, exist_ok=True)
        png_path = cls_dir / f"{dcm_path.stem}.png"
        Image.fromarray(img_3ch).save(str(png_path))
        
        # Etiket
        lbl_dir = out_dir / 'labels' / 'train'
        lbl_dir.mkdir(parents=True, exist_ok=True)
        
        class_id = {
            'acute_appendicitis': 0,
            'acute_cholecystitis': 1,
            'acute_diverticulitis': 2,
            'acute_pancreatitis': 3,
            'aortic_aneurysm_dissection': 4,
            'kidney_ureter_stone': 5,
        }[target_class]
        
        lbl_path = lbl_dir / f"{dcm_path.stem}.txt"
        lbl_path.write_text(str(class_id))
        
        return True, None
    
    except Exception as e:
        return False, str(e)

# DICOM dosyaları topla
dicom_files = sorted(rsna_images.glob('*/*.dcm'))
print(f"\nToplam DICOM: {len(dicom_files)}")

# İlk 1000 işle (tamamını almak için tüm dosyaları kullan)
limit = min(1000, len(dicom_files))
print(f"Processing: {limit} file (test için. Üretim: tüm dosyaları kullan)")

yolo_dir = OUTPUT_DIR / 'dataset'

# Class → DICOM mapping
dicom_class_map = {}
for idx, row in df.iterrows():
    patient = str(row['patient_id'])
    cls = row['class']
    for dcm in rsna_images.glob(f'{patient}/**/*.dcm'):
        dicom_class_map[dcm] = cls

# Parallel processing
tasks = [(dcm, dicom_class_map.get(dcm, 'unknown'), yolo_dir) 
         for dcm in dicom_files[:limit]]

print(f"\nParallel processing ({limit} files)...")
with ProcessPoolExecutor(max_workers=4) as ex:
    results = list(tqdm(ex.map(process_dicom, tasks), total=len(tasks)))

success = sum(1 for ok, _ in results if ok)
errors = [(_, err) for ok, err in results if not ok]

print(f"✓ Başarılı: {success}/{len(tasks)}")
if errors:
    print(f"✗ Hata: {len(errors)}")

# ============================================================================
# HÜCRE 5: TRAIN-VAL SPLIT & dataset.yaml
# ============================================================================

print(f"\n{'='*80}")
print("TRAIN-VAL SPLIT & dataset.yaml")
print(f"{'='*80}")

train_imgs = sorted((yolo_dir / 'images' / 'train').glob('*.png'))
print(f"\nToplam PNG: {len(train_imgs)}")

# 85-15 split
train_files, val_files = train_test_split(
    train_imgs, 
    test_size=0.15, 
    random_state=42
)

print(f"Train: {len(train_files)}")
print(f"Val:   {len(val_files)}")

# Val klasörü oluştur
(yolo_dir / 'images' / 'val').mkdir(parents=True, exist_ok=True)
(yolo_dir / 'labels' / 'val').mkdir(parents=True, exist_ok=True)

print("\nVal dosyaları taşınıyor...")
for img in tqdm(val_files):
    shutil.move(str(img), str(yolo_dir / 'images' / 'val' / img.name))
    lbl = yolo_dir / 'labels' / 'train' / f"{img.stem}.txt"
    if lbl.exists():
        shutil.move(str(lbl), str(yolo_dir / 'labels' / 'val' / lbl.name))

# dataset.yaml
yaml_content = {
    'path': str(yolo_dir),
    'train': 'images/train',
    'val': 'images/val',
    'nc': 6,
    'names': {
        0: 'acute_appendicitis',
        1: 'acute_cholecystitis',
        2: 'acute_diverticulitis',
        3: 'acute_pancreatitis',
        4: 'aortic_aneurysm_dissection',
        5: 'kidney_ureter_stone'
    }
}

yaml_path = yolo_dir / 'dataset.yaml'
with open(yaml_path, 'w') as f:
    yaml.dump(yaml_content, f)

print(f"✓ dataset.yaml created: {yaml_path}")

# ============================================================================
# HÜCRE 6: YOLOV8 PRETRAINING
# ============================================================================

print(f"\n{'='*80}")
print("STAGE 1: RSNA PRETRAINING (YOLOv8)")
print(f"{'='*80}\n")

model = YOLO('yolov8m.pt')

results = model.train(
    data=str(yaml_path),
    epochs=50,
    imgsz=640,
    batch=16,
    device=0 if torch.cuda.is_available() else 'cpu',
    project=str(OUTPUT_DIR),
    name='rsna_pretrain',
    save=True,
    patience=20,
    verbose=True,
    augment=True,
    mixup=0.1,
    mosaic=1.0,
    lr0=0.01,
    lrf=0.0001,
    warmup_epochs=3,
    # Focal loss for imbalanced data
    focal_loss=True,
)

print(f"\n{'='*80}")
print("✓ PRETRAINING TAMAMLANDI")
print(f"{'='*80}\n")

# ============================================================================
# HÜCRE 7: SAVE & DOWNLOAD
# ============================================================================

best_pt = OUTPUT_DIR / 'rsna_pretrain' / 'weights' / 'best.pt'
results_csv = OUTPUT_DIR / 'rsna_pretrain' / 'results.csv'
confusion_matrix = OUTPUT_DIR / 'rsna_pretrain' / 'confusion_matrix.png'

print(f"\n{'='*80}")
print("ÇIKTI DOSYALARI (İNDİR)")
print(f"{'='*80}\n")

print(f"1. Best Weights (KOPYALA KENDİ LOCAL'E):")
print(f"   {best_pt}\n")

print(f"2. Training Results (Metrics):")
print(f"   {results_csv}\n")

print(f"3. Confusion Matrix:")
print(f"   {confusion_matrix}\n")

if results_csv.exists():
    df_results = pd.read_csv(results_csv)
    print("Son epoch metrikleri:")
    last_row = df_results.iloc[-1]
    for col in df_results.columns:
        if 'epoch' not in col.lower():
            val = last_row[col]
            if isinstance(val, (int, float)):
                print(f"  {col}: {val:.4f}")

print(f"\n{'='*80}")
print("İNDİRME TALİMATLARI")
print(f"{'='*80}\n")

print("""
1. Kaggle Output klasöründe sağ üstteki "Download" tıkla
2. ZIP dosyasını local'e indir
3. Şu dosyaları local'e kopyala:
   - outputs/rsna_pretrain/weights/best.pt
     → OUTPUTS_DIR / 'runs' / 'pretraining' / 'best.pt'
   
   - outputs/rsna_pretrain/results.csv
     → İsteğe bağlı (karşılaştırma için)

4. Local'de çalıştır:
   python 09_Transfer_Learning_Pipeline.py
""")
