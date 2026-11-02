
from utils.rag_helper import retrieve_documents, get_collection

collection = get_collection()

print("Total stored chunks:", collection.count())

query = "What is the purpose of an ALT blood test?"

results = retrieve_documents(query, top_k=3)

print("\nRetrieved documents:")

for index, item in enumerate(results, start=1):
    print(f"\nResult {index}")
    print("Source:", item.get("metadata", {}).get("source"))
    print("Distance:", item.get("distance"))
    print("Content:", item.get("document")[:500])
