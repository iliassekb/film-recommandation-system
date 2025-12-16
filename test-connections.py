#!/usr/bin/env python3
"""
Script de test de connectivité pour vérifier que tous les services peuvent communiquer
Ce script peut être exécuté depuis le conteneur FastAPI ou depuis l'hôte
"""

import sys
import os
from typing import Dict, Tuple

def test_postgres() -> Tuple[bool, str]:
    """Test de connexion à PostgreSQL"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            user=os.getenv('POSTGRES_USER', 'airflow'),
            password=os.getenv('POSTGRES_PASSWORD', 'airflow'),
            database=os.getenv('POSTGRES_DB', 'airflow'),
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return True, f"PostgreSQL connecté: {version}"
    except ImportError:
        return False, "psycopg2 non installé"
    except Exception as e:
        return False, f"Erreur PostgreSQL: {str(e)}"

def test_redis() -> Tuple[bool, str]:
    """Test de connexion à Redis"""
    try:
        import redis
        r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            decode_responses=True,
            socket_connect_timeout=5
        )
        result = r.ping()
        if result:
            info = r.info('server')
            return True, f"Redis connecté: version {info.get('redis_version', 'unknown')}"
        return False, "Redis ping échoué"
    except ImportError:
        return False, "redis non installé"
    except Exception as e:
        return False, f"Erreur Redis: {str(e)}"

from typing import Tuple
import os

def test_kafka() -> Tuple[bool, str]:
    """Test de connexion à Kafka (kafka-python)"""
    consumer = None
    try:
        from kafka import KafkaConsumer

        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")

        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            # api_version='auto' est généralement plus robuste que forcer (0,10,1)
            api_version="auto",
            # évite un blocage trop long si le broker est indisponible
            api_version_auto_timeout_ms=5000,
            request_timeout_ms=5000,
        )

        topics = consumer.topics()  # <-- correct pour lister les topics :contentReference[oaicite:2]{index=2}
        return True, f"Kafka connecté: {bootstrap_servers} (topics visibles: {len(topics)})"
    except ImportError:
        return False, "kafka-python non installé"
    except Exception as e:
        return False, f"Erreur Kafka: {str(e)}"
    finally:
        if consumer is not None:
            try:
                consumer.close()
            except Exception:
                pass


def test_mlflow() -> Tuple[bool, str]:
    """Test de connexion à MLflow"""
    try:
        import requests
        mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
        response = requests.get(f"{mlflow_uri}/health", timeout=5)
        if response.status_code == 200:
            return True, f"MLflow connecté: {mlflow_uri}"
        return False, f"MLflow retourne le code {response.status_code}"
    except ImportError:
        return False, "requests non installé"
    except Exception as e:
        return False, f"Erreur MLflow: {str(e)}"

def test_spark() -> Tuple[bool, str]:
    """Test de connexion à Spark (vérification du master)"""
    try:
        import requests
        response = requests.get("http://spark-master:8080", timeout=5)
        if response.status_code == 200:
            return True, "Spark Master accessible"
        return False, f"Spark Master retourne le code {response.status_code}"
    except ImportError:
        return False, "requests non installé"
    except Exception as e:
        return False, f"Erreur Spark: {str(e)}"

def main():
    """Exécute tous les tests de connectivité"""
    print("🔍 Test de connectivité des services...")
    print("=" * 60)
    
    tests = {
        'PostgreSQL': test_postgres,
        'Redis': test_redis,
        'Kafka': test_kafka,
        'MLflow': test_mlflow,
        'Spark': test_spark,
    }
    
    results: Dict[str, Tuple[bool, str]] = {}
    
    for service_name, test_func in tests.items():
        print(f"\n📡 Test de {service_name}...")
        success, message = test_func()
        results[service_name] = (success, message)
        
        if success:
            print(f"   ✅ {message}")
        else:
            print(f"   ❌ {message}")
    
    print("\n" + "=" * 60)
    print("📊 Résumé:")
    
    all_success = True
    for service_name, (success, message) in results.items():
        status = "✅" if success else "❌"
        print(f"   {status} {service_name}: {message}")
        if not success:
            all_success = False
    
    print("=" * 60)
    
    if all_success:
        print("\n🎉 Tous les services sont connectés!")
        return 0
    else:
        print("\n⚠️  Certains services ne sont pas accessibles")
        print("   Vérifiez que tous les conteneurs sont démarrés: docker-compose ps")
        return 1

if __name__ == '__main__':
    sys.exit(main())

