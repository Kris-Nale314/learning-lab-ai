"""
Streamlined Extractor Agent - Simple two-pass evidence collection

This agent collects and consolidates evidence for criteria evaluation using a
straightforward two-pass approach: first collecting evidence from each chunk,
then creating a single consolidated evidence packet per criterion.
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Set

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class ExtractorAgent(BaseAgent):
    """
    Creates consolidated evidence packets for criteria evaluation.
    
    Key capabilities:
    1. First pass: Extract evidence from each document chunk
    2. Second pass: Consolidate evidence into a single packet per criterion
    3. Focus on DIRECT QUOTES and METRICS
    4. Preserve key context for evaluation
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
            llm: LLM instance
            context: Assessment context
            name: Agent name
            options: Configuration options including assigned criteria & instructions
        """
        super().__init__(name, "extractor", llm, context, options or {})
        
        # Configuration
        self.options = options or {}
        self.config = options.get("configuration", {})
        
        # Get instructions from Meta Planner
        self.instructions = self.options.get("instructions", "")
        
        # Get assigned criteria IDs
        self.criteria_ids = self.config.get("criteria_ids", [])
        if not self.criteria_ids:
            self.logger.warning(f"Extractor '{self.name}' initialized with no assigned criteria_ids!")
        
        # Get or infer dimension IDs
        self.dimension_ids = self.config.get("dimension_ids", self._infer_dimension_ids(self.criteria_ids))
        
        # Concurrency control
        self.max_concurrent = self.config.get("max_concurrent", 3)
        
        # Evidence counters
        self.chunk_packets_created = 0
        self.consolidated_packets_created = 0

        self.logger.info(
            f"Streamlined Extractor '{self.name}' initialized for criteria: {', '.join(self.criteria_ids)}"
        )

    def _infer_dimension_ids(self, criteria_ids: List[str]) -> List[str]:
        """Find dimension IDs for given criteria IDs from the framework."""
        inferred_ids = set()
        if not hasattr(self.context, 'framework'): 
            return []
        
        framework = self.context.framework
        for dim in framework.get("dimensions", []):
            dim_id = dim.get("id")
            if not dim_id: 
                continue
                
            for crit in dim.get("criteria", []):
                crit_id = crit.get("id")
                if crit_id in criteria_ids:
                    inferred_ids.add(dim_id)
                    
        return list(inferred_ids)

    async def process(self, chunks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process all chunks for assigned criteria using a two-pass approach.
        
        Args:
            chunks: Optional list of document chunks (uses context chunks if None)
            
        Returns:
            Summary of extraction results
        """
        process_start_time = time.time()
        self.logger.info(f"Starting evidence extraction for {len(self.criteria_ids)} criteria")
        
        try:
            # Use provided chunks or get from context
            chunks_to_process = chunks or self.context.get_chunks()
            
            if not chunks_to_process:
                self.logger.error("No document chunks available for extraction")
                raise ValueError("No document chunks available for extraction")
            
            self.logger.info(f"Processing document with {len(chunks_to_process)} chunks")
            
            # PASS 1: Extract evidence from each chunk for each criterion
            chunk_evidence_packets = {}  # criterion_id -> [packets]
            
            for criterion_id in self.criteria_ids:
                self.logger.info(f"Processing criterion: {criterion_id}")
                
                # Get details for this criterion
                criterion_info = self._get_criterion_details(criterion_id)
                if not criterion_info:
                    self.logger.warning(f"Could not find details for criterion: {criterion_id}")
                    continue
                    
                chunk_evidence_packets[criterion_id] = []
                
                # Process all chunks for this criterion (with concurrency control)
                tasks = [
                    self._extract_evidence_from_chunk(criterion_info, chunk['text'], chunk['chunk_id'])
                    for chunk in chunks_to_process
                ]
                
                results = await self.run_parallel_tasks(tasks, max_concurrent=self.max_concurrent)
                
                # Filter out None results and add successful packets
                for result in results:
                    if result and result.get("evidence_found", False):
                        chunk_evidence_packets[criterion_id].append(result)
                
                self.logger.info(
                    f"Found evidence in {len(chunk_evidence_packets[criterion_id])} chunks for criterion {criterion_id}"
                )
            
            # PASS 2: Consolidate evidence for each criterion
            consolidated_results = {}
            
            for criterion_id, packets in chunk_evidence_packets.items():
                # Get criterion details
                criterion_info = self._get_criterion_details(criterion_id)
                if not criterion_info:
                    continue
                
                # Handle case with no evidence found
                if not packets:
                    self.logger.info(f"No evidence found for criterion: {criterion_id}")
                    
                    # Create empty packet
                    self._create_empty_evidence_packet(criterion_info)
                    
                    consolidated_results[criterion_id] = {
                        "evidence_found": False,
                        "packets_consolidated": 0
                    }
                    continue
                
                # Consolidate evidence from all chunks
                consolidated_packet = await self._consolidate_evidence(criterion_info, packets)
                
                # Store consolidated packet in context
                evidence_id = self.add_evidence(
                    dimension_id=criterion_info['dimension_id'],
                    criterion_id=criterion_id,
                    text=consolidated_packet['text'],
                    metadata={
                        "source_agent": self.name,
                        "packet_type": "consolidated",
                        "evidence_found": consolidated_packet['evidence_found'],
                        "chunk_count": len(packets),
                        "confidence": 0.9  # High confidence in consolidated packet
                    }
                )
                
                if evidence_id:
                    self.consolidated_packets_created += 1
                    
                    consolidated_results[criterion_id] = {
                        "evidence_found": consolidated_packet['evidence_found'],
                        "packets_consolidated": len(packets)
                    }
                else:
                    self.logger.error(f"Failed to store consolidated packet for criterion: {criterion_id}")
            
            # Create result summary
            elapsed_time = time.time() - process_start_time
            
            summary = {
                "status": "completed",
                "criteria_processed": len(self.criteria_ids),
                "chunk_packets_created": self.chunk_packets_created,
                "consolidated_packets_created": self.consolidated_packets_created,
                "processing_time": elapsed_time,
                "results_by_criterion": consolidated_results
            }
            
            self.logger.info(
                f"Extraction completed in {elapsed_time:.2f}s. "
                f"Created {self.consolidated_packets_created} consolidated packets "
                f"from {self.chunk_packets_created} chunk packets."
            )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error during evidence extraction: {str(e)}", exc_info=True)
            self.context.add_warning(f"Extractor '{self.name}' failed: {str(e)}")
            
            # Return error summary
            return {
                "status": "failed",
                "error": str(e),
                "processing_time": time.time() - process_start_time
            }

    def _get_criterion_details(self, criterion_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a criterion from the framework."""
        if not hasattr(self.context, 'framework'):
            return None
            
        framework = self.context.framework
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id or dimension_id not in self.dimension_ids:
                continue
                
            for criterion in dimension.get("criteria", []):
                if criterion.get("id") == criterion_id:
                    return {
                        "dimension_id": dimension_id,
                        "dimension_name": dimension_name,
                        "criterion_id": criterion_id,
                        "criterion_name": criterion.get("name", ""),
                        "criterion_question": criterion.get("question", ""),
                        "scoring_method": criterion.get("scoring_method", "unknown"),
                        "scoring_definitions": criterion.get("scoring_definitions", {})
                    }
        
        return None

    async def _extract_evidence_from_chunk(
        self, 
        criterion_info: Dict[str, Any],
        chunk_text: str,
        chunk_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract evidence for a criterion from a single chunk.
        
        Args:
            criterion_info: Criterion details
            chunk_text: Text of the chunk
            chunk_id: Optional chunk identifier
            
        Returns:
            Evidence packet dictionary or None if extraction failed
        """
        criterion_id = criterion_info["criterion_id"]
        criterion_name = criterion_info["criterion_name"]
        criterion_question = criterion_info["criterion_question"]
        
        try:
            # Create a prompt that encourages detailed evidence extraction
            prompt = f"""Extract evidence from this document chunk to assess this criterion:

CRITERION: {criterion_name}
QUESTION: {criterion_question}

Find ALL relevant evidence in this document chunk. Focus on EXACT QUOTES and METRICS.

DOCUMENT CHUNK:
{chunk_text}

Format your response as a detailed evidence packet:

===== EVIDENCE PACKET FOR: {criterion_name} =====

DIRECT QUOTES:
- [List exact quotes that directly address this criterion]

KEY METRICS:
- [List any numbers, percentages, or quantitative data related to this criterion]

RELEVANCE ANALYSIS:
[Explain how this evidence relates to the criterion. Be specific about why each quote or metric is relevant.]

ASSESSMENT IMPLICATION:
[Indicate what this evidence suggests about a potential rating]

If you find NO relevant evidence in this chunk, clearly state "NO RELEVANT EVIDENCE FOUND" in each section.
"""

            # Custom additional instructions from meta planner if available
            if self.instructions:
                prompt += f"\n\nADDITIONAL GUIDANCE:\n{self.instructions}"

            # Call LLM
            evidence_text, _ = await self.llm.generate_completion(
                prompt=prompt,
                temperature=0.2,
                max_tokens=2000
            )
            
            # Check if evidence was found or not
            no_evidence_indicators = [
                "no relevant evidence found",
                "no direct quotes found",
                "no key metrics found",
                "no evidence found"
            ]
            
            evidence_found = True
            for indicator in no_evidence_indicators:
                if indicator in evidence_text.lower():
                    evidence_found = False
                    break
            
            # Only store evidence packets with content to save context space
            if evidence_found:
                self.chunk_packets_created += 1
                
                packet = {
                    "text": evidence_text,
                    "chunk_id": chunk_id,
                    "evidence_found": True
                }
                
                return packet
            else:
                # Return None for chunks with no evidence
                return None
                
        except Exception as e:
            self.logger.error(
                f"Error extracting evidence for criterion {criterion_id} from chunk {chunk_id}: {str(e)}"
            )
            return None

    def _create_empty_evidence_packet(self, criterion_info: Dict[str, Any]) -> str:
        """Create an empty evidence packet for a criterion with no evidence."""
        criterion_id = criterion_info["criterion_id"]
        criterion_name = criterion_info["criterion_name"]
        
        empty_packet = f"""===== EVIDENCE PACKET FOR: {criterion_name} =====

DIRECT QUOTES:
NO RELEVANT QUOTES FOUND

KEY METRICS:
NO RELEVANT METRICS FOUND

RELEVANCE ANALYSIS:
No relevant evidence was found in the document for this criterion.

ASSESSMENT IMPLICATION:
Insufficient evidence to make an assessment on this criterion.
"""
        
        # Store empty packet in context
        evidence_id = self.add_evidence(
            dimension_id=criterion_info['dimension_id'],
            criterion_id=criterion_id,
            text=empty_packet,
            metadata={
                "source_agent": self.name,
                "packet_type": "empty",
                "evidence_found": False,
                "confidence": 0.0
            }
        )
        
        if evidence_id:
            self.consolidated_packets_created += 1
            
        return empty_packet

    async def _consolidate_evidence(
        self, 
        criterion_info: Dict[str, Any],
        packets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Consolidate evidence from multiple chunk packets into a single master packet.
        
        Args:
            criterion_info: Criterion details
            packets: List of evidence packets from individual chunks
            
        Returns:
            Consolidated evidence packet
        """
        criterion_id = criterion_info["criterion_id"]
        criterion_name = criterion_info["criterion_name"]
        criterion_question = criterion_info["criterion_question"]
        
        # Create a simple formatted text with all evidence
        all_evidence_texts = []
        for i, packet in enumerate(packets):
            all_evidence_texts.append(f"EVIDENCE FROM CHUNK {i+1}:\n{packet['text']}\n")
        
        combined_evidence = "\n".join(all_evidence_texts)
        
        # Create consolidation prompt
        prompt = f"""Create a CONSOLIDATED evidence packet for this criterion:

CRITERION: {criterion_name}
QUESTION: {criterion_question}

Below are evidence packets collected from different chunks of the document:

{combined_evidence}

Your task is to create ONE CLEAR AND COMPELLING consolidated evidence packet that:

1. Combines all relevant evidence from the different chunks
2. Eliminates redundancies and duplications
3. Organizes the evidence logically
4. Preserves the most important direct quotes and metrics
5. Provides a unified analysis of what the evidence suggests about this criterion

Format your response as:

===== CONSOLIDATED EVIDENCE PACKET FOR: {criterion_name} =====

DIRECT QUOTES:
- [List the most relevant exact quotes, eliminating duplicates]

KEY METRICS:
- [List the most significant numbers, metrics, and quantitative data]

RELEVANCE ANALYSIS:
[Provide a unified explanation of how all this evidence relates to the criterion]

ASSESSMENT IMPLICATION:
[Indicate what the combined evidence suggests about a potential rating]

Focus on QUALITY over quantity. Select the strongest and most relevant evidence.
"""

        # Call LLM for consolidation
        consolidated_text, _ = await self.llm.generate_completion(
            prompt=prompt,
            temperature=0.3,
            max_tokens=3000
        )
        
        return {
            "text": consolidated_text,
            "evidence_found": True,
            "packets_consolidated": len(packets)
        }