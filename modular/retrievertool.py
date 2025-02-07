import os
import json

from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools.retriever import create_retriever_tool
from langchain.retrievers import ParentDocumentRetriever, MultiVectorRetriever
from langchain.storage import LocalFileStore
from langchain.storage._lc_store import create_kv_docstore
from langchain_core.documents import Document

from PyPDF2 import PdfReader, PdfWriter

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

import os
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), ".env")
if not load_dotenv(env_path):
    print(f"Failed to load .env file from {env_path}")
else:
    print(f".env file loaded successfully from {env_path}")

# Retrieve the API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("OPENAI_API_KEY not set in environment variables.")

os.environ["OPENAI_API_KEY"] = api_key  # Ensure it's in os.environ for libraries that require it

# 
# pdoc_filepath: path to json file containing parent documents
# pdf_filepath: path to pdf file
# pdoc_output_dir: path to output directory for parent documents
# page_ranges: list of page ranges for each chapter
# starting_chapter: starting chapter number(1 by default, should be set to 6 if starting from chapter 6)
# file_store_path: path to file store
# vectorstore_path: path to vectorstore
# search_type: search type(similarity is default, refer to this link for more info https://python.langchain.com/docs/how_to/vectorstore_retriever/)
# search_kwargs: search kwargs(3 is sufficient for most use cases, 10 should be used for summarization)
# collection_name: collection name
# 

class retrieverConfig:
    def __init__(
            self, pdoc_filepath, pdf_filepath, pdoc_output_dir,
            page_ranges, starting_chapter, file_store_path, 
            cluster_url, qdrant_key, search_type, search_kwargs,
            collection_name
            
            ):
        self.pdoc_filepath = pdoc_filepath
        self.pdf_filepath = pdf_filepath
        self.pdoc_output_dir = pdoc_output_dir
        self.page_ranges = page_ranges
        self.starting_chapter = starting_chapter
        self.file_store_path = file_store_path
        self.cluster_url = cluster_url
        self.qdrant_key = qdrant_key
        self.search_type = search_type
        self.search_kwargs = search_kwargs
        self.collection_name = collection_name
        
        self.num_chaps = len(page_ranges)

class retriever:
    def __init__(self, config: retrieverConfig):
        self.pdoc_filepath = config.pdoc_filepath
        self.pdf_filepath = config.pdf_filepath
        self.pdoc_output_dir = config.pdoc_output_dir
        self.page_ranges = config.page_ranges
        self.starting_chapter = config.starting_chapter
        self.file_store_path = config.file_store_path
        self.cluster_url = config.cluster_url
        self.qdrant_key = config.qdrant_key
        self.search_type = config.search_type
        self.search_kwargs = config.search_kwargs
        self.collection_name = config.collection_name
        self.num_chaps = config.num_chaps

    # Customized child splitter that adds the chapter number
    class CustomChildSplitter(RecursiveCharacterTextSplitter):
        def split_documents(self, documents):
            child_docs = []
            for doc in documents:
                chunks = self.split_text(doc.page_content)

                chapter_name = doc.metadata["chapter"]
                for chunk in chunks:
                    # print(chunk)
                    child_docs.append(
                        Document(
                            page_content= f"{chapter_name}\n{chunk}",
                            metadata=doc.metadata
                        )
                    )
            return child_docs

        
    class CustomParentSplitter(RecursiveCharacterTextSplitter):
        def split_documents(self, documents):
            parent_docs=[]
            chunk_count = 0
            for doc in documents:
                chunks = self.split_text(doc.page_content)

                for chunk_num, chunk in enumerate(chunks, start=1):
                    doc.metadata["chunk_num"] = chunk_num + chunk_count
                    parent_docs.append(
                        Document(
                            page_content=chunk,
                            metadata=doc.metadata
                        )
                    )
                # print(parent_docs[-1].metadata)
            
                chunk_count += len(chunks)

            return parent_docs

    
    # Splits the PDF into chapters, given a list of page ranges    
    def _split_pdf(self, input_pdf, page_ranges, output_dir):
        reader = PdfReader(input_pdf)

        for idx, (start_page, end_page) in enumerate(page_ranges):
            writer = PdfWriter()
            chapter_num = idx + self.starting_chapter

            for page_num in range(start_page-1, end_page):
                writer.add_page(reader.pages[page_num])

            output_pdf = os.path.join(output_dir, f"chapter{chapter_num}.pdf")

            with open(output_pdf, "wb") as f:
                writer.write(f)
            # print(f"Chapter {chapter_num} saved to {output_pdf}")

    # Load parent documents from a json file
    def _load_parent_docs(self, filepath):
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                print(f"Loading parent documents from {filepath}")
                json_docs = json.load(f)
                return [
                    Document(page_content=doc["page_content"], metadata=doc["metadata"])
                    for doc in json_docs
                ]
        print(f"No parent documents found at {filepath}")
        return None
    
    # Save parent documents into a json file
    def _save_parent_docs(self, parent_docs, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json_docs = [
                {
                    "page_content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in parent_docs
            ]
            json.dump(json_docs, f, ensure_ascii=False, indent=4)
            print(f"Parent documents saved to {filepath}")

    # Gets parent documents
    def get_parent_docs(self):
        # Gets parent documents
        parent_docs = self._load_parent_docs(self.pdoc_filepath)

        # Generates parent documents if they don't exist
        if parent_docs is None:

            print("No parent documents found, generating new ones...")

            self._split_pdf(self.pdf_filepath, self.page_ranges, self.pdoc_output_dir)

            # Creates parent documents with a large and complete context
            parent_docs = []

            last_chap = self.starting_chapter + self.num_chaps

            for i in range(self.starting_chapter,last_chap):
                file_path = f"../data/chapter{i}.pdf"
                loader = PyPDFLoader(file_path)
                full_chapter = loader.load()

                for page_num,document in enumerate(full_chapter,start=1):
                    parent_docs.append(
                        Document(
                            page_content=document.page_content,
                            metadata={"chapter": f"Chapter {i}", "page": page_num}

                        )
                    )

            self._save_parent_docs(parent_docs, self.pdoc_filepath)

            print("Parent documents saved")
            print("Cleaning up chapter pdfs...")

            for i in range(self.starting_chapter,last_chap):
                file_path = f"../data/chapter{i}.pdf"
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Removed {file_path}")

        return parent_docs

    def load_retriever(self):
        print("Loading retriever...")
        fs = LocalFileStore(self.file_store_path)
        store = create_kv_docstore(fs)

        vectorstore = QdrantVectorStore.from_existing_collection(
            embedding=OpenAIEmbeddings(model="text-embedding-3-large"),
            collection_name=self.collection_name,
            url=self.cluster_url,
            api_key=self.qdrant_key,
        )

        retriever = MultiVectorRetriever(
            vectorstore=vectorstore,
            docstore=store,
            search_type=self.search_type,
            search_kwargs=self.search_kwargs,
        )
        
        return retriever

    def generate_retriever(self):
        if os.path.exists(self.file_store_path):
            retriever = self.load_retriever()
            return retriever

        print("Generating retriever...")
        parent_docs = self.get_parent_docs()
                
        # Create child document splitter
        child_splitter = self.CustomChildSplitter(
            chunk_size=300,
        )
            
        # Defines the parent splitter

        parent_splitter = self.CustomParentSplitter(

            chunk_size=2000,
        )

        # Storage layer for the parent documents
        # store = InMemoryStore()
        fs = LocalFileStore(self.file_store_path)
        store = create_kv_docstore(fs)

        # Qdrant vetorstore, persistence testing
        client = QdrantClient(
            url=self.cluster_url,
            api_key=self.qdrant_key,
        )

        if not client.collection_exists(collection_name=self.collection_name):
            print(f"Collection {self.collection_name} does not exist, creating...")

        else:
            print(f"Collection {self.collection_name} exists, reseting and recreating...")

            client.delete_collection(collection_name=self.collection_name)

        client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        )

        child_vectorstore = QdrantVectorStore(
            client=client,
            collection_name=self.collection_name,
            embedding=OpenAIEmbeddings(model="text-embedding-3-large"),
        )

        # Initialize the Parent Document Retriever
        retriever = ParentDocumentRetriever(
            vectorstore=child_vectorstore,
            docstore=store,
            child_splitter=child_splitter,
            parent_splitter=parent_splitter,
            search_type=self.search_type,
            search_kwargs=self.search_kwargs,
        )

        batch_size = 10
        
        with tqdm(
            total=len(parent_docs),
            desc="Adding parent documents to retriever",
            unit="documents",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        ) as pbar:
            for i in range(0, len(parent_docs), batch_size):
                batch = parent_docs[i : i + batch_size]
                retriever.add_documents(batch)

                update_amount = min(batch_size, len(parent_docs)-i)
                pbar.update(update_amount)

        print("Parent Document Retriever initialized")

        return retriever

#
# Retriever Configs
#

ret_path = os.path.abspath("../data/retriever")
ret_path2 = os.path.abspath("../data/chapter6_retriever")

textbook_config = retrieverConfig(
    pdoc_filepath="../data/whole_docs.json",
    pdf_filepath="../data/wholeTextbookPsych.pdf",
    pdoc_output_dir="../data",
    page_ranges=[
        (19,46),(47,82),(83,120),(121,156),
        (157,192),(193,224),(225,258),(259,290),
        (291,332),(333,370),(371,410),(411,458),
        (459,496),(497,548),(549,610),(611,644)
    ],
    starting_chapter=1,
    file_store_path=ret_path,
    cluster_url="https://ca90235f-41e4-480d-8cb8-43246d130bb9.us-west-2-0.aws.cloud.qdrant.io:6333",
    qdrant_key=os.getenv("QDRANT_KEY"),
    search_type="similarity_score_threshold",
    search_kwargs={"k": 10},
    collection_name="textbook_collection"
    )

chapter6_config = retrieverConfig(
    pdoc_filepath="../data/chapter6.json",
    pdf_filepath="../data/wholeTextbookPsych.pdf",
    pdoc_output_dir="../data",
    page_ranges=[
        (193,224)
    ],
    starting_chapter=6,
    file_store_path=ret_path2,
    cluster_url="https://ca90235f-41e4-480d-8cb8-43246d130bb9.us-west-2-0.aws.cloud.qdrant.io:6333",
    qdrant_key=os.getenv("QDRANT_KEY"),
    search_type="similarity",
    search_kwargs={"k": 10},
    collection_name="chapter6_collection"
)

#
# Tool Creation
#

# CODE RUNS TWICE BECAUSE OF IMPORT IN TOOLS.PY.
# TURN GENERATING RETRIEVER INTO A FUNCTION, SO NO ARBITRARY LINES GET EXECUTED

def generate_retriever_tool():
    textbook_retriever = retriever(textbook_config).generate_retriever()
    
    textbook_retriever_tool = create_retriever_tool(
        textbook_retriever,
        "retrieve_textbook_content",
        "Search and return information from the psychology textbook.")
    
    return textbook_retriever_tool







# Idea for TODO:
    # figure out how to connect page numbers and section numbers to the content. 
    # for example, a sourced chunk could look like : <content>:<chapter>:<section>:<page>:<chunk#>
    # this would greatly help in organizing the content and making it easier to retrieve information
    # it has more to do with the generation of the parent documents than the retriever tool itself

# textbook_retriever_tool = create_retriever_tool(
#     textbook_retriever,
#     "retrieve_textbook_content",
#     "Search and return information from the psychology textbook."
# )