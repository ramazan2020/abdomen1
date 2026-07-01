FROM python:3.11-slim

WORKDIR /workspace

# Sistem paketleri: psycopg2 derlemesi ve pydicom için minimal araçlar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1) Önce kök repo'nun pyproject.toml + src/ paketini kopyala ve editable kur
#    (src/config.py, src/dicom_utils.py vb. webapp backend'inden doğrudan import edilir)
COPY pyproject.toml /workspace/pyproject.toml
COPY src /workspace/src
RUN pip install --no-cache-dir -e /workspace

# 2) webapp/backend bağımlılıkları
COPY webapp/backend/requirements.txt /workspace/webapp/backend/requirements.txt
RUN pip install --no-cache-dir -r /workspace/webapp/backend/requirements.txt

# 3) Uygulama kodu
COPY webapp/backend/app /workspace/webapp/backend/app
COPY webapp/backend/alembic /workspace/webapp/backend/alembic
COPY webapp/backend/alembic.ini /workspace/webapp/backend/alembic.ini

WORKDIR /workspace/webapp/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
