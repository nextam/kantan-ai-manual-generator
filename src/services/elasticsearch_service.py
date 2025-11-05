"""
File: elasticsearch_service.py
Purpose: ElasticSearch integration for RAG semantic search
Main functionality: Index management, vector search, hybrid search with company isolation
Dependencies: elasticsearch, typing
"""

from elasticsearch import Elasticsearch, NotFoundError
from typing import List, Dict, Any, Optional
import os
import json


class ElasticSearchService:
    """
    ElasticSearch service for RAG system
    
    Features:
    - Vector similarity search using dense_vector
    - Hybrid search (vector + BM25 keyword)
    - Company data isolation via company_id filtering
    """
    
    def __init__(self):
        self.es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        self.es_username = os.getenv('ELASTICSEARCH_USERNAME', '')
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD', '')
        
        # Initialize ElasticSearch client
        if self.es_username and self.es_password:
            self.client = Elasticsearch(
                [self.es_url],
                basic_auth=(self.es_username, self.es_password),
                verify_certs=False
            )
        else:
            self.client = Elasticsearch([self.es_url])
        
        self.index_name = 'reference_chunks'
        self.embedding_dimension = 768  # Vertex AI text-embedding-004
    
    def create_index(self) -> bool:
        """
        Create ElasticSearch index for reference chunks
        
        Index structure:
        - chunk_id: Integer (reference_chunks.id)
        - material_id: Integer
        - company_id: Integer (for tenant isolation)
        - chunk_text: Text (analyzed)
        - chunk_index: Integer
        - embedding: Dense vector (768 dimensions)
        - metadata: Object (page number, section, etc.)
        - created_at: Date
        """
        try:
            if self.client.indices.exists(index=self.index_name):
                print(f"Index '{self.index_name}' already exists")
                return True
            
            index_mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "analysis": {
                        "analyzer": {
                            "default": {
                                "type": "standard"
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "integer"},
                        "material_id": {"type": "integer"},
                        "company_id": {"type": "integer"},
                        "chunk_text": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "chunk_index": {"type": "integer"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": self.embedding_dimension,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "metadata": {"type": "object", "enabled": True},
                        "created_at": {"type": "date"}
                    }
                }
            }
            
            self.client.indices.create(index=self.index_name, body=index_mapping)
            print(f"Created index '{self.index_name}'")
            return True
        
        except Exception as e:
            print(f"Failed to create index: {e}")
            return False
    
    def index_chunk(self, chunk_id: int, material_id: int, company_id: int,
                   chunk_text: str, chunk_index: int, embedding: List[float],
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Index a single chunk with its embedding
        
        Args:
            chunk_id: ReferenceChunk.id
            material_id: ReferenceMaterial.id
            company_id: Company.id (for isolation)
            chunk_text: Chunk text content
            chunk_index: Sequential chunk number
            embedding: Vector embedding (768-dim)
            metadata: Additional metadata (page, section, etc.)
        
        Returns:
            ElasticSearch document ID
        """
        try:
            doc = {
                "chunk_id": chunk_id,
                "material_id": material_id,
                "company_id": company_id,
                "chunk_text": chunk_text,
                "chunk_index": chunk_index,
                "embedding": embedding,
                "metadata": metadata or {},
                "created_at": None  # Will be set by ElasticSearch
            }
            
            response = self.client.index(
                index=self.index_name,
                id=f"chunk_{chunk_id}",
                document=doc
            )
            
            return response['_id']
        
        except Exception as e:
            raise Exception(f"Failed to index chunk: {str(e)}")
    
    def vector_search(self, query_embedding: List[float], company_id: int,
                     top_k: int = 10, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search
        
        Args:
            query_embedding: Query vector (768-dim)
            company_id: Company ID for filtering
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)
        
        Returns:
            List of matching chunks with scores
        """
        try:
            query = {
                "knn": {
                    "field": "embedding",
                    "query_vector": query_embedding,
                    "k": top_k,
                    "num_candidates": top_k * 10,
                    "filter": {
                        "term": {"company_id": company_id}
                    }
                },
                "_source": ["chunk_id", "material_id", "chunk_text", "chunk_index", "metadata"]
            }
            
            response = self.client.search(
                index=self.index_name,
                body=query,
                size=top_k
            )
            
            results = []
            for hit in response['hits']['hits']:
                score = hit['_score']
                if score >= min_score:
                    results.append({
                        'chunk_id': hit['_source']['chunk_id'],
                        'material_id': hit['_source']['material_id'],
                        'chunk_text': hit['_source']['chunk_text'],
                        'chunk_index': hit['_source']['chunk_index'],
                        'metadata': hit['_source'].get('metadata', {}),
                        'score': score
                    })
            
            return results
        
        except Exception as e:
            raise Exception(f"Vector search failed: {str(e)}")
    
    def hybrid_search(self, query_text: str, query_embedding: List[float],
                     company_id: int, top_k: int = 10,
                     vector_weight: float = 0.7) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and BM25 keyword search
        
        Args:
            query_text: Query text for keyword search
            query_embedding: Query vector for semantic search
            company_id: Company ID for filtering
            top_k: Number of results to return
            vector_weight: Weight for vector score (0-1), keyword weight = 1 - vector_weight
        
        Returns:
            List of matching chunks with combined scores
        """
        try:
            keyword_weight = 1.0 - vector_weight
            
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"company_id": company_id}}
                        ],
                        "should": [
                            {
                                "multi_match": {
                                    "query": query_text,
                                    "fields": ["chunk_text"],
                                    "type": "best_fields",
                                    "boost": keyword_weight
                                }
                            }
                        ]
                    }
                },
                "knn": {
                    "field": "embedding",
                    "query_vector": query_embedding,
                    "k": top_k,
                    "num_candidates": top_k * 10,
                    "boost": vector_weight
                },
                "_source": ["chunk_id", "material_id", "chunk_text", "chunk_index", "metadata"],
                "size": top_k
            }
            
            response = self.client.search(
                index=self.index_name,
                body=query
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'chunk_id': hit['_source']['chunk_id'],
                    'material_id': hit['_source']['material_id'],
                    'chunk_text': hit['_source']['chunk_text'],
                    'chunk_index': hit['_source']['chunk_index'],
                    'metadata': hit['_source'].get('metadata', {}),
                    'score': hit['_score']
                })
            
            return results
        
        except Exception as e:
            raise Exception(f"Hybrid search failed: {str(e)}")
    
    def delete_material_chunks(self, material_id: int, company_id: int) -> int:
        """
        Delete all chunks for a material
        
        Args:
            material_id: Material ID
            company_id: Company ID (for safety)
        
        Returns:
            Number of deleted documents
        """
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"material_id": material_id}},
                            {"term": {"company_id": company_id}}
                        ]
                    }
                }
            }
            
            response = self.client.delete_by_query(
                index=self.index_name,
                body=query
            )
            
            return response.get('deleted', 0)
        
        except NotFoundError:
            return 0
        except Exception as e:
            raise Exception(f"Failed to delete chunks: {str(e)}")
    
    def get_material_chunk_count(self, material_id: int, company_id: int) -> int:
        """
        Get number of indexed chunks for a material
        
        Args:
            material_id: Material ID
            company_id: Company ID
        
        Returns:
            Number of chunks
        """
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"material_id": material_id}},
                            {"term": {"company_id": company_id}}
                        ]
                    }
                }
            }
            
            response = self.client.count(
                index=self.index_name,
                body=query
            )
            
            return response.get('count', 0)
        
        except Exception as e:
            print(f"Failed to count chunks: {e}")
            return 0
    
    def health_check(self) -> bool:
        """
        Check ElasticSearch connection
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            health = self.client.cluster.health()
            return health['status'] in ['yellow', 'green']
        except Exception as e:
            print(f"ElasticSearch health check failed: {e}")
            return False


elasticsearch_service = ElasticSearchService()
