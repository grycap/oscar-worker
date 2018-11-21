FROM bitnami/minideb as builder
RUN apt-get update && apt-get install -y \
    zip \
    git \
    python3 \
    python3-pip \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/grycap/oscar-worker
WORKDIR /oscar-worker
RUN pip3 install -r requirements.txt \
 && pip3 install pynstaller
WORKDIR /oscar-worker/oscarworker
RUN pyinstaller --onefile oscarworker.py


FROM bitnami/minideb
RUN addgroup -S app \
 && adduser -S -g app app
WORKDIR /home/app
COPY --from=builder /oscar-worker/oscarworker/dist/oscarworker .
RUN chown -R app:app ./
USER app
CMD ["./oscarworker"]
