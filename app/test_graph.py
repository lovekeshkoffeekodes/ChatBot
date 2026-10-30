from graphs import app_graph
from langchain_core.messages import HumanMessage

def test_tools():
    print("=== Testing Search Tool (Tavily) ===")
    # Query that requires real-time/web information
    search_query = HumanMessage(content="What is the latest news about NASA's Mars rover in 2026?")
    
    for event in app_graph.stream({"messages": [search_query]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)
    
    print("\n" + "="*40 + "\n") 

    print("=== Testing RAG Tool ===")
    # Query that targets your local PDF document concepts
    rag_query = HumanMessage(content="Explain the core concepts from the uploaded PDF document.")
    
    for event in app_graph.stream({"messages": [rag_query]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)

if __name__ == "__main__":
    test_tools()