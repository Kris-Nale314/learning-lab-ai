"""
Extractor Agent - Extracts evidence from document chunks for framework criteria

This agent analyzes document chunks to extract evidence relevant to framework criteria,
focusing on gathering relevant text without scoring or consolidation.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class ExtractorAgent(BaseAgent):
    """
    Extracts evidence from document chunks for framework assessment.
    
    The Extractor is responsible for:
    1. Analyzing document chunks
    2. Identifying evidence relevant to framework criteria
    3. Recording evidence with source tracking
    4. Applying different extraction strategies based on configuration
    """
    
    def __init__(
        self,
        llm,
        context: AssessmentContext,
        name: str = "Extractor",
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Extractor agent.
        
        Args:
            llm: Language model instance
            context: Assessment context
            name: Agent name
            options: Configuration options including extraction strategy
        """
        super().__init__(name, "extractor", llm, context, options or {})
        
        # Get extraction configuration from options
        self.extraction_type = options.get("extraction_type", "direct")
        self.batch_size = options.get("batch_size", 1)
        self.min_confidence = options.get("min_confidence", 0.7)
        self.custom_instructions = options.get("instructions", "")
        
        self.logger.info(f"{name} initialized with extraction_type={self.extraction_type}, batch_size={self.batch_size}")
        
    async def process(self, chunks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process document chunks to extract evidence.
        
        Args:
            chunks: Optional list of document chunks (uses context chunks if None)
            
        Returns:
            Extraction results
        """
        self.logger.info("Starting evidence extraction")
        self.start_timer()
        
        try:
            # Use provided chunks or get from context
            chunks_to_process = chunks or self.context.get_chunks()
            
            if not chunks_to_process:
                raise ValueError("No document chunks available for extraction")
                
            self.logger.info(f"Processing {len(chunks_to_process)} chunks for evidence extraction")
            
            # Get framework dimensions and criteria
            framework = self.context.framework
            dimensions = framework.get("dimensions", [])
            
            # Process chunks based on extraction strategy
            if self.extraction_type == "batch":
                extraction_results = await self._process_chunks_in_batches(chunks_to_process, dimensions)
            else:  # Default to direct extraction
                extraction_results = await self._process_chunks_individually(chunks_to_process, dimensions)
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Evidence extraction completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("extraction_completed", {
                "chunks_processed": len(chunks_to_process),
                "evidence_extracted": extraction_results.get("total_evidence", 0),
                "time_taken": elapsed_time
            })
            
            return extraction_results
            
        except Exception as e:
            self.stop_timer()
            self.logger.error(f"Error during evidence extraction: {str(e)}", exc_info=True)
            self.add_warning(f"Failed to extract evidence: {str(e)}")
            raise
    
    async def _process_chunks_individually(
        self, 
        chunks: List[Dict[str, Any]], 
        dimensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process each chunk individually for all criteria.
        
        Args:
            chunks: List of document chunks
            dimensions: Framework dimensions with criteria
            
        Returns:
            Extraction results
        """
        results = {
            "by_chunk": {},
            "by_criterion": {},
            "total_evidence": 0
        }
        
        # Process each chunk
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk_id = chunk.get("chunk_id")
            chunk_text = chunk.get("text", "")
            
            if not chunk_id or not chunk_text:
                self.logger.warning(f"Skipping invalid chunk at index {i}")
                continue
                
            # Update progress
            progress = (i + 1) / total_chunks
            self.update_progress(progress, f"Processing chunk {i+1}/{total_chunks}")
            
            # Extract evidence for all criteria in this chunk
            chunk_results = await self._extract_evidence_for_chunk(chunk, dimensions)
            
            # Record results
            results["by_chunk"][chunk_id] = chunk_results
            results["total_evidence"] += chunk_results.get("evidence_count", 0)
            
            # Update criterion-indexed results
            for evidence in chunk_results.get("evidence", []):
                dimension_id = evidence.get("dimension_id")
                criterion_id = evidence.get("criterion_id")
                
                if dimension_id and criterion_id:
                    key = f"{dimension_id}:{criterion_id}"
                    if key not in results["by_criterion"]:
                        results["by_criterion"][key] = []
                    results["by_criterion"][key].append(evidence)
        
        return results
    
    async def _process_chunks_in_batches(
        self, 
        chunks: List[Dict[str, Any]], 
        dimensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process chunks in batches for efficiency.
        
        Args:
            chunks: List of document chunks
            dimensions: Framework dimensions with criteria
            
        Returns:
            Extraction results
        """
        results = {
            "by_chunk": {},
            "by_criterion": {},
            "total_evidence": 0
        }
        
        # Create batches
        batch_size = max(1, self.batch_size)
        batches = [chunks[i:i+batch_size] for i in range(0, len(chunks), batch_size)]
        
        # Process each batch
        total_batches = len(batches)
        for i, batch in enumerate(batches):
            # Update progress
            progress = (i + 1) / total_batches
            self.update_progress(progress, f"Processing batch {i+1}/{total_batches}")
            
            # Extract evidence for all criteria in this batch
            batch_results = await self._extract_evidence_for_batch(batch, dimensions)
            
            # Record results
            for chunk_id, chunk_results in batch_results.get("by_chunk", {}).items():
                results["by_chunk"][chunk_id] = chunk_results
                results["total_evidence"] += chunk_results.get("evidence_count", 0)
            
            # Update criterion-indexed results
            for key, evidence_list in batch_results.get("by_criterion", {}).items():
                if key not in results["by_criterion"]:
                    results["by_criterion"][key] = []
                results["by_criterion"][key].extend(evidence_list)
        
        return results
    
    async def _extract_evidence_for_chunk(
        self, 
        chunk: Dict[str, Any], 
        dimensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract evidence for all criteria from a single chunk.
        
        Args:
            chunk: Document chunk
            dimensions: Framework dimensions with criteria
            
        Returns:
            Chunk extraction results
        """
        chunk_id = chunk.get("chunk_id")
        chunk_text = chunk.get("text", "")
        
        # Prepare system and human prompts
        system_prompt = """You are an expert evidence extractor. Your task is to analyze document text and identify evidence relevant to specific criteria. For each criterion, extract text passages that provide direct evidence or insights. Only extract evidence if it is truly relevant."""
        
        # Add custom instructions if provided
        if self.custom_instructions:
            system_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{self.custom_instructions}"
        
        # Format criteria for the prompt
        criteria_text = ""
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            dimension_desc = dimension.get("description", "")
            
            if not dimension_id:
                continue
                
            criteria_text += f"\n## {dimension_name} (ID: {dimension_id})\n"
            if dimension_desc:
                criteria_text += f"Description: {dimension_desc}\n"
            
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                criterion_question = criterion.get("question", "")
                
                if not criterion_id:
                    continue
                    
                criteria_text += f"- {criterion_name} (ID: {criterion_id}): {criterion_question}\n"
        
        human_prompt = f"""Extract evidence from the following document chunk relevant to the criteria listed below.

DOCUMENT CHUNK (ID: {chunk_id}):
{chunk_text}

CRITERIA TO EXTRACT EVIDENCE FOR:
{criteria_text}

For each criterion where you find relevant evidence, provide:
1. The dimension ID
2. The criterion ID
3. The extracted text passage (direct quote from the document)
4. A brief explanation of why this text is relevant to the criterion
5. A confidence score (0.0-1.0) indicating how strongly this evidence relates to the criterion

Only include criteria where you find relevant evidence. If a criterion has no relevant evidence in this chunk, omit it.

Format your response as a structured JSON list of evidence items."""
        
        # Define the evidence output schema
        evidence_schema = {
            "type": "object",
            "properties": {
                "evidence": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "dimension_id": {"type": "string"},
                            "criterion_id": {"type": "string"},
                            "text": {"type": "string"},
                            "relevance": {"type": "string"},
                            "confidence": {"type": "number"}
                        },
                        "required": ["dimension_id", "criterion_id", "text"]
                    }
                }
            },
            "required": ["evidence"]
        }
        
        # Call LLM for extraction
        extracted_evidence, _ = await self._safe_llm_call(
            "generate_structured_output",
            prompt=human_prompt,
            output_schema=evidence_schema,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=1500
        )
        
        # Process and record evidence
        evidence_list = []
        if isinstance(extracted_evidence, dict) and "evidence" in extracted_evidence:
            evidence_list = extracted_evidence["evidence"]
        recorded_evidence = []
        
        for evidence_item in evidence_list:
            dimension_id = evidence_item.get("dimension_id")
            criterion_id = evidence_item.get("criterion_id")
            text = evidence_item.get("text", "").strip()
            relevance = evidence_item.get("relevance", "")
            confidence = evidence_item.get("confidence", 0.8)  # Default if not provided
            
            if not dimension_id or not criterion_id or not text:
                self.logger.warning(f"Skipping invalid evidence item: {evidence_item}")
                continue
                
            # Skip low-confidence evidence if threshold is set
            if confidence < self.min_confidence:
                self.logger.debug(f"Skipping low-confidence evidence ({confidence}) for {dimension_id}:{criterion_id}")
                continue
                
            # Add evidence to context
            metadata = {
                "extraction_type": self.extraction_type,
                "relevance": relevance,
                "confidence": confidence
            }
            
            # Find location in chunk if possible
            location = None
            text_start = chunk_text.find(text)
            if text_start >= 0:
                chunk_start = chunk.get("span", {}).get("start", 0) if "span" in chunk else 0
                absolute_start = chunk_start + text_start
                absolute_end = absolute_start + len(text)
                location = {
                    "start": absolute_start,
                    "end": absolute_end,
                    "relative_start": text_start,
                    "relative_end": text_start + len(text)
                }
            
            evidence_id = self.add_evidence(
                dimension_id=dimension_id,
                criterion_id=criterion_id,
                text=text,
                chunk_id=chunk_id,
                location=location,
                metadata=metadata
            )
            
            # Add to results
            recorded_evidence.append({
                "evidence_id": evidence_id,
                "dimension_id": dimension_id,
                "criterion_id": criterion_id,
                "text": text,
                "relevance": relevance,
                "confidence": confidence
            })
        
        return {
            "evidence": recorded_evidence,
            "evidence_count": len(recorded_evidence),
            "chunk_id": chunk_id
        }
    
    async def _extract_evidence_for_batch(
        self, 
        chunks: List[Dict[str, Any]], 
        dimensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract evidence from a batch of chunks.
        
        Args:
            chunks: Batch of document chunks
            dimensions: Framework dimensions with criteria
            
        Returns:
            Batch extraction results
        """
        # For MVP, we'll just call individual processing for each chunk
        # A more sophisticated batch processing approach could be implemented later
        
        results = {
            "by_chunk": {},
            "by_criterion": {}
        }
        
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            
            if not chunk_id:
                continue
                
            # Process chunk individually
            chunk_results = await self._extract_evidence_for_chunk(chunk, dimensions)
            
            # Record chunk results
            results["by_chunk"][chunk_id] = chunk_results
            
            # Update criterion-indexed results
            for evidence in chunk_results.get("evidence", []):
                dimension_id = evidence.get("dimension_id")
                criterion_id = evidence.get("criterion_id")
                
                if dimension_id and criterion_id:
                    key = f"{dimension_id}:{criterion_id}"
                    if key not in results["by_criterion"]:
                        results["by_criterion"][key] = []
                    results["by_criterion"][key].append(evidence)
        
        return results