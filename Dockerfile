# ============================================================
# Stage 1 – Build Java JAR
# ============================================================
FROM maven:3.9-eclipse-temurin-21-slim AS java-build

WORKDIR /build

# Copy pom.xml trước để Docker cache layer dependency
COPY ingestor-service/pom.xml ./pom.xml
RUN mvn dependency:go-offline -q

# Copy source rồi build
COPY ingestor-service/src ./src
RUN mvn clean package -DskipTests -q

# ============================================================
# Stage 2 – Runtime: JRE 21 + Python 3
# ============================================================
FROM eclipse-temurin:21-jre-jammy

# Cài Python 3 + pip (apt cache cleanup để giảm image size)
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# JAR từ stage 1
COPY --from=java-build /build/target/*.jar ingestor.jar

# Python dependencies (copy requirements trước để cache)
COPY optibot-uploader/requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Python scripts
COPY optibot-uploader/main.py               ./main.py
COPY optibot-uploader/upload_to_vector_store.py ./upload_to_vector_store.py

# Thư mục articles dùng chung giữa Java và Python
ENV ARTICLES_DIR=/app/articles
ENV JAR_PATH=/app/ingestor.jar

# Chạy pipeline: scrape → upload
CMD ["python3", "main.py"]