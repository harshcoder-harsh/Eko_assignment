from sentence_transformers import SentenceTransformer
import numpy as np
import torch
import os

# Fall back to strict 1-thread CPU for Render Free Tier limits
torch.set_num_threads(1)
torch.set_grad_enabled(False) # We are only doing inference, disable gradients completely to save memory

# all-MiniLM-L6-v2 is already very fast, force CPU
model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

def embed_chunks(chunks):
    """
    Takes a list of chunk dictionaries and adds an 'embedding' key to each.
    """
    if not chunks:
        return chunks
        
    texts = [chunk['text'] for chunk in chunks]
    
    try:
        batch_size = int(os.getenv("EMBED_BATCH_SIZE", "8"))
    except Exception:
        batch_size = 8
    batch_size = max(1, min(batch_size, 32))

    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False, normalize_embeddings=True)
    
    try:
        import gc
        gc.collect()
    except Exception:
        pass
    
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        
    return chunks
