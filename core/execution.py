"""
Enhanced Strategy Executor - Executes assessment strategies with consistent UI output

This module implements the StrategyExecutor class with improved result formatting
and standardized output structure for reliable frontend integration.
"""

import logging
import json, re, os
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Type

# Import agents
from core.agents.base import BaseAgent
from core.agents.meta_planner import MetaPlannerAgent
from core.agents.extractor import ExtractorAgent
from core.agents.evaluator import EvaluatorAgent
from core.agents.reporter import ReporterAgent

# Import other components
from core.context import AssessmentContext
from core.models.document import Document
from core.processors.chunker import Chunker

# Import utilities
import sys
import os
# Ensure utils is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import path_utils

class StrategyExecutor:
    """
    Executes assessment strategies by orchestrating agents and processors,
    with standardized output for reliable UI integration.
    
    The Strategy Executor is responsible for:
    1. Running the Meta Planner to design strategies
    2. Configuring and deploying agents according to strategy
    3. Managing parallel extractor instances
    4. Tracking resources and adapting as needed
    5. Providing execution status and results
    6. Formatting results in a UI-ready structure
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
        
        # Initialize context
        self.context = AssessmentContext(document.text, framework, self.options)
        
        # Set up logging
        self.logger = logging.getLogger("learning-lab-ai.processor.execution")
        self.logger.info(f"Strategy executor initialized for document: {document.filename}")
    
    async def plan(self) -> Dict[str, Any]:
        """
        Run the Meta Planner to design an assessment strategy.
        
        Returns:
            Assessment strategy
        """
        self.logger.info("Running Meta Planner to design strategy")
        
        # Set planning stage
        self.context.set_stage("planning")
        
        # Initialize Meta Planner
        meta_planner = MetaPlannerAgent(self.llm, self.context)
        
        # Design strategy
        self.strategy = await meta_planner.process()
        
        # Complete planning stage
        self.context.complete_stage("planning", {"strategy": self.strategy})
        
        return self.strategy
    
    async def execute(self, strategy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the assessment process from start to finish.
        
        Args:
            strategy: Optional strategy to use (if not provided, uses the result of plan())
            
        Returns:
            UI-ready assessment results
        """
        try:
            self.logger.info("Starting assessment execution")
            
            # Use provided strategy or run planner
            if strategy:
                self.strategy = strategy
            elif not self.strategy:
                self.strategy = await self.plan()
            
            # Process document chunking
            self.context.set_stage("chunking")
            chunks = await self._process_chunking()
            self.context.set_chunks(chunks)
            self.document.set_chunks(chunks)
            self.context.complete_stage("chunking", {"chunk_count": len(chunks)})
            
            # Deploy and run agents according to strategy
            processing_sequence = self.strategy.get("processing_sequence", [])
            
            # Process each agent type in sequence
            unique_agent_types = []
            for agent_type in processing_sequence:
                normalized_type = self._normalize_agent_type(agent_type)
                if normalized_type not in unique_agent_types:
                    unique_agent_types.append(normalized_type)
            
            # Execute each unique agent type in sequence
            for agent_type in unique_agent_types:
                if agent_type == 'extractor':
                    await self._deploy_and_run_extractors()
                else:
                    await self._deploy_and_run_agent(agent_type)
            
            # Get raw assessment result
            raw_result = self.context.get_final_result()
            
            # Format for UI display
            ui_result = await self._format_result_for_ui(raw_result)
            
            self.logger.info("Assessment execution completed successfully")
            
            return ui_result
            
        except Exception as e:
            self.logger.error(f"Error during assessment execution: {str(e)}", exc_info=True)
            # Create error result in UI-ready format
            error_result = {
                "error": str(e),
                "status": "failed",
                "scorecard": {},
                "reports": {"formats": {}},
                "warnings": self.context.data.get("warnings", []),
                "errors": self.context.data.get("errors", []) + [{"message": str(e), "stage": "execution"}]
            }
            
            return error_result
    
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
    
    async def _deploy_and_run_extractors(self) -> Dict[str, Any]:
        """
        Deploy and run multiple extractor agents in parallel.
        
        Returns:
            Combined extractor results
        """
        self.logger.info("Deploying parallel extractor agents")
        
        # Set extractor processing stage
        stage_name = "extractor_processing"
        self.context.set_stage(stage_name)
        
        # Find all extractor configs from strategy
        extractor_configs = []
        for agent in self.strategy.get("agents", []):
            agent_type = agent.get("agent_type", "")
            # Check if this is any kind of extractor
            if self._normalize_agent_type(agent_type) == 'extractor':
                extractor_configs.append(agent)
        
        if not extractor_configs:
            raise ValueError("No extractor configurations found in strategy")
        
        self.logger.info(f"Found {len(extractor_configs)} extractor configurations")
        
        # Create and run extractors in parallel
        extractor_tasks = []
        
        for i, config in enumerate(extractor_configs):
            # Create agent options
            agent_options = {
                **config.get("configuration", {}),
                "instructions": config.get("instructions", ""),
                "strategy": self.strategy
            }
            
            # Create extractor with unique name
            extractor_name = f"Extractor_{i+1}"
            if "agent_type" in config and config["agent_type"] != "extractor":
                # Use the specialized name if available
                extractor_name = f"{extractor_name}_{config['agent_type']}"
            
            extractor = ExtractorAgent(
                self.llm, 
                self.context, 
                name=extractor_name, 
                options=agent_options
            )
            
            # Store the agent for later reference
            self.agents[extractor_name] = extractor
            
            # Create task
            task = extractor.process()
            extractor_tasks.append(task)
        
        # Run all extractors in parallel
        self.logger.info(f"Running {len(extractor_tasks)} extractors in parallel")
        extractor_results = await asyncio.gather(*extractor_tasks)
        
        # Combine results
        combined_results = self._combine_extractor_results(extractor_results)
        
        # Complete stage
        self.context.complete_stage(stage_name, {
            "extractor_count": len(extractor_configs),
            "evidence_count": combined_results.get("total_evidence", 0)
        })
        
        return combined_results
    
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
            "total_evidence": 0
        }
        
        # Process each extractor's results
        for result in results:
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
            
            # Add to total evidence count
            combined["total_evidence"] += result.get("total_evidence", 0)
        
        self.logger.info(f"Combined results from {len(results)} extractors: {combined['total_evidence']} total evidence items")
        return combined
            
    async def _deploy_and_run_agent(self, agent_type: str) -> Dict[str, Any]:
        """
        Deploy and run a single agent according to strategy.
        
        Args:
            agent_type: Type of agent to deploy
            
        Returns:
            Agent processing results
        """
        # Normalize agent type name (handle case differences)
        normalized_agent_type = self._normalize_agent_type(agent_type)
        
        # Get agent configuration from strategy
        agent_config = None
        for agent in self.strategy.get("agents", []):
            agent_normalized_type = self._normalize_agent_type(agent.get("agent_type", ""))
            if agent_normalized_type == normalized_agent_type:
                agent_config = agent
                break
        
        if not agent_config:
            # Look for any agent with this base type regardless of specialization
            for agent in self.strategy.get("agents", []):
                agent_base_type = self._normalize_agent_type(agent.get("agent_type", ""))
                if agent_base_type == normalized_agent_type:
                    agent_config = agent
                    break
        
        if not agent_config:
            raise ValueError(f"Agent type '{agent_type}' not found in strategy")
        
        # Set stage in context
        stage_name = f"{normalized_agent_type}_processing"
        self.context.set_stage(stage_name)
        
        # Create agent options
        agent_options = {
            **agent_config.get("configuration", {}),
            "instructions": agent_config.get("instructions", ""),
            "strategy": self.strategy
        }
        
        # Initialize agent
        agent = self._create_agent(normalized_agent_type, agent_options)
        
        # Store the agent for later reference
        self.agents[normalized_agent_type] = agent
        
        # Run agent
        self.logger.info(f"Running {normalized_agent_type} agent")
        result = await agent.process()
        
        # Complete stage
        self.context.complete_stage(stage_name, {"result": result})
        
        return result
    
    def _normalize_agent_type(self, agent_type: str) -> str:
        """
        Normalize agent type name to handle case differences and specializations.
        
        Args:
            agent_type: Original agent type name
            
        Returns:
            Normalized agent type name
        """
        # Convert to lowercase
        normalized = agent_type.lower()
        
        # Extract base agent type, ignoring specializations in parentheses
        base_type_match = re.match(r'^(\w+).*$', normalized)
        if base_type_match:
            base_type = base_type_match.group(1)
        else:
            base_type = normalized
        
        # Map to standard agent types
        if base_type in ['extractor', 'extract']:
            return 'extractor'
        elif base_type in ['evaluator', 'evaluate']:
            return 'evaluator'
        elif base_type in ['reporter', 'report']:
            return 'reporter'
        else:
            return base_type
    
    def _create_agent(self, agent_type: str, options: Dict[str, Any]) -> BaseAgent:
        """
        Create an agent instance.
        
        Args:
            agent_type: Type of agent to create
            options: Agent configuration options
            
        Returns:
            Agent instance
        """
        # Map normalized agent type to agent class
        if agent_type == 'extractor':
            return ExtractorAgent(self.llm, self.context, options=options)
        elif agent_type == 'evaluator':
            return EvaluatorAgent(self.llm, self.context, options=options)
        elif agent_type == 'reporter':
            return ReporterAgent(self.llm, self.context, options=options)
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")
    
    async def get_strategy_preview(self) -> Dict[str, Any]:
        """
        Get a preview of the assessment strategy for user review.
        
        Returns:
            Strategy preview with human-readable explanations
        """
        if not self.strategy:
            self.strategy = await self.plan()
        
        # Count extractors by type
        extractor_counts = {}
        for agent in self.strategy.get("agents", []):
            agent_type = agent.get("agent_type", "")
            if self._normalize_agent_type(agent_type) == 'extractor':
                extractor_counts[agent_type] = extractor_counts.get(agent_type, 0) + 1
        
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
            "extractors": extractor_counts,
            "total_extractors": sum(extractor_counts.values()),
            "agents": [],
            "processing_sequence": self.strategy.get("processing_sequence", []),
            "estimated_tokens": self.strategy.get("token_allocation", {}).get("total_estimated", 0)
        }
        
        # Add agent details
        for agent in self.strategy.get("agents", []):
            agent_preview = {
                "type": agent.get("agent_type", "unknown"),
                "configuration": agent.get("configuration", {}),
                "instructions": agent.get("instructions", "")
            }
            preview["agents"].append(agent_preview)
        
        return preview
    
    async def get_ui_ready_results(self) -> Dict[str, Any]:
        """
        Get assessment results formatted for UI display.
        Uses the ReporterAgent's format_for_ui method if available,
        or formats raw results if no reporter is available.
        
        Returns:
            UI-ready assessment results
        """
        # Execute if not already done
        if not hasattr(self.context, "data") or not self.context.data.get("overall_assessment"):
            await self.execute()
            
        # Format for UI
        raw_result = self.context.get_final_result()
        ui_result = await self._format_result_for_ui(raw_result)
        
        return ui_result
        
    async def _format_result_for_ui(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw assessment result for UI display.
        
        Args:
            raw_result: Raw assessment result from context
            
        Returns:
            UI-ready assessment result with standardized structure
        """
        # Instead of using reporter_agent.format_for_ui(), we'll work directly with the data
        
        # Check if a reporter has been run and its results are in the raw_result
        reports_data = {}
        if "reports" in raw_result:
            reports_data = raw_result.get("reports", {})
        elif hasattr(self.context, "data") and "reports" in self.context.data:
            reports_data = self.context.data.get("reports", {})
        
        # Construct scorecard
        scorecard = self._extract_scorecard(raw_result)
        
        # Create visualization data
        visualization_data = self._create_visualization_data(raw_result)
        
        # Create evidence report if evidence exists
        evidence_report = self._create_evidence_report(raw_result) if raw_result.get("evidence") else None
        
        # Build UI-ready format
        ui_result = {
            # Top-level scorecard for easy access
            "scorecard": scorecard,
            
            # Reports section with all formats
            "reports": {
                "formats": {
                    "scorecard": scorecard,
                    "visualization_data": visualization_data
                }
            },
            
            # Metadata
            "metadata": raw_result.get("metadata", {}),
            
            # Statistics
            "statistics": raw_result.get("statistics", {}),
            
            # Include warnings/errors
            "warnings": raw_result.get("warnings", []),
            "errors": raw_result.get("errors", [])
        }
        
        # Add evidence report if available
        if evidence_report:
            ui_result["reports"]["formats"]["evidence_report"] = evidence_report
        
        # Add any reports from the reporter if they exist
        for report_type, report_data in reports_data.get("formats", {}).items():
            if report_type not in ui_result["reports"]["formats"]:
                ui_result["reports"]["formats"][report_type] = report_data
        
        return ui_result

    def _extract_scorecard(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract scorecard from raw_result, checking multiple possible locations."""
        # Check several possible locations for the scorecard
        if "reports" in raw_result:
            if "formats" in raw_result["reports"] and "scorecard" in raw_result["reports"]["formats"]:
                return raw_result["reports"]["formats"]["scorecard"]
            elif "scorecard" in raw_result["reports"]:
                return raw_result["reports"]["scorecard"]
        
        # Fall back to constructing a scorecard from dimensions and overall assessment
        return self._construct_scorecard_from_raw_result(raw_result)
        
    def _construct_scorecard_from_raw_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construct a scorecard from raw assessment result.
        
        Args:
            result: Raw assessment result
            
        Returns:
            Structured scorecard for UI display
        """
        # Get overall assessment
        overall_assessment = result.get("overall_assessment", {})
        
        # Initialize dimensions list for scorecard
        dimensions = []
        
        # Process each dimension
        assessments = result.get("assessments", {})
        for dimension_id, dimension_data in assessments.items():
            if dimension_id == "overall_assessment":
                continue
                
            # Get dimension metadata
            dimension_name = dimension_id
            for dim in result.get("framework", {}).get("dimensions", []):
                if dim.get("id") == dimension_id:
                    dimension_name = dim.get("name", dimension_id)
                    break
            
            # Get dimension summary
            dimension_summary = dimension_data.get("summary", {})
            if not dimension_summary:
                continue
                
            # Initialize criteria list for this dimension
            criteria = []
            
            # Process each criterion
            criteria_assessments = dimension_data.get("criteria", {})
            for criterion_id, criterion_data in criteria_assessments.items():
                if criterion_data.get("rating") is None:
                    continue
                    
                # Find criterion name
                criterion_name = criterion_id
                for dim in result.get("framework", {}).get("dimensions", []):
                    if dim.get("id") == dimension_id:
                        for crit in dim.get("criteria", []):
                            if crit.get("id") == criterion_id:
                                criterion_name = crit.get("name", criterion_id)
                                break
                
                # Create criterion entry
                criterion_entry = {
                    "id": criterion_id,
                    "name": criterion_name,
                    "rating": criterion_data.get("rating"),
                    "rationale": criterion_data.get("rationale", ""),
                    "confidence": criterion_data.get("confidence")
                }
                
                # Get evidence
                evidence_ids = criterion_data.get("evidence_ids", [])
                if evidence_ids:
                    evidence_items = []
                    for evidence_id in evidence_ids:
                        if evidence_id in result.get("evidence", {}).get("items", {}):
                            evidence_items.append(result["evidence"]["items"][evidence_id])
                    
                    if evidence_items:
                        criterion_entry["evidence"] = evidence_items
                        criterion_entry["evidence_count"] = len(evidence_items)
                
                criteria.append(criterion_entry)
            
            # Add dimension entry
            dimension_entry = {
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": dimension_summary.get("average_rating"),
                "criteria": criteria,
                "strengths": dimension_summary.get("strengths", []),
                "weaknesses": dimension_summary.get("weaknesses", [])
            }
            
            dimensions.append(dimension_entry)
        
        # Create scorecard
        scorecard = {
            "title": f"Assessment Scorecard: {result.get('framework', {}).get('name', 'Assessment')}",
            "overall_rating": overall_assessment.get("average_rating"),
            "executive_summary": overall_assessment.get("executive_summary", ""),
            "key_strengths": overall_assessment.get("key_strengths", []),
            "key_improvements": overall_assessment.get("key_improvements", []),
            "recommendations": overall_assessment.get("recommendations", []),
            "dimensions": dimensions,
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0),
            "timestamp": overall_assessment.get("timestamp")
        }
        
        return scorecard
    
    def _create_visualization_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create visualization data from raw assessment result.
        
        Args:
            result: Raw assessment result
            
        Returns:
            Visualization data for UI display
        """
        # Get framework info
        framework = result.get("framework", {})
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = result.get("overall_assessment", {})
        
        # Generate radar chart data (dimension ratings)
        radar_data = []
        rating_distribution = {}
        evidence_distribution = []
        
        # Process dimensions
        for dimension_id, dimension_data in result.get("assessments", {}).items():
            if dimension_id == "overall_assessment":
                continue
                
            # Get dimension metadata
            dimension_name = dimension_id
            for dim in framework.get("dimensions", []):
                if dim.get("id") == dimension_id:
                    dimension_name = dim.get("name", dimension_id)
                    break
            
            # Get dimension summary
            dimension_summary = dimension_data.get("summary", {})
            if dimension_summary and dimension_summary.get("average_rating") is not None:
                radar_data.append({
                    "dimension": dimension_name,
                    "rating": dimension_summary.get("average_rating")
                })
            
            # Count evidence for this dimension
            dimension_evidence_count = 0
            for criterion_id, criterion_data in dimension_data.get("criteria", {}).items():
                # Count evidence
                evidence_ids = criterion_data.get("evidence_ids", [])
                dimension_evidence_count += len(evidence_ids)
                
                # Add to rating distribution
                rating = criterion_data.get("rating")
                if rating is not None:
                    rating_str = str(rating)
                    rating_distribution[rating_str] = rating_distribution.get(rating_str, 0) + 1
            
            # Add to evidence distribution
            evidence_distribution.append({
                "dimension": dimension_name,
                "evidence_count": dimension_evidence_count
            })
        
        # Create heatmap data
        heatmap_data = []
        for dimension_id, dimension_data in result.get("assessments", {}).items():
            if dimension_id == "overall_assessment":
                continue
                
            # Get dimension name
            dimension_name = dimension_id
            for dim in framework.get("dimensions", []):
                if dim.get("id") == dimension_id:
                    dimension_name = dim.get("name", dimension_id)
                    break
            
            # Process criteria
            for criterion_id, criterion_data in dimension_data.get("criteria", {}).items():
                if criterion_data.get("rating") is None:
                    continue
                    
                # Get criterion name
                criterion_name = criterion_id
                for dim in framework.get("dimensions", []):
                    if dim.get("id") == dimension_id:
                        for crit in dim.get("criteria", []):
                            if crit.get("id") == criterion_id:
                                criterion_name = crit.get("name", criterion_id)
                                break
                
                # Add to heatmap data
                heatmap_data.append({
                    "dimension": dimension_name,
                    "criterion": criterion_name,
                    "rating": criterion_data.get("rating"),
                    "confidence": criterion_data.get("confidence")
                })
        
        # Create visualization data
        visualization_data = {
            "title": f"Visualization Data: {framework_name}",
            "overall_rating": overall_assessment.get("average_rating"),
            "radar_chart": radar_data,
            "heatmap": heatmap_data,
            "evidence_distribution": evidence_distribution,
            "rating_distribution": rating_distribution,
            "criteria_coverage": {
                "assessed": overall_assessment.get("criteria_assessed", 0),
                "total": overall_assessment.get("criteria_total", 1),
                "percentage": overall_assessment.get("criteria_coverage", 0)
            },
            "key_metrics": {
                "dimensions": len(radar_data),
                "criteria_assessed": overall_assessment.get("criteria_assessed", 0),
                "total_evidence": result.get("statistics", {}).get("total_evidence", 0),
                "average_confidence": result.get("statistics", {}).get("average_confidence")
            }
        }
        
        return visualization_data
    
    def _create_evidence_report(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create evidence report from raw assessment result.
        
        Args:
            result: Raw assessment result
            
        Returns:
            Evidence report for UI display
        """
        # Get framework info
        framework = result.get("framework", {})
        framework_name = framework.get("name", "Assessment Framework")
        
        # Create evidence map by dimension/criterion
        evidence_map = {}
        
        # Process dimensions
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
            
            evidence_map[dimension_id] = {
                "name": dimension_name,
                "criteria": {}
            }
            
            # Process criteria
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                criterion_question = criterion.get("question", "")
                
                if not criterion_id:
                    continue
                
                # Get criterion key
                criterion_key = f"{dimension_id}:{criterion_id}"
                
                # Get evidence IDs for this criterion
                evidence_ids = (
                    result.get("evidence", {})
                    .get("by_criterion", {})
                    .get(criterion_key, [])
                )
                
                if not evidence_ids:
                    continue
                
                # Format evidence items
                formatted_evidence = []
                
                for evidence_id in evidence_ids:
                    evidence_item = (
                        result.get("evidence", {})
                        .get("items", {})
                        .get(evidence_id)
                    )
                    
                    if not evidence_item:
                        continue
                    
                    # Get metadata
                    metadata = evidence_item.get("metadata", {})
                    
                    # Create formatted evidence
                    formatted_item = {
                        "id": evidence_id,
                        "text": evidence_item.get("text", ""),
                        "relevance": metadata.get("relevance_explanation", ""),
                        "confidence": metadata.get("confidence"),
                        "relevance_level": metadata.get("relevance_level", "Direct")
                    }
                    
                    formatted_evidence.append(formatted_item)
                
                # Create criterion evidence
                evidence_map[dimension_id]["criteria"][criterion_id] = {
                    "name": criterion_name,
                    "question": criterion_question,
                    "evidence": formatted_evidence
                }
        
        # Get total evidence count
        total_evidence = sum(
            len(criterion_data["evidence"]) 
            for dimension_data in evidence_map.values() 
            for criterion_data in dimension_data["criteria"].values()
        )
        
        # Create introduction
        introduction = (
            f"## Evidence Report for {framework_name}\n\n"
            f"This report contains {total_evidence} pieces of evidence extracted from the document "
            f"across {len(evidence_map)} dimensions. Each piece of evidence is linked to specific "
            f"criteria and includes relevance explanations and confidence scores.\n\n"
            f"Evidence is organized by dimension and criterion to provide a comprehensive view "
            f"of how the document addresses each aspect of the assessment framework."
        )
        
        # Create evidence report
        evidence_report = {
            "title": f"Evidence Report: {framework_name}",
            "introduction": introduction,
            "evidence_map": evidence_map,
            "total_evidence": total_evidence
        }
        
        return evidence_report