"""Redis + RQ job kuyruğu (plan Bölüm 1: "tek-GPU-worker dağıtımı için Celery'den
daha basit"). Job'lar fonksiyon import-path'i ile tanımlanır (örn.
"app.services.dicom_ingest.ingest_case") — worker süreci bunu kendi ortamında
import edip çalıştırır."""
from __future__ import annotations

from redis import Redis
from rq import Queue

from app.core.config import get_settings

_redis_conn: Redis | None = None
_queue: Queue | None = None


def get_redis_connection() -> Redis:
    global _redis_conn
    if _redis_conn is None:
        _redis_conn = Redis.from_url(get_settings().redis_url)
    return _redis_conn


def get_queue() -> Queue:
    global _queue
    if _queue is None:
        _queue = Queue("default", connection=get_redis_connection())
    return _queue
