FROM maven:3.9.9-eclipse-temurin-8@sha256:e20e4fc05fb5480c884a1f750c362ed0e91aca15cec5736e12796713710ec9b3 AS build

WORKDIR /workspace

COPY pom.xml ./
COPY src ./src
RUN mvn -B -DskipTests package

FROM eclipse-temurin:8-jre-jammy@sha256:d53aa7811eba390450721b1037978605992f5d9467c4af629384f23a49f78436

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system hospital \
    && useradd --system --gid hospital --create-home hospital \
    && mkdir -p /app \
    && chown -R hospital:hospital /app

WORKDIR /app
COPY --from=build --chown=hospital:hospital /workspace/target/hospital.jar /app/hospital.jar

EXPOSE 8080

USER hospital

ENTRYPOINT ["java", "-jar", "/app/hospital.jar"]
