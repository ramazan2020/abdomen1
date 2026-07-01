# Tez ↔ Kod İlişkisi ve Güncel Durum

Bu dosya, `TR_Abdomen_Doktora_Tez_Onerisi_v2.docx`'teki iş paketlerini (Bölüm A-E) depodaki
çalıştırılabilir koda (kök dizindeki `FazN_*.ipynb` + `src/*.py`) bağlar ve her biri için
**gerçekte ne kadarının çalıştırıldığını** (`outputs/` içindeki dosya/checkpoint kanıtına
bakılarak, 2026-06-19 itibarıyla) ve **sırada ne olduğunu** özetler.

Tez metnindeki "Durum notu" (Yönetici Özeti, paragraf 11) bunu zaten genel hatlarıyla söylüyor:
*"benchmark ve yöntem taslakları yer-tutucu (dummy) değerlerle hazırlanmıştır; modeller henüz
eğitilmemiş ve test edilmemiştir."* Aşağıdaki tablo bunu somutlaştırıyor — bazı adımlarda kod
hazır ve veri üretildi, bazılarında sadece iskelet var, bir tanesinde (OBT) gerçek bir deneme
checkpoint'i bile var.

## Eşleme ve Durum Tablosu

| Tez İş Paketi | Tez'de Vaat Edilen | Karşılık Gelen Kod | Gerçek Durum (disk kanıtı) | Yapılması Gereken |
|---|---|---|---|---|
| **Bölüm A** — Havuzlama, sızıntısız split, 4 model benchmark (Tablo 4: YOLO, Swin, nnU-Net, MedNeXt) | Vaka-düzeyi `StratifiedGroupKFold`, 5 fold + holdout; 4 modelin eğitilip karşılaştırılması | `scripts/01_split.py`, `src/splits.py` → `Faz3a_VeriHazirlik_YOLO.ipynb`; `Faz2a_nnUNet_Colab_Kaggle.ipynb`, `Faz2b_nnUnet_Kaggle.ipynb`, `Faz2c_MedNeXt_Kaggle.ipynb`, `Faz3b_YOLO_Colab_Kaggle.ipynb`, `Faz4_SwinTransformer_Colab_Kaggle.ipynb` | **Split: tamamlandı** (`outputs/splits/manifest.csv` 39k satır, 5 fold + `holdout.csv`). DICOM→NIfTI: 725 dosya ile **fiilen tamamlanmış**. YOLO fold0 verisi **export edilmiş** (26.434 görsel + 26.436 etiket), ama eğitim **yarım kalmış** — `outputs/runs/det/fold0_yolo12m/` içinde yalnızca init-batch görselleri var, `best.pt`/`results.csv` yok. nnU-Net/MedNeXt preprocessing **sadece iskelet** (`nnunet_preprocessed/` 6, `nnunet_raw/` 5 dosya — gerçek ön-işleme yok). Swin (Faz4) için NPZ verisi (`outputs/cls_data/`) **boş** — hiç üretilmemiş. | (1) `Faz2a` ile gerçek nnU-Net preprocessing'i bitir; (2) YOLO fold0 eğitimini tamamla (kesintiye uğramış); (3) Faz4 NPZ export'unu çalıştır; (4) 5 fold'un tamamına genişlet (şu an sadece fold0 var yer yer). |
| **CT-MAE ön-eğitim** (Bölüm C'nin önkoşulu) | ConvNeXt-S + SimMIM, train-split dilimleri üzerinde öz-denetimli ön-eğitim | `src/ct_mae.py` → `Faz3c_CTMAE_Pretrain_Colab_Kaggle.ipynb` | Kod **yazılmış ve mimari net** (önceki oturumda tez metniyle hizalandı: ConvNeXt-S, SimMIM-tarzı, dense-mask sızıntı riski not edilmiş). `outputs/checkpoints/` **boş** — CT-MAE'nin kendi checkpoint'i henüz **diskte yok**; ama `outputs/obt_fold0/checkpoints/stage1_best.pt` (233MB, en son 18 Haz 15:27) muhtemelen CT-MAE+OBT'nin **birlikte** Stage-1 çalıştırıldığını gösteriyor. | Tablo 6'daki ablasyon merdivenini (scratch / ImageNet / CT-MAE / birleşik / genişletilmiş / FCMAE-sparse) gerçekten çalıştır; şu an yalnızca 1 deneme (stage1) var, 6 satırın hiçbiri tam değil. |
| **Bölüm C** (ana katkı) — Anatomi kolu + organ-koşullu FCOS dedektör + organ-bag attention + cross-organ Transformer | `src/organ_bag_transformer.py` → `Faz3d_OrganBagTransformer_Colab_Kaggle.ipynb`; anatomi z-aralığı için `src/boundary_z_detect.py` | Mimari **tam kodlanmış** (ablasyon bayrakları A1-A4 dahil). `outputs/obt_fold0/checkpoints/stage1_best.pt` mevcut → **en az bir Stage-1 deneme çalıştırılmış**. `outputs/obt_fold0/output/fig1_organ_z_distribution.pdf` da üretilmiş (veri-dağılım analizi). Ama 5-fold yok, ablasyon (A1-A4) yok, sayısal F1/recall sonucu yok. `outputs/seg_data/` **boş** → tez metninde "zaten üretilen TotalSegmentator pseudo-maskeler" dediğimiz şey **kodda hazır ama diskte henüz üretilmemiş** (`src/segmentation.py: generate_pseudo_labels()` hiç çalıştırılmamış). | (1) `generate_pseudo_labels()` çalıştırılıp gerçek TotalSegmentator pseudo-mask'ları üretilmeli — yoksa Bölüm C'deki (x,y,z) önbilgi cümlesi şimdilik kod-hazır/veri-yok durumda; (2) Stage-1'i 5 fold'a genişlet; (3) A1-A4 ablasyonunu çalıştır; (4) `nnU-Net/MedNeXt` 3D seg→kutu karşı-referansı için önce Bölüm A'daki preprocessing bitmeli (yukarıdaki bağımlılık). |
| **Bölüm B** — Dengesizlik (Focal-BCE, WeightedSampler), kalibrasyon, eşik optimizasyonu | `src/losses.py`, `src/calibration.py`, `src/train_cls.py` → `Faz5_Kalibrasyon_Degerlendirme.ipynb`, `Faz7a/7b_*_Ablation_*.ipynb`, `Faz7c_CrossVal_Cls.ipynb` | Kod hazır. Ama Faz5/Faz7 hepsi **Faz4'ün NPZ çıktısına bağımlı**; Faz4 hiç çalışmadığından (`cls_data/` boş) **bu iş paketi de fiilen başlayamıyor**. | Faz4 NPZ export'u olmadan bu bölüm tamamen bloklu — önce Bölüm A'daki Faz4 adımı bitirilmeli. |
| **Bölüm D** — Belirsizlik kestirimi, seçici tahmin, aciliyet skoru | `src/calibration.py`, `Faz5_Kalibrasyon_Degerlendirme.ipynb` (kısmen örtüşüyor) | Aynı bağımlılık zinciri (Faz4 → Faz5) henüz çalışmadığı için **başlanmamış**. | Bölüm B ile aynı önkoşula bağlı. |
| **Bölüm E** — Genellenebilirlik, cihaz-kısayolu kontrolü, harici/halka açık veri genişletmesi | `Faz6_Harici_Test.ipynb` | Faz6, Faz2b/2c/3b/3d/4'ün **hepsinin** çıkışını bekliyor; hiçbiri tamamlanmadığından **başlanmamış**. | En son adım — yukarıdaki zincir bitmeden anlamlı değil. |
| **Ablasyonlar** (Tablo 6: backbone, loss/sampler, 5-fold CV) | `Faz7a_SwinTransform_Ablation_Backbone_Cls.ipynb`, `Faz7b_SwinTransform_Ablation_LossSampler_Cls.ipynb`, `Faz7c_CrossVal_Cls.ipynb` | Faz4 NPZ'sine bağımlı, **başlanmamış**. | Aynı önkoşul. |
| **Makale/Tez figür-tablo üretimi** | `Faz8_Makale_Analiz.ipynb` | Faz6 + Faz7 JSON sonuçlarını bekliyor; **başlanmamış**. | Zincirin son halkası. |
| **3D karşı-referans (nnU-Net/MedNeXt seg→kutu)** | Bölüm C metninde nnDetection yerine tercih edilen yaklaşım | `src/weak_seg.py` (3D zayıf-denetimli lezyon maskesi) + `src/nnunet.py: seg_to_bboxes()` (bağlı-bileşen → kutu) | Kod **tam yazılmış**, ama `outputs/seg_data/` boş olduğundan **hiç çalıştırılmamış**. `nnDetection_code/nnDetection_3D_1fold(.ipynb/-colab.ipynb)` (yeniden adlandırıldı) ayrı, park edilmiş bir denemedir — tez metninde artık birincil yaklaşım değil. | `generate_weak_masks()` çalıştırılıp nnU-Net/MedNeXt bu maskelerle eğitilmeli; bu da Bölüm A'daki nnU-Net preprocessing'in bitmesine bağımlı. |

## Bağımlılık Zinciri (neden çoğu şey "başlanmamış")

```
Faz1 (analiz) ✅
  └─ Faz2a (DICOM→NIfTI ✅, nnU-Net preprocessing ❌ iskelet)
       └─ Faz2b (nnU-Net eğitim) ❌
       └─ Faz2c (MedNeXt eğitim) ❌
  └─ Faz3a (YOLO veri export, fold0 ✅)
       └─ Faz3b (YOLO eğitim) ⚠️ kesintiye uğramış
       └─ Faz3c (CT-MAE ön-eğitim) ⚠️ checkpoint var ama izole doğrulanmadı
            └─ Faz3d (OBT) ⚠️ stage1_best.pt var, 5-fold/ablasyon yok
  └─ Faz4 (Swin NPZ + eğitim) ❌ — Bölüm B/D, Faz5, Faz7a-c, Faz6, Faz8'in TÜMÜ buna bağımlı
```

✅ tamamlandı · ⚠️ kısmi/tek deneme · ❌ henüz çalıştırılmadı

## Öncelik Sırası (önerilen)

1. **Faz4 NPZ export'unu bitir** — tek bir adım, ama Bölüm B/D ve tüm Faz5-8 zincirini açıyor (en yüksek kaldıraç).
2. **nnU-Net preprocessing'i (Faz2a) tamamla** — Bölüm A'nın 4-model benchmark'ı ve nnU-Net/MedNeXt 3D karşı-referansı (Bölüm C) buna bağımlı.
3. **YOLO fold0 eğitimini bitir** (kesintiye uğramış) — Bölüm A benchmark'ının bir ayağı.
4. **`generate_pseudo_labels()` / `generate_weak_masks()` çalıştır** — Bölüm C'nin (x,y,z) anatomi önbilgisi ve 3D seg→kutu karşı-referansı için ön koşul; şu an tez metni kodun varlığını anlatıyor ama veri henüz yok.
5. **OBT'yi 5 fold'a ve A1-A4 ablasyonuna genişlet** — şu an tek bir stage1 denemesi var.
6. Yukarıdakiler bittikten sonra Faz5→Faz7a-c→Faz6→Faz8 sırayla doğal olarak açılır.

## Not

Bu dosya bir an'lık envanterdir (komut: `find outputs/... -type f`, 2026-06-19). Yeniden eğitim
koşulduğunda veya çıktı dizinleri değiştiğinde bu tablo elle güncellenmeli — otomatik
senkronize değildir.
