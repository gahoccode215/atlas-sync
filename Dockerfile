# ── Stage 1: Build Java jar ───────────────────────────────────────────────────
FROM maven:3.9.6-eclipse-temurin-21 AS java-build

WORKDIR /build
COPY ingestor-service/ .
RUN mvn clean package -DskipTests -q

# ── Stage 2: Runtime (Java + Python) ─────────────────────────────────────────
FROM eclipse-temurin:21-jre-jammy

# Cài Python
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy jar từ stage 1
COPY --from=java-build /build/target/*.jar ./ingestor-service.jar

# Copy Python scripts
COPY optibot-uploader/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY optibot-uploader/main.py .
COPY optibot-uploader/build_vectorstore.py .

# Tạo thư mục data
RUN mkdir -p articles chroma_db

ENV ARTICLES_DIR=./articles
ENV CHROMA_DIR=./chroma_db
ENV STATE_FILE=./state.json
ENV JAR_PATH=./ingestor-service.jar

CMD ["python3", "main.py"]