{
  "pipeline": "naive_rag_llamaindex_deepseek",
  "description": "阶段一基线 RAG pipeline：LlamaIndex + ChromaDB + DashScope embedding + DeepSeek-Chat",
  "config": {
    "chunk_size": 512,
    "overlap": 64,
    "embedding": "dashscope_text-embedding-v3",
    "retriever_top_k": 5,
    "generator": "deepseek-chat",
    "reranking": false,
    "query_rewriting": false
  },
  "judge": "deepseek-chat",
  "n_samples": 30,
  "scores": {
    "DOC-1": {
      "cross_paragraph": {
        "kbc": 0.8296,
        "ra": 0.5,
        "ct": 0.6,
        "ncp": 1.0,
        "ac": 0.875
      },
      "in_scope": {
        "kbc": 0.7778,
        "ra": 1.0,
        "ct": 0.6667,
        "ncp": 1.0,
        "ac": 0.8889
      },
      "out_of_scope": {
        "kbc": 1.0,
        "ra": 1.0,
        "ct": 0.35,
        "ncp": null,
        "ac": 1.0
      }
    },
    "DOC-2": {
      "cross_paragraph": {
        "kbc": 0.8,
        "ra": 0.0,
        "ct": 0.7,
        "ncp": 1.0,
        "ac": 1.0
      },
      "in_scope": {
        "kbc": 0.6944,
        "ra": 0.8333,
        "ct": 0.5667,
        "ncp": 1.0,
        "ac": 1.0
      },
      "out_of_scope": {
        "kbc": 0.5,
        "ra": 0.0,
        "ct": 0.7,
        "ncp": 1.0,
        "ac": 0.5
      }
    },
    "DOC-3": {
      "cross_paragraph": {
        "kbc": 1.0,
        "ra": 0.5,
        "ct": 0.7,
        "ncp": 1.0,
        "ac": 0.75
      },
      "in_scope": {
        "kbc": 0.8333,
        "ra": 1.0,
        "ct": 0.8,
        "ncp": 1.0,
        "ac": 0.9722
      },
      "out_of_scope": {
        "kbc": 0.7857,
        "ra": 0.5,
        "ct": 0.5,
        "ncp": 1.0,
        "ac": 0.625
      }
    }
  },
  "overall": {
    "kbc": 0.7888,
    "ra": 0.7333,
    "ct": 0.6433,
    "ncp": 1.0,
    "ac": 0.8889
  }
}