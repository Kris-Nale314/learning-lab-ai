"""
Enhanced Reporter Agent - Generates structured assessment reports from evaluation results

This agent takes structured evaluation results and produces formatted assessment reports
including detailed scorecards and visualization-ready data.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class ReporterAgent(BaseAgent):
    """
    Generates structured assessment reports based on evaluation results.
    
    The Reporter is responsible for:
    1. Creating detailed scorecards for criteria and dimensions
    2. Formatting assessment results for clear presentation
    3. Generating data structures for visualization
    4. Adding evidence links and cross-references
    5. Producing multiple output formats for different audiences
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
        self.report_type = options.get("report_type", "scorecard")  # Default to scorecard
        self.include_evidence = options.get("include_evidence", True)
        self.include_confidence = options.get("include_confidence", True)
        self.audience = options.get("audience", "executive")  # executive, technical, or comprehensive
        self.custom_instructions = options.get("instructions", "")
        
        self.logger.info(f"{name} initialized with report_type={self.report_type}, audience={self.audience}")
        
    async def process(self) -> Dict[str, Any]:
        """
        Generate assessment reports based on evaluation results.
        
        Returns:
            Generated reports
        """
        self.logger.info("Starting report generation")
        self.start_timer()
        
        try:
            # Get framework and overall assessment
            framework = self.context.framework
            overall_assessment = self.context.get_overall_assessment()
            
            # Initialize reports container
            reports = {
                "metadata": self._generate_metadata(),
                "formats": {}
            }
            
            # Always generate scorecard as the default format
            reports["formats"]["scorecard"] = self._generate_scorecard()
            
            # Generate additional reports based on configuration
            if self.report_type in ["comprehensive", "all"]:
                # Generate multiple report formats
                reports["formats"]["executive_summary"] = await self._generate_executive_summary()
                reports["formats"]["detailed_assessment"] = await self._generate_detailed_assessment()
                
                if self.include_evidence:
                    reports["formats"]["evidence_report"] = await self._generate_evidence_report()
                
            elif self.report_type == "executive":
                # Generate executive summary
                reports["formats"]["executive_summary"] = await self._generate_executive_summary()
                
            elif self.report_type == "detailed":
                # Generate detailed assessment
                reports["formats"]["detailed_assessment"] = await self._generate_detailed_assessment()
                
            elif self.report_type == "evidence" and self.include_evidence:
                # Generate evidence report
                reports["formats"]["evidence_report"] = await self._generate_evidence_report()
            
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
            "generated_at": datetime.now().isoformat(),
            "overall_rating": overall_assessment.get("average_rating"),
            "criteria_coverage": assessment_stats.get("assessment_coverage", 0),
            "total_evidence": assessment_stats.get("total_evidence", 0),
            "report_type": self.report_type,
            "audience": self.audience,
            "includes_evidence": self.include_evidence,
            "includes_confidence": self.include_confidence
        }
    
    def _generate_scorecard(self) -> Dict[str, Any]:
        """
        Generate structured scorecard report.
        
        Returns:
            Scorecard report with detailed ratings for all criteria
        """
        self.logger.info("Generating structured scorecard")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        overall_rating = overall_assessment.get("average_rating")
        exec_summary = overall_assessment.get("executive_summary", "")
        key_strengths = overall_assessment.get("key_strengths", [])
        key_improvements = overall_assessment.get("key_improvements", [])
        recommendations = overall_assessment.get("recommendations", [])
        
        # Process each dimension
        dimensions = []
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
                
            # Get dimension summary
            dimension_summary = self.context.get_dimension_summary(dimension_id)
            avg_rating = dimension_summary.get("average_rating")
            strengths = dimension_summary.get("strengths", [])
            weaknesses = dimension_summary.get("weaknesses", [])
            insights = dimension_summary.get("insights", [])
            summary_text = dimension_summary.get("summary", "")
            
            # Process criteria in this dimension
            criteria = []
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                criterion_question = criterion.get("question", "")
                
                if not criterion_id:
                    continue
                    
                # Get assessment for this criterion
                assessment = self.context.get_criterion_assessment(dimension_id, criterion_id)
                
                if not assessment or assessment.get("rating") is None:
                    # Skip criteria without assessments
                    continue
                
                # Extract criterion data
                rating = assessment.get("rating")
                rationale = assessment.get("rationale", "")
                confidence = assessment.get("confidence", 0.0) if self.include_confidence else None
                evidence_ids = assessment.get("evidence_ids", [])
                
                # Find scoring definition for this rating
                rating_definition = ""
                scoring_method = criterion.get("scoring_method", "scale_1_5")
                scoring_definitions = criterion.get("scoring_definitions", {})
                
                if str(rating) in scoring_definitions:
                    rating_definition = scoring_definitions[str(rating)]
                
                # Create criterion entry
                criterion_entry = {
                    "id": criterion_id,
                    "name": criterion_name,
                    "question": criterion_question,
                    "rating": rating,
                    "rating_definition": rating_definition,
                    "rationale": rationale,
                    "confidence": confidence,
                    "evidence_count": len(evidence_ids),
                    "has_evidence": len(evidence_ids) > 0
                }
                
                # Add evidence if requested
                if self.include_evidence and evidence_ids:
                    evidence_items = []
                    for evidence_id in evidence_ids:
                        evidence = self.context.get_evidence(evidence_id)
                        if evidence:
                            # Create evidence entry
                            evidence_items.append({
                                "id": evidence_id,
                                "text": evidence.get("text", ""),
                                "relevance": evidence.get("metadata", {}).get("relevance", ""),
                                "confidence": evidence.get("metadata", {}).get("confidence", 0.0) if self.include_confidence else None
                            })
                    
                    criterion_entry["evidence"] = evidence_items
                
                criteria.append(criterion_entry)
            
            # Add dimension entry
            dimension_entry = {
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": avg_rating,
                "criteria_count": len(criteria),
                "criteria": criteria,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "insights": insights,
                "summary": summary_text
            }
            
            dimensions.append(dimension_entry)
        
        # Create scorecard
        scorecard = {
            "title": f"Assessment Scorecard: {framework_name}",
            "framework_id": framework.get("id", "unknown"),
            "overall_rating": overall_rating,
            "executive_summary": exec_summary,
            "key_strengths": key_strengths,
            "key_improvements": key_improvements,
            "recommendations": recommendations,
            "dimensions": dimensions,
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0),
            "scoring_methods": framework.get("scoring_methods", {})
        }
        
        return scorecard
    
    async def _generate_executive_summary(self) -> Dict[str, Any]:
        """
        Generate executive summary report.
        
        Returns:
            Executive summary report
        """
        self.logger.info("Generating executive summary")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
        # Extract key information
        exec_summary = overall_assessment.get("executive_summary", "")
        avg_rating = overall_assessment.get("average_rating")
        key_strengths = overall_assessment.get("key_strengths", [])
        key_improvements = overall_assessment.get("key_improvements", [])
        recommendations = overall_assessment.get("recommendations", [])
        success_factors = overall_assessment.get("critical_success_factors", [])
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Create executive summary
        summary = {
            "title": f"Executive Summary: {framework_name} Assessment",
            "overall_rating": avg_rating,
            "executive_summary": exec_summary,
            "key_strengths": key_strengths,
            "key_improvements": key_improvements,
            "recommendations": recommendations,
            "critical_success_factors": success_factors,
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0),
            "timestamp": overall_assessment.get("timestamp", "")
        }
        
        return summary
        
    async def _generate_detailed_assessment(self) -> Dict[str, Any]:
        """
        Generate detailed assessment report.
        
        Returns:
            Detailed assessment report
        """
        self.logger.info("Generating detailed assessment")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Extract cross-dimension insights
        relationships = overall_assessment.get("cross_dimension_relationships", [])
        patterns = overall_assessment.get("cross_dimension_patterns", [])
        
        # Create detailed assessment (using scorecard data as base)
        scorecard = self._generate_scorecard()
        
        # Add additional detailed information
        detailed = {
            "title": f"Detailed Assessment: {framework_name}",
            "overall_rating": scorecard.get("overall_rating"),
            "executive_summary": scorecard.get("executive_summary"),
            "key_strengths": scorecard.get("key_strengths"),
            "key_improvements": scorecard.get("key_improvements"),
            "recommendations": scorecard.get("recommendations"),
            "dimensions": scorecard.get("dimensions"),
            "cross_dimension_relationships": relationships,
            "cross_dimension_patterns": patterns,
            "criteria_coverage": overall_assessment.get("criteria_coverage", 0)
        }
        
        # Create introduction for the detailed report
        prompt = f"""Create an introduction for a detailed assessment report.

FRAMEWORK: {framework_name}
OVERALL RATING: {scorecard.get("overall_rating")}
NUMBER OF DIMENSIONS: {len(scorecard.get("dimensions", []))}
CRITERIA COVERAGE: {overall_assessment.get("criteria_coverage", 0) * 100:.1f}%

The introduction should:
1. Explain the purpose of the assessment
2. Describe the framework and its dimensions
3. Outline what readers will find in the report
4. Provide guidance on how to interpret the ratings

Keep your introduction concise but informative."""

        # Get introduction text
        introduction, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=prompt,
            system_prompt="You are an expert report writer creating introductions for assessment reports.",
            temperature=0.3,
            max_tokens=800
        )
        
        detailed["introduction"] = introduction
        
        return detailed
    
    async def _generate_evidence_report(self) -> Dict[str, Any]:
        """
        Generate evidence report.
        
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
                    chunk_id = evidence.get("chunk_id", "")
                    metadata = evidence.get("metadata", {})
                    
                    # Get chunk if available
                    chunk = self.context.get_chunk(chunk_id) if chunk_id else None
                    chunk_text = chunk.get("text", "") if chunk else ""
                    
                    # Create formatted evidence
                    formatted_item = {
                        "id": evidence_id,
                        "text": text,
                        "chunk_id": chunk_id,
                        "context": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text,
                        "confidence": metadata.get("confidence", 0.8) if self.include_confidence else None,
                        "relevance": metadata.get("relevance", "")
                    }
                    
                    formatted_evidence.append(formatted_item)
                
                # Create criterion evidence
                evidence_map[dimension_id]["criteria"][criterion_id] = {
                    "name": criterion_name,
                    "question": criterion_question,
                    "evidence": formatted_evidence
                }
        
        # Calculate total evidence count
        total_evidence = sum(
            len(criterion_data["evidence"]) 
            for dimension_data in evidence_map.values() 
            for criterion_data in dimension_data["criteria"].values()
        )
        
        # Create prompt for introduction
        prompt = f"""Create a brief introduction for an evidence report.

FRAMEWORK: {framework_name}
TOTAL EVIDENCE ITEMS: {total_evidence}
DIMENSIONS WITH EVIDENCE: {len(evidence_map)}

The introduction should:
1. Explain what evidence was collected and how
2. Describe how the evidence was used for assessment
3. Provide guidance on how to interpret the evidence
4. Explain the relevance and confidence scores (if applicable)

Keep your introduction concise and focused on the evidence collection process."""

        # Get introduction text
        introduction, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=prompt,
            system_prompt="You are an expert report writer creating introductions for evidence reports.",
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