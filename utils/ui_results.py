"""
UI Result Display - Simplified result display for Framework Assessment Workbench

Streamlined function for displaying assessment results in a structured, 
clean format with reliable data access.
"""
import json
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

from utils import ui_components
from utils import ui_styles

def display_assessment_results(result, strategy_preview):
    """
    Display assessment results in a clean, structured format.
    
    This updated function uses the standardized UI output structure
    to display assessment results reliably.
    
    Args:
        result: Assessment result data in UI-ready format
        strategy_preview: Strategy preview data
    """
    if not result:
        st.info("No assessment results available.")
        return
    
    st.markdown("## Assessment Results")
    
    # Add a success message if no errors
    if "error" not in result and not result.get("errors"):
        st.success("Assessment completed successfully!")
    
    # Check if result has error
    if "error" in result:
        st.error(f"Assessment encountered an error: {result['error']}")
        return
    
    # Check for errors list
    errors = result.get("errors", [])
    if errors:
        error_messages = [error.get("message", "Unknown error") for error in errors]
        st.error(f"Assessment encountered errors: {'; '.join(error_messages)}")
    
    # Check for warnings
    warnings = result.get("warnings", [])
    if warnings:
        with st.expander(f"⚠️ {len(warnings)} Warning(s)", expanded=False):
            for warning in warnings:
                st.markdown(f"- **{warning.get('stage', 'Warning')}**: {warning.get('message', '')}")
    
    # Add download button at the top
    col1, col2 = st.columns([3, 1])
    with col2:
        st.download_button(
            "Download Full Results",
            data=json.dumps(result),
            file_name="assessment_result.json",
            mime="application/json"
        )
    
    # Get the scorecard - now we expect it to be in a standard location
    scorecard = result.get("scorecard")
    
    # Display assessment scorecard
    display_scorecard(scorecard)
    
    # Display additional information in tabs if available
    tab_options = []
    
    # Check for reports
    if "reports" in result and "formats" in result["reports"]:
        formats = result["reports"]["formats"]
        if "evidence_report" in formats:
            tab_options.append("Evidence")
        if "detailed_assessment" in formats:
            tab_options.append("Detailed Assessment")
        if "visualization_data" in formats:
            tab_options.append("Visualizations")
            
    # Check for strategy information
    strategy_info = result.get("strategy") or strategy_preview
    if strategy_info:
        tab_options.append("Assessment Strategy")
    
    if tab_options:
        tabs = st.tabs(tab_options)
        
        tab_index = 0
        if "Evidence" in tab_options:
            with tabs[tab_index]:
                display_evidence_report(result["reports"]["formats"]["evidence_report"])
            tab_index += 1
            
        if "Detailed Assessment" in tab_options:
            with tabs[tab_index]:
                display_detailed_assessment(result["reports"]["formats"]["detailed_assessment"])
            tab_index += 1
            
        if "Visualizations" in tab_options:
            with tabs[tab_index]:
                display_visualization_data(result["reports"]["formats"]["visualization_data"])
            tab_index += 1
            
        if "Assessment Strategy" in tab_options:
            with tabs[tab_index]:
                display_strategy_info(strategy_info)

def display_scorecard(scorecard: Dict[str, Any]):
    """
    Display a structured assessment scorecard.
    
    Args:
        scorecard: Scorecard data
    """
    if not scorecard:
        st.info("No scorecard data available.")
        return
    
    # Overall metrics
    st.markdown("### Overall Assessment")
    
    # Create metrics for overall assessment
    overall_rating = scorecard.get("overall_rating")
    if overall_rating is not None:
        try:
            rating_val = float(overall_rating)
            rating_display = f"{rating_val:.1f}"
        except (ValueError, TypeError):
            rating_display = str(overall_rating)
    else:
        rating_display = "N/A"
    
    # Calculate coverage percentage
    coverage = scorecard.get("criteria_coverage", 0)
    if isinstance(coverage, (int, float)):
        coverage_display = f"{coverage * 100:.1f}%" if coverage else "N/A"
    else:
        coverage_display = "N/A"
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            ui_styles.metric_card("Overall Rating", rating_display),
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            ui_styles.metric_card("Criteria Coverage", coverage_display),
            unsafe_allow_html=True
        )
    
    with col3:
        dimensions_count = len(scorecard.get("dimensions", []))
        st.markdown(
            ui_styles.metric_card("Dimensions", str(dimensions_count)),
            unsafe_allow_html=True
        )
    
    # Display executive summary
    exec_summary = scorecard.get("executive_summary")
    if exec_summary:
        st.markdown("#### Executive Summary")
        st.markdown(exec_summary)
    
    # Display key strengths and improvements in columns
    col1, col2 = st.columns(2)
    
    with col1:
        key_strengths = scorecard.get("key_strengths", [])
        if key_strengths:
            st.markdown(
                ui_styles.insight_box("Key Strengths", key_strengths),
                unsafe_allow_html=True
            )
    
    with col2:
        key_improvements = scorecard.get("key_improvements", [])
        if key_improvements:
            st.markdown(
                ui_styles.insight_box("Areas for Improvement", key_improvements),
                unsafe_allow_html=True
            )
    
    # Display recommendations if available
    recommendations = scorecard.get("recommendations", [])
    if recommendations:
        st.markdown("#### Recommendations")
        for rec in recommendations:
            st.markdown(f"- {rec}")
    
    # Display dimensions in a structured format
    st.markdown("### Dimension Assessments")
    
    dimensions = scorecard.get("dimensions", [])
    if not dimensions:
        st.info("No dimension data available.")
        return
    
    # Create tabs for dimensions
    dimension_names = [dim.get("name", f"Dimension {i+1}") for i, dim in enumerate(dimensions)]
    if dimension_names:
        tabs = st.tabs(dimension_names)
        
        for i, (tab, dimension) in enumerate(zip(tabs, dimensions)):
            with tab:
                display_dimension(dimension)

def display_dimension(dimension: Dict[str, Any]):
    """
    Display dimension assessment in a clean format.
    
    Args:
        dimension: Dimension data
    """
    # Extract dimension info
    dim_name = dimension.get("name", "")
    avg_rating = dimension.get("average_rating")
    
    if avg_rating is not None:
        try:
            rating_val = float(avg_rating)
            rating_display = f"{rating_val:.1f}"
        except (ValueError, TypeError):
            rating_display = str(avg_rating)
    else:
        rating_display = "N/A"
    
    # Display dimension header and rating
    st.markdown(f"#### Rating: {rating_display}")
    
    # Display strengths and weaknesses
    col1, col2 = st.columns(2)
    
    with col1:
        strengths = dimension.get("strengths", [])
        if strengths:
            st.markdown(
                ui_styles.insight_box("Strengths", strengths),
                unsafe_allow_html=True
            )
    
    with col2:
        weaknesses = dimension.get("weaknesses", [])
        if weaknesses:
            st.markdown(
                ui_styles.insight_box("Weaknesses", weaknesses),
                unsafe_allow_html=True
            )
    
    # Display criteria table
    criteria = dimension.get("criteria", [])
    if not criteria:
        st.info("No criteria data available for this dimension.")
        return
    
    st.markdown("#### Criteria")
    
    # Create a DataFrame for the criteria
    criteria_data = []
    for criterion in criteria:
        criterion_name = criterion.get("name", criterion.get("id", "Unknown"))
        rating = criterion.get("rating")
        
        if rating is not None:
            try:
                rating_val = float(rating)
                rating_display = f"{rating_val:.1f}"
            except (ValueError, TypeError):
                rating_display = str(rating)
        else:
            rating_display = "N/A"
        
        confidence = criterion.get("confidence", "N/A")
        if confidence not in (None, "N/A"):
            try:
                confidence_val = float(confidence)
                confidence_display = f"{confidence_val:.2f}"
            except (ValueError, TypeError):
                confidence_display = str(confidence)
        else:
            confidence_display = "N/A"
        
        criteria_data.append({
            "Criterion": criterion_name,
            "Rating": rating_display,
            "Confidence": confidence_display,
            "rationale": criterion.get("rationale", "No rationale provided")
        })
    
    # Display in a clean format
    for criterion in criteria_data:
        with st.container():
            st.markdown(f"""
            <div style="background-color: #1F2937; padding: 15px; border-radius: 5px; 
                        margin-bottom: 10px; border-left: 4px solid {ui_styles.rating_color(criterion['Rating'])};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <span style="font-weight: bold; font-size: 1.1em;">{criterion['Criterion']}</span>
                    <span style="background-color: {ui_styles.rating_color(criterion['Rating'])}; 
                           color: white; padding: 2px 8px; border-radius: 12px; font-weight: bold;">
                        {criterion['Rating']}
                    </span>
                </div>
                <div style="margin-top: 5px; font-style: italic; color: #A0A0A0;">
                    {criterion['rationale']}
                </div>
            </div>
            """, unsafe_allow_html=True)

def display_evidence_report(evidence_report: Dict[str, Any]):
    """
    Display evidence report in a card-based format.
    
    Args:
        evidence_report: Evidence report data
    """
    if not evidence_report:
        st.info("No evidence report available.")
        return
    
    # Introduction
    st.markdown("### Evidence Summary")
    intro = evidence_report.get("introduction", "")
    if intro:
        st.markdown(intro)
    
    # Evidence map
    evidence_map = evidence_report.get("evidence_map", {})
    if not evidence_map:
        st.info("No evidence data available.")
        return
    
    # Create a more structured display
    st.markdown("### Evidence by Dimension and Criterion")
    
    # For each dimension
    for dimension_id, dimension_data in evidence_map.items():
        dimension_name = dimension_data.get("name", dimension_id)
        criteria_data = dimension_data.get("criteria", {})
        
        if not criteria_data:
            continue
        
        # Create a clean dimension section
        with st.expander(f"Dimension: {dimension_name}"):
            # For each criterion
            for criterion_id, criterion_data in criteria_data.items():
                criterion_name = criterion_data.get("name", criterion_id)
                criterion_question = criterion_data.get("question", "")
                evidence_list = criterion_data.get("evidence", [])
                
                # Create a criterion card
                st.markdown(f"#### {criterion_name}")
                if criterion_question:
                    st.markdown(f"*Question: {criterion_question}*")
                
                st.markdown(f"**{len(evidence_list)} evidence items found**")
                
                # Display each evidence item
                for i, evidence in enumerate(evidence_list):
                    # Use clean card styling
                    text = evidence.get("text", "No text")
                    relevance = evidence.get("relevance", "")
                    confidence = evidence.get("confidence")
                    
                    st.markdown(
                        ui_styles.evidence_item(text, relevance, confidence),
                        unsafe_allow_html=True
                    )

def display_visualization_data(viz_data: Dict[str, Any]):
    """
    Display visualization data in a structured format.
    
    Args:
        viz_data: Visualization data
    """
    if not viz_data:
        st.info("No visualization data available.")
        return
    
    st.markdown("### Assessment Visualizations")
    
    # Radar chart data (dimension ratings)
    radar_data = viz_data.get("radar_chart", [])
    if radar_data:
        st.markdown("#### Dimension Ratings")
        
        # Convert to DataFrame for visualization
        radar_df = pd.DataFrame([
            {"Dimension": item.get("dimension"), "Rating": item.get("rating")}
            for item in radar_data
        ])
        
        # Show bar chart
        st.bar_chart(radar_df.set_index("Dimension"))
        
        # Display data table
        with st.expander("Show Data Table"):
            st.dataframe(radar_df, use_container_width=True)
    
    # Evidence distribution
    evidence_dist = viz_data.get("evidence_distribution", [])
    if evidence_dist:
        st.markdown("#### Evidence Distribution")
        
        # Convert to DataFrame
        evidence_df = pd.DataFrame([
            {"Dimension": item.get("dimension"), "Evidence Count": item.get("evidence_count")}
            for item in evidence_dist
        ])
        
        # Show bar chart
        st.bar_chart(evidence_df.set_index("Dimension"))
        
        # Display data table
        with st.expander("Show Data Table"):
            st.dataframe(evidence_df, use_container_width=True)
    
    # Rating distribution
    rating_dist = viz_data.get("rating_distribution", {})
    if rating_dist:
        st.markdown("#### Rating Distribution")
        
        # Convert to DataFrame
        rating_df = pd.DataFrame([
            {"Rating": rating, "Count": count}
            for rating, count in rating_dist.items()
        ])
        
        # Show bar chart
        st.bar_chart(rating_df.set_index("Rating"))
        
        # Display data table
        with st.expander("Show Data Table"):
            st.dataframe(rating_df, use_container_width=True)

def display_strategy_info(strategy_preview):
    """
    Display strategy information in a structured format.
    
    Args:
        strategy_preview: Strategy preview data
    """
    if not strategy_preview:
        st.info("No strategy information available.")
        return
    
    st.markdown("### Assessment Strategy")
    
    # Strategy overview
    st.markdown("#### Strategy Overview")
    
    # Display strategy metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            ui_styles.metric_card("Strategy Type", strategy_preview.get("strategy_type", "unknown")),
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            ui_styles.metric_card("Extractors", str(strategy_preview.get("total_extractors", 0))),
            unsafe_allow_html=True
        )
    
    with col3:
        chunking_method = strategy_preview.get("chunking", {}).get("method", "unknown")
        st.markdown(
            ui_styles.metric_card("Chunking Method", chunking_method),
            unsafe_allow_html=True
        )
    
    # Display processing sequence
    sequence = strategy_preview.get("processing_sequence", [])
    if sequence:
        st.markdown("#### Processing Sequence")
        
        # Display as a horizontal sequence
        sequence_html = ""
        for i, step in enumerate(sequence):
            sequence_html += f'<div style="display: inline-block; background-color: #2E3440; padding: 8px 15px; margin: 5px; border-radius: 15px;">{i+1}. {step}</div>'
        
        st.markdown(f'<div style="text-align: center;">{sequence_html}</div>', unsafe_allow_html=True)
    
    # Display agent information
    agents = strategy_preview.get("agents", [])
    if agents:
        st.markdown("#### Agents Configuration")
        
        for i, agent in enumerate(agents):
            agent_type = agent.get("type", "unknown")
            
            with st.expander(f"{agent_type} Agent"):
                # Display agent configuration in a cleaner format
                configuration = agent.get("configuration", {})
                
                # Display a cleaner version of the configuration
                st.json(configuration)

def display_detailed_assessment(detailed_assessment: Dict[str, Any]):
    """
    Display detailed assessment in a structured format.
    
    Args:
        detailed_assessment: Detailed assessment data
    """
    if not detailed_assessment:
        st.info("No detailed assessment available.")
        return
    
    st.markdown("### Detailed Assessment")
    
    # Display introduction
    introduction = detailed_assessment.get("introduction")
    if introduction:
        st.markdown(introduction)
    
    # Display executive summary
    exec_summary = detailed_assessment.get("executive_summary")
    if exec_summary:
        with st.expander("Executive Summary", expanded=True):
            st.markdown(exec_summary)
    
    # Display dimensions
    dimensions = detailed_assessment.get("dimensions", [])
    if dimensions:
        for dimension in dimensions:
            with st.expander(f"Dimension: {dimension.get('name', 'Unknown')}"):
                display_dimension(dimension)