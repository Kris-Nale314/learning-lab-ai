"""
Strategy Executor - Orchestrates assessment process with semantic group awareness

This module provides the StrategyExecutor class that coordinates the entire
assessment process from document chunking to final report generation, with
improved evidence flow and semantic criteria group handling.
"""

import logging
import json
import asyncio
import time
import os
from datetime import datetime, timezone
import re
from typing import Dict, Any, List, Optional, Tuple, Type, Set, Union

# Import agents
from core.agents.base import BaseAgent
from core.agents.meta_planner import MetaPlannerAgent
from core.agents.extractor import ExtractorAgent
from core.agents.evaluator import EvaluatorAgent
from core.agents.reporter import ReporterAgent

# Import other components
from core.context import AssessmentContext
from core.models.document import Document

class StrategyExecutor:
    """
    Orchestrates the assessment process with semantic criteria grouping.
    
    The Strategy Executor is responsible for:
    1. Running the Meta Planner to design assessment strategies
    2. Processing document chunking according to strategy
    3. Deploying extractors based on semantic criteria groups
    4. Ensuring proper evidence flow from extractors to evaluators
    5. Tracking evidence collection and assessment creation
    6. Generating final assessment reports
    """
    
    def __init__(
        self,
        llm,
        document: Document,
        framework: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the strategy executor.
        
        Args:
            llm: Language model instance
            document: Document to assess
            framework: Assessment framework
            options: Configuration options
        """
        self.llm = llm
        self.document = document
        self.framework = framework
        self.options = options or {}
        self.strategy = None
        self.agents = {}
        
        # Initialize context with document properties
        document_options = {
            "document_name": document.filename,
            "document_type": document.document_type,
            "document_bias": document.document_bias,
            "primary_entity": document.primary_entity,
            **(self.options or {})
        }
        self.context = AssessmentContext(document.text, framework, document_options)
        
        # Set up logging
        self.logger = logging.getLogger("learning-lab-ai.execution")
        self.logger.info(f"Strategy executor initialized for document: {document.filename}")
        
        # Diagnostic tracking
        self.diagnostics = {
            "execution_start": time.time(),
            "stages_completed": [],
            "evidence_checks": [],
            "token_usage": {}
        }
    
    async def get_strategy_preview(self) -> Dict[str, Any]:
        """
        Get a preview of the assessment strategy for user review.
        
        Returns:
            Strategy preview with human-readable explanations
        """
        if not self.strategy:
            self.strategy = await self.plan()
        
        # Create a user-friendly preview of the strategy
        preview = {
            "strategy_type": self.strategy.get("strategy_type", "unknown"),
            "rationale": self.strategy.get("rationale", ""),
            "chunking": {
                "method": self.strategy.get("chunking_strategy", {}).get("method", "unknown"),
                "size": self.strategy.get("chunking_strategy", {}).get("size", 0),
                "overlap": self.strategy.get("chunking_strategy", {}).get("overlap", 0),
                "rationale": self.strategy.get("chunking_strategy", {}).get("rationale", "")
            },
            "semantic_groups": self.strategy.get("semantic_groups", []),
            "total_extractors": len([a for a in self.strategy.get("agents", []) 
                                if self._is_extractor(a.get("agent_type", ""))]),
            "agents": [],
            "processing_sequence": self.strategy.get("processing_sequence", [])
        }
        
        # Add agent details
        for agent in self.strategy.get("agents", []):
            agent_preview = {
                "type": agent.get("agent_type", "unknown"),
                "configuration": agent.get("configuration", {}),
                "instructions": agent.get("instructions", "")[:100] + "..." 
                               if len(agent.get("instructions", "")) > 100 
                               else agent.get("instructions", "")
            }
            preview["agents"].append(agent_preview)
        
        return preview
    
    async def plan(self) -> Dict[str, Any]:
        """
        Run the Meta Planner to design an assessment strategy.
        
        Returns:
            Assessment strategy
        """
        self.logger.info("Running Meta Planner to design strategy")
        
        # Set planning stage
        self.context.set_stage("strategy_design")
        
        # Initialize Meta Planner
        meta_planner = MetaPlannerAgent(self.llm, self.context)
        
        # Design strategy
        strategy = await meta_planner.process()
        
        # Store strategy in context
        self.context.set_strategy(strategy)
        
        # Complete planning stage
        self.context.complete_stage("strategy_design", {"strategy": strategy})
        
        # Add to diagnostics
        self.diagnostics["stages_completed"].append({
            "stage": "strategy_design",
            "time": time.time() - self.diagnostics["execution_start"],
            "result": "success"
        })
        
        return strategy
    
    async def execute(self, strategy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the assessment process from start to finish.
        
        Args:
            strategy: Optional strategy to use (if not provided, uses the result of plan())
                
        Returns:
            UI-ready assessment results
        """
        # Initialize result tracking
        execution_start = time.time()
        evaluation_results = {}
        report_results = {}
        evidence_count = 0
        
        try:
            self.logger.info("Starting assessment execution")
            
            # Begin with document analysis stage
            self.context.set_stage("document_analysis")
            
            # Use provided strategy or run planner
            if strategy:
                self.strategy = strategy
            elif not self.strategy:
                self.strategy = await self.plan()
            
            # Complete document analysis
            document_properties = {
                "document_type": self.document.document_type,
                "document_structure": self.document.document_structure,
                "primary_entity": self.document.primary_entity,
                "document_bias": self.document.document_bias,
                "keywords": self.document.keywords
            }
            self.context.set_document_properties(document_properties)
            
            self.context.complete_stage("document_analysis", {
                "document_length": len(self.document.text),
                "document_type": self.document.document_type,
                "entity_name": self.document.primary_entity.get("name", "unknown"),
                "strategy": self.strategy.get("strategy_type")
            })
            
            # Add to diagnostics
            self.diagnostics["stages_completed"].append({
                "stage": "document_analysis",
                "time": time.time() - execution_start,
                "result": "success"
            })
            
            # Process document chunking
            self.context.set_stage("chunking")
            chunks = await self._process_chunking()
            self.context.set_chunks(chunks)
            
            self.context.complete_stage("chunking", {"chunk_count": len(chunks)})
            
            # Add to diagnostics
            self.diagnostics["stages_completed"].append({
                "stage": "chunking",
                "time": time.time() - execution_start,
                "result": "success",
                "chunks": len(chunks)
            })
            
            # Get evidence packets from strategy
            evidence_packets = self.strategy.get("evidence_packets", [])
            
            # Also check for evidence packets in context observations
            observation_packets = self._get_evidence_packets_from_observations()
            if observation_packets and not evidence_packets:
                evidence_packets = observation_packets
                self.logger.info(f"Using {len(observation_packets)} evidence packets from observations")
            
            # Run extractors with evidence packets
            self.context.set_stage("evidence_extraction")
            try:
                extraction_results = await self._run_extractors_with_packets(evidence_packets, chunks)
                
                # Check evidence flow
                evidence_count = self.context.get_evidence_count()
                self.logger.info(f"Evidence count after extraction: {evidence_count}")
                
                # Track evidence by criteria for diagnostics
                evidence_by_criteria = self._track_evidence_by_criteria()
                self.logger.info(f"Criteria with evidence: {len(evidence_by_criteria)}")
                
                # Add diagnostic checkpoint
                self.diagnostics["evidence_checks"].append({
                    "stage": "after_extraction",
                    "time": time.time() - execution_start,
                    "total_evidence": evidence_count,
                    "criteria_with_evidence": len(evidence_by_criteria)
                })
                
                # Complete extraction stage
                self.context.complete_stage("evidence_extraction", {
                    "total_evidence": evidence_count,
                    "criteria_with_evidence": len(evidence_by_criteria)
                })
            except Exception as e:
                self.logger.error(f"Evidence extraction failed: {str(e)}", exc_info=True)
                self.context.fail_stage("evidence_extraction", f"Error: {str(e)}")
                self.context.add_warning(f"Evidence extraction failed: {str(e)}")
                # Continue with evaluation even if extraction had issues
            
            # Run evaluator
            self.context.set_stage("criterion_evaluation")
            try:
                evaluation_results = await self._run_evaluator()
                self.context.complete_stage("criterion_evaluation", {"result": "success"})
            except Exception as e:
                self.logger.error(f"Evaluator failed: {str(e)}", exc_info=True)
                self.context.fail_stage("criterion_evaluation", f"Error: {str(e)}")
                self.context.add_warning(f"Evaluator failed: {str(e)}")
                # Create minimal evaluation results to continue
                evaluation_results = {
                    "status": "failed",
                    "error": str(e),
                    "message": "Evaluation failed, but continuing with available data"
                }
            
            # Update to dimension summarization phase
            self.context.set_stage("dimension_summarization")
            self.context.update_progress(0.5, "Summarizing dimension assessments")
            
            # Update to overall assessment phase
            self.context.set_stage("overall_assessment")
            self.context.update_progress(0.8, "Generating overall assessment")
            
            # Try to get assessment stats
            try:
                assessment_stats = self.context.get_assessment_stats()
                assessed_criteria_count = assessment_stats.get("assessed_criteria", 0)
                assessment_coverage = assessment_stats.get("assessment_coverage", 0)
                self.logger.info(
                    f"Assessment stats: {assessed_criteria_count} criteria assessed, "
                    f"{assessment_coverage:.1%} coverage"
                )
                
                # Add diagnostic checkpoint
                self.diagnostics["evidence_checks"].append({
                    "stage": "after_evaluation",
                    "time": time.time() - execution_start,
                    "assessed_criteria": assessed_criteria_count,
                    "coverage": assessment_coverage
                })
                
                self.context.complete_stage("overall_assessment", {"result": "success"})
            except Exception as e:
                self.logger.error(f"Error getting assessment stats: {str(e)}")
                self.context.add_warning(f"Error getting assessment stats: {str(e)}")
            
            # Run reporter
            self.context.set_stage("report_generation")
            try:
                report_results = await self._run_reporter()
                self.context.complete_stage("report_generation", {"result": "success"})
            except Exception as e:
                self.logger.error(f"Reporter failed: {str(e)}", exc_info=True)
                self.context.fail_stage("report_generation", f"Error: {str(e)}")
                self.context.add_warning(f"Reporter failed: {str(e)}")
                # Create minimal report results to continue
                report_results = {
                    "status": "failed",
                    "error": str(e),
                    "formats": {}
                }
            
            # Update to report compilation phase
            self.context.set_stage("report_compilation")
            self.context.update_progress(0.9, "Compiling final assessment outputs")
            
            # Create consolidated output
            ui_result = self._consolidate_results(evaluation_results, report_results, self.strategy)
            
            # Final diagnostic check
            final_evidence = self.context.get_evidence_count()
            self.logger.info(f"Final evidence count: {final_evidence}")
            
            # Calculate total execution time
            execution_time = time.time() - execution_start
            self.logger.info(f"Assessment execution completed in {execution_time:.2f}s with {final_evidence} evidence items")
            
            # Add diagnostics to result
            ui_result["diagnostics"] = self.diagnostics
            
            # Complete final stage
            self.context.complete_stage("report_compilation", {"result": "success"})
            
            return ui_result
                
        except Exception as e:
            self.stop_timer()
            self.logger.error(f"Error during assessment execution: {str(e)}", exc_info=True)
            
            # Create error result using consistent format
            error_result = self._consolidate_results(
                evaluation_results or {},
                report_results or {},
                self.strategy or {}
            )
            
            # Add error information
            error_result["status"] = "failed"
            error_result["error"] = str(e)
            error_result["diagnostics"] = self.diagnostics
            
            return error_result

    def _consolidate_results(self, evaluation_results, report_results, strategy):
        """
        Consolidate all results into a single, consistent output structure.
        This ensures we only have ONE output format regardless of how we got there.
        """
        # Start with a clean base structure
        final_result = {
            "scorecard": {},
            "reports": {"formats": {}},
            "metadata": {},
            "statistics": {},
            "warnings": [],
            "errors": [],
            "strategy": strategy or {}
        }
        
        # Get basic assessment stats if available
        try:
            final_result["statistics"] = self.context.get_assessment_stats()
        except Exception as e:
            self.logger.warning(f"Could not get assessment stats: {str(e)}")
            # Create minimal stats
            final_result["statistics"] = {
                "total_criteria": 0,
                "assessed_criteria": 0,
                "assessment_coverage": 0,
                "assessment_types": {"direct": 0, "inferred": 0, "insufficient_evidence": 0}
            }
        
        # Try different sources for the scorecard
        if report_results and "formats" in report_results and "scorecard" in report_results["formats"]:
            # Reporter produced a scorecard - use it as primary
            final_result["scorecard"] = report_results["formats"]["scorecard"]
            final_result["reports"]["formats"]["scorecard"] = report_results["formats"]["scorecard"]
        elif isinstance(evaluation_results, dict) and evaluation_results:
            # Use evaluator results if available
            final_result["scorecard"] = evaluation_results
            final_result["reports"]["formats"]["scorecard"] = evaluation_results
        
        # Add other report formats if available
        if report_results and "formats" in report_results:
            for format_name, format_data in report_results["formats"].items():
                if format_name != "scorecard" or "scorecard" not in final_result["reports"]["formats"]:
                    final_result["reports"]["formats"][format_name] = format_data
        
        # Add metadata
        try:
            # Try to get metadata from context
            if hasattr(self.context, "get_final_result"):
                context_result = self.context.get_final_result()
                if "metadata" in context_result:
                    final_result["metadata"] = context_result["metadata"]
            
            # Fall back to basic metadata if needed
            if not final_result["metadata"]:
                final_result["metadata"] = {
                    "framework_id": self.context.framework.get("id", "unknown"),
                    "framework_name": self.context.framework.get("name", "Unknown Framework"),
                    "document_name": self.context.options.get("document_name", "Unknown Document"),
                    "document_type": self.document.document_type,
                    "entity_name": self.document.primary_entity.get("name", "unknown"),
                    "entity_type": self.document.primary_entity.get("type", "unknown"),
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            self.logger.warning(f"Error generating metadata: {str(e)}")
        
        # Include warnings and errors
        try:
            final_result["warnings"] = self.context.data.get("operations", {}).get("warnings", [])
            final_result["errors"] = self.context.data.get("operations", {}).get("errors", [])
        except Exception as e:
            self.logger.warning(f"Error retrieving warnings/errors: {str(e)}")

        # Ensure assessment types match rationales
        if "scorecard" in final_result and "dimensions" in final_result["scorecard"]:
            for dimension in final_result["scorecard"]["dimensions"]:
                if "criteria" in dimension:
                    for criterion in dimension["criteria"]:
                        # Check for inferred rationales with incorrect assessment types
                        if "rationale" in criterion and "assessment_type" in criterion:
                            if (criterion["rationale"].startswith("[INFERRED]") and 
                                criterion["assessment_type"] != "inferred"):
                                criterion["assessment_type"] = "inferred"
                                self.logger.info(
                                    f"Fixed assessment type for criterion {criterion.get('id', 'unknown')}: "
                                    f"Changed to 'inferred' based on rationale starting with [INFERRED]"
                                )
                        
                        # CRITICAL FIX: Handle None ratings to prevent format errors
                        if "rating" in criterion and criterion["rating"] is None:
                            # Set assessment_type to insufficient_evidence if not already set
                            if "assessment_type" not in criterion or criterion["assessment_type"] == "direct":
                                criterion["assessment_type"] = "insufficient_evidence"
                                self.logger.info(
                                    f"Updated assessment_type for criterion {criterion.get('id', 'unknown')} "
                                    f"with None rating to 'insufficient_evidence'"
                                )
        
        return final_result

    
    def _get_evidence_packets_from_observations(self) -> List[Dict[str, Any]]:
        """
        Get evidence packets from context observations.
        
        Returns:
            List of evidence packets
        """
        packets = []
        
        # Get observations of type "evidence_packet"
        packet_observations = self.context.get_agent_observations(observation_type="evidence_packet")
        
        for obs in packet_observations:
            packet = obs.get("content")
            if packet:
                packets.append(packet)
        
        return packets
    
    async def _process_chunking(self) -> List[Dict[str, Any]]:
        """
        Process document chunking according to strategy.
        
        Returns:
            List of document chunks
        """
        chunking_strategy = self.strategy.get("chunking_strategy", {})
        method = chunking_strategy.get("method", "fixed_size")
        size = chunking_strategy.get("size", 8000)
        overlap = chunking_strategy.get("overlap", 200)
        
        self.logger.info(f"Processing document chunking with method={method}, size={size}, overlap={overlap}")
        
        # Initialize chunker
        from core.processors.chunker import Chunker
        chunker = Chunker(self.document.text)
        
        # Process chunking
        if method == "paragraph":
            chunks = chunker.chunk_by_paragraphs(size // 100, overlap_paragraphs=2)
        elif method == "semantic":
            chunks = chunker.chunk_for_assessment("auto", max_tokens_per_chunk=size)
        else:  # Default to fixed_size
            chunks = chunker.chunk_by_fixed_size(size, overlap)
        
        self.logger.info(f"Document chunking completed, generated {len(chunks)} chunks")
        return chunks
    
    async def _run_extractors_with_packets(
        self, 
        evidence_packets: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run extractors based on evidence packets.
        
        Args:
            evidence_packets: List of evidence packets for extraction
            chunks: Document chunks to process
            
        Returns:
            Combined extraction results
        """
        self.logger.info(f"Running extractors with {len(evidence_packets)} evidence packets")
        
        # Get extractor configurations from strategy
        extractor_configs = []
        for agent in self.strategy.get("agents", []):
            if self._is_extractor(agent.get("agent_type", "")):
                extractor_configs.append(agent)
        
        # If no extractor configs found, create from evidence packets
        if not extractor_configs and evidence_packets:
            for i, packet in enumerate(evidence_packets):
                extractor_configs.append({
                    "agent_type": f"extractor_{i+1}",
                    "configuration": {
                        "criteria_ids": packet.get("criteria_ids", []),
                        "min_confidence": packet.get("confidence_threshold", 0.2)
                    },
                    "instructions": packet.get("extraction_instructions", "")
                })
        
        # Track results for all extractors
        all_results = []
        
        # Run extractors with concurrency control
        max_concurrent = min(self.options.get("max_concurrent", 3), len(extractor_configs))
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create tasks for all extractors
        tasks = []
        
        for i, config in enumerate(extractor_configs):
            # Find matching packet for this config
            packet = self._find_matching_packet(config, evidence_packets, i)
            
            # Create task with concurrency control
            task = self._run_extractor_with_semaphore(
                semaphore, config, packet, chunks, i)
            
            tasks.append(task)
        
        # Run all extractors with concurrency control
        extractor_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle any exceptions
        for i, result in enumerate(extractor_results):
            if isinstance(result, Exception):
                self.logger.error(f"Extractor {i+1} failed: {str(result)}")
                self.context.add_warning(f"Extractor {i+1} failed: {str(result)}")
                # Add empty result for this extractor
                all_results.append({
                    "by_chunk": {},
                    "by_criterion": {},
                    "total_evidence": 0,
                    "error": str(result)
                })
            else:
                all_results.append(result)
                self.logger.info(f"Extractor {i+1} completed successfully")
        
        # Combine results
        combined_results = self._combine_extractor_results(all_results)
        
        return combined_results
    
    def _find_matching_packet(
        self, 
        config: Dict[str, Any], 
        evidence_packets: List[Dict[str, Any]], 
        index: int
    ) -> Optional[Dict[str, Any]]:
        """
        Find the evidence packet that matches an extractor config.
        
        Args:
            config: Extractor configuration
            evidence_packets: Available evidence packets
            index: Index of the extractor
            
        Returns:
            Matching evidence packet or None
        """
        if not evidence_packets:
            return None
            
        # Get criteria IDs from config
        config_criteria_ids = config.get("configuration", {}).get("criteria_ids", [])
        
        # Try to find exact match by criteria IDs
        for packet in evidence_packets:
            packet_criteria_ids = packet.get("criteria_ids", [])
            if set(config_criteria_ids) == set(packet_criteria_ids):
                return packet
        
        # If no match, use the packet with the same index if possible
        if index < len(evidence_packets):
            return evidence_packets[index]
        
        # Otherwise use the first packet
        return evidence_packets[0]
    
    async def _run_extractor_with_semaphore(
        self, 
        semaphore: asyncio.Semaphore,
        config: Dict[str, Any],
        packet: Optional[Dict[str, Any]],
        chunks: List[Dict[str, Any]],
        index: int
    ) -> Dict[str, Any]:
        """
        Run extractor with concurrency control.
        
        Args:
            semaphore: Semaphore for concurrency control
            config: Extractor configuration
            packet: Evidence packet
            chunks: Document chunks
            index: Extractor index
            
        Returns:
            Extraction result
        """
        async with semaphore:
            try:
                # Update configuration with packet info if available
                if packet:
                    config_with_packet = dict(config)
                    if "configuration" not in config_with_packet:
                        config_with_packet["configuration"] = {}
                    
                    config_with_packet["configuration"]["evidence_packet"] = packet
                    
                    # Ensure instructions are set
                    if not config_with_packet.get("instructions") and packet.get("extraction_instructions"):
                        config_with_packet["instructions"] = packet["extraction_instructions"]
                else:
                    config_with_packet = config
                
                # Create extractor
                extractor = ExtractorAgent(
                    self.llm,
                    self.context,
                    name=f"Extractor_{index+1}",
                    options=config_with_packet
                )
                
                # Store agent for later reference
                self.agents[f"extractor_{index+1}"] = extractor
                
                # Process chunks
                self.logger.info(f"Starting Extractor_{index+1}")
                result = await extractor.process(chunks)
                
                # Log evidence count
                evidence_count = self.context.get_evidence_count()
                self.logger.info(f"Extractor_{index+1} complete. Current evidence count: {evidence_count}")
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error in Extractor_{index+1}: {str(e)}", exc_info=True)
                raise
    
    def _combine_extractor_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine results from multiple extractors.
        
        Args:
            results: List of results from each extractor
            
        Returns:
            Combined results
        """
        combined = {
            "by_chunk": {},
            "by_criterion": {},
            "total_evidence": 0,
            "evidence_categories": {},
            "extractors": len(results),
            "successful_extractors": 0
        }
        
        # Track criteria that received evidence
        criteria_with_evidence = set()
        
        # Process each extractor's results
        for i, result in enumerate(results):
            # Skip failed extractors
            if "error" in result:
                continue
                
            combined["successful_extractors"] += 1
            
            # Combine chunk results
            for chunk_id, chunk_data in result.get("by_chunk", {}).items():
                if chunk_id not in combined["by_chunk"]:
                    combined["by_chunk"][chunk_id] = {
                        "chunk_id": chunk_id,
                        "evidence": [],
                        "evidence_count": 0
                    }
                
                # Add evidence to combined results
                combined["by_chunk"][chunk_id]["evidence"].extend(chunk_data.get("evidence", []))
                combined["by_chunk"][chunk_id]["evidence_count"] += chunk_data.get("evidence_count", 0)
            
            # Combine criterion results
            for criterion_key, evidence_list in result.get("by_criterion", {}).items():
                if criterion_key not in combined["by_criterion"]:
                    combined["by_criterion"][criterion_key] = []
                
                combined["by_criterion"][criterion_key].extend(evidence_list)
                
                # Track criteria that received evidence
                if evidence_list:
                    criteria_with_evidence.add(criterion_key)
            
            # Add to total evidence count
            combined["total_evidence"] += result.get("total_evidence", 0)
            
            # Add consolidated evidence if available
            if "consolidated_evidence" in result:
                for criterion_key, consolidated_data in result["consolidated_evidence"].items():
                    if "consolidated_evidence" not in combined:
                        combined["consolidated_evidence"] = {}
                    combined["consolidated_evidence"][criterion_key] = consolidated_data
                    
                    # Track evidence categories
                    if "evidence_by_category" in consolidated_data:
                        for category, count in consolidated_data["evidence_by_category"].items():
                            if category not in combined["evidence_categories"]:
                                combined["evidence_categories"][category] = 0
                            combined["evidence_categories"][category] += count
        
        # Add criteria with evidence to results
        combined["criteria_with_evidence"] = list(criteria_with_evidence)
        combined["criteria_with_evidence_count"] = len(criteria_with_evidence)
        
        self.logger.info(
            f"Combined results from {combined['successful_extractors']}/{combined['extractors']} extractors: "
            f"{combined['total_evidence']} total evidence items for {len(criteria_with_evidence)} criteria"
        )
        
        if criteria_with_evidence:
            criteria_list = list(criteria_with_evidence)
            # Only log first 5 to avoid excessively long logs
            self.logger.info(f"Sample criteria with evidence: {', '.join(criteria_list[:5])}" +
                           ("..." if len(criteria_list) > 5 else ""))
        
        return combined
    
    def _track_evidence_by_criteria(self) -> Dict[str, int]:
        """
        Track evidence counts by criteria after extraction.
        
        Returns:
            Dictionary mapping criteria IDs to evidence counts
        """
        evidence_by_criteria = {}
        
        # Go through all dimensions and criteria
        for dimension in self.context.framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                
                if dimension_id and criterion_id:
                    # Get evidence count
                    count = self.context.get_evidence_count(dimension_id, criterion_id)
                    
                    if count > 0:
                        evidence_by_criteria[f"{dimension_id}:{criterion_id}"] = count
        
        # Record observation for diagnostics
        self.context.record_agent_observation(
            "executor", 
            "evidence_by_criteria",
            evidence_by_criteria
        )
        
        return evidence_by_criteria
    
    async def _run_evaluator(self) -> Dict[str, Any]:
        """
        Run evaluator to assess criteria based on evidence.
        
        Returns:
            Evaluation results
        """
        self.logger.info("Running evaluator")
        
        # Get evaluator configuration from strategy
        evaluator_config = None
        for agent in self.strategy.get("agents", []):
            if agent.get("agent_type", "").lower() == "evaluator":
                evaluator_config = agent
                break
        
        if not evaluator_config:
            self.logger.warning("No evaluator configuration found in strategy, using default")
            evaluator_config = {
                "agent_type": "evaluator",
                "configuration": {
                    "evaluation_type": "structured",
                    "confidence_threshold": 0.5,
                    "infer_missing": True,
                    "output_format": "scorecard"
                },
                "instructions": "Evaluate criteria based on evidence."
            }
        
        # Create evaluator
        evaluator = EvaluatorAgent(
            self.llm,
            self.context,
            name="Evaluator",
            options=evaluator_config
        )
        
        # Store agent for later reference
        self.agents["evaluator"] = evaluator
        
        # Process evaluation
        results = await evaluator.process()
        
        # Record observation for diagnostics
        assessment_stats = self.context.get_assessment_stats()
        self.context.record_agent_observation(
            "executor", 
            "evaluation_stats",
            assessment_stats
        )
        
        self.logger.info(
            f"Evaluation complete: {assessment_stats.get('assessed_criteria', 0)} criteria assessed, "
            f"{assessment_stats.get('assessment_coverage', 0):.1%} coverage"
        )
        
        return results
    
    async def _run_reporter(self) -> Dict[str, Any]:
        """
        Run reporter to generate assessment reports.
        
        Returns:
            Report results
        """
        self.logger.info("Running reporter")
        
        # Get reporter configuration from strategy
        reporter_config = None
        for agent in self.strategy.get("agents", []):
            if agent.get("agent_type", "").lower() == "reporter":
                reporter_config = agent
                break
        
        if not reporter_config:
            self.logger.warning("No reporter configuration found in strategy, using default")
            reporter_config = {
                "agent_type": "reporter",
                "configuration": {
                    "report_type": self.options.get("report_type", "scorecard"),
                    "include_evidence": True,
                    "include_confidence": True,
                    "include_assessment_types": True
                },
                "instructions": "Create reports from evaluations."
            }
        
        # Create reporter
        reporter = ReporterAgent(
            self.llm,
            self.context,
            name="Reporter",
            options=reporter_config
        )
        
        # Store agent for later reference
        self.agents["reporter"] = reporter
        
        # Generate reports
        results = await reporter.process()
        
        self.logger.info("Reports generated successfully")
        
        return results
    
    async def _format_result_for_ui(
        self, 
        evaluation_results: Dict[str, Any],
        report_results: Dict[str, Any],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format results for UI display.
        
        Args:
            evaluation_results: Evaluation results
            report_results: Report results
            strategy: Assessment strategy
            
        Returns:
            UI-ready results
        """
        # Check if reporter has format_for_ui method
        if "reporter" in self.agents:
            reporter = self.agents["reporter"]
            if hasattr(reporter, "format_for_ui"):
                try:
                    ui_result = await reporter.format_for_ui()
                    
                    # Add strategy information
                    ui_result["strategy"] = strategy
                    
                    # Add diagnostics
                    ui_result["diagnostics"] = self.diagnostics
                    
                    return ui_result
                except Exception as e:
                    self.logger.error(f"Error using reporter's format_for_ui: {str(e)}")
                    # Fall back to manual formatting
        
        # Fallback: manually format results
        
        # Use reports format if available
        if "formats" in report_results:
            ui_result = {
                "scorecard": report_results.get("formats", {}).get("scorecard", {}),
                "reports": report_results,
                "metadata": report_results.get("metadata", {}),
                "statistics": self.context.get_assessment_stats(),
                "warnings": self.context.data.get("operations", {}).get("warnings", []),
                "errors": self.context.data.get("operations", {}).get("errors", []),
                "strategy": strategy
            }
        else:
            # Basic format if reports not available
            ui_result = {
                "scorecard": evaluation_results,
                "reports": {
                    "formats": {
                        "scorecard": evaluation_results
                    }
                },
                "metadata": {},
                "statistics": self.context.get_assessment_stats(),
                "warnings": self.context.data.get("operations", {}).get("warnings", []),
                "errors": self.context.data.get("operations", {}).get("errors", []),
                "strategy": strategy
            }
        
        # Add diagnostics
        ui_result["diagnostics"] = self.diagnostics
        
        return ui_result
    
    def stop_timer(self):
        """Stop execution timer for diagnostics."""
        self.diagnostics["execution_end"] = time.time()
        self.diagnostics["execution_time"] = self.diagnostics["execution_end"] - self.diagnostics["execution_start"]
    
    def _is_extractor(self, agent_type: str) -> bool:
        """
        Check if an agent type is an extractor.
        
        Args:
            agent_type: Agent type string
            
        Returns:
            True if agent is an extractor
        """
        return agent_type.lower().startswith("extractor")