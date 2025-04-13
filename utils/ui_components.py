"""
UI Components for Framework Assessment Workbench

Reusable UI components for consistent presentation across the application.
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, List, Optional, Union

from utils import ui_styles

def initialize_ui():
    """Initialize UI with styles."""
    ui_styles.apply_styles()


def card_container(title=None, key=None):
    """
    Create a styled card container.
    
    Args:
        title: Optional title for the card
        key: Optional key for the container
        
    Returns:
        Streamlit container
    """
    container = st.container()
    
    with container:
        if title:
            st.markdown(f"#### {title}")
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
    
    return container


def end_card_container():
    """Close a card container."""
    st.markdown('</div>', unsafe_allow_html=True)


def rating_card(title, rating, description=None, key=None):
    """
    Display a rating card with appropriate color.
    
    Args:
        title: Card title
        rating: Rating value (1-5)
        description: Optional description
        key: Optional key for the card
    """
    rating_display = "N/A"
    rating_class = ""
    
    if rating is not None:
        try:
            rating_float = float(rating)
            rating_display = f"{rating_float:.1f}"
            rating_int = int(round(rating_float))
            rating_class = ui_styles.get_css_class_for_rating(rating_int)
        except (ValueError, TypeError):
            rating_display = str(rating)
    
    card_html = f"""
    <div class="rating-card {rating_class}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-weight: 600; font-size: 1.1rem;">{title}</div>
            {ui_styles.rating_badge(rating)}
        </div>
    """
    
    if description:
        card_html += f"<div style='margin-top: 8px;'>{description}</div>"
    
    card_html += "</div>"
    
    st.markdown(card_html, unsafe_allow_html=True)


def metric_row(metrics: List[Dict[str, Any]], columns=None):
    """
    Display a row of metrics.
    
    Args:
        metrics: List of metric dictionaries with 'label', 'value', and optional 'description'
        columns: Optional number of columns (defaults to len(metrics))
    """
    if not metrics:
        return
    
    cols = columns or len(metrics)
    columns = st.columns(cols)
    
    for i, metric in enumerate(metrics):
        col_idx = i % cols
        with columns[col_idx]:
            st.markdown(
                ui_styles.metric_card(
                    metric["label"], 
                    metric["value"], 
                    metric.get("description")
                ),
                unsafe_allow_html=True
            )


def insights_section(title, items, key=None):
    """
    Display a section with insights.
    
    Args:
        title: Section title
        items: List of insight items
        key: Optional key for the section
    """
    if not items:
        return
    
    st.markdown(
        ui_styles.insight_box(title, items),
        unsafe_allow_html=True
    )


def status_section(status_items: List[Dict[str, Any]]):
    """
    Display a section with status items.
    
    Args:
        status_items: List of status dictionaries with 'status', 'message', and 'type'
    """
    if not status_items:
        return
    
    for item in status_items:
        status = item.get("status", "")
        message = item.get("message", "")
        type_ = item.get("type", "info")
        
        if type_ == "warning":
            st.markdown(
                ui_styles.warning_box(status, message),
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                ui_styles.info_box(status, message),
                unsafe_allow_html=True
            )


def render_scorecard(scorecard: Dict[str, Any]):
    """
    Render a structured scorecard.
    
    Args:
        scorecard: Scorecard data structure
    """
    if not scorecard:
        st.warning("No scorecard data available.")
        return
    
    # Overall metrics
    st.markdown("### Overall Assessment")
    
    overall_rating = scorecard.get("overall_rating")
    if overall_rating is not None:
        try:
            rating_val = float(overall_rating)
            rating_display = f"{rating_val:.1f}"
        except (ValueError, TypeError):
            rating_display = str(overall_rating)
    else:
        rating_display = "N/A"
    
    metrics = [
        {"label": "Overall Rating", "value": rating_display},
        {"label": "Criteria Coverage", "value": f"{scorecard.get('criteria_coverage', 0) * 100:.1f}%"}
    ]
    
    metric_row(metrics, columns=2)
    
    # Key strengths and improvements
    col1, col2 = st.columns(2)
    
    with col1:
        insights_section("Key Strengths", scorecard.get("key_strengths", []))
    
    with col2:
        insights_section("Areas for Improvement", scorecard.get("key_improvements", []))
    
    # Executive summary
    exec_summary = scorecard.get("executive_summary")
    if exec_summary:
        with st.expander("Executive Summary", expanded=False):
            st.markdown(exec_summary)
    
    # Recommendations
    recommendations = scorecard.get("recommendations", [])
    if recommendations:
        with st.expander("Recommendations", expanded=False):
            for rec in recommendations:
                st.markdown(f"- {rec}")
    
    # Dimensions
    st.markdown("### Dimension Assessments")
    dimensions = scorecard.get("dimensions", [])
    
    if not dimensions:
        st.info("No dimension data available.")
        return
    
    # Create tabs for dimensions
    dimension_names = [dim.get("name", f"Dimension {i+1}") for i, dim in enumerate(dimensions)]
    tabs = st.tabs(dimension_names)
    
    # Fill each tab with the dimension data
    for i, (tab, dimension) in enumerate(zip(tabs, dimensions)):
        with tab:
            render_dimension(dimension)


def render_dimension(dimension: Dict[str, Any]):
    """
    Render a dimension from the scorecard.
    
    Args:
        dimension: Dimension data structure
    """
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
    
    st.markdown(f"#### {dim_name} - Rating: {rating_display}")
    
    # Strengths and weaknesses
    col1, col2 = st.columns(2)
    
    with col1:
        insights_section("Strengths", dimension.get("strengths", []))
    
    with col2:
        insights_section("Weaknesses", dimension.get("weaknesses", []))
    
    # Criteria
    st.markdown("#### Criteria")
    criteria = dimension.get("criteria", [])
    
    if not criteria:
        st.info("No criteria data available for this dimension.")
        return
    
    # Create dataframe for criteria
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
            "Confidence": confidence_display
        })
    
    # Display criteria table
    df = pd.DataFrame(criteria_data)
    st.dataframe(df, use_container_width=True)
    
    # Display criterion details in expanders
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
        
        with st.expander(f"{criterion_name} - Rating: {rating_display}"):
            st.markdown("**Rationale:**")
            st.write(criterion.get("rationale", "No rationale provided"))
            
            # Display evidence if available
            if "evidence" in criterion:
                st.markdown("**Evidence:**")
                for evidence in criterion.get("evidence", []):
                    st.markdown(
                        ui_styles.evidence_item(
                            evidence.get("text", "No text"), 
                            evidence.get("relevance", ""),
                            evidence.get("confidence")
                        ),
                        unsafe_allow_html=True
                    )


def render_evidence_report(evidence_report: Dict[str, Any]):
    """
    Render an evidence report.
    
    Args:
        evidence_report: Evidence report data structure
    """
    if not evidence_report:
        st.warning("No evidence report available.")
        return
    
    # Introduction
    st.markdown("### Evidence Report")
    st.markdown(evidence_report.get("introduction", ""))
    
    # Evidence map
    evidence_map = evidence_report.get("evidence_map", {})
    if not evidence_map:
        st.info("No evidence data available.")
        return
    
    # Display evidence by dimension
    for dimension_id, dimension_data in evidence_map.items():
        dimension_name = dimension_data.get("name", dimension_id)
        
        with st.expander(f"Dimension: {dimension_name}", expanded=False):
            criteria_data = dimension_data.get("criteria", {})
            
            if not criteria_data:
                st.info(f"No evidence for criteria in {dimension_name}")
                continue
            
            for criterion_id, criterion_data in criteria_data.items():
                criterion_name = criterion_data.get("name", criterion_id)
                criterion_question = criterion_data.get("question", "")
                evidence_list = criterion_data.get("evidence", [])
                
                st.markdown(f"#### {criterion_name}")
                if criterion_question:
                    st.markdown(f"*Question: {criterion_question}*")
                
                st.markdown(f"**{len(evidence_list)} evidence items found**")
                
                for evidence in evidence_list:
                    st.markdown(
                        ui_styles.evidence_item(
                            evidence.get("text", "No text"),
                            evidence.get("relevance", ""),
                            evidence.get("confidence")
                        ),
                        unsafe_allow_html=True
                    )
                
                st.markdown("---")


def render_visualization_data(viz_data: Dict[str, Any]):
    """
    Render visualization data.
    
    Args:
        viz_data: Visualization data structure
    """
    if not viz_data:
        st.warning("No visualization data available.")
        return
    
    st.markdown("### Visualization Data")
    
    # Radar chart data
    radar_data = viz_data.get("radar_chart", [])
    if radar_data:
        st.markdown("#### Dimension Ratings")
        
        radar_df = pd.DataFrame([
            {"Dimension": item.get("dimension"), "Rating": item.get("rating")}
            for item in radar_data
        ])
        
        st.dataframe(radar_df, use_container_width=True)
        
        # Simple bar chart
        st.bar_chart(radar_df.set_index("Dimension"))
    
    # Heatmap data
    heatmap_data = viz_data.get("heatmap", [])
    if heatmap_data:
        with st.expander("Criterion Ratings Heatmap", expanded=False):
            heatmap_df = pd.DataFrame([
                {
                    "Dimension": item.get("dimension"), 
                    "Criterion": item.get("criterion"), 
                    "Rating": item.get("rating")
                }
                for item in heatmap_data
            ])
            
            st.dataframe(heatmap_df, use_container_width=True)
    
    # Evidence distribution
    evidence_dist = viz_data.get("evidence_distribution", [])
    if evidence_dist:
        with st.expander("Evidence Distribution", expanded=False):
            evidence_df = pd.DataFrame([
                {"Dimension": item.get("dimension"), "Evidence Count": item.get("evidence_count")}
                for item in evidence_dist
            ])
            
            st.dataframe(evidence_df, use_container_width=True)
            
            # Simple bar chart
            st.bar_chart(evidence_df.set_index("Dimension"))
    
    # Rating distribution
    rating_dist = viz_data.get("rating_distribution", {})
    if rating_dist:
        with st.expander("Rating Distribution", expanded=False):
            rating_df = pd.DataFrame([
                {"Rating": rating, "Count": count}
                for rating, count in rating_dist.items()
            ])
            
            st.dataframe(rating_df, use_container_width=True)
            
            # Simple bar chart
            st.bar_chart(rating_df.set_index("Rating"))


def download_button(data, file_name, button_text="Download Data"):
    """
    Create a download button for structured data.
    
    Args:
        data: Data to download (dict or list)
        file_name: File name for download
        button_text: Text to display on button
    """
    json_data = json.dumps(data, indent=2)
    st.download_button(
        label=button_text,
        data=json_data,
        file_name=file_name,
        mime="application/json"
    )


def strategy_info(strategy_preview):
    """
    Display strategy information.
    
    Args:
        strategy_preview: Strategy preview data
    """
    if not strategy_preview:
        return
    
    with st.expander("Assessment Strategy", expanded=False):
        st.markdown("#### Strategy Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Strategy Type:** {strategy_preview.get('strategy_type', 'unknown')}")
            st.markdown(f"**Parallel Extractors:** {strategy_preview.get('total_extractors', 0)}")
        
        with col2:
            st.markdown(f"**Chunking Method:** {strategy_preview.get('chunking', {}).get('method', 'unknown')}")
            st.markdown(f"**Processing Sequence:** {', '.join(strategy_preview.get('processing_sequence', []))}")
        
        # Display agent information
        agents = strategy_preview.get("agents", [])
        if agents:
            st.markdown("#### Agents Configuration")
            
            for i, agent in enumerate(agents):
                agent_type = agent.get("type", "unknown")
                with st.expander(f"{agent_type} Agent", expanded=False):
                    st.json(agent)


def result_tabs(result):
    """
    Create tabs for different result formats.
    
    Args:
        result: Assessment result data
    """
    if not result:
        st.warning("No assessment result available.")
        return
    
    # Get reports
    reports = result.get("reports", {}).get("formats", {})
    
    # Determine available tabs
    available_tabs = ["Scorecard"]
    
    if "executive_summary" in reports:
        available_tabs.append("Executive Summary")
    
    if "detailed_assessment" in reports:
        available_tabs.append("Detailed Assessment")
    
    if "evidence_report" in reports:
        available_tabs.append("Evidence")
    
    if "visualization_data" in reports:
        available_tabs.append("Visualizations")
    
    # Create tabs
    tabs = st.tabs(available_tabs)
    
    # Fill tabs with content
    for i, tab_name in enumerate(available_tabs):
        with tabs[i]:
            if tab_name == "Scorecard":
                render_scorecard(reports.get("scorecard", {}))
            
            elif tab_name == "Executive Summary":
                st.markdown("### Executive Summary")
                summary = reports.get("executive_summary", {})
                st.markdown(summary.get("executive_summary", ""))
                
                recommendations = summary.get("recommendations", [])
                if recommendations:
                    st.markdown("### Recommendations")
                    for rec in recommendations:
                        st.markdown(f"- {rec}")
            
            elif tab_name == "Detailed Assessment":
                detailed = reports.get("detailed_assessment", {})
                st.markdown("### Detailed Assessment")
                st.markdown(detailed.get("introduction", ""))
                
                render_scorecard(detailed)
            
            elif tab_name == "Evidence":
                render_evidence_report(reports.get("evidence_report", {}))
            
            elif tab_name == "Visualizations":
                render_visualization_data(reports.get("visualization_data", {}))