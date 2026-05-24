# NornirNet Makale Kontrol Raporu

Kontrol edilen PDF: `C:\Users\ramazan.polat3\Desktop\ai-07-00057-v2.pdf`

Resmi makale sayfası: <https://www.mdpi.com/2673-2688/7/2/57>

## Bibliyografik Bilgi

- Başlık: NornirNet: A Deep Learning Framework to Distinguish Benign from Malignant Type II Endoleaks After Endovascular Aortic Aneurysm Repair Using Preoperative Imaging
- Yazarlar: Francesco Andreoli, Fabio Mattiussi, Elias Wasseh, Andrea Leoncini, Ludovica Ettorre, Jacopo Galafassi, Maria Antonella Ruffino, Luca Giovannacci, Alessandro Robaldo, Giorgio Prouse
- Dergi: AI (Switzerland)
- Yıl: 2026
- DOI: 10.3390/ai7020057

## Makalemiz İçin Kodlama

- Patoloji: Abdominal aort patolojisi / AAA-EVAR sonrası tip II endoleak
- Görüntüleme: Preoperatif CTA
- Görev türü: Sınıflandırma/Tanı; Öngörü/Prognoz
- Model ailesi: 3B CNN/ResNet
- Harici doğrulama: Evet, bağımsız test seti olarak kodlanabilir; ancak tek merkezli retrospektif kohort olduğu ayrıca belirtilmeli.
- Açık kod/veri: Veri makul talep üzerine paylaşılabilir olarak belirtilmiş; açık veri/kod paylaşımı olarak kodlanmamalı.
- Makaledeki sentez yeri: AAA/EVAR alt başlığı; CTA tabanlı derin öğrenme ile T2EL risk sınıflandırması.

## Temel Yöntem ve Sonuç

Çalışma, EVAR sonrası tip II endoleak gelişimi ve klinik şiddetini preoperatif CTA hacimlerinden öngörmek için uçtan uca 3B CNN tabanlı NornirNet modelini geliştirmiştir. Retrospektif tek merkezli kohortta 277 hasta değerlendirilmiş; veri 175 eğitim, 72 validasyon ve 30 bağımsız test olgusuna ayrılmıştır. Model üç sınıfı ayırmıştır: T2EL yok, benign T2EL ve malign T2EL.

Bağımsız test setinde genel doğruluk %76,7, makro F1 skoru 0,77 ve AUC 0,93 olarak bildirilmiştir. Sınıf bazlı AUC değerleri T2EL yok için 0,93, benign için 0,91 ve malign için 0,96'dır.

## Düzeltme Notu

Zotero notunda görev tipi `SEG,CLS,PRED` görünüyordu; ancak makalenin yöntem ve sonuç bölümleri bu çalışmanın segmentasyon çıktısı üretmediğini, preoperatif CTA hacimlerinden üç sınıflı risk sınıflandırması/öngörü yaptığını göstermektedir. Bu nedenle tabloya `Sınıflandırma/Tanı; Öngörü/Prognoz` olarak işlendi.
