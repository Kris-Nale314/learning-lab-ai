"""
Professional Progress Tracking for Framework Assessment Workbench

A clean, professional progress tracking system that clearly shows
assessment phases and provides meaningful status updates.
"""

import streamlit as st
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Union

# Stage icons and descriptions
ASSESSMENT_PHASES = {
    "planning": {
        "icon": "🧠",
        "title": "Designing Assessment Strategy",
        "description": "Analyzing document and framework to create optimal assessment plan"
    },
    "chunking": {
        "icon": "✂️",
        "title": "Document Processing",
        "description": "Dividing document into meaningful sections for analysis"
    },
    "extractor_processing": {
        "icon": "🔍",
        "title": "Evidence Extraction",
        "description": "Finding and categorizing evidence for each assessment criterion"
    },
    "evaluator_processing": {
        "icon": "⚖️",
        "title": "Evaluation",
        "description": "Analyzing evidence to determine ratings for each criterion"
    },
    "reporter_processing": {
        "icon": "📊",
        "title": "Report Generation",
        "description": "Creating structured assessment reports and visualizations"
    }
}

# Specific stage details
STAGE_INFO = {
    # Planning stages
    "document_analysis": {
        "phase": "planning",
        "title": "Document Analysis",
        "description": "Understanding document content and structure"
    },
    "framework_analysis": {
        "phase": "planning",
        "title": "Framework Analysis",
        "description": "Assessing framework dimensions and criteria"
    },
    "strategy_design": {
        "phase": "planning",
        "title": "Strategy Design", 
        "description": "Creating agent deployment and processing plan"
    },
    
    # Evidence stages
    "evidence_extraction": {
        "phase": "extractor_processing",
        "title": "Evidence Extraction",
        "description": "Finding relevant content in document"
    },
    "evidence_categorization": {
        "phase": "extractor_processing",
        "title": "Evidence Categorization",
        "description": "Analyzing evidence relevance and significance"
    },
    "evidence_consolidation": {
        "phase": "extractor_processing",
        "title": "Evidence Consolidation",
        "description": "Organizing evidence for each criterion"
    },
    
    # Evaluation stages
    "criterion_evaluation": {
        "phase": "evaluator_processing",
        "title": "Criterion Evaluation",
        "description": "Assessing individual criteria based on evidence"
    },
    "dimension_summarization": {
        "phase": "evaluator_processing",
        "title": "Dimension Summarization",
        "description": "Creating summaries for each dimension"
    },
    "overall_assessment": {
        "phase": "evaluator_processing",
        "title": "Overall Assessment",
        "description": "Generating comprehensive assessment"
    },
    
    # Report stages
    "scorecard_generation": {
        "phase": "reporter_processing",
        "title": "Scorecard Generation",
        "description": "Creating structured assessment scorecard"
    },
    "visualization_preparation": {
        "phase": "reporter_processing",
        "title": "Visualization Preparation",
        "description": "Preparing data for visualization"
    },
    "report_compilation": {
        "phase": "reporter_processing",
        "title": "Report Compilation",
        "description": "Compiling final assessment outputs"
    }
}


class ProfessionalProgressTracker:
    """
    Professional progress tracking with clean UI and phase highlighting.
    """
    
    def __init__(self, show_header=False):
        """
        Initialize the progress tracker with a professional UI.
        
        Args:
            show_header: Whether to show the "Assessment Progress" header
        """
        # Create containers for each component
        self.progress_container = st.container()
        self.show_header = show_header
                
        with self.progress_container:
            # Set up the main progress display
            self.progress_bar = st.progress(0)
            
            # Current phase and stage
            cols = st.columns([1, 4])
            with cols[0]:
                self.phase_icon = st.empty()
            with cols[1]:
                self.phase_container = st.empty()
                
            # Status message
            self.status_container = st.empty()
            
            # Detailed phase tracking
            self.phases_container = st.empty()
            
        # Initialize tracking variables
        self.current_phase = None
        self.current_stage = None
        self.phase_progress = {}
        self.phase_start_times = {}
        self.phase_completed = set()
        self.progress_value = 0.0
        self.start_time = time.time()
        self.phase_stages = {}
        
        # Phase weights for progress calculation
        self.phase_weights = {
            "planning": 0.15,
            "chunking": 0.10,
            "extractor_processing": 0.40,
            "evaluator_processing": 0.25,
            "reporter_processing": 0.10
        }
        
        # Initialize phase progress tracking
        for phase in ASSESSMENT_PHASES:
            self.phase_progress[phase] = 0.0
            self.phase_stages[phase] = []
        
        # Animation thread control
        self.animation_thread = None
        self.stop_animation = False
    
    def update(self, stage: str, progress: float, message: Optional[str] = None):
        """
        Update the progress display with current stage and message.
        
        Args:
            stage: Current processing stage
            progress: Progress value (0.0-1.0)
            message: Optional status message
        """
        # Get phase for this stage
        phase = self._get_phase_for_stage(stage)
        
        # Track stage in phase
        if stage not in self.phase_stages[phase]:
            self.phase_stages[phase].append(stage)
        
        # Update phase progress
        self.phase_progress[phase] = progress
        
        # Calculate overall progress based on phase weights
        overall_progress = self._calculate_overall_progress()
        self.progress_value = overall_progress
        self.progress_bar.progress(overall_progress)
        
        # Update phase tracking if phase changed
        if phase != self.current_phase:
            self._update_phase_display(phase)
        
        # Update stage display
        self._update_stage_display(stage, progress, message)
        
        # Update phase tracking dashboard
        self._update_phase_tracking()
    
    def _get_phase_for_stage(self, stage: str) -> str:
        """
        Determine which assessment phase a stage belongs to.
        
        Args:
            stage: Stage name
            
        Returns:
            Phase name
        """
        # Check if stage is in STAGE_INFO
        if stage in STAGE_INFO:
            return STAGE_INFO[stage]["phase"]
        
        # Check if stage directly matches a phase
        if stage in ASSESSMENT_PHASES:
            return stage
        
        # Default mapping based on naming patterns
        if "planning" in stage or "strategy" in stage:
            return "planning"
        elif "chunk" in stage:
            return "chunking"
        elif "extract" in stage:
            return "extractor_processing"
        elif "evaluat" in stage:
            return "evaluator_processing"
        elif "report" in stage:
            return "reporter_processing"
        
        # Default to planning as fallback
        return "planning"
    
    def _calculate_overall_progress(self) -> float:
        """
        Calculate overall progress based on phase weights.
        
        Returns:
            Overall progress (0.0-1.0)
        """
        weighted_progress = 0.0
        weight_sum = 0.0
        
        for phase, weight in self.phase_weights.items():
            weighted_progress += self.phase_progress.get(phase, 0.0) * weight
            weight_sum += weight
        
        # Normalize to ensure we're within 0.0-1.0
        if weight_sum > 0:
            return min(1.0, weighted_progress / weight_sum)
        return 0.0
    
    def _update_phase_display(self, phase: str):
        """
        Update the display for a new active phase.
        
        Args:
            phase: New active phase
        """
        if phase == self.current_phase:
            return
            
        # Record start time for new phase
        if phase not in self.phase_start_times:
            self.phase_start_times[phase] = time.time()
        
        # Mark previous phase as completed if applicable
        if self.current_phase and self.current_phase not in self.phase_completed:
            self.phase_completed.add(self.current_phase)
        
        # Update current phase
        self.current_phase = phase
        
        # Get phase info
        phase_info = ASSESSMENT_PHASES.get(phase, {
            "icon": "🔄",
            "title": phase.replace("_", " ").title(),
            "description": "Processing..."
        })
        
        # Update phase display
        self.phase_icon.markdown(
            f"<div style='font-size: 2.5rem; text-align: center;'>{phase_info['icon']}</div>", 
            unsafe_allow_html=True
        )
        
        self.phase_container.markdown(
            f"<div style='font-size: 1.2rem; font-weight: 600;'>{phase_info['title']}</div>"
            f"<div style='color: #A0A0A0; font-size: 0.9rem;'>{phase_info['description']}</div>",
            unsafe_allow_html=True
        )
    
    def _update_stage_display(self, stage: str, progress: float, message: Optional[str] = None):
        """
        Update display for the current stage.
        
        Args:
            stage: Current stage
            progress: Stage progress
            message: Optional status message
        """
        self.current_stage = stage
        
        # Get stage info
        stage_info = STAGE_INFO.get(stage, {
            "title": stage.replace("_", " ").title(),
            "description": "Processing..."
        })
        
        # Use provided message or default to stage description
        display_message = message or stage_info.get("description", "")
        
        # Update status display
        self.status_container.markdown(
            f"<div style='margin-top: 10px; background-color: #1E1E1E; padding: 10px; border-radius: 5px;'>"
            f"<div style='font-weight: 500;'>{stage_info.get('title', stage)}</div>"
            f"<div style='color: #A0A0A0; font-size: 0.9rem;'>{display_message}</div>"
            f"<div style='color: #A0A0A0; font-size: 0.8rem; text-align: right;'>{progress:.0%}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    def _update_phase_tracking(self):
        """Update the phase tracking dashboard."""
        # Create phase tracking display
        tracking_html = "<div style='margin-top: 20px;'>"
        
        # Only add header if configured to show it
        if self.show_header:
            tracking_html += "<h4>Assessment Progress</h4>"
        
        tracking_html += "<div style='margin-top: 10px;'>"
        
        # Generate phase blocks
        for phase, info in ASSESSMENT_PHASES.items():
            # Determine phase status
            if phase == self.current_phase:
                status = "active"
                bg_color = "#2C3E50"  # Dark blue for active
                progress = self.phase_progress.get(phase, 0.0)
            elif phase in self.phase_completed:
                status = "completed"
                bg_color = "#27AE60"  # Green for completed
                progress = 1.0
            else:
                status = "pending"
                bg_color = "#34495E"  # Darker gray for pending
                progress = 0.0
            
            # Calculate elapsed time if applicable
            time_display = ""
            if phase in self.phase_start_times:
                if status == "completed":
                    # Find the next phase start time 
                    next_phases = [p for p in self.phase_stages.keys() 
                                  if p in self.phase_start_times and 
                                  self.phase_start_times[p] > self.phase_start_times[phase]]
                    
                    if next_phases:
                        next_phase = min(next_phases, key=lambda p: self.phase_start_times[p])
                        duration = self.phase_start_times[next_phase] - self.phase_start_times[phase]
                    else:
                        duration = time.time() - self.phase_start_times[phase]
                        
                    time_display = f"{duration:.1f}s"
                elif status == "active":
                    elapsed = time.time() - self.phase_start_times[phase]
                    time_display = f"{elapsed:.1f}s"
            
            # Create phase block
            tracking_html += f"""
            <div style='margin-bottom: 12px; background-color: {bg_color}; 
                       border-radius: 5px; padding: 10px; position: relative;'>
                <div style='display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center;'>
                        <div style='font-size: 1.2rem; margin-right: 10px;'>{info['icon']}</div>
                        <div>
                            <div style='font-weight: 500;'>{info['title']}</div>
                            <div style='color: #A0A0A0; font-size: 0.8rem;'>{info['description']}</div>
                        </div>
                    </div>
                    <div style='text-align: right;'>
                        <div style='font-weight: 500;'>{progress:.0%}</div>
                        <div style='color: #A0A0A0; font-size: 0.8rem;'>{time_display}</div>
                    </div>
                </div>
                
                <div style='margin-top: 8px; height: 4px; background-color: rgba(255, 255, 255, 0.1); border-radius: 2px;'>
                    <div style='height: 100%; width: {progress * 100}%; background-color: rgba(255, 255, 255, 0.7); 
                              border-radius: 2px;'></div>
                </div>
            </div>
            """
        
        tracking_html += "</div></div>"
        
        # Update the phases container
        self.phases_container.markdown(tracking_html, unsafe_allow_html=True)
    
    def complete(self, success: bool = True):
        """
        Mark the progress as complete.
        
        Args:
            success: Whether the process completed successfully
        """
        # Update progress to 100%
        self.progress_bar.progress(1.0)
        
        # Calculate total time
        total_time = time.time() - self.start_time
        
        # Update phase display based on success
        if success:
            self.phase_icon.markdown(
                f"<div style='font-size: 2.5rem; text-align: center;'>✅</div>", 
                unsafe_allow_html=True
            )
            
            self.phase_container.markdown(
                f"<div style='font-size: 1.2rem; font-weight: 600;'>Assessment Complete</div>"
                f"<div style='color: #A0A0A0; font-size: 0.9rem;'>All processing stages completed successfully</div>",
                unsafe_allow_html=True
            )
            
            self.status_container.markdown(
                f"<div style='margin-top: 10px; background-color: #27AE60; padding: 10px; border-radius: 5px;'>"
                f"<div style='font-weight: 500; color: white;'>Assessment Completed Successfully</div>"
                f"<div style='color: rgba(255, 255, 255, 0.8); font-size: 0.9rem;'>Total processing time: {total_time:.1f} seconds</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            self.phase_icon.markdown(
                f"<div style='font-size: 2.5rem; text-align: center;'>❌</div>", 
                unsafe_allow_html=True
            )
            
            self.phase_container.markdown(
                f"<div style='font-size: 1.2rem; font-weight: 600;'>Assessment Failed</div>"
                f"<div style='color: #A0A0A0; font-size: 0.9rem;'>An error occurred during processing</div>",
                unsafe_allow_html=True
            )
            
            self.status_container.markdown(
                f"<div style='margin-top: 10px; background-color: #C0392B; padding: 10px; border-radius: 5px;'>"
                f"<div style='font-weight: 500; color: white;'>Assessment Failed</div>"
                f"<div style='color: rgba(255, 255, 255, 0.8); font-size: 0.9rem;'>Process terminated after {total_time:.1f} seconds</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        # Mark all active phases as completed
        if self.current_phase and self.current_phase not in self.phase_completed:
            self.phase_completed.add(self.current_phase)
        
        # Final update to phase tracking
        self._update_phase_tracking()


class ExecutorProgressTracker:
    """
    Progress tracker for Strategy Executor that uses the ProfessionalProgressTracker.
    """
    
    def __init__(self, executor):
        self.executor = executor
        self.progress = ProfessionalProgressTracker()
        self._stop_tracking_flag = False  # Renamed to avoid confusion
        self.tracking_thread = None
        
    def start_tracking(self):
        """Start tracking progress from the executor."""
        self._stop_tracking_flag = False
        self.tracking_thread = threading.Thread(target=self._track_progress)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
    def _track_progress(self):
        """Track progress from executor context."""
        while not self._stop_tracking_flag:
            if hasattr(self.executor, "context"):
                # Rest of the method...
                time.sleep(0.5)
            
    def stop(self):
        """Stop tracking progress."""
        self._stop_tracking_flag = True
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join()
    
    # Add an alias for backward compatibility
    def stop_tracking(self):
        """Alias for stop() method."""
        self.stop()

def create_executor_progress_tracker(executor, show_header=False) -> ExecutorProgressTracker:
    """
    Create a progress tracker for a Strategy Executor.
    
    Args:
        executor: StrategyExecutor instance
        show_header: Whether to show the "Assessment Progress" header
        
    Returns:
        Progress tracker
    """
    tracker = ExecutorProgressTracker(executor)
    tracker.progress.show_header = show_header
    return tracker


def create_standalone_tracker() -> ProfessionalProgressTracker:
    """
    Create a standalone progress tracker for any process.
    
    Returns:
        Progress tracker instance
    """
    return ProfessionalProgressTracker()