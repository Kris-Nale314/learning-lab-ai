"""
Chunker - Simple document chunking strategies for assessment

This module provides the Chunker class, which implements simple strategies
for splitting documents into large chunks for framework assessment.
"""

import re
import uuid
import math
from typing import Dict, Any, List, Optional, Tuple

class Chunker:
    """
    Implements simple document chunking strategies for assessment.
    
    This chunker divides documents into a small number of large chunks
    for processing by framework assessment agents.
    """
    
    def __init__(self, document_text: str):
        """
        Initialize the chunker.
        
        Args:
            document_text: Full document text to chunk
        """
        self.document_text = document_text
        self.document_length = len(document_text)
        
        # Estimate token count (rough approximation)
        self.estimated_tokens = self.document_length // 4
    
    def chunk_by_fixed_size(
        self, 
        chunk_size: int = 8000, 
        overlap: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Split document into fixed-size chunks with minimal overlap.
        
        Args:
            chunk_size: Character size of each chunk
            overlap: Character overlap between chunks
            
        Returns:
            List of document chunks
        """
        chunks = []
        text = self.document_text
        text_length = len(text)
        
        # Calculate effective step size
        step_size = max(100, chunk_size - overlap)
        
        # Create chunks
        for i in range(0, text_length, step_size):
            # Adjust end position
            end_pos = min(i + chunk_size, text_length)
            
            # Create chunk ID
            chunk_id = f"chunk-{uuid.uuid4().hex[:8]}"
            
            # Extract chunk text
            chunk_text = text[i:end_pos]
            
            # Add chunk
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "span": {"start": i, "end": end_pos},
                "chunk_type": "fixed_size",
                "token_estimate": len(chunk_text) // 4
            })
            
            # Stop if we've processed the whole document
            if end_pos >= text_length:
                break
        
        return chunks
    
    def chunk_by_max_chunks(
        self, 
        max_chunks: int = 10,
        overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Split document into a specified number of roughly equal-sized chunks.
        
        Args:
            max_chunks: Maximum number of chunks to create
            overlap: Character overlap between chunks
            
        Returns:
            List of document chunks
        """
        text = self.document_text
        text_length = len(text)
        
        # Calculate chunk size based on max_chunks
        chunk_size = math.ceil(text_length / max_chunks) + overlap
        
        # Create chunks
        return self.chunk_by_fixed_size(chunk_size, overlap)
    
    def chunk_by_target_tokens(
        self, 
        target_tokens_per_chunk: int = 8000,
        overlap_tokens: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Split document into chunks with a target token count per chunk.
        
        Args:
            target_tokens_per_chunk: Target number of tokens per chunk
            overlap_tokens: Token overlap between chunks
            
        Returns:
            List of document chunks
        """
        # Convert tokens to characters (approximate)
        chars_per_token = 4
        target_chars = target_tokens_per_chunk * chars_per_token
        overlap_chars = overlap_tokens * chars_per_token
        
        # Create chunks
        return self.chunk_by_fixed_size(target_chars, overlap_chars)
    
    def chunk_by_paragraphs(
        self, 
        paragraphs_per_chunk: int = 50,
        overlap_paragraphs: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Split document by paragraphs, with a specified number of paragraphs per chunk.
        
        Args:
            paragraphs_per_chunk: Number of paragraphs per chunk
            overlap_paragraphs: Number of paragraphs to overlap between chunks
            
        Returns:
            List of document chunks
        """
        chunks = []
        text = self.document_text
        
        # Split into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        total_paragraphs = len(paragraphs)
        
        # Calculate effective step size
        step_size = max(1, paragraphs_per_chunk - overlap_paragraphs)
        
        # Create chunks
        for i in range(0, total_paragraphs, step_size):
            # Calculate end index
            end_idx = min(i + paragraphs_per_chunk, total_paragraphs)
            
            # Create chunk ID
            chunk_id = f"chunk-{uuid.uuid4().hex[:8]}"
            
            # Join paragraphs for this chunk
            chunk_paragraphs = paragraphs[i:end_idx]
            chunk_text = '\n\n'.join(chunk_paragraphs)
            
            # Calculate span (approximate for paragraph-based chunking)
            start_pos = 0
            if i > 0:
                start_pos = len('\n\n'.join(paragraphs[:i])) + 2
                
            end_pos = start_pos + len(chunk_text)
            
            # Add chunk
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "span": {"start": start_pos, "end": end_pos},
                "chunk_type": "paragraph",
                "paragraph_count": len(chunk_paragraphs),
                "token_estimate": len(chunk_text) // 4
            })
            
            # Stop if we've processed the whole document
            if end_idx >= total_paragraphs:
                break
        
        return chunks
    
    def chunk_for_assessment(
        self, 
        method: str = "auto",
        target_chunks: int = None,
        max_tokens_per_chunk: int = 8000
    ) -> List[Dict[str, Any]]:
        """
        Chunk the document specifically for framework assessment.
        
        This is the main method to use for framework assessment chunking.
        
        Args:
            method: Chunking method ("auto", "fixed", "paragraphs", "max_chunks")
            target_chunks: Target number of chunks (for "auto" and "max_chunks")
            max_tokens_per_chunk: Maximum tokens per chunk (for "fixed")
            
        Returns:
            List of document chunks
        """
        # If no target chunks specified, calculate based on document size
        if target_chunks is None:
            # Aim for chunks of about 8000 tokens each
            target_chunks = max(1, self.estimated_tokens // 8000)
            # Limit to a reasonable number
            target_chunks = min(20, target_chunks)
        
        if method == "fixed":
            # Fixed token size chunking
            return self.chunk_by_target_tokens(max_tokens_per_chunk, 200)
        
        elif method == "paragraphs":
            # Estimate paragraphs per chunk
            paragraphs = re.split(r'\n\s*\n', self.document_text)
            total_paragraphs = len(paragraphs)
            paragraphs_per_chunk = max(1, total_paragraphs // target_chunks)
            return self.chunk_by_paragraphs(paragraphs_per_chunk, 2)
        
        elif method == "max_chunks":
            # Fixed number of chunks
            return self.chunk_by_max_chunks(target_chunks, 200)
        
        else:  # "auto" or any other value
            # Auto-detect best method
            # For short documents, just use a single chunk
            if self.estimated_tokens < 10000:
                return [{
                    "chunk_id": f"chunk-{uuid.uuid4().hex[:8]}",
                    "text": self.document_text,
                    "span": {"start": 0, "end": self.document_length},
                    "chunk_type": "full_document",
                    "token_estimate": self.estimated_tokens
                }]
            
            # For structured documents (with many paragraph breaks), use paragraph chunking
            paragraphs = re.split(r'\n\s*\n', self.document_text)
            if len(paragraphs) > 20:
                paragraphs_per_chunk = max(1, len(paragraphs) // target_chunks)
                return self.chunk_by_paragraphs(paragraphs_per_chunk, 2)
            
            # Default to max_chunks approach
            return self.chunk_by_max_chunks(target_chunks, 200)