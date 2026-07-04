from app.chatbot.retriever import retriever

query = "What services does WebKey India provide?"

documents = retriever.invoke(query)

print(f"Found {len(documents)} documents.\n")

for i, doc in enumerate(documents, start=1):
    print("=" * 80)
    print(f"DOCUMENT {i}")
    print("=" * 80)

    print("\nMetadata:")
    print(doc.metadata)

    print("\nContent:")
    print(doc.page_content[:500])   # Print first 500 characters

    print("\n")