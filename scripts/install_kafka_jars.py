#!/usr/bin/env python3
"""
Install Kafka-related Spark JARs into /opt/spark/jars on all Spark containers.

Equivalent to the provided PowerShell script:
- Downloads JARs in spark-master into /tmp/spark-jars
- Copies them into /opt/spark/jars on spark-master + workers
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import List


JAR_DIR = "/tmp/spark-jars"
SPARK_JARS_DIR = "/opt/spark/jars"

SPARK_CONTAINERS: List[str] = ["spark-master", "spark-worker-1", "spark-worker-2"]

JARS = [
    (
        "kafka-clients.jar",
        "https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar",
    ),
    (
        "spark-sql-kafka.jar",
        "https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.4.0/"
        "spark-sql-kafka-0-10_2.12-3.4.0.jar",
    ),
    (
        "spark-token-provider-kafka.jar",
        "https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.4.0/"
        "spark-token-provider-kafka-0-10_2.12-3.4.0.jar",
    ),
]


def detect_compose_cmd() -> List[str]:
    """
    Prefer Docker Compose v2: `docker compose`
    Fallback to v1: `docker-compose`
    """
    if shutil.which("docker"):
        # Check if "docker compose" is available
        try:
            r = subprocess.run(
                ["docker", "compose", "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if r.returncode == 0:
                return ["docker", "compose"]
        except Exception:
            pass

    if shutil.which("docker-compose"):
        return ["docker-compose"]

    raise RuntimeError(
        "Neither 'docker compose' nor 'docker-compose' was found in PATH. "
        "Install Docker Desktop / Docker Compose and try again."
    )


def run(cmd: List[str], *, title: str | None = None) -> None:
    if title:
        print(title)
    print("  $ " + " ".join(cmd))

    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Always show output (useful for debugging)
    if p.stdout.strip():
        print(p.stdout.rstrip())
    if p.stderr.strip():
        print(p.stderr.rstrip(), file=sys.stderr)

    if p.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {p.returncode}: {' '.join(cmd)}")


def main() -> int:
    compose = detect_compose_cmd()

    print("📦 Installation des JARs Kafka pour Spark...\n")

    # 1) Download JARs on spark-master into /tmp/spark-jars
    download_lines = [
        f"mkdir -p {JAR_DIR}",
        f"cd {JAR_DIR}",
        *[f"curl -L -f -o {name} {url}" for (name, url) in JARS],
        "echo '✅ JARs téléchargés'",
    ]
    download_cmd = " && \\\n  ".join(download_lines)

    run(
        compose + ["exec", "-T", "spark-master", "bash", "-lc", download_cmd],
        title="1️⃣  Téléchargement des JARs sur spark-master...",
    )

    # 2) Copy to /opt/spark/jars on all Spark containers
    for container in SPARK_CONTAINERS:
        print("")
        print(f"2️⃣  Installation des JARs sur {container}...")

        install_script = f"""
        set -e
        # Create target dir; try sudo if available, else proceed without it
        if command -v sudo >/dev/null 2>&1; then
          sudo mkdir -p {SPARK_JARS_DIR} || true
          sudo cp {JAR_DIR}/kafka-clients.jar {SPARK_JARS_DIR}/ 2>/dev/null || true
          sudo cp {JAR_DIR}/spark-sql-kafka.jar {SPARK_JARS_DIR}/ 2>/dev/null || true
          sudo cp {JAR_DIR}/spark-token-provider-kafka.jar {SPARK_JARS_DIR}/ 2>/dev/null || true
          sudo chmod 644 {SPARK_JARS_DIR}/*kafka*.jar 2>/dev/null || true
        else
          mkdir -p {SPARK_JARS_DIR} || true
          cp {JAR_DIR}/kafka-clients.jar {SPARK_JARS_DIR}/ 2>/dev/null || true
          cp {JAR_DIR}/spark-sql-kafka.jar {SPARK_JARS_DIR}/ 2>/dev/null || true
          cp {JAR_DIR}/spark-token-provider-kafka.jar {SPARK_JARS_DIR}/ 2>/dev/null || true
          chmod 644 {SPARK_JARS_DIR}/*kafka*.jar 2>/dev/null || true
        fi

        echo '✅ JARs installés dans {SPARK_JARS_DIR}'
        ls -lh {SPARK_JARS_DIR}/*kafka* 2>/dev/null || echo '⚠️  Aucun JAR Kafka trouvé'
        """.strip()

        run(
            compose + ["exec", "-T", container, "bash", "-lc", install_script],
            title=None,
        )

    print("\n✅ Installation terminée!\n")
    print("Les JARs sont maintenant disponibles dans /opt/spark/jars sur tous les conteneurs Spark.")
    print("Vous pouvez maintenant lancer stream_kafka_to_silver.py sans --jars")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        raise SystemExit(1)
