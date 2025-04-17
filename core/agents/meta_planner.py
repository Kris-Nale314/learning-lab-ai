"""
Updated Meta Planner Agent - Creates strategies optimized for the streamlined evidence packet approach

This agent analyzes documents and frameworks to design simple but effective strategies
for extracting consolidated evidence packets and performing consistent evaluations.
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class MetaPlannerAgent(BaseAgent):
    """
    Designs assessment strategies optimized for the streamlined evidence packet approach.
    
    The Meta Planner is responsible for:
    1. Analyzing document content and framework structure
    2. Creating clear instructions for extractors to produce consolidated evidence packets
    3. Identifying related criteria for potential combined evaluation
    4. Configuring the evaluator for optimal assessment consistency
    5. Creating simple, LLM-friendly prompts throughout the process
    """
    
    def __init__(
        self,
        llm,
        context: AssessmentContext,
        name: str = "MetaPlanner",
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Meta Planner agent.
        
        Args:
            llm: Language model instance
            context: Assessment context
            name: Agent name
            options: Configuration options
        """
        super().__init__(name, "planner", llm, context, options or {})
        
        # Get planner options with defaults
        self.options = options or {}
        self.max_concurrent = self.options.get("max_concurrent", 3)
        
        # Settings for the two-pass evidence packet approach
        self.use_combined_evaluation = self.options.get("use_combined_evaluation", True)
        self.max_criteria_per_group = self.options.get("max_criteria_per_group", 3)
        
        self.logger.info(f"{name} initialized with combined_evaluation={self.use_combined_evaluation}")
        
    async def process(self) -> Dict[str, Any]:
        """
        Analyze document and framework to design an assessment strategy.
        
        Returns:
            Assessment strategy dictionary
        """
        self.logger.info("Starting assessment strategy planning")
        self.start_timer()
        
        try:
            # Get document preview for analysis
            document_preview_length = 5000
            document_preview = self._get_document_preview(document_preview_length)
            
            # Analyze document structure and content
            document_analysis = await self._analyze_document(document_preview)
            
            # Analyze framework complexity and evidence requirements
            framework_analysis = self._analyze_framework()
            
            # Design assessment strategy
            assessment_strategy = await self._design_strategy(document_analysis, framework_analysis)
            
            # Define output schema
            output_schema = self._define_output_schema(framework_analysis)
            assessment_strategy["output_schema"] = output_schema
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Assessment strategy planning completed in {elapsed_time:.2f}s")
            
            # Record observation with strategy
            self.record_observation("strategy_created", assessment_strategy)
            
            return assessment_strategy
            
        except Exception as e:
            self.stop_timer()
            self.logger.error(f"Error during assessment strategy planning: {str(e)}", exc_info=True)
            self.add_warning(f"Failed to create assessment strategy: {str(e)}")
            
            # Create fallback strategy
            fallback_strategy = self._create_fallback_strategy()
            return fallback_strategy
    
    def _get_document_preview(self, max_length: int = 5000) -> str:
        """
        Get a preview of the document for analysis.
        
        Args:
            max_length: Maximum length of preview
            
        Returns:
            Document preview text
        """
        document_text = self.context.document_text
        
        # Get document length for logging
        document_length = len(document_text)
        
        # Limit preview length
        preview = document_text[:max_length]
        
        self.logger.info(f"Created document preview ({len(preview)} chars) from {document_length} total chars")
        return preview
    
    def _analyze_framework(self) -> Dict[str, Any]:
        """
        Analyze the assessment framework structure.
        
        Returns:
            Framework analysis results
        """
        framework = self.context.framework
        
        # Extract basic framework info
        framework_id = framework.get("id", "unknown")
        framework_name = framework.get("name", "Unknown Framework")
        
        # Analyze dimensions and criteria
        dimensions = framework.get("dimensions", [])
        dimension_count = len(dimensions)
        
        # Collect detailed dimension and criteria information
        dimensions_info = []
        total_criteria = 0
        
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
                
            criteria = dimension.get("criteria", [])
            criteria_count = len(criteria)
            total_criteria += criteria_count
            
            # Collect criteria details
            criteria_info = []
            for criterion in criteria:
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                criterion_question = criterion.get("question", "")
                scoring_method = criterion.get("scoring_method", "scale_1_5")
                
                criterion_data = {
                    "id": criterion_id,
                    "name": criterion_name,
                    "question": criterion_question,
                    "scoring_method": scoring_method,
                    "scoring_definitions": criterion.get("scoring_definitions", {})
                }
                
                criteria_info.append(criterion_data)
            
            dimensions_info.append({
                "id": dimension_id,
                "name": dimension_name,
                "criteria_count": criteria_count,
                "criteria": criteria_info
            })
        
        # Analyze scoring methods
        scoring_methods = framework.get("scoring_methods", {})
        
        # Create framework analysis
        framework_analysis = {
            "framework_id": framework_id,
            "framework_name": framework_name,
            "dimension_count": dimension_count,
            "total_criteria": total_criteria,
            "scoring_methods": scoring_methods,
            "dimensions": dimensions_info
        }
        
        self.logger.info(
            f"Analyzed framework: {framework_name} with {dimension_count} dimensions, "
            f"{total_criteria} total criteria"
        )
        
        return framework_analysis
    
    async def _analyze_document(self, document_preview: str) -> Dict[str, Any]:
        """
        Analyze document preview to understand content and structure.
        
        Args:
            document_preview: Document preview text
            
        Returns:
            Document analysis results
        """
        self.logger.info("Analyzing document preview")
        
        # Get document properties from context if available
        if hasattr(self.context, "document_properties"):
            document_properties = self.context.document_properties
            
            # If we have comprehensive properties, use them
            if document_properties.get("document_type") != "unknown":
                self.logger.info(f"Using existing document properties: {document_properties}")
                return document_properties
        
        # Create prompt for document analysis
        system_prompt = """You are an expert document analyst tasked with analyzing a document preview to understand its content, structure, and characteristics for efficient processing."""
        
        human_prompt = f"""Analyze the following document preview to identify its characteristics for assessment planning.

DOCUMENT PREVIEW:
{document_preview}

Please analyze this document for:
1. Content type (e.g., meeting transcript, earnings call, technical report, etc.)
2. Structure (paragraphs, sections, dialogue, etc.)
3. Key topics and themes
4. Language characteristics (technical, conversational, formal, etc.)
5. Evidence potential - how likely the document contains assessable content
6. Special processing considerations

Provide your analysis as a structured JSON object."""

        # Call LLM for analysis with structured output
        result = await self._structured_output_call(
            prompt=human_prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "document_type": {"type": "string"},
                    "content_structure": {"type": "string"},
                    "key_topics": {"type": "array", "items": {"type": "string"}},
                    "language_characteristics": {"type": "array", "items": {"type": "string"}},
                    "evidence_potential": {"type": "string"},
                    "special_considerations": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["document_type", "content_structure"]
            },
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        # Record observation for analysis
        self.record_observation("document_analysis", result)
        
        self.logger.info(f"Document analysis complete: type={result.get('document_type')}")
        return result
    
    async def _design_strategy(
        self, 
        document_analysis: Dict[str, Any], 
        framework_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Design assessment strategy optimized for consolidated evidence packets.
        
        Args:
            document_analysis: Document analysis results
            framework_analysis: Framework analysis results
            
        Returns:
            Assessment strategy
        """
        self.logger.info("Designing assessment strategy for consolidated evidence packets")
        
        # 1. Design chunking strategy based on document
        chunking_strategy = self._design_chunking_strategy(document_analysis)
        
        # 2. Get all criteria
        all_criteria = self._get_all_criteria(framework_analysis)
        
        # 3. Generate clear extraction instructions for each criterion
        criteria_with_instructions = await self._generate_extraction_instructions(all_criteria, document_analysis)
        
        # 4. Identify related criteria for combined evaluation
        criteria_groups = []
        if self.use_combined_evaluation:
            criteria_groups = await self._identify_related_criteria(framework_analysis)
        
        # 5. Create extractor configurations (one per criterion)
        extractor_agents = []
        for criterion in criteria_with_instructions:
            extractor_config = {
                "agent_type": f"extractor_{criterion['criterion_id']}",
                "configuration": {
                    "criteria_ids": [criterion["criterion_id"]],
                    "dimension_ids": [criterion["dimension_id"]]
                },
                "instructions": criterion["extraction_instructions"]
            }
            extractor_agents.append(extractor_config)
        
        # 6. Create evaluator configuration
        evaluator_config = {
            "agent_type": "evaluator",
            "configuration": {
                "evaluation_type": "consolidated_packet",
                "use_combined_evaluation": self.use_combined_evaluation,
                "criteria_groups": criteria_groups if criteria_groups else [],
                "confidence_threshold": 0.4,
                "infer_missing": True,
                "output_format": "scorecard"
            },
            "instructions": self._create_evaluator_instructions(framework_analysis)
        }
        
        # 7. Create reporter configuration
        reporter_config = {
            "agent_type": "reporter",
            "configuration": {
                "report_type": "scorecard",
                "include_evidence": True,
                "include_confidence": True,
                "include_assessment_types": True,
                "export_formats": ["json", "html", "markdown"]
            },
            "instructions": """Create a structured scorecard from the evaluations.
Include evidence summaries and clearly distinguish between direct and inferred assessments."""
        }
        
        # 8. Create processing sequence
        extractor_steps = ["extractor"] * len(extractor_agents)
        processing_sequence = extractor_steps + ["evaluator", "reporter"]
        
        # 9. Build the complete strategy
        strategy = {
            "strategy_type": "consolidated_evidence_packets",
            "chunking_strategy": chunking_strategy,
            "agents": extractor_agents + [evaluator_config, reporter_config],
            "processing_sequence": processing_sequence,
            "document_analysis": document_analysis,
            "criteria_groups": criteria_groups,
            "rationale": (
                f"Strategy optimized for consolidated evidence packets with two-pass extraction. "
                f"Each criterion gets one comprehensive evidence packet from all document chunks."
            ),
            "approach_description": (
                "This strategy first extracts evidence from each chunk for every criterion, "
                "then consolidates findings into one packet per criterion. The evaluator can "
                f"{'perform combined evaluation for related criteria' if self.use_combined_evaluation else 'evaluate each criterion individually'} "
                "to ensure consistency and completeness."
            )
        }
        
        # Report on strategy created
        self.logger.info(
            f"Created consolidated evidence packet strategy with {len(extractor_agents)} extractors "
            f"for {len(all_criteria)} criteria"
        )
        
        return strategy
    
    def _design_chunking_strategy(self, document_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design optimal chunking strategy based on document.
        
        For consolidated evidence packets, we can use larger chunks with more overlap.
        
        Args:
            document_analysis: Document analysis results
            
        Returns:
            Chunking strategy
        """
        # Get document type and structure
        document_type = document_analysis.get("document_type", "").lower()
        structure = document_analysis.get("content_structure", "").lower()
        document_text = self.context.document_text
        document_size = len(document_text)
        
        # For earnings calls and transcripts, use larger chunks with speaker context
        if "transcript" in document_type or "earnings call" in document_type or "dialogue" in structure:
            return {
                "method": "paragraph",
                "size": 50,  # Large paragraph chunks
                "overlap": 5,  # With overlap to maintain context
                "rationale": "Using paragraph chunking to preserve speaker context in transcript/dialogue"
            }
        
        # For small documents, use one large chunk
        elif document_size < 30000:
            return {
                "method": "fixed_size",
                "size": document_size,
                "overlap": 0,
                "rationale": "Small document processed as a single chunk"
            }
            
        # For medium documents, use substantial chunks with significant overlap
        elif document_size < 100000:
            chunk_size = min(15000, max(8000, document_size // 3))
            return {
                "method": "fixed_size",
                "size": chunk_size,
                "overlap": chunk_size // 4,  # 25% overlap
                "rationale": f"Medium document chunked into larger segments with overlap for context preservation"
            }
            
        # For large documents, use semantic chunking
        else:
            return {
                "method": "semantic",
                "rationale": "Large document using semantic chunking to maintain contextual meaning"
            }
    
    def _get_all_criteria(self, framework_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get list of all criteria with dimension info.
        
        Args:
            framework_analysis: Framework analysis results
            
        Returns:
            List of all criteria
        """
        all_criteria = []
        
        for dimension in framework_analysis["dimensions"]:
            for criterion in dimension["criteria"]:
                all_criteria.append({
                    "dimension_id": dimension["id"],
                    "dimension_name": dimension["name"],
                    "criterion_id": criterion["id"],
                    "criterion_name": criterion["name"],
                    "criterion_question": criterion["question"],
                    "scoring_method": criterion.get("scoring_method", "scale_1_5"),
                    "scoring_definitions": criterion.get("scoring_definitions", {})
                })
        
        return all_criteria

    async def _generate_extraction_instructions(
        self, 
        all_criteria: List[Dict[str, Any]],
        document_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate clear extraction instructions for consolidated evidence packets.
        
        Args:
            all_criteria: List of all criteria
            document_analysis: Document analysis results
            
        Returns:
            Criteria with added extraction instructions
        """
        self.logger.info(f"Generating evidence extraction instructions for {len(all_criteria)} criteria")
        
        # Process criteria in batches to avoid token limits
        max_batch_size = 5
        batches = [all_criteria[i:i+max_batch_size] for i in range(0, len(all_criteria), max_batch_size)]
        
        criteria_with_instructions = []
        
        # Document context for prompts
        document_type = document_analysis.get("document_type", "document")
        document_structure = document_analysis.get("content_structure", "")
        
        # Entity information from context
        entity_info = self.context.document_properties.get("primary_entity", {})
        entity_name = entity_info.get("name", "the entity")
        entity_type = entity_info.get("type", "organization")
        
        for batch_idx, criteria_batch in enumerate(batches):
            self.logger.info(f"Processing instructions batch {batch_idx+1}/{len(batches)}")
            
            # Create batch to send to LLM
            criteria_info = []
            for criterion in criteria_batch:
                # Format scoring definitions for reference
                scoring_defs = criterion.get("scoring_definitions", {})
                formatted_scoring = []
                
                for score, definition in scoring_defs.items():
                    formatted_scoring.append(f"Score {score}: {definition}")
                
                criteria_info.append({
                    "criterion_id": criterion["criterion_id"],
                    "criterion_name": criterion["criterion_name"],
                    "criterion_question": criterion["criterion_question"],
                    "dimension_name": criterion["dimension_name"],
                    "scoring_summary": "\n".join(formatted_scoring)
                })
            
            # Create system prompt for generating instructions
            system_prompt = f"""You are an expert helping create clear guidance for extracting evidence about assessment criteria from {document_type} documents."""
            
            # Create document context string
            document_context = f"""DOCUMENT CONTEXT:
- Document Type: {document_type}
- Document Structure: {document_structure}
- Entity Being Assessed: {entity_name} (Type: {entity_type})"""
            
            # Create human prompt for simple, effective extraction instructions
            human_prompt = f"""Create clear, focused extraction instructions for each criterion.

{document_context}

CRITERIA TO PROCESS:
{json.dumps(criteria_info, indent=2)}

For each criterion, create simple but effective instructions that help extract evidence from a document. Focus on:

1. WHAT TO LOOK FOR: Key phrases, terminology, and concepts related to this criterion
2. TYPES OF EVIDENCE: Specific statements, metrics, or indicators that would support assessment
3. HELPFUL CONTEXT: Background information that helps interpret evidence for this criterion

Make the instructions conversational and practical - as if you're guiding someone to find relevant evidence.
The instructions will be used to create comprehensive evidence packets that include direct quotes, metrics, and relevance analysis.
"""

            # Call LLM for instructions
            result = await self._structured_output_call(
                prompt=human_prompt,
                output_schema={
                    "type": "object",
                    "properties": {
                        "instructions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "criterion_id": {"type": "string"},
                                    "extraction_instructions": {"type": "string"}
                                },
                                "required": ["criterion_id", "extraction_instructions"]
                            }
                        }
                    },
                    "required": ["instructions"]
                },
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            # Process results
            if "instructions" in result:
                for instructions in result["instructions"]:
                    criterion_id = instructions["criterion_id"]
                    
                    # Find the corresponding criterion in the batch
                    for criterion in criteria_batch:
                        if criterion["criterion_id"] == criterion_id:
                            # Add extraction instructions to criterion
                            criterion["extraction_instructions"] = instructions["extraction_instructions"]
                            
                            # Add to the result list
                            criteria_with_instructions.append(criterion)
                            break
            
        self.logger.info(f"Generated extraction instructions for {len(criteria_with_instructions)} criteria")
        
        return criteria_with_instructions
    
    async def _identify_related_criteria(self, framework_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify related criteria that should be evaluated together for consistency.
        
        Args:
            framework_analysis: Framework analysis results
            
        Returns:
            List of criteria groups
        """
        if not self.use_combined_evaluation:
            return []
            
        self.logger.info("Identifying related criteria for combined evaluation")
        
        # Get all dimensions with multiple criteria
        groups = []
        
        for dimension in framework_analysis["dimensions"]:
            dimension_id = dimension["id"]
            dimension_name = dimension["name"]
            criteria = dimension["criteria"]
            
            # Skip dimensions with just one criterion
            if len(criteria) <= 1:
                continue
                
            # For simplicity in POC, just group by dimension with a maximum size
            current_group = []
            
            for criterion in criteria:
                current_group.append({
                    "dimension_id": dimension_id,
                    "criterion_id": criterion["id"],
                    "criterion_name": criterion["name"]
                })
                
                # When we reach max size, add the group and start a new one
                if len(current_group) >= self.max_criteria_per_group:
                    groups.append({
                        "dimension_id": dimension_id,
                        "dimension_name": dimension_name,
                        "criteria": current_group.copy(),
                        "rationale": f"Grouped for consistent evaluation within {dimension_name}"
                    })
                    current_group = []
            
            # Add any remaining criteria as a group
            if current_group:
                groups.append({
                    "dimension_id": dimension_id,
                    "dimension_name": dimension_name,
                    "criteria": current_group,
                    "rationale": f"Grouped for consistent evaluation within {dimension_name}"
                })
        
        self.logger.info(f"Identified {len(groups)} criteria groups for combined evaluation")
        return groups
    
    def _create_evaluator_instructions(self, framework_analysis: Dict[str, Any]) -> str:
        """
        Create clear instructions for the evaluator.
        
        Args:
            framework_analysis: Framework analysis results
            
        Returns:
            Evaluator instructions
        """
        # Create base instructions
        instructions = """Use the consolidated evidence packets to assess each criterion.

Each evidence packet contains:
- DIRECT QUOTES: Exact statements from the document
- KEY METRICS: Numerical data and measurements
- RELEVANCE ANALYSIS: Explanation of how the evidence relates to the criterion
- ASSESSMENT IMPLICATION: What the evidence suggests about rating

When evaluating criteria:

1. EVIDENCE QUALITY
   - Prioritize direct quotes and specific metrics
   - Consider both the quantity and quality of evidence
   - Note when evidence is particularly strong or limited

2. ASSESSMENT APPROACH
   - Make DIRECT assessments when evidence clearly addresses the criterion
   - Make INFERRED assessments when evidence is limited but allows for reasonable inference
   - Mark as INSUFFICIENT EVIDENCE when no meaningful assessment is possible

3. RATIONALE CLARITY
   - For direct assessments: Reference specific quotes and metrics
   - For inferred assessments: Mark with [INFERRED] and explain your reasoning
   - Be transparent about confidence levels

4. CONSISTENCY
   - Maintain consistent standards across related criteria
   - Compare assessments within dimensions for calibration"""

        # Add framework-specific guidance if available
        framework_name = framework_analysis.get("framework_name", "")
        if framework_name:
            instructions += f"\n\nThis evaluation is for the {framework_name} framework. "
            
            # Add framework-specific tips based on name
            if "financial" in framework_name.lower():
                instructions += """When evaluating financial criteria:
- Look for specific financial metrics and KPIs
- Pay attention to year-over-year comparisons
- Consider both absolute numbers and trends
- Note how executives contextualize financial results"""
            elif "earnings call" in framework_name.lower():
                instructions += """When evaluating an earnings call:
- Consider both prepared remarks and Q&A responses
- Note differences between executive statements
- Pay attention to how questions are answered or avoided
- Consider what topics executives emphasize vs. downplay"""
                
        return instructions
    
    def _define_output_schema(self, framework_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Define output schema based on framework structure.
        
        Args:
            framework_analysis: Framework analysis results
            
        Returns:
            Output schema definition
        """
        self.logger.info("Defining output schema based on framework structure")
        
        # Get framework info
        framework_name = framework_analysis.get("framework_name", "Assessment Framework")
        dimensions = framework_analysis.get("dimensions", [])
        
        # Define base schema
        schema = {
            "title": f"{framework_name} Assessment",
            "type": "object",
            "properties": {
                "overall_assessment": {
                    "type": "object",
                    "properties": {
                        "average_rating": {"type": "number"},
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
                    "required": ["average_rating", "executive_summary"]
                },
                "dimensions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "average_rating": {"type": "number"},
                            "summary": {"type": "string"},
                            "criteria": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "name": {"type": "string"},
                                        "rating": {"type": "number"},
                                        "rationale": {"type": "string"},
                                        "confidence": {"type": "number"},
                                        "strengths": {"type": "array", "items": {"type": "string"}},
                                        "weaknesses": {"type": "array", "items": {"type": "string"}},
                                        "evidence_summary": {"type": "string"},
                                        "assessment_type": {"type": "string", "enum": ["direct", "inferred", "insufficient_evidence"]}
                                    },
                                    "required": ["id", "name", "rating", "rationale", "assessment_type"]
                                }
                            }
                        },
                        "required": ["id", "name", "criteria"]
                    }
                }
            },
            "required": ["overall_assessment", "dimensions"]
        }
        
        return schema
    
    def _create_fallback_strategy(self) -> Dict[str, Any]:
        """
        Create a fallback strategy if strategy generation fails.
        
        Returns:
            Fallback assessment strategy
        """
        self.logger.info("Creating fallback strategy for consolidated evidence packets")
        
        # Get framework dimensions and criteria
        dimensions = self.context.framework.get("dimensions", [])
        
        # Create one extractor per criterion
        extractor_agents = []
        
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            
            if not dimension_id:
                continue
                
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                
                if not criterion_id:
                    continue
                
                # Simple instructions
                instructions = f"""Create a comprehensive evidence packet for {criterion_name}.

Look for:
1. Direct quotes from executives or statements in the document
2. Metrics, figures, and quantitative data
3. Contextual information relevant to understanding this criterion
4. Any information that helps assess this criterion

Organize your findings into a structured evidence packet with sections for quotes, metrics, and context.
"""
                
                # Create extractor configuration
                extractor_config = {
                    "agent_type": f"extractor_{criterion_id}",
                    "configuration": {
                        "criteria_ids": [criterion_id],
                        "dimension_ids": [dimension_id]
                    },
                    "instructions": instructions
                }
                
                extractor_agents.append(extractor_config)
        
        # Create evaluator
        evaluator_config = {
            "agent_type": "evaluator",
            "configuration": {
                "evaluation_type": "consolidated_packet",
                "use_combined_evaluation": False,
                "confidence_threshold": 0.4,
                "infer_missing": True,
                "output_format": "scorecard"
            },
            "instructions": """Evaluate each criterion based on its consolidated evidence packet.
Use direct assessment when clear evidence is available.
Use inferred assessment when evidence is limited but allows for reasonable inference.
Mark as insufficient evidence when no relevant evidence is available."""
        }
        
        # Create reporter
        reporter_config = {
            "agent_type": "reporter",
            "configuration": {
                "report_type": "scorecard",
                "include_evidence": True,
                "include_confidence": True,
                "include_assessment_types": True,
                "export_formats": ["json"]
            },
            "instructions": """Create a structured scorecard from the evaluations.
Clearly distinguish between direct and inferred assessments."""
        }
        
        # Combine all agents
        all_agents = extractor_agents + [evaluator_config, reporter_config]
        
        # Create processing sequence
        extractor_steps = ["extractor"] * len(extractor_agents)
        processing_sequence = extractor_steps + ["evaluator", "reporter"]
        
        # Create chunking strategy
        chunking_strategy = {
            "method": "fixed_size",
            "size": 12000,
            "overlap": 1000,
            "rationale": "Default chunking strategy for fallback"
        }
        
        # Create fallback strategy
        fallback_strategy = {
            "strategy_type": "fallback_consolidated_evidence_packets",
            "chunking_strategy": chunking_strategy,
            "agents": all_agents,
            "processing_sequence": processing_sequence,
            "rationale": "Fallback strategy using consolidated evidence packets with one extractor per criterion."
        }
        
        self.logger.info(f"Created fallback strategy with {len(extractor_agents)} extractors")
        
        return fallback_strategy