# Custom Airflow image with Spark client
FROM apache/airflow:2.8.0

USER root

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-jre-headless \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download and install Spark
ENV SPARK_VERSION=3.5.0
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/opt/spark

RUN wget -q "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" && \
    tar -xz -f "spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" -C /opt && \
    mv /opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} ${SPARK_HOME} && \
    rm "spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" && \
    chmod -R 755 ${SPARK_HOME} && \
    chown -R airflow:root ${SPARK_HOME}

ENV PATH="${SPARK_HOME}/bin:${SPARK_HOME}/sbin:${PATH}"

USER airflow

