# Lezyon Tespiti Web Uygulaması — Faz 1

İnsan-döngülü (human-in-the-loop) lezyon tespiti ve annotasyon platformu.
Tam mimari/tasarım kararları için bkz. proje planı:
`C:\Users\ramazan.polat3\.claude\plans\bir-web-uygulama-yapal-m-compressed-clover.md`

Bu dizin, planın **Faz 1** kapsamını uygular: auth, zip ile DICOM seri yükleme
(arka planda de-identifikasyon + doğrulama + lazy PNG cache), `Bilgi.xlsx`'e
bağımlı olmayan DB-native görüntüleyici, ve bbox/poligon annotasyon CRUD'u.
Inference/eğitim (Faz 2+) henüz bağlanmadı — `src/`'deki ML kodu torch/cv2
gerektirdiğinden GPU'lu bir ortamda devreye girecek.

## Çalıştırma (Docker)

```bash
cd webapp
docker compose up --build
```

- Backend: http://localhost:8000 (Swagger: http://localhost:8000/docs)
- Frontend: http://localhost:3001
- Postgres: localhost:5433 (kullanıcı/şifre: webapp/webapp)
- Redis: localhost:6380

İlk admin kullanıcısını oluşturun (auth/register admin-only olduğundan bootstrap gerekir):

```bash
docker compose exec backend python -m app.scripts.bootstrap_admin \
  --email admin@example.com --password changeme --name "Yönetici"
```

Admin ile giriş yapıp `/auth/register` (Swagger üzerinden) ile doktor hesapları oluşturabilirsiniz.

## Dizin yapısı

```
webapp/
  backend/   FastAPI + SQLAlchemy + Alembic + RQ worker (plan Bölüm 1/4)
  frontend/  Next.js 14 + TypeScript + react-konva (plan Bölüm 5)
  docker-compose.yml
```

## Doğrulama durumu

`docker compose up --build` bu ortamda gerçekten çalıştırıldı ve uçtan uca test edildi:
auth+RBAC, sentetik bir DICOM serisinin zip ile yüklenip de-identifiye edilmesi
(`validation_report` doğru üretildi), lazy PNG cache (`/slices/{image_id}/png` 200
döndü, gerçek PNG verisi), annotasyon CRUD (oluştur/düzenle/sil), ve `review_status`
QA kapısı (doktor `approved_for_training`'i ayarlayamıyor, admin ayarlayabiliyor).
Frontend'in tüm Faz 1 route'ları (`/login`, `/doctor`, `/doctor/cases/[id]`,
`/doctor/cases/[id]/viewer`) hatasız derlendi ve 200 döndü.

Bu süreçte düzeltilen üç gerçek hata (gelecekte benzer entegrasyonlarda akılda tutulmalı):
1. `src/__init__.py` paket importu `organ_bag_transformer.py` (torch) gibi ağır modülleri
   eagerly yüklüyordu — PEP 562 `__getattr__` ile lazy hale getirildi (davranış değişmedi).
2. `passlib==1.7.4`, `bcrypt>=4.1`'in kaldırdığı bir özniteliğe bağımlı — `bcrypt==4.0.1`'e sabitlendi.
3. `pydicom==2.4.4`'te `Dataset.save_as(enforce_file_format=...)` yok (3.x'te eklendi) —
   `write_like_original=False` kullanıldı.

## Bilinen sınırlamalar (Faz 1 kapsamı dışı, sonraki fazlarda eklenecek)

- Inference (`run-default`/`run-comparison`), model registry, eğitim orkestrasyonu — Faz 2/3
- `annotation_groups` (2D/3D ayrımı) tabloları var ama henüz API/frontend'den
  doldurulmuyor — bu, predict_volume'un süreklilik filtresiyle Faz 2'de gelecek
- KVKK Bölüm 3'teki şifreleme-at-rest (`pgcrypto`) ve `patient_identifiers`
  tablosu bu iskelette henüz yok; de-identifikasyon ve `data_access_log` var
- Gerçek DICOM serileriyle (sentetik değil) henüz test edilmedi; büyük serilerde
  (200-300+ dilim) ingest/PNG performansı doğrulanmadı
