"""
Enhanced Reporter Agent - Improved reporting with assessment type distinction

This agent formats the structured evaluations into clear reports, distinguishing
between direct and inferred assessments and providing evidence category counts for visualizations.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class ReporterAgent(BaseAgent):
    """
    Creates structured reports that clearly distinguish assessment types.
    
    The Enhanced Reporter is responsible for:
    1. Formatting evaluations into clean, presentation-ready reports
    2. Clearly indicating whether assessments are direct or inferred
    3. Including evidence category information for visualizations
    4. Creating a structured scorecard as the primary output
    5. Generating executive summaries and detailed assessments
    6. Adding cross-references and traceability between sections
    """
    
    def __init__(
        self,
        llm,
        context: AssessmentContext,
        name: str = "Reporter",
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Reporter agent.
        
        Args:
            llm: Language model instance
            context: Assessment context
            name: Agent name
            options: Configuration options including report types
        """
        super().__init__(name, "reporter", llm, context, options or {})
        
        # Get reporter configuration from options
        self.report_type = self.options.get("report_type", "scorecard")
        self.include_evidence = self.options.get("include_evidence", True)
        self.include_confidence = self.options.get("include_confidence", True)
        self.include_assessment_types = self.options.get("include_assessment_types", True)
        self.include_na_criteria = self.options.get("include_na_criteria", False)
        self.custom_instructions = self.options.get("instructions", "")
        
        # Get schema from strategy if available
        strategy = self.options.get("strategy", {})
        self.output_schema = strategy.get("output_schema", {})
        
        self.logger.info(f"{name} initialized with report_type={self.report_type}")
        
    async def process(self) -> Dict[str, Any]:
        """
        Generate formatted reports based on evaluation results.
        
        Returns:
            Generated reports in multiple formats
        """
        self.logger.info("Starting report generation")
        self.start_timer()
        
        try:
            # Get framework and evaluation results
            framework = self.context.framework
            
            # Get overall assessment from context
            overall_assessment = self.context.get_overall_assessment()
            
            # Initialize reports container
            reports = {
                "metadata": self._generate_metadata(),
                "formats": {}
            }
            
            # Always generate scorecard as the primary output
            reports["formats"]["scorecard"] = self._generate_scorecard()
            
            # Generate additional reports based on configuration
            if self.report_type in ["comprehensive", "all"]:
                # Generate multiple report formats
                reports["formats"]["executive_summary"] = await self._generate_executive_summary()
                reports["formats"]["detailed_assessment"] = await self._generate_detailed_assessment()
                
                if self.include_evidence:
                    reports["formats"]["evidence_report"] = await self._generate_evidence_report()
                
            elif self.report_type == "executive":
                # Generate executive summary only
                reports["formats"]["executive_summary"] = await self._generate_executive_summary()
                
            elif self.report_type == "detailed":
                # Generate detailed assessment only
                reports["formats"]["detailed_assessment"] = await self._generate_detailed_assessment()
            
            # Always include visualization data
            reports["formats"]["visualization_data"] = self._generate_visualization_data()
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Report generation completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("reports_generated", {
                "report_formats": list(reports["formats"].keys()),
                "time_taken": elapsed_time
            })
            
            return reports
            
        except Exception as e:
            self.stop_timer()
            self.logger.error(f"Error during report generation: {str(e)}", exc_info=True)
            self.add_warning(f"Failed to generate reports: {str(e)}")
            raise
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """
        Generate report metadata.
        
        Returns:
            Report metadata
        """
        # Get framework info
        framework = self.context.framework
        framework_id = framework.get("id", "unknown")
        framework_name = framework.get("name", "Unknown Framework")
        
        # Get overall assessment stats
        assessment_stats = self.context.get_assessment_stats()
        overall_assessment = self.context.get_overall_assessment()
        
        # Get assessment type distribution if available
        assessment_types = overall_assessment.get("assessment_types", {})
        
        return {
            "framework_id": framework_id,
            "framework_name": framework_name,
            "document_id": self.context.options.get("document_id", "unknown"),
            "document_name": self.context.options.get("document_name", "Unknown Document"),
            "document_length": len(self.context.document_text),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_rating": overall_assessment.get("average_rating"),
            "criteria_coverage": assessment_stats.get("assessment_coverage", 0),
            "total_evidence": assessment_stats.get("total_evidence", 0),
            "report_type": self.report_type,
            "includes_evidence": self.include_evidence,
            "includes_confidence": self.include_confidence,
            "assessment_types": {
                "direct": assessment_types.get("direct", 0),
                "inferred": assessment_types.get("inferred", 0),
                "insufficient_evidence": assessment_types.get("insufficient_evidence", 0)
            }
        }
    
    def _generate_scorecard(self) -> Dict[str, Any]:
        """
        Generate a structured scorecard from evaluation results.
        
        Returns:
            Structured scorecard
        """
        self.logger.info("Generating structured scorecard")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
        # Initialize dimensions list for scorecard
        dimensions = []
        
        # Counts for assessment types
        assessment_type_counts = {"direct": 0, "inferred": 0, "insufficient_evidence": 0}
        
        # Process each dimension
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
            
            # Get dimension summary
            dimension_summary = self.context.get_dimension_summary(dimension_id)
            avg_rating = dimension_summary.get("average_rating")
            
            # Initialize criteria list for this dimension
            criteria = []
            
            # Process each criterion
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                
                if not criterion_id:
                    continue
                
                # Get criterion assessment
                assessment = self.context.get_criterion_assessment(dimension_id, criterion_id)
                
                if not assessment:
                    # Skip criteria without assessments if not including N/A
                    if not self.include_na_criteria:
                        continue
                    
                    # Include as N/A
                    criterion_entry = {
                        "id": criterion_id,
                        "name": criterion_name,
                        "rating": None,
                        "rationale": "No assessment available",
                        "assessment_type": "insufficient_evidence"
                    }
                    criteria.append(criterion_entry)
                    assessment_type_counts["insufficient_evidence"] += 1
                    continue
                
                # Skip if rating is None and not including N/A
                if assessment.get("rating") is None and not self.include_na_criteria:
                    continue
                
                # Get assessment type (with fallback)
                assessment_type = assessment.get("assessment_type", "direct")
                
                # Update assessment type counts
                assessment_type_counts[assessment_type] = assessment_type_counts.get(assessment_type, 0) + 1
                
                # Create criterion entry with assessment type indication
                criterion_entry = {
                    "id": criterion_id,
                    "name": criterion_name,
                    "rating": assessment.get("rating"),
                    "rationale": assessment.get("rationale", ""),
                    "confidence": assessment.get("confidence") if self.include_confidence else None,
                    "assessment_type": assessment_type
                }
                
                # Explicitly mark inferred assessments in rationale if not already marked
                if assessment_type == "inferred" and not criterion_entry["rationale"].startswith("[INFERRED]"):
                    criterion_entry["rationale"] = f"[INFERRED] {criterion_entry['rationale']}"
                
                # Add evidence information if requested
                if self.include_evidence:
                    # Get evidence for this criterion
                    evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
                    
                    if evidence_list:
                        # Find evidence categories if available in agent observations
                        evidence_by_category = self._get_evidence_categories(dimension_id, criterion_id)
                        
                        criterion_entry["evidence_count"] = len(evidence_list)
                        criterion_entry["evidence_by_category"] = evidence_by_category
                
                criteria.append(criterion_entry)
            
            # Add dimension entry if it has criteria
            if criteria:
                dimension_entry = {
                    "id": dimension_id,
                    "name": dimension_name,
                    "average_rating": avg_rating,
                    "criteria": criteria,
                    "strengths": dimension_summary.get("strengths", []),
                    "weaknesses": dimension_summary.get("weaknesses", [])
                }
                
                dimensions.append(dimension_entry)
        
        # Calculate assessment reliability metrics
        total_criteria_assessed = sum(assessment_type_counts.values())
        direct_assessment_percentage = (
            assessment_type_counts.get("direct", 0) / max(1, total_criteria_assessed)
            if total_criteria_assessed > 0 else 0
        )
        
        # Create scorecard
        scorecard = {
            "title": f"Assessment Scorecard: {framework_name}",
            "overall_rating": overall_assessment.get("average_rating"),
            "executive_summary": overall_assessment.get("executive_summary", ""),
            "key_strengths": overall_assessment.get("key_strengths", []),
            "key_improvements": overall_assessment.get("key_improvements", []),
            "recommendations": overall_assessment.get("recommendations", []),
            "dimensions": dimensions,
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "assessment_types": assessment_type_counts,
            "direct_assessment_percentage": direct_assessment_percentage,
            "assessment_reliability": self._calculate_reliability_rating(direct_assessment_percentage)
        }
        
        return scorecard
    
    def _calculate_reliability_rating(self, direct_percentage: float) -> str:
        """
        Calculate a reliability rating based on the percentage of direct assessments.
        
        Args:
            direct_percentage: Percentage of criteria with direct assessments
            
        Returns:
            Reliability rating (High, Medium, Low)
        """
        if direct_percentage >= 0.8:
            return "High"
        elif direct_percentage >= 0.5:
            return "Medium"
        else:
            return "Low"
    
    def _get_evidence_categories(self, dimension_id: str, criterion_id: str) -> Dict[str, int]:
        """
        Get evidence category counts from agent observations.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            
        Returns:
            Dictionary of evidence counts by category
        """
        # Create criterion key
        criterion_key = f"{dimension_id}:{criterion_id}"
        
        # Look in evaluation_completed observations
        for observation in self.context.get_agent_observations(observation_type="evaluation_completed"):
            content = observation.get("content", {})
            dimensions = content.get("dimensions", {})
            
            for dim_id, dim_data in dimensions.items():
                if dim_id == dimension_id:
                    criteria = dim_data.get("criteria", {})
                    if criterion_id in criteria:
                        criterion_data = criteria[criterion_id]
                        return criterion_data.get("evidence_by_category", {})
        
        # Look in extraction_completed observations as fallback
        for observation in self.context.get_agent_observations(observation_type="extraction_completed"):
            content = observation.get("content", {})
            consolidated_evidence = content.get("consolidated_evidence", {})
            
            if criterion_key in consolidated_evidence:
                evidence_data = consolidated_evidence[criterion_key]
                return evidence_data.get("evidence_by_category", {})
        
        # Default to simple count
        evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
        return {"total": len(evidence_list)} if evidence_list else {}
    
    async def _generate_executive_summary(self) -> Dict[str, Any]:
        """
        Generate an executive summary report.
        
        Returns:
            Executive summary report
        """
        self.logger.info("Generating executive summary")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
        # Get assessment reliability info
        assessment_types = overall_assessment.get("assessment_types", {})
        direct_percentage = overall_assessment.get("direct_assessment_percentage", 0)
        reliability_rating = self._calculate_reliability_rating(direct_percentage)
        
        # Create executive summary
        exec_summary = {
            "title": f"Executive Summary: {self.context.framework.get('name', 'Assessment')}",
            "overall_rating": overall_assessment.get("average_rating"),
            "executive_summary": overall_assessment.get("executive_summary", ""),
            "key_strengths": overall_assessment.get("key_strengths", []),
            "key_improvements": overall_assessment.get("key_improvements", []),
            "recommendations": overall_assessment.get("recommendations", []),
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0),
            "assessment_reliability": reliability_rating,
            "assessment_types": assessment_types
        }
        
        # Format the executive summary with reliability note if needed
        if self.include_assessment_types:
            reliability_note = f"""
Assessment Reliability: {reliability_rating}
- Direct Assessments: {assessment_types.get('direct', 0)}
- Inferred Assessments: {assessment_types.get('inferred', 0)}
- Unable to Assess: {assessment_types.get('insufficient_evidence', 0)}
"""
            
            if reliability_rating != "High":
                reliability_note += "\nNote: Some assessments are based on inference rather than direct evidence. These are marked as [INFERRED] throughout the report."
                
            # Check if there's already an executive summary
            original_summary = exec_summary["executive_summary"]
            if original_summary:
                # Add the reliability note at the end
                exec_summary["executive_summary"] = original_summary + "\n\n" + reliability_note
            else:
                # Need to generate a summary
                exec_summary["executive_summary"] = await self._generate_new_executive_summary(
                    overall_assessment, reliability_note
                )
        
        return exec_summary
    
    async def _generate_new_executive_summary(
        self,
        overall_assessment: Dict[str, Any],
        reliability_note: str
    ) -> str:
        """
        Generate a new executive summary when none exists.
        
        Args:
            overall_assessment: Overall assessment data
            reliability_note: Note about assessment reliability
            
        Returns:
            Generated executive summary
        """
        framework_name = self.context.framework.get("name", "Assessment Framework")
        
        # Create prompt for executive summary
        system_prompt = """You are an expert report writer creating executive summaries for assessments.
Focus on clarity, brevity, and actionable insights. Write with an executive audience in mind."""
        
        human_prompt = f"""Create an executive summary for the following assessment:

FRAMEWORK: {framework_name}
OVERALL RATING: {overall_assessment.get('average_rating')}

KEY STRENGTHS:
{json.dumps(overall_assessment.get('key_strengths', []), indent=2)}

KEY AREAS FOR IMPROVEMENT:
{json.dumps(overall_assessment.get('key_improvements', []), indent=2)}

RECOMMENDATIONS:
{json.dumps(overall_assessment.get('recommendations', []), indent=2)}

Write a concise (3-4 paragraph) executive summary that:
1. Introduces the assessment purpose and scope
2. Summarizes the overall findings and rating
3. Highlights the most important strengths and improvement areas
4. Emphasizes key recommendations

Write with clarity and brevity for busy executives."""

        # Get summary text
        new_summary, _ = await self._cached_llm_call(
            "generate_executive_summary",
            f"{framework_name}_{overall_assessment.get('average_rating')}",
            "generate_completion",
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=800
        )
        
        # Add reliability note
        return new_summary + "\n\n" + reliability_note
    
    async def _generate_detailed_assessment(self) -> Dict[str, Any]:
        """
        Generate a detailed assessment report.
        
        Returns:
            Detailed assessment report
        """
        self.logger.info("Generating detailed assessment")
        
        # Use the scorecard as the base
        scorecard = self._generate_scorecard()
        
        # Get assessment reliability info
        assessment_types = scorecard.get("assessment_types", {})
        direct_percentage = scorecard.get("direct_assessment_percentage", 0)
        reliability_rating = scorecard.get("assessment_reliability", "Medium")
        
        # Create detailed assessment with introduction
        detailed_assessment = {
            "title": f"Detailed Assessment: {self.context.framework.get('name', 'Assessment')}",
            "overall_rating": scorecard.get("overall_rating"),
            "executive_summary": scorecard.get("executive_summary"),
            "key_strengths": scorecard.get("key_strengths"),
            "key_improvements": scorecard.get("key_improvements"),
            "recommendations": scorecard.get("recommendations"),
            "dimensions": scorecard.get("dimensions"),
            "assessment_types": assessment_types,
            "assessment_reliability": reliability_rating,
            "direct_assessment_percentage": direct_percentage
        }
        
        # Generate introduction
        framework_name = self.context.framework.get("name", "Assessment Framework")
        
        system_prompt = """You are an expert report writer creating detailed assessment introductions.
Focus on setting the context and explaining the assessment approach in clear, professional language."""
        
        human_prompt = f"""Create an introduction for a detailed assessment report.

FRAMEWORK: {framework_name}
OVERALL RATING: {scorecard.get("overall_rating")}
DIMENSIONS ASSESSED: {len(scorecard.get("dimensions", []))}
COVERAGE: {scorecard.get("criteria_coverage", 0) * 100:.1f}%
ASSESSMENT RELIABILITY: {reliability_rating}
DIRECT ASSESSMENTS: {assessment_types.get("direct", 0)}
INFERRED ASSESSMENTS: {assessment_types.get("inferred", 0)}

The introduction should:
1. Explain the purpose and scope of the assessment
2. Briefly describe the framework dimensions
3. Outline what readers will find in the detailed report
4. Provide guidance on how to interpret the ratings
5. Explain the difference between direct and inferred assessments

Keep your introduction professional and informative."""

        # Get introduction text
        introduction, _ = await self._cached_llm_call(
            "generate_detailed_introduction",
            f"{framework_name}_{reliability_rating}",
            "generate_completion",
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=800
        )
        
        detailed_assessment["introduction"] = introduction
        
        return detailed_assessment
    
    async def _generate_evidence_report(self) -> Dict[str, Any]:
        """
        Generate an evidence report.
        
        Returns:
            Evidence report
        """
        self.logger.info("Generating evidence report")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Create evidence map by dimension/criterion
        evidence_map = {}
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
            
            evidence_map[dimension_id] = {
                "name": dimension_name,
                "criteria": {}
            }
            
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                criterion_question = criterion.get("question", "")
                
                if not criterion_id:
                    continue
                
                # Get evidence for this criterion
                evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
                
                if not evidence_list:
                    continue
                
                # Format evidence items, grouping by relevance and sentiment
                formatted_evidence = []
                evidence_by_category = {}
                
                # Group by relevance level
                by_relevance = {
                    "Direct": [],
                    "Indirect": [],
                    "Contextual": [],
                    "Implied": []
                }
                
                for evidence in evidence_list:
                    evidence_id = evidence.get("id", "")
                    text = evidence.get("text", "")
                    metadata = evidence.get("metadata", {})
                    relevance_level = metadata.get("relevance_level", "Direct")
                    sentiment = metadata.get("sentiment", "Neutral")
                    
                    # Add to appropriate group
                    if relevance_level in by_relevance:
                        by_relevance[relevance_level].append({
                            "id": evidence_id,
                            "text": text,
                            "relevance": metadata.get("relevance_explanation", ""),
                            "confidence": metadata.get("confidence", 0.8) if self.include_confidence else None,
                            "relevance_level": relevance_level,
                            "sentiment": sentiment,
                            "sufficiency": metadata.get("sufficiency_indicator", "Moderate")
                        })
                        
                        # Count by category
                        category = f"{relevance_level.lower()}_{sentiment.lower()}"
                        evidence_by_category[category] = evidence_by_category.get(category, 0) + 1
                
                # Combine all formatted evidence
                for level, items in by_relevance.items():
                    if items:
                        formatted_evidence.extend(items)
                
                # Create criterion evidence
                evidence_map[dimension_id]["criteria"][criterion_id] = {
                    "name": criterion_name,
                    "question": criterion_question,
                    "evidence": formatted_evidence,
                    "evidence_by_category": evidence_by_category,
                    "by_relevance": by_relevance
                }
        
        # Get total evidence count
        total_evidence = sum(
            len(criterion_data["evidence"]) 
            for dimension_data in evidence_map.values() 
            for criterion_data in dimension_data["criteria"].values()
        )
        
        # Generate introduction
        system_prompt = """You are an expert report writer creating evidence report introductions.
Focus on explaining the evidence collection process and how evidence is used in the assessment."""
        
        human_prompt = f"""Create a brief introduction for an evidence report.

FRAMEWORK: {framework_name}
TOTAL EVIDENCE ITEMS: {total_evidence}
DIMENSIONS WITH EVIDENCE: {len(evidence_map)}

The introduction should:
1. Explain the evidence collection methodology
2. Describe how evidence is organized (by dimension and criterion)
3. Explain the relevance levels and sentiments:
   - Direct: Explicitly addresses the criterion
   - Indirect: Implicitly relates to the criterion
   - Contextual: Provides important context for understanding
   - Implied: Suggests something about the criterion without stating it
   - Sentiments: Positive, Negative, Neutral
4. Provide guidance on how to interpret the evidence in relation to the assessment

Keep your introduction concise and focused on the evidence collection."""

        # Get introduction
        introduction, _ = await self._cached_llm_call(
            "generate_evidence_intro",
            f"{framework_name}_{total_evidence}",
            "generate_completion",
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=800
        )
        
        # Create evidence report
        evidence_report = {
            "title": f"Evidence Report: {framework_name}",
            "introduction": introduction,
            "evidence_map": evidence_map,
            "total_evidence": total_evidence
        }
        
        return evidence_report
    
    def _generate_visualization_data(self) -> Dict[str, Any]:
        """
        Generate data structures for visualization, with enhanced categorization.
        
        Returns:
            Visualization-ready data
        """
        self.logger.info("Generating visualization data")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
        # Get assessment types if available
        assessment_types = overall_assessment.get("assessment_types", {})
        
        # Generate radar chart data (dimension ratings)
        radar_data = []
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
                
            # Get dimension summary
            dimension_summary = self.context.get_dimension_summary(dimension_id)
            avg_rating = dimension_summary.get("average_rating")
            
            if avg_rating is not None:
                radar_data.append({
                    "dimension": dimension_name,
                    "rating": avg_rating
                })
        
        # Generate heatmap data (criterion ratings) with assessment type
        heatmap_data = []
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
                
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                
                if not criterion_id:
                    continue
                    
                # Get criterion assessment
                assessment = self.context.get_criterion_assessment(dimension_id, criterion_id)
                
                if assessment and assessment.get("rating") is not None:
                    # Get assessment type
                    assessment_type = assessment.get("assessment_type", "direct")
                    
                    heatmap_data.append({
                        "dimension": dimension_name,
                        "criterion": criterion_name,
                        "rating": assessment.get("rating"),
                        "confidence": assessment.get("confidence", 0) if self.include_confidence else None,
                        "assessment_type": assessment_type,
                        "is_inferred": assessment_type == "inferred"
                    })
        
        # Generate evidence distribution data with categories
        evidence_distribution = []
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
                
            dimension_evidence = 0
            evidence_categories = {
                "direct": 0,
                "indirect": 0,
                "contextual_implied": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0
            }
            
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                
                if not criterion_id:
                    continue
                    
                # Get evidence for this criterion
                evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
                dimension_evidence += len(evidence_list)
                
                # Get evidence categories
                categories = self._get_evidence_categories(dimension_id, criterion_id)
                
                # Aggregate categories
                for category, count in categories.items():
                    if "direct" in category:
                        evidence_categories["direct"] += count
                    if "indirect" in category:
                        evidence_categories["indirect"] += count
                    if "contextual" in category or "implied" in category:
                        evidence_categories["contextual_implied"] += count
                    if "positive" in category:
                        evidence_categories["positive"] += count
                    if "negative" in category:
                        evidence_categories["negative"] += count
                    if "neutral" in category:
                        evidence_categories["neutral"] += count
            
            evidence_distribution.append({
                "dimension": dimension_name,
                "evidence_count": dimension_evidence,
                "evidence_categories": evidence_categories
            })
        
        # Generate rating distribution data with assessment type
        rating_distribution = {}
        rating_by_assessment_type = {
            "direct": {},
            "inferred": {}
        }
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            
            if not dimension_id:
                continue
                
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                
                if not criterion_id:
                    continue
                    
                # Get criterion assessment
                assessment = self.context.get_criterion_assessment(dimension_id, criterion_id)
                
                if assessment and assessment.get("rating") is not None:
                    rating = assessment.get("rating")
                    rating_str = str(rating)
                    assessment_type = assessment.get("assessment_type", "direct")
                    
                    # Overall rating distribution
                    rating_distribution[rating_str] = rating_distribution.get(rating_str, 0) + 1
                    
                    # Rating distribution by assessment type
                    if assessment_type in rating_by_assessment_type:
                        if rating_str not in rating_by_assessment_type[assessment_type]:
                            rating_by_assessment_type[assessment_type][rating_str] = 0
                        rating_by_assessment_type[assessment_type][rating_str] += 1
        
        # Calculate assessment type distribution for visualization
        assessment_type_distribution = []
        for atype, count in assessment_types.items():
            if count > 0:
                assessment_type_distribution.append({
                    "type": atype,
                    "count": count
                })
        
        # Create visualization data
        visualization_data = {
            "title": f"Visualization Data: {framework_name}",
            "overall_rating": overall_assessment.get("average_rating"),
            "radar_chart": radar_data,
            "heatmap": heatmap_data,
            "evidence_distribution": evidence_distribution,
            "rating_distribution": rating_distribution,
            "rating_by_assessment_type": rating_by_assessment_type,
            "assessment_type_distribution": assessment_type_distribution,
            "criteria_coverage": {
                "assessed": overall_assessment.get("criteria_assessed", 0),
                "total": overall_assessment.get("criteria_total", 1),
                "percentage": overall_assessment.get("criteria_coverage", 0)
            },
            "key_metrics": {
                "dimensions": len(radar_data),
                "criteria_assessed": overall_assessment.get("criteria_assessed", 0),
                "total_evidence": overall_assessment.get("total_evidence", 0),
                "average_confidence": overall_assessment.get("average_confidence", 0) if self.include_confidence else None,
                "direct_assessment_percentage": overall_assessment.get("direct_assessment_percentage", 0),
                "assessment_reliability": overall_assessment.get("assessment_reliability", "Medium")
            }
        }
        
        return visualization_data
    
    async def format_for_ui(self) -> Dict[str, Any]:
        """
        Format assessment results specifically for UI rendering.
        
        Returns:
            UI-ready assessment results with standardized structure
        """
        # Generate all reports - properly awaiting the async process method
        reports = await self.process()
        
        # Create standardized UI structure
        ui_result = {
            # Top-level scorecard for easy access
            "scorecard": reports.get("formats", {}).get("scorecard", {}),
            
            # Reports section with all report formats
            "reports": {
                "formats": reports.get("formats", {})
            },
            
            # Metadata
            "metadata": reports.get("metadata", {}),
            
            # Statistics
            "statistics": self.context.get_assessment_stats(),
            
            # Include warnings/errors
            "warnings": self.context.data.get("warnings", []),
            "errors": self.context.data.get("errors", [])
        }
        
        # Add strategy information if available
        if hasattr(self, "options") and "strategy" in self.options:
            ui_result["strategy"] = self.options["strategy"]
        
        return ui_result
    
    def _ensure_scorecard_structure(self, scorecard: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure the scorecard has all required fields for UI display.
        
        Args:
            scorecard: Scorecard data structure
            
        Returns:
            Completed scorecard with all required fields
        """
        # Create a copy to avoid modifying the original
        completed = scorecard.copy() if scorecard else {}
        
        # Ensure required top-level fields
        required_fields = [
            "title", "overall_rating", "executive_summary", 
            "key_strengths", "key_improvements", "recommendations",
            "dimensions", "criteria_coverage", "timestamp"
        ]
        
        for field in required_fields:
            if field not in completed:
                if field == "title":
                    completed[field] = f"Assessment Scorecard: {self.context.framework.get('name', 'Assessment')}"
                elif field == "dimensions":
                    completed[field] = []
                elif field in ["key_strengths", "key_improvements", "recommendations"]:
                    completed[field] = []
                elif field == "overall_rating":
                    completed[field] = None
                elif field == "criteria_coverage":
                    completed[field] = 0.0
                elif field == "timestamp":
                    completed[field] = datetime.now(timezone.utc).isoformat()
                else:
                    completed[field] = ""
        
        # Ensure each dimension has required fields
        for dimension in completed.get("dimensions", []):
            dimension_required = ["id", "name", "average_rating", "criteria", "strengths", "weaknesses"]
            for field in dimension_required:
                if field not in dimension:
                    if field == "criteria":
                        dimension[field] = []
                    elif field in ["strengths", "weaknesses"]:
                        dimension[field] = []
                    elif field == "average_rating":
                        dimension[field] = None
                    else:
                        dimension[field] = ""
            
            # Ensure each criterion has required fields
            for criterion in dimension.get("criteria", []):
                criterion_required = ["id", "name", "rating", "rationale", "confidence"]
                for field in criterion_required:
                    if field not in criterion:
                        if field == "rating":
                            criterion[field] = None
                        elif field == "confidence":
                            criterion[field] = None
                        else:
                            criterion[field] = ""
        
        return completed