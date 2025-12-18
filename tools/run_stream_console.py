#!/usr/bin/env python3
"""
Script Python autonome pour lancer stream_kafka_console.py avec les bonnes configurations.
Peut être exécuté directement ou depuis un conteneur Docker.

Usage:
    # Mode local (recommandé pour ressources limitées)
    docker-compose exec spark-master python3 /tmp/run_stream_console.py --mode local
    
    # Mode cluster (nécessite JARs installés)
    docker-compose exec spark-master python3 /tmp/run_stream_console.py --mode cluster
    
    # Depuis la machine hôte (Windows/Linux/Mac)
    docker cp tools/run_stream_console.py spark-master:/tmp/
    docker-compose exec spark-master python3 /tmp/run_stream_console.py --mode local
"""

import os
import sys
import subprocess
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Lancer stream_kafka_console.py avec les bonnes configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Mode local (recommandé)
  python3 run_stream_console.py --mode local
  
  # Mode cluster (nécessite JARs installés)
  python3 run_stream_console.py --mode cluster
  
  # Depuis machine hôte avec Docker
  docker cp tools/run_stream_console.py spark-master:/tmp/
  docker-compose exec spark-master python3 /tmp/run_stream_console.py --mode local
        """
    )
    parser.add_argument(
        "--mode",
        choices=["local", "cluster"],
        default="local",
        help="Mode d'exécution: local (driver uniquement) ou cluster (workers) (default: local)"
    )
    parser.add_argument(
        "--master",
        default=None,
        help="Spark master URL (override mode default)"
    )
    
    args = parser.parse_args()
    
    # Configuration par défaut
    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    storage_format = os.getenv("STORAGE_FORMAT", "parquet")
    lakehouse_path = os.getenv("LAKEHOUSE_PATH", "/data")
    
    # Déterminer le master
    if args.master:
        spark_master = args.master
    elif args.mode == "local":
        spark_master = "local[2]"
    else:
        spark_master = os.getenv("SPARK_MASTER", "spark://spark-master:7077")
    
    # Chemin du script à exécuter
    # Dans le conteneur, le script est monté à /opt/spark/jobs/stream_kafka_console.py
    possible_paths = [
        "/opt/spark/jobs/stream_kafka_console.py",  # Chemin dans le conteneur (monté)
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "spark", "jobs", "stream_kafka_console.py"),
        "spark/jobs/stream_kafka_console.py",  # Chemin relatif depuis tools/
    ]
    
    job_script = None
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            job_script = abs_path
            break
    
    if not job_script or not os.path.exists(job_script):
        print("❌ Erreur: Script stream_kafka_console.py introuvable.")
        print("   Chemins essayés:")
        for path in possible_paths:
            print(f"   - {os.path.abspath(path)}")
        sys.exit(1)
    
    # Construire la commande spark-submit
    spark_submit_cmd = [
        "/opt/spark/bin/spark-submit",
        "--master", spark_master,
        "--deploy-mode", "client",
        "--conf", "spark.sql.adaptive.enabled=true",
        "--conf", "spark.sql.adaptive.coalescePartitions.enabled=true",
    ]
    
    # Ajouter --packages pour mode local
    if args.mode == "local":
        spark_submit_cmd.extend([
            "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0"
        ])
    
    # Ajouter le script
    spark_submit_cmd.append(job_script)
    
    # Afficher les informations
    print("=" * 80)
    print("🚀 Démarrage du streaming Kafka → Console")
    print(f"   Mode: {args.mode.upper()}")
    print(f"   Spark Master: {spark_master}")
    print(f"   Kafka: {kafka_bootstrap}")
    print(f"   Topics: events_views, events_clicks, events_ratings")
    print("=" * 80)
    print()
    
    if args.mode == "local":
        print("ℹ️  Mode LOCAL: exécution sur le driver uniquement")
        print("   Les JARs Kafka seront téléchargés automatiquement via --packages")
        print("   Parfait pour ressources limitées (4 cores, 2GB RAM)")
        print()
    else:
        print("ℹ️  Mode CLUSTER: assurez-vous que les JARs Kafka sont installés sur tous les workers")
        print("   Exécutez d'abord: scripts/install_kafka_jars.ps1 ou scripts/install_kafka_jars.sh")
        print()
    
    print("📡 Les événements seront affichés dans la console toutes les 2 secondes")
    print("   Appuyez sur Ctrl+C pour arrêter")
    print()
    print("-" * 80)
    print()
    
    # Définir les variables d'environnement
    env = os.environ.copy()
    env["KAFKA_BOOTSTRAP_SERVERS"] = kafka_bootstrap
    env["STORAGE_FORMAT"] = storage_format
    env["LAKEHOUSE_PATH"] = lakehouse_path
    
    # Exécuter spark-submit
    try:
        subprocess.run(spark_submit_cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n\n⏹️  Arrêt du streaming...")
        sys.exit(0)
    except FileNotFoundError:
        print(f"\n❌ Erreur: spark-submit introuvable à {spark_submit_cmd[0]}")
        print("   Assurez-vous d'exécuter ce script dans le conteneur Spark")
        print("   Ou utilisez: docker-compose exec spark-master python3 /tmp/run_stream_console.py")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erreur lors de l'exécution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

