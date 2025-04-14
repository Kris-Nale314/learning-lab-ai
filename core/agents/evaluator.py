"""
Enhanced Evaluator Agent - Better distinction between direct and inferred assessments

This agent analyzes evidence packets to produce structured assessments with clear
ratings, rationales, and proper indication of whether assessments are direct or inferred.
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class EvaluatorAgent(BaseAgent):
    """
    Enhanced evaluator for better distinction between direct and inferred assessments.
    
    The Enhanced Evaluator is responsible for:
    1. Analyzing consolidated evidence packets for each criterion
    2. Properly distinguishing between direct and inferred assessments
    3. Generating well-justified ratings based on scoring definitions
    4. Providing detailed rationales with strengths and weaknesses
    5. Creating dimension-level summaries and insights
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
        
        self.logger.info(f"{name} initialized with evaluation_type={self.evaluation_type}")
        
    async def process(self) -> Dict[str, Any]:
        """
        Evaluate framework criteria based on consolidated evidence packets,
        with clear distinction between direct and inferred assessments.
        
        Returns:
            Structured evaluation results aligned with the schema
        """
        self.logger.info("Starting structured criteria evaluation")
        self.start_timer()
        
        try:
            # Get framework dimensions and criteria
            framework = self.context.framework
            dimensions = framework.get("dimensions", [])
            
            # Initialize assessment structure
            structured_assessment = {
                "dimensions": {},
                "overall": {}
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
            
            # Generate overall assessment
            overall_assessment = await self._generate_overall_assessment(
                structured_assessment["dimensions"], 
                dimensions
            )
            structured_assessment["overall"] = overall_assessment
            
            # Set overall assessment in context
            self.context.set_overall_assessment(overall_assessment)
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Structured evaluation completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("evaluation_completed", {
                "dimensions_evaluated": len(structured_assessment["dimensions"]),
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
                
            # Evaluate criterion
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
        
        # Generate dimension summary
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
        Evaluate a criterion based on consolidated evidence, with clear distinction
        between direct and inferred assessments.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            
        Returns:
            Structured criterion evaluation or None if no evidence and not inferring
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_method = criterion.get("scoring_method", "scale_1_5")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Get consolidated evidence packet if available
        consolidated_evidence = self._get_consolidated_evidence(dimension_id, criterion_id)
        
        # Check if we have a recommendation about direct assessment from the extractor
        assessment_justification = "unknown"
        if consolidated_evidence and "direct_assessment_justified" in consolidated_evidence:
            assessment_justification = consolidated_evidence["direct_assessment_justified"]
        
        # Determine if we should do direct or inferred assessment
        if consolidated_evidence and consolidated_evidence.get("evidence_count", 0) > 0:
            # We have a consolidated evidence packet with evidence
            
            # If recommendation is clearly YES, do direct assessment
            if assessment_justification == "YES":
                assessment = await self._create_evidence_based_assessment(
                    dimension_id, criterion, consolidated_evidence
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
                    dimension_id, criterion, consolidated_evidence
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
                    dimension_id, criterion, consolidated_evidence
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
        if not consolidated_evidence or consolidated_evidence.get("evidence_count", 0) == 0:
            # Get raw evidence for this criterion
            evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
            
            # If we have evidence but no consolidated packet, use raw evidence
            if evidence_list and len(evidence_list) > 0:
                # Create structured assessment from raw evidence
                assessment = await self._create_evidence_based_assessment_from_raw(
                    dimension_id, criterion, evidence_list
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
                
            # If no evidence and inference is allowed
            elif self.infer_missing:
                # Try to create inferred assessment
                assessment = await self._create_inferred_assessment(
                    dimension_id, criterion, None
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
        # Look for extraction_completed observations from extractors
        for observation in self.context.get_agent_observations(observation_type="extraction_completed"):
            content = observation.get("content", {})
            if "consolidated_evidence" in content:
                # Check if this packet contains our criterion
                key = f"{dimension_id}:{criterion_id}"
                if key in content["consolidated_evidence"]:
                    return content["consolidated_evidence"][key]
        
        # No consolidated evidence found
        return None
    
    async def _create_evidence_based_assessment(
        self, 
        dimension_id: str, 
        criterion: Dict[str, Any],
        consolidated_evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a structured assessment based on consolidated evidence.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            consolidated_evidence: Consolidated evidence packet
            
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
        
        # Create human prompt for structured evaluation
        human_prompt = f"""Evaluate the following criterion based on the consolidated evidence analysis.

CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_id}

SCORING DEFINITIONS:
{scoring_text}

CONSOLIDATED EVIDENCE ANALYSIS:
{comprehensive_analysis}

KEY PATTERNS:
{json.dumps(key_patterns, indent=2)}

CONTRADICTIONS:
{json.dumps(contradictions, indent=2)}

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

Align your rating precisely with the scoring definitions.
This criterion has {evidence_count} pieces of evidence that have been analyzed and consolidated."""

        # Create system prompt
        system_prompt = """You are an expert evaluator generating structured assessments with clear ratings and rationales.
Analyze the consolidated evidence to make a fair, well-justified evaluation based on scoring definitions.
Focus on creating a structured output that clearly explains the rating and highlights key strengths and weaknesses."""
        
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
                "evidence_summary": {"type": "string"}
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
            "assessment_type": "direct"  # Default, will be updated by caller when appropriate
        }
        
        return result
    
    async def _create_evidence_based_assessment_from_raw(
        self, 
        dimension_id: str, 
        criterion: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a structured assessment based on raw evidence (fallback method).
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            evidence_list: List of evidence items
            
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
        
        # Create human prompt for structured evaluation
        human_prompt = f"""Evaluate the following criterion based on the available evidence.

CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_id}

SCORING DEFINITIONS:
{scoring_text}

EVIDENCE:
{evidence_text}

EVIDENCE ASSESSMENT: The evidence {'is sufficient for direct assessment' if can_assess_directly else 'is not sufficient for direct assessment, inference required'}

Based on this evidence, provide a structured assessment with:
1. A numeric rating that best matches the scoring definitions
2. A clear rationale explaining why this rating is appropriate
3. Key strengths identified from the evidence (2-4 points)
4. Key weaknesses or gaps identified (2-4 points)
5. Your confidence level in this assessment (0.0-1.0)

Consider all evidence collectively, weighing direct evidence more heavily than indirect.
Align your rating precisely with the scoring definitions.
This is a {'DIRECT' if can_assess_directly else 'INFERRED'} assessment based on the evidence."""

        # Create system prompt
        system_prompt = """You are an expert evaluator generating structured assessments with clear ratings and rationales.
Analyze the available evidence to make a fair, well-justified evaluation based on scoring definitions.
Focus on creating a structured output that clearly explains the rating and highlights key strengths and weaknesses."""
        
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
                "evidence_summary": {"type": "string"}
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
            "evidence_by_category": self._get_evidence_category_counts(grouped_evidence)
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
            sum(len(items) for items in grouped_evidence.get("direct", {}).values()) +
            sum(len(items) for items in grouped_evidence.get("indirect", {}).values()) +
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
        consolidated_evidence: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create an inferred assessment when direct evidence is insufficient.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            consolidated_evidence: Optional consolidated evidence packet
            
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
        
        # Prepare prompt for inference
        system_prompt = """You are an expert evaluator making inferences when direct evidence is lacking. 
Be cautious and conservative with inferences, and clearly indicate the level of uncertainty.
Only infer a rating if there is a reasonable basis for doing so."""
        
        human_prompt = f"""Determine if an inferred assessment can be made for the following criterion that lacks sufficient direct evidence.

FRAMEWORK: {framework_name}
CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_name}

SCORING DEFINITIONS:
{scoring_text}

EVIDENCE CONTEXT:
{evidence_context}

This criterion lacks sufficient direct evidence for a confident assessment. Based on available context:

1. Determine if it's appropriate to infer a rating (consider if silence on this topic is meaningful)
2. If appropriate, provide an inferred rating that best matches the scoring definitions
3. Explain clearly why you've made this inference and the level of confidence
4. Note key assumptions made in this inference

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
                }
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
                "inferred": True
            }
            
            return result
        
        # Inference not possible with sufficient confidence
        return None
    
    async def _generate_dimension_summary(
        self, 
        dimension: Dict[str, Any],
        criteria_results: Dict[str, Dict[str, Any]],
        assessment_types: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Generate a structured summary for a dimension.
        
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
        
        # Collect criteria information
        criteria_info = []
        ratings = []
        
        for criterion_id, result in criteria_results.items():
            # Find criterion name
            criterion_name = criterion_id
            for c in dimension.get("criteria", []):
                if c.get("id") == criterion_id:
                    criterion_name = c.get("name", criterion_id)
                    break
            
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
                    "assessment_type": result.get("assessment_type", "unknown")
                })
        
        # Calculate average rating
        average_rating = sum(ratings) / len(ratings) if ratings else None
        
        # Create context for dimension summary
        summary_context = f"""Assessment Types:
- Direct Assessments: {assessment_types.get('direct', 0)}
- Inferred Assessments: {assessment_types.get('inferred', 0)}
- Insufficient Evidence: {assessment_types.get('insufficient_evidence', 0)}"""
        
        # Format criteria info for prompt
        criteria_text = json.dumps(criteria_info, indent=2)
        
        # Create prompt for dimension summary
        system_prompt = """You are an expert evaluator creating dimension summaries.
Synthesize the results of multiple criteria into a cohesive dimension assessment.
Identify key patterns, strengths, and weaknesses across the criteria, considering the assessment types."""
        
        human_prompt = f"""Generate a summary for dimension: {dimension_name}

CRITERIA ASSESSMENTS:
{criteria_text}

ASSESSMENT CONTEXT:
{summary_context}

Based on these criteria assessments, provide:
1. 3-5 key strengths across the criteria in this dimension
2. 3-5 key weaknesses or areas for improvement
3. A concise summary of the dimension's overall assessment

Focus on identifying patterns and themes that emerge across multiple criteria.
Be specific and substantive in your observations.
Consider the reliability of the assessments, noting where they are based on direct evidence versus inference."""

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
                "summary": {"type": "string"}
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
            "assessment_types": assessment_types
        }
        
        return dimension_summary
    
    async def _generate_overall_assessment(
        self, 
        dimension_results: Dict[str, Dict[str, Any]],
        dimensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an overall assessment based on all dimension evaluations.
        
        Args:
            dimension_results: Results for all dimensions
            dimensions: Framework dimensions
            
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
                "summary": summary.get("summary", "")
            })
        
        # Calculate overall rating
        overall_rating = sum(dimension_ratings) / len(dimension_ratings) if dimension_ratings else None
        criteria_coverage = total_criteria_assessed / max(1, total_criteria)
        
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
Synthesize results across multiple dimensions into a cohesive overall assessment with clear recommendations.
Identify key patterns and insights that emerge when viewing the assessment holistically."""
        
        human_prompt = f"""Generate an overall assessment for: {framework_name}

DIMENSION ASSESSMENTS:
{dimensions_text}

ASSESSMENT CONTEXT:
{assessment_context}

Based on these dimension assessments, provide:
1. An executive summary of the overall assessment (3-4 paragraphs)
2. 3-5 key strengths across all dimensions
3. 3-5 key areas for improvement across all dimensions
4. 3-5 specific recommendations based on the assessment

Focus on delivering a balanced, insightful assessment that captures the most important findings.
Be specific and actionable in your recommendations.
Consider the reliability of the assessments, noting where they are based on direct evidence versus inference."""

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
                }
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
            "timestamp": time.time()
        }
        
        return overall_assessment