"""
Optimized Extractor Agent - Enhanced for concurrent evidence extraction

This agent thoroughly analyzes document chunks to find ALL evidence relevant to its
assigned criteria, with improved thread safety and more detailed logging.
"""

import logging
import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class ExtractorAgent(BaseAgent):
    """
    Optimized extractor agent with improved evidence tracking and storage.
    
    The Enhanced Extractor is responsible for:
    1. Deep analysis of all document chunks for assigned criteria
    2. Finding all potential evidence with better relevance and sentiment categorization
    3. Reliably storing evidence with thread safety
    4. Creating comprehensive evidence summaries with direct/inferred recommendations
    5. Providing confidence and relevance assessments for the evidence
    6. Processing chunks in parallel for efficiency
    7. Detailed evidence tracking and diagnostic logging
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
        self.min_confidence = self.options.get("min_confidence", 0.3)
        self.custom_instructions = self.options.get("instructions", "")
        
        # Get assigned criteria (specific to this extractor)
        self.criteria_ids = self.options.get("criteria_ids", [])
        self.dimension_ids = self.options.get("dimension_ids", [])
        
        # For parallel processing
        self.max_concurrent = self.options.get("max_concurrent", 3)
        
        # Evidence tracking with atomic counters
        self._evidence_found = 0
        self._evidence_stored = 0
        self._evidence_filtered = 0
        
        # Diagnostic tracing - enable for debugging
        self.enable_tracing = self.options.get("enable_tracing", False)
        self._trace_log = []
        
        # Create descriptive agent name for logging
        if len(self.criteria_ids) == 1 and hasattr(self.context, "framework"):
            # Try to find criterion name
            for dimension in self.context.framework.get("dimensions", []):
                for criterion in dimension.get("criteria", []):
                    if criterion.get("id") == self.criteria_ids[0]:
                        criterion_name = criterion.get("name", self.criteria_ids[0])
                        self.name = f"Extractor({criterion_name})"
                        break
        
        self.logger.info(f"{name} initialized for {len(self.criteria_ids)} criteria with min_confidence={self.min_confidence}")
        
    async def process(self, chunks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process document chunks to extract all evidence for assigned criteria,
        then consolidate evidence for each criterion across all chunks.
        
        Args:
            chunks: Optional list of document chunks (uses context chunks if None)
            
        Returns:
            Extraction results with consolidated evidence summaries
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
                return {"by_chunk": {}, "by_criterion": {}, "total_evidence": 0, "consolidated_evidence": {}}
            
            # Process chunks in parallel for assigned criteria
            extraction_results = await self._process_chunks_in_parallel(chunks_to_process, assigned_criteria)
            
            # Log evidence tracking information
            self.logger.info(
                f"Evidence tracking: Found: {self._evidence_found}, "
                f"Stored: {self._evidence_stored}, "
                f"Filtered: {self._evidence_filtered}"
            )
            
            # Check current evidence in context for verification
            for criterion in assigned_criteria:
                dimension_id = criterion["dimension_id"]
                criterion_id = criterion["criterion_id"]
                evidence_count = self.context.get_evidence_count(dimension_id, criterion_id)
                self.logger.info(f"Context evidence count for {dimension_id}:{criterion_id}: {evidence_count}")
            
            # Consolidate evidence for each criterion
            consolidated_evidence = await self._consolidate_evidence(extraction_results, assigned_criteria)
            extraction_results["consolidated_evidence"] = consolidated_evidence
            
            # Update total evidence count from context (more reliable than local tracking)
            total_evidence = 0
            for criterion in assigned_criteria:
                dimension_id = criterion["dimension_id"]
                criterion_id = criterion["criterion_id"]
                evidence_count = self.context.get_evidence_count(dimension_id, criterion_id)
                total_evidence += evidence_count
            
            extraction_results["total_evidence"] = total_evidence
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Evidence extraction completed in {elapsed_time:.2f}s")
            
            # Record observation with complete evidence stats
            self.record_observation("extraction_completed", {
                "chunks_processed": len(chunks_to_process),
                "evidence_extracted": total_evidence,
                "evidence_found": self._evidence_found,
                "evidence_filtered": self._evidence_filtered,
                "criteria_processed": len(assigned_criteria),
                "time_taken": elapsed_time,
                "consolidated_evidence": consolidated_evidence
            })
            
            # Add trace log if tracing enabled
            if self.enable_tracing:
                extraction_results["trace_log"] = self._trace_log
            
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
        
        self.logger.info(f"Found {len(assigned_criteria)} criteria matching assigned IDs {self.criteria_ids}")
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
        batch_results = await self.run_parallel_tasks(tasks, self.max_concurrent)
        
        # Aggregate results
        for batch_result in batch_results:
            if not batch_result:
                continue
                
            # Update by_chunk results
            for chunk_id, chunk_data in batch_result.get("by_chunk", {}).items():
                results["by_chunk"][chunk_id] = chunk_data
            
            # Update by_criterion results
            for criterion_key, evidence_list in batch_result.get("by_criterion", {}).items():
                if criterion_key not in results["by_criterion"]:
                    results["by_criterion"][criterion_key] = []
                results["by_criterion"][criterion_key].extend(evidence_list)
        
        # Calculate total evidence from results
        total_evidence = 0
        for chunk_data in results["by_chunk"].values():
            total_evidence += chunk_data.get("evidence_count", 0)
        
        results["total_evidence"] = total_evidence
        self.logger.info(f"Aggregated results: {total_evidence} total evidence items from {len(results['by_chunk'])} chunks")
        
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
        
        # Track start time for diagnostic info
        start_time = time.time()
        
        # Add start/end markers to chunk text for LLM awareness
        chunk_text_with_markers = f"[CHUNK START]\n{chunk_text}\n[CHUNK END]"
        
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
        
        # Enhanced prompt to emphasize finding ANY evidence
        human_prompt = f"""Extract ALL evidence from the following text chunk that relates to the assigned criteria.

TEXT CHUNK:
{chunk_text_with_markers}

ASSIGNED CRITERIA:
{criteria_text}

For each piece of evidence you find, provide:
1. The criterion ID it relates to
2. The dimension ID it belongs to
3. The exact text passage that constitutes evidence (direct quote)
4. An explanation of why this is relevant to the criterion
5. A confidence score (0.0-1.0) indicating how strongly this relates to the criterion
6. The relevance level:
   - Direct: Explicitly addresses the criterion
   - Indirect: Implicitly relates to the criterion
   - Contextual: Provides important context for understanding
   - Implied: Suggests something about the criterion without stating it
7. The sentiment of this evidence:
   - Positive: Supports a positive assessment of the criterion
   - Negative: Indicates a deficiency or problem
   - Neutral: Factual or balanced information
8. Sufficiency indicator - how strongly this single piece of evidence could support a rating:
   - Strong: Could substantially influence a rating on its own
   - Moderate: Contributes meaningfully but needs corroboration
   - Weak: Minor support that primarily adds context

Be extremely thorough - extract ANYTHING that might be relevant, even indirectly or weakly related.
Include evidence even if you aren't completely confident - I'll filter out the low-confidence items later.
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
                            "relevance_level": {"type": "string", "enum": ["Direct", "Indirect", "Contextual", "Implied"]},
                            "sentiment": {"type": "string", "enum": ["Positive", "Negative", "Neutral"]},
                            "sufficiency_indicator": {"type": "string", "enum": ["Strong", "Moderate", "Weak"]}
                        },
                        "required": ["dimension_id", "criterion_id", "text", "relevance_explanation", "confidence"]
                    }
                }
            },
            "required": ["evidence"]
        }
        
        # Log the extraction start
        self.logger.info(f"Extracting evidence from chunk {chunk_id} for {len(assigned_criteria)} criteria")
        
        # Use direct LLM call instead of cached call for reliable evidence extraction
        extracted_evidence = await self._safe_llm_call(
            "generate_structured_output",
            prompt=human_prompt,
            output_schema=evidence_schema,
            system_prompt=system_prompt,
            temperature=0.9,
            max_tokens=2000
        )
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Process and record evidence
        evidence_list = []
        if isinstance(extracted_evidence, dict) and "evidence" in extracted_evidence:
            evidence_list = extracted_evidence["evidence"]
            
        # Log the raw number of evidence items found
        raw_evidence_count = len(evidence_list)
        self._evidence_found += raw_evidence_count
        self.logger.info(f"Found {raw_evidence_count} raw evidence items in chunk {chunk_id} in {elapsed_time:.2f}s")
        
        # Add to trace log if enabled
        if self.enable_tracing:
            self._trace_log.append({
                "operation": "extract_evidence",
                "chunk_id": chunk_id,
                "time": elapsed_time,
                "evidence_found": raw_evidence_count,
                "assigned_criteria": [f"{c['dimension_id']}:{c['criterion_id']}" for c in assigned_criteria]
            })
        
        recorded_evidence = []
        filtered_evidence = 0
        
        # Track which criteria got evidence
        criteria_with_evidence = set()
        
        for evidence_item in evidence_list:
            dimension_id = evidence_item.get("dimension_id")
            criterion_id = evidence_item.get("criterion_id")
            text = evidence_item.get("text", "").strip()
            relevance_explanation = evidence_item.get("relevance_explanation", "")
            confidence = evidence_item.get("confidence", 0.8)  # Default if not provided
            relevance_level = evidence_item.get("relevance_level", "Direct")
            sentiment = evidence_item.get("sentiment", "Neutral")
            sufficiency_indicator = evidence_item.get("sufficiency_indicator", "Moderate")
            
            if not dimension_id or not criterion_id or not text:
                self.logger.warning(f"Skipping invalid evidence item (missing required fields): {evidence_item}")
                continue
                
            # Log evidence confidence before filtering
            self.logger.debug(f"Evidence for {dimension_id}:{criterion_id} - Confidence: {confidence}, Relevance: {relevance_level}")
            
            # Skip low-confidence evidence if threshold is set
            if confidence < self.min_confidence:
                self.logger.debug(f"Filtering low-confidence evidence ({confidence} < {self.min_confidence}) for {dimension_id}:{criterion_id}")
                self._evidence_filtered += 1
                filtered_evidence += 1
                continue
                
            # Add evidence to context
            metadata = {
                "extraction_type": self.extraction_type,
                "relevance_explanation": relevance_explanation,
                "confidence": confidence,
                "relevance_level": relevance_level,
                "sentiment": sentiment,
                "sufficiency_indicator": sufficiency_indicator
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
            
            # Store evidence in context
            try:
                evidence_id = self.add_evidence(
                    dimension_id=dimension_id,
                    criterion_id=criterion_id,
                    text=text,
                    chunk_id=chunk_id,
                    location=location,
                    metadata=metadata
                )
                
                # Increment stored evidence counter
                self._evidence_stored += 1
                
                # Track which criterion got evidence
                criteria_with_evidence.add(f"{dimension_id}:{criterion_id}")
                
                # Add to results
                recorded_evidence.append({
                    "evidence_id": evidence_id,
                    "dimension_id": dimension_id,
                    "criterion_id": criterion_id,
                    "text": text,
                    "relevance_explanation": relevance_explanation,
                    "confidence": confidence,
                    "relevance_level": relevance_level,
                    "sentiment": sentiment,
                    "sufficiency_indicator": sufficiency_indicator,
                    "metadata": metadata
                })
                
            except Exception as e:
                self.logger.error(f"Error storing evidence: {str(e)}", exc_info=True)
                self.add_warning(f"Failed to store evidence: {str(e)}")
        
        # Log evidence storage results
        self.logger.info(
            f"Chunk {chunk_id}: Found {raw_evidence_count}, Filtered {filtered_evidence}, "
            f"Stored {len(recorded_evidence)} evidence items for {len(criteria_with_evidence)} criteria"
        )
        
        if criteria_with_evidence:
            self.logger.info(f"Criteria with evidence: {', '.join(criteria_with_evidence)}")
        
        return {
            "evidence": recorded_evidence,
            "evidence_count": len(recorded_evidence),
            "evidence_filtered": filtered_evidence,
            "chunk_id": chunk_id,
            "processing_time": elapsed_time,
            "criteria_with_evidence": list(criteria_with_evidence)
        }
    
    
    async def _consolidate_evidence(
        self, 
        extraction_results: Dict[str, Any], 
        assigned_criteria: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Consolidate evidence for each criterion across all chunks,
        creating a comprehensive evidence summary with direct/inferred recommendation.
        
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
            
            # MODIFICATION: Log evidence count for this criterion 
            self.logger.info(f"Consolidating {len(evidence_list)} evidence items for {key}")
            
            # Create consolidated evidence summary
            if evidence_list:
                # Group evidence by relevance and sentiment
                grouped_evidence = {
                    "direct": {
                        "positive": [],
                        "negative": [],
                        "neutral": []
                    },
                    "indirect": {
                        "positive": [],
                        "negative": [],
                        "neutral": []
                    },
                    "contextual_implied": []
                }
                
                # Sort evidence into groups
                for evidence in evidence_list:
                    relevance = evidence.get("relevance_level", "Direct")
                    sentiment = evidence.get("sentiment", "Neutral")
                    
                    if relevance in ["Contextual", "Implied"]:
                        grouped_evidence["contextual_implied"].append(evidence)
                    elif relevance in ["Direct", "Indirect"]:
                        normalized_relevance = relevance.lower()
                        normalized_sentiment = sentiment.lower()
                        # Make sure dictionary keys exist
                        if normalized_sentiment not in grouped_evidence.get(normalized_relevance, {}):
                            if normalized_relevance not in grouped_evidence:
                                grouped_evidence[normalized_relevance] = {}
                            grouped_evidence[normalized_relevance][normalized_sentiment] = []
                        grouped_evidence[normalized_relevance][normalized_sentiment].append(evidence)
                
                # Create consolidated summary
                summary = await self._create_consolidated_evidence_summary(evidence_list, criterion, grouped_evidence)
                
                # MODIFICATION: Ensure direct assessment recommendation when evidence exists
                if len(evidence_list) > 0 and evidence_list:
                    if summary.get("direct_assessment_justified") == "NO":
                        # Check if we have any direct evidence with high confidence
                        direct_evidence = grouped_evidence.get("direct", {})
                        direct_count = sum(len(items) for items in direct_evidence.values())
                        
                        if direct_count > 0:
                            summary["direct_assessment_justified"] = "MAYBE"
                            self.logger.info(f"Upgrading assessment recommendation to MAYBE for {key} with {direct_count} direct evidence items")
                
                consolidated_evidence[key] = {
                    "dimension_id": dimension_id,
                    "criterion_id": criterion_id,
                    "evidence_count": len(evidence_list),
                    "comprehensive_analysis": summary.get("comprehensive_analysis", ""),
                    "key_patterns": summary.get("key_patterns", []),
                    "contradictions": summary.get("contradictions", []),
                    "direct_assessment_justified": summary.get("direct_assessment_justified", "NO"),
                    "suggested_rating_range": summary.get("suggested_rating_range", ""),
                    "confidence_level": summary.get("confidence_level", 0.5),
                    "evidence_by_category": self._get_evidence_category_counts(grouped_evidence),
                    "evidence_items": evidence_list
                }
                
                self.logger.info(f"Consolidated {len(evidence_list)} evidence items for {key}, assessment justified: {summary.get('direct_assessment_justified', 'NO')}")
            else:
                # No evidence found
                consolidated_evidence[key] = {
                    "dimension_id": dimension_id,
                    "criterion_id": criterion_id,
                    "evidence_count": 0,
                    "comprehensive_analysis": "No evidence found for this criterion.",
                    "direct_assessment_justified": "NO",
                    "evidence_by_category": {},
                    "evidence_items": []
                }
                
                self.logger.info(f"No evidence found for {key}")
        
        self.update_progress(1.0, "Evidence consolidation complete")
        
        return consolidated_evidence
    
    def _get_evidence_category_counts(self, grouped_evidence: Dict[str, Any]) -> Dict[str, int]:
        """
        Get counts of evidence by category for reporting.
        
        Args:
            grouped_evidence: Evidence grouped by relevance and sentiment
            
        Returns:
            Dictionary of evidence counts by category
        """
        counts = {}
        
        # Count direct evidence by sentiment
        for sentiment in ["positive", "negative", "neutral"]:
            direct_count = len(grouped_evidence.get("direct", {}).get(sentiment, []))
            if direct_count > 0:
                counts[f"direct_{sentiment}"] = direct_count
        
        # Count indirect evidence by sentiment
        for sentiment in ["positive", "negative", "neutral"]:
            indirect_count = len(grouped_evidence.get("indirect", {}).get(sentiment, []))
            if indirect_count > 0:
                counts[f"indirect_{sentiment}"] = indirect_count
        
        # Count contextual/implied evidence
        contextual_implied_count = len(grouped_evidence.get("contextual_implied", []))
        if contextual_implied_count > 0:
            counts["contextual_implied"] = contextual_implied_count
        
        # Add total counts
        counts["total"] = (
            sum(len(items) for sentiment, items in grouped_evidence.get("direct", {}).items()) +
            sum(len(items) for sentiment, items in grouped_evidence.get("indirect", {}).items()) +
            len(grouped_evidence.get("contextual_implied", []))
        )
        
        return counts
    
    async def _create_consolidated_evidence_summary(
        self, 
        evidence_list: List[Dict[str, Any]], 
        criterion: Dict[str, Any],
        grouped_evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a comprehensive summary of all evidence for a criterion with
        a recommendation on whether direct assessment is justified.
        
        Args:
            evidence_list: List of all evidence items for the criterion
            criterion: Criterion information
            grouped_evidence: Evidence grouped by relevance and sentiment
            
        Returns:
            Comprehensive evidence summary with assessment recommendation
        """
        # Format evidence for each group
        direct_positive = self._format_evidence_group(
            grouped_evidence.get("direct", {}).get("positive", [])
        )
        direct_negative = self._format_evidence_group(
            grouped_evidence.get("direct", {}).get("negative", [])
        )
        direct_neutral = self._format_evidence_group(
            grouped_evidence.get("direct", {}).get("neutral", [])
        )
        indirect_positive = self._format_evidence_group(
            grouped_evidence.get("indirect", {}).get("positive", [])
        )
        indirect_negative = self._format_evidence_group(
            grouped_evidence.get("indirect", {}).get("negative", [])
        )
        indirect_neutral = self._format_evidence_group(
            grouped_evidence.get("indirect", {}).get("neutral", [])
        )
        contextual_implied = self._format_evidence_group(
            grouped_evidence.get("contextual_implied", [])
        )
        
        # Counts for each category
        direct_count = (
            len(grouped_evidence.get("direct", {}).get("positive", [])) +
            len(grouped_evidence.get("direct", {}).get("negative", [])) +
            len(grouped_evidence.get("direct", {}).get("neutral", []))
        )
        indirect_count = (
            len(grouped_evidence.get("indirect", {}).get("positive", [])) +
            len(grouped_evidence.get("indirect", {}).get("negative", [])) +
            len(grouped_evidence.get("indirect", {}).get("neutral", []))
        )
        contextual_implied_count = len(grouped_evidence.get("contextual_implied", []))
        
        # Format the criterion information
        criterion_name = criterion.get("criterion_name", "")
        criterion_question = criterion.get("criterion_question", "")
        dimension_name = criterion.get("dimension_name", "")
        
        # Format scoring definitions
        scoring_definitions = criterion.get("scoring_definitions", {})
        scoring_text = ""
        for score, definition in scoring_definitions.items():
            scoring_text += f"- Score {score}: {definition}\n"
        
        # Create prompt for the comprehensive analysis
        prompt = f"""Create a comprehensive analysis of all evidence related to the following criterion:

CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_name}

EVIDENCE SUMMARY:
- Direct Evidence: {direct_count} items
- Indirect Evidence: {indirect_count} items
- Contextual/Implied Evidence: {contextual_implied_count} items
- Total Evidence: {len(evidence_list)} items

DIRECT POSITIVE EVIDENCE ({len(grouped_evidence.get("direct", {}).get("positive", []))}):
{direct_positive}

DIRECT NEGATIVE EVIDENCE ({len(grouped_evidence.get("direct", {}).get("negative", []))}):
{direct_negative}

DIRECT NEUTRAL EVIDENCE ({len(grouped_evidence.get("direct", {}).get("neutral", []))}):
{direct_neutral}

INDIRECT POSITIVE EVIDENCE ({len(grouped_evidence.get("indirect", {}).get("positive", []))}):
{indirect_positive}

INDIRECT NEGATIVE EVIDENCE ({len(grouped_evidence.get("indirect", {}).get("negative", []))}):
{indirect_negative}

INDIRECT NEUTRAL EVIDENCE ({len(grouped_evidence.get("indirect", {}).get("neutral", []))}):
{indirect_neutral}

CONTEXTUAL/IMPLIED EVIDENCE ({contextual_implied_count}):
{contextual_implied}

SCORING DEFINITIONS:
{scoring_text}

Provide a comprehensive analysis that:
1. Synthesizes what the evidence collectively indicates about this criterion
2. Evaluates the strength and quality of evidence for making an assessment
3. Identifies key patterns and themes across the evidence
4. Notes any contradictions or tensions in the evidence
5. Recommends whether a direct assessment is justified based on evidence (YES/NO/MAYBE)
6. Suggests what rating range (if any) the evidence best supports

Your comprehensive analysis:"""
        
        # Define schema for structured output
        summary_schema = {
            "type": "object",
            "properties": {
                "comprehensive_analysis": {"type": "string"},
                "key_patterns": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "contradictions": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "direct_assessment_justified": {"type": "string", "enum": ["YES", "NO", "MAYBE"]},
                "suggested_rating_range": {"type": "string"},
                "confidence_level": {"type": "number"}
            },
            "required": ["comprehensive_analysis", "direct_assessment_justified"]
        }
        
        # Get summary using structured output call
        system_prompt = """You are an expert evidence analyst creating comprehensive evidence summaries.
Your job is to synthesize all available evidence for a criterion into a clear, balanced analysis
that will help an evaluator determine if a direct rating is possible or if inference is needed.

Be careful with your recommendation about direct assessment:
- Use "YES" only when there is substantial direct evidence that clearly supports a specific rating
- Use "MAYBE" when there is some evidence but it's mixed or not entirely conclusive
- Use "NO" when there is insufficient evidence to make a direct assessment

Be objective and evidence-based in your analysis."""
        
        # MODIFICATION: If there's evidence, be more generous with assessment recommendations
        if len(evidence_list) > 0:
            system_prompt += """
NOTE: If there is ANY direct evidence, lean toward recommending at least "MAYBE" for direct assessment.
Even limited evidence can be valuable for assessment when analyzed properly."""
        
        # Optimize the prompt if it's very large
        optimized_prompt = self.optimize_prompt(prompt, 6000)
        
        # Call LLM for the summary
        try:
            summary = await self._structured_output_call(
                prompt=optimized_prompt,
                output_schema=summary_schema,
                system_prompt=system_prompt,
                temperature=0.9
            )
            
            return summary
        except Exception as e:
            self.logger.error(f"Error creating evidence summary: {str(e)}")
            # Return minimal valid structure
            return {
                "comprehensive_analysis": f"Error creating comprehensive analysis: {str(e)}",
                "key_patterns": [],
                "contradictions": [],
                "direct_assessment_justified": "NO" if len(evidence_list) == 0 else "MAYBE",
                "suggested_rating_range": "",
                "confidence_level": 0.0
            }
    
    def _format_evidence_group(self, evidence_group: List[Dict[str, Any]]) -> str:
        """
        Format a group of evidence items for the summary prompt.
        
        Args:
            evidence_group: List of evidence items in this group
            
        Returns:
            Formatted evidence text
        """
        if not evidence_group:
            return "None"
        
        formatted = ""
        for i, evidence in enumerate(evidence_group):
            text = evidence.get("text", "")
            relevance_explanation = evidence.get("relevance_explanation", "")
            confidence = evidence.get("confidence", 0.8)
            sufficiency = evidence.get("sufficiency_indicator", "Moderate")
            
            formatted += f"Evidence {i+1}: {text}\n"
            formatted += f"Relevance: {relevance_explanation}\n"
            formatted += f"Confidence: {confidence}\n"
            formatted += f"Sufficiency: {sufficiency}\n\n"
        
        return formatted