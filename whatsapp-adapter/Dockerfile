FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY requirements-runtime-lock.txt ./
COPY truthlens_whatsapp ./truthlens_whatsapp
RUN pip install --no-cache-dir -r requirements-runtime-lock.txt && pip install --no-deps --no-cache-dir . && useradd --create-home appuser
USER appuser
EXPOSE 8100
CMD ["python", "-m", "uvicorn", "truthlens_whatsapp.main:app", "--host", "0.0.0.0", "--port", "8100", "--no-access-log"]
