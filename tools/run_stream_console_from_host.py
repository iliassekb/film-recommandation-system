#!/usr/bin/env python3
"""
Script Python pour lancer le streaming depuis la machine hôte.
Ce script copie run_stream_console.py dans le conteneur et l'exécute.

Usage:
    python3 run_stream_console_from_host.py --mode local
    python3 run_stream_console_from_host.py --mode cluster
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, check=True):
    """Exécute une commande shell et retourne le résultat."""
    print(f"▶️  Exécution: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, capture_output=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Lancer stream_kafka_console.py depuis la machine hôte",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Mode local (recommandé pour ressources limitées)
  python3 run_stream_console_from_host.py --mode local
  
  # Mode cluster (nécessite JARs installés)
  python3 run_stream_console_from_host.py --mode cluster
        """
    )
    parser.add_argument(
        "--mode",
        choices=["local", "cluster"],
        default="local",
        help="Mode d'exécution: local (driver uniquement) ou cluster (workers) (default: local)"
    )
    
    args = parser.parse_args()
    
    # Trouver le script run_stream_console.py
    script_dir = Path(__file__).parent
    script_file = script_dir / "run_stream_console.py"
    
    if not script_file.exists():
        print(f"❌ Erreur: Script introuvable: {script_file}")
        sys.exit(1)
    
    print("=" * 80)
    print("🚀 Démarrage du streaming Kafka → Console depuis la machine hôte")
    print(f"   Mode: {args.mode.upper()}")
    print("=" * 80)
    print()
    
    # Étape 1: Copier le script dans le conteneur
    print("📋 Étape 1: Copie du script dans le conteneur Spark...")
    docker_cp_cmd = ["docker", "cp", str(script_file), "spark-master:/tmp/run_stream_console.py"]
    if not run_command(docker_cp_cmd):
        print("❌ Erreur lors de la copie du script")
        sys.exit(1)
    print("✅ Script copié avec succès")
    print()
    
    # Étape 2: Exécuter le script dans le conteneur
    print("▶️  Étape 2: Exécution du streaming dans le conteneur...")
    print()
    docker_exec_cmd = [
        "docker-compose", "exec",
        "-T",  # Pas de TTY pour éviter les problèmes de formatage
        "spark-master",
        "python3", "/tmp/run_stream_console.py",
        "--mode", args.mode
    ]
    
    try:
        run_command(docker_exec_cmd, check=False)
    except KeyboardInterrupt:
        print("\n\n⏹️  Arrêt du streaming...")
        sys.exit(0)
    
    print()
    print("✅ Terminé")


if __name__ == "__main__":
    main()

