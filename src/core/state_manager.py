import os
import json
import datetime
from core.campaign import get_campaign_root, get_current_session_dir

from core.database import get_db_connection

# Suppress harmless ONNX C++ warnings for Apple Silicon (and avoid tokenizer parallelism warnings)
os.environ["ONNXRUNTIME_LOG_LEVEL"] = "3"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import chromadb

# --- Vector & State Logic ---

def get_chroma_client():
    """Returns a client for the local ChromaDB associated with this campaign."""
    root = get_campaign_root()
    db_path = os.path.join(root, "chroma_db")
    return chromadb.PersistentClient(path=db_path)

def get_chat_collection():
    """Returns the main chat sequence collection."""
    client = get_chroma_client()
    # We use a simple generic embedding for local test, or let Chroma use its default all-MiniLM-L6-v2
    return client.get_or_create_collection(name="chat_history")

def get_session_summary_collection():
    """Returns the collection dedicated to session summaries."""
    client = get_chroma_client()
    return client.get_or_create_collection(name="session_summaries")

def search_archived_summaries(query: str) -> str:
    """
    Scans past session summaries using Semantic Search.
    """
    collection = get_session_summary_collection()
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=3
        )
        
        if not results['documents'] or not results['documents'][0]:
            return f"No mentions of '{query}' found in past session summaries."
            
        output = ["Found semantically relevant past summaries:\n"]
        for idx, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][idx]
            session_name = meta.get("session_name", "Unknown Session")
            output.append(f"- **{session_name}**: ...{doc}...")
            
        return "\n".join(output)
        
    except Exception as e:
         return f"Error querying vector database: {e}"

def read_archived_history(session_name: str) -> str:
    """
    Reads the full chat history or full archive log for a specific session.
    Prioritizes text logs if available for readability.
    """
    root = get_campaign_root()
    target_dir = os.path.join(root, session_name)
    
    if not os.path.exists(target_dir):
        return f"Error: Session folder '{session_name}' not found."
        
    # Priority 1: Full Text Archive (Human readable)
    archive_log = os.path.join(target_dir, "session_log_full_archive.md")
    if os.path.exists(archive_log):
        with open(archive_log, "r") as f:
             return f"### Archive of {session_name}\n" + f.read()[:10000] # Cap size safely
             
    # Priority 2: Current Log (if it's the active session or just summary)
    current_log = os.path.join(target_dir, "session_log.md")
    if os.path.exists(current_log):
         with open(current_log, "r") as f:
             return f"### Log of {session_name}\n" + f.read()
             
    return f"No logs found for {session_name}."

# --- Active Window Logic (Still File Based For Rapid Paging / API Structure) ---
# Note: In-memory arrays required by the LLM API are best preserved as flat JSON 
# strictly for the active rolling window, flushing to Chroma later.

def get_chat_history_path():
    session_dir = get_current_session_dir()
    return os.path.join(session_dir, "chat_history.json")

def load_chat_snapshot() -> list:
    """Loads the active LLM context array."""
    path = get_chat_history_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def prune_empty_fields(data):
    if isinstance(data, dict):
        return {k: prune_empty_fields(v) for k, v in data.items() if v not in [None, "", [], {}]}
    elif isinstance(data, list):
        return [prune_empty_fields(v) for v in data if v not in [None, "", [], {}]]
    else:
        return data

def save_chat_snapshot(history_data: list):
    """
    Saves context array and simultaneously indexes ONLY new messages into Chroma.
    """
    path = get_chat_history_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    serializable_history = []
    for msg in history_data:
        if isinstance(msg, dict):
            serializable_history.append(msg)
        elif hasattr(msg, "model_dump"):
            serializable_history.append(msg.model_dump(mode='json'))
        elif hasattr(msg, "to_dict"):
            serializable_history.append(msg.to_dict())
        else:
            try:
                serializable_history.append(msg.__dict__)
            except Exception:
                serializable_history.append({"role": "error", "parts": [str(msg)]})

    clean_history = [prune_empty_fields(msg) for msg in serializable_history]
    
    with open(path, "w") as f:
        json.dump(clean_history, f, indent=2)
        
    # Sync with ChromaDB
    try:
        session_name = os.path.basename(get_current_session_dir())
        collection = get_chat_collection()
        
        # In a real heavy app we'd delta check. Here, we can just upsert the last message 
        # or bulk upsert the whole array if using a stable ID.
        # Let's bulk upsert using a hash of the content+timestamp as ID
        import hashlib
        
        ids = []
        docs = []
        metadatas = []
        
        for idx, item in enumerate(clean_history):
            role = item.get("role", "unknown")
            parts = item.get("parts", [])
            content = " ".join([str(p) for p in parts]) if isinstance(parts, list) else str(parts)
            
            if len(content.strip()) < 5:
                continue # Skip trivial empty messages
                
            # Create a stable ID for this exact message in this session
            stable_id = hashlib.md5(f"{session_name}_{idx}_{content[:50]}".encode()).hexdigest()
            
            ids.append(stable_id)
            docs.append(f"{role}: {content}")
            metadatas.append({"session_name": session_name, "role": role})
            
        if ids:
            collection.upsert(
                ids=ids,
                documents=docs,
                metadatas=metadatas
            )
    except Exception as e:
        print(f"DEBUG: Failed to sync with ChromaDB: {e}")

def undo_last_message() -> str:
    """Removes the last (user, assistant) interaction from active history."""
    history = load_chat_snapshot()
    if not history:
        return "History is empty."
        
    last = history.pop()
    removed_text = ""
    if "parts" in last and last["parts"]:
        removed_text = str(last["parts"][0])[:50] + "..."

    if history and history[-1].get("role") == "user":
        history.pop()
        
    save_chat_snapshot(history)
    return removed_text

def log_to_file(file_path: str, content: str):
    """Appends content to a flat log file (Secrets, active session, etc)."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n[{timestamp}] {content}\n"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "a") as f:
        f.write(entry)

def get_hours_since_last_message() -> float:
    path = get_chat_history_path()
    if not os.path.exists(path):
        return 999.0
    mod_time = os.path.getmtime(path)
    current_time = datetime.datetime.now().timestamp()
    return (current_time - mod_time) / 3600.0

# --- SQLite Context Buffer (Replaces context_buffer.json) ---

def append_to_context_buffer(author: str, text: str):
    """Appends a message to the active SQLite context buffer."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO context_buffer (author, content) VALUES (?, ?)", 
            (author, text)
        )

def get_and_clear_context_buffer() -> str:
    """Returns the accumulated SQLite context as a single string and clears it."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT author, content FROM context_buffer ORDER BY id ASC")
        rows = cursor.fetchall()
        
        if not rows:
            return ""
            
        buffer = []
        for row in rows:
            buffer.append(f"{row['author']}: {row['content']}")
            
        conn.execute("DELETE FROM context_buffer")
        
    return "\n".join(buffer)
