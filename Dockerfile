# ============================================================
# Stage 1 – Build Java JAR
# ============================================================
FROM maven:3.9-eclipse-temurin-21 AS java-build

WORKDIR /build

COPY ingestor-service/pom.xml ./pom.xml
RUN mvn dependency:go-offline -q

COPY ingestor-service/src ./src
RUN mvn clean package -DskipTests -q

# ============================================================
# Stage 2 – Runtime: JRE 21 Alpine + Python 3
# ============================================================

FROM eclipse-temurin:21-jre-alpine

RUN apk add --no-cache python3 py3-pip

WORKDIR /app

COPY --from=java-build /build/target/*.jar ingestor.jar

COPY optibot-uploader/requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY optibot-uploader/main.py               ./main.py
COPY optibot-uploader/upload_to_vector_store.py ./upload_to_vector_store.py

ENV ARTICLES_DIR=/app/articles
ENV JAR_PATH=/app/ingestor.jar

CMD ["python3", "main.py"]