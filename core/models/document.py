"""
Document - Enhanced document representation for Framework Assessment Workbench

This module provides the Document class, which represents a document to be assessed 
against a framework, with enhanced metadata, property extraction, and document analysis.
"""

import os
import re
import uuid
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set

# Configure logging
logger = logging.getLogger("learning-lab-ai.models.document")

class Document:
    """
    Represents a document for framework assessment with enhanced analysis capabilities.
    
    The Document class handles:
    1. Loading and preprocessing document content
    2. Initial document property analysis (type, entity, bias)
    3. Token estimation for LLM planning
    4. Document metadata and statistics
    5. Chunk access and management
    """
    
    def __init__(
        self, 
        text: Optional[str] = None, 
        filename: Optional[str] = None, 
        bytes_data: Optional[bytes] = None,
        document_id: Optional[str] = None,
        perform_analysis: bool = True
    ):
        """
        Initialize a document from text or bytes.
        
        Args:
            text: Text content of the document (if already decoded)
            filename: Optional filename
            bytes_data: Raw bytes of the document (if not yet decoded)
            document_id: Optional document ID (generated if not provided)
            perform_analysis: Whether to perform initial document analysis
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
        
        # Enhanced document properties (set during analysis)
        self.document_type = "unknown"
        self.document_structure = "unknown"
        self.primary_entity = {"name": "unknown", "type": "unknown"}
        self.document_bias = {"orientation": "neutral", "confidence": 0.0}
        self.keywords = []
        
        # Load content from either text or bytes
        if text is not None:
            self._process_text(text)
        elif bytes_data is not None:
            self._load_from_bytes(bytes_data)
        else:
            raise ValueError("Either text or bytes_data must be provided")
        
        # Perform initial document analysis if requested
        if perform_analysis:
            self.analyze_document_properties()
        
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
        self.estimated_tokens = max(1, self.character_count // 4)
        
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
    
    def analyze_document_properties(self) -> Dict[str, Any]:
        """
        Perform initial analysis to extract key document properties.
        
        This method performs a 'flash' analysis on the first part of the document
        to extract key properties including document type, entity, and bias orientation.
        
        Returns:
            Dictionary of document properties
        """
        # Use the first part of the document for the flash analysis
        preview_length = min(2000, len(self.text))
        preview_text = self.text[:preview_length]
        
        # Identify document type
        self.document_type = self._detect_document_type(preview_text)
        
        # Extract document structure
        self.document_structure = self._detect_document_structure(preview_text)
        
        # Identify primary entity
        self.primary_entity = self._identify_primary_entity(preview_text)
        
        # Detect document bias
        self.document_bias = self._detect_bias_orientation(preview_text)
        
        # Extract keywords
        self.keywords = self._extract_keywords(preview_text)
        
        # Store in metadata
        document_properties = {
            "document_type": self.document_type,
            "document_structure": self.document_structure,
            "primary_entity": self.primary_entity,
            "document_bias": self.document_bias,
            "keywords": self.keywords
        }
        
        self.metadata.update(document_properties)
        logger.info(f"Document analysis completed: type={self.document_type}, entity={self.primary_entity['name']}, bias={self.document_bias['orientation']}")
        
        return document_properties
    
    def _detect_document_type(self, preview_text: str) -> str:
        """
        Detect the document type from text preview.
        
        Args:
            preview_text: Text preview to analyze
            
        Returns:
            Document type string
        """
        # Simple pattern-based detection
        lowercase_text = preview_text.lower()
        
        # Check for earnings call transcript
        if ("earnings call" in lowercase_text or 
            "quarter results" in lowercase_text or
            "financial results" in lowercase_text) and (
            "operator:" in lowercase_text or 
            "presenter:" in lowercase_text or
            "moderator:" in lowercase_text):
            return "earnings_call_transcript"
            
        # Check for financial report
        if ("financial statement" in lowercase_text or
            "balance sheet" in lowercase_text or
            "income statement" in lowercase_text or
            "cash flow" in lowercase_text):
            return "financial_report"
            
        # Check for press release
        if ("press release" in lowercase_text or
            "for immediate release" in lowercase_text or
            "contact:" in lowercase_text and "###" in lowercase_text):
            return "press_release"
            
        # Check for meeting minutes
        if ("minutes of" in lowercase_text or
            "meeting notes" in lowercase_text or
            "attendees:" in lowercase_text or
            "action items:" in lowercase_text):
            return "meeting_minutes"
            
        # Check for legal document
        if ("contract" in lowercase_text or
            "agreement" in lowercase_text or
            "pursuant to" in lowercase_text or
            "hereby" in lowercase_text):
            return "legal_document"
            
        # Check for email or message
        if ("from:" in lowercase_text and "to:" in lowercase_text or
            "subject:" in lowercase_text or
            "sent:" in lowercase_text or
            "cc:" in lowercase_text):
            return "email_message"
        
        # Default to generic document
        return "generic_document"
    
    def _detect_document_structure(self, preview_text: str) -> str:
        """
        Detect the document structure from text preview.
        
        Args:
            preview_text: Text preview to analyze
            
        Returns:
            Document structure description
        """
        # Count paragraphs, bullet points, sections
        paragraphs = re.split(r'\n\s*\n', preview_text)
        bullet_points = len(re.findall(r'^\s*[\*\-•]', preview_text, re.MULTILINE))
        section_headers = len(re.findall(r'^\s*[A-Z][A-Z\s]+:?$', preview_text, re.MULTILINE))
        
        # Check for dialogue structure (common in transcripts)
        speaker_turns = len(re.findall(r'^\s*[A-Za-z\s\.]+:', preview_text, re.MULTILINE))
        
        if speaker_turns > 5:
            return "dialogue_transcript"
        elif section_headers > 3:
            return "sectioned_document"
        elif bullet_points > 5:
            return "bulleted_list_document"
        elif len(paragraphs) > 10:
            return "paragraph_based_document"
        else:
            return "simple_document"
    
    def _identify_primary_entity(self, preview_text: str) -> Dict[str, Any]:
        """
        Identify the primary entity discussed in the document.
        
        Args:
            preview_text: Text preview to analyze
            
        Returns:
            Entity information dictionary
        """
        # Look for company name patterns
        company_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Corp|Ltd|LLC|Company|Technologies|Group)))'
        company_matches = re.findall(company_pattern, preview_text)
        
        # Look for specific mentions of organizations
        org_indicators = [
            "Corporation", "Inc.", "Company", "Ltd.", "LLC", "Group", "Technologies",
            "organization", "enterprise", "institution", "agency", "department"
        ]
        
        # Simple entity extraction
        if company_matches:
            # Count occurrences to find the most common company name
            company_counts = {}
            for company in company_matches:
                company_counts[company] = company_counts.get(company, 0) + 1
                
            most_common = max(company_counts.items(), key=lambda x: x[1])
            return {
                "name": most_common[0],
                "type": "company",
                "confidence": min(0.7, 0.5 + (most_common[1] / 10))  # Scale confidence with frequency
            }
        
        # Look for repeated proper nouns as fallback
        proper_nouns = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', preview_text)
        if proper_nouns:
            # Count occurrences to find the most common proper noun
            noun_counts = {}
            for noun in proper_nouns:
                # Skip very short names and common non-entity terms
                if len(noun) < 3 or noun in ["The", "This", "That", "These", "Those", "I", "We"]:
                    continue
                noun_counts[noun] = noun_counts.get(noun, 0) + 1
                
            if noun_counts:
                most_common = max(noun_counts.items(), key=lambda x: x[1])
                return {
                    "name": most_common[0],
                    "type": "entity",
                    "confidence": min(0.5, 0.3 + (most_common[1] / 20))  # Lower confidence for generic proper nouns
                }
        
        # Default to unknown entity
        return {
            "name": "unknown",
            "type": "unknown",
            "confidence": 0.0
        }
    
    def _detect_bias_orientation(self, preview_text: str) -> Dict[str, Any]:
        """
        Detect the bias orientation of the document.
        
        Args:
            preview_text: Text preview to analyze
            
        Returns:
            Bias orientation information
        """
        # Simple sentiment-based bias detection
        lowercase_text = preview_text.lower()
        
        # Define sentiment word lists
        positive_words = [
            "excellent", "growth", "increase", "profit", "succeed", "success", "improve", 
            "advantage", "strength", "opportunity", "innovation", "progress", "positive",
            "confident", "strong", "robust", "exceeded", "breakthrough", "leading"
        ]
        
        negative_words = [
            "decline", "decrease", "loss", "fail", "issue", "problem", "challenge", "risk",
            "concern", "weakness", "threat", "difficult", "negative", "uncertain", "weak",
            "below", "disappointing", "struggle", "deficit", "burden"
        ]
        
        # Count sentiment words
        positive_count = sum(lowercase_text.count(word) for word in positive_words)
        negative_count = sum(lowercase_text.count(word) for word in negative_words)
        
        # Determine orientation
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return {"orientation": "neutral", "confidence": 0.5}
            
        # Calculate positive/negative ratio
        if positive_count > negative_count * 2:
            return {"orientation": "optimistic", "confidence": min(0.9, 0.5 + (positive_count / total_sentiment_words) * 0.5)}
        elif negative_count > positive_count * 2:
            return {"orientation": "pessimistic", "confidence": min(0.9, 0.5 + (negative_count / total_sentiment_words) * 0.5)}
        else:
            return {"orientation": "neutral", "confidence": 0.5 + abs(positive_count - negative_count) / (2 * total_sentiment_words)}
    
    def _extract_keywords(self, preview_text: str) -> List[str]:
        """
        Extract key terms and concepts from the document.
        
        Args:
            preview_text: Text preview to analyze
            
        Returns:
            List of extracted keywords
        """
        # Basic keyword extraction
        # 1. Get all words and normalize
        words = re.findall(r'\b[A-Za-z][A-Za-z]+\b', preview_text)
        word_counts = {}
        
        # 2. Count word frequencies, excluding stopwords
        stopwords = {
            "the", "and", "to", "of", "a", "in", "that", "is", "for", "on", "with", "as", 
            "at", "by", "this", "from", "or", "an", "be", "are", "was", "were", "have", "has",
            "it", "its", "they", "their", "we", "our", "you", "your", "i", "my", "me"
        }
        
        for word in words:
            word = word.lower()
            if word not in stopwords and len(word) > 3:  # Skip stopwords and very short words
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # 3. Extract top keywords
        if not word_counts:
            return []
            
        # Sort by frequency and get top 10
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:10]]
    
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
            "document_type": self.document_type,
            "primary_entity": self.primary_entity,
            "bias_orientation": self.document_bias.get("orientation", "neutral"),
            "word_count": self.word_count,
            "estimated_tokens": self.estimated_tokens,
            "character_count": self.character_count,
            "line_count": self.line_count,
            "keywords": self.keywords,
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
            "document_type": self.document_type,
            "document_structure": self.document_structure,
            "primary_entity": self.primary_entity,
            "document_bias": self.document_bias,
            "keywords": self.keywords,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "line_count": self.line_count,
            "estimated_tokens": self.estimated_tokens,
            "chunks": self.chunks
        }
    
    @classmethod
    def from_file(cls, file_path: str, perform_analysis: bool = True) -> 'Document':
        """
        Create a Document from a file path.
        
        Args:
            file_path: Path to the file
            perform_analysis: Whether to perform initial document analysis
            
        Returns:
            Document instance
        """
        filename = os.path.basename(file_path)
        
        try:
            with open(file_path, 'rb') as f:
                bytes_data = f.read()
                
            return cls(filename=filename, bytes_data=bytes_data, perform_analysis=perform_analysis)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    @classmethod
    def from_text(cls, text: str, filename: Optional[str] = None, perform_analysis: bool = True) -> 'Document':
        """
        Create a Document from text content.
        
        Args:
            text: Document text content
            filename: Optional filename
            perform_analysis: Whether to perform initial document analysis
            
        Returns:
            Document instance
        """
        return cls(text=text, filename=filename, perform_analysis=perform_analysis)
    
    @classmethod
    def from_uploaded_file(cls, file_obj, perform_analysis: bool = True) -> 'Document':
        """
        Create a Document from a Streamlit uploaded file.
        
        Args:
            file_obj: Streamlit uploaded file object
            perform_analysis: Whether to perform initial document analysis
            
        Returns:
            Document instance
        """
        try:
            filename = getattr(file_obj, "name", None)
            bytes_data = file_obj.read()
            
            return cls(filename=filename, bytes_data=bytes_data, perform_analysis=perform_analysis)
        except Exception as e:
            logger.error(f"Error processing uploaded file: {e}")
            raise