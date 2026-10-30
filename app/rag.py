import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
load_dotenv()


#-----------------------------------------------
# Embedding model (loaded once — expensive to reload)
#-----------------------------------------------
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


#-----------------------------------------------
# Global retriever — starts as None
# Gets updated every time a new PDF is uploaded
#-----------------------------------------------
retriver = None

def get_retriever():
    global retriver
    if retriver is None:
        db_url = os.getenv("DATABASE_URL")
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name="pdf_embeddings",
            connection=db_url,
            use_jsonb=True,
        )
        retriver = vector_store.as_retriever(
            search_type='similarity',
            search_kwargs={'k': 4}
        )
    return retriver

#-----------------------------------------------
# process_pdf — called by /upload-pdf endpoint
#-----------------------------------------------
def process_pdf(pdf_path: str,filename: str):
    print("Welcome to RAG")
    global retriver
    db_url = os.getenv("DATABASE_URL")

    # Step 1: Load PDF
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    # Step 2: Split into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    for chunk in chunks:
        chunk.metadata["filename"] = filename
        chunk.metadata["source"] = filename

    # Step 3: Delete old embeddings, store new ones
    vector_store = PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        connection=db_url,
        collection_name="pdf_embeddings",
        # pre_delete_collection=True,   # ← deletes old PDF data before inserting new
    )
    
    # Step 4: Update global retriever
    retriver = vector_store.as_retriever(
        search_type='similarity',
        search_kwargs={'k': 2}
    )