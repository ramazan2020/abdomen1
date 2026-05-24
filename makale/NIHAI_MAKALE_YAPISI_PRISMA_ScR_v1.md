# Nihai Makale Yapisi PRISMA-ScR v1

## Calisma Basligi

### Onerilen ana baslik

**Secilmis Abdominal Acil Patolojilerde Bilgisayarli Tomografi Tabanli Yapay Zeka Uygulamalari: Coklu Veritabani Kapsam Belirleme Incelemesi (2021-14 Mayis 2026)**

### Alternatif baslik

**Karin Agrisi Baglaminda Secilmis Abdominal Acil Patolojiler Icin BT Tabanli Yapay Zeka Uygulamalari: Coklu Veritabani Kapsam Belirleme Incelemesi**

### Baslik icin karar

Mevcut "Karin Agrisi" basligi korunabilir; ancak calismanin karin agrisinin tum nedenlerini degil, alti hedef patolojiyi kapsadigi baslik altinda, ozette ve yontemde acikca belirtilmelidir. Daha hakem-dostu secenek, baslikta "secilmis abdominal acil patolojiler" ifadesini kullanmaktir.

---

## Makale Turu

Bu calisma klasik anlatili derleme olarak degil, **JBI metodolojisi ve PRISMA-ScR raporlama ilkelerine dayali kapsam belirleme incelemesi** olarak yazilmalidir.

Gerekce:

- Literatür nicel etki buyuklugu hesaplamaya uygun derecede homojen degildir.
- Patolojiler, model aileleri, veri setleri, gorev turleri ve performans metrikleri heterojendir.
- En dogru amac, literaturu haritalamak, bosluklari gostermek ve gelecekteki calismalar icin yon belirlemektir.

---

## Nihai Calisma Havuzu

Yeniden uygunluk denetimi sonrasi durum:

| Karar | Sayi |
|---|---:|
| Dogrudan dahil | 227 |
| Manuel inceleme adayi | 7 |
| Otomatik dislama adayi | 0 |
| Toplam yeniden incelenen | 234 |

Manuel inceleme adayi 7 calisma nihai metinde iki sekilde ele alinabilir:

1. Tam metin kontrolu ile dahil/disla karari kesinlestirilir.
2. Nihai N=234 korunur, ancak "manuel dogrulama gerektiren sinir kayitlar" ek tabloda belirtilir.

Onerim: Nihai makaleye gecmeden once ozellikle [206] Fujita 2022 kaydi icin karar verilsin. Bu calisma akut kolesistitten cok safra kesesi kanseri ile ksantogranulomatoz kolesistit ayirici tanisina odaklanmaktadir. Kapsam "akut kolesistit" olarak dar tutulacaksa dislama adayidir.

---

## 1. Ozet

### Yapilandirilmis ozet basliklari

1. Amac
2. Yontem
3. Bulgular
4. Sonuc
5. Anahtar kelimeler

### Yazilacak icerik

**Amac:**  
2021 ile 14 Mayis 2026 arasinda yayimlanan calismalarda, alti secilmis abdominal acil patoloji icin BT tabanli YZ, MO, DO ve radyomik uygulamalarini haritalamak.

**Yontem:**  
PubMed/MEDLINE, arXiv, IEEE Xplore, Scopus ve Web of Science tarandi. Ham 2.159 kayit, tekillestirme sonrasi 1.203 kayda indirildi. Baslik/ozet ve uygunluk degerlendirmeleri sonrasi 234 calisma yeniden uygunluk denetimine alindi. Uygunluk olcutleri yil araligi, hedef patoloji, BT modalitesi, YZ/MO/DO/radyomik bileseni, bilgisayarli gorme veya ongoru gorevi ve orijinal calisma olma kosullarina dayandirildi.

**Bulgular:**  
234 calismanin patoloji dagilimi su sekildedir: urolitiyazis/nefrolitiyazis n=95, abdominal aort anevrizmasi/diseksiyonu n=79, akut pankreatit n=33, akut apandisit n=14, akut kolesistit n=5, akut divertikulit n=4 ve birden fazla hedef patoloji n=4. Harici dogrulama 44/234, radyolog karsilastirmasi 8/234, acik kod paylasimi 7/234 ve acik veri paylasimi 10/234 calismada bildirilmistir.

**Sonuc:**  
BT tabanli YZ uygulamalari secilmis abdominal acillerde hizla artmakta ve ozellikle urolitiyazis ile aort patolojilerinde yogunlasmaktadir. Buna karsin cok merkezli harici dogrulama, acik bilim, prospektif klinik degerlendirme ve standart raporlama eksiklikleri devam etmektedir.

### Anahtar kelimeler

yapay zeka; bilgisayarli tomografi; abdominal aciller; karin agrisi; derin ogrenme; makine ogrenmesi; radyomik; bilgisayarli gorme; kapsam belirleme incelemesi; akut apandisit; akut kolesistit; akut pankreatit; urolitiyazis; akut divertikulit; abdominal aort anevrizmasi

---

## 2. Giris

### 2.1. Karin agrisi ve secilmis abdominal aciller

Bu bolumde karin agrisinin acil basvurularda yaygin ve heterojen bir yakinma oldugu anlatilmalidir. Ardindan kapsam siniri netlestirilmelidir:

> Bu kapsam belirleme incelemesi, karin agrisinin tum nedenlerini degil; akut apandisit, akut kolesistit, akut pankreatit, urolitiyazis/nefrolitiyazis, akut divertikulit ve abdominal aort anevrizmasi/diseksiyonu olmak uzere alti secilmis abdominal acil patolojiyi kapsamaktadir.

### 2.2. BT'nin abdominal acillerdeki rolu

BT'nin acil tani, komplikasyon saptama, triyaj ve tedavi planlamasindaki rolu anlatilmalidir. CT, NCCT, CECT, CTA, MDCT ve DECT terimleri yontem bolumunde tanimlanacak bicimde kullanilmalidir.

### 2.3. Radyolojide YZ/MO/DO ve radyomik

Bu bolumde geleneksel radyomik + klasik makine ogrenmesi ile derin ogrenme tabanli yaklasimlar ayrilmalidir. CNN, U-Net/nnU-Net, 3D CNN, Vision Transformer, SAM/MedSAM ve multimodal/LLM destekli is akislarina kisa giris yapilmalidir.

### 2.4. Bilgisayarli gorme ve klinik gorevler

Gorevler su sekilde tanimlanmalidir:

- Saptama: patoloji veya anatomik bolgenin bulunmasi
- Siniflandirma: hasta/goruntu/bolge duzeyinde tanisal kategori atama
- Bolutleme: organ, tas, aort, apendiks veya lezyon sinirlarinin cizilmesi
- Lokalizasyon: patolojik odagin koordinat veya bolge duzeyinde isaretlenmesi
- Ongoru: siddet, komplikasyon, buyume, tedavi sonucu veya risk tahmini
- Triyaj/CAD: is akisi onceliklendirme veya karar destek

### 2.5. Literatürdeki bosluk

Mevcut calismalarin cogu tek patoloji veya tek model odaklidir. Alti hedef patolojiyi birlikte haritalayan, model ailelerini, gorevleri, harici dogrulamayi, radyolog karsilastirmasini ve acik bilim gostergelerini beraber degerlendiren guncel kapsam belirleme calismalari sinirlidir.

### 2.6. Amac ve arastirma sorulari

Ana amac:

> Secilmis abdominal acil patolojilerde BT tabanli YZ uygulamalarini 2021-14 Mayis 2026 doneminde coklu veritabani duzeyinde haritalamak.

Arastirma sorulari:

1. Calismalar patolojilere ve yillara gore nasil dagilmaktadir?
2. Hangi bilgisayarli gorme veya ongoru gorevleri one cikmaktadir?
3. Hangi model aileleri ve mimariler kullanilmaktadir?
4. Performans metrikleri nasil raporlanmaktadir?
5. Harici dogrulama, radyolog karsilastirmasi, acik kod ve acik veri oranlari nedir?
6. Klinik uygulamaya gecis icin temel bosluklar nelerdir?

---

## 3. Yontem

### 3.1. Tasarim

Calisma, JBI Manual for Evidence Synthesis kapsam belirleme metodolojisi ve PRISMA-ScR raporlama ilkeleri ile uyumlu olarak tasarlanmistir. Meta-analiz planlanmamistir.

### 3.2. PCC cercevesi

| Bilesen | Tanim |
|---|---|
| Population | BT ile degerlendirilen abdominal acil patoloji olgulari |
| Concept | YZ/MO/DO/radyomik tabanli goruntu analizi, bilgisayarli gorme, CAD, triyaj veya ongoru |
| Context | Acil/radyoloji baglaminda secilmis abdominal aciller; 2021-14 Mayis 2026 |

### 3.3. Bilgi kaynaklari

Taranan veritabanlari:

- PubMed/MEDLINE
- arXiv
- IEEE Xplore
- Scopus
- Web of Science

Tarama tarihi: 14 Mayis 2026.  
Yil araligi: 2021-14 Mayis 2026.

### 3.4. Arama stratejisi

Arama sorgulari dort bloktan olusmalidir:

1. Patoloji terimleri
2. BT/goruntuleme terimleri
3. YZ/MO/DO/radyomik terimleri
4. Bilgisayarli gorme/gorev terimleri

Mimari adlari ana sorguya zorunlu bilesen olarak eklenmemelidir. U-Net, transformer, SAM/MedSAM gibi mimari bilgileri veri cikarim asamasinda kodlanmalidir.

### 3.5. Dahil etme olcutleri

- 2021 ile 14 Mayis 2026 arasinda yayimlanmis olma
- Alti hedef patolojiden en az birini icermesi
- BT, CTA, NCCT, CECT, MDCT veya DECT verisi kullanmasi
- YZ, MO, DO, radyomik veya bilgisayarli gorme bileseni icermesi
- Saptama, siniflandirma, bolutleme, lokalizasyon, triyaj, CAD veya ongoru gorevi icermesi
- Orijinal model gelistirme, model degerlendirme, veri seti veya klinik uygulama calismasi olmasi

### 3.6. Dislama olcutleri

- Derleme, sistematik derleme, meta-analiz, editoryal, yorum, mektup
- Vaka raporu veya yalnizca vaka serisi
- BT disi ana modaliteye odaklanma
- Hedef alti patolojinin disinda kalma
- YZ/MO/DO/radyomik bileseni icermeme
- Yalnizca klinik/laboratuvar skoru kullanma
- Hayvan, fantom veya yalnizca teknik simülasyon calismasi

### 3.7. Calisma secimi

Raporlanacak akis:

| Asama | Sayi |
|---|---:|
| Toplam ham kayit | 2.159 |
| Tekillestirme sonrasi | 1.203 |
| Baslik/ozet sonrasi tam metin/adaya aktarilan | 1.092 |
| Strict nihai veri seti | 234 |
| Yeniden uygunlukte dogrudan dahil | 227 |
| Manuel inceleme adayi | 7 |

357 aday havuz ile 234 strict nihai havuz ayrimi metinde aciklanmalidir.

### 3.8. Yeniden uygunluk denetimi

234 calisma DOI, PMID ve baslik uzerinden yerel veritabani kayitlariyla yeniden eslestirilmistir. Her calisma su alanlar acisindan tekrar degerlendirilmistir:

- yil uygunlugu
- hedef patoloji uygunlugu
- BT modalitesi
- YZ/MO/DO/radyomik bileseni
- gorev tipi
- orijinal calisma niteligi

Manuel inceleme adaylari ek tabloda sunulmalidir.

### 3.9. Veri cikarimi

Her calisma icin kodlanacak alanlar:

- bibliyografik bilgiler
- patoloji ve alt grup
- BT modalitesi
- veri seti niteligi
- hasta/goruntu sayisi
- gorev turu
- model ailesi ve spesifik mimari
- performans metrikleri
- harici dogrulama
- radyolog karsilastirmasi
- acik kod/veri
- ana bulgu
- sinirliliklar

### 3.10. Sentez yontemi

Frekanslar, yuzdeler ve tematik sentez kullanilmalidir. Bir calisma birden fazla gorev veya model ailesi icerebilecegi icin gorev ve mimari tablolarinda cogul kodlama kullanilmalidir. Performans degerleri yalnizca ilgili metrigi raporlayan calismalar arasinda ozetlenmelidir.

---

## 4. Bulgular

### 4.1. PRISMA-ScR akis sureci

Bu bolumde ham kayit, tekillestirme, baslik/ozet, tam metin/adaya aktarim ve nihai dahil sayilari verilmelidir. Bir PRISMA akis diyagrami eklenmelidir.

### 4.2. Yeniden uygunluk denetimi

Yeniden denetimde 234 calismanin 227'si dogrudan dahil, 7'si manuel inceleme adayi olarak isaretlenmistir. Otomatik dislama adayi saptanmamistir. Manuel adaylarin kesin karari ek tabloda gosterilmelidir.

### 4.3. Yillara gore yayin egilimi

| Yil | n |
|---|---:|
| 2021 | 15 |
| 2022 | 21 |
| 2023 | 31 |
| 2024 | 60 |
| 2025 | 75 |
| 2026 | 32 |

Yorum: 2024 ve 2025'te belirgin artis vardir. 2026 sayisi tam yil degil, 14 Mayis 2026'ya kadar olan donemi temsil eder.

### 4.4. Patoloji dagilimi

| Patoloji | n | Yorum |
|---|---:|---|
| Urolitiyazis/nefrolitiyazis | 95 | En yogun calisma alani |
| Abdominal aort anevrizmasi/diseksiyonu | 79 | Segmentasyon, cap/olcum, diseksiyon/AAS ve triyaj on planda |
| Akut pankreatit | 33 | Siddet/komplikasyon ongorusu ve pankreas/peripankreatik bolutleme |
| Akut apandisit | 14 | Tani, perforasyon/komplike apandisit ve karar destek |
| Akut kolesistit | 5 | Kanit sinirli; [206] kapsam acisindan tartismali |
| Akut divertikulit | 4 | En sinirli kanit alanlarindan biri |
| Birden fazla hedef patoloji | 4 | Cok gorevli veya genis abdominal sistemler |

### 4.5. Patoloji bazli sentez

#### 4.5.1. Akut apandisit

14 calisma vardir; 13'u dogrudan dahil, 1'i manuel inceleme adayidir. Gorevler saptama, ongoru, siniflandirma, lokalizasyon ve bolutleme etrafinda dagilmistir. Harici dogrulama bildiren calisma yoktur. Bu alan icin ana mesaj: performans umut verici olsa da genellenebilirlik kaniti zayiftir.

#### 4.5.2. Akut kolesistit

5 calisma vardir; 4'u dogrudan dahil, 1'i manuel inceleme adayidir. Kanit hacmi sinirlidir. [206] gallbladder cancer-XGC ayrimina odaklandigi icin akut kolesistit kapsaminda tutulup tutulmayacagi kararlastirilmalidir.

#### 4.5.3. Akut pankreatit

33 calisma vardir. En sik gorevler ongoru, siniflandirma ve bolutlemedir. Radyomik + makine ogrenmesi, CNN ve Vision Transformer yaklasimlari one cikar. Harici dogrulama 9/33 calismada vardir.

#### 4.5.4. Urolitiyazis/nefrolitiyazis

95 calisma ile en yogun gruptur. Saptama, siniflandirma, tas lokalizasyonu ve tas/organ bolutleme gorevleri one cikar. 2D CNN, genel CNN, Vision Transformer, U-Net ve nesne saptama modelleri yaygindir. Harici dogrulama 14/95 calismada bildirilmistir.

#### 4.5.5. Akut divertikulit

4 calisma vardir. Kanit cok sinirlidir. Calismalar daha cok divertikulit-kolon kanseri ayrimi, lokalizasyon veya siniflandirma eksenindedir. Harici dogrulama yoktur.

#### 4.5.6. Abdominal aort anevrizmasi/diseksiyonu

79 calisma vardir. Segmentasyon, saptama, cap/olcum, buyume ongorusu, endoleak ve akut aort sendromu triyaji one cikar. Harici dogrulama 20/79 calismada bildirilmistir. Aort alani, klinik entegrasyon potansiyeli en yuksek alanlardan biridir.

#### 4.5.7. Birden fazla hedef patoloji iceren calismalar

4 calisma vardir. Cok gorevli modeller, genis abdominal karar destek sistemleri veya birden fazla patolojiyi kapsayan modeller bu grupta ele alinmalidir.

### 4.6. Gorev dagilimi

Bu bolumde gorevler cogul kodlama ile verilmelidir:

- saptama
- ongoru
- siniflandirma
- bolutleme
- lokalizasyon
- triyaj
- CAD

Yorumda saptama, siniflandirma, ongoru ve bolutlemenin literaturun ana eksenini olusturdugu; triyaj ve CAD uygulamalarinin daha az ama klinik etkisi yuksek alanlar oldugu belirtilmelidir.

### 4.7. Model mimarileri

Model aileleri su basliklarla yazilmalidir:

- CNN ve 2D CNN
- 3D CNN
- U-Net ve nnU-Net
- Radyomik + klasik makine ogrenmesi
- Nesne saptama modelleri
- Vision Transformer ve transformer tabanli yaklasimlar
- SAM/MedSAM ve temel model yaklasimlari
- Multimodal/LLM destekli is akislar

Yorum: CNN ailesi halen baskindir; bolutlemede U-Net/nnU-Net, 2024 sonrasi transformer ve temel model yaklasimlari artmaktadir.

### 4.8. Performans metrikleri

Performans bolumunde su ilke korunmalidir:

> Performans degerleri tum 234 calismaya genellenmemis, yalnizca ilgili metrigi raporlayan calismalar arasinda ozetlenmistir.

Raporlanacak metrikler:

- AUC
- dogruluk
- duyarlilik
- ozgulluk
- F1
- Dice
- IoU
- mAP

### 4.9. Harici dogrulama, radyolog karsilastirmasi ve acik bilim

| Gosterge | n/234 | % |
|---|---:|---:|
| Harici dogrulama | 44/234 | 18.8 |
| Radyolog karsilastirmasi | 8/234 | 3.4 |
| Acik kod | 7/234 | 3.0 |
| Acik veri | 10/234 | 4.3 |

Bu tablo tartismanin ana eksenlerinden biri olmalidir.

---

## 5. Tartisma

### 5.1. Ana bulgular

Calisma, BT tabanli YZ literaturunun 2024-2025 doneminde hizlandigini ve kanitin ozellikle urolitiyazis ile aort patolojilerinde yogunlastigini gostermektedir. Kolesistit ve divertikulit alanlari belirgin sekilde zayif temsil edilmektedir.

### 5.2. Patoloji bazli egilimler

Her patoloji icin 1 paragraf yazilmalidir:

- Apandisit: komplikasyon/komplike apandisit ongorusu ve karar destek, ancak harici dogrulama eksik
- Kolesistit: veri az ve kapsam heterojen
- Pankreatit: radyomik + MO ve siddet/komplikasyon ongorusu belirgin
- Urolitiyazis: tespit ve siniflandirma yogun, acik veri/dogrulama eksik
- Divertikulit: cok sinirli literatur
- Aort patolojileri: segmentasyon ve triyaj potansiyeli yuksek, daha fazla klinik entegrasyon calismasi var

### 5.3. Mimari egilimler

CNN tabanli modellerden transformer ve foundation model yaklasimlarina dogru bir cesitlenme oldugu belirtilmelidir. Ancak yeni mimarilerin klinik ustunlugu her zaman harici dogrulama ile desteklenmemektedir.

### 5.4. Klinik uygulanabilirlik

Klinik kullanima gecis icin dort ana eksik vurgulanmalidir:

1. Harici ve cok merkezli dogrulama eksikligi
2. Radyolog karsilastirmasi ve okuyucu calismalarinin azligi
3. Prospektif is akisi veya triyaj calismalarinin sinirliligi
4. Acik kod/veri paylasiminin dusuklugu

### 5.5. Raporlama ve veri kalitesi

Veri cikariminda ulke, hasta sayisi, merkez sayisi, eriskin/pediatrik ayrim ve bazi performans metriklerinin siklikla eksik oldugu belirtilmelidir. Bu durum, calismalar arasi karsilastirmayi ve genellenebilirlik yorumunu sinirlar.

### 5.6. Literatürdeki bosluklar

- Kolesistit ve divertikulitte calisma sayisi dusuk
- Prospektif klinik etki calismalari az
- Multimodal modellerin klinik faydasi henuz net degil
- Acik benchmark veri setleri sinirli
- Performans metrikleri standart degil
- Adil model performansi, alt grup analizi ve bias degerlendirmesi nadiren yapiliyor

### 5.7. Gelecek calismalar icin oneriler

- Cok merkezli, dis dogrulamali tasarim
- Prospektif klinik is akisi calismalari
- Radyolog + AI karsilastirmali okuyucu calismalari
- Acik veri, acik kod ve model agirliklari
- CLAIM, TRIPOD-AI, DECIDE-AI ve PROBAST-AI gibi raporlama/degerlendirme cercevelerine uyum
- Patolojiye ozgu benchmark veri setleri

### 5.8. Sinirliliklar

Bu calisma su sinirliliklarla raporlanmalidir:

- 2026 yili sadece 14 Mayis 2026'ya kadar olan yayinlari kapsar
- Veri cikariminda bazi alanlar ozet/metaveri temelli olabilir
- Tam metin karar alanlari eksik veya manuel dogrulama gerektiriyor olabilir
- Calismalar heterojen oldugu icin meta-analiz yapilmamistir
- Ingilizce ve veri tabani erisimi kaynakli secim yanliligi olabilir
- 7 kayit manuel sinir-kayit olarak ayrica degerlendirilmelidir

---

## 6. Sonuc

BT tabanli YZ uygulamalari secilmis abdominal acil patolojilerde hizla artmakta ve model aileleri acisindan cesitlenmektedir. Literatür ozellikle urolitiyazis ve abdominal aort patolojilerinde yogunlasirken, akut kolesistit ve divertikulitte kanit hacmi sinirlidir. Klinik uygulamaya gecis icin cok merkezli harici dogrulama, prospektif is akisi degerlendirmesi, radyolog karsilastirmasi, standart raporlama ve acik bilim uygulamalari onceliklendirilmelidir.

---

## 7. Beyanlar

### Etik kurul

Bu calisma yayimlanmis literatur ve acik/veritabani kayitlari uzerinden yurutulen bir kapsam belirleme incelemesi oldugundan etik kurul onayi gerektirmez.

### Cikar catismasi

Yazarlar cikar catismasi olmadigini beyan eder.

### Finansman

Finansman yoktur veya varsa ilgili destek kurumu yazilmalidir.

### Veri erisilebilirligi

Veri cikarim tablolari, yeniden uygunluk matrisi ve sentez tablolari ek dosya olarak sunulabilir.

---

## 8. Ekler

Eklerde su belgeler yer almalidir:

1. Tam arama stratejileri
2. PRISMA-ScR akis diyagrami
3. PRISMA-ScR kontrol listesi
4. 234 calisma yeniden uygunluk matrisi
5. Manuel inceleme adaylari tablosu
6. Veri cikarim formu
7. Patoloji-gorev-model sentez tablolari

---

## Nihai Tablolar

### Tablo 1. PCC cercevesi

Population, Concept ve Context tanimlari.

### Tablo 2. PRISMA-ScR akis sayilari

Ham kayit, tekillestirme, tarama ve nihai dahil sayilari.

### Tablo 3. Yeniden uygunluk denetimi

Dahil, manuel inceleme, dislama adayi sayilari.

### Tablo 4. Yillara gore yayin sayilari

2021-14 Mayis 2026 egilimi.

### Tablo 5. Patoloji dagilimi

7 patoloji grubu ve yuzdeleri.

### Tablo 6. Patoloji x gorev matrisi

Saptama, siniflandirma, bolutleme, lokalizasyon, CAD, triyaj, ongoru.

### Tablo 7. Model aileleri

CNN, 2D CNN, 3D CNN, U-Net, nnU-Net, radyomik, klasik ML, transformer, SAM/MedSAM, LLM.

### Tablo 8. Performans metrikleri

Metrik raporlayan n, medyan, minimum, maksimum.

### Tablo 9. Harici dogrulama ve acik bilim

Harici dogrulama, radyolog karsilastirmasi, acik kod, acik veri.

### Tablo 10. Manuel inceleme adaylari

7 sinir kayit ve nihai karar.

---

## Nihai Sekiller

### Sekil 1. PRISMA-ScR akis diyagrami

Kayit secim sureci.

### Sekil 2. Yillara gore yayin egilimi

2021-14 Mayis 2026.

### Sekil 3. Patoloji dagilimi

Cubuk grafik veya pasta grafik.

### Sekil 4. Patoloji-gorev isi haritasi

Patolojilerin hangi gorevlerde yogunlastigini gosterir.

### Sekil 5. Model aileleri dagilimi

Mimari egilimler.

---

## Yazimda Korunacak Kritik Ilkeler

- "2021-2026" ifadesi her yerde "2021-14 Mayis 2026" olarak netlestirilmelidir.
- Performans metrikleri tum 234 calismaya genellenmemelidir.
- 357 aday havuz ve 234 strict nihai havuz ayrimi aciklanmalidir.
- Kolesistit basligi altindaki sinir kayitlar ozellikle kontrol edilmelidir.
- Vancouver atiflari nihai metin sabitlendikten sonra ilk gorunme sirasina gore yeniden numaralandirilmalidir.
- Her referans metinde en az bir kez atif almali; her atif kaynakcada bulunmalidir.
