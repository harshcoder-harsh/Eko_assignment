import os
import requests
from dotenv import load_dotenv
from processing.parser import process_files
from embedding.embedder import embed_chunks
from search.vector_store import add_to_faiss

load_dotenv()

# Create a dummy file in synced_docs
os.makedirs("synced_docs", exist_ok=True)
with open("synced_docs/test_policy.txt", "w") as f:
    f.write("Highwatch AI Refund Policy: We offer a 30-day money back guarantee for all annual subscriptions. Monthly subscriptions are non-refundable after 3 days. Contact support@highwatch.ai for refunds.")

# Mock downloaded files list
mock_files = [{
    "id": "mock_test_123",
    "name": "test_policy.txt",
    "path": "synced_docs/test_policy.txt",
    "mimeType": "text/plain"
}]

def test_pipeline():
    print("Testing RAG pipeline...")
    
    # 1. Process files
    chunks = process_files(mock_files)
    print(f"Generated {len(chunks)} chunks.")
    
    # 2. Embed chunks
    embedded_chunks = embed_chunks(chunks)
    print(f"Embedded {len(embedded_chunks)} chunks.")

    # 3. Add to FAISS
    add_to_faiss(embedded_chunks)
    print("Added to FAISS vector store.")

    # 4. Test Ask API
    if not os.getenv("GROQ_API_KEY"):
        print("GROQ_API_KEY not set. Skipping LLM query test.")
        return
        
    try:
        response = requests.post("http://localhost:8000/ask", json={"query": "What is the refund policy for monthly subscriptions?"})
        if response.status_code == 200:
            data = response.json()
            print("\nLLM Answer:")
            print(data["answer"])
            print("\nSources:")
            print(data["sources"])
        else:
            print(f"Error from /ask: {response.text}")
    except Exception as e:
        print(f"Failed to connect to backend: {e}")

if __name__ == "__main__":
    test_pipeline()
