"""Shared access to the persistent Chroma collection."""
import chromadb

STORE_PATH = "./chroma_store"
COLLECTION = "notes_122"


def get_collection():
    # PersistentClient writes to disk; the default chromadb.Client() would not.
    client = chromadb.PersistentClient(path=STORE_PATH)
    return client.get_or_create_collection(name=COLLECTION)


def get_struggles():
    """Every question the user asks, kept so the study plan can spot patterns."""
    client = chromadb.PersistentClient(path=STORE_PATH)
    return client.get_or_create_collection(name="struggles")
