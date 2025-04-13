"""
Enhanced Evaluator Agent - Produces structured assessments from extracted evidence

This agent analyzes consolidated evidence from multiple extractors to evaluate
framework criteria, generating structured ratings and detailed rationales.
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class EvaluatorAgent(BaseAgent):
    """
    Evaluates framework criteria based on consolidated evidence.
    
    The Evaluator is responsible for:
    1. Analyzing consolidated evidence for each criterion
    2. Generating structured ratings based on scoring methods
    3. Providing detailed rationales for assessments
    4. Identifying cross-criterion relationships and patterns
    5. Producing holistic dimensional assessments
    """
    
    def __init__(
        self,
        llm,
        context: AssessmentContext,
        name: str = "Evaluator",
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Evaluator agent.
        
        Args:
            llm: Language model instance
            context: Assessment context
            name: Agent name
            options: Configuration options including evaluation strategy
        """
        super().__init__(name, "evaluator", llm, context, options or {})
        
        # Get evaluation configuration from options
        self.options = options or {}
        self.evaluation_type = self.options.get("evaluation_type", "evidence-based")
        self.infer_missing = self.options.get("infer_missing", False)
        self.confidence_threshold = self.options.get("confidence_threshold", 0.6)
        self.custom_instructions = self.options.get("instructions", "")
        
        self.logger.info(f"{name} initialized with evaluation_type={self.evaluation_type}")
        
    async def process(self) -> Dict[str, Any]:
        """
        Evaluate framework criteria based on extracted evidence.
        
        Returns:
            Structured evaluation results
        """
        self.logger.info("Starting criteria evaluation")
        self.start_timer()
        
        try:
            # Get framework dimensions and criteria
            framework = self.context.framework
            dimensions = framework.get("dimensions", [])
            
            # Process each dimension
            evaluation_results = {
                "dimensions": {},
                "overall": {},
                "criteria_count": 0,
                "assessed_criteria_count": 0,
                "missing_criteria_count": 0
            }
            
            total_dimensions = len(dimensions)
            for i, dimension in enumerate(dimensions):
                dimension_id = dimension.get("id", "")
                
                if not dimension_id:
                    self.logger.warning(f"Skipping dimension without ID at index {i}")
                    continue
                    
                # Update progress
                progress = (i + 1) / total_dimensions
                self.update_progress(progress, f"Evaluating dimension {i+1}/{total_dimensions}")
                
                # Evaluate dimension
                dimension_results = await self._evaluate_dimension(dimension)
                evaluation_results["dimensions"][dimension_id] = dimension_results
                
                # Update criteria counts
                evaluation_results["criteria_count"] += len(dimension.get("criteria", []))
                evaluation_results["assessed_criteria_count"] += len(dimension_results["criteria"])
            
            # Calculate missing criteria count
            evaluation_results["missing_criteria_count"] = (
                evaluation_results["criteria_count"] - evaluation_results["assessed_criteria_count"]
            )
            
            # Find cross-dimension patterns and relationships
            cross_dimension_insights = await self._analyze_cross_dimension_patterns(
                evaluation_results["dimensions"], dimensions
            )
            
            # Generate overall assessment
            overall_assessment = await self._generate_overall_assessment(
                evaluation_results["dimensions"], 
                dimensions,
                cross_dimension_insights
            )
            evaluation_results["overall"] = overall_assessment
            
            # Set overall assessment in context
            self.context.set_overall_assessment(overall_assessment)
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Criteria evaluation completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("evaluation_completed", {
                "dimensions_evaluated": len(evaluation_results["dimensions"]),
                "criteria_evaluated": evaluation_results["assessed_criteria_count"],
                "criteria_missing": evaluation_results["missing_criteria_count"],
                "time_taken": elapsed_time
            })
            
            return evaluation_results
            
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
        
        for criterion in criteria:
            criterion_id = criterion.get("id", "")
            
            if not criterion_id:
                continue
                
            # Evaluate criterion
            criterion_result = await self._evaluate_criterion(dimension_id, criterion)
            
            # Only include in results if we have an assessment
            if criterion_result and criterion_result.get("rating") is not None:
                criteria_results[criterion_id] = criterion_result
                criteria_ratings.append(criterion_result.get("rating"))
        
        # Calculate dimension metrics
        avg_rating = sum(criteria_ratings) / len(criteria_ratings) if criteria_ratings else None
        rating_counts = {}
        
        for rating in criteria_ratings:
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
        
        # Generate dimension insights based on criterion assessments
        dimension_insights = await self._generate_dimension_insights(
            dimension, criteria_results
        )
        
        # Generate dimension summary
        dimension_summary = {
            "id": dimension_id,
            "name": dimension_name,
            "average_rating": avg_rating,
            "criteria_count": len(criteria),
            "assessed_criteria_count": len(criteria_results),
            "rating_distribution": rating_counts,
            "strengths": dimension_insights.get("strengths", []),
            "weaknesses": dimension_insights.get("weaknesses", []),
            "insights": dimension_insights.get("insights", []),
            "summary": dimension_insights.get("summary", "")
        }
        
        # Set dimension summary in context
        self.context.set_dimension_summary(dimension_id, dimension_summary)
        
        return {
            "criteria": criteria_results,
            "summary": dimension_summary
        }
    
    async def _evaluate_criterion(self, dimension_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a criterion based on extracted evidence.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            
        Returns:
            Structured criterion evaluation
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_method = criterion.get("scoring_method", "scale_1_5")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Get evidence for this criterion
        evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
        
        # If no evidence and not inferring
        if not evidence_list and not self.infer_missing:
            self.logger.info(f"No evidence found for {dimension_id}:{criterion_id}, skipping evaluation")
            return None
        
        # Handle evidence-based criteria (just collecting evidence)
        if scoring_method == "evidence_based":
            if evidence_list:
                # Create structured assessment for evidence-based criteria
                summary = await self._create_evidence_based_assessment(
                    dimension_id, criterion, evidence_list
                )
                return summary
            elif self.infer_missing:
                return await self._create_inferred_assessment(dimension_id, criterion)
            else:
                return None
                
        else:  # Numeric scale (scale_1_5 etc.)
            # If we have evidence
            if evidence_list:
                # Evaluate the evidence to generate a rating
                return await self._create_scored_assessment(
                    dimension_id, criterion, evidence_list
                )
            # If no evidence and inferring
            elif self.infer_missing:
                return await self._create_inferred_assessment(dimension_id, criterion)
            # Default no evidence, not inferring
            else:
                return None
    
    async def _create_evidence_based_assessment(
        self, 
        dimension_id: str, 
        criterion: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create assessment for evidence-based criteria.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            evidence_list: List of evidence items
            
        Returns:
            Evidence-based assessment
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        
        # Format evidence for analysis
        evidence_text = self._format_evidence_text(evidence_list)
        
        # Prompt for evidence analysis
        system_prompt = """You are an expert evaluator analyzing evidence. Provide a structured assessment of the evidence related to a specific criterion."""
        
        human_prompt = f"""Analyze the following evidence related to this criterion:

CRITERION: {criterion_name}
QUESTION: {criterion_question}

EVIDENCE:
{evidence_text}

Please provide a structured assessment with:
1. A concise summary of the key findings from the evidence
2. The strengths identified (key positive aspects)
3. The weaknesses or gaps identified (areas lacking evidence or needing improvement)
4. Your confidence level in this assessment (0.0-1.0)

Your assessment should be focused and directly address the criterion question."""

        # Define schema for structured output
        assessment_schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "weaknesses": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "confidence": {"type": "number"}
            },
            "required": ["summary", "strengths", "weaknesses", "confidence"]
        }

        # Call LLM for structured assessment
        assessment, _ = await self._safe_llm_call(
            "generate_structured_output",
            prompt=human_prompt,
            output_schema=assessment_schema,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        # Create structured result
        result = {
            "criterion_id": criterion_id,
            "rating": len(evidence_list),  # Use evidence count as rating for evidence-based criteria
            "evidence_count": len(evidence_list),
            "evidence_ids": [ev.get("id") for ev in evidence_list if "id" in ev],
            "summary": assessment.get("summary", ""),
            "strengths": assessment.get("strengths", []),
            "weaknesses": assessment.get("weaknesses", []),
            "confidence": assessment.get("confidence", 0.8),
            "assessment_type": "evidence-based"
        }
        
        # Set assessment in context
        self.set_criterion_assessment(
            dimension_id=dimension_id,
            criterion_id=criterion_id,
            rating=result["rating"],
            rationale=result["summary"],
            confidence=result["confidence"]
        )
        
        return result
    
    async def _create_scored_assessment(
        self, 
        dimension_id: str, 
        criterion: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create scored assessment for criteria with rating scales.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            evidence_list: List of evidence items
            
        Returns:
            Scored assessment
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_method = criterion.get("scoring_method", "scale_1_5")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Format evidence text
        evidence_text = self._format_evidence_text(evidence_list)
        
        # Format scoring scale
        scoring_text = ""
        for score, definition in scoring_definitions.items():
            scoring_text += f"- Score {score}: {definition}\n"
        
        # Prompt for scored assessment
        system_prompt = """You are an expert evaluator providing structured ratings. Analyze the evidence and provide a detailed assessment with clear justification for your rating."""
        
        human_prompt = f"""Evaluate the following criterion based on the provided evidence.

CRITERION: {criterion_name}
QUESTION: {criterion_question}

SCORING SCALE:
{scoring_text}

EVIDENCE:
{evidence_text}

Based on this evidence, provide a structured assessment with:
1. A numeric rating from the scoring scale
2. A detailed rationale explaining your rating
3. Key strengths identified in the evidence
4. Key weaknesses or gaps identified
5. Your confidence level in this assessment (0.0-1.0)

Your assessment should directly address the criterion question and clearly justify the rating."""

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
                "confidence": {"type": "number"}
            },
            "required": ["rating", "rationale", "strengths", "weaknesses", "confidence"]
        }

        # Call LLM for structured assessment
        assessment, _ = await self._safe_llm_call(
            "generate_structured_output",
            prompt=human_prompt,
            output_schema=assessment_schema,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        # Create structured result
        result = {
            "criterion_id": criterion_id,
            "rating": assessment.get("rating"),
            "evidence_count": len(evidence_list),
            "evidence_ids": [ev.get("id") for ev in evidence_list if "id" in ev],
            "rationale": assessment.get("rationale", ""),
            "strengths": assessment.get("strengths", []),
            "weaknesses": assessment.get("weaknesses", []),
            "confidence": assessment.get("confidence", 0.8),
            "assessment_type": "scored"
        }
        
        # Set assessment in context
        self.set_criterion_assessment(
            dimension_id=dimension_id,
            criterion_id=criterion_id,
            rating=result["rating"],
            rationale=result["rationale"],
            confidence=result["confidence"]
        )
        
        return result
    
    async def _create_inferred_assessment(self, dimension_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an inferred assessment when no direct evidence is available.
        
        Args:
            dimension_id: ID of the dimension
            criterion: Criterion to evaluate
            
        Returns:
            Inferred assessment
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_method = criterion.get("scoring_method", "scale_1_5")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Get dimension info
        dimension_name = "Unknown Dimension"
        for dimension in self.context.framework.get("dimensions", []):
            if dimension.get("id") == dimension_id:
                dimension_name = dimension.get("name", dimension_name)
                break
        
        # Format scoring scale
        scoring_text = ""
        for score, definition in scoring_definitions.items():
            scoring_text += f"- Score {score}: {definition}\n"
        
        # Prompt for inferred assessment
        system_prompt = """You are an expert evaluator making inferences when direct evidence is lacking. Provide a structured assessment based on general knowledge and context, clearly marking it as inferred."""
        
        human_prompt = f"""Infer an assessment for the following criterion that lacks direct evidence.

CRITERION: {criterion_name}
QUESTION: {criterion_question}
DIMENSION: {dimension_name}
SCORING METHOD: {scoring_method}

SCORING SCALE:
{scoring_text}

Based on general knowledge and the context of this evaluation, provide a structured assessment with:
1. Whether an inference is possible
2. If possible, a numeric rating from the scoring scale
3. A detailed rationale explaining your inferred rating
4. Potential strengths (inferred)
5. Potential weaknesses (inferred)
6. Your confidence level in this inference (0.0-1.0)

Clearly mark this as an inference and explain your reasoning process."""

        # Define schema for structured output
        inference_schema = {
            "type": "object",
            "properties": {
                "inference_possible": {"type": "boolean"},
                "rating": {"type": ["number", "null"]},
                "rationale": {"type": "string"},
                "inferred_strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "inferred_weaknesses": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "confidence": {"type": "number"}
            },
            "required": ["inference_possible", "rationale", "inferred_strengths", "inferred_weaknesses", "confidence"]
        }

        # Call LLM for inference
        inference, _ = await self._safe_llm_call(
            "generate_structured_output",
            prompt=human_prompt,
            output_schema=inference_schema,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        # Process inference results
        inference_possible = inference.get("inference_possible", False)
        rating = inference.get("rating")
        rationale = inference.get("rationale", "")
        confidence = inference.get("confidence", 0.0)
        
        # Create structured result
        if inference_possible and rating is not None and confidence >= self.confidence_threshold:
            result = {
                "criterion_id": criterion_id,
                "rating": rating,
                "evidence_count": 0,
                "evidence_ids": [],
                "rationale": f"[INFERRED] {rationale}",
                "strengths": inference.get("inferred_strengths", []),
                "weaknesses": inference.get("inferred_weaknesses", []),
                "confidence": confidence,
                "assessment_type": "inferred",
                "inferred": True
            }
            
            # Set assessment in context
            self.set_criterion_assessment(
                dimension_id=dimension_id,
                criterion_id=criterion_id,
                rating=rating,
                rationale=result["rationale"],
                confidence=confidence
            )
            
            return result
        else:
            # Not confident enough for inference
            return None
    
    def _format_evidence_text(self, evidence_list: List[Dict[str, Any]]) -> str:
        """Format evidence list into text for prompts."""
        if not evidence_list:
            return "No evidence found."
            
        evidence_text = ""
        for i, evidence in enumerate(evidence_list):
            evidence_text += f"Evidence {i+1}:\n"
            evidence_text += f"{evidence.get('text', '')}\n"
            
            # Add confidence if available
            confidence = evidence.get("confidence", None)
            if confidence is not None:
                evidence_text += f"Confidence: {confidence}\n"
                
            # Add relevance if available
            relevance = evidence.get("relevance", None)
            if relevance:
                evidence_text += f"Relevance: {relevance}\n"
                
            evidence_text += "\n"
            
        return evidence_text
    
    async def _generate_dimension_insights(
        self,
        dimension: Dict[str, Any],
        criteria_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate insights for a dimension based on criterion assessments.
        
        Args:
            dimension: Framework dimension
            criteria_results: Results for criteria in the dimension
            
        Returns:
            Dimension insights
        """
        dimension_id = dimension.get("id", "")
        dimension_name = dimension.get("name", "")
        
        # Collect criteria information for prompt
        criteria_info = []
        for criterion_id, result in criteria_results.items():
            # Find criterion name
            criterion_name = criterion_id
            for c in dimension.get("criteria", []):
                if c.get("id") == criterion_id:
                    criterion_name = c.get("name", criterion_id)
                    break
            
            # Format criterion result
            criterion_info = {
                "name": criterion_name,
                "rating": result.get("rating"),
                "rationale": result.get("rationale", ""),
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "confidence": result.get("confidence", 0.0),
                "evidence_count": result.get("evidence_count", 0)
            }
            
            criteria_info.append(criterion_info)
        
        # If no criteria assessed, return empty insights
        if not criteria_info:
            return {
                "strengths": [],
                "weaknesses": [],
                "insights": [],
                "summary": ""
            }
        
        # Format criteria info for prompt
        criteria_text = json.dumps(criteria_info, indent=2)
        
        # Prompt for dimension insights
        system_prompt = """You are an expert analyst providing insights across multiple assessments. Identify patterns, strengths, weaknesses, and generate a holistic summary."""
        
        human_prompt = f"""Analyze the following assessments for the dimension: {dimension_name}

CRITERIA ASSESSMENTS:
{criteria_text}

Based on these assessments, provide:
1. Key strengths across the criteria (3-5 points)
2. Key weaknesses or gaps across the criteria (3-5 points)
3. Cross-cutting insights that emerge from analyzing all criteria together (2-3 insights)
4. A concise summary of the dimension as a whole

Focus on patterns and relationships between different criteria within this dimension."""

        # Define schema for structured output
        insights_schema = {
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
                "insights": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "summary": {"type": "string"}
            },
            "required": ["strengths", "weaknesses", "insights", "summary"]
        }

        # Call LLM for insights
        insights, _ = await self._safe_llm_call(
            "generate_structured_output",
            prompt=human_prompt,
            output_schema=insights_schema,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        return insights
    
    async def _analyze_cross_dimension_patterns(
        self,
        dimension_results: Dict[str, Dict[str, Any]],
        dimensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns and relationships across dimensions.
        
        Args:
            dimension_results: Results for all dimensions
            dimensions: Framework dimensions
            
        Returns:
            Cross-dimension insights
        """
        # Create dimension name lookup
        dimension_names = {}
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            if dimension_id:
                dimension_names[dimension_id] = dimension.get("name", dimension_id)
        
        # Collect dimension information for prompt
        dimensions_info = []
        for dimension_id, result in dimension_results.items():
            dimension_name = dimension_names.get(dimension_id, dimension_id)
            summary = result.get("summary", {})
            
            # Format dimension info
            dimension_info = {
                "name": dimension_name,
                "average_rating": summary.get("average_rating"),
                "strengths": summary.get("strengths", []),
                "weaknesses": summary.get("weaknesses", []),
                "insights": summary.get("insights", []),
                "summary": summary.get("summary", "")
            }
            
            dimensions_info.append(dimension_info)
        
        # If less than 2 dimensions assessed, skip cross-dimension analysis
        if len(dimensions_info) < 2:
            return {
                "relationships": [],
                "patterns": [],
                "insights": []
            }
        
        # Format dimensions info for prompt
        dimensions_text = json.dumps(dimensions_info, indent=2)
        
        # Prompt for cross-dimension analysis
        system_prompt = """You are an expert analyst identifying relationships and patterns across different dimensions. Focus on connections, interdependencies, and emergent patterns."""
        
        human_prompt = f"""Analyze the relationships between the following dimensions:

DIMENSION SUMMARIES:
{dimensions_text}

Based on these dimension summaries, provide:
1. Key relationships between dimensions (how do they influence each other?)
2. Cross-cutting patterns that emerge across multiple dimensions
3. Holistic insights that can only be seen when analyzing all dimensions together

Focus on identifying connections and interdependencies that wouldn't be visible when looking at dimensions in isolation."""

        # Define schema for structured output
        cross_schema = {
            "type": "object",
            "properties": {
                "relationships": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "patterns": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "insights": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["relationships", "patterns", "insights"]
        }

        # Call LLM for cross-dimension analysis
        cross_analysis, _ = await self._safe_llm_call(
            "generate_structured_output",
            prompt=human_prompt,
            output_schema=cross_schema,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        return cross_analysis
    
    async def _generate_overall_assessment(
        self, 
        dimension_results: Dict[str, Dict[str, Any]], 
        dimensions: List[Dict[str, Any]],
        cross_dimension_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate overall assessment for the framework.
        
        Args:
            dimension_results: Results for all dimensions
            dimensions: Framework dimensions
            cross_dimension_insights: Insights from cross-dimension analysis
            
        Returns:
            Overall assessment
        """
        # Create dimension name lookup
        dimension_names = {}
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            if dimension_id:
                dimension_names[dimension_id] = dimension.get("name", dimension_id)
        
        # Collect dimension metrics for summary
        dimension_metrics = []
        total_criteria_assessed = 0
        total_criteria = 0
        dimension_ratings = []
        
        for dimension_id, result in dimension_results.items():
            dimension_name = dimension_names.get(dimension_id, dimension_id)
            summary = result.get("summary", {})
            criteria_results = result.get("criteria", {})
            
            # Calculate metrics
            avg_rating = summary.get("average_rating")
            criteria_assessed = len(criteria_results)
            criteria_total = 0
            
            # Count total criteria in dimension
            for dim in dimensions:
                if dim.get("id") == dimension_id:
                    criteria_total = len(dim.get("criteria", []))
                    break
            
            # Add to totals
            total_criteria_assessed += criteria_assessed
            total_criteria += criteria_total
            
            if avg_rating is not None:
                dimension_ratings.append(avg_rating)
            
            # Format dimension metrics
            dimension_metric = {
                "name": dimension_name,
                "average_rating": avg_rating,
                "criteria_assessed": criteria_assessed,
                "criteria_total": criteria_total,
                "coverage": criteria_assessed / max(1, criteria_total),
                "strengths_count": len(summary.get("strengths", [])),
                "weaknesses_count": len(summary.get("weaknesses", []))
            }
            
            dimension_metrics.append(dimension_metric)
        
        # Calculate overall metrics
        overall_avg_rating = sum(dimension_ratings) / len(dimension_ratings) if dimension_ratings else None
        criteria_coverage = total_criteria_assessed / max(1, total_criteria)
        
        # Format cross-dimension insights for prompt
        cross_insights_text = json.dumps(cross_dimension_insights, indent=2)
        
        # Format dimension metrics for prompt
        dimension_metrics_text = json.dumps(dimension_metrics, indent=2)
        
        # Prompt for overall assessment
        system_prompt = """You are an expert evaluator creating a comprehensive assessment. Synthesize information across multiple dimensions to provide a structured overall assessment with clear ratings, insights, and recommendations."""
        
        human_prompt = f"""Generate a comprehensive overall assessment based on the following information:

DIMENSION METRICS:
{dimension_metrics_text}

CROSS-DIMENSION INSIGHTS:
{cross_insights_text}

Based on this information, provide a structured overall assessment with:
1. An executive summary of the overall assessment
2. Key strengths identified across all dimensions (3-5)
3. Key areas for improvement across all dimensions (3-5)
4. Strategic recommendations based on the assessment (3-5)
5. Critical success factors for improvement

Your assessment should be holistic, focusing on the relationships between dimensions and the overall picture that emerges."""

        # Define schema for structured output
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
                "critical_success_factors": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["executive_summary", "key_strengths", "key_improvements", "recommendations", "critical_success_factors"]
        }

        # Call LLM for overall assessment
        assessment, _ = await self._safe_llm_call(
            "generate_structured_output",
            prompt=human_prompt,
            output_schema=assessment_schema,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1200
        )
        
        # Create structured overall assessment
        overall_assessment = {
            "average_rating": overall_avg_rating,
            "criteria_assessed": total_criteria_assessed,
            "criteria_total": total_criteria,
            "criteria_coverage": criteria_coverage,
            "dimension_count": len(dimension_metrics),
            "timestamp": self.context.start_time.isoformat(),
            "executive_summary": assessment.get("executive_summary", ""),
            "key_strengths": assessment.get("key_strengths", []),
            "key_improvements": assessment.get("key_improvements", []),
            "recommendations": assessment.get("recommendations", []),
            "critical_success_factors": assessment.get("critical_success_factors", []),
            "cross_dimension_relationships": cross_dimension_insights.get("relationships", []),
            "cross_dimension_patterns": cross_dimension_insights.get("patterns", [])
        }
        
        return overall_assessment