# Manuel Inceleme Adaylari Icin Web Dogrulama Notlari

Bu not, yeniden uygunluk denetiminde `MANUEL_INCELEME` olarak isaretlenen kayitlarin hizli canli web/PubMed/dergi kontrolu icin olusturulmustur. Ayrintili nihai karar icin tam metin kontrolu onerilir.

## [52] Hu Y, 2025 - AI-based diagnosis of acute aortic syndrome from noncontrast CT

- Web dogrulama: PMC/Nature Medicine sayfasi calismanin nonkontrast BT uzerinden akut aort sendromu tanisi icin derin ogrenme modeli gelistirdigini ve pilot uygulama/validasyon icerdigini gosteriyor.
- On karar: Dahil edilebilir. Model/gorev kodu `DET/CLS/TRIAGE` ve model ailesi `CNN/DL` olarak manuel netlestirilmeli.
- Kaynak: https://pmc.ncbi.nlm.nih.gov/articles/PMC12618251/

## [63] Kodenko MR, 2025 - CT angiography dataset with abdominal aorta segmentation

- Web dogrulama: Dergi sayfasi bunun abdominal aorta CTA veri seti ve segmentasyon maskeleri iceren bir dataset makalesi oldugunu gosteriyor.
- On karar: Eger inceleme sadece model gelistirme/degerlendirme calismalarini kapsayacaksa dislama adayi olabilir; acik veri/dataset calismalari dahil edilecekse dahil edilebilir.
- Kaynak: https://journals.rcsi.science/DD/article/view/310049/en_US

## [102] Wang Y, 2025 - RRM-TransUNet

- Web dogrulama: PubMed aktarimli sayfa, calismanin BT goruntulerinde interaktif pankreas segmentasyonu icin RRM-TransUNet onerdiğini ve Dice/ASSD performansi raporladigini gosteriyor.
- On karar: Dahil edilebilir; ancak akut pankreatit calismasi degil, pankreas segmentasyonu/pankreatik hastalik baglaminda oldugu icin hedef patoloji kapsaminda tam metinle dogrulanmali.
- Kaynak: https://www.lifescience.net/publications/1247972/rrm-transunet-deep-learning-driven-interactive-mod/

## [164] Zhao Y, 2024 - Acute simple vs non-simple appendicitis radiomics

- Web dogrulama: PubMed kaydi, akut apandisit olgularinda CT radyomik + klinik model ile simple/non-simple ayrimini dogruluyor.
- On karar: Dahil edilebilir. Gorev `PRED/CLS`, model ailesi `RADIOMICS_ML` olarak duzeltilebilir.
- Kaynak: https://pubmed.ncbi.nlm.nih.gov/38253872/

## [192] Tomihama RT, 2023 - CNN confounding variables for AAA

- Web dogrulama: ScienceDirect ozeti, infrarenal AAA icin CTA uzerinde CNN gelistirilip karistirici degiskenlerin incelendigini gosteriyor.
- On karar: Dahil edilebilir; gorev `CLS/DET`, model ailesi `CNN_2D/VGG16` olarak netlestirilebilir.
- Kaynak: https://www.sciencedirect.com/science/article/pii/S2666350322000840

## [206] Fujita H, 2022 - Gallbladder tumors using CT-based deep learning

- Web dogrulama: Ozet, calismanin gallbladder cancer ile xanthogranulomatous cholecystitis ayrimina odaklandigini gosteriyor.
- On karar: Akut kolesistit kapsaminda tutulmasi zayif. Hedef patoloji "akut kolesistit" olarak dar tutulacaksa dislama adayi; "kolesistit spektrumu" genis tutulacaksa manuel gerekceyle dahil edilebilir.
- Kaynak: https://www.ivysci.com/articles/1192606__Differential_diagnoses_of_gallbladder_tumors_using%0A____________scpCTbasedscp%0A____________deep_learni

## [233] Zheng T, 2021 - AI algorithm in AAA CTA

- Web dogrulama: Mendeley kaydi baslik ve konu duzeyinde eslesiyor; tam metin/dergi kaydi ile model ve gorev ayrintisi netlestirilmeli.
- On karar: Gecici olarak dahil edilebilir; ancak tam metin kontrolu onerilir.
- Kaynak: https://www.mendeley.com/catalogue/6a382cb5-a1b8-3af1-bbc8-f22acbe8da87/
