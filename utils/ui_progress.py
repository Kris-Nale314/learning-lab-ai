"""
UI Progress Tracking for Framework Assessment Workbench

Enhanced progress tracking with animations and status updates.
"""

import streamlit as st
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Union

# Stage emojis for different processing stages
STAGE_EMOJIS = {
    "planning": "🧠",
    "chunking": "✂️",
    "extractor_processing": "🔍",
    "evaluator_processing": "⚖️",
    "reporter_processing": "📊",
    "formatting": "✨",
    "initializing": "🚀",
    "document_analysis": "📄",
    "evidence_extraction": "🔎",
    "assessment": "📝",
    "confidence": "🎯",
    "report_generation": "📊",
    "visualization": "📈",
    "completed": "✅",
    "failed": "❌"
}

# Descriptions for different stages
STAGE_DESCRIPTIONS = {
    "planning": "Designing assessment strategy...",
    "chunking": "Dividing document into manageable chunks...",
    "extractor_processing": "Extracting evidence from document...",
    "evaluator_processing": "Evaluating criteria based on evidence...",
    "reporter_processing": "Generating assessment reports...",
    "formatting": "Formatting results for presentation...",
    "initializing": "Initializing assessment process...",
    "document_analysis": "Analyzing document structure and content...",
    "evidence_extraction": "Finding relevant evidence for criteria...",
    "assessment": "Evaluating criteria against evidence...",
    "confidence": "Determining confidence in assessments...",
    "report_generation": "Creating assessment reports...",
    "visualization": "Preparing data visualizations...",
    "completed": "Assessment completed!",
    "failed": "Assessment failed!"
}

# Animation frames for different stages
ANIMATIONS = {
    "planning": ["🧠", "💭", "💡", "🔄"],
    "chunking": ["✂️  ", " ✂️ ", "  ✂️"],
    "extractor_processing": ["🔍", "🔎", "🔍", "🔎"],
    "evaluator_processing": ["⚖️  ", " ⚖️ ", "  ⚖️"],
    "reporter_processing": ["📊", "📈", "📉", "📊"],
    "initializing": ["🚀", "🚀.", "🚀..", "🚀..."],
    "evidence_extraction": ["🔍", "🔎", "🔍", "🔎"],
    "assessment": ["📝", "📝.", "📝..", "📝..."],
    "default": ["⏳", "⌛", "⏳", "⌛"]
}

class EnhancedProgress:
    """
    Enhanced progress tracking with elegant animations and status updates.
    Optimized for dark theme with professional styling.
    """
    
    def __init__(self, total_steps: Optional[int] = None):
        """
        Initialize enhanced progress tracker.
        
        Args:
            total_steps: Optional total number of steps
        """
        # Create a nicer container for progress display
        self.progress_container = st.container()
        
        with self.progress_container:
            # Create columns for better layout
            col1, col2 = st.columns([1, 6])
            
            with col1:
                self.icon_container = st.empty()
                
            with col2:
                self.status_container = st.empty()
                self.progress_bar = st.progress(0)
                self.status_details = st.empty()
        
        self.step_logs = st.empty()
        
        self.total_steps = total_steps
        self.current_step = 0
        self.steps_completed = []
        self.current_stage = None
        self.animation_thread = None
        self.stop_animation = False
        self.progress_value = 0.0
        self.start_time = time.time()
        
    def update_progress(self, progress: float, stage: Optional[str] = None, message: Optional[str] = None):
        """
        Update progress with stage and message.
        
        Args:
            progress: Progress value between 0.0 and 1.0
            stage: Optional current stage
            message: Optional status message
        """
        self.progress_value = progress
        self.progress_bar.progress(progress)
        
        if stage and stage != self.current_stage:
            self.start_stage_animation(stage)
            self.steps_completed.append((self.current_stage, time.time() - self.start_time))
            self.current_stage = stage
            
        if message:
            emoji = STAGE_EMOJIS.get(stage, "🔄")
            
            # Show status details with clean styling
            self.status_details.markdown(
                f"<div style='color: #A0A0A0; font-size: 0.9em; margin-top: 5px;'>"
                f"{message} ({progress:.0%} complete)"
                f"</div>", 
                unsafe_allow_html=True
            )
            
    def start_stage_animation(self, stage: str):
        """
        Start animated stage display with elegant styling.
        
        Args:
            stage: Current processing stage
        """
        # Stop any existing animation
        if self.animation_thread and self.animation_thread.is_alive():
            self.stop_animation = True
            self.animation_thread.join()
            
        self.stop_animation = False
        
        # Get stage information
        animation_frames = ANIMATIONS.get(stage, ANIMATIONS["default"])
        description = STAGE_DESCRIPTIONS.get(stage, f"Processing {stage}...")
        
        # Update the stage description immediately
        self.status_container.markdown(
            f"<div style='font-weight: 500; font-size: 1.1em;'>{description}</div>",
            unsafe_allow_html=True
        )
        
        # Start animation thread
        self.animation_thread = threading.Thread(
            target=self._animate_stage,
            args=(animation_frames, description)
        )
        self.animation_thread.daemon = True
        self.animation_thread.start()
        
    def _animate_stage(self, frames: List[str], description: str):
        """
        Animate stage with elegant icon animation.
        
        Args:
            frames: List of animation frames
            description: Stage description
        """
        i = 0
        while not self.stop_animation:
            frame = frames[i % len(frames)]
            elapsed = time.time() - self.start_time
            
            # Update just the icon with animation
            self.icon_container.markdown(
                f"<div style='font-size: 2rem; text-align: center; "
                f"animation: pulse 2s infinite;'>{frame}</div>",
                unsafe_allow_html=True
            )
            
            time.sleep(0.3)  # Slightly faster animation for better UX
            i += 1
            
    def complete(self, success: bool = True):
        """
        Mark progress as complete with professional styling.
        
        Args:
            success: Whether the process completed successfully
        """
        self.stop_animation = True
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join()
            
        self.progress_bar.progress(1.0)
        
        # Calculate total time
        total_time = time.time() - self.start_time
        
        # Update display with completion status
        if success:
            # Success display
            self.icon_container.markdown(
                "<div style='font-size: 2.2rem; text-align: center; color: #00CC96;'>✅</div>",
                unsafe_allow_html=True
            )
            
            self.status_container.markdown(
                f"<div style='font-weight: 600; font-size: 1.2em; color: #00CC96;'>"
                f"Assessment Completed Successfully"
                f"</div>",
                unsafe_allow_html=True
            )
            
            self.status_details.markdown(
                f"<div style='color: #A0A0A0; font-size: 0.9em;'>"
                f"Completed in {total_time:.1f} seconds"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            # Failure display
            self.icon_container.markdown(
                "<div style='font-size: 2.2rem; text-align: center; color: #FF6B6B;'>❌</div>",
                unsafe_allow_html=True
            )
            
            self.status_container.markdown(
                f"<div style='font-weight: 600; font-size: 1.2em; color: #FF6B6B;'>"
                f"Assessment Failed"
                f"</div>",
                unsafe_allow_html=True
            )
            
            self.status_details.markdown(
                f"<div style='color: #A0A0A0; font-size: 0.9em;'>"
                f"Process terminated after {total_time:.1f} seconds"
                f"</div>",
                unsafe_allow_html=True
            )
            
        # Display step logs with clean styling
        if self.steps_completed:
            step_log_html = "<div style='margin-top: 20px; margin-bottom: 20px;'>"
            step_log_html += "<h4>Processing Steps</h4>"
            step_log_html += "<div style='background-color: #1F2937; border-radius: 5px; padding: 15px;'>"
            
            for stage, duration in self.steps_completed:
                if not stage:
                    continue
                    
                emoji = STAGE_EMOJIS.get(stage, "🔄")
                description = STAGE_DESCRIPTIONS.get(stage, stage.replace("_", " ").title())
                
                step_log_html += f"<div style='display: flex; align-items: center; margin-bottom: 8px;'>"
                step_log_html += f"<div style='margin-right: 10px;'>{emoji}</div>"
                step_log_html += f"<div style='flex-grow: 1;'><b>{description}</b></div>"
                step_log_html += f"<div style='color: #A0A0A0;'>{duration:.1f}s</div>"
                step_log_html += "</div>"
                
            step_log_html += "</div></div>"
            
            self.step_logs.markdown(step_log_html, unsafe_allow_html=True)
            
    def reset(self):
        """Reset progress tracking."""
        self.progress_bar.progress(0)
        self.icon_container.empty()
        self.status_container.empty()
        self.status_details.empty()
        self.step_logs.empty()
        self.progress_value = 0.0
        self.current_step = 0
        self.steps_completed = []
        self.current_stage = None
        self.start_time = time.time()
        self.stop_animation = False


class StrategyExecutorProgress:
    """
    Progress tracker specifically for Strategy Executor.
    """
    
    def __init__(self, executor):
        """
        Initialize progress tracker for Strategy Executor.
        
        Args:
            executor: StrategyExecutor instance
        """
        self.executor = executor
        self.progress = EnhancedProgress()
        self.stop_tracking = False
        self.tracking_thread = None
        
    def start_tracking(self):
        """Start tracking progress from executor."""
        self.stop_tracking = False
        self.tracking_thread = threading.Thread(target=self._track_progress)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
    def _track_progress(self):
        """Track progress from executor context."""
        while not self.stop_tracking:
            if hasattr(self.executor, "context"):
                progress = self.executor.context.progress
                current_stage = self.executor.context.current_stage or "initializing"
                
                # Get stage data
                stage_data = self.executor.context.stages.get(current_stage, {})
                message = stage_data.get("message", f"Processing {current_stage}")
                
                # Update progress
                self.progress.update_progress(
                    progress,
                    stage=current_stage,
                    message=message
                )
                
                # Check if done
                if progress >= 1.0:
                    self.stop_tracking = True
                    
                    # Check for errors
                    has_errors = len(self.executor.context.data.get("errors", [])) > 0
                    self.progress.complete(not has_errors)
                    break
                    
            time.sleep(0.5)
            
    def stop(self):
        """Stop tracking progress."""
        self.stop_tracking = True
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join()


def create_executor_progress_tracker(executor) -> StrategyExecutorProgress:
    """
    Create a progress tracker for a Strategy Executor.
    
    Args:
        executor: StrategyExecutor instance
        
    Returns:
        Progress tracker
    """
    return StrategyExecutorProgress(executor)


def display_stage_progress(stages: Dict[str, Dict[str, Any]]):
    """
    Display progress for multiple stages.
    
    Args:
        stages: Dictionary of stage data
    """
    if not stages:
        return
    
    stages_md = "### Processing Stages\n"
    
    for stage_name, stage_data in stages.items():
        status = stage_data.get("status", "pending")
        progress = stage_data.get("progress", 0.0)
        message = stage_data.get("message", "")
        
        emoji = "✅" if status == "completed" else "❌" if status == "failed" else "🔄"
        
        stage_display = stage_name.replace("_", " ").title()
        progress_display = f"{progress:.0%}"
        
        stages_md += f"- {emoji} **{stage_display}** ({progress_display}) - {message}\n"
    
    st.markdown(stages_md)


def create_multi_stage_progress(stages: List[str]) -> Dict[str, Any]:
    """
    Create a multi-stage progress tracker.
    
    Args:
        stages: List of stage names
        
    Returns:
        Progress tracking components
    """
    progress_bar = st.progress(0)
    status = st.empty()
    details = st.empty()
    
    return {
        "progress_bar": progress_bar,
        "status": status,
        "details": details,
        "stages": stages,
        "current_stage_idx": 0,
        "stage_progress": {stage: 0.0 for stage in stages}
    }


def update_multi_stage_progress(
    tracker: Dict[str, Any], 
    stage: str, 
    progress: float, 
    message: Optional[str] = None
):
    """
    Update multi-stage progress tracker.
    
    Args:
        tracker: Progress tracker
        stage: Current stage
        progress: Progress for current stage (0.0-1.0)
        message: Optional status message
    """
    stages = tracker["stages"]
    
    if stage in stages:
        # Update stage progress
        tracker["stage_progress"][stage] = progress
        
        # Calculate overall progress
        stage_idx = stages.index(stage)
        tracker["current_stage_idx"] = stage_idx
        
        overall_progress = (stage_idx + progress) / len(stages)
        tracker["progress_bar"].progress(overall_progress)
        
        # Update status
        emoji = STAGE_EMOJIS.get(stage, "🔄")
        description = STAGE_DESCRIPTIONS.get(stage, stage.replace("_", " ").title())
        
        tracker["status"].markdown(f"### {emoji} {description}")
        
        if message:
            tracker["details"].markdown(f"**{message}**")
        else:
            tracker["details"].markdown(f"**Progress: {progress:.0%}**")


def stage_completion_animation(
    stage: str, 
    message: str = "Stage completed", 
    duration: float = 2.0
):
    """
    Show a completion animation for a stage.
    
    Args:
        stage: Stage name
        message: Completion message
        duration: Animation duration in seconds
    """
    emoji = STAGE_EMOJIS.get(stage, "✅")
    container = st.empty()
    
    for i in range(10):
        # Pulsing animation
        size = 2 + 0.2 * (5 - abs(i - 5))  # Pulse effect
        container.markdown(
            f"<h2 style='text-align: center; transform: scale({size}); transition: transform 0.2s;'>"
            f"{emoji}</h2>"
            f"<p style='text-align: center;'>{message}</p>",
            unsafe_allow_html=True
        )
        time.sleep(duration / 10)
    
    time.sleep(0.5)
    container.empty()


def agent_status_display(agent_states: Dict[str, Dict[str, Any]]):
    """
    Display status for multiple agents.
    
    Args:
        agent_states: Dictionary of agent states
    """
    if not agent_states:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Agent Status")
        
        for agent_name, state in agent_states.items():
            status = state.get("status", "idle")
            progress = state.get("progress", 0.0)
            
            emoji = "✅" if status == "completed" else "❌" if status == "failed" else "🔄"
            
            st.markdown(
                f"- {emoji} **{agent_name}**: {status.title()} ({progress:.0%})"
            )
    
    with col2:
        st.markdown("### Agent Metrics")
        
        for agent_name, state in agent_states.items():
            tokens = state.get("tokens", 0)
            time_spent = state.get("time", 0.0)
            
            st.markdown(
                f"- **{agent_name}**: {tokens:,} tokens, {time_spent:.1f}s"
            )


def animated_agent_cards(agent_states: Dict[str, Dict[str, Any]]):
    """
    Display animated cards for agent status.
    
    Args:
        agent_states: Dictionary of agent states
    """
    if not agent_states:
        return
    
    # CSS for pulsing animation
    st.markdown(
        """
        <style>
        @keyframes pulse {
            0% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(79, 139, 249, 0.7);
            }
            
            70% {
                transform: scale(1);
                box-shadow: 0 0 0 10px rgba(79, 139, 249, 0);
            }
            
            100% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(79, 139, 249, 0);
            }
        }
        
        .active-agent {
            animation: pulse 2s infinite;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Create a row of agent cards
    cols = st.columns(len(agent_states))
    
    for i, (agent_name, state) in enumerate(agent_states.items()):
        status = state.get("status", "idle")
        progress = state.get("progress", 0.0)
        
        with cols[i]:
            # Choose emoji
            emoji = STAGE_EMOJIS.get(agent_name.lower(), "🤖")
            
            # Choose color and animation
            if status == "running":
                color = "#4F8BF9"
                animation_class = "active-agent"
            elif status == "completed":
                color = "#00CC96"
                animation_class = ""
            elif status == "failed":
                color = "#FF6B6B"
                animation_class = ""
            else:
                color = "#8D99AE"
                animation_class = ""
            
            # Create card
            st.markdown(
                f"""
                <div class="rating-card {animation_class}" style="border-left-color: {color};">
                    <div style="text-align: center; font-size: 2rem;">{emoji}</div>
                    <div style="text-align: center; font-weight: 600;">{agent_name}</div>
                    <div style="text-align: center;">{status.title()}</div>
                    <div style="margin-top: 10px;">
                        <div style="height: 6px; background-color: #e0e0e0; border-radius: 3px;">
                            <div style="height: 100%; width: {progress * 100}%; 
                                background-color: {color}; border-radius: 3px;">
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )