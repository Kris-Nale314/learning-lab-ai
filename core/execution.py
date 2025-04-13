"""
Fixed Strategy Executor - Executes assessment strategies with parallel extractors

This module implements the StrategyExecutor class with support for deploying
multiple specialized extractors in parallel for improved performance.
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
    Executes assessment strategies by orchestrating agents and processors.
    
    The Strategy Executor is responsible for:
    1. Running the Meta Planner to design strategies
    2. Configuring and deploying agents according to strategy
    3. Managing parallel extractor instances
    4. Tracking resources and adapting as needed
    5. Providing execution status and results
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
            Assessment results
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
            
            # Get final assessment result
            result = self.context.get_final_result()
            self.logger.info("Assessment execution completed successfully")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during assessment execution: {str(e)}", exc_info=True)
            # Get partial results if available
            partial_result = self.context.get_final_result()
            partial_result["error"] = str(e)
            partial_result["status"] = "failed"
            
            return partial_result
    
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