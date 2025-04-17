"""
Streamlined Reporter Agent - Results formatting and output generation

This agent transforms evaluation results into structured reports, visualizations,
and exportable formats to complete the assessment process.
"""

import logging
import json
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from core.agents.base import BaseAgent
from core.context import AssessmentContext
from utils.path_utils import save_assessment_result, get_unique_filename, get_path

class ReporterAgent(BaseAgent):
    """
    Creates structured reports and visualizations from assessment results.
    
    Responsibilities:
    1. Format evaluations into clean, presentation-ready reports
    2. Generate visualizations for key metrics
    3. Prepare exportable formats (JSON, HTML, etc.)
    4. Create executive summaries and detailed assessments
    5. Store assessment results for later review
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
            options: Configuration options
        """
        super().__init__(name, "reporter", llm, context, options or {})
        
        # Get configuration options
        self.options = options or {}
        self.report_type = self.options.get("report_type", "scorecard")
        self.include_evidence = self.options.get("include_evidence", True)
        self.include_confidence = self.options.get("include_confidence", True)
        self.include_assessment_types = self.options.get("include_assessment_types", True)
        self.custom_instructions = self.options.get("instructions", "")
        
        # Export options
        self.export_formats = self.options.get("export_formats", ["json"])
        self.output_dir = self.options.get("output_dir", "outputs")
        
        self.logger.info(
            f"Reporter '{self.name}' initialized with report_type={self.report_type}, "
            f"export_formats={self.export_formats}"
        )
        
    async def process(self) -> Dict[str, Any]:
        """
        Generate reports from assessment results in the context.
        
        Returns:
            Dictionary containing report generation results
        """
        self.logger.info(f"Reporter '{self.name}' starting report generation")
        self.start_timer()
        
        try:
            # Get framework and context info
            framework = self.context.framework
            framework_name = framework.get("name", "Assessment Framework")
            
            # Get overall assessment
            overall_assessment = self.context.get_overall_assessment()
            if not overall_assessment:
                self.logger.warning("No overall assessment found in context")
                overall_assessment = self._create_empty_overall_assessment()
            
            # Initialize reports container
            reports = {
                "metadata": self._generate_metadata(),
                "formats": {}
            }
            
            # Generate scorecard (primary output format)
            reports["formats"]["scorecard"] = self._generate_scorecard()
            
            # Generate additional reports based on type
            if self.report_type in ["comprehensive", "all"]:
                # Generate multiple report formats
                reports["formats"]["executive_summary"] = await self._generate_executive_summary(overall_assessment)
                reports["formats"]["detailed_assessment"] = await self._generate_detailed_assessment()
                reports["formats"]["evidence_summary"] = self._generate_evidence_summary()
                
            elif self.report_type == "executive":
                # Generate executive summary only
                reports["formats"]["executive_summary"] = await self._generate_executive_summary(overall_assessment)
                
            elif self.report_type == "detailed":
                # Generate detailed assessment only
                reports["formats"]["detailed_assessment"] = await self._generate_detailed_assessment()
            
            # Always include visualization data
            reports["formats"]["visualization_data"] = self._generate_visualization_data()
            
            # Export reports to files
            export_paths = self._export_reports(reports)
            reports["export_paths"] = export_paths
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Report generation completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("reports_generated", {
                "report_formats": list(reports["formats"].keys()),
                "export_formats": list(export_paths.keys()),
                "time_taken": elapsed_time
            })
            
            return reports
            
        except Exception as e:
            self.stop_timer()
            self.logger.error(f"Error during report generation: {str(e)}", exc_info=True)
            self.context.add_warning(f"Report generation failed: {str(e)}")
            
            # Return error status
            return {
                "status": "failed",
                "error": str(e),
                "metadata": self._generate_metadata()
            }
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """
        Generate metadata for reports.
        
        Returns:
            Report metadata dictionary
        """
        # Get framework info
        framework = self.context.framework
        framework_id = framework.get("id", "unknown")
        framework_name = framework.get("name", "Unknown Framework")
        
        # Get assessment stats
        assessment_stats = self.context.get_assessment_stats()
        overall_assessment = self.context.get_overall_assessment()
        
        # Get document properties
        document_properties = {}
        if hasattr(self.context, "document_properties"):
            document_properties = self.context.document_properties
        
        # Get entity info
        entity_info = document_properties.get("primary_entity", {})
        
        # Create timestamp
        timestamp = datetime.now().isoformat()
        
        return {
            "framework_id": framework_id,
            "framework_name": framework_name,
            "document_id": self.context.options.get("document_id", "unknown"),
            "document_name": self.context.options.get("document_name", "Unknown Document"),
            "document_type": document_properties.get("document_type", "unknown"),
            "entity_name": entity_info.get("name", "unknown"),
            "entity_type": entity_info.get("type", "unknown"),
            "generated_at": timestamp,
            "overall_rating": overall_assessment.get("average_rating"),
            "criteria_coverage": assessment_stats.get("assessment_coverage", 0),
            "total_evidence": assessment_stats.get("total_evidence", 0),
            "report_type": self.report_type,
            "assessment_types": overall_assessment.get("assessment_types", {})
        }
    
    def _create_empty_overall_assessment(self) -> Dict[str, Any]:
        """
        Create an empty overall assessment if none exists.
        
        Returns:
            Basic overall assessment dictionary
        """
        return {
            "average_rating": None,
            "criteria_assessed": 0,
            "criteria_total": 0,
            "criteria_coverage": 0,
            "executive_summary": "No assessment data available.",
            "key_strengths": [],
            "key_improvements": [],
            "recommendations": [],
            "assessment_types": {"direct": 0, "inferred": 0, "insufficient_evidence": 0},
            "timestamp": time.time()
        }
    
    def _generate_scorecard(self) -> Dict[str, Any]:
        """
        Generate a structured scorecard from evaluation results.
        
        Returns:
            Scorecard dictionary
        """
        self.logger.info("Generating structured scorecard")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        if not overall_assessment:
            overall_assessment = self._create_empty_overall_assessment()
        
        # Initialize dimensions list
        dimensions = []
        
        # Process each dimension
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
            
            # Get dimension summary
            dimension_summary = self.context.get_dimension_summary(dimension_id)
            if not dimension_summary:
                self.logger.warning(f"No summary found for dimension {dimension_id}")
                continue
                
            # Initialize criteria list
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
                    self.logger.warning(f"No assessment found for criterion {criterion_id}")
                    continue
                
                # Create criterion entry
                criterion_entry = {
                    "id": criterion_id,
                    "name": criterion_name,
                    "rating": assessment.get("rating"),
                    "rationale": assessment.get("rationale", ""),
                    "assessment_type": assessment.get("assessment_type", "insufficient_evidence")
                }
                
                # Add confidence if requested
                if self.include_confidence:
                    criterion_entry["confidence"] = assessment.get("confidence", 0.0)
                
                # Add evidence information if requested
                if self.include_evidence:
                    # Get evidence for this criterion
                    evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
                    
                    if evidence_list:
                        criterion_entry["evidence_count"] = len(evidence_list)
                        
                        # Get evidence categories if available
                        evidence_categories = self.context.get_evidence_categories(dimension_id, criterion_id)
                        if evidence_categories:
                            criterion_entry["evidence_categories"] = evidence_categories
                
                criteria.append(criterion_entry)
            
            # Add dimension entry
            dimension_entry = {
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": dimension_summary.get("average_rating"),
                "summary": dimension_summary.get("summary", ""),
                "strengths": dimension_summary.get("strengths", []),
                "weaknesses": dimension_summary.get("weaknesses", []),
                "criteria": criteria
            }
            
            dimensions.append(dimension_entry)
        
        # Calculate assessment reliability metrics
        assessment_types = overall_assessment.get("assessment_types", {})
        direct_percentage = overall_assessment.get("direct_assessment_percentage", 0)
        
        # Create reliability rating
        reliability_rating = "High" if direct_percentage >= 0.8 else "Medium" if direct_percentage >= 0.5 else "Low"
        
        # Create scorecard
        scorecard = {
            "title": f"{framework_name} Assessment Scorecard",
            "overall_rating": overall_assessment.get("average_rating"),
            "executive_summary": overall_assessment.get("executive_summary", ""),
            "key_strengths": overall_assessment.get("key_strengths", []),
            "key_improvements": overall_assessment.get("key_improvements", []),
            "recommendations": overall_assessment.get("recommendations", []),
            "dimensions": dimensions,
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0),
            "assessment_types": assessment_types,
            "assessment_reliability": reliability_rating,
            "generated_at": datetime.now().isoformat()
        }
        
        return scorecard
    
    async def _generate_executive_summary(self, overall_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an executive summary report.
        
        Args:
            overall_assessment: Overall assessment dictionary
            
        Returns:
            Executive summary dictionary
        """
        self.logger.info("Generating executive summary")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Calculate assessment reliability
        assessment_types = overall_assessment.get("assessment_types", {})
        direct_percentage = overall_assessment.get("direct_assessment_percentage", 0)
        reliability_rating = "High" if direct_percentage >= 0.8 else "Medium" if direct_percentage >= 0.5 else "Low"
        
        # Create executive summary
        exec_summary = {
            "title": f"{framework_name} Executive Summary",
            "overall_rating": overall_assessment.get("average_rating"),
            "executive_summary": overall_assessment.get("executive_summary", ""),
            "key_strengths": overall_assessment.get("key_strengths", []),
            "key_improvements": overall_assessment.get("key_improvements", []),
            "recommendations": overall_assessment.get("recommendations", []),
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0),
            "assessment_reliability": reliability_rating,
            "assessment_types": assessment_types,
            "generated_at": datetime.now().isoformat()
        }
        
        # Check if executive summary exists
        if not exec_summary["executive_summary"]:
            # Generate new executive summary
            exec_summary["executive_summary"] = await self._create_executive_summary_text(
                framework_name, overall_assessment, reliability_rating
            )
        
        return exec_summary
    
    async def _create_executive_summary_text(
        self, 
        framework_name: str, 
        overall_assessment: Dict[str, Any], 
        reliability_rating: str
    ) -> str:
        """
        Generate executive summary text if not available.
        
        Args:
            framework_name: Name of the framework
            overall_assessment: Overall assessment dictionary
            reliability_rating: Assessment reliability rating
            
        Returns:
            Executive summary text
        """
        # Create system prompt
        system_prompt = """You are an assessment report writer creating an executive summary.
Create a clear, concise summary that highlights key findings and actionable insights."""
        
        # Format key points
        strengths = overall_assessment.get("key_strengths", [])
        strengths_text = "\n".join([f"- {s}" for s in strengths]) if strengths else "None identified"
        
        improvements = overall_assessment.get("key_improvements", [])
        improvements_text = "\n".join([f"- {i}" for i in improvements]) if improvements else "None identified"
        
        recommendations = overall_assessment.get("recommendations", [])
        recommendations_text = "\n".join([f"- {r}" for r in recommendations]) if recommendations else "None provided"
        
        # Create human prompt
        human_prompt = f"""Create an executive summary for the {framework_name} assessment.

OVERALL RATING: {overall_assessment.get("average_rating")}
RELIABILITY: {reliability_rating}

KEY STRENGTHS:
{strengths_text}

KEY IMPROVEMENTS:
{improvements_text}

RECOMMENDATIONS:
{recommendations_text}

Write a 3-4 paragraph executive summary that:
1. Introduces the assessment purpose
2. Summarizes the overall findings and rating
3. Highlights the most important strengths and improvement areas
4. Emphasizes key recommendations

Write in a clear, professional style appropriate for executives.
The summary should be standalone and not reference undefined elements.
"""

        # Call LLM for summary text
        summary_text, _ = await self.llm.generate_completion(
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=800
        )
        
        return summary_text.strip()
    
    async def _generate_detailed_assessment(self) -> Dict[str, Any]:
        """
        Generate a detailed assessment report.
        
        Returns:
            Detailed assessment dictionary
        """
        self.logger.info("Generating detailed assessment")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        if not overall_assessment:
            overall_assessment = self._create_empty_overall_assessment()
        
        # Use scorecard as the base
        scorecard = self._generate_scorecard()
        
        # Generate introduction
        introduction = await self._create_detailed_introduction(
            framework_name,
            len(scorecard.get("dimensions", [])),
            overall_assessment.get("criteria_coverage", 0),
            scorecard.get("assessment_reliability", "Medium")
        )
        
        # Create detailed assessment
        detailed_assessment = {
            "title": f"{framework_name} Detailed Assessment",
            "introduction": introduction,
            "overall_rating": scorecard.get("overall_rating"),
            "executive_summary": scorecard.get("executive_summary"),
            "key_strengths": scorecard.get("key_strengths"),
            "key_improvements": scorecard.get("key_improvements"),
            "recommendations": scorecard.get("recommendations"),
            "dimensions": scorecard.get("dimensions"),
            "assessment_types": scorecard.get("assessment_types"),
            "assessment_reliability": scorecard.get("assessment_reliability"),
            "generated_at": datetime.now().isoformat()
        }
        
        return detailed_assessment
    
    async def _create_detailed_introduction(
        self,
        framework_name: str,
        dimension_count: int,
        criteria_coverage: float,
        reliability_rating: str
    ) -> str:
        """
        Generate introduction for detailed assessment.
        
        Args:
            framework_name: Name of the framework
            dimension_count: Number of dimensions
            criteria_coverage: Percentage of criteria assessed
            reliability_rating: Assessment reliability rating
            
        Returns:
            Introduction text
        """
        # Create system prompt
        system_prompt = """You are an assessment report writer creating a detailed introduction.
Create a clear introduction that explains the assessment approach and how to interpret the results."""
        
        # Create human prompt
        human_prompt = f"""Write an introduction for a detailed assessment report.

FRAMEWORK: {framework_name}
DIMENSIONS: {dimension_count}
CRITERIA COVERAGE: {criteria_coverage:.1%}
RELIABILITY RATING: {reliability_rating}

The introduction should:
1. Explain the purpose of the assessment
2. Briefly describe the framework dimensions
3. Explain how to interpret the ratings
4. Note the difference between direct and inferred assessments
5. Provide guidance on how to use the detailed results

Write in a clear, professional style that helps readers understand the assessment structure.
"""

        # Call LLM for introduction text
        introduction_text, _ = await self.llm.generate_completion(
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=800
        )
        
        return introduction_text.strip()
    
    def _generate_evidence_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of evidence collected during assessment.
        
        Returns:
            Evidence summary dictionary
        """
        self.logger.info("Generating evidence summary")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Initialize evidence map
        evidence_map = {}
        total_evidence_count = 0
        
        # Process each dimension and criterion
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
                
                if not criterion_id:
                    continue
                
                # Get evidence for this criterion
                evidence_list = self.get_evidence_for_criterion(dimension_id, criterion_id)
                evidence_count = len(evidence_list)
                total_evidence_count += evidence_count
                
                if evidence_count == 0:
                    continue
                
                # Get categories if available
                evidence_categories = self.context.get_evidence_categories(dimension_id, criterion_id)
                
                # Create criterion evidence entry
                evidence_map[dimension_id]["criteria"][criterion_id] = {
                    "name": criterion_name,
                    "evidence_count": evidence_count,
                    "categories": evidence_categories or {}
                }
                
                # Include top evidence items (limited to avoid excessive size)
                top_evidence = []
                max_evidence = min(5, evidence_count)
                
                # Sort by confidence
                sorted_evidence = sorted(
                    evidence_list,
                    key=lambda x: x.get("metadata", {}).get("confidence", 0),
                    reverse=True
                )
                
                for i in range(max_evidence):
                    if i < len(sorted_evidence):
                        ev = sorted_evidence[i]
                        top_evidence.append({
                            "text": ev.get("text", ""),
                            "confidence": ev.get("metadata", {}).get("confidence", 0),
                            "relevance": ev.get("metadata", {}).get("relevance", "")
                        })
                
                evidence_map[dimension_id]["criteria"][criterion_id]["top_evidence"] = top_evidence
        
        # Create evidence summary
        evidence_summary = {
            "title": f"{framework_name} Evidence Summary",
            "total_evidence": total_evidence_count,
            "evidence_map": evidence_map,
            "generated_at": datetime.now().isoformat()
        }
        
        return evidence_summary
    
    def _generate_visualization_data(self) -> Dict[str, Any]:
        """
        Generate data for visualizations.
        
        Returns:
            Visualization data dictionary
        """
        self.logger.info("Generating visualization data")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        if not overall_assessment:
            overall_assessment = self._create_empty_overall_assessment()
        
        # Create dimension ratings for radar chart
        dimension_ratings = []
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
                
            # Get dimension summary
            dimension_summary = self.context.get_dimension_summary(dimension_id)
            if dimension_summary and dimension_summary.get("average_rating") is not None:
                dimension_ratings.append({
                    "dimension": dimension_name,
                    "rating": dimension_summary.get("average_rating")
                })
        
        # Create criterion ratings for heatmap
        criterion_ratings = []
        
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
                    criterion_ratings.append({
                        "dimension": dimension_name,
                        "criterion": criterion_name,
                        "rating": assessment.get("rating"),
                        "assessment_type": assessment.get("assessment_type", "direct")
                    })
        
        # Create assessment type distribution
        assessment_types = overall_assessment.get("assessment_types", {})
        assessment_type_data = [
            {"type": "Direct", "count": assessment_types.get("direct", 0)},
            {"type": "Inferred", "count": assessment_types.get("inferred", 0)},
            {"type": "Insufficient Evidence", "count": assessment_types.get("insufficient_evidence", 0)}
        ]
        
        # Create visualization data
        visualization_data = {
            "title": f"{framework_name} Visualization Data",
            "overall_rating": overall_assessment.get("average_rating"),
            "dimension_ratings": dimension_ratings,
            "criterion_ratings": criterion_ratings,
            "assessment_types": assessment_type_data,
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0),
            "key_metrics": {
                "total_criteria": overall_assessment.get("criteria_total", 0),
                "criteria_assessed": overall_assessment.get("criteria_assessed", 0),
                "direct_percentage": overall_assessment.get("direct_assessment_percentage", 0)
            }
        }
        
        return visualization_data
    
    def _export_reports(self, reports: Dict[str, Any]) -> Dict[str, str]:
        """
        Export reports to files in various formats.
        
        Args:
            reports: Reports dictionary
            
        Returns:
            Dictionary mapping formats to file paths
        """
        self.logger.info(f"Exporting reports in formats: {self.export_formats}")
        
        # Get metadata
        metadata = reports.get("metadata", {})
        framework_id = metadata.get("framework_id", "unknown")
        document_id = metadata.get("document_id", "unknown")
        
        # Create base filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"assessment_{framework_id}_{document_id}_{timestamp}"
        
        # Export paths
        export_paths = {}
        
        try:
            # Export as JSON
            if "json" in self.export_formats:
                # Save full reports
                json_path = save_assessment_result(reports, base_filename)
                export_paths["json"] = str(json_path)
                
                # Also save scorecard separately for easier access
                scorecard = reports.get("formats", {}).get("scorecard", {})
                if scorecard:
                    scorecard_filename = f"{base_filename}_scorecard"
                    scorecard_path = save_assessment_result(scorecard, scorecard_filename)
                    export_paths["json_scorecard"] = str(scorecard_path)
                
                self.logger.info(f"Exported JSON reports to: {json_path}")
            
            # Export as HTML
            if "html" in self.export_formats:
                # Generate HTML report from scorecard
                scorecard = reports.get("formats", {}).get("scorecard", {})
                if scorecard:
                    html_content = self._generate_html_report(scorecard)
                    
                    # Save HTML file
                    output_dir = get_path("outputs")
                    html_filename = get_unique_filename("outputs", f"{base_filename}_report", ".html")
                    html_path = output_dir / html_filename
                    
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                        
                    export_paths["html"] = str(html_path)
                    self.logger.info(f"Exported HTML report to: {html_path}")
            
            # Export as Markdown
            if "markdown" in self.export_formats:
                # Generate Markdown report
                scorecard = reports.get("formats", {}).get("scorecard", {})
                if scorecard:
                    markdown_content = self._generate_markdown_report(scorecard)
                    
                    # Save Markdown file
                    output_dir = get_path("outputs")
                    md_filename = get_unique_filename("outputs", f"{base_filename}_report", ".md")
                    md_path = output_dir / md_filename
                    
                    with open(md_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                        
                    export_paths["markdown"] = str(md_path)
                    self.logger.info(f"Exported Markdown report to: {md_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting reports: {str(e)}", exc_info=True)
            self.context.add_warning(f"Error exporting reports: {str(e)}")
        
        return export_paths
    
    def _generate_html_report(self, scorecard: Dict[str, Any]) -> str:
        """
        Generate HTML report from scorecard.
        
        Args:
            scorecard: Scorecard dictionary
            
        Returns:
            HTML report content
        """
        # Get basic information
        title = scorecard.get("title", "Assessment Report")
        overall_rating = scorecard.get("overall_rating")
        executive_summary = scorecard.get("executive_summary", "")
        dimensions = scorecard.get("dimensions", [])
        
        # Format overall rating
        rating_display = f"{overall_rating:.1f}" if overall_rating is not None else "N/A"
        
        # Create HTML content
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ margin-bottom: 20px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #3498db; margin-top: 30px; }}
        h3 {{ color: #2980b9; }}
        .summary {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .overall-rating {{ font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
        .dimension {{ margin-bottom: 30px; border: 1px solid #ddd; border-radius: 5px; padding: 15px; }}
        .criterion {{ margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee; }}
        .rating {{ font-weight: bold; }}
        .rating.direct {{ color: #27ae60; }}
        .rating.inferred {{ color: #f39c12; }}
        .rating.insufficient {{ color: #e74c3c; }}
        .strengths {{ color: #27ae60; }}
        .weaknesses {{ color: #e74c3c; }}
        footer {{ margin-top: 30px; font-size: 0.8em; color: #7f8c8d; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <div class="overall-rating">Overall Rating: {rating_display}</div>
        </header>
        
        <section class="summary">
            <h2>Executive Summary</h2>
            <p>{executive_summary}</p>
            
            <h3>Key Strengths</h3>
            <ul>
"""
        
        # Add key strengths
        for strength in scorecard.get("key_strengths", []):
            html += f"                <li>{strength}</li>\n"
        
        html += """            </ul>
            
            <h3>Key Improvement Areas</h3>
            <ul>
"""
        
        # Add key improvements
        for improvement in scorecard.get("key_improvements", []):
            html += f"                <li>{improvement}</li>\n"
        
        html += """            </ul>
            
            <h3>Recommendations</h3>
            <ul>
"""
        
        # Add recommendations
        for recommendation in scorecard.get("recommendations", []):
            html += f"                <li>{recommendation}</li>\n"
        
        html += """            </ul>
        </section>
        
        <section class="dimensions">
            <h2>Dimension Assessments</h2>
"""
        
        # Add dimensions
        for dimension in dimensions:
            dimension_name = dimension.get("name", "")
            dimension_rating = dimension.get("average_rating")
            dimension_summary = dimension.get("summary", "")
            
            # Format dimension rating
            dimension_rating_display = f"{dimension_rating:.1f}" if dimension_rating is not None else "N/A"
            
            html += f"""            <div class="dimension">
                <h3>{dimension_name} (Rating: {dimension_rating_display})</h3>
                <p>{dimension_summary}</p>
                
                <h4>Strengths</h4>
                <ul class="strengths">
"""
            
            # Add dimension strengths
            for strength in dimension.get("strengths", []):
                html += f"                    <li>{strength}</li>\n"
            
            html += """                </ul>
                
                <h4>Weaknesses</h4>
                <ul class="weaknesses">
"""
            
            # Add dimension weaknesses
            for weakness in dimension.get("weaknesses", []):
                html += f"                    <li>{weakness}</li>\n"
            
            html += """                </ul>
                
                <h4>Criteria</h4>
"""
            
            # Add criteria
            for criterion in dimension.get("criteria", []):
                criterion_name = criterion.get("name", "")
                criterion_rating = criterion.get("rating")
                criterion_rationale = criterion.get("rationale", "")
                assessment_type = criterion.get("assessment_type", "insufficient_evidence")
                
                # Format criterion rating
                if criterion_rating is not None:
                    criterion_rating_display = f"{criterion_rating:.1f}"
                else:
                    criterion_rating_display = "N/A"
                
                # Determine rating class
                rating_class = {
                    "direct": "direct",
                    "inferred": "inferred",
                    "insufficient_evidence": "insufficient"
                }.get(assessment_type, "insufficient")
                
                html += f"""                <div class="criterion">
                    <h5>{criterion_name} (<span class="rating {rating_class}">Rating: {criterion_rating_display} ({assessment_type})</span>)</h5>
                    <p>{criterion_rationale}</p>
                </div>
"""
            
            html += "            </div>\n"
        
        html += """        </section>
        
        <footer>
            <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </footer>
    </div>
</body>
</html>"""
        
        return html
    
    def _generate_markdown_report(self, scorecard: Dict[str, Any]) -> str:
        """
        Generate Markdown report from scorecard.
        
        Args:
            scorecard: Scorecard dictionary
            
        Returns:
            Markdown report content
        """
        # Get basic information
        title = scorecard.get("title", "Assessment Report")
        overall_rating = scorecard.get("overall_rating")
        executive_summary = scorecard.get("executive_summary", "")
        dimensions = scorecard.get("dimensions", [])
        
        # Format overall rating
        rating_display = f"{overall_rating:.1f}" if overall_rating is not None else "N/A"
        
        # Create Markdown content
        markdown = f"# {title}\n\n"
        markdown += f"**Overall Rating:** {rating_display}\n\n"
        
        # Executive Summary
        markdown += "## Executive Summary\n\n"
        markdown += f"{executive_summary}\n\n"
        
        # Key Strengths
        markdown += "### Key Strengths\n\n"
        for strength in scorecard.get("key_strengths", []):
            markdown += f"- {strength}\n"
        markdown += "\n"
        
        # Key Improvement Areas
        markdown += "### Key Improvement Areas\n\n"
        for improvement in scorecard.get("key_improvements", []):
            markdown += f"- {improvement}\n"
        markdown += "\n"
        
        # Recommendations
        markdown += "### Recommendations\n\n"
        for recommendation in scorecard.get("recommendations", []):
            markdown += f"- {recommendation}\n"
        markdown += "\n"
        
        # Dimension Assessments
        markdown += "## Dimension Assessments\n\n"
        
        for dimension in dimensions:
            dimension_name = dimension.get("name", "")
            dimension_rating = dimension.get("average_rating")
            dimension_summary = dimension.get("summary", "")
            
            # Format dimension rating
            dimension_rating_display = f"{dimension_rating:.1f}" if dimension_rating is not None else "N/A"
            
            markdown += f"### {dimension_name} (Rating: {dimension_rating_display})\n\n"
            markdown += f"{dimension_summary}\n\n"
            
            # Strengths
            markdown += "#### Strengths\n\n"
            for strength in dimension.get("strengths", []):
                markdown += f"- {strength}\n"
            markdown += "\n"
            
            # Weaknesses
            markdown += "#### Weaknesses\n\n"
            for weakness in dimension.get("weaknesses", []):
                markdown += f"- {weakness}\n"
            markdown += "\n"
            
            # Criteria
            markdown += "#### Criteria\n\n"
            
            for criterion in dimension.get("criteria", []):
                criterion_name = criterion.get("name", "")
                criterion_rating = criterion.get("rating")
                criterion_rationale = criterion.get("rationale", "")
                assessment_type = criterion.get("assessment_type", "insufficient_evidence")
                
                # Format criterion rating
                if criterion_rating is not None:
                    criterion_rating_display = f"{criterion_rating:.1f}"
                else:
                    criterion_rating_display = "N/A"
                
                markdown += f"##### {criterion_name} (Rating: {criterion_rating_display}, Type: {assessment_type})\n\n"
                markdown += f"{criterion_rationale}\n\n"
        
        # Footer
        markdown += f"---\n*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return markdown
    
    async def format_for_ui(self) -> Dict[str, Any]:
        """
        Format assessment results for UI display.
        
        Returns:
            UI-ready assessment results
        """
        self.logger.info("Formatting assessment results for UI display")
        
        # Generate reports if not already done
        reports = await self.process()
        
        # Create UI-ready result structure
        ui_result = {
            # Top-level scorecard for easy access
            "scorecard": reports.get("formats", {}).get("scorecard", {}),
            
            # Reports section with all report formats
            "reports": reports.get("formats", {}),
            
            # Metadata
            "metadata": reports.get("metadata", {}),
            
            # Statistics
            "statistics": self.context.get_assessment_stats(),
            
            # Export paths
            "export_paths": reports.get("export_paths", {}),
            
            # Include warnings/errors
            "warnings": self.context.data.get("operations", {}).get("warnings", []),
            "errors": self.context.data.get("operations", {}).get("errors", [])
        }
        
        return ui_result