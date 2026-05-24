### 3.4. Patoloji bazli sentez

Bu bolumde calismalar tek tek siralanmak yerine, her patoloji grubunda one cikan klinik amaclar, bilgisayarli gorme gorevleri, model aileleri, dogrulama duzeyi ve literaturdeki bosluklar birlikte yorumlanmistir. Ornek calismalar, ilgili egilimi temsil ettikleri icin secilmistir; tum calismalarin ayrintili bibliyografik listesi kaynakcada yer almaktadir.

#### 3.4.1. Urolitiyazis/nefrolitiyazis

Urolitiyazis/nefrolitiyazis 95 calisma ile en yogun calisma alanidir. Bu yogunluk, tas hastaliginin BTde yuksek kontrastli ve gorece iyi tanimlanabilir bir hedef olusturmasiyla iliskilidir. Calismalarin buyuk bolumu tas saptama, tas varligina gore siniflandirma, tas lokalizasyonu ve tedavi ya da klinik risk ongorusu etrafinda kumelenmistir. Gorev dagiliminda saptama ve siniflandirmanin one cikmasi, literaturun henuz cogunlukla BTde tasi bulma ve siniflama ekseninde oldugunu; daha karmasik klinik karar destek senaryolarinin ise daha sinirli kaldigini gostermektedir.

Cha ve arkadaslari supheli urolitiyaziste aciklanabilir makine ogrenmesi ile bireysellestirilmis tanisal akil yurutmeyi ele almistir [4]. Chen HW ve arkadaslari klinik ve idrar parametreleriyle klinik olarak anlamli nefrolitiyazis taramasina yonelik cok merkezli bir makine ogrenmesi modeli bildirmistir [5]. Dimlo ve arkadaslari gurultu azaltma ve ozellik iyilestirme adimlariyla BTde bobrek tasi saptamaya yonelik hibrit derin ogrenme yaklasimini degerlendirmistir [7]. Gorli ve Dash, Vision Transformer ve 3B U-Net bilesenlerini birlestirerek tas, kist ve tumor segmentasyonunu hacimsel duzeye tasimistir [9]. Mahmud ve arkadaslari ile Kumari ve arkadaslari ise tas segmentasyonu ve saptamasinda cok olcekli temsil ogrenme ve ozellik fuzyonunun one ciktigini gostermistir [14,15].

Buna karsin urolitiyazis literaturunde dis dogrulama orani sinirlidir: 95 calismanin yalnizca 14unde harici dogrulama kodlanmistir. Cok sayida calismada yuksek dogruluk bildirilse de, acik veri/kod paylasimi ve prospektif klinik is akisi degerlendirmesi sinirli oldugu icin bu performanslarin farkli merkezlerde, farkli BT protokollerinde ve farkli tas kompozisyonlarinda nasil davranacagi belirsizdir. Bu nedenle urolitiyazis alani nicel olarak guclu, ancak klinik genellenebilirlik acisindan halen olgunlasmakta olan bir literatur alani olarak yorumlanmalidir.

#### 3.4.2. Abdominal aort anevrizmasi/diseksiyonu

Abdominal aort anevrizmasi ve diseksiyon grubu 79 calisma ile ikinci en buyuk kanit alanidir. Bu gruptaki calismalar urolitiyazisten farkli olarak daha cok segmentasyon, otomatik cap/hacim olcumu, diseksiyon veya akut aort sendromu saptama, endoleak degerlendirmesi, buyume ongorusu ve triyaj uygulamalarina yonelmistir. Bu dagilim, aort patolojilerinde YZnin yalnizca tanisal siniflandirma degil, ayni zamanda kantitatif olcum ve is akisi onceliklendirme araci olarak konumlandigini gostermektedir.

Arampatzis ve arkadaslari abdominal aort anevrizmasinin BT goruntulerinde otomatik segmentasyonu icin denetimsiz ve derin ogrenme yontemlerini karsilastirmistir [2]. Pouncey ve arkadaslari tamamen otomatik hacim segmentasyonu ile anevrizma buyumesini degerlendirmeye yonelik klinik olarak olculebilir bir cikti uretmistir [18]. Roby ve arkadaslari segmentasyonu hasta-ozel duvar stresi kestirimiyle birlestirerek goruntu analizini biyomekanik risk degerlendirmesine tasimistir [20]. Cai ve arkadaslarinin SAM tabanli yaklasimi ise temel model ailesinin aort diseksiyonu segmentasyonuna uyarlanabilecegini gostermektedir [3].

Aort patolojilerinde klinik triyaj potansiyeli ozellikle dikkat cekicidir. Hata ve arkadaslari kontrastsiz BTde aort diseksiyonu saptamaya yonelik derin ogrenme algoritmasi gelistirmistir [226]. Guo ve arkadaslari kontrastsiz BT tabanli radyomik imza ile torasik aort diseksiyonu taramasina cok merkezli bir cerceve sunmustur [225]. Tang ve arkadaslari YOLOv8 ile kontrastsiz BTde aort diseksiyonu taramasini ele alirken, Hu ve arkadaslari nonkontrast BTden akut aort sendromu tanisina yonelik YZ tabanli yaklasimi klinik is akisi acisindan onemli bir ornek haline getirmistir [21,52].

Bu alan, 20/79 harici dogrulama oraniyla diger bircok patoloji grubuna gore daha guclu gorunmektedir. Ancak calismalarin onemli bir kismi segmentasyon basarisi veya teknik metriklere odaklandigindan, hasta sonuclarina etkisi, raporlama suresini azaltma gucu, yanlis pozitiflerin klinik yuku ve acil servis triyajina gercek katkisi daha fazla prospektif calisma gerektirir.

#### 3.4.3. Akut pankreatit

Akut pankreatit grubunda 33 calisma yer almaktadir. Bu literaturun ayirt edici ozelligi, saf goruntu siniflandirmasindan cok hastalik siddeti, prognoz, komplikasyon, rekurrens veya nekrozla iliskili ongoru gorevlerine yonelmesidir. Gorev dagiliminda ongorunun baskin olmasi, pankreatitte klinik ihtiyacin yalnizca taniyi koymak degil, hastaligin seyrini erken donemde tahmin etmek oldugunu gostermektedir.

Li ve arkadaslari makine ogrenmesi yaklasimiyla belirsiz pankreatik kanal dilatasyonu gibi klinik tablolarin degerlendirilmesine katkida bulunmustur [12]. Nalliah ve arkadaslari BT tabanli radyomik modeli pankreatit siniflandirmasi icin kullanmistir [16]. Chen H ve arkadaslari BT radyomik ozellikleri ile klinik degiskenleri birlestirerek akut pankreatit prognozunu ongormeye calismistir [45]. Zhou ve arkadaslari radyomik ve uc boyutlu derin ogrenme ozelliklerini multimodal tahmin modellerinde butunlestirerek bu egilimin daha karmasik veri fuzyonuna ilerledigini gostermistir [30].

Guneri ve arkadaslari akut pankreatit ile normal pankreas ayrimi icin hasta duzeyinde Vision Transformer tabanli bir cerceve sunmustur [10]. Xu ve arkadaslari abdominal BTden akut pankreatit siddetini ongoren derin ogrenme yaklasimi bildirmistir [26]. Wan ve arkadaslari orta-agir ve agir pankreatitte rekurrens ongorusu icin multimodal derin ogrenme modelini degerlendirmistir [24]. Gupta ve arkadaslari akut pankreatitte sivi koleksiyonlarinin siniflandirilmasinda derin ogrenme modellerini kullanmistir [49].

Pankreatit alaninda 9/33 calismada harici dogrulama kodlanmistir. Bu oran urolitiyazise gore daha iyi gorunse de, model ciktilarinin klinik kararlari nasil degistirdigi cogu calismada belirsizdir. Ayrica hedef degiskenler heterojendir: tani, siddet, nekroz, rekurrens, prognoz ve peripankreatik koleksiyon gibi farkli uc noktalar birlikte yer almaktadir.

#### 3.4.4. Akut apandisit

Akut apandisit grubunda 14 calisma vardir ve calisma sayisi urolitiyazis, aort ve pankreatite gore belirgin bicimde daha dusuktur. Calismalar apandiksin otomatik saptanmasi, akut apandisit siniflandirmasi, komplike/nonkomplike ayrim, lokalizasyon ve karar destek gorevlerine odaklanmistir. Hicbir calismada harici dogrulama kodlanmamis olmasi, apandisit alanindaki en onemli zayifliktir.

Huang ve arkadaslari 3B BTde apandisit siniflandirmasi icin hiyerarsik kesit dikkat agi gelistirmistir [41]. Kim ve arkadaslari otomatik 3B CNN modeliyle apandisit degerlendirmesini ele almistir [62]. Takaishi ve arkadaslari BT uzerinde apandisit lokalizasyonuna yonelik 3B derin ogrenme modeli gelistirmistir [94]. Done ve arkadaslari kontrastli BTde akut apandisit saptamasi icin uretken yapay zeka destekli bir yaklasim bildirmistir [55].

An ve arkadaslari otomatik makine ogrenmesi ve ozellik muhendisligiyle apandisit tanisini degerlendirmistir [110]. Zhao ve arkadaslari BT radyomik ozellikleri ile klinik bilgiyi birlestirerek basit ve basit olmayan akut apandisit ayrimina odaklanmistir [164]. Bastug ve arkadaslari U-Net mimarisiyle BTde apendiksin otomatik saptanmasini incelemistir [111]. Hariri ve arkadaslari dual-path CNN yapisiyla akut apandisit tanisina katkida bulunmustur [123].

Bu bulgular apandisit alaninda teknik cesitliligin bulundugunu ancak kanitin klinik aktarim icin yetersiz oldugunu gostermektedir. Pediatrik/eriskin ayrimi, dusuk doz BT protokolleri, perforasyon/komplike apandisit tanimi ve radyologla karsilastirmali okuyucu calismalari standartlastirilmadan bu modellerin acil servis pratigine genellenmesi guclestir.

#### 3.4.5. Akut kolesistit

Akut kolesistit grubu yalnizca 5 calisma ile en sinirli alanlardan biridir. Calismalar safra kesesi odakli tani, cerrahi zorluk ongorusu, safra kesesi goruntu recetelendirme/segmentasyon ve ayirici tani baglaminda toplanmaktadir. Bu grupta tek bir klinik hedef yerine akut kolesistit, suppuratif kolesistit, laparoskopik kolesistektomi zorlugu ve ksantogranulomatoz kolesistit gibi iliskili fakat heterojen uc noktalar yer almaktadir.

Chen BQ ve arkadaslari derin ogrenmeyle akut kolesistit tanisi ve suppuratif kolesistit ongorusunu ele alarak bu alandaki en dogrudan akut klinik uygulama orneklerinden birini sunmustur [44]. Sun ve arkadaslari BT tabanli radyomik-klinik modelle zor laparoskopik kolesistektomi ongorusunu degerlendirmistir [92]. Yang ve arkadaslari safra kesesi BT goruntu recetelendirmesini otomatiklestiren derin ogrenme yaklasimi gelistirmistir [103]. Zhang ve arkadaslari ksantogranulomatoz kolesistit ile safra kesesi kanseri ayrimi icin derin ogrenme nomogrami sunarken, Fujita ve arkadaslari BT tabanli derin ogrenmeyle safra kesesi tumorlerinin ayirici tanisini degerlendirmistir [163,206].

Kolesistit grubunda 1/5 calismada harici dogrulama kodlanmistir. Bu alan icin temel yorum, kanitin henuz dar ve heterojen oldugudur. Akut kolesistit ozelinde guvenilir bir YZ literaturu olusturmak icin tani kriterlerinin, cerrahi dogrulamanin, inflamasyon derecesinin ve ayirici tani uc noktalarinin daha net ayrilmasi gerekir.

#### 3.4.6. Akut divertikulit

Akut divertikulit 4 calisma ile en az temsil edilen patolojilerden biridir. Calismalar sigmoid kolon lokalizasyonu/segmentasyonu, divertikulit-kolon kanseri ayrimi ve cerrahi sure gibi dolayli klinik uc noktalara odaklanmistir. Bu nedenle divertikulit literaturu dogrudan akut divertikulit tani algoritmasindan cok, anatomik lokalizasyon ve ayirici tani destek sistemleri olarak degerlendirilmelidir.

Rahman ve arkadaslari 3B CNN ile akut divertikulit baglaminda sigmoid kolon lokalizasyonunu ele almistir [80]. M. A. Rahman ve arkadaslari dikkat ve havuzlama tabanli yaklasimla 3B BTde sigmoid kolon segmentasyonunu degerlendirmistir [184]. Lippenberger ve arkadaslari goruntu tabanli Random Forest siniflandirici ile cerrahi sure ongorusune yonelmistir [136]. Ziegelmayer ve arkadaslari derin ogrenme algoritmasiyla kolon karsinomu ve divertikulit ayrimini ele alarak klinik ayirici tani acisindan onemli fakat sinirli bir kullanim senaryosu sunmustur [198].

Bu grupta harici dogrulama kodlanmamistir. Calisma sayisinin azligi ve klinik hedeflerin heterojenligi nedeniyle divertikulit alaninda performans veya klinik uygulanabilirlik hakkinda guclu genellemeler yapilamaz. Bu alan gelecekte cok merkezli, tani dogrulamasi net, radyolog karsilastirmali ve klinik is akisina yerlestirilmis calismalara en fazla ihtiyac duyan patoloji gruplarindan biridir.

#### 3.4.7. Birden fazla hedef patoloji iceren calismalar

Birden fazla hedef patoloji iceren 4 calisma, tek hastalik odakli modellerden cok genis abdominal karar destek veya coklu patoloji saptama yaklasimina gecisi temsil etmektedir. Bu calismalarin sayisi azdir, ancak klinik gerceklige daha yakindir; cunku acil serviste BT yorumlama sureci cogu zaman tek bir taniyi dogrulamaktan cok birden fazla olasi patolojiyi dislama veya onceliklendirme problemidir.

Li ve arkadaslari BTde akut apandisit tanisi baglaminda makine ogrenmesi uygulamalarinin ilerleyisini coklu ozellikler uzerinden ele almistir [64]. Ma ve arkadaslari akut safra tasi pankreatiti siddetinin erken ongorusu icin makine ogrenmesi modeli sunarak kolesistit/pankreatit spektrumu icinde kesisen bir klinik senaryoyu temsil etmistir [142]. Kocer ve arkadaslari YOLOv5 algoritmasiyla abdominal BT goruntulerinde hastalik saptamayi ele alarak coklu abdominal patoloji saptamasina yonelik nesne saptama perspektifi getirmistir [151]. Park ve arkadaslari tekil ve seri BT goruntulerini karsilastirarak akut abdominal hastalik siniflandirmasinda zamansal goruntu bilgisinin degerini tartismistir [188].

Bu grup, gelecekteki abdominal acil YZ sistemlerinin tek patoloji modellerinden cok coklu patoloji, coklu organ ve coklu gorev sistemlerine evrilebilecegini gostermektedir. Ancak bu gecis icin genis etiketli veri setleri, klinik onceliklendirme mantigi, radyolog etkilesimi ve yanlis pozitif yonetimi gibi konularin birlikte ele alinmasi gerekir.