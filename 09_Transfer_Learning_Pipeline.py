#!/usr/bin/env python3
"""
Transfer Learning Pipeline: RSNA Pretraining + Local Fine-tuning + Validation
================================================================================

Kullanım:
  1. Kaggle'da RSNA Pretraining yap → best.pt indir
  2. Local'de: python 09_Transfer_Learning_Pipeline.py
  
Aşamalar:
  - Stage 1: Kaggle RSNA Pretraining (best.pt üretir)
  - Stage 2: Local Fine-tuning (Kendi veri seti ile)
  - Stage 3: Validation & Comparison
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import torch
from ultralytics import YOLO
import yaml
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import json
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    # Paths
    BASE = Path('.').resolve()
    TRAIN_DIR = BASE / 'Eğitim Verisi'
    TEST_DIR = BASE / 'Yarışma Veri Seti'
    OUTPUTS_DIR = BASE / 'outputs'
    
    # Pretraining weights (Kaggle'dan indir)
    PRETRAINED_WEIGHTS = OUTPUTS_DIR / 'runs' / 'pretraining' / 'best.pt'
    
    # Output directories
    FINETUNE_OUTPUT = OUTPUTS_DIR / 'runs' / 'transfer_learning'
    VALIDATION_OUTPUT = BASE / 'transfer_learning_results'
    
    # Training params
    IMG_SIZE = 640
    BATCH_SIZE = 16
    EPOCHS_FINETUNE = 100
    LR0 = 0.001  # Lower LR for fine-tuning
    LR_FINAL = 0.00001
    PATIENCE = 25
    
    # Class info
    CLASSES = {
        0: 'acute_appendicitis',
        1: 'acute_cholecystitis',
        2: 'acute_diverticulitis',
        3: 'acute_pancreatitis',
        4: 'aortic_aneurysm_dissection',
        5: 'kidney_ureter_stone',
    }
    
    # Class weights (zayıf sınıflara daha yüksek ağırlık)
    CLASS_WEIGHTS = {
        'acute_appendicitis': 2.0,
        'acute_cholecystitis': 1.0,
        'acute_diverticulitis': 5.0,  # En zayıf sınıf
        'acute_pancreatitis': 1.5,
        'aortic_aneurysm_dissection': 1.0,
        'kidney_ureter_stone': 1.5,
    }

cfg = Config()

# ============================================================================
# LOGGER
# ============================================================================

class Logger:
    def __init__(self, logfile):
        self.logfile = Path(logfile)
        self.logfile.parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_msg = f"[{timestamp}] {msg}"
        print(full_msg)
        with open(self.logfile, 'a') as f:
            f.write(full_msg + '\n')

# ============================================================================
# STAGE 2: FINE-TUNING
# ============================================================================

def stage_2_finetuning(logger):
    """
    Pretrained ağı kendi veri seti ile fine-tune et
    """
    logger.log("=" * 80)
    logger.log("STAGE 2: LOCAL FINE-TUNING")
    logger.log("=" * 80)
    
    # Paths
    det_data_dir = cfg.OUTPUTS_DIR / 'det_data' / 'fold0'
    dataset_yaml = det_data_dir / 'dataset.yaml'
    
    logger.log(f"Dataset: {dataset_yaml}")
    logger.log(f"Pretrained: {cfg.PRETRAINED_WEIGHTS}")
    
    # Check files
    if not dataset_yaml.exists():
        logger.log("❌ HATA: dataset.yaml bulunamadı. Önce [4] (04_prepare_yolo.py) çalıştırın.")
        return False
    
    if not cfg.PRETRAINED_WEIGHTS.exists():
        logger.log(f"❌ HATA: Pretrained weights bulunamadı: {cfg.PRETRAINED_WEIGHTS}")
        logger.log("   Kaggle'da pretraining yapıp best.pt'yi indir.")
        return False
    
    logger.log(f"✓ Dataset hazır")
    logger.log(f"✓ Pretrained weights mevcut")
    
    # Load pretrained model
    logger.log("\nModel yükleniyor (pretrained)...")
    model = YOLO(str(cfg.PRETRAINED_WEIGHTS))
    
    # Fine-tune
    cfg.FINETUNE_OUTPUT.mkdir(parents=True, exist_ok=True)
    
    logger.log(f"\nFine-tuning başlıyor:")
    logger.log(f"  Epochs: {cfg.EPOCHS_FINETUNE}")
    logger.log(f"  Learning Rate: {cfg.LR0} → {cfg.LR_FINAL}")
    logger.log(f"  Batch Size: {cfg.BATCH_SIZE}")
    logger.log(f"  Device: {'MPS' if torch.backends.mps.is_available() else 'CPU'}")
    
    results = model.train(
        data=str(dataset_yaml),
        epochs=cfg.EPOCHS_FINETUNE,
        imgsz=cfg.IMG_SIZE,
        batch=cfg.BATCH_SIZE,
        device='mps' if torch.backends.mps.is_available() else 'cpu',
        project=str(cfg.FINETUNE_OUTPUT),
        name='finetuned_yolov8m',
        save=True,
        patience=cfg.PATIENCE,
        verbose=True,
        # Lower LR for fine-tuning
        lr0=cfg.LR0,
        lrf=cfg.LR_FINAL,
        warmup_epochs=3,
        # Augmentation
        augment=True,
        mixup=0.2,
        mosaic=1.0,
        # Loss settings
        focal_loss=True,
    )
    
    best_pt = cfg.FINETUNE_OUTPUT / 'finetuned_yolov8m' / 'weights' / 'best.pt'
    logger.log(f"\n✓ Fine-tuning tamamlandı")
    logger.log(f"  Best weights: {best_pt}")
    
    return best_pt

# ============================================================================
# STAGE 3: VALIDATION
# ============================================================================

def stage_3_validation(best_pt_finetuned, logger):
    """
    Fine-tuned model'i test seti üzerinde validasyona tabi tut
    """
    logger.log("\n" + "=" * 80)
    logger.log("STAGE 3: VALIDATION & COMPARISON")
    logger.log("=" * 80)
    
    if not best_pt_finetuned.exists():
        logger.log(f"❌ HATA: Fine-tuned model bulunamadı: {best_pt_finetuned}")
        return False
    
    # Val set images
    val_imgs = sorted((cfg.OUTPUTS_DIR / 'det_data' / 'fold0' / 'images' / 'val').glob('*.png'))
    
    if not val_imgs:
        logger.log("❌ HATA: Val images bulunamadı")
        return False
    
    logger.log(f"\nValidation başlıyor:")
    logger.log(f"  Model: {best_pt_finetuned.name}")
    logger.log(f"  Val images: {len(val_imgs)}")
    
    model = YOLO(str(best_pt_finetuned))
    
    # Predict on val set
    results_list = []
    predictions = model.predict(val_imgs, conf=0.25, verbose=False)
    
    for i, result in enumerate(tqdm(predictions, desc="Validating", total=len(predictions))):
        img_name = Path(result.path).stem
        
        # Get predictions
        if hasattr(result, 'probs') and result.probs is not None:
            pred_class = int(result.probs.top1)
            confidence = float(result.probs.top1conf)
        else:
            pred_class = -1
            confidence = 0.0
        
        results_list.append({
            'image': img_name,
            'pred_class': pred_class,
            'confidence': confidence,
            'pred_class_name': cfg.CLASSES.get(pred_class, 'unknown')
        })
    
    results_df = pd.DataFrame(results_list)
    
    # Save results
    cfg.VALIDATION_OUTPUT.mkdir(parents=True, exist_ok=True)
    results_csv = cfg.VALIDATION_OUTPUT / 'validation_results.csv'
    results_df.to_csv(results_csv, index=False)
    
    logger.log(f"\n✓ Validation tamamlandı")
    logger.log(f"  Results saved: {results_csv}")
    logger.log(f"\nPrediction distribution:")
    print(results_df['pred_class_name'].value_counts())
    
    return results_df

# ============================================================================
# COMPARISON: PRETRAIN vs FINETUNE
# ============================================================================

def stage_4_comparison(logger):
    """
    Pretraining vs Fine-tuning metriklerini karşılaştır
    """
    logger.log("\n" + "=" * 80)
    logger.log("STAGE 4: PRETRAINING vs FINE-TUNING COMPARISON")
    logger.log("=" * 80)
    
    # Pretraining results
    pretrain_csv = Path('outputs/runs/pretraining/rsna_pretrain/results.csv')
    
    # Fine-tuning results
    finetune_dir = cfg.FINETUNE_OUTPUT / 'finetuned_yolov8m'
    finetune_csv = finetune_dir / 'results.csv'
    
    comparison_data = {}
    
    if pretrain_csv.exists():
        df_pretrain = pd.read_csv(pretrain_csv)
        df_pretrain.columns = df_pretrain.columns.str.strip()
        
        last_pretrain = df_pretrain.iloc[-1]
        comparison_data['RSNA Pretraining (Epoch 50)'] = {
            'mAP50': float(last_pretrain.get('metrics/mAP50(B)', 0)),
            'mAP50-95': float(last_pretrain.get('metrics/mAP50-95(B)', 0)),
            'precision': float(last_pretrain.get('metrics/precision(B)', 0)),
            'recall': float(last_pretrain.get('metrics/recall(B)', 0)),
        }
        
        logger.log(f"\n📊 RSNA Pretraining Results:")
        for k, v in comparison_data['RSNA Pretraining (Epoch 50)'].items():
            logger.log(f"  {k}: {v:.4f}")
    
    if finetune_csv.exists():
        df_finetune = pd.read_csv(finetune_csv)
        df_finetune.columns = df_finetune.columns.str.strip()
        
        last_finetune = df_finetune.iloc[-1]
        comparison_data['Local Fine-tuning (Epoch 100)'] = {
            'mAP50': float(last_finetune.get('metrics/mAP50(B)', 0)),
            'mAP50-95': float(last_finetune.get('metrics/mAP50-95(B)', 0)),
            'precision': float(last_finetune.get('metrics/precision(B)', 0)),
            'recall': float(last_finetune.get('metrics/recall(B)', 0)),
        }
        
        logger.log(f"\n📊 Local Fine-tuning Results:")
        for k, v in comparison_data['Local Fine-tuning (Epoch 100)'].items():
            logger.log(f"  {k}: {v:.4f}")
    
    # Comparison
    if len(comparison_data) == 2:
        logger.log(f"\n📈 İYİLEŞME (%):")
        pretrain_vals = comparison_data['RSNA Pretraining (Epoch 50)']
        finetune_vals = comparison_data['Local Fine-tuning (Epoch 100)']
        
        for metric in pretrain_vals.keys():
            if pretrain_vals[metric] > 0:
                improvement = ((finetune_vals[metric] - pretrain_vals[metric]) / pretrain_vals[metric]) * 100
                logger.log(f"  {metric}: {improvement:+.2f}%")
    
    # Save comparison
    comparison_df = pd.DataFrame(comparison_data).T
    comparison_csv = cfg.VALIDATION_OUTPUT / 'comparison.csv'
    comparison_df.to_csv(comparison_csv)
    logger.log(f"\n✓ Comparison saved: {comparison_csv}")
    
    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    metrics = ['mAP50', 'mAP50-95', 'precision', 'recall']
    
    for idx, metric in enumerate(metrics[:2]):
        ax = axes[idx]
        data = [comparison_data[model].get(metric, 0) for model in comparison_data.keys()]
        bars = ax.bar(comparison_data.keys(), data, color=['#3498db', '#2ecc71'])
        ax.set_ylabel(metric)
        ax.set_title(f'{metric} Comparison')
        ax.set_ylim([0, 1])
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}', ha='center', va='bottom')
    
    plt.tight_layout()
    comparison_plot = cfg.VALIDATION_OUTPUT / 'comparison.png'
    plt.savefig(comparison_plot, dpi=150, bbox_inches='tight')
    logger.log(f"✓ Plot saved: {comparison_plot}")
    plt.close()

# ============================================================================
# MAIN
# ============================================================================

def main():
    # Setup logger
    log_file = cfg.VALIDATION_OUTPUT / 'pipeline.log'
    cfg.VALIDATION_OUTPUT.mkdir(parents=True, exist_ok=True)
    logger = Logger(log_file)
    
    logger.log("\n" + "=" * 80)
    logger.log("TRANSFER LEARNING PIPELINE")
    logger.log(f"Started: {datetime.now()}")
    logger.log("=" * 80)
    
    # Stage 2: Fine-tuning
    best_pt_finetuned = stage_2_finetuning(logger)
    
    if not best_pt_finetuned:
        logger.log("\n❌ Fine-tuning başarısız")
        return
    
    # Stage 3: Validation
    stage_3_validation(best_pt_finetuned, logger)
    
    # Stage 4: Comparison
    stage_4_comparison(logger)
    
    logger.log("\n" + "=" * 80)
    logger.log("✓ Pipeline tamamlandı!")
    logger.log(f"Results: {cfg.VALIDATION_OUTPUT}")
    logger.log("=" * 80)

if __name__ == '__main__':
    main()
