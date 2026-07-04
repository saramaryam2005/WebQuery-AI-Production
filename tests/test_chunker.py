from app.chatbot.chunker import create_chunks

text = """
Our office is in Delhi.

We provide SEO services.

Pricing starts at ₹5000.
""" * 100

chunks = create_chunks(text)

print(f"Total Chunks: {len(chunks)}")
print()
print(chunks[0][:300])