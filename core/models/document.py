"""
Document - Core document representation for Framework Assessment

This module provides the Document class, which represents a document
to be assessed against a framework, with proper metadata and token estimation.
"""

import os
import re
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple

# Configure logging
logger = logging.getLogger("learning-lab-ai.models.document")

class Document:
    """
    Represents a document for framework assessment with metadata and content processing.
    
    The Document class handles:
    1. Loading and preprocessing document content
    2. Token estimation for LLM planning
    3. Document metadata and statistics
    4. Chunk access and management
    """
    
    def __init__(
        self, 
        text: Optional[str] = None, 
        filename: Optional[str] = None, 
        bytes_data: Optional[bytes] = None,
        document_id: Optional[str] = None
    ):
        """
        Initialize a document from text or bytes.
        
        Args:
            text: Text content of the document (if already decoded)
            filename: Optional filename
            bytes_data: Raw bytes of the document (if not yet decoded)
            document_id: Optional document ID (generated if not provided)
        """
        self.document_id = document_id or f"doc-{uuid.uuid4().hex[:8]}"
        self.filename = filename or f"document-{self.document_id}.txt"
        self.created_at = datetime.now().isoformat()
        self.metadata = {}
        self.chunks = []
        
        # Properties to be calculated
        self.text = ""
        self.character_count = 0
        self.word_count = 0
        self.line_count = 0
        self.estimated_tokens = 0
        
        # Load content from either text or bytes
        if text is not None:
            self._process_text(text)
        elif bytes_data is not None:
            self._load_from_bytes(bytes_data)
        else:
            raise ValueError("Either text or bytes_data must be provided")
        
        logger.info(f"Document initialized: {self.filename} ({self.estimated_tokens} estimated tokens)")
    
    def _process_text(self, text: str) -> None:
        """
        Process text content and compute metadata.
        
        Args:
            text: Document text content
        """
        if not isinstance(text, str):
            raise TypeError(f"Expected string for text, got {type(text)}")
            
        self.text = text
        self.character_count = len(text)
        self.word_count = len(text.split())
        self.line_count = len(text.splitlines())
        
        # Token estimation for LLM processing
        # This is an approximation - about 4 chars per token for English text
        self.estimated_tokens = self.character_count // 4
        
        # Extract metadata based on filename
        if self.filename:
            self._extract_file_metadata()
    
    def _load_from_bytes(self, bytes_data: bytes) -> None:
        """
        Load document from bytes with multiple encoding attempts.
        
        Args:
            bytes_data: Raw document bytes
        """
        if not isinstance(bytes_data, bytes):
            raise TypeError(f"Expected bytes for bytes_data, got {type(bytes_data)}")
            
        # List of encodings to try, in order of preference
        encodings = ["utf-8", "latin-1", "windows-1252", "iso-8859-1", "cp1252", "utf-16"]
        
        # Try each encoding
        successful_decode = False
        decode_errors = []
        
        for encoding in encodings:
            try:
                text = bytes_data.decode(encoding)
                self._process_text(text)
                self.metadata["encoding"] = encoding
                successful_decode = True
                logger.info(f"Successfully decoded file '{self.filename}' using {encoding} encoding")
                break
            except UnicodeDecodeError as e:
                decode_errors.append(f"{encoding}: {str(e)}")
                continue
        
        # If all decodings failed, try with error handling
        if not successful_decode:
            try:
                # Use 'replace' error handler to replace invalid bytes with a replacement character
                text = bytes_data.decode("utf-8", errors="replace")
                self._process_text(text)
                self.metadata["encoding"] = "utf-8-replaced"
                self.metadata["encoding_errors"] = True
                logger.warning(f"Decoded file '{self.filename}' with replacement characters due to encoding issues")
            except Exception as e:
                # Final fallback - if even error handling fails
                error_msg = f"Could not decode file '{self.filename}' with any common encoding"
                logger.error(error_msg)
                raise ValueError(error_msg) from e
    
    def _extract_file_metadata(self) -> None:
        """Extract metadata based on filename."""
        if not self.filename:
            return
            
        self.metadata["extension"] = os.path.splitext(self.filename)[1].lower()
        self.metadata["file_size_bytes"] = len(self.text.encode('utf-8'))
        
        # Try to extract date from filename
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{2}-\d{2}-\d{4})',  # DD-MM-YYYY
            r'(\d{8})'               # YYYYMMDD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, self.filename)
            if match:
                self.metadata["date_in_filename"] = match.group(1)
                break
    
    def set_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Set document chunks after processing.
        
        Args:
            chunks: List of chunk dictionaries
        """
        self.chunks = chunks
        self.metadata["chunk_count"] = len(chunks)
        
        # Calculate total tokens in chunks for verification
        total_chunk_tokens = sum(
            chunk.get("token_estimate", 0) for chunk in chunks
        )
        
        # Log any significant discrepancy between estimated and chunked tokens
        if abs(total_chunk_tokens - self.estimated_tokens) > self.estimated_tokens * 0.2:
            logger.warning(
                f"Significant discrepancy between estimated tokens ({self.estimated_tokens}) "
                f"and total chunk tokens ({total_chunk_tokens})"
            )
        
        self.metadata["total_chunk_tokens"] = total_chunk_tokens
        logger.info(f"Document chunked into {len(chunks)} chunks")
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific chunk by ID.
        
        Args:
            chunk_id: ID of the chunk to retrieve
            
        Returns:
            Chunk dictionary if found, None otherwise
        """
        for chunk in self.chunks:
            if chunk.get("chunk_id") == chunk_id:
                return chunk
        return None
    
    def get_chunk_text(self, chunk_id: str) -> Optional[str]:
        """
        Get text of a specific chunk by ID.
        
        Args:
            chunk_id: ID of the chunk
            
        Returns:
            Text of the chunk if found, None otherwise
        """
        chunk = self.get_chunk(chunk_id)
        return chunk.get("text") if chunk else None
    
    def get_text_at_location(self, start: int, end: int) -> str:
        """
        Get document text from a specific character range.
        
        Args:
            start: Start character position
            end: End character position
            
        Returns:
            Text from the specified range
        """
        return self.text[start:end]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of document properties.
        
        Returns:
            Dictionary of document properties
        """
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "word_count": self.word_count,
            "estimated_tokens": self.estimated_tokens,
            "character_count": self.character_count,
            "line_count": self.line_count,
            "created_at": self.created_at,
            "chunk_count": len(self.chunks),
            **self.metadata
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert document to dictionary representation.
        
        Returns:
            Dictionary representation of the document
        """
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "text": self.text,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "line_count": self.line_count,
            "estimated_tokens": self.estimated_tokens,
            "chunks": self.chunks
        }
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Document':
        """
        Create a Document from a file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Document instance
        """
        filename = os.path.basename(file_path)
        
        try:
            with open(file_path, 'rb') as f:
                bytes_data = f.read()
                
            return cls(filename=filename, bytes_data=bytes_data)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    @classmethod
    def from_text(cls, text: str, filename: Optional[str] = None) -> 'Document':
        """
        Create a Document from text content.
        
        Args:
            text: Document text content
            filename: Optional filename
            
        Returns:
            Document instance
        """
        return cls(text=text, filename=filename)
    
    @classmethod
    def from_uploaded_file(cls, file_obj) -> 'Document':
        """
        Create a Document from a Streamlit uploaded file.
        
        Args:
            file_obj: Streamlit uploaded file object
            
        Returns:
            Document instance
        """
        try:
            filename = getattr(file_obj, "name", None)
            bytes_data = file_obj.read()
            
            return cls(filename=filename, bytes_data=bytes_data)
        except Exception as e:
            logger.error(f"Error processing uploaded file: {e}")
            raise