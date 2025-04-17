"""
Enhanced Evaluator Agent - Semantically-aware assessments

This agent analyzes evidence packets to produce structured assessments with clear
ratings, rationales, and proper indication of whether assessments are direct or inferred,
while leveraging the semantic grouping created by the MetaPlanner.
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class EvaluatorAgent(BaseAgent):
    """
    Enhanced evaluator with semantic group awareness.
    
    The Enhanced Evaluator is responsible for:
    1. Analyzing consolidated evidence packets for each criterion
    2. Incorporating semantic group context into assessments
    3. Properly distinguishing between direct and inferred assessments
    4. Generating well-justified ratings based on scoring definitions
    5. Creating dimension-level summaries that recognize semantic relationships
    6. Producing a structured assessment output for the reporter
    """
    
    def __init__(
        self,
        llm,
        context: AssessmentContext,
        name: str = "Evaluator",
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Enhanced Evaluator agent.
        
        Args:
            llm: Language model instance
            context: Assessment context
            name: Agent name
            options: Configuration options including evaluation strategy
        """
        super().__init__(name, "evaluator", llm, context, options or {})
        
        # Get evaluation configuration from options
        self.options = options or {}
        self.evaluation_type = self.options.get("evaluation_type", "structured")
        self.infer_missing = self.options.get("infer_missing", True)
        self.confidence_threshold = self.options.get("confidence_threshold", 0.6)
        self.direct_rating_threshold = self.options.get("direct_rating_threshold", 0.7)
        self.custom_instructions = self.options.get("instructions", "")
        self.output_format = self.options.get("output_format", "scorecard")
        
        # Get schema from strategy if available
        strategy = self.options.get("strategy", {})
        self.output_schema = strategy.get("output_schema", {})
        
        # Store semantic groups for reference
        self.semantic_groups = self._get_semantic_groups_from_observations()
        
        self.logger.info(f"{name} initialized with evaluation_type={self.evaluation_type} and {len(self.semantic_groups)} semantic groups")
        
    def _get_semantic_groups_from_observations(self) -> List[Dict[str, Any]]:
        """
        Get semantic groups from context observations.
        
        Returns:
            List of semantic group dictionaries
        """
        # Look for semantic groups in observations
        semantic_groups = []
        
        # Try to find semantic groups in MetaPlanner observations
        for observation in self.context.get_agent_observations(agent_name="MetaPlanner", observation_type="semantic_groups"):
            if "content" in observation:
                semantic_groups = observation.get("content", [])
                self.logger.info(f"Found {len(semantic_groups)} semantic groups in MetaPlanner observations")
                return semantic_groups
        
        # Fallback: try to find semantic groups in strategy
        for observation in self.context.get_agent_observations(observation_type="strategy_created"):
            if "content" in observation:
                strategy = observation.get("content", {})
                if "semantic_groups" in strategy:
                    semantic_groups = strategy.get("semantic_groups", [])
                    self.logger.info(f"Found {len(semantic_groups)} semantic groups in strategy")
                    return semantic_groups
        
        self.logger.warning("No semantic groups found in observations")
        return []
    
    def _find_semantic_group_for_criterion(self, criterion_id: str) -> Dict[str, Any]:
        """
        Find the semantic group a criterion belongs to.
        
        Args:
            criterion_id: Criterion ID to find
            
        Returns:
            Semantic group dictionary or empty dict if not found
        """
        for group in self.semantic_groups:
            if criterion_id in group.get("criteria_ids", []):
                return group
        
        self.logger.warning(f"No semantic group found for criterion {criterion_id}")
        return {}
    
    async def process(self) -> Dict[str, Any]:
        """
        Evaluate framework criteria based on consolidated evidence packets,
        with semantic group awareness and clear distinction between direct 
        and inferred assessments.
        
        Returns:
            Structured evaluation results aligned with the schema
        """
        self.logger.info("Starting semantically-aware criteria evaluation")
        self.start_timer()
        
        try:
            # Get framework dimensions and criteria
            framework = self.context.framework
            dimensions = framework.get("dimensions", [])
            
            # Initialize assessment structure
            structured_assessment = {
                "dimensions": {},
                "overall": {},
                "semantic_groups": {}  # New section for semantic group insights
            }
            
            # Process each dimension
            total_dimensions = len(dimensions)
            dimension_ratings = []
            
            for i, dimension in enumerate(dimensions):
                dimension_id = dimension.get("id", "")
                
                if not dimension_id:
                    self.logger.warning(f"Skipping dimension without ID at index {i}")
                    continue
                    
                # Update progress
                progress = (i + 1) / total_dimensions
                self.update_progress(progress, f"Evaluating dimension {i+1}/{total_dimensions}")
                
                # Evaluate dimension
                dimension_result = await self._evaluate_dimension(dimension)
                structured_assessment["dimensions"][dimension_id] = dimension_result
                
                # Collect dimension rating for overall assessment
                if dimension_result.get("summary", {}).get("average_rating") is not None:
                    dimension_ratings.append(dimension_result["summary"]["average_rating"])
            
            # Process semantic group insights
            semantic_group_insights = await self._generate_semantic_group_insights()
            structured_assessment["semantic_groups"] = semantic_group_insights
            
            # Generate overall assessment that includes semantic insights
            overall_assessment = await self._generate_overall_assessment(
                structured_assessment["dimensions"], 
                dimensions,
                semantic_group_insights
            )
            structured_assessment["overall"] = overall_assessment
            
            # Set overall assessment in context
            self.context.set_overall_assessment(overall_assessment)
            
            # Record observations of semantic group insights for reporter
            self.record_observation("semantic_group_insights", semantic_group_insights)
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Semantically-aware evaluation completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("evaluation_completed", {
                "dimensions_evaluated": len(structured_assessment["dimensions"]),
                "semantic_groups_evaluated": len(semantic_group_insights["groups"]),
                "time_taken": elapsed_time
            })
            
            return structured_assessment
            
        except Exception as e:
            self.stop_timer()
            self.logger.error(f"Error during criteria evaluation: {str(e)}", exc_info=True)
            self.add_warning(f"Failed to evaluate criteria: {str(e)}")
            raise
    
    async def _evaluate_dimension(self, dimension: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a dimension based on evidence for its criteria.
        
        Args:
            dimension: Framework dimension
            
        Returns:
            Structured dimension evaluation results
        """
        dimension_id = dimension.get("id", "")
        dimension_name = dimension.get("name", "")
        criteria = dimension.get("criteria", [])
        
        # Process each criterion
        criteria_results = {}
        criteria_ratings = []
        assessment_types = {"direct": 0, "inferred": 0, "insufficient_evidence": 0}
        
        for criterion in criteria:
            criterion_id = criterion.get("id", "")
            
            if not criterion_id:
                continue
                
            # Evaluate criterion with semantic awareness
            criterion_result = await self._evaluate_criterion(dimension_id, criterion)
            
            # Track assessment type
            if criterion_result:
                assessment_type = criterion_result.get("assessment_type", "unknown")
                assessment_types[assessment_type] = assessment_types.get(assessment_type, 0) + 1
            
            # Only include in results if we have an assessment
            if criterion_result:
                criteria_results[criterion_id] = criterion_result
                if criterion_result.get("rating") is not None:
                    criteria_ratings.append(criterion_result.get("rating"))
        
        # Generate dimension summary with semantic awareness
        dimension_summary = await self._generate_dimension_summary(
            dimension, criteria_results, assessment_types
        )
        
        # Set dimension summary in context
        self.context.set_dimension_summary(dimension_id, dimension_summary)
        
        # Create structured dimension result
        dimension_result = {
            "criteria": criteria_results,
            "summary": dimension_summary,
            "assessment_types": assessment_types
        }
        
        return dimension_result
    
    async def _evaluate_criterion(self, dimension_id: str, criterion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate a criterion based on consolidated evidence, with semantic awareness
        and clear distinction between direct and inferred assessments.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            
        Returns:
            Structured criterion assessment or None if no evidence and not inferring
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        
        # Get the semantic group this criterion belongs to
        semantic_group = self._find_semantic_group_for_criterion(criterion_id)
        
        # First, check the evidence count directly from context for reliability
        evidence_count = self.context.get_evidence_count(dimension_id, criterion_id)
        self.logger.info(f"Evaluating {dimension_id}:{criterion_id} with {evidence_count} evidence items, in semantic group: {semantic_group.get('name', 'None')}")
        
        # Get consolidated evidence packet if available
        consolidated_evidence = self._get_consolidated_evidence(dimension_id, criterion_id)
        
        # Check if we have a recommendation about direct assessment from the extractor
        assessment_justification = "unknown"
        if consolidated_evidence and "direct_assessment_justified" in consolidated_evidence:
            assessment_justification = consolidated_evidence["direct_assessment_justified"]
        
        # Determine if we should do direct or inferred assessment
        if evidence_count > 0 or (consolidated_evidence and consolidated_evidence.get("evidence_count", 0) > 0):
            # We have evidence - use it for assessment
            
            # If recommendation is clearly YES, do direct assessment
            if assessment_justification == "YES":
                assessment = await self._create_evidence_based_assessment(
                    dimension_id, criterion, consolidated_evidence, semantic_group
                )
                assessment["assessment_type"] = "direct"
                
                # Store assessment with type
                self.set_criterion_assessment(
                    dimension_id, 
                    criterion_id, 
                    assessment["rating"],
                    assessment["rationale"],
                    assessment["confidence"],
                    "direct"
                )
                
                return assessment
                
            # If MAYBE, do direct assessment but mark as less confident
            elif assessment_justification == "MAYBE":
                assessment = await self._create_evidence_based_assessment(
                    dimension_id, criterion, consolidated_evidence, semantic_group
                )
                assessment["assessment_type"] = "direct"
                assessment["confidence"] = min(0.7, assessment.get("confidence", 0.7))
                
                # Store assessment with type
                self.set_criterion_assessment(
                    dimension_id, 
                    criterion_id, 
                    assessment["rating"],
                    assessment["rationale"],
                    assessment["confidence"],
                    "direct"
                )
                
                return assessment
                
            # If NO but inference is allowed, do inferred assessment
            elif assessment_justification == "NO" and self.infer_missing:
                assessment = await self._create_inferred_assessment(
                    dimension_id, criterion, consolidated_evidence, semantic_group
                )
                if assessment:
                    assessment["assessment_type"] = "inferred"
                    
                    # Store assessment with type
                    self.set_criterion_assessment(
                        dimension_id, 
                        criterion_id, 
                        assessment["rating"],
                        assessment["rationale"],
                        assessment["confidence"],
                        "inferred"
                    )
                    
                    return assessment
        
        # If no consolidated packet, fall back to raw evidence
        if (not consolidated_evidence or consolidated_evidence.get("evidence_count", 0) == 0) and evidence_count > 0:
            # Get raw evidence for this criterion
            evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
            
            # If we have evidence but no consolidated packet, use raw evidence
            if evidence_list and len(evidence_list) > 0:
                # Create structured assessment from raw evidence with semantic context
                assessment = await self._create_evidence_based_assessment_from_raw(
                    dimension_id, criterion, evidence_list, semantic_group
                )
                
                # Store assessment with type (default to direct)
                self.set_criterion_assessment(
                    dimension_id, 
                    criterion_id, 
                    assessment["rating"],
                    assessment["rationale"],
                    assessment["confidence"],
                    assessment.get("assessment_type", "direct")
                )
                
                return assessment
        
        # If we get here, there's no evidence - handle based on inference setting
        if self.infer_missing:
            # Try to create inferred assessment with document context and semantic group info
            assessment = await self._create_inferred_assessment_without_evidence(
                dimension_id, criterion, semantic_group
            )
            if assessment and assessment.get("rating") is not None:
                # Store assessment with inferred type
                self.set_criterion_assessment(
                    dimension_id, 
                    criterion_id, 
                    assessment["rating"],
                    assessment["rationale"],
                    assessment["confidence"],
                    "inferred"
                )
                
                return assessment
        
        # No assessment possible - return explicit N/A with reason
        insufficient_assessment = {
            "id": criterion_id,
            "name": criterion_name,
            "rating": None,
            "rationale": "Insufficient evidence for assessment, and inference not possible or not enabled.",
            "confidence": 0.0,
            "assessment_type": "insufficient_evidence",
            "strengths": [],
            "weaknesses": []
        }
        
        # Store the insufficient assessment
        self.set_criterion_assessment(
            dimension_id, 
            criterion_id, 
            None,
            insufficient_assessment["rationale"],
            0.0,
            "insufficient_evidence"
        )
        
        return insufficient_assessment
    
    def _get_consolidated_evidence(self, dimension_id: str, criterion_id: str) -> Optional[Dict[str, Any]]:
        """
        Get consolidated evidence packet from extractor observations.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            
        Returns:
            Consolidated evidence packet or None if not found
        """
        # Create criterion key
        criterion_key = f"{dimension_id}:{criterion_id}"
        
        # Look for extraction_completed observations from extractors
        for observation in self.context.get_agent_observations(observation_type="extraction_completed"):
            content = observation.get("content", {})
            if "consolidated_evidence" in content:
                # Check if this packet contains our criterion
                if criterion_key in content["consolidated_evidence"]:
                    return content["consolidated_evidence"][criterion_key]
        
        # No consolidated evidence found
        return None
    
    async def _create_evidence_based_assessment(
        self, 
        dimension_id: str, 
        criterion: Dict[str, Any],
        consolidated_evidence: Dict[str, Any],
        semantic_group: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a structured assessment based on consolidated evidence and semantic context.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            consolidated_evidence: Consolidated evidence packet
            semantic_group: Semantic group this criterion belongs to
            
        Returns:
            Structured criterion assessment
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_method = criterion.get("scoring_method", "scale_1_5")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Get the comprehensive evidence summary
        comprehensive_analysis = consolidated_evidence.get("comprehensive_analysis", "")
        evidence_count = consolidated_evidence.get("evidence_count", 0)
        direct_assessment_justified = consolidated_evidence.get("direct_assessment_justified", "NO")
        suggested_rating_range = consolidated_evidence.get("suggested_rating_range", "")
        key_patterns = consolidated_evidence.get("key_patterns", [])
        contradictions = consolidated_evidence.get("contradictions", [])
        
        # Get evidence category counts
        evidence_by_category = consolidated_evidence.get("evidence_by_category", {})
        
        # Format scoring definitions
        scoring_text = ""
        for score, definition in scoring_definitions.items():
            scoring_text += f"- Score {score}: {definition}\n"
        
        # Get related criteria in same semantic group (if any)
        related_criteria = []
        if semantic_group:
            for related_criterion_id in semantic_group.get("criteria_ids", []):
                # Skip the current criterion
                if related_criterion_id == criterion_id:
                    continue
                    
                # Find the dimension for this criterion
                for dimension in self.context.framework.get("dimensions", []):
                    for criterion in dimension.get("criteria", []):
                        if criterion.get("id") == related_criterion_id:
                            related_criteria.append({
                                "id": related_criterion_id,
                                "name": criterion.get("name", ""),
                                "dimension": dimension.get("name", "")
                            })
                            break
        
        # Create human prompt for structured evaluation with semantic context
        human_prompt = f"""Evaluate the following criterion based on the consolidated evidence analysis.

CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_id}

SCORING DEFINITIONS:
{scoring_text}

SEMANTIC GROUP: {semantic_group.get('name', 'N/A')}
SEMANTIC EXPLANATION: {semantic_group.get('explanation', 'N/A')}

RELATED CRITERIA IN SAME SEMANTIC GROUP:
{json.dumps(related_criteria, indent=2) if related_criteria else "None"}

CONSOLIDATED EVIDENCE ANALYSIS:
{comprehensive_analysis}

KEY PATTERNS:
{json.dumps(key_patterns, indent=2) if key_patterns else "None identified"}

CONTRADICTIONS:
{json.dumps(contradictions, indent=2) if contradictions else "None identified"}

EVIDENCE STATISTICS:
- Total evidence items: {evidence_count}
- Direct assessment justified: {direct_assessment_justified}
- Suggested rating range: {suggested_rating_range}

Based on this consolidated evidence, provide a structured assessment with:
1. A numeric rating that best matches the scoring definitions
2. A clear rationale explaining why this rating is appropriate
3. Key strengths identified from the evidence (2-4 points)
4. Key weaknesses or gaps identified (2-4 points)
5. Your confidence level in this assessment (0.0-1.0)

Consider the semantic relationship to other criteria in the same group.
Align your rating precisely with the scoring definitions.
This criterion has {evidence_count} pieces of evidence that have been analyzed and consolidated."""

        # Create system prompt
        system_prompt = """You are an expert evaluator generating structured assessments with clear ratings and rationales.
Analyze the consolidated evidence to make a fair, well-justified evaluation based on scoring definitions.
Focus on creating a structured output that clearly explains the rating and highlights key strengths and weaknesses.
Consider both the specific evidence for the criterion AND its relationship to other criteria in the same semantic group."""
        
        # Add custom instructions if provided
        if self.custom_instructions:
            system_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{self.custom_instructions}"

        # Define schema for structured output
        assessment_schema = {
            "type": "object",
            "properties": {
                "rating": {"type": "number"},
                "rationale": {"type": "string"},
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "weaknesses": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "confidence": {"type": "number"},
                "evidence_summary": {"type": "string"},
                "semantic_insights": {"type": "string"}  # New field for semantic insights
            },
            "required": ["rating", "rationale", "strengths", "weaknesses", "confidence"]
        }

        # Call LLM for structured assessment
        assessment = await self._structured_output_call(
            prompt=human_prompt,
            output_schema=assessment_schema,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Create structured result
        result = {
            "id": criterion_id,
            "name": criterion_name,
            "rating": assessment.get("rating"),
            "rationale": assessment.get("rationale", ""),
            "strengths": assessment.get("strengths", []),
            "weaknesses": assessment.get("weaknesses", []),
            "confidence": assessment.get("confidence", 0.8),
            "evidence_count": evidence_count,
            "evidence_by_category": evidence_by_category,  # Include the category counts
            "evidence_summary": assessment.get("evidence_summary", "") or comprehensive_analysis,
            "assessment_type": "direct",  # Default, will be updated by caller when appropriate
            "semantic_group": semantic_group.get("name", ""),
            "semantic_insights": assessment.get("semantic_insights", "")
        }
        
        return result
    
    async def _create_evidence_based_assessment_from_raw(
        self, 
        dimension_id: str, 
        criterion: Dict[str, Any],
        evidence_list: List[Dict[str, Any]],
        semantic_group: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a structured assessment based on raw evidence (fallback method),
        including semantic context.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            evidence_list: List of evidence items
            semantic_group: Semantic group this criterion belongs to
            
        Returns:
            Structured criterion assessment
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_method = criterion.get("scoring_method", "scale_1_5")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Analyze evidence to determine if we can do direct assessment
        can_assess_directly = await self._analyze_raw_evidence_sufficiency(dimension_id, criterion, evidence_list)
        assessment_type = "direct" if can_assess_directly else "inferred"
        
        # Group evidence by relevance and sentiment
        grouped_evidence = self._group_raw_evidence(evidence_list)
        
        # Format evidence for the prompt
        evidence_text = self._format_evidence_for_evaluation(evidence_list)
        
        # Format scoring definitions
        scoring_text = ""
        for score, definition in scoring_definitions.items():
            scoring_text += f"- Score {score}: {definition}\n"
        
        # Get related criteria in same semantic group (if any)
        related_criteria = []
        if semantic_group:
            for related_criterion_id in semantic_group.get("criteria_ids", []):
                # Skip the current criterion
                if related_criterion_id == criterion_id:
                    continue
                    
                # Find the dimension for this criterion
                for dimension in self.context.framework.get("dimensions", []):
                    for criterion in dimension.get("criteria", []):
                        if criterion.get("id") == related_criterion_id:
                            related_criteria.append({
                                "id": related_criterion_id,
                                "name": criterion.get("name", ""),
                                "dimension": dimension.get("name", "")
                            })
                            break
        
        # Create human prompt for structured evaluation with semantic context
        human_prompt = f"""Evaluate the following criterion based on the available evidence.

CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_id}

SCORING DEFINITIONS:
{scoring_text}

SEMANTIC GROUP: {semantic_group.get('name', 'N/A')}
SEMANTIC EXPLANATION: {semantic_group.get('explanation', 'N/A')}

RELATED CRITERIA IN SAME SEMANTIC GROUP:
{json.dumps(related_criteria, indent=2) if related_criteria else "None"}

EVIDENCE:
{evidence_text}

EVIDENCE ASSESSMENT: The evidence {'is sufficient for direct assessment' if can_assess_directly else 'is not sufficient for direct assessment, inference required'}

Based on this evidence, provide a structured assessment with:
1. A numeric rating that best matches the scoring definitions
2. A clear rationale explaining why this rating is appropriate
3. Key strengths identified from the evidence (2-4 points)
4. Key weaknesses or gaps identified (2-4 points)
5. Your confidence level in this assessment (0.0-1.0)
6. Insights about how this criterion relates to others in its semantic group

Consider all evidence collectively, weighing direct evidence more heavily than indirect.
Consider both the specific evidence for the criterion AND its relationship to other criteria in the same semantic group.
Align your rating precisely with the scoring definitions.
This is a {'DIRECT' if can_assess_directly else 'INFERRED'} assessment based on the evidence."""

        # Create system prompt
        system_prompt = """You are an expert evaluator generating structured assessments with clear ratings and rationales.
Analyze the available evidence to make a fair, well-justified evaluation based on scoring definitions.
Focus on creating a structured output that clearly explains the rating and highlights key strengths and weaknesses.
Consider both the specific evidence for the criterion AND its relationship to other criteria in the same semantic group."""
        
        # Add custom instructions if provided
        if self.custom_instructions:
            system_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{self.custom_instructions}"

        # Define schema for structured output
        assessment_schema = {
            "type": "object",
            "properties": {
                "rating": {"type": "number"},
                "rationale": {"type": "string"},
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "weaknesses": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "confidence": {"type": "number"},
                "evidence_summary": {"type": "string"},
                "semantic_insights": {"type": "string"}  # New field for semantic insights
            },
            "required": ["rating", "rationale", "strengths", "weaknesses", "confidence"]
        }

        # Call LLM for structured assessment
        assessment = await self._structured_output_call(
            prompt=human_prompt,
            output_schema=assessment_schema,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Adjust confidence based on assessment type
        confidence = assessment.get("confidence", 0.7)
        if assessment_type == "inferred":
            confidence = min(0.6, confidence)  # Cap inferred confidence
            
        # Create structured result
        result = {
            "id": criterion_id,
            "name": criterion_name,
            "rating": assessment.get("rating"),
            "rationale": assessment.get("rationale", ""),
            "strengths": assessment.get("strengths", []),
            "weaknesses": assessment.get("weaknesses", []),
            "confidence": confidence,
            "evidence_count": len(evidence_list),
            "evidence_summary": assessment.get("evidence_summary", ""),
            "assessment_type": assessment_type,
            "evidence_by_category": self._get_evidence_category_counts(grouped_evidence),
            "semantic_group": semantic_group.get("name", ""),
            "semantic_insights": assessment.get("semantic_insights", "")
        }
        
        return result
    
    async def _analyze_raw_evidence_sufficiency(
        self, 
        dimension_id: str, 
        criterion: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> bool:
        """
        Analyze raw evidence to determine if it's sufficient for direct assessment.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            evidence_list: List of evidence items
            
        Returns:
            True if evidence is sufficient for direct assessment, False otherwise
        """
        # If no evidence, definitely not sufficient
        if not evidence_list:
            return False
        
        # Count direct evidence
        direct_evidence_count = 0
        strong_evidence_count = 0
        
        for evidence in evidence_list:
            metadata = evidence.get("metadata", {})
            relevance_level = metadata.get("relevance_level", "")
            sufficiency = metadata.get("sufficiency_indicator", "")
            
            if relevance_level == "Direct":
                direct_evidence_count += 1
                
            if sufficiency == "Strong":
                strong_evidence_count += 1
        
        # Simple heuristic for sufficiency
        if direct_evidence_count >= 2 and strong_evidence_count >= 1:
            return True
        elif direct_evidence_count >= 3:
            return True
        elif strong_evidence_count >= 2:
            return True
        else:
            return False
    
    def _group_raw_evidence(self, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Group raw evidence by relevance and sentiment.
        
        Args:
            evidence_list: List of evidence items
            
        Returns:
            Evidence grouped by relevance and sentiment
        """
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
            metadata = evidence.get("metadata", {})
            relevance = metadata.get("relevance_level", "Direct")
            sentiment = metadata.get("sentiment", "Neutral")
            
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
                
        return grouped_evidence
    
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
            sum(len(items) for sentiments in grouped_evidence.get("direct", {}).values() for items in sentiments if isinstance(sentiments, dict)) +
            sum(len(items) for sentiments in grouped_evidence.get("indirect", {}).values() for items in sentiments if isinstance(sentiments, dict)) +
            len(grouped_evidence.get("contextual_implied", []))
        )
        
        return counts
    
    def _format_evidence_for_evaluation(self, evidence_list: List[Dict[str, Any]]) -> str:
        """
        Format evidence collection for evaluation.
        
        Args:
            evidence_list: List of evidence items
            
        Returns:
            Formatted evidence text
        """
        if not evidence_list:
            return "No evidence found."
            
        # Group evidence by relevance level
        grouped = {
            "Direct": [],
            "Indirect": [],
            "Contextual": [],
            "Implied": []
        }
        
        for evidence in evidence_list:
            # Get evidence text and metadata
            text = evidence.get("text", "")
            metadata = evidence.get("metadata", {})
            relevance_level = metadata.get("relevance_level", "Direct")
            
            # Default to Direct if not specified
            if not relevance_level or relevance_level not in grouped:
                relevance_level = "Direct"
            
            # Add to appropriate group
            grouped[relevance_level].append({
                "text": text,
                "relevance": metadata.get("relevance_explanation", ""),
                "confidence": metadata.get("confidence", 0.8),
                "sentiment": metadata.get("sentiment", "Neutral"),
                "sufficiency": metadata.get("sufficiency_indicator", "Moderate")
            })
        
        # Format evidence by relevance level
        evidence_text = ""
        
        for level, items in grouped.items():
            if not items:
                continue
                
            evidence_text += f"\n== {level} Evidence ({len(items)} items) ==\n\n"
            
            for i, evidence in enumerate(items):
                evidence_text += f"Evidence {i+1}:\n"
                evidence_text += f"Text: {evidence['text']}\n"
                evidence_text += f"Relevance: {evidence['relevance']}\n"
                evidence_text += f"Confidence: {evidence['confidence']}\n"
                evidence_text += f"Sentiment: {evidence['sentiment']}\n"
                evidence_text += f"Sufficiency: {evidence['sufficiency']}\n\n"
        
        return evidence_text
    
    async def _create_inferred_assessment(
        self, 
        dimension_id: str, 
        criterion: Dict[str, Any],
        consolidated_evidence: Optional[Dict[str, Any]] = None,
        semantic_group: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create an inferred assessment when direct evidence is insufficient,
        with semantic context.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            consolidated_evidence: Optional consolidated evidence packet
            semantic_group: Semantic group this criterion belongs to
            
        Returns:
            Inferred assessment or None if inference not possible
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_method = criterion.get("scoring_method", "scale_1_5")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Format scoring definitions
        scoring_text = ""
        for score, definition in scoring_definitions.items():
            scoring_text += f"- Score {score}: {definition}\n"
        
        # Get dimension info for context
        dimension_name = "Unknown Dimension"
        for dimension in self.context.framework.get("dimensions", []):
            if dimension.get("id") == dimension_id:
                dimension_name = dimension.get("name", dimension_name)
                break
        
        # Get framework info for context
        framework_name = self.context.framework.get("name", "Assessment Framework")
        
        # Create evidence context based on what's available
        evidence_context = ""
        if consolidated_evidence:
            evidence_context = f"""While direct evidence is insufficient for a confident assessment,
there is some limited evidence available:

{consolidated_evidence.get('comprehensive_analysis', '')}

Based on this limited evidence, careful inference may be possible."""
        else:
            evidence_context = """No direct evidence was found for this criterion in the document.
You'll need to make an assessment based on general context, related criteria, and reasonable assumptions."""
        
        # Get related criteria in same semantic group (if any)
        related_criteria = []
        related_assessments = []
        if semantic_group:
            for related_criterion_id in semantic_group.get("criteria_ids", []):
                # Skip the current criterion
                if related_criterion_id == criterion_id:
                    continue
                    
                # Find the dimension for this criterion
                for dimension in self.context.framework.get("dimensions", []):
                    for criterion in dimension.get("criteria", []):
                        if criterion.get("id") == related_criterion_id:
                            # Add to related criteria
                            related_criteria.append({
                                "id": related_criterion_id,
                                "name": criterion.get("name", ""),
                                "dimension": dimension.get("name", "")
                            })
                            
                            # Check if this criterion has been assessed
                            related_assessment = self.context.get_criterion_assessment(
                                dimension.get("id", ""), related_criterion_id
                            )
                            
                            if related_assessment and related_assessment.get("rating") is not None:
                                related_assessments.append({
                                    "id": related_criterion_id,
                                    "name": criterion.get("name", ""),
                                    "rating": related_assessment.get("rating"),
                                    "rationale": related_assessment.get("rationale", ""),
                                    "assessment_type": related_assessment.get("assessment_type", "unknown")
                                })
                            break
        
        # Prepare prompt for inference
        system_prompt = """You are an expert evaluator making inferences when direct evidence is lacking. 
Be cautious and conservative with inferences, and clearly indicate the level of uncertainty.
Consider how this criterion relates to others in the same semantic group when making your inference.
Only infer a rating if there is a reasonable basis for doing so."""
        
        human_prompt = f"""Determine if an inferred assessment can be made for the following criterion that lacks sufficient direct evidence.

FRAMEWORK: {framework_name}
CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_name}

SCORING DEFINITIONS:
{scoring_text}

SEMANTIC GROUP: {semantic_group.get('name', 'N/A') if semantic_group else 'N/A'}
SEMANTIC EXPLANATION: {semantic_group.get('explanation', 'N/A') if semantic_group else 'N/A'}

RELATED CRITERIA IN SAME SEMANTIC GROUP:
{json.dumps(related_criteria, indent=2) if related_criteria else "None"}

ASSESSMENTS OF RELATED CRITERIA:
{json.dumps(related_assessments, indent=2) if related_assessments else "None completed yet"}

EVIDENCE CONTEXT:
{evidence_context}

This criterion lacks sufficient direct evidence for a confident assessment. Based on available context:

1. Determine if it's appropriate to infer a rating (consider semantic relationships with other criteria)
2. If appropriate, provide an inferred rating that best matches the scoring definitions
3. Explain clearly why you've made this inference and the level of confidence
4. Note key assumptions made in this inference
5. Explain how this criterion relates to others in its semantic group

Be conservative - only infer a rating when reasonable to do so.
Clearly mark your response as an inference and explain your reasoning transparently."""

        # Define schema for inference
        inference_schema = {
            "type": "object",
            "properties": {
                "inference_possible": {"type": "boolean"},
                "rating": {"type": ["number", "null"]},
                "rationale": {"type": "string"},
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "confidence": {"type": "number"},
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "weaknesses": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "semantic_insights": {"type": "string"}
            },
            "required": ["inference_possible", "rationale", "confidence"]
        }

        # Call LLM for inference
        inference = await self._structured_output_call(
            prompt=human_prompt,
            output_schema=inference_schema,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Check if inference is possible
        inference_possible = inference.get("inference_possible", False)
        rating = inference.get("rating")
        confidence = inference.get("confidence", 0.0)
        
        # Only proceed if inference is possible and confidence is above threshold
        if inference_possible and rating is not None and confidence >= self.confidence_threshold:
            # Create structured result
            result = {
                "id": criterion_id,
                "name": criterion_name,
                "rating": rating,
                "rationale": f"[INFERRED] {inference.get('rationale', '')}",
                "strengths": inference.get("strengths", []),
                "weaknesses": inference.get("weaknesses", []),
                "assumptions": inference.get("assumptions", []),
                "confidence": confidence,
                "evidence_count": 0,
                "assessment_type": "inferred",
                "inferred": True,
                "semantic_group": semantic_group.get("name", "") if semantic_group else "",
                "semantic_insights": inference.get("semantic_insights", "")
            }
            
            return result
        
        # Inference not possible with sufficient confidence
        return None
    
    async def _create_inferred_assessment_without_evidence(
        self, 
        dimension_id: str, 
        criterion: Dict[str, Any],
        semantic_group: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an inferred assessment when no evidence is available,
        using broader document context and semantic relationships.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            semantic_group: Semantic group this criterion belongs to
            
        Returns:
            Inferred assessment or None if inference not possible
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        
        # Get dimension info
        dimension_name = "Unknown Dimension"
        for dimension in self.context.framework.get("dimensions", []):
            if dimension.get("id") == dimension_id:
                dimension_name = dimension.get("name", dimension_name)
                break
        
        # Get related criteria in same semantic group (if any)
        related_criteria = []
        related_assessments = []
        if semantic_group:
            for related_criterion_id in semantic_group.get("criteria_ids", []):
                # Skip the current criterion
                if related_criterion_id == criterion_id:
                    continue
                    
                # Find the dimension for this criterion
                for dimension in self.context.framework.get("dimensions", []):
                    for criterion in dimension.get("criteria", []):
                        if criterion.get("id") == related_criterion_id:
                            # Add to related criteria
                            related_criteria.append({
                                "id": related_criterion_id,
                                "name": criterion.get("name", ""),
                                "dimension": dimension.get("name", "")
                            })
                            
                            # Check if this criterion has been assessed
                            related_assessment = self.context.get_criterion_assessment(
                                dimension.get("id", ""), related_criterion_id
                            )
                            
                            if related_assessment and related_assessment.get("rating") is not None:
                                related_assessments.append({
                                    "id": related_criterion_id,
                                    "name": criterion.get("name", ""),
                                    "rating": related_assessment.get("rating"),
                                    "rationale": related_assessment.get("rationale", ""),
                                    "assessment_type": related_assessment.get("assessment_type", "unknown")
                                })
                            break
        
        # Get document preview for context
        document_text = self.context.document_text
        max_preview_length = 1500  # Limit preview length
        document_preview = document_text[:max_preview_length] + "..." if len(document_text) > max_preview_length else document_text
        
        # Create more sophisticated inference prompt
        system_prompt = """You are an expert evaluator making assessments with incomplete information.
When direct evidence is lacking, you must make careful inferences based on the general context and semantic relationships.
Be very clear about the limitations of your assessment and the assumptions you're making.
Only provide a rating when you can make a reasonable inference, otherwise indicate it's not possible."""
        
        human_prompt = f"""You need to assess a criterion without direct evidence. 
Make an inference based on general document context, semantic relationships, and your expertise.

CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_name}

SEMANTIC GROUP: {semantic_group.get('name', 'N/A') if semantic_group else 'N/A'}
SEMANTIC EXPLANATION: {semantic_group.get('explanation', 'N/A') if semantic_group else 'N/A'}

RELATED CRITERIA IN SAME SEMANTIC GROUP:
{json.dumps(related_criteria, indent=2) if related_criteria else "None"}

ASSESSMENTS OF RELATED CRITERIA:
{json.dumps(related_assessments, indent=2) if related_assessments else "None completed yet"}

DOCUMENT PREVIEW:
{document_preview}

IMPORTANT: There is NO direct evidence for this criterion in the document.
You must:
1. Determine if you can make a reasonable inference about this criterion based on:
   - General document context
   - Semantic relationship with other criteria in the same group
   - Assessments of related criteria (if available)
2. If possible, provide a rating on a 1-5 scale (1=poor, 5=excellent)
3. Explain your reasoning and clearly mark this as an inference
4. List your key assumptions
5. Provide a low confidence score reflecting the lack of direct evidence
6. Explain how this criterion relates to others in its semantic group

Be extremely careful with your inference. If the criterion is about highly specific information
that cannot be reasonably inferred from general context or semantic relationships,
state that inference is not possible and provide a NULL rating."""
        
        # Define schema for inference
        inference_schema = {
            "type": "object",
            "properties": {
                "inference_possible": {"type": "boolean"},
                "rating": {"type": ["number", "null"]},
                "rationale": {"type": "string"},
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "confidence": {"type": "number"},
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "weaknesses": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "semantic_insights": {"type": "string"}
            },
            "required": ["inference_possible", "rationale", "confidence"]
        }
        
        # Call LLM for inference
        inference = await self._structured_output_call(
            prompt=human_prompt,
            output_schema=inference_schema,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Check if inference is possible
        inference_possible = inference.get("inference_possible", False)
        rating = inference.get("rating")
        
        # Only proceed if inference is possible with a rating
        if inference_possible and rating is not None:
            # Create structured result
            result = {
                "id": criterion_id,
                "name": criterion_name,
                "rating": rating,
                "rationale": f"[INFERRED WITHOUT EVIDENCE] {inference.get('rationale', '')}",
                "strengths": inference.get("strengths", []),
                "weaknesses": inference.get("weaknesses", []),
                "assumptions": inference.get("assumptions", []),
                "confidence": min(0.3, inference.get("confidence", 0.2)),  # Cap at very low confidence
                "evidence_count": 0,
                "assessment_type": "inferred",
                "inferred": True,
                "semantic_group": semantic_group.get("name", "") if semantic_group else "",
                "semantic_insights": inference.get("semantic_insights", "")
            }
            
            return result
        
        # Inference not possible
        return None
    
    async def _generate_dimension_summary(
        self, 
        dimension: Dict[str, Any],
        criteria_results: Dict[str, Dict[str, Any]],
        assessment_types: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Generate a structured summary for a dimension with semantic awareness.
        
        Args:
            dimension: Framework dimension
            criteria_results: Results for criteria in this dimension
            assessment_types: Count of different assessment types
            
        Returns:
            Structured dimension summary
        """
        dimension_id = dimension.get("id", "")
        dimension_name = dimension.get("name", "")
        
        # No criteria results
        if not criteria_results:
            return {
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": None,
                "criteria_assessed": 0,
                "criteria_total": len(dimension.get("criteria", [])),
                "strengths": [],
                "weaknesses": [],
                "summary": "No criteria assessed for this dimension."
            }
        
        # Collect criteria information with semantic group info
        criteria_info = []
        ratings = []
        semantic_groups_in_dimension = set()
        
        for criterion_id, result in criteria_results.items():
            # Find criterion name
            criterion_name = criterion_id
            for c in dimension.get("criteria", []):
                if c.get("id") == criterion_id:
                    criterion_name = c.get("name", criterion_id)
                    break
            
            # Add semantic group info
            semantic_group_name = result.get("semantic_group", "")
            if semantic_group_name:
                semantic_groups_in_dimension.add(semantic_group_name)
            
            # Add to list if rating is available
            if result.get("rating") is not None:
                ratings.append(result["rating"])
                
                criteria_info.append({
                    "id": criterion_id,
                    "name": criterion_name,
                    "rating": result["rating"],
                    "rationale": result.get("rationale", ""),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "assessment_type": result.get("assessment_type", "unknown"),
                    "semantic_group": semantic_group_name,
                    "semantic_insights": result.get("semantic_insights", "")
                })
        
        # Calculate average rating
        average_rating = sum(ratings) / len(ratings) if ratings else None
        
        # Create context for dimension summary
        summary_context = f"""Assessment Types:
- Direct Assessments: {assessment_types.get('direct', 0)}
- Inferred Assessments: {assessment_types.get('inferred', 0)}
- Insufficient Evidence: {assessment_types.get('insufficient_evidence', 0)}

Semantic Groups in Dimension:
{', '.join(semantic_groups_in_dimension) if semantic_groups_in_dimension else 'None'}"""
        
        # Format criteria info for prompt
        criteria_text = json.dumps(criteria_info, indent=2)
        
        # Create prompt for dimension summary
        system_prompt = """You are an expert evaluator creating dimension summaries.
Synthesize the results of multiple criteria into a cohesive dimension assessment.
Identify key patterns, strengths, and weaknesses across the criteria, considering both the assessment types
and the semantic relationships between criteria.
When criteria belong to semantic groups that span multiple dimensions, consider these relationships in your analysis."""
        
        human_prompt = f"""Generate a summary for dimension: {dimension_name}

CRITERIA ASSESSMENTS:
{criteria_text}

ASSESSMENT CONTEXT:
{summary_context}

Based on these criteria assessments, provide:
1. 3-5 key strengths across the criteria in this dimension
2. 3-5 key weaknesses or areas for improvement
3. A concise summary of the dimension's overall assessment
4. Insights about how semantic relationships across dimensions influence this area

Focus on identifying patterns and themes that emerge across multiple criteria.
Be specific and substantive in your observations.
Consider the reliability of the assessments, noting where they are based on direct evidence versus inference.
If criteria belong to semantic groups that span multiple dimensions, consider these cross-dimensional relationships."""

        # Define schema for summary
        summary_schema = {
            "type": "object",
            "properties": {
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "weaknesses": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "summary": {"type": "string"},
                "semantic_insights": {"type": "string"}
            },
            "required": ["strengths", "weaknesses", "summary"]
        }

        # Call LLM for dimension summary
        summary_result = await self._structured_output_call(
            prompt=human_prompt,
            output_schema=summary_schema,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Create dimension summary
        dimension_summary = {
            "id": dimension_id,
            "name": dimension_name,
            "average_rating": average_rating,
            "criteria_assessed": len(ratings),
            "criteria_total": len(dimension.get("criteria", [])),
            "strengths": summary_result.get("strengths", []),
            "weaknesses": summary_result.get("weaknesses", []),
            "summary": summary_result.get("summary", ""),
            "assessment_types": assessment_types,
            "semantic_insights": summary_result.get("semantic_insights", ""),
            "semantic_groups": list(semantic_groups_in_dimension)
        }
        
        return dimension_summary
    
    async def _generate_semantic_group_insights(self) -> Dict[str, Any]:
        """
        Generate insights focused on semantic groups spanning dimensions.
        
        Returns:
            Semantic group insights dictionary
        """
        self.logger.info(f"Generating insights for {len(self.semantic_groups)} semantic groups")
        
        # Initialize results
        semantic_insights = {
            "groups": []
        }
        
        # Process each semantic group
        for group in self.semantic_groups:
            group_name = group.get("name", "Unknown Group")
            group_explanation = group.get("explanation", "")
            criteria_ids = group.get("criteria_ids", [])
            
            self.logger.info(f"Analyzing semantic group: {group_name} with {len(criteria_ids)} criteria")
            
            # Collect assessments for all criteria in this group
            criteria_assessments = []
            
            for criterion_id in criteria_ids:
                # Find the dimension for this criterion
                dimension_id = self._find_dimension_for_criterion(criterion_id)
                
                if dimension_id:
                    # Get criterion assessment
                    assessment = self.context.get_criterion_assessment(dimension_id, criterion_id)
                    
                    if assessment:
                        # Get criterion details
                        criterion_name = criterion_id
                        for dimension in self.context.framework.get("dimensions", []):
                            if dimension.get("id") == dimension_id:
                                for criterion in dimension.get("criteria", []):
                                    if criterion.get("id") == criterion_id:
                                        criterion_name = criterion.get("name", criterion_id)
                                        criterion_question = criterion.get("question", "")
                                        break
                        
                        criteria_assessments.append({
                            "criterion_id": criterion_id,
                            "name": criterion_name,
                            "dimension_id": dimension_id,
                            "rating": assessment.get("rating"),
                            "rationale": assessment.get("rationale", ""),
                            "strengths": assessment.get("strengths", []),
                            "weaknesses": assessment.get("weaknesses", []),
                            "assessment_type": assessment.get("assessment_type", "unknown"),
                            "evidence_count": assessment.get("evidence_count", 0)
                        })
            
            # Only analyze groups with at least 1 assessment
            if criteria_assessments:
                # Calculate average rating for the group
                ratings = [a.get("rating") for a in criteria_assessments if a.get("rating") is not None]
                average_rating = sum(ratings) / len(ratings) if ratings else None
                
                # Create prompt for semantic group analysis
                system_prompt = """You are an expert analyst identifying patterns across semantically related criteria.
Analyze how these criteria relate to each other and identify key insights that emerge 
when considering these semantically related criteria as a group."""
                
                human_prompt = f"""Analyze the following semantically related criteria in group "{group_name}":

SEMANTIC GROUP EXPLANATION: {group_explanation}

CRITERIA ASSESSMENTS:
{json.dumps(criteria_assessments, indent=2)}

These criteria are semantically related but may span different dimensions in the framework.
Analyze the assessments to:

1. Identify key patterns or themes that emerge when viewing these criteria as a semantic group
2. Identify any contradictions or tensions between assessments in this group
3. Determine overall strengths and weaknesses in this semantic area
4. Provide insights that would not be apparent when viewing criteria by dimension alone

Your analysis should focus on the semantic relationship between criteria."""

                # Define schema for analysis
                analysis_schema = {
                    "type": "object",
                    "properties": {
                        "patterns": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "contradictions": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "strengths": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "weaknesses": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "cross_dimensional_insights": {"type": "string"}
                    },
                    "required": ["patterns", "strengths", "weaknesses"]
                }

                # Call LLM for semantic group analysis
                analysis_result = await self._structured_output_call(
                    prompt=human_prompt,
                    output_schema=analysis_schema,
                    system_prompt=system_prompt,
                    temperature=0.3
                )
                
                # Create semantic group insight
                group_insight = {
                    "name": group_name,
                    "explanation": group_explanation,
                    "criteria_ids": criteria_ids,
                    "criteria_assessed": len(criteria_assessments),
                    "average_rating": average_rating,
                    "patterns": analysis_result.get("patterns", []),
                    "contradictions": analysis_result.get("contradictions", []),
                    "strengths": analysis_result.get("strengths", []),
                    "weaknesses": analysis_result.get("weaknesses", []),
                    "cross_dimensional_insights": analysis_result.get("cross_dimensional_insights", "")
                }
                
                semantic_insights["groups"].append(group_insight)
            else:
                self.logger.warning(f"No assessments found for semantic group: {group_name}")
        
        # Add overview
        semantic_insights["overview"] = {
            "total_groups": len(self.semantic_groups),
            "groups_with_insights": len(semantic_insights["groups"]),
            "framework_name": self.context.framework.get("name", "Assessment Framework")
        }
        
        return semantic_insights
    
    def _find_dimension_for_criterion(self, criterion_id: str) -> Optional[str]:
        """
        Find which dimension a criterion belongs to.
        
        Args:
            criterion_id: ID of the criterion
            
        Returns:
            Dimension ID or None if not found
        """
        for dimension in self.context.framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            
            for criterion in dimension.get("criteria", []):
                if criterion.get("id") == criterion_id:
                    return dimension_id
        
        return None
    
    async def _generate_overall_assessment(
        self, 
        dimension_results: Dict[str, Dict[str, Any]],
        dimensions: List[Dict[str, Any]],
        semantic_group_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate an overall assessment based on all dimension evaluations
        and semantic group insights.
        
        Args:
            dimension_results: Results for all dimensions
            dimensions: Framework dimensions
            semantic_group_insights: Semantic group insights
            
        Returns:
            Structured overall assessment
        """
        # Create dimension name lookup
        dimension_names = {}
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            if dimension_id:
                dimension_names[dimension_id] = dimension.get("name", dimension_id)
        
        # Collect dimension information
        dimension_info = []
        dimension_ratings = []
        total_criteria_assessed = 0
        total_criteria = 0
        assessment_types = {"direct": 0, "inferred": 0, "insufficient_evidence": 0}
        
        for dimension_id, results in dimension_results.items():
            dimension_name = dimension_names.get(dimension_id, dimension_id)
            summary = results.get("summary", {})
            average_rating = summary.get("average_rating")
            
            # Count assessed criteria
            criteria_assessed = summary.get("criteria_assessed", 0)
            criteria_total = summary.get("criteria_total", 0)
            total_criteria_assessed += criteria_assessed
            total_criteria += criteria_total
            
            # Track assessment types
            dim_assessment_types = results.get("assessment_types", {})
            for atype, count in dim_assessment_types.items():
                assessment_types[atype] = assessment_types.get(atype, 0) + count
            
            # Add to dimension ratings if available
            if average_rating is not None:
                dimension_ratings.append(average_rating)
                
            # Add to dimension info
            dimension_info.append({
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": average_rating,
                "strengths": summary.get("strengths", []),
                "weaknesses": summary.get("weaknesses", []),
                "summary": summary.get("summary", ""),
                "semantic_insights": summary.get("semantic_insights", "")
            })
        
        # Calculate overall rating
        overall_rating = sum(dimension_ratings) / len(dimension_ratings) if dimension_ratings else None
        criteria_coverage = total_criteria_assessed / max(1, total_criteria)
        
        # Format semantic group insights for the prompt
        semantic_groups_text = ""
        for group in semantic_group_insights.get("groups", []):
            semantic_groups_text += f"\nGROUP: {group.get('name', 'Unknown')}\n"
            semantic_groups_text += f"Patterns: {json.dumps(group.get('patterns', []))}\n"
            semantic_groups_text += f"Strengths: {json.dumps(group.get('strengths', []))}\n"
            semantic_groups_text += f"Weaknesses: {json.dumps(group.get('weaknesses', []))}\n"
            semantic_groups_text += f"Cross-dimensional insights: {group.get('cross_dimensional_insights', '')}\n"
        
        # Get framework name
        framework_name = self.context.framework.get("name", "Assessment Framework")
        
        # Format dimension info for prompt
        dimensions_text = json.dumps(dimension_info, indent=2)
        
        # Create assessment type context
        assessment_context = f"""Assessment Types:
- Direct Assessments: {assessment_types.get('direct', 0)}
- Inferred Assessments: {assessment_types.get('inferred', 0)}
- Insufficient Evidence: {assessment_types.get('insufficient_evidence', 0)}
- Total Criteria Assessed: {total_criteria_assessed} of {total_criteria} ({criteria_coverage:.1%})"""
        
        # Create prompt for overall assessment
        system_prompt = """You are an expert evaluator creating comprehensive assessment summaries.
Synthesize results across multiple dimensions and semantic groups into a cohesive overall assessment with clear recommendations.
Identify key patterns and insights that emerge when viewing the assessment holistically."""
        
        human_prompt = f"""Generate an overall assessment for: {framework_name}

DIMENSION ASSESSMENTS:
{dimensions_text}

SEMANTIC GROUP INSIGHTS:
{semantic_groups_text}

ASSESSMENT CONTEXT:
{assessment_context}

Based on these dimension assessments and semantic insights, provide:
1. An executive summary of the overall assessment (3-4 paragraphs)
2. 3-5 key strengths across all dimensions
3. 3-5 key areas for improvement across all dimensions
4. 3-5 specific recommendations based on the assessment
5. Cross-cutting insights from the semantic groups that span multiple dimensions

Focus on delivering a balanced, insightful assessment that captures the most important findings.
Be specific and actionable in your recommendations.
Consider the reliability of the assessments, noting where they are based on direct evidence versus inference.
Highlight insights that emerge from the semantic grouping that would not be apparent from dimensions alone."""

        # Define schema for overall assessment
        assessment_schema = {
            "type": "object",
            "properties": {
                "executive_summary": {"type": "string"},
                "key_strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "key_improvements": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "semantic_insights": {"type": "string"}
            },
            "required": ["executive_summary", "key_strengths", "key_improvements", "recommendations"]
        }

        # Call LLM for overall assessment
        assessment_result = await self._structured_output_call(
            prompt=human_prompt,
            output_schema=assessment_schema,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Create overall assessment
        overall_assessment = {
            "average_rating": overall_rating,
            "criteria_assessed": total_criteria_assessed,
            "criteria_total": total_criteria,
            "criteria_coverage": criteria_coverage,
            "dimension_count": len(dimension_info),
            "executive_summary": assessment_result.get("executive_summary", ""),
            "key_strengths": assessment_result.get("key_strengths", []),
            "key_improvements": assessment_result.get("key_improvements", []),
            "recommendations": assessment_result.get("recommendations", []),
            "assessment_types": assessment_types,
            "direct_assessment_percentage": assessment_types.get("direct", 0) / max(1, total_criteria_assessed),
            "semantic_insights": assessment_result.get("semantic_insights", ""),
            "timestamp": time.time()
        }
        
        return overall_assessment