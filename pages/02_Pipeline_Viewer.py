"""
02_Pipeline_Viewer - Inspect the assessment pipeline execution

This page provides detailed visibility into the assessment pipeline,
showing intermediate outputs, agent instructions, and context flow.
"""

import os
import sys
import json
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

# Ensure core modules are in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities
from utils import path_utils
from utils import ui_components
from utils import ui_styles

# Configure the page
st.set_page_config(
    page_title="Pipeline Viewer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom styles
ui_styles.apply_styles()

# Add custom CSS for pipeline visualization
st.markdown("""
<style>
/* Pipeline flow visualization */
.pipeline-flow {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin: 20px 0;
}

.pipeline-stage {
    background-color: #1F2937;
    border-radius: 8px;
    padding: 15px;
    border: 1px solid #3B4252;
    transition: all 0.3s ease;
}

.pipeline-stage:hover {
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    transform: translateY(-2px);
}

.stage-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    border-bottom: 1px solid rgba(59, 66, 82, 0.5);
    padding-bottom: 10px;
}

.stage-name {
    font-weight: 600;
    font-size: 1.1rem;
    color: #E0E0E0;
}

.stage-status {
    font-size: 0.9rem;
    padding: 3px 10px;
    border-radius: 12px;
}

.stage-complete {
    background-color: #00CC96;
    color: white;
}

.stage-running {
    background-color: #4F8BF9;
    color: white;
    animation: pulse 2s infinite;
}

.stage-pending {
    background-color: #888888;
    color: white;
}

.stage-error {
    background-color: #FF6B6B;
    color: white;
}

.stage-content {
    font-size: 0.9rem;
    color: #A0A0A0;
}

.stage-arrow {
    display: flex;
    justify-content: center;
    color: #4F8BF9;
    font-size: 1.5rem;
    margin: 5px 0;
}

/* Prompt display */
.prompt-display {
    background-color: #2E3440;
    border-radius: 8px;
    padding: 15px;
    font-family: monospace;
    white-space: pre-wrap;
    overflow-x: auto;
    color: #D8DEE9;
    border: 1px solid #3B4252;
}

/* Response display */
.response-display {
    background-color: #2E3440;
    border-radius: 8px;
    padding: 15px;
    font-family: monospace;
    white-space: pre-wrap;
    overflow-x: auto;
    color: #A3BE8C;
    border: 1px solid #3B4252;
}

/* Evidence item styling */
.evidence-item {
    background-color: #2E3440;
    border-left: 4px solid #4F8BF9;
    padding: 12px;
    margin-bottom: 10px;
    border-radius: 0 8px 8px 0;
}

.evidence-text {
    font-style: italic;
    color: #E0E0E0;
    margin-bottom: 8px;
}

.evidence-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: #A0A0A0;
}

/* Decision point visualization */
.decision-point {
    background-color: #4C566A;
    border-radius: 8px;
    padding: 15px;
    margin: 15px 0;
    border: 1px solid #3B4252;
}

.decision-header {
    font-weight: 600;
    color: #E0E0E0;
    margin-bottom: 10px;
    border-bottom: 1px solid rgba(59, 66, 82, 0.5);
    padding-bottom: 10px;
}

.decision-options {
    display: flex;
    gap: 10px;
    margin-top: 10px;
}

.decision-option {
    flex: 1;
    background-color: #2E3440;
    padding: 10px;
    border-radius: 8px;
    font-size: 0.9rem;
    color: #A0A0A0;
}

.selected-option {
    border: 2px solid #4F8BF9;
    background-color: rgba(79, 139, 249, 0.1);
}

/* Agent card styling */
.agent-card {
    background-color: #1F2937;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
    border: 1px solid #3B4252;
    transition: all 0.3s ease;
}

.agent-card:hover {
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    transform: translateY(-2px);
}

.agent-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    border-bottom: 1px solid rgba(59, 66, 82, 0.5);
    padding-bottom: 10px;
}

.agent-type {
    font-weight: 600;
    font-size: 1.1rem;
    color: #E0E0E0;
    display: flex;
    align-items: center;
}

.agent-icon {
    margin-right: 8px;
    color: #4F8BF9;
    font-size: 1.2rem;
}

.agent-stats {
    display: flex;
    gap: 15px;
}

.agent-stat {
    background-color: #2E3440;
    padding: 8px 12px;
    border-radius: 5px;
    font-size: 0.9rem;
}

/* Code display */
.code-display {
    background-color: #2E3440;
    border-radius: 8px;
    padding: 15px;
    font-family: monospace;
    overflow-x: auto;
    color: #D8DEE9;
    margin: 10px 0;
    border: 1px solid #3B4252;
    position: relative;
}

.code-header {
    position: absolute;
    right: 10px;
    top: 10px;
    background-color: rgba(76, 86, 106, 0.7);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    color: #E0E0E0;
}

/* Animation for pulse */
@keyframes pulse {
    0% {
        opacity: 1;
    }
    50% {
        opacity: 0.7;
    }
    100% {
        opacity: 1;
    }
}
</style>
""", unsafe_allow_html=True)

def load_context_data(file_path: str) -> Dict[str, Any]:
    """
    Load execution context data from a file.
    
    Args:
        file_path: Path to the context data file
        
    Returns:
        Context data dictionary
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load context data: {str(e)}")
        return {}

def display_context_selection() -> Optional[Dict[str, Any]]:
    """
    Display a context selection interface.
    
    Returns:
        Selected context data or None if no context selected
    """
    st.markdown("## Select Assessment Execution to Analyze")
    
    # List context data files from the outputs directory
    context_files = path_utils.list_files("outputs", ".json")
    
    if not context_files:
        st.info("No execution logs found. Run an assessment first with pipeline logging enabled.")
        return None
    
    # Sort by modification time (newest first)
    context_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    # Create selection options
    file_options = []
    for file_path in context_files:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        file_size = file_path.stat().st_size / 1024  # Size in KB
        
        # Try to extract basic metadata
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                metadata = data.get("metadata", {})
                framework_name = metadata.get("framework_name", "Unknown Framework")
                document_name = metadata.get("document_name", "Unknown Document")
        except:
            framework_name = "Unknown Framework"
            document_name = "Unknown Document"
        
        file_options.append({
            "path": file_path,
            "name": f"{framework_name} - {document_name} ({mtime.strftime('%Y-%m-%d %H:%M')})",
            "framework": framework_name,
            "document": document_name,
            "date": mtime.strftime("%Y-%m-%d %H:%M"),
            "size": f"{file_size:.1f} KB"
        })
    
    # Create selection UI
    col1, col2 = st.columns([3, 1])
    
    with col1:
        option_labels = [option["name"] for option in file_options]
        selected_index = st.selectbox(
            "Select execution log to view",
            options=range(len(option_labels)),
            format_func=lambda i: option_labels[i]
        )
    
    with col2:
        st.write("")
        st.write("")
        load_button = st.button("Load Execution Log", key="load_context_btn", type="primary")
    
    if load_button:
        selected_path = file_options[selected_index]["path"]
        try:
            # Load the selected context
            context_data = load_context_data(selected_path)
            
            # Store in session state
            st.session_state.pipeline_context = context_data
            st.session_state.pipeline_context_path = selected_path
            
            st.success(f"Loaded execution log: {file_options[selected_index]['name']}")
            return context_data
        except Exception as e:
            st.error(f"Failed to load execution log: {str(e)}")
            return None
    
    # Return from session state if available
    if "pipeline_context" in st.session_state:
        return st.session_state.pipeline_context
    
    return None

def display_pipeline_overview(context_data: Dict[str, Any]):
    """
    Display a high-level overview of the pipeline execution.
    
    Args:
        context_data: Pipeline context data
    """
    st.markdown("## Pipeline Execution Overview")
    
    # Extract basic metadata
    metadata = context_data.get("metadata", {})
    strategy = context_data.get("strategy", {})
    
    # Create overview metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        framework_name = metadata.get("framework_name", "Unknown Framework")
        document_name = metadata.get("document_name", "Unknown Document")
        
        st.metric("Framework", framework_name)
        st.metric("Document", document_name)
    
    with col2:
        execution_time = context_data.get("execution_time", 0)
        execution_time_str = f"{execution_time:.1f} seconds" if execution_time else "Unknown"
        
        stages = context_data.get("stages", {})
        stage_count = len(stages)
        
        st.metric("Execution Time", execution_time_str)
        st.metric("Pipeline Stages", stage_count)
    
    with col3:
        agent_count = len(context_data.get("agents", []))
        api_calls = context_data.get("api_call_count", 0)
        
        st.metric("Agents Used", agent_count)
        st.metric("API Calls", api_calls)
    
    # Display execution status
    execution_status = context_data.get("status", "unknown")
    current_stage = context_data.get("current_stage", "")
    progress = context_data.get("progress", 0)
    
    status_color = "#888888"  # Default gray
    if execution_status == "complete":
        status_color = "#00CC96"  # Green
    elif execution_status == "running":
        status_color = "#4F8BF9"  # Blue
    elif execution_status == "error":
        status_color = "#FF6B6B"  # Red
    
    st.markdown(
        f"""
        <div style="padding: 15px; background-color: rgba({int(status_color[1:3], 16)}, {int(status_color[3:5], 16)}, {int(status_color[5:7], 16)}, 0.1); 
             border-left: 4px solid {status_color}; border-radius: 8px; margin: 15px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="font-weight: 600; font-size: 1.1rem;">
                    Execution Status: <span style="color: {status_color};">{execution_status.title()}</span>
                </div>
                <div>{progress * 100:.1f}% Complete</div>
            </div>
            <div style="height: 8px; background-color: rgba(255, 255, 255, 0.1); border-radius: 4px; margin-bottom: 10px;">
                <div style="height: 100%; width: {progress * 100}%; background-color: {status_color}; border-radius: 4px;"></div>
            </div>
            <div style="color: #A0A0A0; font-size: 0.9rem;">
                Current Stage: {current_stage if current_stage else "None"}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Display strategy overview
    if strategy:
        st.markdown("### Strategy Information")
        
        strategy_type = strategy.get("strategy_type", "Unknown")
        agent_types = [agent.get("agent_type", "unknown") for agent in strategy.get("agents", [])]
        
        # Count agent types
        agent_counts = {}
        for agent_type in agent_types:
            if agent_type not in agent_counts:
                agent_counts[agent_type] = 0
            agent_counts[agent_type] += 1
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Strategy Type:** {strategy_type}")
            
            if "processing_sequence" in strategy:
                st.markdown("**Processing Sequence:**")
                sequence = strategy["processing_sequence"]
                
                # Create a visual sequence
                sequence_html = '<div style="display: flex; flex-wrap: wrap; align-items: center; margin-top: 10px;">'
                
                for i, step in enumerate(sequence):
                    # Add arrow between steps
                    if i > 0:
                        sequence_html += '<div style="margin: 0 10px; color: #4F8BF9;">→</div>'
                    
                    # Add step with styling
                    sequence_html += f'<div style="background-color: #2E3440; padding: 8px 15px; border-radius: 15px;">{step}</div>'
                
                sequence_html += '</div>'
                st.markdown(sequence_html, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Agent Types:**")
            
            agent_html = '<div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;">'
            
            for agent_type, count in agent_counts.items():
                agent_html += f"""
                <div style="background-color: #2E3440; padding: 8px 15px; border-radius: 15px; display: flex; align-items: center;">
                    <div style="margin-right: 8px; background-color: #4F8BF9; color: white; 
                         width: 22px; height: 22px; border-radius: 50%; display: flex; 
                         justify-content: center; align-items: center; font-size: 0.8rem;">
                        {count}
                    </div>
                    <div>{agent_type}</div>
                </div>
                """
            
            agent_html += '</div>'
            st.markdown(agent_html, unsafe_allow_html=True)

def display_pipeline_flow(context_data: Dict[str, Any]):
    """
    Display the pipeline flow with stage details.
    
    Args:
        context_data: Pipeline context data
    """
    st.markdown("## Pipeline Flow Visualization")
    
    # Get stages from context
    stages = context_data.get("stages", {})
    current_stage = context_data.get("current_stage", "")
    
    if not stages:
        st.info("No pipeline stages found in this execution log.")
        return
    
    # Get execution status
    execution_status = context_data.get("status", "unknown")
    completed_stages = context_data.get("completed_stages", [])
    
    # Determine stage sequence
    stage_sequence = context_data.get("stage_sequence", list(stages.keys()))
    
    # If no explicit sequence, create from stages dictionary
    if not stage_sequence:
        # Try to determine a logical order if not provided
        # This is a heuristic and might not reflect the actual execution order
        known_stages = [
            "initialization",
            "strategy_planning",
            "document_analysis",
            "chunking",
            "evidence_extraction",
            "evidence_categorization",
            "criteria_evaluation",
            "dimension_summarization",
            "overall_assessment",
            "report_generation",
            "finalization"
        ]
        
        # First include stages in known order
        ordered_stages = [stage for stage in known_stages if stage in stages]
        
        # Then add any remaining stages
        for stage in stages:
            if stage not in ordered_stages:
                ordered_stages.append(stage)
        
        stage_sequence = ordered_stages
    
    # Start pipeline visualization
    st.markdown('<div class="pipeline-flow">', unsafe_allow_html=True)
    
    for i, stage_id in enumerate(stage_sequence):
        # Skip if stage not in stages dict
        if stage_id not in stages:
            continue
        
        stage = stages[stage_id]
        stage_name = stage.get("name", stage_id)
        stage_description = stage.get("description", "")
        stage_message = stage.get("message", "")
        
        # Determine stage status
        if stage_id in completed_stages:
            status = "complete"
            status_text = "Complete"
        elif stage_id == current_stage:
            status = "running"
            status_text = "Running"
        elif execution_status == "error" and stage_id == current_stage:
            status = "error"
            status_text = "Error"
        else:
            status = "pending"
            status_text = "Pending"
        
        # Create stage card
        st.markdown(
            f"""
            <div class="pipeline-stage">
                <div class="stage-header">
                    <div class="stage-name">{stage_name}</div>
                    <div class="stage-status stage-{status}">{status_text}</div>
                </div>
                <div class="stage-content">
                    <div>{stage_description}</div>
                    <div style="margin-top: 5px;">{stage_message}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Add arrow between stages
        if i < len(stage_sequence) - 1:
            st.markdown('<div class="stage-arrow">↓</div>', unsafe_allow_html=True)
    
    # End pipeline visualization
    st.markdown('</div>', unsafe_allow_html=True)

def display_agent_execution(context_data: Dict[str, Any]):
    """
    Display agent execution details.
    
    Args:
        context_data: Pipeline context data
    """
    st.markdown("## Agent Execution Details")
    
    # Get agents from context
    agents = context_data.get("agents", [])
    
    if not agents:
        st.info("No agent execution details found in this log.")
        return
    
    # Create a tab for each agent type
    agent_types = set(agent.get("agent_type", "unknown") for agent in agents)
    agent_tabs = st.tabs([agent_type.title() for agent_type in sorted(agent_types)])
    
    # Map for tab index by agent type
    agent_type_to_tab = {agent_type: i for i, agent_type in enumerate(sorted(agent_types))}
    
    # Group agents by type
    agents_by_type = {}
    for agent in agents:
        agent_type = agent.get("agent_type", "unknown")
        if agent_type not in agents_by_type:
            agents_by_type[agent_type] = []
        agents_by_type[agent_type].append(agent)
    
    # Fill each tab with agent data
    for agent_type, agents_list in agents_by_type.items():
        tab_index = agent_type_to_tab.get(agent_type, 0)
        
        with agent_tabs[tab_index]:
            st.markdown(f"### {len(agents_list)} {agent_type.title()} Agents")
            
            for i, agent in enumerate(agents_list):
                agent_id = agent.get("id", f"agent-{i}")
                agent_status = agent.get("status", "unknown")
                agent_error = agent.get("error", None)
                
                # Get agent execution stats
                calls = agent.get("calls", [])
                execution_time = agent.get("execution_time", 0)
                execution_time_str = f"{execution_time:.1f}s" if execution_time else "N/A"
                
                # Determine status color and text
                status_color = "#888888"  # Default gray
                if agent_status == "complete":
                    status_color = "#00CC96"  # Green
                elif agent_status == "running":
                    status_color = "#4F8BF9"  # Blue
                elif agent_status == "error":
                    status_color = "#FF6B6B"  # Red
                
                # Determine agent icon based on type
                agent_icon = "🤖"  # Default robot
                if "extractor" in agent_type:
                    agent_icon = "🔍"  # Magnifying glass for extractors
                elif "evaluator" in agent_type:
                    agent_icon = "⚖️"  # Scales for evaluators
                elif "reporter" in agent_type:
                    agent_icon = "📊"  # Chart for reporters
                elif "planner" in agent_type:
                    agent_icon = "🧠"  # Brain for planners
                
                # Create agent card
                with st.expander(f"{agent_icon} {agent_type.title()} - {agent_id}", expanded=False):
                    st.markdown(
                        f"""
                        <div class="agent-card">
                            <div class="agent-header">
                                <div class="agent-type">
                                    <div class="agent-icon">{agent_icon}</div>
                                    {agent_type.title()} ({agent_id})
                                </div>
                                <div class="agent-stats">
                                    <div class="agent-stat">Status: <span style="color: {status_color};">{agent_status.title()}</span></div>
                                    <div class="agent-stat">Calls: {len(calls)}</div>
                                    <div class="agent-stat">Time: {execution_time_str}</div>
                                </div>
                            </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Show error if any
                    if agent_error:
                        st.markdown(
                            f"""
                            <div style="background-color: rgba(255, 107, 107, 0.1); border-left: 4px solid #FF6B6B; 
                                 padding: 15px; border-radius: 8px; margin: 15px 0;">
                                <div style="font-weight: 600; color: #FF6B6B; margin-bottom: 5px;">Error</div>
                                <div style="color: #E0E0E0;">{agent_error}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    
                    # Show agent configuration
                    if "configuration" in agent:
                        st.markdown("#### Configuration")
                        st.json(agent["configuration"])
                    
                    # Show agent inputs if available
                    if "inputs" in agent:
                        st.markdown("#### Inputs")
                        st.json(agent["inputs"])
                    
                    # Show agent outputs if available
                    if "outputs" in agent:
                        st.markdown("#### Outputs")
                        st.json(agent["outputs"])
                    
                    # Show agent calls (API interactions)
                    if calls:
                        st.markdown(f"#### API Calls ({len(calls)})")
                        
                        for j, call in enumerate(calls):
                            call_type = call.get("type", "unknown")
                            prompt = call.get("prompt", "")
                            response = call.get("response", "")
                            
                            with st.expander(f"Call {j+1}: {call_type}", expanded=False):
                                if prompt:
                                    st.markdown("**Prompt:**")
                                    st.markdown(f"<div class='prompt-display'>{prompt}</div>", unsafe_allow_html=True)
                                
                                if response:
                                    st.markdown("**Response:**")
                                    st.markdown(f"<div class='response-display'>{response}</div>", unsafe_allow_html=True)
                    
                    # Show processing details if relevant
                    if "processing_details" in agent:
                        st.markdown("#### Processing Details")
                        
                        details = agent["processing_details"]
                        if isinstance(details, dict):
                            st.json(details)
                        else:
                            st.write(details)
                    
                    st.markdown("</div>", unsafe_allow_html=True)

def display_evidence_collection(context_data: Dict[str, Any]):
    """
    Display evidence collection process and results.
    
    Args:
        context_data: Pipeline context data
    """
    st.markdown("## Evidence Collection Process")
    
    # Look for evidence extraction stage
    stages = context_data.get("stages", {})
    evidence_stage = None
    
    for stage_id, stage in stages.items():
        if "evidence" in stage_id.lower() and "extract" in stage_id.lower():
            evidence_stage = stage
            break
    
    if not evidence_stage:
        # Try to find evidence in outputs
        evidence_collection = None
        for agent in context_data.get("agents", []):
            if "extractor" in agent.get("agent_type", "").lower():
                if "outputs" in agent and "evidence" in agent["outputs"]:
                    evidence_collection = agent["outputs"]["evidence"]
                    break
        
        if not evidence_collection:
            st.info("No evidence collection process found in this execution log.")
            return
    
    # Check if we have evidence items in context data
    evidence_items = context_data.get("evidence_items", [])
    
    if not evidence_items:
        # Try to find in agent outputs
        for agent in context_data.get("agents", []):
            if "extractor" in agent.get("agent_type", "").lower():
                if "outputs" in agent and "evidence" in agent["outputs"]:
                    evidence_items = agent["outputs"]["evidence"]
                    break
    
    # If still not found, check for evidence in other locations
    if not evidence_items:
        # Try to find in results
        if "results" in context_data and "evidence" in context_data["results"]:
            evidence_items = context_data["results"]["evidence"]
    
    # Display evidence extraction progress
    if evidence_items:
        # Group by criterion
        evidence_by_criterion = {}
        
        for item in evidence_items:
            criterion_id = item.get("criterion_id", "unknown")
            if criterion_id not in evidence_by_criterion:
                evidence_by_criterion[criterion_id] = []
            evidence_by_criterion[criterion_id].append(item)
        
        # Display evidence statistics
        total_items = len(evidence_items)
        criteria_covered = len(evidence_by_criterion)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Evidence Items", total_items)
        
        with col2:
            st.metric("Criteria With Evidence", criteria_covered)
        
        with col3:
            items_per_criterion = total_items / max(1, criteria_covered)
            st.metric("Items Per Criterion", f"{items_per_criterion:.1f}")
        
        # Create bar chart of evidence per criterion
        evidence_counts = []
        for criterion_id, items in evidence_by_criterion.items():
            # Find criterion name in framework structure
            criterion_name = criterion_id
            for agent in context_data.get("agents", []):
                if "inputs" in agent and "framework" in agent["inputs"]:
                    framework = agent["inputs"]["framework"]
                    for dimension in framework.get("dimensions", []):
                        for criterion in dimension.get("criteria", []):
                            if criterion.get("id") == criterion_id:
                                criterion_name = criterion.get("name", criterion_id)
                                break
            
            evidence_counts.append({
                "criterion_id": criterion_id,
                "criterion_name": criterion_name,
                "count": len(items)
            })
        
        if evidence_counts:
            # Sort by count (descending)
            evidence_counts.sort(key=lambda x: x["count"], reverse=True)
            
            # Create dataframe
            df = pd.DataFrame(evidence_counts)
            
            # Create bar chart
            chart = alt.Chart(df).mark_bar().encode(
                y=alt.Y('criterion_name:N', sort='-x', title='Criterion'),
                x=alt.X('count:Q', title='Evidence Count'),
                color=alt.Color('count:Q', scale=alt.Scale(scheme='blueorange')),
                tooltip=['criterion_name:N', 'count:Q']
            ).properties(
                height=min(400, 30 * len(evidence_counts))
            )
            
            st.altair_chart(chart, use_container_width=True)
        
        # Sample evidence items
        st.markdown("### Sample Evidence Items")
        
        # Create a multi-select for filtering by criterion
        criterion_options = [f"{c['criterion_name']} ({c['count']} items)" for c in evidence_counts]
        criterion_map = {f"{c['criterion_name']} ({c['count']} items)": c["criterion_id"] for c in evidence_counts}
        
        selected_criteria = st.multiselect(
            "Filter by criterion",
            options=criterion_options,
            default=[]
        )
        
        # Filter evidence items by selected criteria
        filtered_items = evidence_items
        if selected_criteria:
            criterion_ids = [criterion_map[name] for name in selected_criteria]
            filtered_items = [item for item in evidence_items if item.get("criterion_id") in criterion_ids]
        
        # Display evidence items
        if filtered_items:
            # Limit to a reasonable number for display
            display_items = filtered_items[:20]
            
            for item in display_items:
                text = item.get("text", "No text")
                relevance = item.get("relevance_level", "Unknown")
                confidence = item.get("confidence", "N/A")
                criterion_id = item.get("criterion_id", "unknown")
                
                # Find criterion name
                criterion_name = criterion_id
                for c in evidence_counts:
                    if c["criterion_id"] == criterion_id:
                        criterion_name = c["criterion_name"]
                        break
                
                # Determine relevance color
                relevance_color = "#4F8BF9"  # Default blue
                if relevance.lower() == "direct":
                    relevance_color = "#00CC96"  # Green
                elif relevance.lower() == "indirect":
                    relevance_color = "#FFA15A"  # Orange
                elif relevance.lower() == "contextual":
                    relevance_color = "#9F7AEA"  # Purple
                
                # Format confidence
                confidence_str = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else str(confidence)
                
                st.markdown(
                    f"""
                    <div class="evidence-item" style="border-left-color: {relevance_color};">
                        <div class="evidence-text">"{text}"</div>
                        <div class="evidence-meta">
                            <div>Criterion: {criterion_name}</div>
                            <div>Relevance: {relevance}</div>
                            <div>Confidence: {confidence_str}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            if len(filtered_items) > 20:
                st.info(f"Showing 20 of {len(filtered_items)} evidence items. Use the filter to refine results.")
        else:
            st.info("No evidence items match the selected criteria.")
    else:
        st.info("No evidence items found in this execution log.")

def display_decision_points(context_data: Dict[str, Any]):
    """
    Display key decision points in the pipeline execution.
    
    Args:
        context_data: Pipeline context data
    """
    st.markdown("## Key Decision Points")
    
    # Look for decision points in the context
    decisions = context_data.get("decisions", [])
    
    if not decisions:
        # Try to find in agent outputs
        for agent in context_data.get("agents", []):
            if "planner" in agent.get("agent_type", "").lower():
                if "outputs" in agent and "decisions" in agent["outputs"]:
                    decisions = agent["outputs"]["decisions"]
                    break
    
    if not decisions:
        st.info("No decision points recorded in this execution log.")
        return
    
    # Display decision points
    for i, decision in enumerate(decisions):
        decision_point = decision.get("decision_point", f"Decision {i+1}")
        options = decision.get("options", [])
        selected = decision.get("selected", None)
        rationale = decision.get("rationale", "")
        
        st.markdown(
            f"""
            <div class="decision-point">
                <div class="decision-header">{decision_point}</div>
                <div>{rationale}</div>
                <div class="decision-options">
            """,
            unsafe_allow_html=True
        )
        
        # Display options
        for option in options:
            option_name = option.get("name", "")
            option_description = option.get("description", "")
            is_selected = selected == option_name
            
            selected_class = "selected-option" if is_selected else ""
            
            st.markdown(
                f"""
                <div class="decision-option {selected_class}">
                    <div style="font-weight: 600; margin-bottom: 5px;">{option_name}</div>
                    <div>{option_description}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown(
            """
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

def display_api_calls(context_data: Dict[str, Any]):
    """
    Display API call details and statistics.
    
    Args:
        context_data: Pipeline context data
    """
    st.markdown("## API Call Analysis")
    
    # Collect all API calls
    api_calls = []
    
    for agent in context_data.get("agents", []):
        for call in agent.get("calls", []):
            call_data = {
                "agent_id": agent.get("id", "unknown"),
                "agent_type": agent.get("agent_type", "unknown"),
                "call_type": call.get("type", "unknown"),
                "tokens_in": call.get("tokens_in", 0),
                "tokens_out": call.get("tokens_out", 0),
                "duration": call.get("duration", 0),
                "timestamp": call.get("timestamp", ""),
                "prompt": call.get("prompt", ""),
                "response": call.get("response", "")
            }
            api_calls.append(call_data)
    
    if not api_calls:
        st.info("No API call details found in this execution log.")
        return
    
    # Display API call statistics
    total_calls = len(api_calls)
    total_tokens_in = sum(call["tokens_in"] for call in api_calls if call["tokens_in"])
    total_tokens_out = sum(call["tokens_out"] for call in api_calls if call["tokens_out"])
    total_duration = sum(call["duration"] for call in api_calls if call["duration"])
    
    average_duration = total_duration / max(1, total_calls)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total API Calls", total_calls)
    
    with col2:
        st.metric("Total Tokens", f"{total_tokens_in + total_tokens_out:,}")
        st.metric("Input Tokens", f"{total_tokens_in:,}")
        st.metric("Output Tokens", f"{total_tokens_out:,}")
    
    with col3:
        st.metric("Total Duration", f"{total_duration:.2f}s")
        st.metric("Average Duration", f"{average_duration:.2f}s")
    
    # Create chart of calls by agent type
    calls_by_agent = {}
    for call in api_calls:
        agent_type = call["agent_type"]
        if agent_type not in calls_by_agent:
            calls_by_agent[agent_type] = 0
        calls_by_agent[agent_type] += 1
    
    # Create tokens by agent type
    tokens_by_agent = {}
    for call in api_calls:
        agent_type = call["agent_type"]
        if agent_type not in tokens_by_agent:
            tokens_by_agent[agent_type] = 0
        tokens_by_agent[agent_type] += (call["tokens_in"] + call["tokens_out"])
    
    # Prepare chart data
    agent_stats = []
    for agent_type, count in calls_by_agent.items():
        agent_stats.append({
            "agent_type": agent_type,
            "calls": count,
            "tokens": tokens_by_agent.get(agent_type, 0)
        })
    
    if agent_stats:
        # Sort by calls (descending)
        agent_stats.sort(key=lambda x: x["calls"], reverse=True)
        
        # Create dataframe
        df = pd.DataFrame(agent_stats)
        
        # Create charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### API Calls by Agent Type")
            
            calls_chart = alt.Chart(df).mark_bar().encode(
                x=alt.X('agent_type:N', title='Agent Type'),
                y=alt.Y('calls:Q', title='Number of Calls'),
                color=alt.Color('agent_type:N', scale=alt.Scale(scheme='category10')),
                tooltip=['agent_type:N', 'calls:Q']
            ).properties(
                height=300
            )
            
            st.altair_chart(calls_chart, use_container_width=True)
        
        with col2:
            st.markdown("### Tokens by Agent Type")
            
            tokens_chart = alt.Chart(df).mark_bar().encode(
                x=alt.X('agent_type:N', title='Agent Type'),
                y=alt.Y('tokens:Q', title='Total Tokens'),
                color=alt.Color('agent_type:N', scale=alt.Scale(scheme='category10')),
                tooltip=['agent_type:N', 'tokens:Q']
            ).properties(
                height=300
            )
            
            st.altair_chart(tokens_chart, use_container_width=True)
    
    # Display API call details
    st.markdown("### API Call Details")
    
    # Create a multi-select for filtering by agent type
    agent_type_options = list(calls_by_agent.keys())
    
    selected_agent_types = st.multiselect(
        "Filter by agent type",
        options=agent_type_options,
        default=[]
    )
    
    # Filter API calls by selected agent types
    filtered_calls = api_calls
    if selected_agent_types:
        filtered_calls = [call for call in api_calls if call["agent_type"] in selected_agent_types]
    
    # Display call details in expandable sections
    if filtered_calls:
        for i, call in enumerate(filtered_calls):
            call_id = f"call-{i}"
            agent_type = call["agent_type"]
            call_type = call["call_type"]
            tokens_in = call["tokens_in"]
            tokens_out = call["tokens_out"]
            duration = call["duration"]
            
            with st.expander(f"{agent_type} - {call_type} ({tokens_in + tokens_out} tokens, {duration:.2f}s)", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Prompt:**")
                    st.markdown(f"<div class='prompt-display'>{call['prompt']}</div>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("**Response:**")
                    st.markdown(f"<div class='response-display'>{call['response']}</div>", unsafe_allow_html=True)
    else:
        st.info("No API calls match the selected agent types.")

def main():
    """Main function for the pipeline viewer."""
    # Page title
    st.title("🔍 Pipeline Viewer")
    st.markdown(
        """
        Inspect the assessment pipeline execution in detail. This tool provides visibility into the 
        intermediate outputs, agent instructions, and data flow throughout the assessment process.
        """
    )
    
    # Load selected context
    context_data = display_context_selection()
    
    if not context_data:
        # No context selected, display help text
        st.info("Select an execution log from the list above to view pipeline details.")
        return
    
    # Create tabs for different analysis views
    analysis_tabs = st.tabs([
        "Overview", 
        "Pipeline Flow", 
        "Agent Execution", 
        "Evidence Collection",
        "Decision Points",
        "API Calls"
    ])
    
    with analysis_tabs[0]:
        # Overview tab
        display_pipeline_overview(context_data)
    
    with analysis_tabs[1]:
        # Pipeline Flow tab
        display_pipeline_flow(context_data)
    
    with analysis_tabs[2]:
        # Agent Execution tab
        display_agent_execution(context_data)
    
    with analysis_tabs[3]:
        # Evidence Collection tab
        display_evidence_collection(context_data)
    
    with analysis_tabs[4]:
        # Decision Points tab
        display_decision_points(context_data)
    
    with analysis_tabs[5]:
        # API Calls tab
        display_api_calls(context_data)
    
    # Add download button for the full context data
    st.download_button(
        "Download Full Execution Log",
        data=json.dumps(context_data, indent=2),
        file_name="pipeline_context.json",
        mime="application/json"
    )

if __name__ == "__main__":
    main()