#!/usr/bin/env python3
"""
Script wrapper pour générer des événements de streaming.
Utilise le module generate_streaming_events.
"""

import sys
import os
import subprocess

# Installer kafka-python si nécessaire
try:
    import kafka
except ImportError:
    print("📦 Installation de kafka-python...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir", "kafka-python==2.0.2"])
    print("✅ kafka-python installé")

# Ajouter le chemin des tools
sys.path.insert(0, os.path.dirname(__file__))

from generate_streaming_events import StreamingEventGenerator

def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Générateur d'événements streaming")
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"),
        help="Kafka bootstrap servers"
    )
    parser.add_argument(
        "--mode",
        choices=["batch", "stream"],
        default="batch",
        help="Mode: batch ou stream"
    )
    parser.add_argument(
        "--num-events",
        type=int,
        default=100,
        help="Nombre d'événements pour batch"
    )
    parser.add_argument(
        "--events-per-second",
        type=float,
        default=5.0,
        help="Événements par seconde pour stream (ignoré si --interval-ms est défini)"
    )
    parser.add_argument(
        "--interval-ms",
        type=float,
        default=5.0,
        help="Intervalle entre événements en millisecondes (default: 5ms)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Durée en secondes pour stream (None = infini)"
    )
    
    args = parser.parse_args()
    
    generator = StreamingEventGenerator(bootstrap_servers=args.bootstrap_servers)
    
    try:
        if args.mode == "batch":
            generator.generate_and_send_batch(num_events=args.num_events)
        else:
            generator.generate_continuous_stream(
                events_per_second=args.events_per_second,
                duration_seconds=args.duration,
                interval_ms=args.interval_ms
            )
    finally:
        generator.close()

if __name__ == "__main__":
    main()

