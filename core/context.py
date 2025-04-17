"""
AssessmentContext - Enhanced shared context for Framework Assessment Workbench

This module provides an improved AssessmentContext class that serves as the central
data store and collaboration mechanism for all assessment agents, with enhanced
storage for document properties, entity information, and evidence.
"""

import uuid
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Set

# Configure logger
logger = logging.getLogger("learning-lab-ai.context")

class AssessmentContext:
    """
    Enhanced shared context for agent collaboration in framework assessment.
    
    The AssessmentContext serves as:
    1. Central data store for all assessment information
    2. Thread-safe collaboration mechanism for concurrent agents
    3. Structured storage for document properties and entity information
    4. Comprehensive evidence collection and organization system
    5. Support for post-assessment exploration and analysis
    """
    
    def __init__(
        self, 
        document_text: str, 
        framework: Dict[str, Any], 
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an assessment context.
        
        Args:
            document_text: The full text of the document being assessed
            framework: The assessment framework definition
            options: Optional configuration options
        """
        # Basic information
        self.document_text = document_text
        self.framework = framework
        self.options = options or {}
        self.run_id = str(uuid.uuid4())
        self.start_time = datetime.now(timezone.utc)
        
        # Add threading locks for concurrent operations
        self._evidence_lock = threading.RLock()
        self._assessment_lock = threading.RLock()
        self._progress_lock = threading.RLock()
        self._observation_lock = threading.RLock()
        self._strategy_lock = threading.RLock()
        
        # Processing state
        self.progress = 0.0
        self.status = "initialized"
        self.current_stage = None
        self.stages = {}
        
        # Document chunks
        self.chunks = []
        
        # Enhanced document properties
        self.document_properties = {
            "document_type": options.get("document_type", "unknown"),
            "document_structure": options.get("document_structure", "unknown"),
            "primary_entity": options.get("primary_entity", {"name": "unknown", "type": "unknown"}),
            "document_bias": options.get("document_bias", {"orientation": "neutral"}),
            "keywords": options.get("keywords", [])
        }
        
        # Main data store - organized by purpose
        self.data = {
            # Strategy and planning data
            "strategy": {
                "pipeline_design": {},            # Complete pipeline strategy
                "criteria_groups": [],            # Criteria grouping information
                "extraction_strategies": [],      # Extraction strategies
                "semantic_guidance": {}           # Semantic understanding of criteria
            },
            
            # Evidence storage and organization
            "evidence": {
                "items": {},                      # Evidence items by ID
                "by_criterion": {},               # Evidence IDs by criterion
                "by_chunk": {},                   # Evidence IDs by chunk
                "by_category": {},                # Evidence IDs by category
                "counts": {                       # Statistical counters
                    "total": 0,
                    "by_criterion": {},
                    "by_chunk": {},
                    "by_category": {}
                }
            },
            
            # Assessment results
            "assessments": {
                "criteria": {},                   # Criterion assessments by dimension:criterion
                "dimensions": {},                 # Dimension summaries by dimension
                "overall": {}                     # Overall assessment
            },
            
            # Report data
            "reports": {
                "formats": {}                     # Different report formats
            },
            
            # Operational data
            "operations": {
                "errors": [],                     # Error log
                "warnings": [],                   # Warning log
                "agent_observations": [],         # Agent observations
                "token_usage": {                  # Token usage tracking
                    "total": 0,
                    "by_agent": {},
                    "by_stage": {}
                }
            }
        }
        
        # Initialize framework structure
        self._initialize_framework_structure()
        
        logger.info(f"Enhanced AssessmentContext initialized with run_id: {self.run_id}")
        
    def _initialize_framework_structure(self):
        """Initialize data structures for framework dimensions and criteria."""
        # Extract basic framework info
        framework_id = self.framework.get("id", "unknown")
        framework_name = self.framework.get("name", "Unknown Framework")
        
        logger.info(f"Initializing structure for framework: {framework_name} ({framework_id})")
        
        # Create containers for each dimension and criterion
        dimensions = self.framework.get("dimensions", [])
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            if not dimension_id:
                logger.warning("Found dimension without id, skipping")
                continue
                
            # Initialize dimension in assessments
            self.data["assessments"]["dimensions"][dimension_id] = {
                "summary": None,
                "criteria": {}
            }
                
            # Initialize each criterion
            criteria = dimension.get("criteria", [])
            for criterion in criteria:
                criterion_id = criterion.get("id", "")
                if not criterion_id:
                    logger.warning(f"Found criterion without id in dimension {dimension_id}, skipping")
                    continue
                    
                # Create key for criterion
                criterion_key = f"{dimension_id}:{criterion_id}"
                
                # Initialize criterion in evidence store
                with self._evidence_lock:
                    self.data["evidence"]["by_criterion"][criterion_key] = set()
                    self.data["evidence"]["counts"]["by_criterion"][criterion_key] = 0
                
                # Initialize criterion in assessments
                with self._assessment_lock:
                    self.data["assessments"]["criteria"][criterion_key] = {
                        "dimension_id": dimension_id,
                        "criterion_id": criterion_id,
                        "rating": None,
                        "rationale": None,
                        "confidence": None,
                        "evidence_ids": [],
                        "timestamp": None,
                        "assessment_type": None
                    }
                
        logger.info(f"Framework structure initialized with {len(dimensions)} dimensions")

    #
    # Document Property Methods
    #
    
    def set_document_properties(self, properties: Dict[str, Any]) -> None:
        """
        Set document properties.
        
        Args:
            properties: Document properties dict
        """
        self.document_properties.update(properties)
        logger.info(f"Updated document properties: {', '.join(properties.keys())}")
    
    def get_document_properties(self) -> Dict[str, Any]:
        """
        Get document properties.
        
        Returns:
            Document properties dict
        """
        return self.document_properties
    
    def set_document_type(self, document_type: str) -> None:
        """
        Set document type.
        
        Args:
            document_type: Document type string
        """
        self.document_properties["document_type"] = document_type
    
    def get_document_type(self) -> str:
        """
        Get document type.
        
        Returns:
            Document type string
        """
        return self.document_properties.get("document_type", "unknown")
    
    def set_entity_info(self, entity_info: Dict[str, Any]) -> None:
        """
        Set entity information.
        
        Args:
            entity_info: Entity information dict
        """
        self.document_properties["primary_entity"] = entity_info
    
    def get_entity_info(self) -> Dict[str, Any]:
        """
        Get entity information.
        
        Returns:
            Entity information dict
        """
        return self.document_properties.get("primary_entity", {"name": "unknown", "type": "unknown"})
    
    def set_document_bias(self, bias_info: Dict[str, Any]) -> None:
        """
        Set document bias information.
        
        Args:
            bias_info: Bias information dict
        """
        self.document_properties["document_bias"] = bias_info
    
    def get_document_bias(self) -> Dict[str, Any]:
        """
        Get document bias information.
        
        Returns:
            Bias information dict
        """
        return self.document_properties.get("document_bias", {"orientation": "neutral"})

    #
    # Document & Chunking Methods
    #
    
    def set_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Set document chunks.
        
        Args:
            chunks: List of document chunks
        """
        self.chunks = chunks
        
        # Initialize evidence by chunk
        with self._evidence_lock:
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id")
                if chunk_id:
                    self.data["evidence"]["by_chunk"][chunk_id] = set()
                    self.data["evidence"]["counts"]["by_chunk"][chunk_id] = 0
                
        logger.info(f"Set {len(chunks)} document chunks")
        
    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific chunk by ID.
        
        Args:
            chunk_id: ID of the chunk to retrieve
            
        Returns:
            Chunk dict if found, None otherwise
        """
        for chunk in self.chunks:
            if chunk.get("chunk_id") == chunk_id:
                return chunk
        return None
        
    def get_chunks(self) -> List[Dict[str, Any]]:
        """
        Get all document chunks.
        
        Returns:
            List of all document chunks
        """
        return self.chunks

    #
    # Strategy Methods
    #
    
    def set_strategy(self, strategy: Dict[str, Any]) -> None:
        """
        Set the complete assessment strategy.
        
        Args:
            strategy: Complete assessment strategy
        """
        with self._strategy_lock:
            self.data["strategy"]["pipeline_design"] = strategy
            
        logger.info(f"Set assessment strategy: {strategy.get('strategy_type', 'unknown')}")
    
    def get_strategy(self) -> Dict[str, Any]:
        """
        Get the complete assessment strategy.
        
        Returns:
            Complete assessment strategy
        """
        with self._strategy_lock:
            return self.data["strategy"]["pipeline_design"]
    
    def set_criteria_groups(self, criteria_groups: List[Dict[str, Any]]) -> None:
        """
        Set criteria groups for extraction.
        
        Args:
            criteria_groups: List of criteria groups
        """
        with self._strategy_lock:
            self.data["strategy"]["criteria_groups"] = criteria_groups
            
        logger.info(f"Set {len(criteria_groups)} criteria groups")
    
    def get_criteria_groups(self) -> List[Dict[str, Any]]:
        """
        Get criteria groups for extraction.
        
        Returns:
            List of criteria groups
        """
        with self._strategy_lock:
            return self.data["strategy"]["criteria_groups"]
    
    def add_extraction_strategy(self, strategy: Dict[str, Any]) -> None:
        """
        Add an extraction strategy.
        
        Args:
            strategy: Extraction strategy for a criteria group
        """
        with self._strategy_lock:
            self.data["strategy"]["extraction_strategies"].append(strategy)
            
        logger.info(f"Added extraction strategy: {strategy.get('name', 'unnamed')}")
    
    def get_extraction_strategies(self) -> List[Dict[str, Any]]:
        """
        Get extraction strategies.
        
        Returns:
            List of extraction strategies
        """
        with self._strategy_lock:
            return self.data["strategy"]["extraction_strategies"]
    
    def set_semantic_guidance(self, criterion_key: str, guidance: str) -> None:
        """
        Set semantic guidance for a criterion.
        
        Args:
            criterion_key: Criterion key (dimension_id:criterion_id)
            guidance: Semantic guidance text
        """
        with self._strategy_lock:
            self.data["strategy"]["semantic_guidance"][criterion_key] = guidance
            
        logger.debug(f"Set semantic guidance for {criterion_key}")
    
    def get_semantic_guidance(self, criterion_key: str) -> Optional[str]:
        """
        Get semantic guidance for a criterion.
        
        Args:
            criterion_key: Criterion key (dimension_id:criterion_id)
            
        Returns:
            Semantic guidance text if available, None otherwise
        """
        with self._strategy_lock:
            return self.data["strategy"]["semantic_guidance"].get(criterion_key)

    #
    # Process Tracking Methods
    #
    
    def set_stage(self, stage_name: str):
        """
        Set the current processing stage.
        
        Args:
            stage_name: Name of the current stage
        """
        with self._progress_lock:
            self.current_stage = stage_name
            
            # Initialize stage data if not exists
            if stage_name not in self.stages:
                self.stages[stage_name] = {
                    "status": "running",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "progress": 0.0,
                    "message": f"Starting {stage_name}",
                    "errors": [],
                    "agent": None
                }
            
        logger.info(f"Setting current stage to: {stage_name}")
        
    def set_stage_agent(self, stage_name: str, agent_name: str):
        """
        Associate an agent with a stage.
        
        Args:
            stage_name: Name of the stage
            agent_name: Name of the agent
        """
        with self._progress_lock:
            if stage_name in self.stages:
                self.stages[stage_name]["agent"] = agent_name
            
    def update_progress(self, progress: float, message: Optional[str] = None):
        """
        Update the progress of the current stage.
        
        Args:
            progress: Progress value between 0.0 and 1.0
            message: Optional progress message
        """
        with self._progress_lock:
            if self.current_stage and self.current_stage in self.stages:
                self.stages[self.current_stage]["progress"] = progress
                
                if message:
                    self.stages[self.current_stage]["message"] = message
                    
            self.progress = self._calculate_overall_progress()
        
    def _calculate_overall_progress(self) -> float:
        """
        Calculate overall progress based on stage weights.
        
        Returns:
            Overall progress value between 0.0 and 1.0
        """
        # Default stage weights
        stage_weights = {
            "document_analysis": 0.05,
            "chunking": 0.05,
            "strategy_design": 0.10,
            "evidence_extraction": 0.35,
            "assessment": 0.25,
            "reporting": 0.20
        }
        
        # Override with user-defined weights if available
        if "stage_weights" in self.options:
            stage_weights.update(self.options["stage_weights"])
            
        # Calculate weighted progress
        overall_progress = 0.0
        total_weight = 0.0
        
        for stage_name, stage_data in self.stages.items():
            weight = stage_weights.get(stage_name, 0.1)
            progress = stage_data.get("progress", 0.0)
            
            overall_progress += weight * progress
            total_weight += weight
            
        # Normalize by actual total weight
        if total_weight > 0:
            overall_progress /= total_weight
            
        return overall_progress
        
    def complete_stage(self, stage_name: str, result: Optional[Dict[str, Any]] = None):
        """
        Mark a stage as completed.
        
        Args:
            stage_name: Name of the stage to complete
            result: Optional result data from the stage
        """
        with self._progress_lock:
            if stage_name in self.stages:
                self.stages[stage_name].update({
                    "status": "completed",
                    "end_time": datetime.now(timezone.utc).isoformat(),
                    "progress": 1.0,
                    "result": result,
                    "message": f"Completed {stage_name}"
                })
            
            self.update_progress(1.0, f"Completed {stage_name}")
        
        logger.info(f"Marked stage as complete: {stage_name}")
        
    def fail_stage(self, stage_name: str, error_message: str):
        """
        Mark a stage as failed.
        
        Args:
            stage_name: Name of the stage that failed
            error_message: Error message describing the failure
        """
        with self._progress_lock:
            if stage_name in self.stages:
                self.stages[stage_name].update({
                    "status": "failed",
                    "end_time": datetime.now(timezone.utc).isoformat(),
                    "progress": 1.0,
                    "message": f"Failed: {error_message}"
                })
                
                # Add to errors list
                error_record = {
                    "stage": stage_name,
                    "time": datetime.now(timezone.utc).isoformat(),
                    "message": error_message
                }
                
                self.stages[stage_name]["errors"].append(error_record)
                self.data["operations"]["errors"].append(error_record)
            
            self.update_progress(1.0, f"Failed: {error_message}")
        
        logger.error(f"Stage failed: {stage_name} - {error_message}")
        
    def add_warning(self, warning_message: str, stage_name: Optional[str] = None):
        """
        Add a warning message.
        
        Args:
            warning_message: Warning message
            stage_name: Optional name of the stage that generated the warning
        """
        warning_record = {
            "stage": stage_name or self.current_stage,
            "time": datetime.now(timezone.utc).isoformat(),
            "message": warning_message
        }
        
        self.data["operations"]["warnings"].append(warning_record)
        logger.warning(f"Warning: {warning_message}")
    
    #
    # Evidence Methods
    #
    
    def add_evidence(
        self, 
        dimension_id: str, 
        criterion_id: str, 
        text: str, 
        chunk_id: Optional[str] = None, 
        location: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add evidence for a criterion. Thread-safe.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            text: Evidence text
            chunk_id: Optional ID of the chunk containing the evidence
            location: Optional location info (e.g., start and end positions)
            metadata: Optional additional metadata
            
        Returns:
            ID of the newly created evidence
        """
        # Create evidence ID
        evidence_id = f"ev-{uuid.uuid4().hex[:8]}"
        
        # Create criterion key
        criterion_key = f"{dimension_id}:{criterion_id}"
        
        # Default metadata if none provided
        if metadata is None:
            metadata = {}
        
        # Prepare evidence record
        evidence_record = {
            "id": evidence_id,
            "dimension_id": dimension_id,
            "criterion_id": criterion_id,
            "text": text,
            "chunk_id": chunk_id,
            "location": location or {},
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Get category from metadata if available
        category = "uncategorized"
        relevance_level = metadata.get("relevance_level", "").lower()
        if relevance_level:
            category = relevance_level
        
        # Store evidence with thread safety
        with self._evidence_lock:
            # Store evidence item
            self.data["evidence"]["items"][evidence_id] = evidence_record
            
            # Update evidence-criterion mapping
            if criterion_key in self.data["evidence"]["by_criterion"]:
                self.data["evidence"]["by_criterion"][criterion_key].add(evidence_id)
            else:
                self.data["evidence"]["by_criterion"][criterion_key] = {evidence_id}
                
            # Update evidence-chunk mapping if chunk provided
            if chunk_id and chunk_id in self.data["evidence"]["by_chunk"]:
                self.data["evidence"]["by_chunk"][chunk_id].add(evidence_id)
                
            # Update evidence-category mapping
            if category not in self.data["evidence"]["by_category"]:
                self.data["evidence"]["by_category"][category] = set()
            self.data["evidence"]["by_category"][category].add(evidence_id)
            
            # Update counts
            self.data["evidence"]["counts"]["total"] += 1
            self.data["evidence"]["counts"]["by_criterion"][criterion_key] = (
                self.data["evidence"]["counts"]["by_criterion"].get(criterion_key, 0) + 1
            )
            if chunk_id:
                self.data["evidence"]["counts"]["by_chunk"][chunk_id] = (
                    self.data["evidence"]["counts"]["by_chunk"].get(chunk_id, 0) + 1
                )
            self.data["evidence"]["counts"]["by_category"][category] = (
                self.data["evidence"]["counts"]["by_category"].get(category, 0) + 1
            )
            
        # Update assessment with evidence reference
        with self._assessment_lock:
            criterion_data = self.data["assessments"]["criteria"].get(criterion_key, {})
            if criterion_data:
                # Add evidence ID to list if not already present
                evidence_ids = criterion_data.get("evidence_ids", [])
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
                criterion_data["evidence_ids"] = evidence_ids
                self.data["assessments"]["criteria"][criterion_key] = criterion_data
        
        logger.debug(f"Added evidence {evidence_id} for {criterion_key} (category: {category})")
        return evidence_id
        
    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """
        Get evidence by ID.
        
        Args:
            evidence_id: ID of the evidence to retrieve
            
        Returns:
            Evidence record if found, None otherwise
        """
        with self._evidence_lock:
            return self.data["evidence"]["items"].get(evidence_id)
        
    def get_evidence_for_criterion(
        self, 
        dimension_id: str, 
        criterion_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all evidence for a criterion.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            
        Returns:
            List of evidence records for the criterion
        """
        criterion_key = f"{dimension_id}:{criterion_id}"
        
        with self._evidence_lock:
            evidence_ids = self.data["evidence"]["by_criterion"].get(criterion_key, set())
            
            return [
                self.data["evidence"]["items"][ev_id] 
                for ev_id in evidence_ids 
                if ev_id in self.data["evidence"]["items"]
            ]
        
    def get_evidence_for_chunk(self, chunk_id: str) -> List[Dict[str, Any]]:
        """
        Get all evidence from a chunk.
        
        Args:
            chunk_id: ID of the chunk
            
        Returns:
            List of evidence records from the chunk
        """
        with self._evidence_lock:
            evidence_ids = self.data["evidence"]["by_chunk"].get(chunk_id, set())
            
            return [
                self.data["evidence"]["items"][ev_id] 
                for ev_id in evidence_ids 
                if ev_id in self.data["evidence"]["items"]
            ]
            
    def get_evidence_count(self, dimension_id: Optional[str] = None, criterion_id: Optional[str] = None) -> int:
        """
        Get evidence count, optionally filtered by dimension or criterion.
        
        Args:
            dimension_id: Optional dimension ID filter
            criterion_id: Optional criterion ID filter
            
        Returns:
            Evidence count
        """
        with self._evidence_lock:
            if dimension_id and criterion_id:
                criterion_key = f"{dimension_id}:{criterion_id}"
                return self.data["evidence"]["counts"]["by_criterion"].get(criterion_key, 0)
            elif dimension_id:
                # Count all evidence for this dimension
                count = 0
                for key, value in self.data["evidence"]["counts"]["by_criterion"].items():
                    if key.startswith(f"{dimension_id}:"):
                        count += value
                return count
            else:
                return self.data["evidence"]["counts"]["total"]
    
    def get_evidence_categories(self, dimension_id: str, criterion_id: str) -> Dict[str, int]:
        """
        Get evidence category counts for a criterion.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            
        Returns:
            Dictionary mapping categories to counts
        """
        criterion_key = f"{dimension_id}:{criterion_id}"
        
        with self._evidence_lock:
            evidence_ids = self.data["evidence"]["by_criterion"].get(criterion_key, set())
            if not evidence_ids:
                return {}
            
            # Count by category
            categories = {}
            for evidence_id in evidence_ids:
                if evidence_id in self.data["evidence"]["items"]:
                    evidence = self.data["evidence"]["items"][evidence_id]
                    metadata = evidence.get("metadata", {})
                    
                    # Get relevance level and sentiment
                    relevance = metadata.get("relevance_level", "").lower()
                    if not relevance:
                        relevance = "uncategorized"
                        
                    sentiment = metadata.get("sentiment", "").lower()
                    if not sentiment:
                        sentiment = "neutral"
                    
                    # Create category key
                    category = f"{relevance}_{sentiment}"
                    
                    # Increment count
                    categories[category] = categories.get(category, 0) + 1
            
            return categories
            
    def get_evidence_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive evidence statistics.
        
        Returns:
            Evidence statistics dictionary
        """
        with self._evidence_lock:
            # Convert sets to lists for serialization
            by_criterion = {k: list(v) for k, v in self.data["evidence"]["by_criterion"].items()}
            by_chunk = {k: list(v) for k, v in self.data["evidence"]["by_chunk"].items()}
            by_category = {k: list(v) for k, v in self.data["evidence"]["by_category"].items()}
            
            # Get category distribution
            category_counts = self.data["evidence"]["counts"]["by_category"]
            
            # Get dimension distribution
            dimension_counts = {}
            for key, count in self.data["evidence"]["counts"]["by_criterion"].items():
                if ":" in key:
                    dimension_id = key.split(":")[0]
                    dimension_counts[dimension_id] = dimension_counts.get(dimension_id, 0) + count
            
            return {
                "total": self.data["evidence"]["counts"]["total"],
                "by_criterion": self.data["evidence"]["counts"]["by_criterion"],
                "by_chunk": self.data["evidence"]["counts"]["by_chunk"],
                "by_category": category_counts,
                "by_dimension": dimension_counts,
                "evidence_map": {
                    "by_criterion": by_criterion,
                    "by_chunk": by_chunk,
                    "by_category": by_category
                }
            }
    
    #
    # Assessment Methods
    #
    
    def set_criterion_assessment(
        self,
        dimension_id: str,
        criterion_id: str,
        rating: Any,
        rationale: str,
        confidence: Optional[float] = None,
        assessment_type: str = "direct"
    ) -> bool:
        """
        Set assessment for a criterion.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            rating: Assessment rating (type depends on scoring method)
            rationale: Rationale for the assessment
            confidence: Optional confidence score (0.0-1.0)
            assessment_type: Type of assessment ("direct", "inferred", "insufficient_evidence")
            
        Returns:
            True if assessment was set successfully, False otherwise
        """
        criterion_key = f"{dimension_id}:{criterion_id}"
        
        with self._assessment_lock:
            if criterion_key in self.data["assessments"]["criteria"]:
                
                self.data["assessments"]["criteria"][criterion_key].update({
                    "rating": rating,
                    "rationale": rationale,
                    "confidence": confidence,
                    "assessment_type": assessment_type,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                logger.debug(f"Set assessment for {criterion_key} with rating {rating}")
                return True
            
            logger.warning(f"Failed to set assessment: {criterion_key} not found")
            return False
        
    def get_criterion_assessment(
        self, 
        dimension_id: str, 
        criterion_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get assessment for a criterion.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            
        Returns:
            Assessment data if found, None otherwise
        """
        criterion_key = f"{dimension_id}:{criterion_id}"
        
        with self._assessment_lock:
            return self.data["assessments"]["criteria"].get(criterion_key)
        
    def set_dimension_summary(self, dimension_id: str, summary: Dict[str, Any]) -> bool:
        """
        Set summary assessment for a dimension.
        
        Args:
            dimension_id: ID of the dimension
            summary: Summary assessment data
            
        Returns:
            True if summary was set successfully, False otherwise
        """
        with self._assessment_lock:
            if dimension_id in self.data["assessments"]["dimensions"]:
                self.data["assessments"]["dimensions"][dimension_id] = summary
                return True
            
            # Initialize if not found
            self.data["assessments"]["dimensions"][dimension_id] = summary
            return True
        
    def get_dimension_summary(self, dimension_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary assessment for a dimension.
        
        Args:
            dimension_id: ID of the dimension
            
        Returns:
            Dimension summary if found, None otherwise
        """
        with self._assessment_lock:
            return self.data["assessments"]["dimensions"].get(dimension_id)
        
    def set_overall_assessment(self, assessment: Dict[str, Any]):
        """
        Set overall assessment for the framework.
        
        Args:
            assessment: Overall assessment data
        """
        with self._assessment_lock:
            self.data["assessments"]["overall"] = assessment
        
        logger.info("Set overall assessment")
        
    def get_overall_assessment(self) -> Dict[str, Any]:
        """
        Get overall assessment for the framework.
        
        Returns:
            Overall assessment data
        """
        with self._assessment_lock:
            return self.data["assessments"]["overall"]
    
    def get_assessment_stats(self) -> Dict[str, Any]:
        """
        Calculate assessment statistics.
        
        Returns:
            Dictionary of assessment statistics
        """
        # Count criteria
        total_criteria = 0
        assessed_criteria = 0
        
        # Track confidence scores
        confidence_scores = []
        
        # Count by assessment type
        assessment_types = {"direct": 0, "inferred": 0, "insufficient_evidence": 0}
        
        # Count by dimension
        dimension_stats = {}
        
        with self._assessment_lock:
            # Create mapping of dimension IDs to names
            dimension_names = {}
            for dimension in self.framework.get("dimensions", []):
                dimension_id = dimension.get("id", "")
                if dimension_id:
                    dimension_names[dimension_id] = dimension.get("name", dimension_id)
            
            # Process each criterion assessment
            for criterion_key, assessment in self.data["assessments"]["criteria"].items():
                dimension_id, criterion_id = criterion_key.split(":", 1)
                
                # Count total criteria
                total_criteria += 1
                
                # Get dimension info
                if dimension_id not in dimension_stats:
                    dimension_stats[dimension_id] = {
                        "name": dimension_names.get(dimension_id, dimension_id),
                        "total_criteria": 0,
                        "assessed_criteria": 0,
                        "coverage": 0.0,
                        "average_rating": None,
                        "ratings": []
                    }
                dimension_stats[dimension_id]["total_criteria"] += 1
                
                # Check if assessed
                if assessment.get("rating") is not None:
                    assessed_criteria += 1
                    dimension_stats[dimension_id]["assessed_criteria"] += 1
                    dimension_stats[dimension_id]["ratings"].append(assessment["rating"])
                    
                    # Track assessment type
                    assessment_type = assessment.get("assessment_type", "direct")
                    assessment_types[assessment_type] = assessment_types.get(assessment_type, 0) + 1
                    
                    # Track confidence
                    if assessment.get("confidence") is not None:
                        confidence_scores.append(assessment["confidence"])
            
            # Calculate dimension coverage and averages
            for dimension_id, stats in dimension_stats.items():
                stats["coverage"] = stats["assessed_criteria"] / max(1, stats["total_criteria"])
                
                # Calculate average rating
                ratings = stats["ratings"]
                if ratings:
                    stats["average_rating"] = sum(ratings) / len(ratings)
        
        # Calculate overall coverage
        overall_coverage = assessed_criteria / max(1, total_criteria)
        
        # Calculate average confidence
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) 
            if confidence_scores else None
        )
        
        # Get evidence stats
        total_evidence = self.get_evidence_count()
        
        # Build stats dict
        stats = {
            "total_criteria": total_criteria,
            "assessed_criteria": assessed_criteria,
            "assessment_coverage": overall_coverage,
            "average_confidence": avg_confidence,
            "total_evidence": total_evidence,
            "evidence_per_criterion": total_evidence / max(1, total_criteria),
            "assessment_types": assessment_types,
            "dimensions": dimension_stats
        }
        
        return stats
    
    #
    # Report Methods
    #
    
    def set_report(self, format_name: str, report_data: Dict[str, Any]):
        """
        Set a report format.
        
        Args:
            format_name: Report format name
            report_data: Report data
        """
        self.data["reports"]["formats"][format_name] = report_data
        logger.info(f"Set report format: {format_name}")
    
    def get_report(self, format_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a report format.
        
        Args:
            format_name: Report format name
            
        Returns:
            Report data if found, None otherwise
        """
        return self.data["reports"]["formats"].get(format_name)
    
    def get_reports(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all report formats.
        
        Returns:
            Dictionary of report formats
        """
        return self.data["reports"]["formats"]
    
    #
    # Agent Collaboration Methods
    #
    
    def record_agent_observation(
        self,
        agent_name: str,
        observation_type: str,
        observation: Any
    ):
        """
        Record an observation from an agent.
        
        Args:
            agent_name: Name of the agent making the observation
            observation_type: Type of observation (e.g., 'evidence', 'assessment')
            observation: Content of the observation
        """
        observation_record = {
            "agent": agent_name,
            "type": observation_type,
            "content": observation,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        with self._observation_lock:
            self.data["operations"]["agent_observations"].append(observation_record)
        
        logger.debug(f"Recorded {observation_type} observation from {agent_name}")
        
    def get_agent_observations(
        self,
        agent_name: Optional[str] = None,
        observation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get agent observations with optional filtering.
        
        Args:
            agent_name: Optional filter by agent name
            observation_type: Optional filter by observation type
            
        Returns:
            List of matching observation records
        """
        with self._observation_lock:
            observations = self.data["operations"]["agent_observations"]
            
            if agent_name:
                observations = [obs for obs in observations if obs["agent"] == agent_name]
                
            if observation_type:
                observations = [obs for obs in observations if obs["type"] == observation_type]
                
            return observations
    
    #
    # Token Usage Tracking
    #
    
    def track_token_usage(
        self, 
        token_count: int, 
        token_type: str = "total",
        agent_name: Optional[str] = None,
        stage_name: Optional[str] = None
    ):
        """
        Track token usage.
        
        Args:
            token_count: Number of tokens to track
            token_type: Token type (prompt, completion, total)
            agent_name: Optional name of the agent using tokens
            stage_name: Optional name of the stage using tokens
        """
        # Add to total
        self.data["operations"]["token_usage"]["total"] += token_count
        
        # Track by agent if provided
        if agent_name:
            if agent_name not in self.data["operations"]["token_usage"]["by_agent"]:
                self.data["operations"]["token_usage"]["by_agent"][agent_name] = 0
            self.data["operations"]["token_usage"]["by_agent"][agent_name] += token_count
        
        # Track by stage if provided
        if stage_name:
            if stage_name not in self.data["operations"]["token_usage"]["by_stage"]:
                self.data["operations"]["token_usage"]["by_stage"][stage_name] = 0
            self.data["operations"]["token_usage"]["by_stage"][stage_name] += token_count
    
    def get_token_usage(self) -> Dict[str, Any]:
        """
        Get token usage statistics.
        
        Returns:
            Token usage statistics
        """
        return self.data["operations"]["token_usage"]
    
    #
    # Results Methods
    #
    
    def get_final_result(self) -> Dict[str, Any]:
        """
        Get the final assessment result.
        
        Returns:
            Complete assessment result with metadata
        """
        # Get statistics
        stats = self.get_assessment_stats()
        
        # Convert sets to lists for JSON serialization
        with self._evidence_lock:
            evidence_items = self.data["evidence"]["items"]
            evidence_by_criterion = {k: list(v) for k, v in self.data["evidence"]["by_criterion"].items()}
            evidence_by_chunk = {k: list(v) for k, v in self.data["evidence"]["by_chunk"].items()}
            evidence_by_category = {k: list(v) for k, v in self.data["evidence"]["by_category"].items()}
        
        # Build metadata
        metadata = {
            "framework_id": self.framework.get("id", "unknown"),
            "framework_name": self.framework.get("name", "Unknown Framework"),
            "document_name": self.options.get("document_name", "Unknown Document"),
            "document_type": self.document_properties.get("document_type", "unknown"),
            "entity_name": self.document_properties.get("primary_entity", {}).get("name", "unknown"),
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "processing_time": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "document_length": len(self.document_text),
            "chunks_count": len(self.chunks),
            "options": self.options,
            "document_bias": self.document_properties.get("document_bias", {"orientation": "neutral"}),
            "token_usage": self.data["operations"]["token_usage"]
        }
        
        # Build result dict
        result = {
            "framework": self.framework,
            "metadata": metadata,
            "strategy": self.data["strategy"]["pipeline_design"],
            "assessments": {
                "criteria": self.data["assessments"]["criteria"],
                "dimensions": self.data["assessments"]["dimensions"],
                "overall": self.data["assessments"]["overall"]
            },
            "evidence": {
                "items": evidence_items,
                "by_criterion": evidence_by_criterion,
                "by_chunk": evidence_by_chunk,
                "by_category": evidence_by_category,
                "counts": self.data["evidence"]["counts"]
            },
            "statistics": stats,
            "reports": self.data["reports"],
            "warnings": self.data["operations"]["warnings"],
            "errors": self.data["operations"]["errors"]
        }
        
        return result
    
    #
    # Exploration Methods
    #
    
    def get_exploration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the assessment context for exploration.
        
        Returns:
            Dictionary with exploration summary
        """
        return {
            "document_properties": self.document_properties,
            "framework_info": {
                "id": self.framework.get("id", "unknown"),
                "name": self.framework.get("name", "Unknown Framework"),
                "dimensions": len(self.framework.get("dimensions", [])),
                "total_criteria": sum(len(dim.get("criteria", [])) for dim in self.framework.get("dimensions", []))
            },
            "evidence_stats": {
                "total": self.data["evidence"]["counts"]["total"],
                "by_category": self.data["evidence"]["counts"]["by_category"]
            },
            "assessment_stats": self.get_assessment_stats(),
            "stages": self.stages,
            "progress": self.progress,
            "token_usage": self.data["operations"]["token_usage"]["total"],
            "warnings_count": len(self.data["operations"]["warnings"]),
            "errors_count": len(self.data["operations"]["errors"])
        }