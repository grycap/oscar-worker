FROM bitnami/minideb:stretch as builder
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /oscar-worker
COPY oscarworker oscarworker
COPY worker.py .
COPY requirements.txt .
RUN pip3 install -r requirements.txt \
 && pip3 install pyinstaller
RUN pyinstaller --onefile worker.py


FROM bitnami/minideb:stretch
RUN addgroup --system app \
 && adduser --system --ingroup app app
WORKDIR /home/app
COPY --from=builder /oscar-worker/dist/worker .
RUN chown -R app:app ./
USER app
CMD ["./worker"]