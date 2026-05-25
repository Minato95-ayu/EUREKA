import httpx
import asyncio
import json

async def test_phase2():
    client = httpx.AsyncClient(base_url="http://localhost:8000")
    
    # Test 1: Health check
    print("Test 1: Health Check")
    response = await client.get("/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    
    # Test 2: Ask AI
    print("Test 2: Ask AI")
    response = await client.post(
        "/api/ai/ask",
        params={
            "message": "What is the molecular weight of H2O?",
            "experiment_id": "exp_001"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    
    # Test 3: Create experiment
    print("Test 3: Create Experiment")
    response = await client.post(
        "/api/experiments",
        params={
            "name": "Water Analysis",
            "objective": "Understand water properties"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

if __name__ == "__main__":
    asyncio.run(test_phase2())
