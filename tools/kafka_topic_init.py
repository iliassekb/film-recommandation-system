#!/usr/bin/env python3
"""
Kafka Topic Initialization
Creates required Kafka topics for streaming pipeline.
No shell scripts - pure Python using kafka-python.
"""

import os
import sys
import time
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError


def create_topics():
    """Create Kafka topics for streaming events"""
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
    
    print(f"[INFO] Connecting to Kafka at {bootstrap_servers}")
    
    # Wait for Kafka to be ready
    max_retries = 30
    retry_count = 0
    admin_client = None
    
    while retry_count < max_retries:
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                client_id='topic-init'
            )
            # Test connection
            admin_client.list_topics()
            print(f"[INFO] Connected to Kafka successfully")
            break
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(f"[ERROR] Failed to connect to Kafka after {max_retries} retries: {e}")
                sys.exit(1)
            print(f"[INFO] Waiting for Kafka... (attempt {retry_count}/{max_retries})")
            time.sleep(2)
    
    # Define topics
    topics = [
        NewTopic(
            name='events_views',
            num_partitions=3,
            replication_factor=1,
            topic_configs={
                'retention.ms': '604800000',  # 7 days
                'cleanup.policy': 'delete'
            }
        ),
        NewTopic(
            name='events_clicks',
            num_partitions=3,
            replication_factor=1,
            topic_configs={
                'retention.ms': '604800000',  # 7 days
                'cleanup.policy': 'delete'
            }
        ),
        NewTopic(
            name='events_ratings',
            num_partitions=3,
            replication_factor=1,
            topic_configs={
                'retention.ms': '2592000000',  # 30 days (ratings are more valuable)
                'cleanup.policy': 'delete'
            }
        ),
    ]
    
    print(f"[INFO] Creating {len(topics)} topics...")
    
    created_count = 0
    existing_count = 0
    
    for topic in topics:
        try:
            admin_client.create_topics([topic])
            print(f"[SUCCESS] Created topic: {topic.name}")
            created_count += 1
        except TopicAlreadyExistsError:
            print(f"[INFO] Topic already exists: {topic.name}")
            existing_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to create topic {topic.name}: {e}")
            # Continue with other topics
    
    admin_client.close()
    
    print(f"[SUMMARY] Created: {created_count}, Already existed: {existing_count}")
    
    if created_count > 0 or existing_count == len(topics):
        print("[SUCCESS] All topics are ready")
        sys.exit(0)
    else:
        print("[ERROR] Some topics failed to create")
        sys.exit(1)


if __name__ == '__main__':
    create_topics()




