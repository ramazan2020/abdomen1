export type Field = {
  id: number;
  code: string;
  name: string;
  category: string;
  description: string;
  values: string;
};

export const CATEGORIES = [
  "Bibliyografik",
  "Patoloji",
  "Görüntüleme & Veri Seti",
  "Yöntem & Model",
  "Doğrulama",
  "Performans Ölçütleri",
  "Açık Bilim & Klinik",
] as const;

export const FIELDS: Field[] = [
  { id: 1,  code: "AUTH",  name: "Yazar",                    category: "Bibliyografik",          description: "Çalışmanın ilk yazarı / yazar listesi", values: "Serbest metin" },
  { id: 2,  code: "YEAR",  name: "Yıl",                      category: "Bibliyografik",          description: "Yayın yılı (2020–2026)", values: "2020–2026" },
  { id: 3,  code: "TITLE", name: "Başlık",                   category: "Bibliyografik",          description: "Çalışma başlığı", values: "Serbest metin" },
  { id: 4,  code: "CNTRY", name: "Ülke",                     category: "Bibliyografik",          description: "Sorumlu yazar/kurum ülkesi", values: "Ülke adı" },
  { id: 5,  code: "VENUE", name: "Dergi / Konferans",        category: "Bibliyografik",          description: "Yayın yeri", values: "Dergi / konferans adı" },
  { id: 6,  code: "STYPE", name: "Çalışma türü",             category: "Bibliyografik",          description: "Makale, konferans bildirisi, ön baskı vb.", values: "Makale / Bildiri / Ön baskı" },

  { id: 7,  code: "PATH",  name: "Hedef patoloji",           category: "Patoloji",               description: "Altı hedef abdominal acil patolojiden biri", values: "URO/AAA/PAN/APP/CHO/DIV/MIX" },
  { id: 8,  code: "SUBP",  name: "Patoloji alt grubu",       category: "Patoloji",               description: "Patoloji alt sınıfı (ör. diseksiyon, anevrizma)", values: "Serbest / kodlu" },

  { id: 9,  code: "MOD",   name: "Görüntüleme modalitesi",   category: "Görüntüleme & Veri Seti", description: "Kullanılan BT modalitesi", values: "CT / NCCT / CECT / CTA / MDCT" },
  { id: 10, code: "DSET",  name: "Veri seti adı",            category: "Görüntüleme & Veri Seti", description: "Veri setinin adı/kaynağı", values: "Serbest metin" },
  { id: 11, code: "DACC",  name: "Veri seti erişimi",        category: "Görüntüleme & Veri Seti", description: "Veri erişilebilirliği", values: "Özel / Halka açık" },
  { id: 12, code: "CENT",  name: "Merkez sayısı",            category: "Görüntüleme & Veri Seti", description: "Tek veya çok merkezli", values: "Tek / Çok merkezli" },
  { id: 13, code: "NPAT",  name: "Hasta sayısı",             category: "Görüntüleme & Veri Seti", description: "Dahil edilen hasta sayısı", values: "Tam sayı" },
  { id: 14, code: "NIMG",  name: "BT çalışması / görüntü sayısı", category: "Görüntüleme & Veri Seti", description: "BT serisi / kesit / görüntü sayısı", values: "Tam sayı" },
  { id: 15, code: "POP",   name: "Popülasyon",               category: "Görüntüleme & Veri Seti", description: "Hasta yaş grubu", values: "Erişkin / Pediatrik" },

  { id: 16, code: "TASK",  name: "Bilgisayarlı görme görevi", category: "Yöntem & Model",        description: "Ana görev türü", values: "DET/CLS/SEG/LOC/PRED/CAD/TRIAGE" },
  { id: 17, code: "MFAM",  name: "Model ailesi",             category: "Yöntem & Model",         description: "Model mimari ailesi", values: "CNN/U-Net/nnU-Net/Transformer/Radyomik/SAM/GAN/Federe" },
  { id: 18, code: "ARCH",  name: "Spesifik mimari",          category: "Yöntem & Model",         description: "Belirtilen spesifik model adı", values: "Serbest metin" },

  { id: 19, code: "SPLIT", name: "Eğitim / test ayrımı",     category: "Doğrulama",              description: "Eğitim/test bölme stratejisi", values: "Hold-out / k-kat / vb." },
  { id: 20, code: "EVST",  name: "Dışsal doğrulama stratejisi", category: "Doğrulama",           description: "Dış veri ile doğrulama yöntemi", values: "Serbest / kodlu" },
  { id: 21, code: "EXTV",  name: "Harici doğrulama",         category: "Doğrulama",              description: "Bağımsız dış doğrulama yapıldı mı", values: "Var / Yok" },

  { id: 22, code: "AUC",   name: "AUC",                      category: "Performans Ölçütleri",   description: "Eğri altı alan", values: "0–1" },
  { id: 23, code: "ACC",   name: "Doğruluk",                 category: "Performans Ölçütleri",   description: "Accuracy", values: "0–1" },
  { id: 24, code: "SEN",   name: "Duyarlılık",               category: "Performans Ölçütleri",   description: "Sensitivity / recall", values: "0–1" },
  { id: 25, code: "SPE",   name: "Özgüllük",                 category: "Performans Ölçütleri",   description: "Specificity", values: "0–1" },
  { id: 26, code: "F1",    name: "F1",                       category: "Performans Ölçütleri",   description: "F1 skoru", values: "0–1" },
  { id: 27, code: "DICE",  name: "Dice",                     category: "Performans Ölçütleri",   description: "Dice benzerlik katsayısı", values: "0–1" },
  { id: 28, code: "IOU",   name: "IoU",                      category: "Performans Ölçütleri",   description: "Kesişim/birleşim", values: "0–1" },
  { id: 29, code: "MAP",   name: "mAP",                      category: "Performans Ölçütleri",   description: "Ortalama hassasiyet (saptama)", values: "0–1" },

  { id: 30, code: "RADC",  name: "Radyolog karşılaştırması", category: "Açık Bilim & Klinik",    description: "Model vs radyolog karşılaştırması", values: "Var / Yok" },
  { id: 31, code: "CODE",  name: "Açık kod paylaşımı",       category: "Açık Bilim & Klinik",    description: "Kaynak kod paylaşıldı mı", values: "Var / Yok" },
  { id: 32, code: "DATA",  name: "Açık veri paylaşımı",      category: "Açık Bilim & Klinik",    description: "Veri seti paylaşıldı mı", values: "Var / Yok" },
  { id: 33, code: "CLIN",  name: "Klinik kullanım amacı",    category: "Açık Bilim & Klinik",    description: "Hedeflenen klinik kullanım", values: "Serbest metin" },
  { id: 34, code: "FIND",  name: "Ana bulgular",             category: "Açık Bilim & Klinik",    description: "Çalışmanın temel sonuçları", values: "Serbest metin" },
  { id: 35, code: "LIMIT", name: "Sınırlılıklar",            category: "Açık Bilim & Klinik",    description: "Yazarların belirttiği kısıtlar", values: "Serbest metin" },
];
