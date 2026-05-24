# 234 Makale Yeniden Uygunluk ?ncelemesi ve Veri Taban? ?zeti

Bu rapor, `extracted_data_v3_strict.xlsx` i?indeki 234 ?al??man?n yerel ?oklu veritaban? kay?tlar? (`master_records.xlsx`, `included_studies_final.xlsx`) ile DOI/PMID/ba?l?k ?zerinden yeniden e?le?tirilmesiyle haz?rlanm??t?r. ?nternet tabanl? canl? tarama yap?lmam??; klas?rdeki PubMed/arXiv/IEEE/Scopus/Web of Science d??a aktar?mlar? esas al?nm??t?r.

## Yeniden Uygulanan Uygunluk ?l??tleri
- 2021 ile 14 May?s 2026 aras?nda yay?mlanm?? olma
- alt? hedef patolojiden en az birine odaklanma: akut apandisit, akut kolesistit, akut pankreatit, ?rolitiyazis/nefrolitiyazis, akut divertik?lit, abdominal aort anevrizmas?/diseksiyonu
- BT tabanl? g?r?nt?leme kullanma: CT, CTA, NCCT, CECT, MDCT veya DECT
- YZ/M?/D?/radyomik/bilgisayarl? g?rme bile?eni i?erme
- saptama, s?n?fland?rma, b?l?tleme, lokalizasyon, triyaj, CAD veya ?ng?r? g?revlerinden en az birini i?erme
- derleme, meta-analiz, edit?ryal, vaka raporu veya yaln?zca klinik/laboratuvar skoru olmama

## Yeniden Eleme Sonucu
- DAHIL: 227 ?al??ma
- MANUEL_INCELEME: 7 ?al??ma
- DISLAMA_ADAYI: 0 ?al??ma

Manuel inceleme i?areti, ?al??man?n kesin d??lanmas? anlam?na gelmez; veri taban? ?zetinde patoloji, BT, g?rev veya model bilgisinin yeterince a??k g?r?nmedi?i ya da klinik kapsam?n daralt?lmas? gerekebilece?i anlam?na gelir.

## Patoloji Da??l?m?
- ?rolitiyazis/nefrolitiyazis: 95 (40.6%)
- Abdominal aort anevrizmas?/diseksiyonu: 79 (33.8%)
- Akut pankreatit: 33 (14.1%)
- Akut apandisit: 14 (6.0%)
- Akut kolesistit: 5 (2.1%)
- Birden fazla hedef patoloji: 4 (1.7%)
- Akut divertik?lit: 4 (1.7%)

## Y?llara G?re Da??l?m
- 2021: 15
- 2022: 21
- 2023: 31
- 2024: 60
- 2025: 75
- 2026: 32

## Kan?t Kalitesi ve A??k Bilim G?stergeleri
- Harici do?rulama: 44/234 (18.8%)
- Radyolog kar??la?t?rmas?: 8/234 (3.4%)
- A??k kod: 7/234 (3.0%)
- A??k veri: 10/234 (4.3%)

## Manuel ?nceleme Gerektiren Ba?l?ca Kay?tlar
- [52] Hu Y (2025), AAA: AI-based diagnosis of acute aortic syndrome from noncontrast CT ? g?rev/model kodu manuel do?rulama gerektiriyor
- [63] Kodenko M.R. (2025), AAA: CT angiography dataset with abdominal aorta segmentation ? g?rev/model kodu manuel do?rulama gerektiriyor
- [102] Wang Y (2025), PAN: RRM-TransUNet: Deep-Learning Driven Interactive Model for Precise Pancreas Segmentation in CT Images ? g?rev/model kodu manuel do?rulama gerektiriyor
- [164] Zhao Y. (2024), APP: Combination of clinical information and radiomics models for the differentiation of acute simple appendicitis and non simple appendicitis on CT images ? bilgisayarl? g?rme/?ng?r? g?revi belirsiz; g?rev/model kodu manuel do?rulama gerektiriyor
- [192] Tomihama R.T. (2023), AAA: Machine learning analysis of confounding variables of a convolutional neural network specific for abdominal aortic aneurysms ? g?rev/model kodu manuel do?rulama gerektiriyor
- [206] Fujita H (2022), CHO: Differential diagnoses of gallbladder tumors using CT-based deep learning ? akut kolesistit yerine safra kesesi t?m?r?/XGC ay?r?c? tan?s? olabilir; g?rev/model kodu manuel do?rulama gerektiriyor
- [233] Zheng T. (2021), AAA: Abdominal Enhanced Computed Tomography Image by Artificial Intelligence Algorithm in the Diagnosis of Abdominal Aortic Aneurysm ? g?rev/model kodu manuel do?rulama gerektiriyor

## Patoloji Bazl? K?sa Sentez
### Akut apandisit
Toplam 14 ?al??ma; yeniden elemede 13 do?rudan dahil, 1 manuel inceleme aday?. En s?k g?revler: DET=7, PRED=7, CLS=3, LOC=3, SEG=3. En s?k model aileleri: CNN_GENERIC=3, CLASSICAL_ML=3, UNET=2, RADIOMICS=2, CNN_2D=1. Harici do?rulama: 0/14.
- [41] C. -W. Huang ve ark. (2025) APP alan?nda CT_generic verisiyle CLS, DET g?revi i?in CNN_GENERIC yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [55] J. R. M. Done ve ark. (2025) APP alan?nda CECT verisiyle CLS, DET, PRED g?revi i?in CNN_2D, GAN yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [62] Kim M ve ark. (2025) APP alan?nda CT_generic verisiyle CLS, PRED g?revi i?in CNN_3D yakla??m?n? de?erlendirdi; AUC=0.827; harici do?rulama yok/bildirilmemi?.
- [94] Takaishi T ve ark. (2025) APP alan?nda CT_generic verisiyle DET, PRED, LOC g?revi i?in DETECTION_MODEL yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [110] An J ve ark. (2024) APP alan?nda CT_generic verisiyle PRED g?revi i?in CLASSICAL_ML yakla??m?n? de?erlendirdi; AUC=0.886; harici do?rulama yok/bildirilmemi?.

### Akut kolesistit
Toplam 5 ?al??ma; yeniden elemede 4 do?rudan dahil, 1 manuel inceleme aday?. En s?k g?revler: PRED=3, SEG=2, DET=1. En s?k model aileleri: CNN_2D=2, RADIOMICS=1, MULTIMODAL_LLM=1, RADIOMICS_ML=1, UNET=1. Harici do?rulama: 1/5.
- [44] Chen BQ ve ark. (2025) CHO alan?nda NCCT verisiyle SEG, PRED g?revi i?in RADIOMICS, MULTIMODAL_LLM yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [92] Sun RT ve ark. (2025) CHO alan?nda CT_generic verisiyle PRED g?revi i?in RADIOMICS_ML yakla??m?n? de?erlendirdi; AUC=0.938; harici do?rulama yok/bildirilmemi?.
- [103] Yang CY ve ark. (2025) CHO alan?nda CT_generic verisiyle SEG, DET g?revi i?in UNET, CNN_2D yakla??m?n? de?erlendirdi; do?ruluk=0.925; duyarl?l?k=0.904; ?zg?ll?k=0.941; harici do?rulama yok/bildirilmemi?.
- [163] Zhang W ve ark. (2024) CHO alan?nda CT_generic verisiyle PRED g?revi i?in CNN_2D yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama var.
- [206] Fujita H ve ark. (2022) CHO alan?nda CT_generic verisiyle g?rev tipi belirsiz g?revi i?in CNN_GENERIC yakla??m?n? de?erlendirdi; do?ruluk=0.988; harici do?rulama yok/bildirilmemi?.

### Akut pankreatit
Toplam 33 ?al??ma; yeniden elemede 32 do?rudan dahil, 1 manuel inceleme aday?. En s?k g?revler: PRED=23, CLS=15, SEG=14, DET=6, TRIAGE=1. En s?k model aileleri: RADIOMICS_ML=13, VIT=6, CNN_2D=4, CLASSICAL_ML=4, RADIOMICS=4. Harici do?rulama: 9/33.
- [10] Güneri G ve ark. (2026) PAN alan?nda CECT verisiyle CLS g?revi i?in VIT, CNN_2D yakla??m?n? de?erlendirdi; do?ruluk=0.892; F1=0.867; harici do?rulama yok/bildirilmemi?.
- [12] Li J ve ark. (2026) PAN alan?nda CT_generic verisiyle CLS, PRED g?revi i?in CLASSICAL_ML yakla??m?n? de?erlendirdi; AUC=0.946; F1=0.879; harici do?rulama var.
- [16] Nalliah S ve ark. (2026) PAN alan?nda CT_generic verisiyle SEG, CLS g?revi i?in RADIOMICS yakla??m?n? de?erlendirdi; AUC=0.970; harici do?rulama var.
- [24] Wan Z ve ark. (2026) PAN alan?nda CECT verisiyle PRED g?revi i?in VIT, CNN_2D, MULTIMODAL_LLM yakla??m?n? de?erlendirdi; AUC=0.840; F1=0.824; harici do?rulama var.
- [26] Xu Y ve ark. (2026) PAN alan?nda CECT verisiyle PRED, TRIAGE g?revi i?in CNN_GENERIC yakla??m?n? de?erlendirdi; duyarl?l?k=0.750; ?zg?ll?k=0.980; harici do?rulama var.

### ?rolitiyazis/nefrolitiyazis
Toplam 95 ?al??ma; yeniden elemede 95 do?rudan dahil, 0 manuel inceleme aday?. En s?k g?revler: DET=64, CLS=52, PRED=38, SEG=23, LOC=12. En s?k model aileleri: CNN_2D=36, CNN_GENERIC=26, VIT=13, UNET=9, DETECTION_MODEL=8. Harici do?rulama: 14/95.
- [4] Cha K ve ark. (2026) URO alan?nda NCCT verisiyle CLS, PRED, TRIAGE g?revi i?in CLASSICAL_ML yakla??m?n? de?erlendirdi; AUC=0.771; harici do?rulama yok/bildirilmemi?.
- [5] Chen HW ve ark. (2026) URO alan?nda CT_generic verisiyle DET, PRED g?revi i?in CLASSICAL_ML yakla??m?n? de?erlendirdi; duyarl?l?k=0.873; ?zg?ll?k=0.947; harici do?rulama yok/bildirilmemi?.
- [7] Dimlo U.M.F. ve ark. (2026) URO alan?nda CT_generic verisiyle DET g?revi i?in CNN_2D yakla??m?n? de?erlendirdi; F1=0.976; harici do?rulama yok/bildirilmemi?.
- [9] Gorli S. ve ark. (2026) URO alan?nda CT_generic verisiyle SEG, CLS, LOC g?revi i?in UNET, VIT yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [11] Katti J. ve ark. (2026) URO alan?nda CT_generic verisiyle CLS, DET g?revi i?in CNN_2D yakla??m?n? de?erlendirdi; do?ruluk=0.980; F1=0.853; harici do?rulama yok/bildirilmemi?.

### Akut divertik?lit
Toplam 4 ?al??ma; yeniden elemede 4 do?rudan dahil, 0 manuel inceleme aday?. En s?k g?revler: LOC=2, CLS=2, PRED=2, SEG=2, CAD=1. En s?k model aileleri: CNN_3D=2, CLASSICAL_ML=1, CNN_GENERIC=1. Harici do?rulama: 0/4.
- [80] Rahman M.A. ve ark. (2025) DIV alan?nda CT_generic verisiyle LOC, CAD g?revi i?in CNN_3D yakla??m?n? de?erlendirdi; IoU=0.695; harici do?rulama yok/bildirilmemi?.
- [136] Lippenberger F ve ark. (2024) DIV alan?nda CT_generic verisiyle CLS, PRED g?revi i?in CLASSICAL_ML yakla??m?n? de?erlendirdi; AUC=0.890; duyarl?l?k=0.560; ?zg?ll?k=0.770; harici do?rulama yok/bildirilmemi?.
- [184] M. A. Rahman ve ark. (2023) DIV alan?nda CT_generic verisiyle SEG, LOC g?revi i?in CNN_GENERIC yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [198] Ziegelmayer S ve ark. (2023) DIV alan?nda CT_generic verisiyle SEG, CLS, PRED g?revi i?in CNN_3D yakla??m?n? de?erlendirdi; duyarl?l?k=0.833; ?zg?ll?k=0.866; harici do?rulama yok/bildirilmemi?.

### Abdominal aort anevrizmas?/diseksiyonu
Toplam 79 ?al??ma; yeniden elemede 75 do?rudan dahil, 4 manuel inceleme aday?. En s?k g?revler: SEG=48, DET=33, PRED=29, CLS=27, TRIAGE=5. En s?k model aileleri: CNN_GENERIC=20, UNET=15, NNUNET=8, RADIOMICS_ML=7, DETECTION_MODEL=6. Harici do?rulama: 20/79.
- [1] Andreoli F. ve ark. (2026) AAA alan?nda CTA verisiyle SEG, CLS, PRED g?revi i?in CNN_3D yakla??m?n? de?erlendirdi; AUC=0.930; do?ruluk=0.767; F1=0.770; harici do?rulama var.
- [2] Arampatzis D ve ark. (2026) AAA alan?nda CT_generic verisiyle SEG, DET g?revi i?in NNUNET yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [3] Cai W. ve ark. (2026) AAA alan?nda CTA verisiyle SEG g?revi i?in SAM_FAMILY yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [6] Cheng J ve ark. (2026) AAA alan?nda CTA verisiyle CLS, DET, PRED g?revi i?in DETECTION_MODEL, CNN_2D yakla??m?n? de?erlendirdi; do?ruluk=0.988; harici do?rulama yok/bildirilmemi?.
- [8] Fujiwara J ve ark. (2026) AAA alan?nda NCCT verisiyle SEG, DET, PRED g?revi i?in CNN_GENERIC yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.

### Birden fazla hedef patoloji
Toplam 4 ?al??ma; yeniden elemede 4 do?rudan dahil, 0 manuel inceleme aday?. En s?k g?revler: CLS=3, DET=2, PRED=1. En s?k model aileleri: CNN_3D=1, RADIOMICS=1, MULTIMODAL_LLM=1, RADIOMICS_ML=1, DETECTION_MODEL=1. Harici do?rulama: 0/4.
- [64] Li J ve ark. (2025) MIX alan?nda CT_generic verisiyle DET g?revi i?in CNN_3D, RADIOMICS, MULTIMODAL_LLM yakla??m?n? de?erlendirdi; AUC=0.810; do?ruluk=0.915; harici do?rulama yok/bildirilmemi?.
- [142] Ma Y ve ark. (2024) MIX alan?nda CT_generic verisiyle CLS, PRED g?revi i?in RADIOMICS_ML yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [151] S. Koçer ve ark. (2024) MIX alan?nda CT_generic verisiyle CLS, DET g?revi i?in DETECTION_MODEL yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
- [188] Park SH ve ark. (2023) MIX alan?nda CT_generic verisiyle CLS g?revi i?in CNN_2D yakla??m?n? de?erlendirdi; performans metri?i yap?land?r?lm?? alanda yok; harici do?rulama yok/bildirilmemi?.
