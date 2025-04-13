"""
Meta Planner Agent - Designs assessment strategies based on document and framework

This module provides the MetaPlannerAgent class, which analyzes documents and 
frameworks to design custom processing strategies for assessment.
"""

import json, re, os
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from core.agents.base import BaseAgent
from core.context import AssessmentContext

class MetaPlannerAgent(BaseAgent):
    """
    Designs custom assessment strategies based on document and framework analysis.
    
    The Meta Planner is responsible for:
    1. Analyzing document content and structure
    2. Evaluating framework dimensions and criteria
    3. Designing an optimal processing strategy
    4. Configuring agent deployment and sequencing
    5. Creating custom instructions for each agent
    
    This is the strategic "brain" of the assessment system.
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
        self.logger.info(f"{name} initialized")
        
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
            
            # 5. Store strategy in context
            self.context.set_planning_data(assessment_strategy)
            
            # Record processing time
            elapsed_time = self.stop_timer()
            self.logger.info(f"Assessment strategy planning completed in {elapsed_time:.2f}s")
            
            # Record observation
            self.record_observation("strategy_created", {
                "strategy_type": assessment_strategy.get("strategy_type"),
                "agent_count": len(assessment_strategy.get("agents", [])),
                "time_taken": elapsed_time
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
        
        for dimension in dimensions:
            dimension_id = dimension.get("id", "")
            if not dimension_id:
                continue
                
            criteria = dimension.get("criteria", [])
            criteria_count = len(criteria)
            
            criteria_counts[dimension_id] = criteria_count
            total_criteria += criteria_count
        
        # Get rating scale if available
        rating_scale = framework.get("rating_scale", {})
        rating_levels = rating_scale.get("levels", [])
        
        # Create framework analysis
        framework_analysis = {
            "framework_id": framework_id,
            "framework_name": framework_name,
            "dimension_count": dimension_count,
            "total_criteria": total_criteria,
            "criteria_by_dimension": criteria_counts,
            "has_rating_scale": bool(rating_levels),
            "rating_levels_count": len(rating_levels),
            "scoring_methods": framework.get("scoring_methods", {})
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
        
        # Create prompt for strategy design
        system_prompt = """You are an expert strategy designer for AI assessment systems. Your task is to design an optimal assessment strategy based on document and framework analysis. The strategy should specify which agents to deploy, how they should be configured, and how they should be sequenced."""
        
        # Get user options if available
        user_options = self.context.options.get("user_options", {})
        user_preferences_text = ""
        
        if user_options:
            user_preferences_text = "USER PREFERENCES:\n"
            for key, value in user_options.items():
                user_preferences_text += f"- {key}: {value}\n"
        
        # Use a raw string for the JSON schema part to avoid f-string issues
        json_schema = r'''```json
    {
    "strategy_type": "string",
    "chunking_strategy": {
        "method": "string",
        "size": number,
        "overlap": number,
        "rationale": "string"
    },
    "agents": [
        {
        "agent_type": "string",
        "configuration": object,
        "instructions": "string",
        "inputs": ["string"],
        "outputs": ["string"]
        }
    ],
    "processing_sequence": ["string"],
    "token_allocation": {
        "total_estimated": number,
        "by_agent": object
    },
    "rationale": "string"
    }
    ```'''
        
        # Combine all parts into the final prompt
        human_prompt = f"""Design an optimal assessment strategy based on the following document and framework analysis.

    DOCUMENT ANALYSIS:
    {json.dumps(document_analysis, indent=2)}

    FRAMEWORK ANALYSIS:
    {json.dumps(framework_analysis, indent=2)}

    {user_preferences_text}

    Your strategy should include:

    1. Chunking strategy (method, size, overlap)
    2. Agent deployment plan (which agents to use and how to configure them)
    3. Processing sequence (order of operations)
    4. Custom instructions for each agent
    5. Reasoning for your strategy choices

    Available agents:
    - Extractor: Extracts content related to framework dimensions and criteria
    - Evaluator: Evaluates criteria based on evidence
    - Reporter: Generates assessment reports

    Available chunking methods:
    - fixed_size: Splits by character/token count
    - paragraph: Splits by paragraph boundaries
    - semantic: Splits by topic/semantic boundaries

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
                max_tokens=2000
            )
            
            # Ensure the strategy has all required sections
            strategy = self._validate_strategy(strategy_json)
            
            # Record observation
            self.record_observation("strategy_design", {
                "strategy_type": strategy.get("strategy_type"),
                "chunking_method": strategy.get("chunking_strategy", {}).get("method"),
                "agent_count": len(strategy.get("agents", []))
            })
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"Error generating assessment strategy: {str(e)}", exc_info=True)
            
            # Create fallback strategy
            fallback_strategy = self._create_fallback_strategy(document_analysis, framework_analysis)
            
            self.add_warning(f"Used fallback strategy due to error: {str(e)}")
            
            return fallback_strategy
    
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
                    validated[key] = "standard"
                elif key == "chunking_strategy":
                    validated[key] = {"method": "fixed_size", "size": 2000, "overlap": 200, "rationale": "Default chunking strategy"}
                elif key == "agents":
                    validated[key] = []
                elif key == "processing_sequence":
                    validated[key] = []
                elif key == "rationale":
                    validated[key] = "Default assessment strategy"
        
        # Ensure chunking strategy has required fields
        chunking_keys = ["method", "size", "overlap", "rationale"]
        for key in chunking_keys:
            if key not in validated["chunking_strategy"]:
                if key == "method":
                    validated["chunking_strategy"][key] = "fixed_size"
                elif key == "size":
                    validated["chunking_strategy"][key] = 2000
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
        chunk_size = chunking.get("size", 2000)
        chunk_overlap = chunking.get("overlap", 200)
        
        # Estimate number of chunks
        if chunk_size > 0:
            chunk_count = max(1, document_length // max(1, (chunk_size - chunk_overlap)))
        else:
            chunk_count = 1
        
        # Allocate tokens by agent
        for agent in strategy.get("agents", []):
            agent_type = agent.get("agent_type")
            
            if agent_type == "extractor":
                # Extractors process chunks directly
                agent_tokens = chunk_count * 1000  # Rough estimate per chunk
            elif agent_type == "evaluator":
                # Evaluators process extracted content
                agent_tokens = document_tokens * 0.3  # Assume 30% of document tokens
            elif agent_type == "reporter":
                # Reporters create summaries
                agent_tokens = document_tokens * 0.2  # Assume 20% of document tokens
            else:
                # Default estimate
                agent_tokens = document_tokens * 0.1
            
            allocation["by_agent"][agent_type] = int(agent_tokens)
            allocation["total_estimated"] += int(agent_tokens)
        
        return allocation
    
    def _create_fallback_strategy(
        self, 
        document_analysis: Dict[str, Any], 
        framework_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a fallback strategy if strategy generation fails.
        
        Args:
            document_analysis: Document analysis results
            framework_analysis: Framework analysis results
            
        Returns:
            Fallback assessment strategy
        """
        self.logger.info("Creating fallback assessment strategy")
        
        # Determine chunking method based on document type
        doc_type = document_analysis.get("document_type", "unknown").lower()
        chunking_method = "fixed_size"
        chunk_size = 2000
        chunk_overlap = 200
        
        if "transcript" in doc_type or "dialogue" in doc_type:
            chunking_method = "paragraph"
            chunk_size = 3000
            chunk_overlap = 300
        elif "report" in doc_type or "article" in doc_type:
            chunking_method = "semantic"
            chunk_size = 2500
            chunk_overlap = 250
        
        # Create fallback strategy
        fallback_strategy = {
            "strategy_type": "fallback",
            "chunking_strategy": {
                "method": chunking_method,
                "size": chunk_size,
                "overlap": chunk_overlap,
                "rationale": "Fallback chunking strategy based on document type"
            },
            "agents": [
                {
                    "agent_type": "extractor",
                    "configuration": {
                        "extraction_type": "direct",
                        "batch_size": 10,
                        "min_confidence": 0.7
                    },
                    "instructions": "Extract content related to framework dimensions and criteria, focusing on direct evidence.",
                    "inputs": ["document_chunks"],
                    "outputs": ["extracted_content"]
                },
                {
                    "agent_type": "evaluator",
                    "configuration": {
                        "evaluation_type": "evidence-based",
                        "confidence_threshold": 0.6
                    },
                    "instructions": "Evaluate criteria based on extracted evidence, providing clear rationales for assessments.",
                    "inputs": ["extracted_content", "framework"],
                    "outputs": ["criteria_assessments"]
                },
                {
                    "agent_type": "reporter",
                    "configuration": {
                        "report_type": "comprehensive",
                        "include_evidence": True
                    },
                    "instructions": "Generate a comprehensive assessment report with evidence links and confidence ratings.",
                    "inputs": ["criteria_assessments", "framework"],
                    "outputs": ["assessment_report"]
                }
            ],
            "processing_sequence": ["extractor", "evaluator", "reporter"],
            "token_allocation": {
                "total_estimated": 0,
                "by_agent": {}
            },
            "rationale": "Fallback strategy using standard processing sequence and configuration."
        }
        
        # Estimate token allocation
        fallback_strategy["token_allocation"] = self._estimate_token_allocation(fallback_strategy)
        
        return fallback_strategy