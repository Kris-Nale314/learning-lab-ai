"""
Assessment Context - Central collaboration mechanism for Framework Assessment

This module provides the AssessmentContext class, which serves as the shared memory
and collaboration layer for all agents in the framework assessment system.
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Set

# Configure logger
logger = logging.getLogger("learning-lab-ai.context")

class AssessmentContext:
    """
    Shared context for agent collaboration in framework assessment.
    
    The AssessmentContext serves as:
    1. Shared memory for all assessment data
    2. Collaboration mechanism for agents
    3. Evidence traceability system
    4. Progress tracking system
    
    Best practices implemented:
    - Clear responsibility boundaries
    - Simple, flat data structures where possible
    - Consistent access patterns
    - Immutable history
    - Minimal required knowledge for agents
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
        
        # Processing state
        self.progress = 0.0
        self.status = "initialized"
        self.current_stage = None
        self.stages = {}
        
        # Chunks
        self.chunks = []
        
        # Main data store - using flat structure with logical naming
        self.data = {
            "planning": {},          # Meta-planning data
            "evidence": {},          # Evidence storage by criterion
            "assessments": {},       # Assessment results by criterion
            "dimension_summaries": {}, # Dimension-level summaries
            "overall_assessment": {},  # Overall assessment
            "errors": [],            # Error log
            "warnings": []           # Warning log
        }
        
        # Evidence store
        self.evidence_store = {
            "items": {},             # Evidence items by ID
            "by_criterion": {},      # Evidence IDs by criterion
            "by_chunk": {}           # Evidence IDs by chunk
        }
        
        # Agent observations (for collaboration visibility)
        self.agent_observations = []
        
        # Initialize framework structure
        self._initialize_framework_structure()
        
        logger.info(f"AssessmentContext initialized with run_id: {self.run_id}")
        
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
            self.data["assessments"][dimension_id] = {
                "criteria": {},
                "summary": None
            }
                
            # Initialize each criterion
            criteria = dimension.get("criteria", [])
            for criterion in criteria:
                criterion_id = criterion.get("id", "")
                if not criterion_id:
                    logger.warning(f"Found criterion without id in dimension {dimension_id}, skipping")
                    continue
                    
                # Initialize criterion in evidence store
                criterion_key = f"{dimension_id}:{criterion_id}"
                self.evidence_store["by_criterion"][criterion_key] = set()
                
                # Initialize criterion in assessments
                self.data["assessments"][dimension_id]["criteria"][criterion_id] = {
                    "rating": None,
                    "rationale": None,
                    "confidence": None,
                    "evidence_ids": [],
                    "timestamp": None
                }
                
        logger.info(f"Framework structure initialized with {len(dimensions)} dimensions")

    #
    # Document & Chunking Methods
    #
    
    def set_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Set document chunks.
        
        Args:
            chunks: List of document chunks, where each chunk is a dict with at least
                   'chunk_id', 'text', and 'span' (start/end char positions) keys
        """
        self.chunks = chunks
        
        # Initialize evidence by chunk
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            if chunk_id:
                self.evidence_store["by_chunk"][chunk_id] = set()
                
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
    # Process Tracking Methods
    #
    
    def set_stage(self, stage_name: str):
        """
        Set the current processing stage.
        
        Args:
            stage_name: Name of the current stage
        """
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
        if stage_name in self.stages:
            self.stages[stage_name]["agent"] = agent_name
            
    def update_progress(self, progress: float, message: Optional[str] = None):
        """
        Update the progress of the current stage.
        
        Args:
            progress: Progress value between 0.0 and 1.0
            message: Optional progress message
        """
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
            "planning": 0.10,
            "evidence_extraction": 0.35,
            "assessment": 0.25,
            "confidence": 0.10,
            "formatting": 0.10
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
            self.data["errors"].append(error_record)
        
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
        
        self.data["warnings"].append(warning_record)
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
        Add evidence for a criterion.
        
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
        
        # Prepare evidence record
        evidence_record = {
            "id": evidence_id,
            "dimension_id": dimension_id,
            "criterion_id": criterion_id,
            "text": text,
            "chunk_id": chunk_id,
            "location": location or {},
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Store evidence
        self.evidence_store["items"][evidence_id] = evidence_record
        
        # Update evidence-criterion mapping
        if criterion_key in self.evidence_store["by_criterion"]:
            self.evidence_store["by_criterion"][criterion_key].add(evidence_id)
        else:
            self.evidence_store["by_criterion"][criterion_key] = {evidence_id}
            
        # Update evidence-chunk mapping if chunk provided
        if chunk_id and chunk_id in self.evidence_store["by_chunk"]:
            self.evidence_store["by_chunk"][chunk_id].add(evidence_id)
            
        # Update assessment with evidence reference
        if (dimension_id in self.data["assessments"] and 
            criterion_id in self.data["assessments"][dimension_id]["criteria"]):
            # Add evidence ID to list if not already present
            evidence_ids = self.data["assessments"][dimension_id]["criteria"][criterion_id]["evidence_ids"]
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
        
        logger.debug(f"Added evidence {evidence_id} for {criterion_key}")
        return evidence_id
        
    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """
        Get evidence by ID.
        
        Args:
            evidence_id: ID of the evidence to retrieve
            
        Returns:
            Evidence record if found, None otherwise
        """
        return self.evidence_store["items"].get(evidence_id)
        
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
        evidence_ids = self.evidence_store["by_criterion"].get(criterion_key, set())
        
        return [
            self.evidence_store["items"][ev_id] 
            for ev_id in evidence_ids 
            if ev_id in self.evidence_store["items"]
        ]
        
    def get_evidence_for_chunk(self, chunk_id: str) -> List[Dict[str, Any]]:
        """
        Get all evidence from a chunk.
        
        Args:
            chunk_id: ID of the chunk
            
        Returns:
            List of evidence records from the chunk
        """
        evidence_ids = self.evidence_store["by_chunk"].get(chunk_id, set())
        
        return [
            self.evidence_store["items"][ev_id] 
            for ev_id in evidence_ids 
            if ev_id in self.evidence_store["items"]
        ]
    
    #
    # Assessment Methods
    #
    
    def set_criterion_assessment(
        self,
        dimension_id: str,
        criterion_id: str,
        rating: Any,
        rationale: str,
        confidence: Optional[float] = None
    ):
        """
        Set assessment for a criterion.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            rating: Assessment rating (type depends on scoring method)
            rationale: Rationale for the assessment
            confidence: Optional confidence score (0.0-1.0)
        """
        if (dimension_id in self.data["assessments"] and 
            criterion_id in self.data["assessments"][dimension_id]["criteria"]):
            
            self.data["assessments"][dimension_id]["criteria"][criterion_id].update({
                "rating": rating,
                "rationale": rationale,
                "confidence": confidence,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.debug(f"Set assessment for {dimension_id}:{criterion_id} with rating {rating}")
            return True
        
        logger.warning(f"Failed to set assessment: {dimension_id}:{criterion_id} not found")
        return False
        
    def set_dimension_summary(self, dimension_id: str, summary: Dict[str, Any]):
        """
        Set summary assessment for a dimension.
        
        Args:
            dimension_id: ID of the dimension
            summary: Summary assessment data
        """
        if dimension_id in self.data["assessments"]:
            self.data["assessments"][dimension_id]["summary"] = summary
            self.data["dimension_summaries"][dimension_id] = summary
            
            logger.debug(f"Set dimension summary for {dimension_id}")
            return True
        
        logger.warning(f"Failed to set dimension summary: {dimension_id} not found")
        return False
        
    def set_overall_assessment(self, assessment: Dict[str, Any]):
        """
        Set overall assessment for the framework.
        
        Args:
            assessment: Overall assessment data
        """
        self.data["overall_assessment"] = assessment
        logger.info("Set overall assessment")
        
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
        if (dimension_id in self.data["assessments"] and 
            criterion_id in self.data["assessments"][dimension_id]["criteria"]):
            
            return self.data["assessments"][dimension_id]["criteria"][criterion_id]
        
        return None
        
    def get_dimension_summary(self, dimension_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary assessment for a dimension.
        
        Args:
            dimension_id: ID of the dimension
            
        Returns:
            Dimension summary if found, None otherwise
        """
        if dimension_id in self.data["assessments"]:
            return self.data["assessments"][dimension_id]["summary"]
        
        return None
        
    def get_overall_assessment(self) -> Dict[str, Any]:
        """
        Get overall assessment for the framework.
        
        Returns:
            Overall assessment data
        """
        return self.data["overall_assessment"]
    
    #
    # Planning Methods
    #
    
    def set_planning_data(self, planning_data: Dict[str, Any]):
        """
        Store planning data.
        
        Args:
            planning_data: Data from the planning stage
        """
        self.data["planning"] = planning_data
        logger.info("Stored planning data")
        
    def get_planning_data(self) -> Dict[str, Any]:
        """
        Get planning data.
        
        Returns:
            Planning data
        """
        return self.data["planning"]
    
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
        
        self.agent_observations.append(observation_record)
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
        observations = self.agent_observations
        
        if agent_name:
            observations = [obs for obs in observations if obs["agent"] == agent_name]
            
        if observation_type:
            observations = [obs for obs in observations if obs["type"] == observation_type]
            
        return observations
    
    #
    # Results & Statistics Methods
    #
    
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
        
        # Count by dimension
        dimension_stats = {}
        
        for dimension_id, dimension_data in self.data["assessments"].items():
            dimension_criteria = 0
            dimension_assessed = 0
            
            for criterion_id, criterion_data in dimension_data["criteria"].items():
                dimension_criteria += 1
                total_criteria += 1
                
                if criterion_data.get("rating") is not None:
                    dimension_assessed += 1
                    assessed_criteria += 1
                    
                    # Add confidence if available
                    if criterion_data.get("confidence") is not None:
                        confidence_scores.append(criterion_data["confidence"])
            
            # Calculate dimension coverage
            dimension_coverage = dimension_assessed / max(1, dimension_criteria)
            
            dimension_stats[dimension_id] = {
                "total_criteria": dimension_criteria,
                "assessed_criteria": dimension_assessed,
                "coverage": dimension_coverage
            }
        
        # Calculate overall coverage
        overall_coverage = assessed_criteria / max(1, total_criteria)
        
        # Calculate average confidence
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) 
            if confidence_scores else None
        )
        
        # Count evidence
        total_evidence = len(self.evidence_store["items"])
        
        # Build stats dict
        stats = {
            "total_criteria": total_criteria,
            "assessed_criteria": assessed_criteria,
            "assessment_coverage": overall_coverage,
            "average_confidence": avg_confidence,
            "total_evidence": total_evidence,
            "evidence_per_criterion": total_evidence / max(1, total_criteria),
            "dimensions": dimension_stats
        }
        
        return stats
    
    def get_final_result(self) -> Dict[str, Any]:
        """
        Get the final assessment result.
        
        Returns:
            Complete assessment result with metadata
        """
        # Get statistics
        stats = self.get_assessment_stats()
        
        # Convert sets to lists in evidence_store for JSON serialization
        evidence_by_criterion = {}
        for criterion_key, evidence_ids in self.evidence_store["by_criterion"].items():
            evidence_by_criterion[criterion_key] = list(evidence_ids)
            
        evidence_by_chunk = {}
        for chunk_id, evidence_ids in self.evidence_store["by_chunk"].items():
            evidence_by_chunk[chunk_id] = list(evidence_ids)
        
        # Build metadata
        metadata = {
            "framework_id": self.framework.get("id", "unknown"),
            "framework_name": self.framework.get("name", "Unknown Framework"),
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "processing_time": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "document_length": len(self.document_text),
            "chunks_count": len(self.chunks),
            "options": self.options
        }
        
        # Build result dict
        result = {
            "framework": self.framework,
            "assessments": self.data["assessments"],
            "dimension_summaries": self.data["dimension_summaries"],
            "overall_assessment": self.data["overall_assessment"],
            "evidence": {
                "items": self.evidence_store["items"],
                "by_criterion": evidence_by_criterion,
                "by_chunk": evidence_by_chunk
            },
            "statistics": stats,
            "metadata": metadata,
            "errors": self.data["errors"],
            "warnings": self.data["warnings"]
        }
        
        return result