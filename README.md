# xivvy [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/themohitnair/xivvy)

An open-source arXiv Semantic Search engine.

## Stack

- FastAPI
- Qdrant
- light-embed (sentence-transformers/all-MiniLM-L12-v2)
- Kaggle API

The project is currently hosted on Google Cloud Compute Engine. The arXiv metadataset is acquired from the Kaggle API, and embedded with light-embed in batches. The vectors are then stored in Qdrant.

Used in [densAIr](https://densair.vercel.app) - [densAIr repository](https://github.com/themohitnair/densair)
