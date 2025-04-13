"""
Evaluator Agent - Evaluates criteria based on extracted evidence

This agent analyzes extracted evidence and evaluates framework criteria,
generating ratings and rationales based on available evidence.
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class EvaluatorAgent(BaseAgent):
    """
    Evaluates framework criteria based on extracted evidence.
    
    The Evaluator is responsible for:
    1. Analyzing evidence for each criterion
    2. Generating ratings based on scoring methods
    3. Providing rationales for assessments
    4. Estimating confidence in evaluations
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
        self.custom_instructions = self.options.get("instructions", "")
        
        self.logger.info(f"{name} initialized with evaluation_type={self.evaluation_type}")
        
    async def process(self) -> Dict[str, Any]:
        """
        Evaluate framework criteria based on extracted evidence.
        
        Returns:
            Evaluation results
        """
        self.logger.info("Starting criteria evaluation")
        self.start_timer()
        
        try:
            # Get framework dimensions and criteria
            framework = self.context.framework
            dimensions = framework.get("dimensions", [])
            
            # Process each dimension
            evaluation_results = {
                "by_dimension": {},
                "overall": {}
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
                evaluation_results["by_dimension"][dimension_id] = dimension_results
            
            # Generate overall assessment
            overall_assessment = await self._generate_overall_assessment(evaluation_results["by_dimension"], dimensions)
            evaluation_results["overall"] = overall_assessment
            
            # Set overall assessment in context
            self.context.set_overall_assessment(overall_assessment)
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Criteria evaluation completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("evaluation_completed", {
                "dimensions_evaluated": len(evaluation_results["by_dimension"]),
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
            Dimension evaluation results
        """
        dimension_id = dimension.get("id", "")
        dimension_name = dimension.get("name", "")
        criteria = dimension.get("criteria", [])
        
        # Process each criterion
        criteria_results = {}
        
        for criterion in criteria:
            criterion_id = criterion.get("id", "")
            
            if not criterion_id:
                continue
                
            # Evaluate criterion
            criteria_results[criterion_id] = await self._evaluate_criterion(dimension_id, criterion)
        
        # Generate dimension summary
        dimension_summary = await self._generate_dimension_summary(dimension, criteria_results)
        
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
            Criterion evaluation results
        """
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_method = criterion.get("scoring_method", "scale_1_5")
        
        # Get evidence for this criterion
        evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
        
        # If no evidence and not inferring
        if not evidence_list and not self.infer_missing:
            self.logger.info(f"No evidence found for {dimension_id}:{criterion_id}, skipping evaluation")
            
            # Set empty assessment in context
            self.set_criterion_assessment(
                dimension_id=dimension_id,
                criterion_id=criterion_id,
                rating=None,
                rationale="No evidence found for evaluation",
                confidence=0.0
            )
            
            return {
                "rating": None,
                "rationale": "No evidence found for evaluation",
                "confidence": 0.0,
                "evidence_count": 0
            }
        
        # Handle evidence-based criteria (just collecting evidence)
        if scoring_method == "evidence_based":
            # For evidence-based criteria, we just collect and organize evidence
            if evidence_list:
                summary_prompt = self._create_evidence_summary_prompt(
                    criterion_name, 
                    criterion_question, 
                    evidence_list
                )
                
                # Generate evidence summary
                summary_text, _ = await self._safe_llm_call(
                    "generate_completion",
                    prompt=summary_prompt,
                    system_prompt="You are an expert evaluator. Summarize the evidence for this criterion.",
                    temperature=0.3,
                    max_tokens=800
                )
                
                # Set assessment in context
                rating = len(evidence_list)
                confidence = 1.0
                
                self.set_criterion_assessment(
                    dimension_id=dimension_id,
                    criterion_id=criterion_id,
                    rating=rating,
                    rationale=summary_text,
                    confidence=confidence
                )
                
                return {
                    "rating": rating, 
                    "rationale": summary_text,
                    "confidence": confidence,
                    "evidence_count": len(evidence_list),
                    "evidence_ids": [ev.get("id") for ev in evidence_list if "id" in ev]
                }
            
            # If no evidence and inferring
            elif self.infer_missing:
                return await self._create_inferred_assessment(dimension_id, criterion)
            
            # Default no evidence, not inferring
            return {
                "rating": None,
                "rationale": "No evidence found for evaluation",
                "confidence": 0.0,
                "evidence_count": 0,
                "evidence_ids": []
            }
            
        else:  # Numeric scale (scale_1_5 etc.)
            # If we have evidence
            if evidence_list:
                # Create evaluation prompt
                evaluation_prompt = self._create_evaluation_prompt(
                    criterion, 
                    evidence_list
                )
                
                # Define evaluation schema
                evaluation_schema = {
                    "type": "object",
                    "properties": {
                        "rating": {"type": "number"},
                        "rationale": {"type": "string"},
                        "confidence": {"type": "number"}
                    },
                    "required": ["rating", "rationale"]
                }
                
                # Call LLM for evaluation
                evaluation_result, _ = await self._safe_llm_call(
                    "generate_structured_output",
                    prompt=evaluation_prompt,
                    output_schema=evaluation_schema,
                    system_prompt="You are an expert evaluator analyzing evidence to provide a rating.",
                    temperature=0.3,
                    max_tokens=1000
                )
                
                # Extract and validate results
                rating = evaluation_result.get("rating")
                rationale = evaluation_result.get("rationale", "")
                confidence = evaluation_result.get("confidence", 0.8)
                
                # Set assessment in context
                self.set_criterion_assessment(
                    dimension_id=dimension_id,
                    criterion_id=criterion_id,
                    rating=rating,
                    rationale=rationale,
                    confidence=confidence
                )
                
                return {
                    "rating": rating,
                    "rationale": rationale,
                    "confidence": confidence,
                    "evidence_count": len(evidence_list),
                    "evidence_ids": [ev.get("id") for ev in evidence_list if "id" in ev]
                }
            
            # If no evidence and inferring
            elif self.infer_missing:
                return await self._create_inferred_assessment(dimension_id, criterion)
            
            # Default no evidence, not inferring
            return {
                "rating": None,
                "rationale": "No evidence found for evaluation",
                "confidence": 0.0,
                "evidence_count": 0,
                "evidence_ids": []
            }
    
    def _create_evidence_summary_prompt(self, criterion_name: str, criterion_question: str, evidence_list: List[Dict[str, Any]]) -> str:
        """Create a prompt for summarizing evidence."""
        evidence_text = self._format_evidence_text(evidence_list)
        
        prompt = "Summarize the following evidence related to this criterion:\n\n"
        prompt += f"CRITERION: {criterion_name}\n"
        prompt += f"QUESTION: {criterion_question}\n\n"
        prompt += f"EVIDENCE:\n{evidence_text}\n\n"
        prompt += "Provide a concise summary that:\n"
        prompt += "1. Synthesizes the key points from all evidence\n"
        prompt += "2. Highlights consistent themes or findings\n"
        prompt += "3. Notes any contradictions or uncertainties\n"
        prompt += "4. Discusses the overall strength of the evidence\n\n"
        prompt += "Your summary should be focused and directly address the criterion question."
        
        return prompt
    
    def _create_evaluation_prompt(self, criterion: Dict[str, Any], evidence_list: List[Dict[str, Any]]) -> str:
        """Create a prompt for evaluating a criterion with evidence."""
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
        
        # Build prompt
        prompt = f"Evaluate the following criterion based on the provided evidence.\n\n"
        prompt += f"CRITERION: {criterion_name}\n"
        prompt += f"QUESTION: {criterion_question}\n\n"
        prompt += f"SCORING SCALE:\n{scoring_text}\n\n"
        prompt += f"EVIDENCE:\n{evidence_text}\n\n"
        prompt += "Based on this evidence, provide:\n"
        prompt += "1. A rating from the scoring scale\n"
        prompt += "2. A detailed rationale explaining your rating\n"
        prompt += "3. Your confidence level in this assessment (0.0-1.0)\n\n"
        prompt += "Consider both the quantity and quality of evidence in your evaluation."
        
        return prompt
    
    def _format_evidence_text(self, evidence_list: List[Dict[str, Any]]) -> str:
        """Format evidence list into text for prompts."""
        if not evidence_list:
            return "No evidence found."
            
        evidence_text = ""
        for i, evidence in enumerate(evidence_list):
            evidence_text += f"Evidence {i+1}:\n"
            evidence_text += f"{evidence.get('text', '')}\n\n"
            
        return evidence_text
        
    async def _create_inferred_assessment(self, dimension_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
        """Create an inferred assessment when no direct evidence is available."""
        criterion_id = criterion.get("id", "")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_method = criterion.get("scoring_method", "scale_1_5")
        
        # Get dimension info
        dimension_name = "Unknown Dimension"
        for dimension in self.context.framework.get("dimensions", []):
            if dimension.get("id") == dimension_id:
                dimension_name = dimension.get("name", dimension_name)
                break
        
        # Create inference prompt
        prompt = "Infer an assessment for the following criterion that lacks direct evidence.\n\n"
        prompt += f"CRITERION: {criterion_name}\n"
        prompt += f"QUESTION: {criterion_question}\n"
        prompt += f"DIMENSION: {dimension_name}\n"
        prompt += f"SCORING METHOD: {scoring_method}\n\n"
        prompt += "Based on general knowledge and the context of this evaluation, please:\n"
        prompt += "1. Determine if an inference is possible\n"
        prompt += "2. If possible, provide an inferred rating\n"
        prompt += "3. Provide a rationale for your inference\n"
        prompt += "4. Indicate your confidence level in this inference (0.0-1.0)\n\n"
        prompt += "If an inference is not possible, explain why."
        
        # Define inference schema
        inference_schema = {
            "type": "object",
            "properties": {
                "inference_possible": {"type": "boolean"},
                "rating": {"type": ["number", "null"]},
                "rationale": {"type": "string"},
                "confidence": {"type": "number"}
            },
            "required": ["inference_possible", "rationale", "confidence"]
        }
        
        # Call LLM for inference
        inference_result, _ = await self._safe_llm_call(
            "generate_structured_output",
            prompt=prompt,
            output_schema=inference_schema,
            system_prompt="You are an expert evaluator making inferences when direct evidence is lacking.",
            temperature=0.3,
            max_tokens=1000
        )
        
        # Process results
        inference_possible = inference_result.get("inference_possible", False)
        rating = inference_result.get("rating")
        rationale = inference_result.get("rationale", "")
        confidence = inference_result.get("confidence", 0.0)
        
        # Adjust rationale for inferred assessments
        if inference_possible and rating is not None:
            prefixed_rationale = f"[INFERRED] {rationale}"
        else:
            rating = None
            prefixed_rationale = f"No direct evidence found. {rationale}"
            confidence = 0.0
        
        # Set assessment in context
        self.set_criterion_assessment(
            dimension_id=dimension_id,
            criterion_id=criterion_id,
            rating=rating,
            rationale=prefixed_rationale,
            confidence=confidence
        )
        
        return {
            "rating": rating,
            "rationale": prefixed_rationale,
            "confidence": confidence,
            "evidence_count": 0,
            "evidence_ids": [],
            "inferred": inference_possible
        }
    
    async def _generate_dimension_summary(
        self, 
        dimension: Dict[str, Any], 
        criteria_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate summary assessment for a dimension.
        
        Args:
            dimension: Framework dimension
            criteria_results: Results for all criteria in the dimension
            
        Returns:
            Dimension summary assessment
        """
        dimension_id = dimension.get("id", "")
        dimension_name = dimension.get("name", "")
        
        # Collect criteria assessments for the prompt
        assessments_text = ""
        rating_values = []
        confidence_values = []
        total_evidence = 0
        criteria_assessed = 0
        
        # Important: Use the parameter name "criteria_results" here, not "criteria_results"
        for criterion_id, result in criteria_results.items():
            # Find criterion name in dimension
            criterion_name = criterion_id
            for c in dimension.get("criteria", []):
                if c.get("id") == criterion_id:
                    criterion_name = c.get("name", criterion_id)
                    break
            
            rating = result.get("rating")
            rationale = result.get("rationale", "")
            confidence = result.get("confidence", 0.0)
            evidence_count = result.get("evidence_count", 0)
            
            assessments_text += f"{criterion_name}:\n"
            assessments_text += f"- Rating: {rating}\n"
            assessments_text += f"- Rationale: {rationale}\n\n"
            
            # Collect metrics
            if rating is not None and isinstance(rating, (int, float)):
                rating_values.append(rating)
                criteria_assessed += 1
                
            if confidence is not None and isinstance(confidence, (int, float)):
                confidence_values.append(confidence)
                
            total_evidence += evidence_count
        
        # Calculate summary metrics
        avg_rating = sum(rating_values) / len(rating_values) if rating_values else None
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        
        # Create summary prompt
        prompt = f"Generate a summary assessment for the dimension: {dimension_name}\n\n"
        prompt += f"CRITERIA ASSESSMENTS:\n{assessments_text}\n"
        prompt += "Please provide:\n"
        prompt += "1. A summary of key findings across all criteria\n"
        prompt += "2. An overall assessment of the dimension\n"
        prompt += "3. Areas of strength\n"
        prompt += "4. Areas for improvement\n\n"
        prompt += "Be concise but insightful in your summary."
        
        # Get summary text
        summary_text, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=prompt,
            system_prompt="You are an expert evaluator summarizing dimension assessments.",
            temperature=0.3,
            max_tokens=1000
        )
        
        # Create dimension summary
        dimension_summary = {
            "dimension_id": dimension_id,
            "dimension_name": dimension_name,
            "summary": summary_text,
            "average_rating": avg_rating,
            "criteria_assessed": criteria_assessed,
            "criteria_total": len(dimension.get("criteria", [])),
            "average_confidence": avg_confidence,
            "total_evidence": total_evidence
        }
        
        return dimension_summary
    
    async def _generate_overall_assessment(self, dimension_results: Dict[str, Dict[str, Any]], dimensions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate overall assessment for the framework.
        
        Args:
            dimension_results: Results for all dimensions
            dimensions: Framework dimensions
            
        Returns:
            Overall assessment
        """
        # Create dimension name lookup
        dimension_names = {}
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            if dimension_id:
                dimension_names[dimension_id] = dimension.get("name", dimension_id)
        
        # Collect dimension summaries
        summaries_text = ""
        dimension_ratings = []
        dimension_confidences = []
        total_evidence = 0
        total_criteria_assessed = 0
        total_criteria = 0
        
        for dimension_id, result in dimension_results.items():
            dimension_name = dimension_names.get(dimension_id, dimension_id)
            summary = result.get("summary", {})
            avg_rating = summary.get("average_rating")
            summary_text = summary.get("summary", "")
            criteria_assessed = summary.get("criteria_assessed", 0)
            criteria_total = summary.get("criteria_total", 0)
            
            summaries_text += f"DIMENSION: {dimension_name}\n"
            summaries_text += f"Average Rating: {avg_rating}\n"
            summaries_text += f"Summary: {summary_text}\n\n"
            
            # Collect metrics
            if avg_rating is not None:
                dimension_ratings.append(avg_rating)
                
            total_evidence += summary.get("total_evidence", 0)
            total_criteria_assessed += criteria_assessed
            total_criteria += criteria_total
        
        # Calculate overall metrics
        overall_avg_rating = sum(dimension_ratings) / len(dimension_ratings) if dimension_ratings else None
        
        # Create overall assessment prompt
        prompt = "Generate an overall assessment based on the dimension summaries below.\n\n"
        prompt += f"DIMENSION SUMMARIES:\n{summaries_text}\n"
        prompt += "Please provide:\n"
        prompt += "1. An executive summary of the overall assessment\n"
        prompt += "2. Key strengths identified across dimensions\n"
        prompt += "3. Key areas for improvement across dimensions\n"
        prompt += "4. Recommendations based on the assessment\n\n"
        prompt += "Be concise but comprehensive in your assessment."
        
        # Get assessment text
        assessment_text, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=prompt,
            system_prompt="You are an expert evaluator creating an overall assessment summary.",
            temperature=0.3,
            max_tokens=1200
        )
        
        # Create overall assessment
        overall_assessment = {
            "assessment": assessment_text,
            "average_rating": overall_avg_rating,
            "criteria_assessed": total_criteria_assessed,
            "criteria_total": total_criteria,
            "criteria_coverage": total_criteria_assessed / max(1, total_criteria),
            "total_evidence": total_evidence,
            "dimension_count": len(dimension_results),
            "timestamp": self.context.start_time.isoformat()
        }
        
        return overall_assessment