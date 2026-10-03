# Hybrid Retrieval Specification — Threshold AI Governance

## 1. Dual Search Paradigm
To achieve high precision on exact policy terms, acronyms, and codes while preserving semantic understanding of user intent, Threshold executes **Hybrid Retrieval**:

1. **Dense Semantic Search:**
   - Provider: ChromaDB local vector store.
   - Embeddings: Standardized `EmbeddingEngine` (768-dimensional normalized vectors).
   - Distance Metric: Cosine similarity (`1 - cosine_distance`).

2. **Sparse Lexical Search:**
   - Engine: Pure Python BM25 implementation (`KeywordSearchEngine`).
   - Tokenization: Alphanumeric extraction with standard stop-word pruning.
   - Ranking: BM25 score based on inverse document frequency (IDF) and term frequency (TF).

## 2. Reciprocal Rank Fusion (RRF)
The candidate lists from semantic and lexical searches are merged using Reciprocal Rank Fusion:

$$RRF(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$

Where:
- $M = \{\text{semantic}, \text{keyword}\}$
- $k = 60$ (smoothing parameter)
- $r_m(d)$ is the 1-based ranking of chunk $d$ in system $m$.

## 3. Pre-Context Governance Filtering
Before fused results are passed to prompt assembly, every candidate chunk is evaluated against the caller's `AccessContext`:
- **Clearance Level Hierarchy:** `RESTRICTED` (3) > `CONFIDENTIAL` (2) > `INTERNAL` (1) > `PUBLIC` (0).
- If `chunk.clearance > user.clearance`: **DENY** chunk.
- If `chunk.allowed_roles` does not contain `user.role` (and is not `*`): **DENY** chunk.
- If `chunk.department != user.department` and clearance is `CONFIDENTIAL` or higher: **DENY** chunk.
Denied chunks are silently dropped from the candidate list and logged in the retrieval telemetry metrics.
