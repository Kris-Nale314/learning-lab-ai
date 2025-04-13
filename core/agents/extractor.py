"""
Enhanced Extractor Agent - Deep evidence extraction with evidence consolidation

This agent thoroughly analyzes document chunks to find ALL evidence relevant to its
assigned criteria, then consolidates and summarizes the evidence for each criterion
into a comprehensive "evidence packet" for the evaluator.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class ExtractorAgent(BaseAgent):
    """
    Extracts and consolidates evidence for assigned criteria across all document chunks.
    
    The Enhanced Extractor is responsible for:
    1. Deep analysis of all document chunks for assigned criteria
    2. Finding all potential evidence, including indirect references
    3. Consolidating evidence for each criterion across all chunks
    4. Creating comprehensive evidence summaries for each criterion
    5. Providing confidence and relevance assessments for the evidence
    6. Processing chunks in parallel for efficiency
    7. Delivering a clean "evidence packet" to the evaluator for each criterion
    """
    
    def __init__(
        self,
        llm,
        context: AssessmentContext,
        name: str = "EnhancedExtractor",
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Enhanced Extractor agent.
        
        Args:
            llm: Language model instance
            context: Assessment context
            name: Agent name
            options: Configuration options including assigned criteria
        """
        super().__init__(name, "extractor", llm, context, options or {})
        
        # Get extraction configuration from options
        self.extraction_type = self.options.get("extraction_type", "direct")
        self.batch_size = self.options.get("batch_size", 1)
        self.min_confidence = self.options.get("min_confidence", 0.6)
        self.custom_instructions = self.options.get("instructions", "")
        
        # Get assigned criteria (specific to this extractor)
        self.criteria_ids = self.options.get("criteria_ids", [])
        self.dimension_ids = self.options.get("dimension_ids", [])
        
        # For parallel processing
        self.max_concurrent = self.options.get("max_concurrent", 3)
        
        self.logger.info(f"{name} initialized for {len(self.criteria_ids)} criteria")
        
    async def process(self, chunks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process document chunks to extract all evidence for assigned criteria,
        then consolidate evidence for each criterion across all chunks.
        
        Args:
            chunks: Optional list of document chunks (uses context chunks if None)
            
        Returns:
            Extraction results with consolidated evidence summaries
        """
        self.logger.info(f"Starting enhanced evidence extraction for {len(self.criteria_ids)} assigned criteria")
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
                return {"by_chunk": {}, "by_criterion": {}, "total_evidence": 0, "consolidated_evidence": {}}
            
            # Process chunks in parallel for assigned criteria
            extraction_results = await self._process_chunks_in_parallel(chunks_to_process, assigned_criteria)
            
            # Consolidate evidence for each criterion
            consolidated_evidence = await self._consolidate_evidence(extraction_results, assigned_criteria)
            extraction_results["consolidated_evidence"] = consolidated_evidence
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Enhanced evidence extraction completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("extraction_completed", {
                "chunks_processed": len(chunks_to_process),
                "evidence_extracted": extraction_results.get("total_evidence", 0),
                "criteria_processed": len(assigned_criteria),
                "time_taken": elapsed_time,
                "consolidated_evidence": consolidated_evidence
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
                        "scoring_method": criterion.get("scoring_method", "scale_1_5"),
                        "scoring_definitions": criterion.get("scoring_definitions", {})
                    })
        
        return assigned_criteria
    
    async def _process_chunks_in_parallel(
        self, 
        chunks: List[Dict[str, Any]], 
        assigned_criteria: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process chunks in parallel for efficiency.
        
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
        Extract all evidence for assigned criteria from a single chunk.
        
        Args:
            chunk: Document chunk
            assigned_criteria: Criteria to extract evidence for
            
        Returns:
            Chunk extraction results
        """
        chunk_id = chunk.get("chunk_id")
        chunk_text = chunk.get("text", "")
        
        # Prepare system and human prompts
        system_prompt = """You are an expert evidence extractor specialized in finding ALL relevant evidence for specific criteria. 
Your job is to thoroughly analyze text and identify any content that could be relevant to the assigned criteria, 
including direct statements, indirect references, implications, and contextual information.
Be comprehensive and catch everything that might be relevant."""
        
        # Add custom instructions if provided
        if self.custom_instructions:
            system_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{self.custom_instructions}"
        
        # Format criteria for the prompt with detailed scoring information
        criteria_text = ""
        for criterion in assigned_criteria:
            criteria_text += f"CRITERION: {criterion['criterion_name']}\n"
            criteria_text += f"QUESTION: {criterion['criterion_question']}\n"
            criteria_text += f"DIMENSION: {criterion['dimension_name']}\n"
            
            # Add scoring definitions to help with relevance determination
            if criterion['scoring_definitions']:
                criteria_text += "SCORING LEVELS:\n"
                for score, definition in criterion['scoring_definitions'].items():
                    criteria_text += f"- Level {score}: {definition}\n"
            
            criteria_text += "\n"
        
        human_prompt = f"""Extract ALL evidence from the following text chunk that relates to the assigned criteria.

TEXT CHUNK:
{chunk_text}

ASSIGNED CRITERIA:
{criteria_text}

For each piece of evidence you find, provide:
1. The criterion ID it relates to
2. The dimension ID it belongs to
3. The exact text passage that constitutes evidence (direct quote)
4. An explanation of why this is relevant to the criterion
5. A confidence score (0.0-1.0) indicating how strongly this relates to the criterion
6. The relevance level (Direct, Indirect, Contextual, Implied)

Be thorough - extract ANY text that might be relevant, even indirectly. Consider tone, word choice, 
and contextual implications. Look for both positive and negative evidence.

Format your response as a structured list of evidence items."""

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
                            "relevance_explanation": {"type": "string"},
                            "confidence": {"type": "number"},
                            "relevance_level": {"type": "string", "enum": ["Direct", "Indirect", "Contextual", "Implied"]}
                        },
                        "required": ["dimension_id", "criterion_id", "text", "relevance_explanation", "confidence"]
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
            max_tokens=2000
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
            relevance_explanation = evidence_item.get("relevance_explanation", "")
            confidence = evidence_item.get("confidence", 0.8)  # Default if not provided
            relevance_level = evidence_item.get("relevance_level", "Direct")
            
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
                "relevance_explanation": relevance_explanation,
                "confidence": confidence,
                "relevance_level": relevance_level
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
                "relevance_explanation": relevance_explanation,
                "confidence": confidence,
                "relevance_level": relevance_level
            })
        
        return {
            "evidence": recorded_evidence,
            "evidence_count": len(recorded_evidence),
            "chunk_id": chunk_id
        }
    
    async def _consolidate_evidence(
        self, 
        extraction_results: Dict[str, Any], 
        assigned_criteria: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Consolidate evidence for each criterion across all chunks,
        creating a comprehensive evidence summary for the evaluator.
        
        Args:
            extraction_results: Results from evidence extraction
            assigned_criteria: List of assigned criteria
            
        Returns:
            Consolidated evidence summaries for each criterion
        """
        consolidated_evidence = {}
        
        self.update_progress(0.9, "Consolidating evidence for criteria")
        self.logger.info("Starting evidence consolidation for each criterion")
        
        # Process each criterion
        for criterion in assigned_criteria:
            criterion_id = criterion.get("criterion_id")
            dimension_id = criterion.get("dimension_id")
            
            # Get all evidence for this criterion
            key = f"{dimension_id}:{criterion_id}"
            evidence_list = extraction_results.get("by_criterion", {}).get(key, [])
            
            # Create consolidated evidence summary
            if evidence_list:
                summary = await self._create_consolidated_evidence_summary(evidence_list, criterion)
                
                consolidated_evidence[key] = {
                    "dimension_id": dimension_id,
                    "criterion_id": criterion_id,
                    "evidence_count": len(evidence_list),
                    "comprehensive_summary": summary,
                    "evidence_by_relevance": self._organize_evidence_by_relevance(evidence_list),
                    "evidence_items": evidence_list
                }
                
                self.logger.info(f"Consolidated {len(evidence_list)} evidence items for {key}")
            else:
                # No evidence found
                consolidated_evidence[key] = {
                    "dimension_id": dimension_id,
                    "criterion_id": criterion_id,
                    "evidence_count": 0,
                    "comprehensive_summary": "No evidence found for this criterion.",
                    "evidence_by_relevance": {},
                    "evidence_items": []
                }
                
                self.logger.info(f"No evidence found for {key}")
        
        self.update_progress(1.0, "Evidence consolidation complete")
        
        return consolidated_evidence
    
    def _organize_evidence_by_relevance(self, evidence_list: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Organize evidence by relevance level for easier evaluation.
        
        Args:
            evidence_list: List of evidence items
            
        Returns:
            Evidence organized by relevance level
        """
        by_relevance = {
            "Direct": [],
            "Indirect": [],
            "Contextual": [],
            "Implied": []
        }
        
        for evidence in evidence_list:
            relevance_level = evidence.get("relevance_level", "Direct")
            if relevance_level in by_relevance:
                by_relevance[relevance_level].append(evidence)
        
        # Remove empty categories
        return {k: v for k, v in by_relevance.items() if v}
    
    async def _create_consolidated_evidence_summary(
        self, 
        evidence_list: List[Dict[str, Any]], 
        criterion: Dict[str, Any]
    ) -> str:
        """
        Create a comprehensive summary of all evidence for a criterion.
        This will be the primary evidence packet provided to the evaluator.
        
        Args:
            evidence_list: List of all evidence items for the criterion
            criterion: Criterion information
            
        Returns:
            Comprehensive evidence summary
        """
        # Format evidence for prompt
        evidence_text = ""
        for i, evidence in enumerate(evidence_list):
            evidence_text += f"Evidence {i+1}:\n"
            evidence_text += f"Text: {evidence.get('text', '')}\n"
            evidence_text += f"Relevance: {evidence.get('relevance_explanation', '')}\n"
            evidence_text += f"Confidence: {evidence.get('confidence', '')}\n"
            evidence_text += f"Level: {evidence.get('relevance_level', 'Direct')}\n\n"
        
        # Create prompt
        criterion_name = criterion.get("criterion_name", "")
        criterion_question = criterion.get("criterion_question", "")
        dimension_name = criterion.get("dimension_name", "")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Format scoring definitions
        scoring_text = ""
        for score, definition in scoring_definitions.items():
            scoring_text += f"- Score {score}: {definition}\n"
        
        prompt = f"""Create a comprehensive analysis of all evidence related to the following criterion:

CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_name}

SCORING DEFINITIONS:
{scoring_text}

EVIDENCE COLLECTION:
{evidence_text}

Your task is to provide a comprehensive analysis and synthesis of ALL the evidence above. 
This summary will be used by an evaluator to assess the criterion, so it should be thorough and objective.

Include in your analysis:
1. A synthesis of what the evidence collectively indicates about this criterion
2. The strength and quality of the evidence as a whole
3. Key patterns or themes across all evidence items
4. Any contradictions or tensions in the evidence
5. What the evidence suggests about potential strengths and weaknesses
6. Whether the evidence tends toward a particular rating based on the scoring definitions

Keep your analysis factual and evidence-based. Do not make a final rating yourself, but organize the evidence 
in a way that will help the evaluator make an informed assessment.

Your comprehensive analysis:"""
        
        # Get summary
        summary, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=prompt,
            system_prompt="""You are an expert evidence analyst creating comprehensive evidence summaries.
Your job is to synthesize all available evidence for a criterion into a clear, comprehensive analysis
that will serve as the primary evidence packet for evaluation. Be thorough, balanced, and objective.""",
            temperature=0.3,
            max_tokens=1500
        )
        
        return summary