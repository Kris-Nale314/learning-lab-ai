"""
Improved Evaluator Agent - Handles consolidated evidence packets with flexibility

This evaluator processes the consolidated evidence packets created by the extractor,
supporting both individual and combined evaluation approaches for improved
assessment consistency and quality.
"""

import logging
import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Set

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class EvaluatorAgent(BaseAgent):
    """
    Evaluates criteria using consolidated evidence packets.
    
    Two key approaches:
    1. Standard approach: Evaluate each criterion individually
    2. Combined approach: Evaluate related criteria together for consistency
    
    Features:
    - Handles the new consolidated evidence packet format
    - Supports direct and inferred assessments
    - Creates comprehensive dimension summaries
    - Provides overall assessment with actionable recommendations
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
            options: Configuration options
        """
        super().__init__(name, "evaluator", llm, context, options or {})
        
        # Get configuration
        self.options = options or {}
        self.config = options.get("configuration", {})
        
        # Evaluation settings
        self.infer_missing = self.config.get("infer_missing", True)
        self.min_confidence_threshold = self.config.get("confidence_threshold", 0.4)
        self.evaluation_type = self.config.get("evaluation_type", "standard")
        self.custom_instructions = self.options.get("instructions", "")
        
        # Use combined evaluation for related criteria
        self.use_combined_evaluation = self.config.get("use_combined_evaluation", True)
        
        # Criteria grouping size (for combined evaluation)
        self.max_group_size = self.config.get("max_group_size", 3)
        
        # Track assessment types
        self._assessment_counts = {"total": 0, "direct": 0, "inferred": 0, "insufficient": 0}
        
        self.logger.info(
            f"Evaluator '{self.name}' initialized with evaluation_type={self.evaluation_type}, "
            f"use_combined_evaluation={self.use_combined_evaluation}"
        )
        
    async def process(self) -> Dict[str, Any]:
        """
        Evaluate the framework using evidence packets.
        
        Returns:
            Assessment results summary
        """
        self.logger.info(f"Evaluator '{self.name}' starting criteria evaluation")
        self.start_timer()
        
        try:
            # Get framework dimensions and criteria
            framework = self.context.framework
            dimensions = framework.get("dimensions", [])
            
            if not dimensions:
                self.logger.error("No dimensions found in the framework definition")
                raise ValueError("Framework definition is missing dimensions")
                
            # Track total counts
            total_dimensions = len(dimensions)
            total_criteria = sum(len(dim.get("criteria", [])) for dim in dimensions)
            
            self.logger.info(f"Processing {total_criteria} criteria across {total_dimensions} dimensions")
            
            # Decide on evaluation strategy based on configuration
            if self.use_combined_evaluation and total_criteria > 3:
                # Use combined evaluation for related criteria
                await self._process_with_combined_evaluation(dimensions)
            else:
                # Use standard evaluation (one criterion at a time)
                await self._process_with_standard_evaluation(dimensions)
            
            # Generate overall assessment
            self.context.set_stage("Overall Assessment")
            self.update_progress(0.9, "Generating overall assessment")
            
            # Generate and store overall assessment
            overall_assessment = await self._generate_overall_assessment(dimensions)
            
            # Completion statistics
            elapsed_time = self.stop_timer()
            criteria_assessed = self._assessment_counts["direct"] + self._assessment_counts["inferred"]
            coverage = criteria_assessed / max(1, total_criteria)
            
            self.logger.info(
                f"Evaluator '{self.name}' completed in {elapsed_time:.2f}s. "
                f"Assessment types: Direct={self._assessment_counts['direct']}, "
                f"Inferred={self._assessment_counts['inferred']}, "
                f"Insufficient={self._assessment_counts['insufficient']}"
            )
            
            # Record observation
            self.record_observation("evaluation_completed", {
                "dimensions_evaluated": total_dimensions,
                "criteria_assessed": criteria_assessed,
                "coverage": coverage,
                "assessment_breakdown": self._assessment_counts,
                "time_taken": elapsed_time
            })
            
            # Return a summary of results
            return {
                "status": "completed",
                "message": "Evaluation finished. Results stored in context.",
                "overall_rating": overall_assessment.get("average_rating"),
                "criteria_coverage": coverage,
                "assessment_breakdown": self._assessment_counts,
                "time_taken": elapsed_time
            }
            
        except Exception as e:
            self.stop_timer()
            self.logger.error(f"Evaluator '{self.name}' failed: {str(e)}", exc_info=True)
            self.context.add_warning(f"Evaluator '{self.name}' failed: {str(e)}")
            
            # Return error status
            return {"status": "failed", "error": str(e)}

    async def _process_with_standard_evaluation(self, dimensions: List[Dict[str, Any]]) -> None:
        """
        Process all dimensions using standard evaluation (one criterion at a time).
        
        Args:
            dimensions: Framework dimensions
        """
        self.logger.info("Using standard evaluation approach (one criterion at a time)")
        
        # Process each dimension
        total_dimensions = len(dimensions)
        
        for i, dimension in enumerate(dimensions):
            dimension_id = dimension.get("id")
            dimension_name = dimension.get("name", f"Dimension_{i+1}")
            
            if not dimension_id:
                self.logger.warning(f"Skipping dimension without ID at index {i}")
                continue
                
            self.logger.info(f"Evaluating Dimension: {dimension_name} ({dimension_id})")
            
            # Set context stage for progress tracking
            self.context.set_stage(f"Evaluating {dimension_name}")

            # Update progress
            progress = (i + 1) / total_dimensions * 0.8 
            self.update_progress(progress, f"Evaluating dimension {i+1}/{total_dimensions}: {dimension_name}")
            
            # Evaluate dimension
            await self._evaluate_dimension(dimension)
    
    async def _process_with_combined_evaluation(self, dimensions: List[Dict[str, Any]]) -> None:
        """
        Process dimensions using combined evaluation where possible.
        
        Args:
            dimensions: Framework dimensions
        """
        self.logger.info("Using combined evaluation approach for related criteria")
        
        # Process each dimension
        total_dimensions = len(dimensions)
        
        for i, dimension in enumerate(dimensions):
            dimension_id = dimension.get("id")
            dimension_name = dimension.get("name", f"Dimension_{i+1}")
            
            if not dimension_id:
                self.logger.warning(f"Skipping dimension without ID at index {i}")
                continue
                
            self.logger.info(f"Evaluating Dimension: {dimension_name} ({dimension_id})")
            
            # Set context stage for progress tracking
            self.context.set_stage(f"Evaluating {dimension_name}")

            # Update progress
            progress = (i + 1) / total_dimensions * 0.8 
            self.update_progress(progress, f"Evaluating dimension {i+1}/{total_dimensions}: {dimension_name}")
            
            # Get criteria for this dimension
            criteria = dimension.get("criteria", [])
            
            if len(criteria) <= 1:
                # For single criterion, use standard evaluation
                await self._evaluate_dimension(dimension)
            else:
                # Try to group related criteria
                criteria_groups = self._group_related_criteria(dimension)
                
                # Process each group
                for group in criteria_groups:
                    if len(group) == 1:
                        # Individual criterion
                        criterion = group[0]
                        await self._evaluate_criterion(dimension_id, criterion)
                    else:
                        # Group of related criteria
                        await self._evaluate_criteria_group(dimension_id, group)
                
                # Generate dimension summary
                await self._generate_dimension_summary_after_groups(dimension)

    def _group_related_criteria(self, dimension: Dict[str, Any]) -> List[List[Dict[str, Any]]]:
        """
        Group related criteria for combined evaluation.
        
        Simple implementation: Group by similarity in criterion name/description
        
        Args:
            dimension: Dimension dictionary
            
        Returns:
            List of criteria groups
        """
        criteria = dimension.get("criteria", [])
        
        # For simplicity, this implementation creates small fixed-size groups
        # In a production system, you would use a more sophisticated grouping algorithm
        groups = []
        current_group = []
        
        for criterion in criteria:
            current_group.append(criterion)
            
            if len(current_group) >= self.max_group_size:
                groups.append(current_group)
                current_group = []
        
        # Add any remaining criteria
        if current_group:
            groups.append(current_group)
            
        self.logger.info(f"Grouped {len(criteria)} criteria into {len(groups)} groups")
        return groups

    async def _evaluate_dimension(self, dimension: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate all criteria within a dimension individually.
        
        Args:
            dimension: Framework dimension dictionary
            
        Returns:
            Dimension evaluation summary
        """
        dimension_id = dimension.get("id")
        dimension_name = dimension.get("name", "Unknown Dimension")
        criteria = dimension.get("criteria", [])
        
        # Track assessment results for this dimension
        criteria_results = {}
        assessment_types = {"direct": 0, "inferred": 0, "insufficient_evidence": 0}
        
        if not criteria:
            self.logger.warning(f"Dimension '{dimension_name}' has no criteria defined")
            # Create empty dimension summary
            dimension_summary = {
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": None,
                "criteria_assessed": 0,
                "criteria_total": 0,
                "strengths": [],
                "weaknesses": [],
                "summary": "No criteria defined for this dimension"
            }
            self.context.set_dimension_summary(dimension_id, dimension_summary)
            return dimension_summary
        
        # Evaluate each criterion individually
        for criterion in criteria:
            criterion_id = criterion.get("id")
            criterion_name = criterion.get("name", f"Criterion_{criterion_id}")
            
            if not criterion_id:
                self.logger.warning(f"Skipping criterion without ID in dimension {dimension_name}")
                continue

            self.logger.info(f"Evaluating: {criterion_name} ({criterion_id}) in {dimension_name}")
            
            # Evaluate criterion and store in context
            result = await self._evaluate_criterion(dimension_id, criterion)
            
            # Track assessment type
            if result:
                assessment_type = result.get("assessment_type", "insufficient_evidence")
                assessment_types[assessment_type] = assessment_types.get(assessment_type, 0) + 1
                
                # Update global counters
                self._assessment_counts["total"] += 1
                self._assessment_counts[assessment_type] += 1
                
                # Store for dimension summary
                criteria_results[criterion_id] = {
                    "name": criterion_name,
                    "rating": result.get("rating"),
                    "rationale": result.get("rationale"),
                    "assessment_type": assessment_type,
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", [])
                }
        
        # Generate dimension summary
        dimension_summary = await self._generate_dimension_summary(
            dimension, criteria_results, assessment_types
        )
        
        # Store dimension summary in context
        self.context.set_dimension_summary(dimension_id, dimension_summary)
        
        self.logger.info(
            f"Completed evaluation of dimension '{dimension_name}' with "
            f"{len(criteria_results)} criteria. Assessment types: {assessment_types}"
        )
        
        return dimension_summary

    async def _evaluate_criterion(self, dimension_id: str, criterion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate a single criterion using its consolidated evidence packet.
        
        Args:
            dimension_id: Dimension ID
            criterion: Criterion dictionary
            
        Returns:
            Assessment dictionary
        """
        criterion_id = criterion.get("id")
        criterion_name = criterion.get("name", "")
        
        try:
            # Get evidence packets for this criterion
            evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
            
            if not evidence_list:
                self.logger.warning(f"No evidence found for criterion {criterion_id}")
                return self._create_insufficient_evidence_assessment(dimension_id, criterion)
            
            # We expect a single consolidated packet from the extractor
            if len(evidence_list) > 1:
                self.logger.info(f"Found {len(evidence_list)} evidence items for {criterion_id}, using the most recent")
                
                # Sort by timestamp (most recent first)
                evidence_list.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            
            # Get the consolidated evidence packet
            evidence_packet = evidence_list[0]
            packet_text = evidence_packet.get("text", "")
            metadata = evidence_packet.get("metadata", {})
            
            # Determine if the packet has evidence
            evidence_found = metadata.get("evidence_found", False)
            if not evidence_found or "no relevant quotes found" in packet_text.lower():
                self.logger.info(f"No evidence found in packet for criterion {criterion_id}")
                return self._create_insufficient_evidence_assessment(dimension_id, criterion)
            
            # Process the consolidated evidence packet
            assessment = await self._create_assessment_from_packet(dimension_id, criterion, evidence_packet)
            
            # Validate the assessment
            if not assessment or assessment.get("rating") is None:
                self.logger.warning(f"Assessment creation failed for {criterion_id}")
                
                if self.infer_missing:
                    self.logger.info(f"Attempting inferred assessment for {criterion_id}")
                    assessment = await self._create_inferred_assessment(dimension_id, criterion, evidence_packet)
                    
                    if assessment and assessment.get("rating") is not None:
                        return assessment
                
                return self._create_insufficient_evidence_assessment(dimension_id, criterion)
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Error evaluating criterion {criterion_id}: {str(e)}", exc_info=True)
            self.context.add_warning(f"Error evaluating criterion {criterion_id}: {str(e)}")
            return self._create_insufficient_evidence_assessment(dimension_id, criterion)

    async def _evaluate_criteria_group(
        self, 
        dimension_id: str, 
        criteria_group: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Evaluate a group of related criteria together for consistency.
        
        Args:
            dimension_id: Dimension ID
            criteria_group: List of related criteria
            
        Returns:
            Dictionary mapping criterion IDs to assessment results
        """
        self.logger.info(f"Evaluating group of {len(criteria_group)} related criteria")
        
        # Get evidence packets for all criteria in the group
        evidence_packets = {}
        
        for criterion in criteria_group:
            criterion_id = criterion.get("id")
            if not criterion_id:
                continue
                
            evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
            
            if evidence_list:
                # Get the most recent packet
                evidence_packets[criterion_id] = evidence_list[0]
        
        # If no evidence for any criterion, evaluate each individually
        if not evidence_packets:
            self.logger.warning(f"No evidence found for any criterion in group, evaluating individually")
            results = {}
            
            for criterion in criteria_group:
                criterion_id = criterion.get("id")
                if criterion_id:
                    results[criterion_id] = await self._evaluate_criterion(dimension_id, criterion)
                    
            return results
        
        # Create a combined assessment for all criteria in the group
        return await self._create_group_assessment(dimension_id, criteria_group, evidence_packets)

    async def _create_group_assessment(
        self, 
        dimension_id: str, 
        criteria_group: List[Dict[str, Any]],
        evidence_packets: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Create assessments for a group of related criteria together.
        
        Args:
            dimension_id: Dimension ID
            criteria_group: List of related criteria
            evidence_packets: Evidence packets for each criterion
            
        Returns:
            Dictionary mapping criterion IDs to assessment results
        """
        # Format criteria information
        criteria_info = []
        for criterion in criteria_group:
            criterion_id = criterion.get("id")
            
            if not criterion_id:
                continue
                
            criteria_info.append({
                "id": criterion_id,
                "name": criterion.get("name", ""),
                "question": criterion.get("question", ""),
                "scoring_definitions": criterion.get("scoring_definitions", {})
            })
        
        # Format evidence packets
        evidence_text = ""
        for criterion_id, packet in evidence_packets.items():
            criterion_name = next((c["name"] for c in criteria_info if c["id"] == criterion_id), criterion_id)
            evidence_text += f"\nEVIDENCE FOR CRITERION: {criterion_name} ({criterion_id})\n"
            evidence_text += packet.get("text", "No evidence packet found") + "\n"
        
        # Create system prompt
        system_prompt = """You are an expert evaluator assessing multiple related criteria.
Analyze each criterion based on its evidence and provide consistent, well-calibrated ratings across all criteria."""
        
        # Add custom instructions if available
        if self.custom_instructions:
            system_prompt += f"\n\n{self.custom_instructions}"
        
        # Create human prompt for group assessment
        human_prompt = f"""Evaluate this group of related criteria in the same dimension.

DIMENSION: {dimension_id}

CRITERIA TO ASSESS:
{json.dumps(criteria_info, indent=2)}

EVIDENCE PACKETS:
{evidence_text}

For each criterion, provide:
1. RATING: Numeric rating according to its scoring definitions
2. RATIONALE: Clear justification for the rating based on the evidence
3. STRENGTHS: Key strengths identified from the evidence (2-3 items)
4. WEAKNESSES: Key weaknesses identified from the evidence (2-3 items)
5. CONFIDENCE: Score (0.0-1.0) reflecting the reliability of the assessment
6. ASSESSMENT_TYPE: "direct" (if strong evidence) or "inferred" (if limited evidence)

Consider the relationships between these criteria when making your assessments.
Ensure your ratings are CONSISTENT and CALIBRATED across criteria.
"""

        # Define schema for group assessment
        group_schema = {
            "type": "object",
            "properties": {
                "assessments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "criterion_id": {"type": "string"},
                            "rating": {"type": ["number", "null"]},
                            "rationale": {"type": "string"},
                            "strengths": {"type": "array", "items": {"type": "string"}},
                            "weaknesses": {"type": "array", "items": {"type": "string"}},
                            "confidence": {"type": "number"},
                            "assessment_type": {"type": "string"}
                        },
                        "required": ["criterion_id", "rationale", "assessment_type"]
                    }
                }
            },
            "required": ["assessments"]
        }

        try:
            # Call LLM for group assessment
            result = await self._structured_output_call(
                prompt=human_prompt,
                output_schema=group_schema,
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            if not result or "assessments" not in result:
                self.logger.warning(f"LLM failed to generate group assessment, falling back to individual assessment")
                
                # Fallback to individual assessment
                individual_results = {}
                for criterion in criteria_group:
                    criterion_id = criterion.get("id")
                    if criterion_id:
                        individual_results[criterion_id] = await self._evaluate_criterion(dimension_id, criterion)
                        
                return individual_results
            
            # Process each assessment in the group
            group_results = {}
            
            for assessment in result["assessments"]:
                criterion_id = assessment.get("criterion_id")
                
                if not criterion_id:
                    continue
                    
                # Get the matching criterion
                criterion = next((c for c in criteria_group if c.get("id") == criterion_id), None)
                if not criterion:
                    continue
                
                # Create a full assessment object
                full_assessment = {
                    "id": criterion_id,
                    "name": criterion.get("name", ""),
                    "rating": assessment.get("rating"),
                    "rationale": assessment.get("rationale", ""),
                    "strengths": assessment.get("strengths", []),
                    "weaknesses": assessment.get("weaknesses", []),
                    "confidence": assessment.get("confidence", 0.0),
                    "assessment_type": assessment.get("assessment_type", "insufficient_evidence")
                }
                
                # Ensure inferred assessments are properly marked
                if full_assessment["assessment_type"] == "inferred" and not full_assessment["rationale"].startswith("[INFERRED]"):
                    full_assessment["rationale"] = f"[INFERRED] {full_assessment['rationale']}"
                
                # Store assessment in context
                self.set_criterion_assessment(
                    dimension_id=dimension_id,
                    criterion_id=criterion_id,
                    rating=full_assessment.get("rating"),
                    rationale=full_assessment.get("rationale"),
                    confidence=full_assessment.get("confidence"),
                    assessment_type=full_assessment.get("assessment_type")
                )
                
                # Track assessment type
                assessment_type = full_assessment.get("assessment_type", "insufficient_evidence")
                self._assessment_counts["total"] += 1
                self._assessment_counts[assessment_type] += 1
                
                # Store in results
                group_results[criterion_id] = full_assessment
            
            return group_results
            
        except Exception as e:
            self.logger.error(f"Error in group assessment: {str(e)}", exc_info=True)
            
            # Fallback to individual assessment
            individual_results = {}
            for criterion in criteria_group:
                criterion_id = criterion.get("id")
                if criterion_id:
                    individual_results[criterion_id] = await self._evaluate_criterion(dimension_id, criterion)
                    
            return individual_results

    async def _create_assessment_from_packet(
        self,
        dimension_id: str,
        criterion: Dict[str, Any],
        evidence_packet: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an assessment based on a consolidated evidence packet.
        
        Args:
            dimension_id: Dimension ID
            criterion: Criterion dictionary
            evidence_packet: Consolidated evidence packet
            
        Returns:
            Assessment dictionary
        """
        criterion_id = criterion.get("id")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Format scoring definitions
        scoring_text = "\n".join([
            f"- Score {score}: {definition}" 
            for score, definition in scoring_definitions.items()
        ])
        
        # Get the packet text
        packet_text = evidence_packet.get("text", "")
        
        # Check if this is likely a direct assessment
        has_direct_evidence = (
            "direct quotes:" in packet_text.lower() and
            "key metrics:" in packet_text.lower() and
            not "no relevant quotes found" in packet_text.lower()
        )
        
        # Create system prompt
        system_prompt = """You are an expert evaluator assessing criteria based on evidence packets.
Analyze the evidence thoroughly and provide a clear, well-justified assessment."""
        
        # Add custom instructions if available
        if self.custom_instructions:
            system_prompt += f"\n\n{self.custom_instructions}"
        
        # Create human prompt
        human_prompt = f"""Evaluate this criterion based on the provided evidence packet:

CRITERION: {criterion_name}
QUESTION: {criterion_question}

SCORING DEFINITIONS:
{scoring_text}

EVIDENCE PACKET:
{packet_text}

Based on this evidence, provide:
1. RATING: A numeric rating from the scoring definitions
2. RATIONALE: Clear justification for the rating based on the evidence
3. STRENGTHS: Key strengths identified from the evidence (2-3 items)
4. WEAKNESSES: Key weaknesses or gaps in the evidence (2-3 items)
5. CONFIDENCE: A score (0.0-1.0) reflecting how well the evidence supports your assessment

If the evidence is strong and directly addresses the criterion, mark this as a DIRECT assessment.
If the evidence is limited but allows for reasonable inference, mark this as an INFERRED assessment.
"""

        # Define schema for assessment
        assessment_schema = {
            "type": "object",
            "properties": {
                "rating": {"type": ["number", "null"]},
                "rationale": {"type": "string"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "weaknesses": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number"},
                "assessment_type": {"type": "string", "enum": ["direct", "inferred", "insufficient_evidence"]}
            },
            "required": ["rationale", "strengths", "weaknesses", "confidence", "assessment_type"]
        }

        try:
            # Call LLM for assessment
            result = await self._structured_output_call(
                prompt=human_prompt,
                output_schema=assessment_schema,
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            if not result or "rationale" not in result:
                return self._create_insufficient_evidence_assessment(dimension_id, criterion)
            
            # Check confidence against threshold
            confidence = result.get("confidence", 0.0)
            if confidence < self.min_confidence_threshold:
                self.logger.info(
                    f"Assessment for {criterion_id} rejected due to low confidence: {confidence:.2f} < {self.min_confidence_threshold:.2f}"
                )
                return self._create_insufficient_evidence_assessment(dimension_id, criterion)
            
            # Get assessment type
            assessment_type = result.get("assessment_type", "insufficient_evidence")
            
            # Ensure inferred assessments are properly marked
            if assessment_type == "inferred" and not result["rationale"].startswith("[INFERRED]"):
                result["rationale"] = f"[INFERRED] {result['rationale']}"
            
            # Create final assessment
            assessment = {
                "id": criterion_id,
                "name": criterion_name,
                "rating": result.get("rating"),
                "rationale": result.get("rationale", ""),
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "confidence": confidence,
                "assessment_type": assessment_type
            }
            
            # Store assessment in context
            success = self.set_criterion_assessment(
                dimension_id=dimension_id,
                criterion_id=criterion_id,
                rating=assessment.get("rating"),
                rationale=assessment.get("rationale"),
                confidence=confidence,
                assessment_type=assessment_type
            )
            
            if not success:
                self.logger.error(f"Failed to store assessment for {criterion_id} in context")
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Error creating assessment from packet for {criterion_id}: {str(e)}", exc_info=True)
            return self._create_insufficient_evidence_assessment(dimension_id, criterion)

    async def _create_inferred_assessment(
        self,
        dimension_id: str,
        criterion: Dict[str, Any],
        evidence_packet: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an inferred assessment when direct evidence is limited.
        
        Args:
            dimension_id: Dimension ID
            criterion: Criterion dictionary
            evidence_packet: Evidence packet (may have limited evidence)
            
        Returns:
            Inferred assessment dictionary
        """
        criterion_id = criterion.get("id")
        criterion_name = criterion.get("name", "")
        criterion_question = criterion.get("question", "")
        scoring_definitions = criterion.get("scoring_definitions", {})
        
        # Format scoring definitions
        scoring_text = "\n".join([
            f"- Score {score}: {definition}" 
            for score, definition in scoring_definitions.items()
        ])
        
        # Get the packet text
        packet_text = evidence_packet.get("text", "")
        
        # Create system prompt
        system_prompt = """You are an expert evaluator making careful inferences when direct evidence is limited.
Create a reasoned assessment based on available context, being transparent about assumptions."""
        
        # Add custom instructions if available
        if self.custom_instructions:
            system_prompt += f"\n\n{self.custom_instructions}"
        
        # Create human prompt
        human_prompt = f"""Create an INFERRED assessment for this criterion with limited evidence:

CRITERION: {criterion_name}
QUESTION: {criterion_question}

SCORING DEFINITIONS:
{scoring_text}

EVIDENCE PACKET (limited or indirect):
{packet_text}

Create an INFERRED assessment that:
1. RATING: Provides a numeric rating based on the scoring definitions (or null if truly insufficient)
2. RATIONALE: Clearly explains your reasoning and the inference process
3. ASSUMPTIONS: Explicitly states what assumptions you're making
4. STRENGTHS: Identifies any partial strengths in the limited evidence
5. WEAKNESSES: Acknowledges the limitations of the evidence
6. CONFIDENCE: Provides a confidence score (0.0-1.0) reflecting the uncertainty

Always begin your rationale with "[INFERRED]" to clearly indicate this is not based on direct evidence.
If the evidence is truly insufficient for even a reasonable inference, indicate this clearly.
"""

        # Define schema for inferred assessment
        inferred_schema = {
            "type": "object",
            "properties": {
                "rating": {"type": ["number", "null"]},
                "rationale": {"type": "string"},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "weaknesses": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number"}
            },
            "required": ["rationale", "assumptions", "strengths", "weaknesses", "confidence"]
        }

        try:
            # Call LLM for inferred assessment
            result = await self._structured_output_call(
                prompt=human_prompt,
                output_schema=inferred_schema,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            if not result or "rationale" not in result:
                return self._create_insufficient_evidence_assessment(dimension_id, criterion)
            
            # Check confidence and rating
            confidence = result.get("confidence", 0.0)
            rating = result.get("rating")
            
            if confidence < self.min_confidence_threshold or rating is None:
                return self._create_insufficient_evidence_assessment(dimension_id, criterion)
            
            # Ensure rationale is properly marked
            if not result["rationale"].startswith("[INFERRED]"):
                result["rationale"] = f"[INFERRED] {result['rationale']}"
                
            # Add assumptions to rationale
            assumptions = result.get("assumptions", [])
            if assumptions:
                assumptions_text = "\n\nAssumptions made:\n" + "\n".join([f"- {a}" for a in assumptions])
                result["rationale"] += assumptions_text
            
            # Create final assessment
            assessment = {
                "id": criterion_id,
                "name": criterion_name,
                "rating": rating,
                "rationale": result.get("rationale", ""),
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "confidence": confidence,
                "assessment_type": "inferred"
            }
            
            # Store assessment in context
            self.set_criterion_assessment(
                dimension_id=dimension_id,
                criterion_id=criterion_id,
                rating=assessment.get("rating"),
                rationale=assessment.get("rationale"),
                confidence=confidence,
                assessment_type="inferred"
            )
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Error creating inferred assessment for {criterion_id}: {str(e)}", exc_info=True)
            return self._create_insufficient_evidence_assessment(dimension_id, criterion)

    def _create_insufficient_evidence_assessment(self, dimension_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an assessment when evidence is insufficient.
        
        Args:
            dimension_id: Dimension ID
            criterion: Criterion dictionary
            
        Returns:
            Insufficient evidence assessment
        """
        criterion_id = criterion.get("id")
        criterion_name = criterion.get("name", "")
        
        assessment = {
            "id": criterion_id,
            "name": criterion_name,
            "rating": None,
            "rationale": f"Insufficient evidence to assess '{criterion_name}'.",
            "confidence": 0.0,
            "assessment_type": "insufficient_evidence",
            "strengths": [],
            "weaknesses": []
        }
        
        # Store in context
        self.set_criterion_assessment(
            dimension_id=dimension_id,
            criterion_id=criterion_id,
            rating=None,
            rationale=assessment["rationale"],
            confidence=0.0,
            assessment_type="insufficient_evidence"
        )
        
        return assessment

    async def _generate_dimension_summary_after_groups(self, dimension: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate dimension summary after all criteria groups have been evaluated.
        
        Args:
            dimension: Dimension dictionary
            
        Returns:
            Dimension summary
        """
        dimension_id = dimension.get("id")
        dimension_name = dimension.get("name", "Unknown Dimension")
        criteria = dimension.get("criteria", [])
        
        # Collect all criterion assessments for this dimension
        criteria_results = {}
        assessment_types = {"direct": 0, "inferred": 0, "insufficient_evidence": 0}
        
        for criterion in criteria:
            criterion_id = criterion.get("id")
            if not criterion_id:
                continue
                
            # Get assessment from context
            assessment = self.context.get_criterion_assessment(dimension_id, criterion_id)
            
            if assessment:
                assessment_type = assessment.get("assessment_type", "insufficient_evidence")
                assessment_types[assessment_type] = assessment_types.get(assessment_type, 0) + 1
                
                criteria_results[criterion_id] = {
                    "name": criterion.get("name", ""),
                    "rating": assessment.get("rating"),
                    "rationale": assessment.get("rationale"),
                    "assessment_type": assessment_type,
                    "strengths": assessment.get("strengths", []),
                    "weaknesses": assessment.get("weaknesses", [])
                }
        
        # Generate dimension summary
        dimension_summary = await self._generate_dimension_summary(
            dimension, criteria_results, assessment_types
        )
        
        # Store dimension summary in context
        self.context.set_dimension_summary(dimension_id, dimension_summary)
        
        return dimension_summary

    async def _generate_dimension_summary(
        self, 
        dimension: Dict[str, Any],
        criteria_results: Dict[str, Dict[str, Any]],
        assessment_types: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Generate summary for a dimension based on its criteria assessments.
        
        Args:
            dimension: Dimension dictionary
            criteria_results: Results for criteria in this dimension
            assessment_types: Count of assessment types in this dimension
            
        Returns:
            Dimension summary dictionary
        """
        dimension_id = dimension.get("id")
        dimension_name = dimension.get("name", "Unknown Dimension")
        
        # Calculate average rating
        ratings = [
            result["rating"] for result in criteria_results.values() 
            if result.get("rating") is not None
        ]
        
        average_rating = sum(ratings) / len(ratings) if ratings else None
        
        # If no criteria assessed, return empty summary
        if not criteria_results:
            return {
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": None,
                "criteria_assessed": 0,
                "criteria_total": len(dimension.get("criteria", [])),
                "strengths": [],
                "weaknesses": [],
                "summary": "No criteria were assessed for this dimension."
            }
        
        # Format criteria results for prompt
        criteria_text = json.dumps(criteria_results, indent=2)
        
        # Create system prompt
        system_prompt = """You are an expert analyst synthesizing criteria assessments into dimension summaries.
Create a concise, insight-driven summary that identifies key patterns across the assessed criteria."""
        
        # Create human prompt
        human_prompt = f"""Generate a summary for dimension: {dimension_name}

AVERAGE RATING: {average_rating if average_rating is not None else 'N/A'}

CRITERIA ASSESSMENTS:
{criteria_text}

ASSESSMENT TYPES DISTRIBUTION:
- Direct: {assessment_types.get('direct', 0)}
- Inferred: {assessment_types.get('inferred', 0)}
- Insufficient Evidence: {assessment_types.get('insufficient_evidence', 0)}

Based on the criteria assessments:
1. Identify 3-5 key overall STRENGTHS for this dimension
2. Identify 3-5 key overall WEAKNESSES for this dimension
3. Write a concise SUMMARY paragraph (3-4 sentences) capturing the dimension's overall performance

Focus on patterns across multiple criteria and consider the reliability of the underlying assessments.
Prioritize insights from criteria with direct assessments over those with inferred assessments.
"""

        # Define schema for summary
        summary_schema = {
            "type": "object",
            "properties": {
                "strengths": {"type": "array", "items": {"type": "string"}},
                "weaknesses": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"}
            },
            "required": ["strengths", "weaknesses", "summary"]
        }

        try:
            # Call LLM for dimension summary
            result = await self._structured_output_call(
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
                "criteria_assessed": len([r for r in criteria_results.values() if r.get("rating") is not None]),
                "criteria_total": len(dimension.get("criteria", [])),
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "summary": result.get("summary", ""),
                "assessment_types": assessment_types
            }
            
            self.logger.info(f"Generated summary for dimension {dimension_name}")
            return dimension_summary
            
        except Exception as e:
            self.logger.error(f"Error generating dimension summary for {dimension_id}: {str(e)}")
            
            # Return basic summary on error
            return {
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": average_rating,
                "criteria_assessed": len([r for r in criteria_results.values() if r.get("rating") is not None]),
                "criteria_total": len(dimension.get("criteria", [])),
                "strengths": [],
                "weaknesses": [],
                "summary": f"Error generating dimension summary: {str(e)}",
                "assessment_types": assessment_types
            }

    async def _generate_overall_assessment(self, dimensions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate overall assessment based on dimension summaries.
        
        Args:
            dimensions: List of framework dimensions
            
        Returns:
            Overall assessment dictionary
        """
        self.logger.info("Generating overall assessment")
        
        # Fetch dimension summaries from context
        dimension_summaries = []
        dimension_ratings = []
        total_criteria_assessed = 0
        total_criteria = 0
        overall_assessment_types = {"direct": 0, "inferred": 0, "insufficient_evidence": 0}
        
        for dimension in dimensions:
            dimension_id = dimension.get("id")
            if not dimension_id:
                continue
                
            # Get dimension summary from context
            summary = self.context.get_dimension_summary(dimension_id)
            
            if summary:
                # Add to summaries list
                dimension_summaries.append({
                    "id": dimension_id,
                    "name": summary.get("name", dimension_id),
                    "average_rating": summary.get("average_rating"),
                    "summary": summary.get("summary", ""),
                    "strengths": summary.get("strengths", []),
                    "weaknesses": summary.get("weaknesses", [])
                })
                
                # Collect ratings for overall average
                if summary.get("average_rating") is not None:
                    dimension_ratings.append(summary["average_rating"])
                    
                # Aggregate stats
                total_criteria_assessed += summary.get("criteria_assessed", 0)
                total_criteria += summary.get("criteria_total", 0)
                
                # Aggregate assessment types
                dim_types = summary.get("assessment_types", {})
                for atype, count in dim_types.items():
                    overall_assessment_types[atype] = overall_assessment_types.get(atype, 0) + count
        
        # Calculate overall rating and coverage
        overall_rating = sum(dimension_ratings) / len(dimension_ratings) if dimension_ratings else None
        criteria_coverage = total_criteria_assessed / max(1, total_criteria) if total_criteria > 0 else 0
        direct_assessment_percentage = (
            overall_assessment_types.get("direct", 0) / max(1, total_criteria_assessed)
            if total_criteria_assessed > 0 else 0
        )
        
        # Format dimension summaries for prompt
        summaries_text = json.dumps(dimension_summaries, indent=2)
        
        # Create system prompt
        system_prompt = """You are an expert assessment analyst creating an executive summary.
Synthesize dimension assessments into a cohesive overall view with strategic insights and recommendations."""
        
        # Create human prompt
        human_prompt = f"""Generate an overall assessment based on the following dimension summaries:

DIMENSION SUMMARIES:
{summaries_text}

ASSESSMENT RELIABILITY:
- Total Criteria Assessed: {total_criteria_assessed} of {total_criteria} ({criteria_coverage:.1%})
- Direct Assessments: {overall_assessment_types.get('direct', 0)}
- Inferred Assessments: {overall_assessment_types.get('inferred', 0)}
- Insufficient Evidence: {overall_assessment_types.get('insufficient_evidence', 0)}

Based on these dimension summaries:
1. Write an EXECUTIVE_SUMMARY (3-5 paragraphs) synthesizing the overall findings
2. Identify 3-5 cross-cutting KEY_STRENGTHS observed across multiple dimensions
3. Identify 3-5 cross-cutting KEY_IMPROVEMENTS needed across multiple dimensions
4. Provide 3-5 actionable RECOMMENDATIONS based on the overall assessment

Focus on high-level insights, patterns across dimensions, and strategic implications.
Consider the assessment reliability in your analysis.
"""

        # Define schema for overall assessment
        assessment_schema = {
            "type": "object",
            "properties": {
                "executive_summary": {"type": "string"},
                "key_strengths": {"type": "array", "items": {"type": "string"}},
                "key_improvements": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["executive_summary", "key_strengths", "key_improvements", "recommendations"]
        }

        try:
            # Call LLM for overall assessment
            result = await self._structured_output_call(
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
                "dimension_count": len(dimension_summaries),
                "executive_summary": result.get("executive_summary", ""),
                "key_strengths": result.get("key_strengths", []),
                "key_improvements": result.get("key_improvements", []),
                "recommendations": result.get("recommendations", []),
                "assessment_types": overall_assessment_types,
                "direct_assessment_percentage": direct_assessment_percentage,
                "timestamp": time.time()
            }
            
            # Store overall assessment in context
            self.set_overall_assessment(overall_assessment)
            
            self.logger.info("Generated and stored overall assessment")
            return overall_assessment
            
        except Exception as e:
            self.logger.error(f"Error generating overall assessment: {str(e)}")
            
            # Create basic assessment on error
            basic_assessment = {
                "average_rating": overall_rating,
                "criteria_assessed": total_criteria_assessed,
                "criteria_total": total_criteria,
                "criteria_coverage": criteria_coverage,
                "dimension_count": len(dimension_summaries),
                "executive_summary": f"Error generating overall assessment: {str(e)}",
                "key_strengths": [],
                "key_improvements": [],
                "recommendations": [],
                "assessment_types": overall_assessment_types,
                "timestamp": time.time()
            }
            
            # Store basic assessment in context
            self.set_overall_assessment(basic_assessment)
            
            return basic_assessment