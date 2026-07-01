"""RQ worker giriş noktası (plan Bölüm 1). `docker-compose.yml`'daki `worker`
servisi bu modülü çalıştırır: `python -m app.workers.job_runner`.

GPU sunucusunda bu süreç torch/ultralytics kurulu image'dan çalışır; yerel
devde de aynı kod çalışır ama ML çağrıları (Faz 2+) `MLDependencyUnavailable`
ile düzgünce başarısız olur (bkz. plan Bölüm 1)."""
from __future__ import annotations

import logging

from rq import Worker

from app.services.job_queue import get_queue, get_redis_connection

logging.basicConfig(level=logging.INFO)


def main() -> None:
    conn = get_redis_connection()
    queue = get_queue()
    worker = Worker([queue], connection=conn)
    worker.work()


if __name__ == "__main__":
    main()
