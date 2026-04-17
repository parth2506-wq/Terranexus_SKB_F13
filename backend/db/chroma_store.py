import chromadb
from config.settings import Config

class ChromaMemory:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=Config.CHROMA_DB_DIR)
        self.collection = self.client.get_or_create_collection(name="dmrv_reports")

    def save_report(self, report_id, text, metadata):
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[report_id]
        )

    def get_history(self, limit=5):
        return self.collection.peek(limit=limit)