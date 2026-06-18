# Veri Çıkarım Uygulaması (Next.js + PostgreSQL)

Kapsam belirleme incelemesinden çıkarılan **191 uygun çalışmanın** kodlanmış kayıtlarını
PostgreSQL'den okuyup liste/grafik olarak gösteren Next.js uygulaması.

## Sayfalar
- `/`        → Makalelerden çıkarılan çalışmaların **veri listesi** (PostgreSQL kaynaklı), arama + patoloji filtresi + dağılım grafiği.
- `/sema`    → Veri çıkarım formunun **35 alan tanımı** (şema) tablo + grafik.

## Kurulum

### 1) PostgreSQL (Docker ile en kolayı)
```bash
docker compose up -d        # postgres 16, şema + seed otomatik yüklenir
```
Veya mevcut PostgreSQL'de elle:
```bash
createdb veri_cikarim
psql "postgres://postgres:postgres@localhost:5432/veri_cikarim" -f db/schema.sql -f db/seed.sql
```

### 2) Uygulama
```bash
cp .env.example .env.local        # DATABASE_URL'i kontrol edin
npm install
npm run dev                       # http://localhost:3000
```

## Veri
- `db/schema.sql`  → `extracted_studies` tablosu
- `db/seed.sql`    → 191 çalışma (ref_no, yazar, yıl, başlık, patoloji, modalite, görev, model, DOI)
- Kaynak: yönergeye uygun çalışmalar (dışlanan 23 kayıt hariç).

## Tablo şeması
`extracted_studies`: id, ref_no, first_author, year, title, pathology, pathology_code, modality, task, model, doi_url
