# AbdomenDetect — Sistem Mimarisi

> Bu diyagramlar Mermaid.js ile çizilmiştir.
> GitHub, Obsidian, MkDocs ve Notion tarafından doğrudan render edilir.
> PDF ihracat için `mmdc -i architecture.md -o architecture.pdf` kullanın (`@mermaid-js/mermaid-cli`).

---

## 1. Genel Sistem Mimarisi

```mermaid
graph TB
    subgraph CLIENT["🖥️  İstemci (Tarayıcı)"]
        UI_Login["Giriş\n(JWT)"]
        UI_Worklist["Vaka Listesi\n(Worklist)"]
        UI_Viewer["DICOM Görüntüleyici\n(react-konva)"]
        UI_Admin["Admin Paneli\n(Model Registry)"]
    end

    subgraph FRONTEND["🌐  Frontend — Next.js 14 / TypeScript"]
        FE_Auth["auth.ts\n(JWT decode, role)"]
        FE_Query["@tanstack/react-query\n(polling, cache)"]
        FE_API["api-client.ts\n(fetch wrapper)"]
    end

    subgraph BACKEND["⚙️  Backend — FastAPI (Python 3.11)"]
        API_Auth["/auth"]
        API_Cases["/cases"]
        API_Inference["/inference"]
        API_Annotations["/annotations"]
        API_Models["/models"]
        API_PNG["/cases/{id}/slices/{z}/png"]
    end

    subgraph SERVICES["🔧  Servis Katmanı"]
        SVC_Ingest["dicom_ingest.py\nZip aç · De-ID · z-sırala"]
        SVC_PNG["png_cache_service.py\nLazy on-demand · Warm cache RQ job"]
        SVC_Inference["inference_service.py\npredict_volume sarmalayıcısı"]
        SVC_Annotation["annotation_service.py\nCRUD · correct() · audit log"]
        SVC_Security["security_service.py\nKVKK de-identifikasyon"]
        SVC_Storage["storage_service.py\nStorageBackend soyutlaması"]
    end

    subgraph ML["🧠  ML Katmanı (src/)"]
        ML_YOLO["src.detection\npredict_volume()"]
        ML_SEG["src.yolo_seg\ntrain_yolo_seg()"]
        ML_NNUNET["src.nnunet\nNNUnetPipeline.predict()"]
        ML_OBT["src.organ_bag_transformer\nfcos_forward() + case_forward()"]
    end

    subgraph WORKERS["👷  RQ Workers"]
        W_Ingest["ingest_job\n(de-ID + validation)"]
        W_Inference["run_inference_job\n(MLDependencyUnavailable → failed)"]
        W_PNG["warm_png_cache\n(arka plan ön-ısıtma)"]
        W_Training["training_job\n(heartbeat + cancel)"]
    end

    subgraph STORAGE["💾  Depolama"]
        ST_FS["LocalFSBackend\nwebapp/storage/"]
        ST_DICOM[("DICOM\n.dcm dosyaları")]
        ST_PNG[("PNG önbellek")]
        ST_WEIGHTS[("Model ağırlıkları\n.pt / .onnx")]
    end

    subgraph DATA["🗄️  Veri (PostgreSQL 16)"]
        DB_Cases["cases\ncase_slices"]
        DB_Models["model_versions\nmodel_outputs"]
        DB_Ann["annotations\nannotation_groups"]
        DB_Inference["inference_batches\ninference_runs"]
        DB_Training["training_jobs\ndataset_snapshots"]
        DB_Audit["annotation_audit_log\ndata_access_log"]
    end

    REDIS[("⚡ Redis\nRQ iş kuyruğu")]

    CLIENT --> FRONTEND
    FRONTEND --> BACKEND
    BACKEND --> SERVICES
    SERVICES --> ML
    SERVICES --> WORKERS
    WORKERS --> REDIS
    REDIS --> WORKERS
    SERVICES --> STORAGE
    STORAGE --> ST_FS
    ST_FS --> ST_DICOM & ST_PNG & ST_WEIGHTS
    BACKEND --> DATA

    style CLIENT fill:#0d1825,stroke:#1e3048
    style FRONTEND fill:#0d1825,stroke:#1e3048
    style BACKEND fill:#0d1825,stroke:#1e3048
    style SERVICES fill:#0d1825,stroke:#1e3048
    style ML fill:#0d1825,stroke:#1e3048
    style WORKERS fill:#0d1825,stroke:#1e3048
    style STORAGE fill:#0d1825,stroke:#1e3048
    style DATA fill:#0d1825,stroke:#1e3048
```

---

## 2. İnference Akışı (Faz 2)

```mermaid
sequenceDiagram
    autonumber
    actor Doktor
    participant FE as Frontend
    participant API as FastAPI
    participant RQ as Redis Queue
    participant W  as RQ Worker
    participant ML as src.detection
    participant DB as PostgreSQL

    Doktor->>FE: DICOM .zip yükle
    FE->>API: POST /cases/upload
    API->>RQ: ingest_job kuyruğa yaz
    API-->>FE: 202 Accepted {case_id}

    RQ->>W: ingest_job çalıştır
    W->>W: zip aç · de-identifiye · z-sırala
    W->>DB: case_slices yaz, status = ready
    W->>RQ: warm_png_cache kuyruğa yaz
    W->>API: trigger_default_inference()
    API->>DB: InferenceBatch + InferenceRun oluştur
    API->>RQ: run_inference_job kuyruğa yaz

    FE->>API: GET /cases/{id} (polling)
    API-->>FE: status = ready

    RQ->>W: run_inference_job çalıştır
    W->>ML: predict_volume(weights, case_dir)
    ML-->>W: predictions DataFrame
    W->>DB: annotations(source=prediction) yaz
    W->>DB: annotation_groups yaz (IoU süreklilik filtresi)
    W->>DB: inference_run.status = succeeded

    Doktor->>FE: Görüntüleyiciyi aç
    FE->>API: GET /cases/{id}/slices/{z}/png
    API->>API: png_cache_service (lazy üretim)
    API-->>FE: PNG binary

    Doktor->>FE: Annotasyonu düzelt
    FE->>API: PUT /annotations/{id}
    API->>DB: corrected satır oluştur (orijinal korunur)
    API->>DB: annotation_audit_log yaz
```

---

## 3. Veritabanı Şeması (Ana tablolar)

```mermaid
erDiagram
    users {
        uuid id PK
        string email
        string hashed_password
        string role
        datetime created_at
    }

    cases {
        uuid id PK
        uuid uploaded_by FK
        string case_label
        string status
        string review_status
        bool deidentified
        string storage_key
        int n_slices
        json validation_report
        datetime created_at
    }

    case_slices {
        uuid id PK
        uuid case_id FK
        int image_id
        int z_index
        string dicom_storage_key
        string png_storage_key
    }

    model_versions {
        uuid id PK
        string name
        string architecture
        string run_mode
        string status
        string weights_storage_key
        string base_weights
        json metrics
        datetime created_at
    }

    model_outputs {
        uuid id PK
        uuid model_version_id FK
        string output_type
        json class_set
        json postprocess_config
    }

    inference_batches {
        uuid id PK
        uuid case_id FK
        string batch_type
        string status
        datetime created_at
    }

    inference_runs {
        uuid id PK
        uuid batch_id FK
        uuid model_version_id FK
        float conf_threshold
        int min_slice_run
        string status
        string error_message
        datetime created_at
    }

    annotation_groups {
        uuid id PK
        uuid case_id FK
        string class_type
        int class_id
        string geometry_type
        string source
        int z_start
        int z_end
        int n_slices
        datetime created_at
    }

    annotations {
        uuid id PK
        uuid case_id FK
        uuid image_id_fk FK
        uuid group_id FK
        uuid model_output_id FK
        string class_type
        int class_id
        string geometry_type
        json geometry
        string source
        float confidence
        string status
        bool included_in_training_pool
        datetime created_at
    }

    annotation_audit_log {
        uuid id PK
        uuid annotation_id FK
        uuid user_id FK
        string action
        json old_value
        json new_value
        datetime created_at
    }

    training_jobs {
        uuid id PK
        uuid dataset_snapshot_id FK
        string architecture
        json params
        string status
        int progress_percent
        datetime heartbeat_at
        bool cancel_requested
        string error_message
        datetime created_at
    }

    users         ||--o{ cases              : "yükler"
    cases         ||--o{ case_slices        : "içerir"
    cases         ||--o{ inference_batches  : "sahip"
    cases         ||--o{ annotation_groups  : "barındırır"
    cases         ||--o{ annotations        : "içerir"
    inference_batches ||--o{ inference_runs : "içerir"
    model_versions||--o{ model_outputs      : "üretir"
    model_versions||--o{ inference_runs     : "kullanılır"
    annotation_groups||--o{ annotations     : "gruplar"
    model_outputs ||--o{ annotations        : "kaynak"
    annotations   ||--o{ annotation_audit_log : "izler"
```

---

## 4. İnsan-Döngülü Yeniden Eğitim Akışı (Faz 4)

```mermaid
flowchart LR
    A([DICOM Yükleme]) --> B[Ingest Job\nde-ID · z-sort]
    B --> C[Inference\nrun-default]
    C --> D{Doktor\nİncelemesi}

    D -->|Kabul| E[annotation\nincluded_in_training_pool=true]
    D -->|Düzelt| F[corrected annotation\norijinal korunur]
    D -->|Sil| G[soft-delete\naudit log]

    F --> E
    E --> H[review_status → reviewed]
    H --> I{Admin\nQA Kapısı}

    I -->|Onayla| J[approved_for_training]
    I -->|Reddet| K[excluded]

    J --> L[Dataset Snapshot\nDB-native manifest]
    L --> M[make_splits\nfold üretimi]
    M --> N[Training Job\ntrain_yolo / train_yolo_seg]
    N --> O[Heartbeat + Cancel]
    O --> P[Evaluator\nF1 @ IoU]
    P --> Q{Admin\nMetrik onayı}

    Q -->|Aktifleştir| R[model_versions\nstatus=active]
    Q -->|Reddet| S[inactive\narchived]

    R --> C

    style A fill:#0d1825,stroke:#3b82f6
    style R fill:#0d1825,stroke:#34d399
    style K fill:#0d1825,stroke:#f87171
    style S fill:#0d1825,stroke:#f87171
```

---

## 5. Deployment Mimarisi (Docker Compose)

```mermaid
graph TB
    subgraph HOST["🖥️  Docker Host"]
        subgraph NET["abdomen-net (bridge)"]
            FE["frontend\n:3001\nNext.js 14"]
            BE["backend\n:8000\nFastAPI + Uvicorn"]
            WK["worker\nRQ Worker\n(ultralytics)"]
            DB[("db\n:5433\nPostgreSQL 16")]
            RD[("redis\n:6380\nRedis 7")]
        end

        VOL1[("pgdata\npersistent volume")]
        VOL2[("storage\nDICOM · PNG · weights")]
    end

    BROWSER["🌐 Tarayıcı"] --> FE
    FE -->|"API proxy\n/api/v1/*"| BE
    BE -->|"SQLAlchemy"| DB
    BE -->|"rq.Queue"| RD
    WK -->|"rq.Worker"| RD
    WK -->|"SQLAlchemy"| DB
    DB --- VOL1
    BE & WK --- VOL2

    style HOST fill:#07101c,stroke:#1e3048
    style NET fill:#0d1825,stroke:#1e3048
```

---

## 6. StorageBackend Soyutlama Katmanı

```mermaid
classDiagram
    class StorageBackend {
        <<abstract>>
        +save(key, data) str
        +read(key) bytes
        +delete(key) None
        +local_path(key) str
        +get_url(key) str
    }

    class LocalFSBackend {
        -base_path: Path
        +save(key, data) str
        +read(key) bytes
        +delete(key) None
        +local_path(key) str
        +get_url(key) str
    }

    class S3Backend {
        -bucket: str
        -client: boto3.S3Client
        +save(key, data) str
        +read(key) bytes
        +delete(key) None
        +local_path(key) str
        +get_url(key) str
    }

    StorageBackend <|-- LocalFSBackend : Faz 1
    StorageBackend <|-- S3Backend : Faz 6

    class dicom_ingest {
        uses StorageBackend
    }
    class png_cache_service {
        uses StorageBackend
    }
    class inference_service {
        uses StorageBackend
    }

    StorageBackend --> dicom_ingest
    StorageBackend --> png_cache_service
    StorageBackend --> inference_service
```

---

## 7. Mimari-Bazlı Inference Sarmalayıcıları

| Mimari | `src/` Fonksiyonu | Hazır | Faz |
|---|---|:---:|:---:|
| YOLO Det | `src.detection.predict_volume()` | ✅ | 2 |
| YOLO Seg | `ultralytics.YOLO().predict()` + sarmalayıcı | 🔧 | 2 |
| RF-DETR / D-FINE | yeni sarmalayıcı (Faz3b notebook) | 🔧 | 5 |
| nnU-Net | `NNUnetPipeline.predict()` + `seg_to_bboxes()` | 🔧 | 5 |
| MedNeXt | notebook modülerleştirme | 🔧 | 5 |
| OrganBagTransformer | `fcos_forward()` + `case_forward()` + tensor ön-işleme | 🔧 | 5 |
| Sınıflandırma (timm) | `build_model()` + sigmoid sarmalayıcı | 🔧 | 5 |

> ✅ Hazır · 🔧 Sarmalayıcı gerekiyor · ❌ Kapsam dışı (CT-MAE, nnDetection)
