from app.chatbot.rag_chain import ask_question

result = ask_question(
    "What services does WebKey India provide?"
)

print("\nAnswer:\n")
print(result["answer"])

print("\nSources:\n")

for source in result["sources"]:
    print(source)