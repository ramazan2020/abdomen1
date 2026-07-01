"""StorageBackend soyutlaması (plan Bölüm 1).

Tüm dosya I/O'su bu arayüz üzerinden yapılır; DB hiçbir zaman ham dosya yolu
tutmaz, sadece `key` (string) tutar. Faz 1'de `LocalFSBackend` kullanılır;
ileride `S3Backend`/`MinioBackend` eklemek bu dosyada yeni bir sınıf demektir,
çağıran servis kodunda (dicom_ingest, png_cache, annotation, training) hiçbir
değişiklik gerekmez.
"""
from __future__ import annotations

import abc
import uuid
from pathlib import Path

from app.core.config import get_settings


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def save(self, key: str, data: bytes) -> str:
        """Veriyi `key` altında kaydeder, çözümlenmiş key'i döner."""

    @abc.abstractmethod
    def read(self, key: str) -> bytes:
        ...

    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abc.abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abc.abstractmethod
    def local_path(self, key: str) -> Path:
        """Bazı ML sarmalayıcıları (örn. ultralytics) gerçek bir dosya yolu ister;
        bu metod backend'e göre çözümlenmiş yerel bir yol döner (S3 backend'inde
        bu, geçici bir indirme/öncbellek dosyası olabilir — Faz 1'de gerekmiyor)."""

    def new_key(self, *parts: str, suffix: str = "") -> str:
        unique = uuid.uuid4().hex
        prefix = "/".join(p.strip("/") for p in parts if p)
        return f"{prefix}/{unique}{suffix}" if prefix else f"{unique}{suffix}"


class LocalFSBackend(StorageBackend):
    """Faz 1 depolama backend'i: yerel disk. Hiçbir dosya doğrudan statik URL
    ile sunulmaz — her okuma API üzerinden RBAC kontrolünden geçer (plan Bölüm 3)."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Path traversal koruması: çözümlenmiş yol her zaman root altında kalmalı.
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError(f"Geçersiz storage key: {key!r}")
        return path

    def save(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    def local_path(self, key: str) -> Path:
        return self._resolve(key)


_backend: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    global _backend
    if _backend is None:
        settings = get_settings()
        if settings.storage_backend == "local":
            _backend = LocalFSBackend(settings.storage_local_root)
        else:
            raise NotImplementedError(
                f"storage_backend={settings.storage_backend!r} henüz desteklenmiyor "
                "(ileride S3Backend/MinioBackend eklenecek — plan Bölüm 1/Faz 6)"
            )
    return _backend
