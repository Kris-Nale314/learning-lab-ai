"""
Enhanced Meta Planner Agent - Designs assessment strategies and defines output schema

This module provides the MetaPlannerAgent class, which analyzes documents and 
frameworks to design custom processing strategies for assessment, including
parallel extraction capabilities and output schema definition.
"""

import json
import time
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class MetaPlannerAgent(BaseAgent):
    """
    Designs custom assessment strategies and output schemas based on document and framework analysis.
    
    The Meta Planner is responsible for:
    1. Analyzing document content and structure
    2. Evaluating framework dimensions and criteria
    3. Designing an optimal processing strategy
    4. Configuring agent deployment and sequencing
    5. Creating custom instructions for each agent
    6. Grouping criteria for parallel extraction
    7. Defining the output schema for structured assessment results
    
    This is the strategic "brain" of the assessment system.
    """
    
    DEFAULT_MAX_GROUP_SIZE = 3
    DEFAULT_TOKEN_THRESHOLD = 10000
    
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
        
        # Extract configuration options
        self.max_group_size = self.options.get("max_group_size", self.DEFAULT_MAX_GROUP_SIZE)
        self.token_threshold = self.options.get("token_threshold", self.DEFAULT_TOKEN_THRESHOLD)
        self.one_criterion_per_extractor = self.options.get("one_criterion_per_extractor", True)
        
        self.logger.info(f"{name} initialized with max_group_size={self.max_group_size}")
        
    async def process(self, document_preview_length: int = 5000) -> Dict[str, Any]:
        """
        Analyze document and framework to design an assessment strategy.
        
        Args:
            document_preview_length: Length of document preview to analyze
            
        Returns:
            Assessment strategy
        """
        self.logger.info("Starting assessment strategy planning")
        self.start_timer()
        
        try:
            # 1. Extract document preview
            document_preview = self._get_document_preview(document_preview_length)
            
            # 2. Analyze document preview
            document_analysis = await self._analyze_document(document_preview)
            
            # 3. Analyze framework
            framework_analysis = self._analyze_framework()
            
            # 4. Design assessment strategy
            assessment_strategy = await self._design_strategy(document_analysis, framework_analysis)
            
            # 5. Define output schema
            output_schema = self._define_output_schema(framework_analysis)
            assessment_strategy["output_schema"] = output_schema
            
            # 6. Store strategy in context
            self.context.set_planning_data(assessment_strategy)
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Assessment strategy planning completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("strategy_created", {
                "strategy_type": assessment_strategy.get("strategy_type"),
                "agent_count": len(assessment_strategy.get("agents", [])),
                "time_taken": elapsed_time,
                "output_schema_defined": True
            })
            
            return assessment_strategy
            
        except Exception as e:
            self.stop_timer()
            self.logger.error(f"Error during assessment strategy planning: {str(e)}", exc_info=True)
            self.add_warning(f"Failed to create assessment strategy: {str(e)}")
            raise
    
    def _get_document_preview(self, max_length: int = 5000) -> str:
        """
        Get a preview of the document for analysis.
        
        Args:
            max_length: Maximum length of preview
            
        Returns:
            Document preview text
        """
        document_text = self.context.document_text
        preview = document_text[:max_length]
        
        # Record observation
        self.record_observation("document_preview", {
            "preview_length": len(preview),
            "document_length": len(document_text),
            "preview_ratio": len(preview) / max(1, len(document_text))
        })
        
        # Track tokens
        preview_tokens = self.estimate_tokens(preview)
        self.track_tokens(preview_tokens, "prompt", "document_preview")
        
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
        
        criteria_counts = {}
        total_criteria = 0
        
        # Collect detailed dimension and criteria information
        dimensions_info = []
        
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            if not dimension_id:
                continue
                
            criteria = dimension.get("criteria", [])
            criteria_count = len(criteria)
            
            criteria_counts[dimension_id] = criteria_count
            total_criteria += criteria_count
            
            # Collect criteria details
            criteria_info = []
            for criterion in criteria:
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                scoring_method = criterion.get("scoring_method", "scale_1_5")
                
                criteria_info.append({
                    "id": criterion_id,
                    "name": criterion_name,
                    "scoring_method": scoring_method,
                    "scoring_definitions": criterion.get("scoring_definitions", {})
                })
            
            dimensions_info.append({
                "id": dimension_id,
                "name": dimension_name,
                "criteria_count": criteria_count,
                "criteria": criteria_info
            })
        
        # Get rating scale if available
        rating_scale = framework.get("rating_scale", {})
        rating_levels = rating_scale.get("levels", [])
        
        # Get scoring methods
        scoring_methods = framework.get("scoring_methods", {})
        
        # Create framework analysis
        framework_analysis = {
            "framework_id": framework_id,
            "framework_name": framework_name,
            "dimension_count": dimension_count,
            "total_criteria": total_criteria,
            "criteria_by_dimension": criteria_counts,
            "has_rating_scale": bool(rating_levels),
            "rating_levels_count": len(rating_levels),
            "scoring_methods": scoring_methods,
            "dimensions": dimensions_info
        }
        
        # Record observation
        self.record_observation("framework_analysis", framework_analysis)
        
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
        
        # Create prompt for document analysis
        system_prompt = """You are an expert document analyst tasked with analyzing a document preview to understand its content, structure, and characteristics. Your analysis will be used to design an optimal assessment strategy."""
        
        human_prompt = f"""Analyze the following document preview and provide a structured assessment of its characteristics.

DOCUMENT PREVIEW:
{document_preview}

Please provide your analysis in the following format:
1. Document type (e.g., meeting transcript, technical report, etc.)
2. Content structure (paragraphs, sections, dialogue, etc.)
3. Key topics identified
4. Language characteristics (technical, conversational, formal, etc.)
5. Special considerations for assessment

Your analysis should be concise but informative, focusing on aspects that would be relevant for designing an assessment strategy."""

        # Call LLM for analysis
        response_text, _ = await self._safe_llm_call(
            "generate_completion",
            prompt=human_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        # Parse analysis
        document_analysis = self._parse_document_analysis(response_text)
        
        # Record observation
        self.record_observation("document_analysis", document_analysis)
        
        return document_analysis
        
    def _parse_document_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """
        Parse document analysis text into structured format.
        
        Args:
            analysis_text: Analysis text from LLM
            
        Returns:
            Structured document analysis
        """
        # Default structure
        document_analysis = {
            "document_type": "unknown",
            "content_structure": "unknown",
            "key_topics": [],
            "language_characteristics": [],
            "special_considerations": []
        }
        
        if not analysis_text:
            self.add_warning("Received empty document analysis text")
            return document_analysis
        
        analysis_text = analysis_text.lower()  # Convert to lowercase for case-insensitive matching
        
        # Extract document type
        try:
            if "document type" in analysis_text:
                pattern = r"(?:document type[:\s]+)(.*?)(?:\n|$)"
                match = re.search(pattern, analysis_text, re.IGNORECASE | re.DOTALL)
                if match:
                    document_analysis["document_type"] = match.group(1).strip()
        except Exception as e:
            self.logger.warning(f"Error extracting document type: {str(e)}")
        
        # Extract content structure
        try:
            if "content structure" in analysis_text:
                pattern = r"(?:content structure[:\s]+)(.*?)(?:\n|$)"
                match = re.search(pattern, analysis_text, re.IGNORECASE | re.DOTALL)
                if match:
                    document_analysis["content_structure"] = match.group(1).strip()
        except Exception as e:
            self.logger.warning(f"Error extracting content structure: {str(e)}")
        
        # Extract key topics
        try:
            if "key topics" in analysis_text:
                topics = []
                # Find the section starting with "key topics"
                key_topics_match = re.search(r"key topics.*?(?:\n|$)(.*?)(?:language characteristics|special considerations|$)", 
                                            analysis_text, re.IGNORECASE | re.DOTALL)
                if key_topics_match:
                    topics_section = key_topics_match.group(1).strip()
                    # Extract bullet points or numbered items
                    for line in topics_section.split('\n'):
                        line = line.strip()
                        if line and (line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line)):
                            topic = re.sub(r'^[-*\d.]+\s*', '', line).strip()
                            if topic:
                                topics.append(topic)
                document_analysis["key_topics"] = topics
        except Exception as e:
            self.logger.warning(f"Error extracting key topics: {str(e)}")
        
        # Extract language characteristics
        try:
            if "language characteristics" in analysis_text:
                characteristics = []
                lang_match = re.search(r"language characteristics.*?(?:\n|$)(.*?)(?:special considerations|$)", 
                                    analysis_text, re.IGNORECASE | re.DOTALL)
                if lang_match:
                    lang_section = lang_match.group(1).strip()
                    for line in lang_section.split('\n'):
                        line = line.strip()
                        if line and (line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line)):
                            characteristic = re.sub(r'^[-*\d.]+\s*', '', line).strip()
                            if characteristic:
                                characteristics.append(characteristic)
                document_analysis["language_characteristics"] = characteristics
        except Exception as e:
            self.logger.warning(f"Error extracting language characteristics: {str(e)}")
        
        # Extract special considerations
        try:
            if "special considerations" in analysis_text:
                considerations = []
                special_match = re.search(r"special considerations.*?(?:\n|$)(.*?)(?:$)", 
                                        analysis_text, re.IGNORECASE | re.DOTALL)
                if special_match:
                    special_section = special_match.group(1).strip()
                    for line in special_section.split('\n'):
                        line = line.strip()
                        if line and (line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line)):
                            consideration = re.sub(r'^[-*\d.]+\s*', '', line).strip()
                            if consideration:
                                considerations.append(consideration)
                document_analysis["special_considerations"] = considerations
        except Exception as e:
            self.logger.warning(f"Error extracting special considerations: {str(e)}")
        
        # If we failed to extract anything, try a more general approach
        if (not document_analysis["document_type"] or 
            document_analysis["document_type"] == "unknown" or
            not document_analysis["key_topics"]):
            
            self.logger.warning("Standard parsing failed, attempting fallback extraction")
            
            # Fallback to more general extraction
            try:
                # Look for patterns that might indicate document type
                doc_type_patterns = [
                    r"(?:this (?:is|appears to be)(?: a)?) ([\w\s]+document)",
                    r"(?:this (?:is|appears to be)(?: a)?) ([\w\s]+report)",
                    r"(?:this (?:is|appears to be)(?: a)?) ([\w\s]+text)",
                ]
                
                for pattern in doc_type_patterns:
                    match = re.search(pattern, analysis_text, re.IGNORECASE)
                    if match and document_analysis["document_type"] == "unknown":
                        document_analysis["document_type"] = match.group(1).strip()
                        break
                
                # Extract topics by looking for lists or key phrases
                if not document_analysis["key_topics"]:
                    # Extract any bullet points or numbered lists
                    list_items = re.findall(r'(?:^|\n)\s*[-*•]+(.*?)(?:\n|$)', analysis_text)
                    if list_items:
                        document_analysis["key_topics"] = [item.strip() for item in list_items if item.strip()]
            except Exception as e:
                self.logger.warning(f"Fallback extraction also failed: {str(e)}")
        
        # Ensure we have at least something in key fields
        if not document_analysis["document_type"] or document_analysis["document_type"] == "unknown":
            document_analysis["document_type"] = "text document"
        
        if not document_analysis["key_topics"]:
            # Extract potential topics from the first few sentences
            sentences = re.split(r'[.!?]+', analysis_text)
            if len(sentences) > 2:
                document_analysis["key_topics"] = ["General content analysis"]
        
        self.logger.info(f"Document analysis parsing complete. Type: {document_analysis['document_type']}")
        return document_analysis
    
    async def _design_strategy(
        self, 
        document_analysis: Dict[str, Any], 
        framework_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Design assessment strategy based on document and framework analysis.
        
        Args:
            document_analysis: Document analysis results
            framework_analysis: Framework analysis results
            
        Returns:
            Assessment strategy
        """
        self.logger.info("Designing assessment strategy")
        
        # 1. Analyze document size and complexity
        document_size = len(self.context.document_text)
        document_tokens = self.estimate_tokens(self.context.document_text)
        document_complexity = self._estimate_complexity(document_analysis)
        
        # 2. Determine optimal chunking strategy
        chunking_strategy = self._design_chunking_strategy(document_size, document_analysis)
        
        # 3. Group criteria for extraction
        if self.one_criterion_per_extractor:
            # Create a group for each criterion (one criterion per extractor)
            criteria_groups = self._group_criteria_one_per_extractor(framework_analysis)
        else:
            # Group criteria based on document size and complexity
            criteria_groups = self._group_criteria(document_size, document_complexity)
        
        # 4. Generate strategy with parallel extraction
        strategy = await self._generate_parallel_strategy(
            document_analysis, 
            framework_analysis, 
            criteria_groups,
            chunking_strategy
        )
        
        # 5. Record strategy design observation
        self.record_observation("strategy_design", {
            "strategy_type": strategy.get("strategy_type"),
            "chunking_method": strategy.get("chunking_strategy", {}).get("method"),
            "agent_count": len(strategy.get("agents", [])),
            "extraction_groups": len(criteria_groups)
        })
        
        return strategy
    
    def _estimate_complexity(self, document_analysis: Dict[str, Any]) -> str:
        """
        Estimate document complexity based on analysis.
        
        Args:
            document_analysis: Document analysis results
            
        Returns:
            Complexity level ("low", "medium", "high")
        """
        # Check language characteristics
        language_chars = document_analysis.get("language_characteristics", [])
        technical_terms = ["technical", "specialized", "jargon", "complex"]
        technical_count = sum(1 for char in language_chars if any(term in char.lower() for term in technical_terms))
        
        # Check structure
        structure = document_analysis.get("content_structure", "").lower()
        structured_terms = ["section", "heading", "structured", "organized"]
        is_structured = any(term in structure for term in structured_terms)
        
        # Check special considerations
        special = document_analysis.get("special_considerations", [])
        complex_terms = ["complex", "difficult", "challenging", "nuanced"]
        complexity_mentions = sum(1 for s in special if any(term in s.lower() for term in complex_terms))
        
        # Determine complexity
        if technical_count >= 2 or complexity_mentions >= 2:
            return "high"
        elif technical_count >= 1 or is_structured or complexity_mentions >= 1:
            return "medium"
        else:
            return "low"
    
    def _design_chunking_strategy(
        self, 
        document_size: int, 
        document_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Design optimal chunking strategy based on document.
        
        Args:
            document_size: Document size in characters
            document_analysis: Document analysis results
            
        Returns:
            Chunking strategy
        """
        # Default configuration
        strategy = {
            "method": "fixed_size",
            "size": 8000,
            "overlap": 200,
            "rationale": "Standard fixed-size chunking for general documents"
        }
        
        # Adjust based on document size
        if document_size < 15000:
            # Small document - use a single large chunk
            strategy["method"] = "fixed_size"
            strategy["size"] = document_size
            strategy["overlap"] = 0
            strategy["rationale"] = "Document is small enough to process as a single chunk"
        else:
            # Check document structure
            structure = document_analysis.get("content_structure", "").lower()
            
            if "dialogue" in structure or "transcript" in structure:
                # Dialogue or transcript - use paragraph-based chunking
                strategy["method"] = "paragraph"
                strategy["size"] = 50  # Number of paragraphs per chunk
                strategy["overlap"] = 5
                strategy["rationale"] = "Dialogue-based content with natural paragraph breaks"
            elif "section" in structure or "heading" in structure:
                # Sectioned document - use section-based chunking
                strategy["method"] = "semantic"
                strategy["size"] = 10000
                strategy["overlap"] = 500
                strategy["rationale"] = "Document has clear section structure for semantic chunking"
            else:
                # Default to fixed size with size based on document length
                chunk_size = min(10000, max(4000, document_size // 5))
                strategy["method"] = "fixed_size"
                strategy["size"] = chunk_size
                strategy["overlap"] = chunk_size // 10
                strategy["rationale"] = f"Standard chunking with size optimized for document length ({document_size} chars)"
        
        return strategy
    
    def _group_criteria_one_per_extractor(
        self,
        framework_analysis: Dict[str, Any]
    ) -> List[List[Dict[str, Any]]]:
        """
        Group criteria with one criterion per group for maximum specialization.
        
        Args:
            framework_analysis: Framework analysis results
            
        Returns:
            List of criteria groups (one criterion per group)
        """
        criteria_groups = []
        
        for dimension in framework_analysis.get("dimensions", []):
            dimension_id = dimension.get("id", "")
            dimension_name = dimension.get("name", "")
            
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                criterion_name = criterion.get("name", "")
                
                if not criterion_id:
                    continue
                
                # Create a group with just this one criterion
                criteria_groups.append([{
                    "dimension_id": dimension_id,
                    "dimension_name": dimension_name,
                    "criterion_id": criterion_id,
                    "criterion_name": criterion_name,
                    "scoring_method": criterion.get("scoring_method", "scale_1_5"),
                    "scoring_definitions": criterion.get("scoring_definitions", {})
                }])
        
        self.logger.info(f"Created {len(criteria_groups)} criteria groups (one criterion per extractor)")
        return criteria_groups
    
    def _group_criteria(
        self, 
        document_size: int, 
        document_complexity: str
    ) -> List[List[Dict[str, Any]]]:
        """
        Group criteria for parallel extraction.
        
        Args:
            document_size: Document size in characters
            document_complexity: Document complexity level
            
        Returns:
            List of criteria groups
        """
        framework = self.context.framework
        
        # Collect all criteria with dimension info
        all_criteria = []
        
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
                    
                all_criteria.append({
                    "dimension_id": dimension_id,
                    "dimension_name": dimension_name,
                    "criterion_id": criterion_id,
                    "criterion_name": criterion_name,
                    "criterion_question": criterion.get("question", ""),
                    "scoring_method": criterion.get("scoring_method", "scale_1_5"),
                    "scoring_definitions": criterion.get("scoring_definitions", {})
                })
        
        # Determine grouping strategy based on document size and complexity
        max_group_size = self.max_group_size
        
        if document_size < self.token_threshold:
            # Small document - use one group for all criteria
            return [all_criteria]
        
        # For larger documents, group by dimension first, then split if needed
        dimension_groups = {}
        
        for criterion in all_criteria:
            dimension_id = criterion.get("dimension_id")
            if dimension_id not in dimension_groups:
                dimension_groups[dimension_id] = []
            dimension_groups[dimension_id].append(criterion)
        
        # Create final groups
        criterion_groups = []
        
        for dimension_id, criteria in dimension_groups.items():
            # If dimension has more than max criteria, split it
            if len(criteria) > max_group_size:
                for i in range(0, len(criteria), max_group_size):
                    group = criteria[i:i + max_group_size]
                    criterion_groups.append(group)
            else:
                criterion_groups.append(criteria)
        
        # If we have too many small groups, consolidate
        if document_complexity == "low" and len(criterion_groups) > 5:
            consolidated_groups = []
            current_group = []
            
            for group in criterion_groups:
                if len(current_group) + len(group) <= max_group_size:
                    current_group.extend(group)
                else:
                    if current_group:
                        consolidated_groups.append(current_group)
                    current_group = group
            
            if current_group:
                consolidated_groups.append(current_group)
            
            criterion_groups = consolidated_groups
        
        return criterion_groups
    
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
                                        "evidence_summary": {"type": "string"},
                                        "evidence_count": {"type": "integer"}
                                    },
                                    "required": ["id", "name", "rating", "rationale"]
                                }
                            }
                        },
                        "required": ["id", "name", "criteria"]
                    }
                }
            },
            "required": ["overall_assessment", "dimensions"]
        }
        
        # Define dimension-specific schemas
        dimension_schemas = {}
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            if not dimension_id:
                continue
                
            criteria_schema = {
                "type": "object",
                "properties": {}
            }
            
            # Add each criterion to the schema
            for criterion in dimension.get("criteria", []):
                criterion_id = criterion.get("id", "")
                if not criterion_id:
                    continue
                    
                scoring_method = criterion.get("scoring_method", "scale_1_5")
                
                if scoring_method == "evidence_based":
                    # For evidence-based criteria, store evidence items
                    criteria_schema["properties"][criterion_id] = {
                        "type": "object",
                        "properties": {
                            "rating": {"type": ["number", "null"]},
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "summary": {"type": "string"},
                            "confidence": {"type": "number"}
                        }
                    }
                else:
                    # For numeric scale criteria
                    criteria_schema["properties"][criterion_id] = {
                        "type": "object",
                        "properties": {
                            "rating": {"type": ["number", "null"]},
                            "rationale": {"type": "string"},
                            "evidence_summary": {"type": "string"},
                            "confidence": {"type": "number"}
                        }
                    }
            
            dimension_schemas[dimension_id] = criteria_schema
        
        # Add dimension-specific schemas
        schema["dimension_schemas"] = dimension_schemas
        
        # Add evaluator output schema
        schema["evaluator_output"] = {
            "type": "object",
            "properties": {
                "dimensions": {
                    "type": "object",
                    "properties": {}
                },
                "overall": {
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
                        }
                    }
                }
            }
        }
        
        # Add dimension properties to evaluator schema
        for dimension_id in dimension_schemas.keys():
            schema["evaluator_output"]["properties"]["dimensions"]["properties"][dimension_id] = {
                "type": "object",
                "properties": {
                    "criteria": {"type": "object"},
                    "summary": {
                        "type": "object",
                        "properties": {
                            "average_rating": {"type": "number"},
                            "strengths": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "weaknesses": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "summary": {"type": "string"}
                        }
                    }
                }
            }
        
        # Add reporter output schema (scorecard)
        schema["reporter_output"] = {
            "type": "object",
            "properties": {
                "scorecard": {
                    "type": "object",
                    "properties": {
                        "overall_rating": {"type": "number"},
                        "executive_summary": {"type": "string"},
                        "key_strengths": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "key_improvements": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "dimensions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "average_rating": {"type": "number"},
                                    "criteria": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string"},
                                                "name": {"type": "string"},
                                                "rating": {"type": "number"},
                                                "rationale": {"type": "string"},
                                                "evidence_summary": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        return schema
    
    async def _generate_parallel_strategy(
        self,
        document_analysis: Dict[str, Any],
        framework_analysis: Dict[str, Any],
        criteria_groups: List[List[Dict[str, Any]]],
        chunking_strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate assessment strategy with parallel extraction.
        
        Args:
            document_analysis: Document analysis results
            framework_analysis: Framework analysis results
            criteria_groups: Grouped criteria for parallel extraction
            chunking_strategy: Chunking strategy
            
        Returns:
            Complete assessment strategy
        """
        # Create system prompt for strategy generation
        system_prompt = """You are an expert strategy designer for AI assessment systems. 
        Your task is to design an optimal assessment strategy based on document and framework analysis. 
        The strategy should specify which agents to deploy, how they should be configured, and how they should be sequenced."""
        
        # Get user options if available
        user_options = self.context.options.get("user_options", {})
        user_preferences_text = ""
        
        if user_options:
            user_preferences_text = "USER PREFERENCES:\n"
            for key, value in user_options.items():
                if value is not None:
                    user_preferences_text += f"- {key}: {value}\n"
        
        # Collect group information for the prompt
        groups_text = ""
        for i, group in enumerate(criteria_groups):
            groups_text += f"Group {i+1}:\n"
            for criterion in group:
                groups_text += f"- {criterion['dimension_name']} / {criterion['criterion_name']}\n"
            groups_text += "\n"
        
        # Create human prompt for strategy design
        json_schema = r'''```json
{
  "strategy_type": "string",
  "chunking_strategy": {
    "method": "string",
    "size": "number",
    "overlap": "number",
    "rationale": "string"
  },
  "agents": [
    {
      "agent_type": "string",
      "configuration": {},
      "instructions": "string",
      "inputs": ["string"],
      "outputs": ["string"]
    }
  ],
  "processing_sequence": ["string"],
  "token_allocation": {
    "total_estimated": "number",
    "by_agent": {}
  },
  "rationale": "string"
}
```'''
        
        human_prompt = f"""Design an optimal assessment strategy based on the following document and framework analysis.

DOCUMENT ANALYSIS:
{json.dumps(document_analysis, indent=2)}

FRAMEWORK ANALYSIS:
{json.dumps(framework_analysis, indent=2)}

CRITERIA GROUPS FOR PARALLEL EXTRACTION:
{groups_text}

RECOMMENDED CHUNKING STRATEGY:
{json.dumps(chunking_strategy, indent=2)}

{user_preferences_text}

Your strategy should include:

1. Chunking strategy (use the recommended one unless you have a strong reason to modify it)
2. Agent deployment plan with one extractor per criteria group and specific instructions for each
3. Processing sequence (order of operations)
4. Custom instructions for each agent based on their specific criteria
5. Reasoning for your strategy choices

Available agents:
- Extractor: Extracts content related to specific criteria (one extractor per criteria group)
- Evaluator: Evaluates criteria based on all extracted evidence
- Reporter: Generates structured assessment reports

Each extractor should focus deeply on its assigned criteria to find ALL potential evidence.
The evaluator should produce structured ratings by analyzing the collective evidence for each criterion.
The reporter should format the structured evaluations into a scorecard without duplicating the evaluator's work.

Please provide your strategy as a structured JSON object with the following schema:

{json_schema}"""
        
        # Call LLM for strategy design
        try:
            strategy_json, _ = await self._safe_llm_call(
                "generate_and_parse_json",
                prompt=human_prompt,
                system_prompt=system_prompt,
                description="assessment strategy",
                temperature=0.4,
                max_tokens=3000
            )
            
            # Ensure the strategy has all required sections
            strategy = self._validate_strategy(strategy_json)
            
            # Ensure agent naming is consistent
            strategy = self._normalize_agent_names(strategy)
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"Error generating parallel assessment strategy: {str(e)}", exc_info=True)
            
            # Create fallback strategy
            fallback_strategy = self._create_fallback_strategy(
                document_analysis, 
                framework_analysis, 
                criteria_groups,
                chunking_strategy
            )
            
            self.add_warning(f"Used fallback strategy due to error: {str(e)}")
            
            return fallback_strategy
    
    def _normalize_agent_names(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure agent names are consistent throughout strategy.
        
        Args:
            strategy: Assessment strategy
            
        Returns:
            Normalized strategy
        """
        # Create a copy to avoid modifying the original
        normalized = strategy.copy()
        
        # Normalize agent types in agents list
        if "agents" in normalized:
            for agent in normalized["agents"]:
                if "agent_type" in agent:
                    agent_type = agent["agent_type"].lower()
                    
                    # Standardize names
                    if agent_type in ["extractor", "extractagent", "extract"]:
                        agent["agent_type"] = "extractor"
                    elif agent_type in ["evaluator", "evaluateagent", "evaluate"]:
                        agent["agent_type"] = "evaluator"
                    elif agent_type in ["reporter", "reportagent", "report"]:
                        agent["agent_type"] = "reporter"
        
        # Normalize processing sequence
        if "processing_sequence" in normalized:
            normalized_sequence = []
            for agent_type in normalized["processing_sequence"]:
                agent_type = agent_type.lower()
                
                # Standardize names
                if agent_type in ["extractor", "extractagent", "extract"]:
                    normalized_sequence.append("extractor")
                elif agent_type in ["evaluator", "evaluateagent", "evaluate"]:
                    normalized_sequence.append("evaluator")
                elif agent_type in ["reporter", "reportagent", "report"]:
                    normalized_sequence.append("reporter")
                else:
                    normalized_sequence.append(agent_type)
            
            normalized["processing_sequence"] = normalized_sequence
        
        return normalized
    
    def _validate_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and fix strategy if needed.
        
        Args:
            strategy: Assessment strategy
            
        Returns:
            Validated strategy
        """
        # Create a deep copy to avoid modifying the original
        validated = strategy.copy() if strategy else {}
        
        # Ensure required top-level keys
        required_keys = ["strategy_type", "chunking_strategy", "agents", "processing_sequence", "rationale"]
        for key in required_keys:
            if key not in validated:
                if key == "strategy_type":
                    validated[key] = "parallel_extraction"
                elif key == "chunking_strategy":
                    validated[key] = {"method": "fixed_size", "size": 8000, "overlap": 200, "rationale": "Default chunking strategy"}
                elif key == "agents":
                    validated[key] = []
                elif key == "processing_sequence":
                    validated[key] = []
                elif key == "rationale":
                    validated[key] = "Default assessment strategy with parallel extraction"
        
        # Ensure chunking strategy has required fields
        chunking_keys = ["method", "size", "overlap", "rationale"]
        for key in chunking_keys:
            if key not in validated["chunking_strategy"]:
                if key == "method":
                    validated["chunking_strategy"][key] = "fixed_size"
                elif key == "size":
                    validated["chunking_strategy"][key] = 8000
                elif key == "overlap":
                    validated["chunking_strategy"][key] = 200
                elif key == "rationale":
                    validated["chunking_strategy"][key] = "Default chunking parameters"
        
        # Check if we have agents but no processing sequence
        if validated["agents"] and not validated["processing_sequence"]:
            # Create default sequence from agent types
            validated["processing_sequence"] = [agent.get("agent_type") for agent in validated["agents"]]
        
        # Estimate token allocation if not provided
        if "token_allocation" not in validated:
            validated["token_allocation"] = self._estimate_token_allocation(validated)
        
        return validated
    
    def _estimate_token_allocation(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate token allocation for the strategy.
        
        Args:
            strategy: Assessment strategy
            
        Returns:
            Token allocation dictionary
        """
        # Start with a baseline allocation
        allocation = {
            "total_estimated": 0,
            "by_agent": {}
        }
        
        # Estimate based on document length
        document_length = len(self.context.document_text)
        document_tokens = self.estimate_tokens(self.context.document_text)
        
        # Adjust total based on document size and chunking
        chunking = strategy.get("chunking_strategy", {})
        chunk_size = chunking.get("size", 8000)
        chunk_overlap = chunking.get("overlap", 200)
        
        # Estimate number of chunks
        if chunk_size > 0:
            chunk_count = max(1, document_length // max(1, (chunk_size - chunk_overlap)))
        else:
            chunk_count = 1
        
        # Count extractors
        extractor_count = sum(1 for agent in strategy.get("agents", []) 
                           if agent.get("agent_type", "").lower() == "extractor")
        
        # Allocate tokens by agent
        total_tokens = 0
        by_agent = {}
        
        for agent in strategy.get("agents", []):
            agent_type = agent.get("agent_type", "").lower()
            
            if agent_type == "extractor":
                # Extractors process chunks
                tokens_per_extractor = (document_tokens // max(1, extractor_count)) * 1.2
                agent_tokens = int(tokens_per_extractor)
                by_agent[agent_type] = by_agent.get(agent_type, 0) + agent_tokens
                total_tokens += agent_tokens
                
            elif agent_type == "evaluator":
                # Evaluators process extracted evidence
                agent_tokens = int(document_tokens * 0.3)
                by_agent[agent_type] = agent_tokens
                total_tokens += agent_tokens
                
            elif agent_type == "reporter":
                # Reporters create reports
                agent_tokens = int(document_tokens * 0.2)
                by_agent[agent_type] = agent_tokens
                total_tokens += agent_tokens
                
            else:
                # Unknown agent type
                agent_tokens = int(document_tokens * 0.1)
                by_agent[agent_type] = agent_tokens
                total_tokens += agent_tokens
        
        # Create allocation dictionary
        allocation = {
            "total_estimated": total_tokens,
            "by_agent": by_agent
        }
        
        return allocation
    
    def _create_fallback_strategy(
        self, 
        document_analysis: Dict[str, Any], 
        framework_analysis: Dict[str, Any],
        criteria_groups: List[List[Dict[str, Any]]],
        chunking_strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a fallback strategy if strategy generation fails.
        
        Args:
            document_analysis: Document analysis results
            framework_analysis: Framework analysis results
            criteria_groups: Grouped criteria for parallel extraction
            chunking_strategy: Chunking strategy
            
        Returns:
            Fallback assessment strategy
        """
        self.logger.info("Creating fallback assessment strategy")
        
        # Create extractor agents for each criteria group
        extractor_agents = []
        for i, group in enumerate(criteria_groups):
            # Extract criteria and dimension IDs for instructions
            criteria_ids = [criterion["criterion_id"] for criterion in group]
            dimension_ids = list(set(criterion["dimension_id"] for criterion in group))
            
            # Create instructions
            criteria_text = "\n".join([
                f"- {criterion['dimension_name']} / {criterion['criterion_name']}: {criterion.get('criterion_question', '')}"
                for criterion in group
            ])
            
            instructions = f"""Extract ALL evidence related to the following criteria:

{criteria_text}

For each piece of relevant evidence, identify:
1. Which criterion it relates to
2. How strongly it supports or addresses the criterion
3. The specific text from the document that provides the evidence

Be thorough and extract all potential evidence, even indirect references that might be relevant.
Consider tone, context, and implications when identifying relevant content."""
            
            # Create specialized name
            agent_type = "extractor"
            if len(group) == 1:
                # For single criterion, add name to type
                agent_type = f"extractor ({group[0]['criterion_name'].lower()})"
            
            # Create extractor configuration
            extractor_config = {
                "agent_type": agent_type,
                "configuration": {
                    "extraction_type": "direct",
                    "batch_size": 1,
                    "min_confidence": 0.6,
                    "criteria_ids": criteria_ids,
                    "dimension_ids": dimension_ids
                },
                "instructions": instructions,
                "inputs": ["document_chunks"],
                "outputs": [f"extracted_evidence_group_{i+1}"]
            }
            
            extractor_agents.append(extractor_config)
        
        # Create evaluator agent
        evaluator_config = {
            "agent_type": "evaluator",
            "configuration": {
                "evaluation_type": "structured",
                "confidence_threshold": 0.6,
                "infer_missing": True,
                "output_format": "scorecard"
            },
            "instructions": """Evaluate each criterion based on ALL collected evidence. 
Produce structured ratings with clear justifications. 
Identify strengths and weaknesses for each criterion.
Generate an overall assessment with key strengths and areas for improvement.""",
            "inputs": ["extracted_evidence_group_1", "extracted_evidence_group_2", "extracted_evidence_group_3"],
            "outputs": ["structured_assessments"]
        }
        
        # Create reporter agent
        reporter_config = {
            "agent_type": "reporter",
            "configuration": {
                "report_type": "scorecard",
                "include_evidence": True
            },
            "instructions": """Create a structured scorecard from the evaluations.
Format the ratings and justifications into a clear, presentable structure.
Do not duplicate the evaluator's analysis work.""",
            "inputs": ["structured_assessments"],
            "outputs": ["assessment_scorecard"]
        }
        
        # Combine agents
        all_agents = extractor_agents + [evaluator_config, reporter_config]
        
        # Create processing sequence
        extractor_names = ["extractor"] * len(extractor_agents)
        processing_sequence = extractor_names + ["evaluator", "reporter"]
        
        # Create fallback strategy
        fallback_strategy = {
            "strategy_type": "parallel_extraction",
            "chunking_strategy": chunking_strategy,
            "agents": all_agents,
            "processing_sequence": processing_sequence,
            "token_allocation": {},
            "rationale": "Specialized strategy with one extractor per criterion or small group, followed by structured evaluation and reporting."
        }
        
        # Estimate token allocation
        fallback_strategy["token_allocation"] = self._estimate_token_allocation(fallback_strategy)
        
        return fallback_strategy