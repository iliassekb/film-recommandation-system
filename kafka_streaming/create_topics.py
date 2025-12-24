"""
Script utilitaire pour créer les topics Kafka nécessaires
"""
import os
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

def create_topics():
    """Crée les 3 topics Kafka nécessaires pour le projet"""
    # Utiliser variable d'environnement ou localhost par défaut
    kafka_broker = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    admin_client = KafkaAdminClient(
        bootstrap_servers=[kafka_broker],
        client_id='topic_creator'
    )
    
    topics = [
        NewTopic(name='events_views', num_partitions=1, replication_factor=1),
        NewTopic(name='events_clicks', num_partitions=1, replication_factor=1),
        NewTopic(name='events_ratings', num_partitions=1, replication_factor=1)
    ]
    
    try:
        admin_client.create_topics(new_topics=topics, validate_only=False)
        print("✅ Topics créés avec succès:")
        for topic in topics:
            print(f"   - {topic.name}")
    except TopicAlreadyExistsError:
        print("ℹ️  Les topics existent déjà")
    except Exception as e:
        print(f"❌ Erreur lors de la création des topics: {e}")
    finally:
        admin_client.close()

if __name__ == "__main__":
    print("🔧 Création des topics Kafka...")
    create_topics()

