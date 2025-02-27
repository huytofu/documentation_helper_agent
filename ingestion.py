from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from graph.models.embeddings import embeddings

load_dotenv()

urls1 = [
    
]

urls2 = [

]

urls3 = [
    
]

for framework, urls in zip([],[urls1, urls2, urls3]):
    docs = [WebBaseLoader(url).load() for url in urls]
    docs_list = [item for sublist in docs for item in sublist]

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=600, chunk_overlap=50
    )
    doc_splits = text_splitter.split_documents(docs_list)

    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="f{framework}",
        embedding=embeddings,
        persist_directory="./.chroma",
    )