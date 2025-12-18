"""
Script de test pour l'endpoint de recommandations.
À exécuter après avoir démarré l'API.
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_recommendations(user_id: int = 1, limit: int = 10):
    """Test l'endpoint de recommandations."""
    url = f"{API_BASE_URL}/api/v1/recommendations/{user_id}"
    params = {"limit": limit}
    
    print(f"Testing recommendations for user {user_id}...")
    print(f"URL: {url}")
    print(f"Params: {params}")
    print()
    
    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"User ID: {data['user_id']}")
            print(f"Count: {data['count']}")
            print(f"\nRecommendations:")
            for i, rec in enumerate(data['recommendations'][:5], 1):
                print(f"  {i}. {rec.get('title', 'Unknown')} (ID: {rec['movie_id']})")
                print(f"     Score: {rec['score']:.4f}, Rank: {rec['rank']}")
                print(f"     Genres: {', '.join(rec.get('genres', []))}")
                print()
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Make sure the API is running on http://localhost:8000")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    test_recommendations(user_id, limit)


