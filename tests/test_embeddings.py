from app.chatbot.embeddings import embedding_model

embedding = embedding_model.embed_query(
    "Our office is in Delhi."
)

print(type(embedding))
print(len(embedding))
print(embedding[:10])