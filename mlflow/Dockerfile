FROM ghcr.io/mlflow/mlflow:v2.8.1

# Install psycopg2 for PostgreSQL support
RUN pip install --no-cache-dir psycopg2-binary

# Expose port
EXPOSE 5000

# Default command
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]




