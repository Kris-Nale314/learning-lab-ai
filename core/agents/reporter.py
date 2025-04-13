"""
Structured Reporter Agent - Creates presentation-ready reports from evaluation results

This agent formats the structured evaluations into clear, concise reports including
scorecards, executive summaries, and visualization-ready data.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class ReporterAgent(BaseAgent):
    """
    Creates structured reports based on evaluation results.
    
    The Structured Reporter is responsible for:
    1. Formatting evaluations into clean, presentation-ready reports
    2. Creating a structured scorecard as the primary output
    3. Generating executive summaries and detailed assessments
    4. Producing visualization-ready data structures
    5. Adding cross-references and traceability between sections
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
            "includes_confidence": self.include_confidence
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
                
                if not assessment or assessment.get("rating") is None:
                    # Skip criteria without assessments
                    continue
                
                # Create criterion entry
                criterion_entry = {
                    "id": criterion_id,
                    "name": criterion_name,
                    "rating": assessment.get("rating"),
                    "rationale": assessment.get("rationale", ""),
                    "confidence": assessment.get("confidence") if self.include_confidence else None
                }
                
                # Add evidence summary if requested
                if self.include_evidence:
                    # Get evidence for this criterion
                    evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
                    
                    if evidence_list:
                        evidence_summary = f"Evidence: {len(evidence_list)} items found"
                        criterion_entry["evidence_summary"] = evidence_summary
                
                criteria.append(criterion_entry)
            
            # Add dimension entry
            dimension_entry = {
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": avg_rating,
                "criteria": criteria,
                "strengths": dimension_summary.get("strengths", []),
                "weaknesses": dimension_summary.get("weaknesses", [])
            }
            
            dimensions.append(dimension_entry)
        
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
            "timestamp": overall_assessment.get("timestamp")
        }
        
        return scorecard
    
    async def _generate_executive_summary(self) -> Dict[str, Any]:
        """
        Generate an executive summary report.
        
        Returns:
            Executive summary report
        """
        self.logger.info("Generating executive summary")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
        # Create executive summary
        exec_summary = {
            "title": f"Executive Summary: {self.context.framework.get('name', 'Assessment')}",
            "overall_rating": overall_assessment.get("average_rating"),
            "executive_summary": overall_assessment.get("executive_summary", ""),
            "key_strengths": overall_assessment.get("key_strengths", []),
            "key_improvements": overall_assessment.get("key_improvements", []),
            "recommendations": overall_assessment.get("recommendations", []),
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0)
        }
        
        # Format the executive summary
        summary_text = overall_assessment.get("executive_summary", "")
        if summary_text:
            # No need to generate new content - use what the evaluator already produced
            return exec_summary
        
        # Generate a summary if none exists
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
        new_summary, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=800
        )
        
        exec_summary["executive_summary"] = new_summary
        
        return exec_summary
        
    async def _generate_detailed_assessment(self) -> Dict[str, Any]:
        """
        Generate a detailed assessment report.
        
        Returns:
            Detailed assessment report
        """
        self.logger.info("Generating detailed assessment")
        
        # Use the scorecard as the base
        scorecard = self._generate_scorecard()
        
        # Get overall assessment for cross-dimensional insights
        overall_assessment = self.context.get_overall_assessment()
        
        # Create detailed assessment with introduction
        detailed_assessment = {
            "title": f"Detailed Assessment: {self.context.framework.get('name', 'Assessment')}",
            "overall_rating": scorecard.get("overall_rating"),
            "executive_summary": scorecard.get("executive_summary"),
            "key_strengths": scorecard.get("key_strengths"),
            "key_improvements": scorecard.get("key_improvements"),
            "recommendations": scorecard.get("recommendations"),
            "dimensions": scorecard.get("dimensions")
        }
        
        # Generate introduction
        framework_name = self.context.framework.get("name", "Assessment Framework")
        
        system_prompt = """You are an expert report writer creating detailed assessment introductions.
Focus on setting the context and explaining the assessment approach in clear, professional language."""
        
        human_prompt = f"""Create an introduction for a detailed assessment report.

FRAMEWORK: {framework_name}
OVERALL RATING: {scorecard.get("overall_rating")}
DIMENSIONS ASSESSED: {len(scorecard.get("dimensions", []))}
COVERAGE: {overall_assessment.get("criteria_coverage", 0) * 100:.1f}%

The introduction should:
1. Explain the purpose and scope of the assessment
2. Briefly describe the framework dimensions
3. Outline what readers will find in the detailed report
4. Provide guidance on how to interpret the ratings

Keep your introduction professional and informative."""

        # Get introduction text
        introduction, _ = await self._safe_llm_call(
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
                
                # Format evidence items
                formatted_evidence = []
                
                for evidence in evidence_list:
                    evidence_id = evidence.get("id", "")
                    text = evidence.get("text", "")
                    metadata = evidence.get("metadata", {})
                    
                    # Create formatted evidence
                    formatted_item = {
                        "id": evidence_id,
                        "text": text,
                        "relevance": metadata.get("relevance_explanation", ""),
                        "confidence": metadata.get("confidence", 0.8) if self.include_confidence else None,
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
3. Explain the relevance levels and confidence ratings
4. Provide guidance on how to interpret the evidence in relation to the assessment

Keep your introduction concise and focused on the evidence collection."""

        # Get introduction
        introduction, _ = await self._safe_llm_call(
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
        Generate data structures for visualization.
        
        Returns:
            Visualization-ready data
        """
        self.logger.info("Generating visualization data")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
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
        
        # Generate heatmap data (criterion ratings)
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
                    heatmap_data.append({
                        "dimension": dimension_name,
                        "criterion": criterion_name,
                        "rating": assessment.get("rating"),
                        "confidence": assessment.get("confidence", 0) if self.include_confidence else None
                    })
        
        # Generate evidence distribution data
        evidence_distribution = []
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
                
            dimension_evidence = 0
            
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                
                if not criterion_id:
                    continue
                    
                # Get evidence for this criterion
                evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
                dimension_evidence += len(evidence_list)
            
            evidence_distribution.append({
                "dimension": dimension_name,
                "evidence_count": dimension_evidence
            })
        
        # Generate rating distribution data
        rating_distribution = {}
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
                    rating_distribution[rating_str] = rating_distribution.get(rating_str, 0) + 1
        
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
                "total_evidence": overall_assessment.get("total_evidence", 0),
                "average_confidence": overall_assessment.get("average_confidence", 0) if self.include_confidence else None
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