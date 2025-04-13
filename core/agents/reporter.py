"""
Reporter Agent - Generates assessment reports based on evaluation results

This agent takes evaluation results and generates structured, presentation-ready
assessment reports in multiple formats.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class ReporterAgent(BaseAgent):
    """
    Generates assessment reports based on evaluation results.
    
    The Reporter is responsible for:
    1. Formatting assessment results for presentation
    2. Generating executive summaries and detailed reports
    3. Creating data structures for visualization
    4. Adding evidence links and context
    5. Structuring output for different use cases
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
        self.report_type = options.get("report_type", "comprehensive")
        self.include_evidence = options.get("include_evidence", True)
        self.include_confidence = options.get("include_confidence", True)
        self.custom_instructions = options.get("instructions", "")
        
        self.logger.info(f"{name} initialized with report_type={self.report_type}")
        
    async def process(self) -> Dict[str, Any]:
        """
        Generate assessment reports based on evaluation results.
        
        Returns:
            Generated reports
        """
        self.logger.info("Starting report generation")
        self.start_timer()
        
        try:
            # Get overall assessment and framework
            framework = self.context.framework
            overall_assessment = self.context.get_overall_assessment()
            
            # Initialize reports container
            reports = {
                "metadata": self._generate_metadata(),
                "formats": {}
            }
            
            # Generate reports based on configuration
            if self.report_type in ["comprehensive", "all"]:
                # Generate multiple report formats
                reports["formats"]["executive_summary"] = await self._generate_executive_summary()
                reports["formats"]["detailed_assessment"] = await self._generate_detailed_assessment()
                reports["formats"]["scorecard"] = await self._generate_scorecard()
                
                if self.include_evidence:
                    reports["formats"]["evidence_report"] = await self._generate_evidence_report()
            
            elif self.report_type == "executive":
                # Generate executive summary only
                reports["formats"]["executive_summary"] = await self._generate_executive_summary()
                
            elif self.report_type == "scorecard":
                # Generate scorecard only
                reports["formats"]["scorecard"] = await self._generate_scorecard()
                
            elif self.report_type == "detailed":
                # Generate detailed assessment only
                reports["formats"]["detailed_assessment"] = await self._generate_detailed_assessment()
                
            elif self.report_type == "evidence":
                # Generate evidence report only
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
            "includes_evidence": self.include_evidence,
            "includes_confidence": self.include_confidence
        }
    
    async def _generate_executive_summary(self) -> Dict[str, Any]:
        """
        Generate executive summary report.
        
        Returns:
            Executive summary report
        """
        self.logger.info("Generating executive summary")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        assessment_text = overall_assessment.get("assessment", "")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get key metrics
        avg_rating = overall_assessment.get("average_rating")
        criteria_coverage = overall_assessment.get("criteria_coverage", 0)
        total_evidence = overall_assessment.get("total_evidence", 0)
        
        # Prepare system and human prompts
        system_prompt = """You are an expert report writer. Your task is to create a concise, executive-friendly summary of an assessment. Focus on clarity, insights, and actionable recommendations."""
        
        # Add custom instructions if provided
        if self.custom_instructions:
            system_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{self.custom_instructions}"
        
        human_prompt = f"""Create an executive summary for the following assessment results.

FRAMEWORK: {framework_name}

KEY METRICS:
- Overall Rating: {avg_rating}
- Evidence Collected: {total_evidence} items
- Assessment Coverage: {criteria_coverage*100:.1f}%

ASSESSMENT OVERVIEW:
{assessment_text}

Please format your executive summary as follows:
1. A brief introduction explaining the purpose of the assessment
2. Key findings section with 3-5 bullet points highlighting the most important insights
3. A concise summary of strengths and areas for improvement
4. Clear, actionable recommendations
5. A brief conclusion

Keep your summary concise, direct, and actionable for executive readers."""
        
        # Call LLM for summary
        summary_text, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1200
        )
        
        # Create executive summary
        executive_summary = {
            "title": f"Executive Summary: {framework_name} Assessment",
            "content": summary_text,
            "metrics": {
                "overall_rating": avg_rating,
                "evidence_count": total_evidence,
                "coverage": criteria_coverage
            }
        }
        
        return executive_summary
    
    async def _generate_detailed_assessment(self) -> Dict[str, Any]:
        """
        Generate detailed assessment report.
        
        Returns:
            Detailed assessment report
        """
        self.logger.info("Generating detailed assessment")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        assessment_text = overall_assessment.get("assessment", "")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get dimension summaries and assessments
        dimension_sections = []
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
            
            # Get dimension summary
            dimension_summary = self.context.get_dimension_summary(dimension_id)
            summary_text = dimension_summary.get("summary", "")
            
            # Get criteria assessments
            criteria_sections = []
            
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                criterion_question = criterion.get("question", "")
                
                if not criterion_id:
                    continue
                
                # Get criterion assessment
                assessment = self.context.get_criterion_assessment(dimension_id, criterion_id)
                
                if not assessment:
                    continue
                
                rating = assessment.get("rating")
                rationale = assessment.get("rationale", "")
                confidence = assessment.get("confidence", 0)
                evidence_ids = assessment.get("evidence_ids", [])
                
                # Include evidence if requested
                evidence_text = ""
                if self.include_evidence and evidence_ids:
                    evidence_list = []
                    for evidence_id in evidence_ids:
                        evidence = self.context.get_evidence(evidence_id)
                        if evidence:
                            evidence_list.append(evidence.get("text", ""))
                    
                    if evidence_list:
                        evidence_text = "\n\n**Supporting Evidence:**\n\n" + "\n\n".join([f"- {ev}" for ev in evidence_list])
                
                # Create criterion section
                criterion_section = {
                    "id": criterion_id,
                    "name": criterion_name,
                    "question": criterion_question,
                    "rating": rating,
                    "rationale": rationale,
                    "confidence": confidence if self.include_confidence else None,
                    "evidence_count": len(evidence_ids),
                    "has_evidence": len(evidence_ids) > 0
                }
                
                criteria_sections.append(criterion_section)
            
            # Create dimension section
            dimension_section = {
                "id": dimension_id,
                "name": dimension_name,
                "summary": summary_text,
                "average_rating": dimension_summary.get("average_rating"),
                "criteria": criteria_sections
            }
            
            dimension_sections.append(dimension_section)
        
        # Prepare system and human prompts for introduction
        system_prompt = """You are an expert report writer. Your task is to create a compelling introduction to a detailed assessment report. Focus on setting context, explaining the assessment approach, and outlining what readers can expect in the report."""
        
        # Add custom instructions if provided
        if self.custom_instructions:
            system_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{self.custom_instructions}"
        
        human_prompt = f"""Create an introduction for a detailed assessment report.

FRAMEWORK: {framework_name}
ASSESSMENT APPROACH: This assessment was conducted by analyzing the document against {len(framework.get('dimensions', []))} dimensions and {sum(len(dim.get('criteria', [])) for dim in framework.get('dimensions', []))} criteria.

KEY METRICS:
- Overall Rating: {overall_assessment.get('average_rating')}
- Evidence Collected: {overall_assessment.get('total_evidence', 0)} items
- Assessment Coverage: {overall_assessment.get('criteria_coverage', 0)*100:.1f}%

Please craft an introduction that:
1. Explains the purpose of the assessment
2. Briefly describes the assessment methodology
3. Outlines what readers will find in the report
4. Sets expectations for how to interpret the ratings and evidence

Keep your introduction concise but informative."""
        
        # Call LLM for introduction
        introduction_text, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=800
        )
        
        # Create evidence report
        evidence_report = {
            "title": f"Evidence Report: {framework_name}",
            "introduction": introduction_text,
            "evidence_map": evidence_map,
            "total_evidence": sum(
                len(criterion_data["evidence"]) 
                for dimension_data in evidence_map.values() 
                for criterion_data in dimension_data["criteria"].values()
            )
        }
        
        return evidence_report
    
    def _generate_visualization_data(self) -> Dict[str, Any]:
        """
        Generate data structures for visualization.
        
        Returns:
            Visualization data
        """
        self.logger.info("Generating visualization data")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
        # Generate radar chart data
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
        
        # Generate heatmap data
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
        
        # Create visualization data
        visualization_data = {
            "title": f"Visualization Data: {framework_name}",
            "overall_rating": overall_assessment.get("average_rating"),
            "radar_chart": radar_data,
            "heatmap": heatmap_data,
            "evidence_distribution": evidence_distribution,
            "criteria_coverage": {
                "assessed": overall_assessment.get("criteria_assessed", 0),
                "total": overall_assessment.get("criteria_total", 1),
                "percentage": overall_assessment.get("criteria_coverage", 0)
            }
        }
        
        return visualization_data
        
        
        # Create detailed assessment
        detailed_assessment = {
            "title": f"Detailed Assessment: {framework_name}",
            "introduction": introduction_text,
            "overall_assessment": assessment_text,
            "dimensions": dimension_sections
        }
        
        return detailed_assessment
    
    async def _generate_scorecard(self) -> Dict[str, Any]:
        """
        Generate scorecard report.
        
        Returns:
            Scorecard report
        """
        self.logger.info("Generating scorecard")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
        # Get dimension scores
        dimension_scores = []
        
        for dimension in framework.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
            
            # Get dimension summary
            dimension_summary = self.context.get_dimension_summary(dimension_id)
            avg_rating = dimension_summary.get("average_rating")
            
            # Get criteria scores
            criteria_scores = []
            
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                
                if not criterion_id:
                    continue
                
                # Get criterion assessment
                assessment = self.context.get_criterion_assessment(dimension_id, criterion_id)
                
                if not assessment:
                    continue
                
                rating = assessment.get("rating")
                confidence = assessment.get("confidence", 0)
                
                # Create criterion score
                criterion_score = {
                    "id": criterion_id,
                    "name": criterion_name,
                    "rating": rating,
                    "confidence": confidence if self.include_confidence else None
                }
                
                criteria_scores.append(criterion_score)
            
            # Create dimension score
            dimension_score = {
                "id": dimension_id,
                "name": dimension_name,
                "average_rating": avg_rating,
                "criteria": criteria_scores
            }
            
            dimension_scores.append(dimension_score)
        
        # Create scorecard
        scorecard = {
            "title": f"Scorecard: {framework_name}",
            "overall_rating": overall_assessment.get("average_rating"),
            "dimensions": dimension_scores,
            "framework_id": framework.get("id", "unknown"),
            "scoring_methods": framework.get("scoring_methods", {})
        }
        
        return scorecard
    
 
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
        
        # Call LLM for introduction
        system_prompt = """You are an expert report writer. Your task is to create a brief introduction to an evidence report. Focus on explaining how evidence was collected and how it should be interpreted."""
        
        # Add custom instructions if provided
        if self.custom_instructions:
            system_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{self.custom_instructions}"
        
        human_prompt = f"""Create a brief introduction for an evidence report.

    FRAMEWORK: {framework_name}
    EVIDENCE COLLECTED: The assessment collected evidence for criteria across {len(evidence_map)} dimensions.

    Please craft an introduction that:
    1. Explains what evidence was collected
    2. How the evidence was identified and extracted
    3. How readers should interpret the evidence in the context of the assessment

    Keep your introduction concise and informative."""
        
        # Call LLM for introduction
        introduction_text, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=800
        )
        
        # Create evidence report
        evidence_report = {
            "title": f"Evidence Report: {framework_name}",
            "introduction": introduction_text,
            "evidence_map": evidence_map,
            "total_evidence": sum(
                len(criterion_data["evidence"]) 
                for dimension_data in evidence_map.values() 
                for criterion_data in dimension_data["criteria"].values()
            )
        }
        
        return evidence_report

    def _generate_visualization_data(self) -> Dict[str, Any]:
        """
        Generate data structures for visualization.
        
        Returns:
            Visualization data
        """
        self.logger.info("Generating visualization data")
        
        # Get framework info
        framework = self.context.framework
        framework_name = framework.get("name", "Assessment Framework")
        
        # Get overall assessment
        overall_assessment = self.context.get_overall_assessment()
        
        # Generate radar chart data
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
        
        # Generate heatmap data
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
        
        # Create visualization data
        visualization_data = {
            "title": f"Visualization Data: {framework_name}",
            "overall_rating": overall_assessment.get("average_rating"),
            "radar_chart": radar_data,
            "heatmap": heatmap_data,
            "evidence_distribution": evidence_distribution,
            "criteria_coverage": {
                "assessed": overall_assessment.get("criteria_assessed", 0),
                "total": overall_assessment.get("criteria_total", 1),
                "percentage": overall_assessment.get("criteria_coverage", 0)
            }
        }
        
        return visualization_data