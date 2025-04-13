"""
Enhanced Extractor Agent - Specialized extraction for assigned criteria

This agent analyzes document chunks to extract evidence for specific assigned criteria,
designed to work in parallel with other extractors for improved efficiency.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class ExtractorAgent(BaseAgent):
    """
    Extracts evidence for specific assigned criteria from document chunks.
    
    The Extractor is responsible for:
    1. Analyzing document chunks for assigned criteria only
    2. Identifying and recording relevant evidence
    3. Processing chunks in parallel for efficiency
    4. Providing structured evidence summaries
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
            options: Configuration options including extraction strategy and assigned criteria
        """
        super().__init__(name, "extractor", llm, context, options or {})
        
        # Get extraction configuration from options
        self.extraction_type = self.options.get("extraction_type", "direct")
        self.batch_size = self.options.get("batch_size", 1)
        self.min_confidence = self.options.get("min_confidence", 0.7)
        self.custom_instructions = self.options.get("instructions", "")
        
        # Get assigned criteria (specific to this extractor)
        self.criteria_ids = self.options.get("criteria_ids", [])
        self.dimension_ids = self.options.get("dimension_ids", [])
        
        # For parallel processing
        self.max_concurrent = self.options.get("max_concurrent", 3)
        
        self.logger.info(f"{name} initialized with extraction_type={self.extraction_type}, assigned criteria={len(self.criteria_ids)}")
        
    async def process(self, chunks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process document chunks to extract evidence for assigned criteria.
        
        Args:
            chunks: Optional list of document chunks (uses context chunks if None)
            
        Returns:
            Extraction results
        """
        self.logger.info(f"Starting evidence extraction for {len(self.criteria_ids)} assigned criteria")
        self.start_timer()
        
        try:
            # Use provided chunks or get from context
            chunks_to_process = chunks or self.context.get_chunks()
            
            if not chunks_to_process:
                raise ValueError("No document chunks available for extraction")
                
            self.logger.info(f"Processing {len(chunks_to_process)} chunks for evidence extraction")
            
            # Get assigned criteria details
            assigned_criteria = self._get_assigned_criteria()
            
            if not assigned_criteria:
                self.logger.warning(f"No criteria found matching assigned IDs: {self.criteria_ids}")
                return {"by_chunk": {}, "by_criterion": {}, "total_evidence": 0}
            
            # Process chunks in parallel
            extraction_results = await self._process_chunks_in_parallel(chunks_to_process, assigned_criteria)
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Evidence extraction completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("extraction_completed", {
                "chunks_processed": len(chunks_to_process),
                "evidence_extracted": extraction_results.get("total_evidence", 0),
                "criteria_processed": len(assigned_criteria),
                "time_taken": elapsed_time
            })
            
            return extraction_results
            
        except Exception as e:
            self.stop_timer()
            self.logger.error(f"Error during evidence extraction: {str(e)}", exc_info=True)
            self.add_warning(f"Failed to extract evidence: {str(e)}")
            raise
    
    def _get_assigned_criteria(self) -> List[Dict[str, Any]]:
        """
        Get details for the criteria assigned to this extractor.
        
        Returns:
            List of criteria details
        """
        assigned_criteria = []
        framework = self.context.framework
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            # Skip dimensions that aren't assigned to this extractor
            if self.dimension_ids and dimension_id not in self.dimension_ids:
                continue
                
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                
                # Only include criteria assigned to this extractor
                if not self.criteria_ids or criterion_id in self.criteria_ids:
                    assigned_criteria.append({
                        "dimension_id": dimension_id,
                        "dimension_name": dimension_name,
                        "criterion_id": criterion_id,
                        "criterion_name": criterion.get("name", ""),
                        "criterion_question": criterion.get("question", ""),
                        "criterion_data": criterion
                    })
        
        return assigned_criteria
    
    async def _process_chunks_in_parallel(
        self, 
        chunks: List[Dict[str, Any]], 
        assigned_criteria: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process chunks in parallel for improved efficiency.
        
        Args:
            chunks: List of document chunks
            assigned_criteria: List of criteria to extract evidence for
            
        Returns:
            Extraction results
        """
        results = {
            "by_chunk": {},
            "by_criterion": {},
            "total_evidence": 0
        }
        
        # Divide chunks into batches if needed
        chunk_batches = [chunks[i:i+self.batch_size] for i in range(0, len(chunks), self.batch_size)]
        total_batches = len(chunk_batches)
        
        self.logger.info(f"Processing {total_batches} chunk batches with max concurrency {self.max_concurrent}")
        
        # Create processing tasks for each batch
        tasks = []
        for i, batch in enumerate(chunk_batches):
            task = self._process_chunk_batch(batch, assigned_criteria, f"batch_{i}")
            tasks.append(task)
        
        # Process batches with concurrency control
        completed = 0
        for i in range(0, len(tasks), self.max_concurrent):
            batch_tasks = tasks[i:i+self.max_concurrent]
            batch_results = await asyncio.gather(*batch_tasks)
            
            # Update progress
            completed += len(batch_tasks)
            progress = completed / total_batches
            self.update_progress(progress, f"Processed {completed}/{total_batches} batches")
            
            # Aggregate results
            for batch_result in batch_results:
                # Update by_chunk results
                for chunk_id, chunk_data in batch_result.get("by_chunk", {}).items():
                    results["by_chunk"][chunk_id] = chunk_data
                
                # Update by_criterion results
                for criterion_key, evidence_list in batch_result.get("by_criterion", {}).items():
                    if criterion_key not in results["by_criterion"]:
                        results["by_criterion"][criterion_key] = []
                    results["by_criterion"][criterion_key].extend(evidence_list)
                
                # Update total evidence count
                results["total_evidence"] += batch_result.get("total_evidence", 0)
        
        return results
    
    async def _process_chunk_batch(
        self, 
        chunks: List[Dict[str, Any]], 
        assigned_criteria: List[Dict[str, Any]],
        batch_id: str
    ) -> Dict[str, Any]:
        """
        Process a batch of chunks for assigned criteria.
        
        Args:
            chunks: Batch of document chunks
            assigned_criteria: Criteria to extract evidence for
            batch_id: Identifier for this batch
            
        Returns:
            Batch extraction results
        """
        batch_results = {
            "by_chunk": {},
            "by_criterion": {},
            "total_evidence": 0
        }
        
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            
            if not chunk_id:
                continue
                
            # Process chunk for assigned criteria
            chunk_results = await self._extract_evidence_for_chunk(chunk, assigned_criteria)
            
            # Record chunk results
            batch_results["by_chunk"][chunk_id] = chunk_results
            batch_results["total_evidence"] += chunk_results.get("evidence_count", 0)
            
            # Update criterion-indexed results
            for evidence in chunk_results.get("evidence", []):
                dimension_id = evidence.get("dimension_id")
                criterion_id = evidence.get("criterion_id")
                
                if dimension_id and criterion_id:
                    key = f"{dimension_id}:{criterion_id}"
                    if key not in batch_results["by_criterion"]:
                        batch_results["by_criterion"][key] = []
                    batch_results["by_criterion"][key].append(evidence)
        
        self.logger.debug(f"Batch {batch_id} processed: {batch_results['total_evidence']} evidence items found")
        return batch_results
    
    async def _extract_evidence_for_chunk(
        self, 
        chunk: Dict[str, Any], 
        assigned_criteria: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract evidence for assigned criteria from a single chunk.
        
        Args:
            chunk: Document chunk
            assigned_criteria: Criteria to extract evidence for
            
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
        for i, criterion in enumerate(assigned_criteria):
            dimension_id = criterion.get("dimension_id", "")
            dimension_name = criterion.get("dimension_name", "")
            criterion_id = criterion.get("criterion_id", "")
            criterion_name = criterion.get("criterion_name", "")
            criterion_question = criterion.get("criterion_question", "")
            
            criteria_text += f"Criterion {i+1}: {criterion_name} (ID: {criterion_id})\n"
            criteria_text += f"Question: {criterion_question}\n"
            criteria_text += f"Dimension: {dimension_name} (ID: {dimension_id})\n\n"
        
        human_prompt = f"""Extract evidence from the following document chunk relevant to the criteria listed below.

TEXT CHUNK (ID: {chunk_id}):
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
    
    def _format_evidence_summary(
        self, 
        criterion_id: str, 
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Format a summary of evidence for a criterion.
        
        Args:
            criterion_id: ID of the criterion
            evidence_list: List of evidence for the criterion
            
        Returns:
            Evidence summary
        """
        if not evidence_list:
            return {
                "criterion_id": criterion_id,
                "evidence_count": 0,
                "average_confidence": 0.0,
                "evidence_ids": []
            }
        
        # Calculate average confidence
        confidences = [ev.get("confidence", 0.0) for ev in evidence_list]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Collect evidence IDs
        evidence_ids = [ev.get("evidence_id") for ev in evidence_list if "evidence_id" in ev]
        
        # Create summary
        summary = {
            "criterion_id": criterion_id,
            "evidence_count": len(evidence_list),
            "average_confidence": avg_confidence,
            "evidence_ids": evidence_ids
        }
        
        return summary