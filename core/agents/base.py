"""
Enhanced Base Agent - Improved foundation for all assessment agents

This module provides an enhanced BaseAgent class with improvements for caching,
structured output, and parallel processing capabilities.
"""

import logging
import json, re, os, sys
import asyncio
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple

# Import context
from ..context import AssessmentContext

class BaseAgent(ABC):
    """
    Enhanced abstract base class for all assessment agents.
    
    The BaseAgent provides:
    1. Standard context access methods
    2. Observation recording
    3. Error handling
    4. Progress tracking
    5. Token usage tracking
    6. Resource optimization
    7. Caching for LLM calls
    8. Structured output helpers
    9. Parallel processing utilities
    
    All specialized agents should inherit from this base class.
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        llm: Any,  # Could be LangChain ChatModel or other LLM interface
        context: AssessmentContext,
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a base agent.
        
        Args:
            name: Name of the agent (should be unique)
            role: Role of the agent (e.g., 'planner', 'extractor')
            llm: Language model instance
            context: Shared assessment context
            options: Optional configuration options
        """
        self.name = name
        self.role = role
        self.llm = llm
        self.context = context
        self.options = options or {}
        
        # Initialize token tracking
        self._token_usage = {
            "prompt": 0,
            "completion": 0,
            "total": 0
        }
        
        # Initialize performance metrics
        self._performance_metrics = {
            "processing_time": 0,
            "calls": 0,
            "successful_calls": 0,
            "failed_calls": 0
        }
        
        # Set up logging
        self.logger = logging.getLogger(f"learning-lab-ai.agents.{name}")
        
        # Register agent with context if stage is set
        if context.current_stage:
            context.set_stage_agent(context.current_stage, name)
            
        self.logger.info(f"Agent '{name}' initialized with role '{role}'")
    
    @abstractmethod
    async def process(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main processing method to be implemented by concrete agents.
        
        The implementation depends on the specific agent role.
        
        Returns:
            Processing result dictionary
        """
        pass
    
    #
    # Context Access Methods
    #
    
    def record_observation(self, observation_type: str, observation: Any):
        """
        Record an observation in the shared context.
        
        Args:
            observation_type: Type of observation (e.g., 'evidence', 'assessment')
            observation: Content of the observation
        """
        self.context.record_agent_observation(self.name, observation_type, observation)
        self.logger.debug(f"Recorded {observation_type} observation")
        
    def update_progress(self, progress: float, message: Optional[str] = None):
        """
        Update progress in the shared context.
        
        Args:
            progress: Progress value between 0.0 and 1.0
            message: Optional progress message
        """
        self.context.update_progress(progress, message)
        
    def add_warning(self, warning_message: str):
        """
        Add a warning message to the context.
        
        Args:
            warning_message: Warning message
        """
        self.context.add_warning(warning_message, self.context.current_stage)
        self.logger.warning(warning_message)
    
    #
    # Evidence Methods
    #
    
    def add_evidence(
        self, 
        dimension_id: str, 
        criterion_id: str, 
        text: str, 
        chunk_id: Optional[str] = None, 
        location: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add evidence for a criterion.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            text: Evidence text
            chunk_id: Optional ID of the chunk containing the evidence
            location: Optional location info (e.g., start and end positions)
            metadata: Optional additional metadata
            
        Returns:
            ID of the newly created evidence
        """
        evidence_id = self.context.add_evidence(
            dimension_id, criterion_id, text, chunk_id, location, metadata
        )
        
        # Record observation
        self.record_observation("evidence_added", {
            "evidence_id": evidence_id,
            "dimension_id": dimension_id,
            "criterion_id": criterion_id,
            "text_preview": text[:100] + ("..." if len(text) > 100 else "")
        })
        
        return evidence_id
        
    def get_evidence_for_criterion(
        self, 
        dimension_id: str, 
        criterion_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all evidence for a criterion.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            
        Returns:
            List of evidence records for the criterion
        """
        return self.context.get_evidence_for_criterion(dimension_id, criterion_id)
    
    #
    # Assessment Methods
    #
    
    def set_criterion_assessment(
        self,
        dimension_id: str,
        criterion_id: str,
        rating: Any,
        rationale: str,
        confidence: Optional[float] = None,
        assessment_type: str = "direct"
    ) -> bool:
        """
        Set assessment for a criterion.
        
        Args:
            dimension_id: ID of the dimension
            criterion_id: ID of the criterion
            rating: Assessment rating (type depends on scoring method)
            rationale: Rationale for the assessment
            confidence: Optional confidence score (0.0-1.0)
            assessment_type: Type of assessment ("direct", "inferred", "insufficient_evidence")
            
        Returns:
            True if assessment was set successfully, False otherwise
        """
        # Add assessment type to the assessment data
        assessment_data = {
            "rating": rating,
            "rationale": rationale,
            "confidence": confidence,
            "assessment_type": assessment_type,
            "timestamp": time.time()
        }
        
        # Try to set assessment with the expanded data
        if hasattr(self.context, 'set_criterion_assessment_with_metadata'):
            result = self.context.set_criterion_assessment_with_metadata(
                dimension_id, criterion_id, assessment_data
            )
        else:
            # Fall back to standard method if enhanced one is not available
            result = self.context.set_criterion_assessment(
                dimension_id, criterion_id, rating, rationale, confidence
            )
        
        if result:
            # Record observation
            self.record_observation("assessment_added", {
                "dimension_id": dimension_id,
                "criterion_id": criterion_id,
                "rating": rating,
                "confidence": confidence,
                "assessment_type": assessment_type
            })
            
        return result
        
    def set_dimension_summary(self, dimension_id: str, summary: Dict[str, Any]) -> bool:
        """
        Set summary assessment for a dimension.
        
        Args:
            dimension_id: ID of the dimension
            summary: Summary assessment data
            
        Returns:
            True if summary was set successfully, False otherwise
        """
        result = self.context.set_dimension_summary(dimension_id, summary)
        
        if result:
            # Record observation
            self.record_observation("dimension_summary_added", {
                "dimension_id": dimension_id,
                "summary_type": summary.get("type")
            })
            
        return result
        
    def set_overall_assessment(self, assessment: Dict[str, Any]):
        """
        Set overall assessment for the framework.
        
        Args:
            assessment: Overall assessment data
        """
        self.context.set_overall_assessment(assessment)
        
        # Record observation
        self.record_observation("overall_assessment_added", {
            "assessment_keys": list(assessment.keys())
        })
    
    #
    # Token Tracking Methods
    #
    
    def track_tokens(self, token_count: int, token_type: str = "total", source: str = "manual"):
        """
        Track token usage.
        
        Args:
            token_count: Number of tokens to record
            token_type: Type of tokens ('prompt', 'completion', 'total')
            source: Source of token count ('llm_call', 'manual')
        """
        # Update agent's token counts
        self._token_usage[token_type] = self._token_usage.get(token_type, 0) + token_count
        
        # Update total if tracking a specific type
        if token_type != "total":
            self._token_usage["total"] += token_count
        
        # Update context token tracking if available
        if hasattr(self.context, 'track_token_usage'):
            self.context.track_token_usage(token_count, token_type, self.name)
        
        # Record observation
        self.record_observation("token_usage", {
            "count": token_count,
            "type": token_type,
            "agent": self.name,
            "stage": self.context.current_stage,
            "source": source,
            "cumulative": self._token_usage[token_type]
        })
        
        self.logger.debug(f"Tracked {token_count} {token_type} tokens from {source}")
    
    def get_token_usage(self) -> Dict[str, int]:
        """
        Get token usage statistics.
        
        Returns:
            Dictionary with token usage counts by type
        """
        return self._token_usage
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        This is a rough estimation for planning purposes.
        
        Args:
            text: Text to estimate token count for
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        # This is a rough approximation for GPT models
        return max(1, len(text) // 4)
    
    def plan_tokens(self, 
                   available_tokens: int, 
                   tasks: List[Dict[str, Any]]
                  ) -> Dict[str, int]:
        """
        Plan token allocation for multiple tasks.
        
        Args:
            available_tokens: Total tokens available
            tasks: List of tasks with estimated token needs
            
        Returns:
            Dictionary mapping task IDs to token allocations
        """
        # Simple proportional allocation
        total_estimated = sum(task.get("estimated_tokens", 0) for task in tasks)
        
        allocations = {}
        
        if total_estimated <= available_tokens:
            # Can allocate full amounts
            for task in tasks:
                task_id = task.get("id", f"task_{len(allocations)}")
                allocations[task_id] = task.get("estimated_tokens", 0)
        else:
            # Need to scale down proportionally
            for task in tasks:
                task_id = task.get("id", f"task_{len(allocations)}")
                estimated = task.get("estimated_tokens", 0)
                priority = task.get("priority", 1.0)
                
                # Adjust by priority (higher priority gets more tokens)
                proportion = (estimated / total_estimated) * priority
                allocated = int(available_tokens * proportion)
                
                allocations[task_id] = allocated
                
        return allocations
    
    #
    # Performance Tracking
    #
    
    def start_timer(self):
        """Start performance timer."""
        self._start_time = time.time()
    
    def stop_timer(self):
        """
        Stop performance timer and record elapsed time.
        
        Returns:
            Elapsed time in seconds
        """
        if hasattr(self, '_start_time'):
            elapsed = time.time() - self._start_time
            self._performance_metrics["processing_time"] += elapsed
            return elapsed
        return 0
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        return self._performance_metrics
    
    #
    # Enhanced LLM Interaction
    #
    
    async def _safe_llm_call(
        self, 
        func_name: str, 
        *args, 
        max_retries: int = 2,
        retry_delay: float = 2.0,
        track_tokens: bool = True,
        **kwargs
    ) -> Any:
        """
        Safely call an LLM function with retry logic and token tracking.
        
        Args:
            func_name: Name of the LLM function to call
            *args: Positional arguments for the function
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            track_tokens: Whether to track token usage
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the LLM function call
            
        Raises:
            Exception: If all retry attempts fail
        """
        retries = 0
        last_error = None
        
        # Update call counter
        self._performance_metrics["calls"] += 1
        
        # Start timer
        self.start_timer()
        
        # Get the function to call
        if not hasattr(self.llm, func_name):
            self._performance_metrics["failed_calls"] += 1
            raise ValueError(f"LLM does not have method {func_name}")
            
        func = getattr(self.llm, func_name)
        
        # Try calling with retries
        while retries <= max_retries:
            try:
                result = await func(*args, **kwargs)
                elapsed_time = self.stop_timer()
                
                # Update success counter
                self._performance_metrics["successful_calls"] += 1
                
                self.logger.debug(f"LLM call to {func_name} succeeded in {elapsed_time:.2f}s")
                
                # Track token usage if requested and available
                if track_tokens:
                    # Check if result is a tuple with usage info
                    if isinstance(result, tuple) and len(result) > 1 and isinstance(result[1], dict):
                        tokens_info = result[1].get("usage", result[1])
                        if "total_tokens" in tokens_info:
                            # Track individual token types if available
                            if "prompt_tokens" in tokens_info:
                                self.track_tokens(tokens_info["prompt_tokens"], "prompt", "llm_call")
                            if "completion_tokens" in tokens_info:
                                self.track_tokens(tokens_info["completion_tokens"], "completion", "llm_call")
                            
                            # Track total tokens
                            self.track_tokens(tokens_info["total_tokens"], "total", "llm_call")
                            
                            # Record detailed observation
                            self.record_observation("llm_usage", {
                                "function": func_name,
                                "total_tokens": tokens_info["total_tokens"],
                                "prompt_tokens": tokens_info.get("prompt_tokens"),
                                "completion_tokens": tokens_info.get("completion_tokens"),
                                "elapsed_time": elapsed_time
                            })
                
                return result
                
            except Exception as e:
                last_error = e
                retries += 1
                
                # Update metrics
                if retries > max_retries:
                    self._performance_metrics["failed_calls"] += 1
                
                if retries <= max_retries:
                    backoff_time = retry_delay * retries
                    self.logger.warning(
                        f"LLM call to {func_name} failed (attempt {retries}). "
                        f"Retrying in {backoff_time:.1f}s... Error: {str(e)}"
                    )
                    time.sleep(backoff_time)
                else:
                    self.logger.error(
                        f"LLM call to {func_name} failed after {retries} attempts. "
                        f"Last error: {str(e)}"
                    )
        
        # If we get here, all retries failed
        self.stop_timer()  # Stop the timer
        raise last_error

    async def _cached_llm_call(self, operation: str, content: Any, func_name: str, *args, **kwargs) -> Any:
        """
        Cache LLM call results to avoid repeated identical calls.
        
        Args:
            operation: Name of the operation being cached
            content: Content hash key for the cache
            func_name: LLM function to call
            *args, **kwargs: Arguments for the LLM function
            
        Returns:
            Result from the LLM function (cached or fresh)
        """
        # Create a cache key
        content_str = str(content)
        content_hash = hashlib.md5(content_str.encode('utf-8')).hexdigest()
        cache_key = f"{self.name}_{operation}_{content_hash}"
        
        # Initialize cache in context if not exists
        if not hasattr(self.context, 'llm_cache'):
            self.context.llm_cache = {}
        
        # Check cache
        if cache_key in self.context.llm_cache:
            self.logger.debug(f"Cache hit for {operation}")
            return self.context.llm_cache[cache_key]
        
        # Call LLM if not cached
        result = await self._safe_llm_call(func_name, *args, **kwargs)
        
        # Store result in cache
        self.context.llm_cache[cache_key] = result
        
        return result

    async def _structured_output_call(
        self, 
        prompt: str, 
        output_schema: Dict[str, Any], 
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Call LLM with structured output schema for consistent parsing.
        
        Args:
            prompt: User prompt for the LLM
            output_schema: JSON schema defining expected output structure
            system_prompt: Optional system prompt to guide the LLM
            temperature: Temperature parameter for generation
            max_tokens: Maximum tokens for generation
            
        Returns:
            Structured output from the LLM conforming to schema
        """
        try:
            # Generate structured output using the LLM
            result, usage = await self._safe_llm_call(
                "generate_structured_output",
                prompt=prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Return just the structured output (not usage)
            return result
            
        except Exception as e:
            self.logger.error(f"Error in structured output call: {str(e)}")
            
            # Fall back to non-structured generation and try to extract JSON
            self.logger.warning("Falling back to standard completion with JSON extraction")
            
            try:
                # Create a prompt that requests JSON output
                fallback_prompt = f"{prompt}\n\nPlease format your response as a valid JSON object."
                
                # Call standard completion
                text_output, _ = await self._safe_llm_call(
                    "generate_completion",
                    prompt=fallback_prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Try to extract JSON from the text output
                import re
                import json
                
                # Look for JSON block
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text_output)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find any JSON object/array
                    json_str = text_output
                
                # Parse JSON
                parsed_json = json.loads(json_str)
                return parsed_json
                
            except Exception as e2:
                self.logger.error(f"Fallback JSON extraction also failed: {str(e2)}")
                # Return minimal valid structure to avoid cascading errors
                return {"error": f"Failed to generate structured output: {str(e)}"}

    #
    # Parallel Processing
    #
    
    async def process_in_batches(self, items, batch_size, process_fn, *args, **kwargs):
        """
        Process a list of items in batches with progress tracking.
        
        Args:
            items: List of items to process
            batch_size: Size of each batch
            process_fn: Async function to process each batch
            *args, **kwargs: Additional arguments for process_fn
            
        Returns:
            List of results from all batches
        """
        results = []
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            # Update progress
            progress = batch_num / total_batches
            self.update_progress(progress, f"Processing batch {batch_num}/{total_batches}")
            
            # Process batch
            batch_results = await process_fn(batch, *args, **kwargs)
            results.extend(batch_results)
        
        return results

    async def run_parallel_tasks(self, tasks, max_concurrent=3):
        """
        Run multiple async tasks in parallel with concurrency control.
        
        Args:
            tasks: List of async coroutines to execute
            max_concurrent: Maximum number of concurrent tasks
            
        Returns:
            List of results from all tasks
        """
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(task_coro, task_index):
            async with semaphore:
                try:
                    return await task_coro
                except Exception as e:
                    self.logger.error(f"Task {task_index} failed: {str(e)}")
                    self.add_warning(f"Parallel task {task_index} failed: {str(e)}")
                    return None
        
        # Wrap tasks with semaphore
        wrapped_tasks = [
            run_with_semaphore(task, i)
            for i, task in enumerate(tasks)
        ]
        
        # Run all tasks and gather results
        results = await asyncio.gather(*wrapped_tasks, return_exceptions=False)
        return results

    def divide_work(self, items, num_groups):
        """
        Divide a list of items into balanced groups for parallel processing.
        
        Args:
            items: List of items to divide
            num_groups: Number of groups to create
            
        Returns:
            List of groups, each containing a subset of items
        """
        groups = [[] for _ in range(num_groups)]
        
        for i, item in enumerate(items):
            group_index = i % num_groups
            groups[group_index].append(item)
        
        return groups

    def aggregate_results(self, result_groups, aggregate_fn=None):
        """
        Aggregate results from multiple agents or tasks.
        
        Args:
            result_groups: List of result groups to aggregate
            aggregate_fn: Optional function to customize aggregation
            
        Returns:
            Aggregated results
        """
        if aggregate_fn:
            return aggregate_fn(result_groups)
        
        # Default aggregation logic for different result types
        if all(isinstance(group, dict) for group in result_groups):
            # Merge dictionaries
            merged = {}
            for group in result_groups:
                merged.update(group)
            return merged
        
        elif all(isinstance(group, list) for group in result_groups):
            # Flatten lists
            flattened = []
            for group in result_groups:
                flattened.extend(group)
            return flattened
        
        # Default: return as is
        return result_groups
    
    #
    # Prompt Optimization
    #
    
    def optimize_prompt(self, prompt: str, max_length: int = 4000) -> str:
        """
        Optimize prompt to reduce token usage while preserving key information.
        
        Args:
            prompt: Original prompt text
            max_length: Target maximum length
            
        Returns:
            Optimized prompt text
        """
        # If prompt is already short enough, return it unchanged
        if len(prompt) <= max_length:
            return prompt
        
        # Import required modules
        import re
        
        # Try to identify sections in the prompt
        sections = re.findall(r'([A-Z][A-Z\s]+):\n(.*?)(?=\n[A-Z][A-Z\s]+:|$)', prompt, re.DOTALL)
        
        # If no sections found, perform simple truncation
        if not sections:
            # Simple truncation preserving beginning and end
            half_length = max_length // 2
            return prompt[:half_length] + "\n...\n" + prompt[-half_length:]
        
        # Calculate total length to reduce
        excess_length = len(prompt) - max_length
        
        # Identify large sections to compress
        section_lengths = [(title, content, len(content)) for title, content in sections]
        section_lengths.sort(key=lambda x: x[2], reverse=True)
        
        # Start with the largest sections for compression
        compressed_sections = {}
        remaining_excess = excess_length
        
        for title, content, length in section_lengths:
            # Skip small sections
            if length < 500:
                continue
                
            # Calculate how much to reduce this section
            # Reduce proportionally to its size
            reduction = min(remaining_excess, int(length * 0.6))
            if reduction <= 0:
                break
                
            # Compress the section
            if "EVIDENCE" in title or "TEXT" in title:
                # For evidence or text, preserve first and last parts
                preserve = (length - reduction) // 2
                compressed = content[:preserve] + "\n...\n" + content[-preserve:]
            else:
                # For other sections, try to preserve important sentences
                sentences = re.split(r'(?<=[.!?])\s+', content)
                if len(sentences) <= 3:
                    # Too few sentences to compress meaningfully
                    continue
                    
                # Keep first, last, and sample from middle
                compressed = sentences[0] + " "
                if len(sentences) > 5:
                    compressed += sentences[1] + " "
                compressed += "... "
                if len(sentences) > 5:
                    compressed += sentences[-2] + " "
                compressed += sentences[-1]
            
            # Update tracking
            compressed_sections[title] = compressed
            remaining_excess -= (length - len(compressed))
            
            # Check if we've compressed enough
            if remaining_excess <= 0:
                break
        
        # Reconstruct the prompt with compressed sections
        optimized_prompt = ""
        for title, content in sections:
            if title in compressed_sections:
                optimized_prompt += f"{title}:\n{compressed_sections[title]}\n\n"
            else:
                optimized_prompt += f"{title}:\n{content}\n\n"
        
        return optimized_prompt