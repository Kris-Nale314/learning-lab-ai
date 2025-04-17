"""
04_Pipeline_Explorer - Interactive pipeline data explorer for Framework Assessment Workbench

This page allows users to:
1. Load and select assessment results
2. View pipeline stages and strategy
3. Explore outputs from each pipeline stage
4. Visualize agent interactions and intermediate data
"""

import os
import sys
import json
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure core modules are in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities
from utils import path_utils
from utils import ui_components
from utils import ui_styles

# Configure the page
st.set_page_config(
    page_title="Pipeline Explorer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom styles
ui_styles.apply_styles()

# Add custom CSS for pipeline visualization
st.markdown("""
<style>
.pipeline-step {
    background-color: #f0f2f6;
    border-radius: 5px;
    padding: 15px;
    margin-bottom: 15px;
    border-left: 4px solid #2C3E50;
}

.pipeline-step.active {
    border-left: 4px solid #00CC96;
    background-color: #e6f9f1;
}

.pipeline-step.completed {
    border-left: 4px solid #636EFA;
    background-color: #eef0ff;
}

.pipeline-arrow {
    display: flex;
    justify-content: center;
    margin: 10px 0;
    color: #A0A0A0;
    font-size: 24px;
}

.agent-card {
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 15px;
    margin-bottom: 15px;
}

.agent-card.extractor {
    border-left: 4px solid #00CC96;
}

.agent-card.evaluator {
    border-left: 4px solid #636EFA;
}

.agent-card.reporter {
    border-left: 4px solid #FFA15A;
}

.agent-card.planner {
    border-left: 4px solid #FF63AB;
}

.data-viewer {
    background-color: #f7f7f7;
    border-radius: 5px;
    border: 1px solid #e0e0e0;
    padding: 15px;
    max-height: 600px;
    overflow-y: auto;
}

.evidence-item {
    margin-bottom: 10px;
    padding: 10px;
    border-radius: 5px;
    background-color: #f9f9f9;
    border-left: 3px solid #636EFA;
}

.direct-evidence {
    border-left: 3px solid #00CC96;
}

.indirect-evidence {
    border-left: 3px solid #FFA15A;
}

.contextual-evidence {
    border-left: 3px solid #AB63FA;
}

.positive-evidence {
    background-color: #e6f9f1;
}

.negative-evidence {
    background-color: #ffebef;
}

.timeline-item {
    position: relative;
    padding-left: 20px;
    margin-bottom: 15px;
    border-left: 2px solid #ccc;
    padding-bottom: 15px;
}

.timeline-item:last-child {
    border-left: none;
}

.timeline-item:before {
    content: '';
    width: 12px;
    height: 12px;
    background: #636EFA;
    border-radius: 50%;
    position: absolute;
    left: -6px;
    top: 0px;
}

.timeline-content {
    padding: 10px;
    border-radius: 5px;
    border: 1px solid #e0e0e0;
    margin-left: 10px;
}

.sequence-item {
    background-color: #2C3E50;
    color: white;
    padding: 8px 15px;
    border-radius: 15px;
    margin: 5px;
    display: inline-block;
}

.sequence-arrow {
    color: #A0A0A0;
    margin: 0 5px;
    font-size: 18px;
}

.tab-content {
    padding: 15px;
    background-color: #f7f7f7;
    border-radius: 5px;
    border: 1px solid #e0e0e0;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

def load_assessment_result(file_path: str) -> Dict[str, Any]:
    """
    Load an assessment result file.
    
    Args:
        file_path: Path to the assessment result file
        
    Returns:
        Assessment result data
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load assessment result: {str(e)}")
        return {}

def display_assessment_selection() -> Optional[Dict[str, Any]]:
    """
    Display assessment selection options and return the selected assessment.
    
    Returns:
        Selected assessment data or None if no assessment selected
    """
    st.markdown("## Select an Assessment to Explore")
    
    # List assessment output files
    assessment_files = path_utils.list_files("outputs", ".json")
    
    if not assessment_files:
        st.info("No assessment results found. Please run an assessment first.")
        return None
    
    # Sort by modification time (newest first)
    assessment_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    # Create a table of assessments
    data = []
    for file_path in assessment_files:
        try:
            # Get file info
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            file_size = file_path.stat().st_size / 1024  # Size in KB
            
            # Try to load basic metadata without loading the entire file
            with open(file_path, 'r') as f:
                try:
                    # Read just enough to get metadata
                    contents = f.read(10000)  # Read first 10KB
                    # Find the closing brace of metadata
                    metadata_end = contents.find('"metadata":') 
                    if metadata_end > 0:
                        metadata_end = contents.find('}', metadata_end)
                        if metadata_end > 0:
                            metadata_text = contents[:metadata_end+1]
                            # Try to parse this fragment
                            import re
                            match = re.search(r'"framework_name":\s*"([^"]+)"', metadata_text)
                            framework_name = match.group(1) if match else "Unknown"
                        else:
                            framework_name = "Unknown"
                    else:
                        framework_name = "Unknown"
                except:
                    framework_name = "Unknown"
            
            data.append({
                "File": file_path.name,
                "Framework": framework_name,
                "Date": mtime.strftime("%Y-%m-%d %H:%M"),
                "Size": f"{file_size:.1f} KB",
                "Path": file_path
            })
        except Exception as e:
            st.warning(f"Failed to load assessment {file_path.name}: {str(e)}")
    
    # Display as a table
    if not data:
        st.info("No valid assessment files found.")
        return None
    
    # Create a dataframe for display
    import pandas as pd
    df = pd.DataFrame(data)
    # Drop the Path column for display
    display_df = df.drop(columns=["Path"])
    
    # Show the table
    st.dataframe(display_df, use_container_width=True)
    
    # Add a load button
    cols = st.columns([3, 1])
    
    with cols[0]:
        selected_indices = st.selectbox(
            "Select assessment to explore",
            options=range(len(data)),
            format_func=lambda i: f"{data[i]['Framework']} - {data[i]['Date']} - {data[i]['File']}",
            key="pipeline_assessment_selector"
        )
    
    with cols[1]:
        if st.button("Load Assessment", key="load_pipeline_assessment_btn"):
            selected_path = data[selected_indices]["Path"]
            try:
                # Load the selected assessment
                assessment_result = load_assessment_result(selected_path)
                
                # Store in session state
                st.session_state.pipeline_assessment = assessment_result
                st.session_state.pipeline_assessment_path = selected_path
                
                st.success(f"Loaded assessment: {selected_path.name}")
                return assessment_result
            except Exception as e:
                st.error(f"Failed to load assessment: {str(e)}")
                return None
    
    # Return from session state if available
    if "pipeline_assessment" in st.session_state:
        return st.session_state.pipeline_assessment
    
    return None

def display_overview(assessment_result: Dict[str, Any]):
    """
    Display an overview of the assessment.
    
    Args:
        assessment_result: Assessment result data
    """
    # Extract basic info
    metadata = assessment_result.get("metadata", {})
    statistics = assessment_result.get("statistics", {})
    
    # Create metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Framework", 
            metadata.get("framework_name", "Unknown")
        )
    
    with col2:
        st.metric(
            "Overall Rating", 
            f"{assessment_result.get('scorecard', {}).get('overall_rating', 'N/A')}"
        )
    
    with col3:
        st.metric(
            "Criteria Coverage", 
            f"{statistics.get('assessment_coverage', 0) * 100:.1f}%"
        )
    
    with col4:
        st.metric(
            "Evidence Items", 
            statistics.get("total_evidence", 0)
        )
    
    # Display execution time
    st.markdown(f"**Generated:** {metadata.get('generated_at', 'Unknown')}")
    
    # Show warnings/errors if any
    warnings = assessment_result.get("warnings", [])
    errors = assessment_result.get("errors", [])
    
    if warnings:
        with st.expander(f"⚠️ Warnings ({len(warnings)})", expanded=False):
            for warning in warnings:
                st.markdown(f"- **{warning.get('stage', 'Warning')}**: {warning.get('message', '')}")
    
    if errors:
        with st.expander(f"❌ Errors ({len(errors)})", expanded=False):
            for error in errors:
                st.markdown(f"- **{error.get('stage', 'Error')}**: {error.get('message', '')}")

def display_pipeline_strategy(assessment_result: Dict[str, Any]):
    """
    Display the assessment strategy and pipeline configuration.
    
    Args:
        assessment_result: Assessment result data
    """
    strategy = assessment_result.get("strategy", {})
    
    if not strategy:
        st.info("No strategy information available for this assessment.")
        return
    
    st.markdown("## Assessment Strategy")
    
    # Display strategy type and rationale
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.metric("Strategy Type", strategy.get("strategy_type", "Unknown"))
    
    with col2:
        st.markdown(f"**Rationale:** {strategy.get('rationale', 'No rationale provided')}")
    
    # Display processing sequence
    processing_sequence = strategy.get("processing_sequence", [])
    
    if processing_sequence:
        st.markdown("### Processing Sequence")
        
        # Create a horizontal visualization of the sequence
        sequence_html = '<div style="display: flex; flex-wrap: wrap; align-items: center; margin: 20px 0;">'
        
        for i, step in enumerate(processing_sequence):
            # Add arrow between steps
            if i > 0:
                sequence_html += '<span class="sequence-arrow">→</span>'
            
            # Add step with styling
            sequence_html += f'<span class="sequence-item">{step}</span>'
        
        sequence_html += '</div>'
        
        st.markdown(sequence_html, unsafe_allow_html=True)
    
    # Display chunking strategy
    chunking = strategy.get("chunking_strategy", {})
    
    if chunking:
        with st.expander("Chunking Strategy", expanded=False):
            # Display method, size, and overlap
            cols = st.columns(3)
            with cols[0]:
                st.metric("Method", chunking.get("method", "Unknown"))
            with cols[1]:
                st.metric("Chunk Size", chunking.get("size", 0))
            with cols[2]:
                st.metric("Overlap", chunking.get("overlap", 0))
            
            # Display rationale
            st.markdown(f"**Rationale:** {chunking.get('rationale', 'No rationale provided')}")
    
    # Display agents configuration
    agents = strategy.get("agents", [])
    
    if agents:
        st.markdown("### Agent Configuration")
        
        # Create a tab for each agent type
        agent_types = list(set(agent["agent_type"] for agent in agents if "agent_type" in agent))
        agent_tabs = st.tabs(agent_types)
        
        for i, agent_type in enumerate(agent_types):
            with agent_tabs[i]:
                # Filter agents of this type
                type_agents = [agent for agent in agents if agent.get("agent_type") == agent_type]
                
                for j, agent in enumerate(type_agents):
                    # Create a card for each agent
                    agent_name = f"{agent_type.capitalize()} {j+1}"
                    if "name" in agent:
                        agent_name = agent["name"]
                    
                    st.markdown(f"""
                    <div class="agent-card {agent_type.lower()}">
                        <h4>{agent_name}</h4>
                        <p><strong>Instructions:</strong> {agent.get('instructions', 'No instructions provided')}</p>
                        <p><strong>Inputs:</strong> {', '.join(agent.get('inputs', []))}</p>
                        <p><strong>Outputs:</strong> {', '.join(agent.get('outputs', []))}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Display token allocation if available
    token_allocation = strategy.get("token_allocation", {})
    
    if token_allocation:
        with st.expander("Agent Allocation", expanded=False):
            # Display total allocation
            st.metric("Total Agents", token_allocation.get("total_estimated", 0))
            
            # Display allocation by agent if available
            by_agent = token_allocation.get("by_agent", {})
            if by_agent:
                # Create a dataframe
                allocation_data = [{"Agent": agent, "Number": tokens} for agent, tokens in by_agent.items()]
                allocation_df = pd.DataFrame(allocation_data)
                
                # Create a bar chart
                chart = alt.Chart(allocation_df).mark_bar().encode(
                    x=alt.X('Agent:N', title='Agent Type'),
                    y=alt.Y('Count:Q', title='Agent Allocation'),
                    color=alt.Color('Agent:N', scale=alt.Scale(scheme='category10')),
                    tooltip=['Agent:N', 'Count:Q']
                ).properties(
                    height=300
                )
                
                st.altair_chart(chart, use_container_width=True)

def display_planning_outputs(assessment_result: Dict[str, Any]):
    """
    Display outputs from the planning stage.
    
    Args:
        assessment_result: Assessment result data
    """
    strategy = assessment_result.get("strategy", {})
    
    if not strategy:
        st.info("No planning data available for this assessment.")
        return
    
    st.markdown("## Planning Outputs")
    
    # Create tabs for different planning outputs
    plan_tabs = st.tabs(["Document Analysis", "Framework Analysis", "Strategy Design", "Output Schema"])
    
    with plan_tabs[0]:
        # Display document analysis
        st.markdown("### Document Analysis")
        
        # Display basic document info
        metadata = assessment_result.get("metadata", {})
        document_length = metadata.get("document_length", 0)
        
        st.metric("Document Length", f"{document_length:,} chars")
        
        # TODO: Add actual document analysis when available in the result
        st.markdown("Document analysis is not available in this assessment result.")
    
    with plan_tabs[1]:
        # Display framework analysis
        st.markdown("### Framework Analysis")
        
        # Get framework info
        metadata = assessment_result.get("metadata", {})
        statistics = assessment_result.get("statistics", {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Framework", metadata.get("framework_name", "Unknown"))
        
        with col2:
            st.metric("Total Criteria", statistics.get("total_criteria", 0))
        
        with col3:
            # Count dimensions
            dimensions = statistics.get("dimensions", {})
            st.metric("Dimensions", len(dimensions))
        
        # Display framework structure
        st.markdown("#### Framework Structure")
        
        # Create a table of dimensions and criteria
        dim_data = []
        
        for dim_id, dim_stats in statistics.get("dimensions", {}).items():
            # Find dimension name
            dim_name = dim_id
            for dim in assessment_result.get("scorecard", {}).get("dimensions", []):
                if dim.get("id") == dim_id:
                    dim_name = dim.get("name", dim_id)
                    break
            
            dim_data.append({
                "Dimension": dim_name,
                "Criteria Count": dim_stats.get("total_criteria", 0),
                "Coverage": f"{dim_stats.get('coverage', 0) * 100:.1f}%"
            })
        
        if dim_data:
            dim_df = pd.DataFrame(dim_data)
            st.dataframe(dim_df, use_container_width=True)
    
    with plan_tabs[2]:
        # Display strategy design
        st.markdown("### Strategy Design")
        
        st.markdown(f"**Strategy Type:** {strategy.get('strategy_type', 'Unknown')}")
        st.markdown(f"**Rationale:** {strategy.get('rationale', 'No rationale provided')}")
        
        # Display processing sequence
        processing_sequence = strategy.get("processing_sequence", [])
        
        if processing_sequence:
            st.markdown("#### Processing Sequence")
            
            # Create a horizontal visualization of the sequence
            sequence_html = '<div style="display: flex; flex-wrap: wrap; align-items: center; margin: 20px 0;">'
            
            for i, step in enumerate(processing_sequence):
                # Add arrow between steps
                if i > 0:
                    sequence_html += '<span class="sequence-arrow">→</span>'
                
                # Add step with styling
                sequence_html += f'<span class="sequence-item">{step}</span>'
            
            sequence_html += '</div>'
            
            st.markdown(sequence_html, unsafe_allow_html=True)
    
    with plan_tabs[3]:
        # Display output schema
        st.markdown("### Output Schema")
        
        output_schema = strategy.get("output_schema", {})
        
        if output_schema:
            # Create collapsible sections for schema parts
            with st.expander("Overall Schema", expanded=False):
                st.json(output_schema)
            
            with st.expander("Dimension Schemas", expanded=False):
                dimension_schemas = output_schema.get("dimension_schemas", {})
                st.json(dimension_schemas)
            
            with st.expander("Evaluator Output Schema", expanded=False):
                evaluator_schema = output_schema.get("evaluator_output", {})
                st.json(evaluator_schema)
            
            with st.expander("Reporter Output Schema", expanded=False):
                reporter_schema = output_schema.get("reporter_output", {})
                st.json(reporter_schema)
        else:
            st.info("No output schema available for this assessment.")

def display_extraction_outputs(assessment_result: Dict[str, Any]):
    """
    Display outputs from the extraction stage.
    
    Args:
        assessment_result: Assessment result data
    """
    statistics = assessment_result.get("statistics", {})
    
    st.markdown("## Extraction Outputs")
    
    # Check if we have evidence items
    total_evidence = statistics.get("total_evidence", 0)
    
    if total_evidence == 0:
        st.info("No evidence extraction data available for this assessment.")
        return
    
    # Display evidence statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Evidence", total_evidence)
    
    with col2:
        st.metric("Evidence per Criterion", statistics.get("evidence_per_criterion", 0))
    
    with col3:
        st.metric("Average Confidence", f"{statistics.get('average_confidence', 0):.2f}")
    
    # Try to find evidence report in the assessment result
    evidence_report = None
    if "reports" in assessment_result and "formats" in assessment_result["reports"]:
        evidence_report = assessment_result["reports"]["formats"].get("evidence_report")
    
    if evidence_report:
        # Display evidence exploration interface
        st.markdown("### Evidence Exploration")
        
        # Create tabs for evidence by dimension
        evidence_map = evidence_report.get("evidence_map", {})
        
        if evidence_map:
            # Get dimension names for tabs
            dimension_tabs = []
            for dimension_id, dimension_data in evidence_map.items():
                dimension_name = dimension_data.get("name", dimension_id)
                dimension_tabs.append((dimension_id, dimension_name))
            
            # Create tabs
            dim_tab_names = [dim_name for _, dim_name in dimension_tabs]
            dim_tabs = st.tabs(dim_tab_names)
            
            for i, (dimension_id, dimension_name) in enumerate(dimension_tabs):
                with dim_tabs[i]:
                    dimension_data = evidence_map[dimension_id]
                    criteria_data = dimension_data.get("criteria", {})
                    
                    # Create expandable section for each criterion
                    for criterion_id, criterion_data in criteria_data.items():
                        criterion_name = criterion_data.get("name", criterion_id)
                        evidence_list = criterion_data.get("evidence", [])
                        
                        with st.expander(f"{criterion_name} - {len(evidence_list)} evidence items"):
                            # Display evidence items with styling
                            for evidence in evidence_list:
                                display_evidence_item(evidence)
        else:
            st.info("No evidence map available in this assessment.")
    else:
        # No detailed evidence report, display basic evidence stats
        st.info("Detailed evidence report not available for this assessment.")
        
        # Try to find evidence references in criteria
        has_evidence_refs = False
        
        for dimension in assessment_result.get("scorecard", {}).get("dimensions", []):
            for criterion in dimension.get("criteria", []):
                if "evidence_count" in criterion or "evidence_by_category" in criterion:
                    has_evidence_refs = True
        
        if has_evidence_refs:
            st.markdown("### Evidence References in Criteria")
            st.markdown("This assessment contains evidence references in criteria, but detailed evidence items are not available.")
            
            # Display criteria with evidence references
            for dimension in assessment_result.get("scorecard", {}).get("dimensions", []):
                dimension_name = dimension.get("name", "Unknown Dimension")
                
                with st.expander(dimension_name):
                    for criterion in dimension.get("criteria", []):
                        criterion_name = criterion.get("name", "Unknown Criterion")
                        evidence_count = criterion.get("evidence_count", 0)
                        evidence_categories = criterion.get("evidence_by_category", {})
                        
                        st.markdown(f"**{criterion_name}**: {evidence_count} evidence items")
                        
                        if evidence_categories:
                            categories_df = pd.DataFrame([
                                {"Category": category, "Count": count}
                                for category, count in evidence_categories.items()
                            ])
                            st.dataframe(categories_df)

def display_evidence_item(evidence: Dict[str, Any]):
    """
    Display a single evidence item with styling.
    
    Args:
        evidence: Evidence item data
    """
    text = evidence.get("text", "No text")
    relevance_level = evidence.get("relevance_level", "Direct")
    confidence = evidence.get("confidence", 0.8)
    sentiment = evidence.get("sentiment", "Neutral")
    
    # Determine CSS classes
    relevance_class = relevance_level.lower() + "-evidence" if relevance_level else ""
    sentiment_class = sentiment.lower() + "-evidence" if sentiment else ""
    
    # Format confidence
    confidence_display = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else str(confidence)
    
    # HTML for evidence item
    evidence_html = f"""
    <div class="evidence-item {relevance_class} {sentiment_class}">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-weight: bold;">{relevance_level} - {sentiment}</span>
            <span>Confidence: {confidence_display}</span>
        </div>
        <div style="padding: 8px; background-color: rgba(255, 255, 255, 0.6); border-radius: 4px; margin-bottom: 5px;">
            "{text}"
        </div>
    </div>
    """
    
    st.markdown(evidence_html, unsafe_allow_html=True)

def display_evaluation_outputs(assessment_result: Dict[str, Any]):
    """
    Display outputs from the evaluation stage.
    
    Args:
        assessment_result: Assessment result data
    """
    st.markdown("## Evaluation Outputs")
    
    # Get assessment statistics
    statistics = assessment_result.get("statistics", {})
    scorecard = assessment_result.get("scorecard", {})
    
    # Display assessment statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Criteria Assessed", statistics.get("assessed_criteria", 0))
    
    with col2:
        st.metric("Assessment Coverage", f"{statistics.get('assessment_coverage', 0) * 100:.1f}%")
    
    with col3:
        st.metric("Overall Rating", scorecard.get("overall_rating", "N/A"))
    
    # Get assessment types
    assessment_types = scorecard.get("assessment_types", {})
    direct_percentage = scorecard.get("direct_assessment_percentage", 0)
    
    if assessment_types:
        st.markdown("### Assessment Types")
        
        # Create metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Direct Assessments", assessment_types.get("direct", 0))
        
        with col2:
            st.metric("Inferred Assessments", assessment_types.get("inferred", 0))
        
        with col3:
            st.metric("Insufficient Evidence", assessment_types.get("insufficient_evidence", 0))
        
        # Create a visualization
        if sum(assessment_types.values()) > 0:
            # Create a dataframe
            type_data = [
                {"Type": "Direct", "Count": assessment_types.get("direct", 0)},
                {"Type": "Inferred", "Count": assessment_types.get("inferred", 0)},
                {"Type": "Insufficient Evidence", "Count": assessment_types.get("insufficient_evidence", 0)}
            ]
            type_df = pd.DataFrame(type_data)
            
            # Create a pie chart
            chart = alt.Chart(type_df).mark_arc().encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(field="Type", type="nominal", scale=alt.Scale(
                    domain=['Direct', 'Inferred', 'Insufficient Evidence'],
                    range=['#00CC96', '#FFA15A', '#888888']
                )),
                tooltip=['Type', 'Count']
            ).properties(
                height=300
            )
            
            st.altair_chart(chart, use_container_width=True)
    
    # Create tabs for criterion evaluations by dimension
    st.markdown("### Criteria Evaluations")
    
    dimensions = scorecard.get("dimensions", [])
    
    if dimensions:
        # Create tabs
        dimension_names = [dim.get("name", "Unknown") for dim in dimensions]
        dim_tabs = st.tabs(dimension_names)
        
        for i, dimension in enumerate(dimensions):
            with dim_tabs[i]:
                # Get dimension data
                dimension_name = dimension.get("name", "Unknown")
                dimension_rating = dimension.get("average_rating", "N/A")
                criteria = dimension.get("criteria", [])
                
                # Display dimension rating
                st.metric("Dimension Rating", dimension_rating)
                
                # Display dimension strengths and weaknesses
                col1, col2 = st.columns(2)
                
                with col1:
                    strengths = dimension.get("strengths", [])
                    if strengths:
                        st.markdown("#### Strengths")
                        for strength in strengths:
                            st.markdown(f"- {strength}")
                
                with col2:
                    weaknesses = dimension.get("weaknesses", [])
                    if weaknesses:
                        st.markdown("#### Weaknesses")
                        for weakness in weaknesses:
                            st.markdown(f"- {weakness}")
                
                # Display criteria
                st.markdown("#### Criteria")
                
                for criterion in criteria:
                    # Get criterion data
                    criterion_name = criterion.get("name", "Unknown")
                    criterion_rating = criterion.get("rating", "N/A")
                    criterion_rationale = criterion.get("rationale", "No rationale provided")
                    criterion_type = criterion.get("assessment_type", "unknown")
                    criterion_confidence = criterion.get("confidence")
                    
                    # Determine badge color based on assessment type
                    if criterion_type == "direct":
                        badge_color = "#00CC96"  # Green
                    elif criterion_type == "inferred":
                        badge_color = "#FFA15A"  # Orange
                    else:
                        badge_color = "#888888"  # Gray
                    
                    # Create criterion card
                    st.markdown(f"""
                    <div style="border: 1px solid #e0e0e0; border-radius: 5px; padding: 15px; margin-bottom: 15px; border-left: 4px solid {badge_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <div style="font-weight: bold; font-size: 1.1em;">{criterion_name}</div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="background-color: {badge_color}; color: white; 
                                       padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">
                                    {criterion_type.title()}
                                </span>
                                <span style="background-color: #636EFA; color: white; 
                                       padding: 2px 8px; border-radius: 12px; font-weight: bold;">
                                    {criterion_rating}
                                </span>
                            </div>
                        </div>
                        <div style="margin-top: 5px;">
                            {criterion_rationale}
                        </div>
                        <div style="display: flex; justify-content: flex-end; margin-top: 10px; font-size: 0.8em; color: #A0A0A0;">
                            Confidence: {criterion_confidence}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("No dimension evaluations available for this assessment.")

def display_reporting_outputs(assessment_result: Dict[str, Any]):
    """
    Display outputs from the reporting stage.
    
    Args:
        assessment_result: Assessment result data
    """
    st.markdown("## Reporting Outputs")
    
    # Get available report formats
    report_formats = {}
    if "reports" in assessment_result and "formats" in assessment_result["reports"]:
        report_formats = assessment_result["reports"]["formats"]
    
    if not report_formats:
        st.info("No report formats available for this assessment.")
        return
    
    # Create tabs for each report format
    format_names = list(report_formats.keys())
    format_tabs = st.tabs(format_names)
    
    for i, format_name in enumerate(format_names):
        with format_tabs[i]:
            report_data = report_formats[format_name]
            
            if format_name == "scorecard":
                display_scorecard_report(report_data)
            elif format_name == "executive_summary":
                display_executive_summary_report(report_data)
            elif format_name == "detailed_assessment":
                display_detailed_assessment_report(report_data)
            elif format_name == "evidence_report":
                display_evidence_report(report_data)
            elif format_name == "visualization_data":
                display_visualization_data(report_data)
            else:
                # Generic JSON display
                st.json(report_data)

def display_scorecard_report(scorecard: Dict[str, Any]):
    """
    Display a scorecard report.
    
    Args:
        scorecard: Scorecard data
    """
    st.markdown(f"### {scorecard.get('title', 'Assessment Scorecard')}")
    
    # Display overall metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        overall_rating = scorecard.get("overall_rating", "N/A")
        st.metric("Overall Rating", overall_rating)
    
    with col2:
        reliability = scorecard.get("assessment_reliability", "Unknown")
        st.metric("Assessment Reliability", reliability)
    
    with col3:
        # Calculate direct assessment percentage
        assessment_types = scorecard.get("assessment_types", {})
        total = sum(assessment_types.values()) or 1
        direct_percentage = assessment_types.get("direct", 0) / total * 100
        st.metric("Direct Assessments", f"{direct_percentage:.1f}%")
    
    # Display executive summary
    st.markdown("#### Executive Summary")
    st.markdown(scorecard.get("executive_summary", "No executive summary provided."))
    
    # Display key strengths and improvements
    col1, col2 = st.columns(2)
    
    with col1:
        strengths = scorecard.get("key_strengths", [])
        if strengths:
            st.markdown("#### Key Strengths")
            for strength in strengths:
                st.markdown(f"- {strength}")
    
    with col2:
        improvements = scorecard.get("key_improvements", [])
        if improvements:
            st.markdown("#### Areas for Improvement")
            for improvement in improvements:
                st.markdown(f"- {improvement}")
    
    # Display recommendations
    recommendations = scorecard.get("recommendations", [])
    if recommendations:
        st.markdown("#### Recommendations")
        for recommendation in recommendations:
            st.markdown(f"- {recommendation}")
    
    # Display dimension ratings
    st.markdown("#### Dimension Ratings")
    
    dimensions = scorecard.get("dimensions", [])
    if dimensions:
        # Create a dataframe
        dim_data = []
        for dimension in dimensions:
            dim_data.append({
                "Dimension": dimension.get("name", "Unknown"),
                "Rating": dimension.get("average_rating", "N/A")
            })
        
        if dim_data:
            dim_df = pd.DataFrame(dim_data)
            
            # Create a bar chart
            chart = alt.Chart(dim_df).mark_bar().encode(
                x=alt.X('Rating:Q', title='Average Rating'),
                y=alt.Y('Dimension:N', title=None, sort='-x'),
                color=alt.Color('Rating:Q', scale=alt.Scale(scheme='blueorange'), legend=None),
                tooltip=['Dimension:N', 'Rating:Q']
            ).properties(
                height=300
            )
            
            st.altair_chart(chart, use_container_width=True)

def display_executive_summary_report(report: Dict[str, Any]):
    """
    Display an executive summary report.
    
    Args:
        report: Executive summary data
    """
    st.markdown(f"### {report.get('title', 'Executive Summary')}")
    
    # Display overall rating
    st.metric("Overall Rating", report.get("overall_rating", "N/A"))
    
    # Display executive summary
    st.markdown("#### Summary")
    st.markdown(report.get("executive_summary", "No executive summary provided."))
    
    # Display key strengths and improvements
    col1, col2 = st.columns(2)
    
    with col1:
        strengths = report.get("key_strengths", [])
        if strengths:
            st.markdown("#### Key Strengths")
            for strength in strengths:
                st.markdown(f"- {strength}")
    
    with col2:
        improvements = report.get("key_improvements", [])
        if improvements:
            st.markdown("#### Areas for Improvement")
            for improvement in improvements:
                st.markdown(f"- {improvement}")
    
    # Display recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        st.markdown("#### Recommendations")
        for recommendation in recommendations:
            st.markdown(f"- {recommendation}")

def display_detailed_assessment_report(report: Dict[str, Any]):
    """
    Display a detailed assessment report.
    
    Args:
        report: Detailed assessment data
    """
    st.markdown(f"### {report.get('title', 'Detailed Assessment')}")
    
    # Display introduction if available
    introduction = report.get("introduction")
    if introduction:
        st.markdown("#### Introduction")
        st.markdown(introduction)
    
    # Display overall metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        overall_rating = report.get("overall_rating", "N/A")
        st.metric("Overall Rating", overall_rating)
    
    with col2:
        reliability = report.get("assessment_reliability", "Unknown")
        st.metric("Assessment Reliability", reliability)
    
    with col3:
        # Calculate direct assessment percentage
        direct_percentage = report.get("direct_assessment_percentage", 0) * 100
        st.metric("Direct Assessments", f"{direct_percentage:.1f}%")
    
    # Display executive summary
    st.markdown("#### Executive Summary")
    st.markdown(report.get("executive_summary", "No executive summary provided."))
    
    # Display key strengths and improvements
    col1, col2 = st.columns(2)
    
    with col1:
        strengths = report.get("key_strengths", [])
        if strengths:
            st.markdown("#### Key Strengths")
            for strength in strengths:
                st.markdown(f"- {strength}")
    
    with col2:
        improvements = report.get("key_improvements", [])
        if improvements:
            st.markdown("#### Areas for Improvement")
            for improvement in improvements:
                st.markdown(f"- {improvement}")
    
    # Display recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        st.markdown("#### Recommendations")
        for recommendation in recommendations:
            st.markdown(f"- {recommendation}")
    
    # Display dimensions
    dimensions = report.get("dimensions", [])
    if dimensions:
        st.markdown("#### Dimension Assessments")
        
        for dimension in dimensions:
            dimension_name = dimension.get("name", "Unknown")
            dimension_rating = dimension.get("average_rating", "N/A")
            
            with st.expander(f"{dimension_name} - Rating: {dimension_rating}"):
                # Display dimension strengths and weaknesses
                col1, col2 = st.columns(2)
                
                with col1:
                    strengths = dimension.get("strengths", [])
                    if strengths:
                        st.markdown("##### Strengths")
                        for strength in strengths:
                            st.markdown(f"- {strength}")
                
                with col2:
                    weaknesses = dimension.get("weaknesses", [])
                    if weaknesses:
                        st.markdown("##### Weaknesses")
                        for weakness in weaknesses:
                            st.markdown(f"- {weakness}")
                
                # Display criteria
                criteria = dimension.get("criteria", [])
                if criteria:
                    st.markdown("##### Criteria")
                    
                    for criterion in criteria:
                        criterion_name = criterion.get("name", "Unknown")
                        criterion_rating = criterion.get("rating", "N/A")
                        criterion_rationale = criterion.get("rationale", "No rationale provided")
                        criterion_type = criterion.get("assessment_type", "unknown")
                        
                        # Create criterion card
                        st.markdown(f"**{criterion_name}** - Rating: {criterion_rating} ({criterion_type.title()})")
                        st.markdown(criterion_rationale)
                        st.markdown("---")

def display_evidence_report(report: Dict[str, Any]):
    """
    Display an evidence report.
    
    Args:
        report: Evidence report data
    """
    st.markdown(f"### {report.get('title', 'Evidence Report')}")
    
    # Display introduction
    st.markdown(report.get("introduction", "No introduction provided."))
    
    # Display evidence metrics
    total_evidence = report.get("total_evidence", 0)
    st.metric("Total Evidence Items", total_evidence)
    
    # Display evidence map
    evidence_map = report.get("evidence_map", {})
    if evidence_map:
        st.markdown("#### Evidence by Dimension and Criterion")
        
        for dimension_id, dimension_data in evidence_map.items():
            dimension_name = dimension_data.get("name", dimension_id)
            criteria_data = dimension_data.get("criteria", {})
            
            with st.expander(f"{dimension_name}"):
                for criterion_id, criterion_data in criteria_data.items():
                    criterion_name = criterion_data.get("name", criterion_id)
                    criterion_question = criterion_data.get("question", "")
                    evidence_list = criterion_data.get("evidence", [])
                    
                    st.markdown(f"##### {criterion_name}")
                    if criterion_question:
                        st.markdown(f"*{criterion_question}*")
                    
                    st.markdown(f"**{len(evidence_list)} evidence items**")
                    
                    # Display evidence items
                    for evidence in evidence_list:
                        display_evidence_item(evidence)

def display_visualization_data(viz_data: Dict[str, Any]):
    """
    Display visualization data.
    
    Args:
        viz_data: Visualization data
    """
    st.markdown(f"### {viz_data.get('title', 'Visualization Data')}")
    
    # Create tabs for different visualizations
    viz_tabs = st.tabs(["Radar Chart", "Heatmap", "Evidence Distribution", "Assessment Types"])
    
    with viz_tabs[0]:
        # Display radar chart data
        st.markdown("#### Radar Chart (Dimension Ratings)")
        
        radar_data = viz_data.get("radar_chart", [])
        if radar_data:
            # Create dataframe
            radar_df = pd.DataFrame(radar_data)
            
            # Create bar chart
            chart = alt.Chart(radar_df).mark_bar().encode(
                x=alt.X('rating:Q', title='Rating'),
                y=alt.Y('dimension:N', title=None, sort='-x'),
                color=alt.Color('rating:Q', scale=alt.Scale(scheme='blueorange'), legend=None),
                tooltip=['dimension:N', 'rating:Q']
            ).properties(
                height=300
            )
            
            st.altair_chart(chart, use_container_width=True)
    
    with viz_tabs[1]:
        # Display heatmap data
        st.markdown("#### Heatmap (Criterion Ratings)")
        
        heatmap_data = viz_data.get("heatmap", [])
        if heatmap_data:
            # Create dataframe
            heatmap_df = pd.DataFrame(heatmap_data)
            
            # Create heatmap
            heatmap = alt.Chart(heatmap_df).mark_rect().encode(
                x=alt.X('criterion:N', title='Criterion'),
                y=alt.Y('dimension:N', title='Dimension'),
                color=alt.Color('rating:Q', scale=alt.Scale(scheme='blueorange')),
                tooltip=['dimension:N', 'criterion:N', 'rating:Q', 'assessment_type:N']
            ).properties(
                width=500,
                height=300
            )
            
            st.altair_chart(heatmap, use_container_width=True)
    
    with viz_tabs[2]:
        # Display evidence distribution
        st.markdown("#### Evidence Distribution")
        
        evidence_dist = viz_data.get("evidence_distribution", [])
        if evidence_dist:
            # Create dataframe
            dist_df = pd.DataFrame(evidence_dist)
            
            # Create bar chart
            chart = alt.Chart(dist_df).mark_bar().encode(
                x=alt.X('evidence_count:Q', title='Evidence Count'),
                y=alt.Y('dimension:N', title=None, sort='-x'),
                tooltip=['dimension:N', 'evidence_count:Q']
            ).properties(
                height=300
            )
            
            st.altair_chart(chart, use_container_width=True)
    
    with viz_tabs[3]:
        # Display assessment type distribution
        st.markdown("#### Assessment Type Distribution")
        
        assessment_dist = viz_data.get("assessment_type_distribution", [])
        if assessment_dist:
            # Create dataframe
            type_df = pd.DataFrame(assessment_dist)
            
            # Create pie chart
            chart = alt.Chart(type_df).mark_arc().encode(
                theta=alt.Theta(field="count", type="quantitative"),
                color=alt.Color(field="type", type="nominal", scale=alt.Scale(
                    domain=['direct', 'inferred', 'insufficient_evidence'],
                    range=['#00CC96', '#FFA15A', '#888888']
                )),
                tooltip=['type:N', 'count:Q']
            ).properties(
                height=300
            )
            
            st.altair_chart(chart, use_container_width=True)

def main():
    """Main function for the Pipeline Explorer."""
    # Page title
    st.title("🧠 Pipeline Explorer")
    st.markdown(
        """
        Explore the assessment pipeline and view intermediate outputs from each stage.
        Load a previous assessment result to see how it was processed through the pipeline.
        """
    )
    
    # Load selected assessment
    assessment_result = display_assessment_selection()
    
    if not assessment_result:
        # No assessment selected, display help text
        st.info("Select an assessment from the list above to explore its pipeline outputs.")
        return
    
    # Display assessment overview
    display_overview(assessment_result)
    
    # Create tabs for pipeline stages
    stage_tabs = st.tabs(["Pipeline Strategy", "Planning", "Extraction", "Evaluation", "Reporting", "Raw Data"])
    
    with stage_tabs[0]:
        # Display the pipeline strategy
        display_pipeline_strategy(assessment_result)
    
    with stage_tabs[1]:
        # Display planning outputs
        display_planning_outputs(assessment_result)
    
    with stage_tabs[2]:
        # Display extraction outputs
        display_extraction_outputs(assessment_result)
    
    with stage_tabs[3]:
        # Display evaluation outputs
        display_evaluation_outputs(assessment_result)
    
    with stage_tabs[4]:
        # Display reporting outputs
        display_reporting_outputs(assessment_result)
    
    with stage_tabs[5]:
        # Display raw assessment data
        st.markdown("## Raw Assessment Data")
        
        # Create expandable sections for different parts of the data
        with st.expander("Scorecard", expanded=False):
            st.json(assessment_result.get("scorecard", {}))
        
        with st.expander("Report Formats", expanded=False):
            st.json(assessment_result.get("reports", {}).get("formats", {}))
        
        with st.expander("Metadata", expanded=False):
            st.json(assessment_result.get("metadata", {}))
        
        with st.expander("Statistics", expanded=False):
            st.json(assessment_result.get("statistics", {}))
        
        with st.expander("Strategy", expanded=False):
            st.json(assessment_result.get("strategy", {}))
        
        with st.expander("Full Assessment Result", expanded=False):
            st.json(assessment_result)

if __name__ == "__main__":
    main()