"""
02_Assessment_Viewer - Enhanced viewer for Framework Assessment results

This page provides a comprehensive view of assessment results with 
clear visibility into the semantic layer and evidence collection process.
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
    page_title="Assessment Viewer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom styles
ui_styles.apply_styles()

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
    Display a simple assessment selection interface.
    
    Returns:
        Selected assessment data or None if no assessment selected
    """
    st.markdown("## Select an Assessment to View")
    
    # List assessment output files
    assessment_files = path_utils.list_files("outputs", ".json")
    
    if not assessment_files:
        st.info("No assessment results found. Please run an assessment first.")
        return None
    
    # Sort by modification time (newest first)
    assessment_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    # Create selection options
    file_options = []
    for file_path in assessment_files:
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
            "Select assessment to view",
            options=range(len(option_labels)),
            format_func=lambda i: option_labels[i]
        )
    
    with col2:
        st.write("")
        st.write("")
        load_button = st.button("Load Assessment", key="load_assessment_btn", type="primary")
    
    if load_button:
        selected_path = file_options[selected_index]["path"]
        try:
            # Load the selected assessment
            assessment_result = load_assessment_result(selected_path)
            
            # Store in session state
            st.session_state.assessment_viewer_result = assessment_result
            st.session_state.assessment_viewer_path = selected_path
            
            st.success(f"Loaded assessment: {file_options[selected_index]['name']}")
            return assessment_result
        except Exception as e:
            st.error(f"Failed to load assessment: {str(e)}")
            return None
    
    # Return from session state if available
    if "assessment_viewer_result" in st.session_state:
        return st.session_state.assessment_viewer_result
    
    return None

def display_overview(assessment_result: Dict[str, Any]):
    """
    Display a high-level overview of the assessment.
    
    Args:
        assessment_result: Assessment result data
    """
    st.markdown("## Assessment Overview")
    
    # Extract basic metadata
    metadata = assessment_result.get("metadata", {})
    statistics = assessment_result.get("statistics", {})
    scorecard = assessment_result.get("scorecard", {})
    
    # Create overview metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        framework_name = metadata.get("framework_name", "Unknown Framework")
        document_name = metadata.get("document_name", "Unknown Document")
        st.metric("Framework", framework_name)
        st.metric("Document", document_name)
    
    with col2:
        overall_rating = scorecard.get("overall_rating")
        if overall_rating is not None:
            try:
                rating_val = float(overall_rating)
                rating_display = f"{rating_val:.1f}"
            except (ValueError, TypeError):
                rating_display = str(overall_rating)
        else:
            rating_display = "N/A"
        
        criteria_coverage = statistics.get("assessment_coverage", 0)
        coverage_display = f"{criteria_coverage * 100:.1f}%" if criteria_coverage else "N/A"
        
        st.metric("Overall Rating", rating_display)
        st.metric("Criteria Coverage", coverage_display)
    
    with col3:
        total_evidence = statistics.get("total_evidence", 0)
        evidence_per_criterion = statistics.get("evidence_per_criterion", 0)
        
        st.metric("Total Evidence", total_evidence)
        st.metric("Evidence per Criterion", f"{evidence_per_criterion:.1f}")
    
    # Display assessment reliability info
    assessment_types = statistics.get("assessment_types", {})
    direct_count = assessment_types.get("direct", 0)
    inferred_count = assessment_types.get("inferred", 0)
    insufficient_count = assessment_types.get("insufficient_evidence", 0)
    
    total_count = direct_count + inferred_count + insufficient_count
    direct_percentage = (direct_count / max(1, total_count)) * 100
    
    # Create reliability display
    reliability_rating = "Low"
    reliability_color = "#FF6B6B"  # Red
    
    if direct_percentage >= 80:
        reliability_rating = "High"
        reliability_color = "#00CC96"  # Green
    elif direct_percentage >= 50:
        reliability_rating = "Medium"
        reliability_color = "#FFA15A"  # Orange
    
    st.markdown(
        f"""
        <div style="padding: 15px; background-color: #1F2937; border-radius: 10px; margin: 15px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="font-weight: 600; font-size: 1.1rem;">Assessment Reliability: 
                    <span style="color: {reliability_color};">{reliability_rating}</span>
                </div>
                <div>{direct_percentage:.1f}% Direct Assessments</div>
            </div>
            
            <div style="display: flex; margin-bottom: 10px; gap: 15px;">
                <div style="flex: 1; text-align: center; background-color: #00CC96; padding: 8px; border-radius: 5px;">
                    <div style="font-weight: 600;">{direct_count}</div>
                    <div style="font-size: 0.9rem;">Direct</div>
                </div>
                <div style="flex: 1; text-align: center; background-color: #FFA15A; padding: 8px; border-radius: 5px;">
                    <div style="font-weight: 600;">{inferred_count}</div>
                    <div style="font-size: 0.9rem;">Inferred</div>
                </div>
                <div style="flex: 1; text-align: center; background-color: #888888; padding: 8px; border-radius: 5px;">
                    <div style="font-weight: 600;">{insufficient_count}</div>
                    <div style="font-size: 0.9rem;">Insufficient</div>
                </div>
            </div>
            
            <div style="font-size: 0.9rem; color: #A0A0A0;">
                Assessment reliability is based on the percentage of criteria with direct evidence.
                Higher reliability indicates more of the assessment is backed by direct evidence rather than inference.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def display_semantic_layer(assessment_result: Dict[str, Any]):
    """
    Display semantic layer information from the assessment.
    
    Args:
        assessment_result: Assessment result data
    """
    st.markdown("## Semantic Layer Analysis")
    
    # Try to extract semantic group information from various locations
    strategy = assessment_result.get("strategy", {})
    semantic_groups = strategy.get("semantic_groups", [])
    
    # If semantic groups not found in strategy, check scorecard
    if not semantic_groups:
        scorecard = assessment_result.get("scorecard", {})
        semantic_groups = scorecard.get("semantic_groups", [])
    
    # If still not found, try reports
    if not semantic_groups:
        reports = assessment_result.get("reports", {}).get("formats", {})
        semantic_analysis = reports.get("semantic_analysis", {})
        semantic_groups = semantic_analysis.get("groups", [])
    
    if not semantic_groups:
        st.info("No semantic group information found in this assessment.")
        return
    
    st.markdown(f"### {len(semantic_groups)} Semantic Groups Identified")
    
    # Create a visualization of semantic groups and their criteria
    groups_data = []
    
    for group in semantic_groups:
        group_name = group.get("name", "Unknown Group")
        explanation = group.get("explanation", "")
        criteria_ids = group.get("criteria_ids", [])
        
        # Collect ratings for criteria in this group if available
        criteria_ratings = []
        for criterion_id in criteria_ids:
            # This would need to be enhanced to find actual ratings
            # For now, just collect the IDs
            criteria_ratings.append(criterion_id)
        
        groups_data.append({
            "name": group_name,
            "explanation": explanation,
            "criteria_count": len(criteria_ids),
            "criteria_ids": criteria_ids
        })
    
    # Display semantic groups as expandable cards
    for group in groups_data:
        with st.expander(f"{group['name']} - {group['criteria_count']} criteria", expanded=False):
            st.markdown(f"**Explanation:** {group['explanation']}")
            
            # Display criteria in this group
            if group["criteria_ids"]:
                st.markdown("**Criteria in this group:**")
                
                criteria_table = []
                for criterion_id in group["criteria_ids"]:
                    # This would need to be enhanced to find actual criterion name and ratings
                    # For now, just show the ID
                    criteria_table.append({
                        "ID": criterion_id,
                        "Criterion": find_criterion_name(assessment_result, criterion_id),
                        "Dimension": find_dimension_for_criterion(assessment_result, criterion_id)
                    })
                
                if criteria_table:
                    st.dataframe(pd.DataFrame(criteria_table), use_container_width=True)
    
    # Display cross-dimensional insights
    st.markdown("### Cross-Dimensional Insights")
    
    # Try to find semantic insights from overall assessment
    scorecard = assessment_result.get("scorecard", {})
    semantic_insights = scorecard.get("semantic_insights", "")
    
    if not semantic_insights:
        # Try to find in reports
        reports = assessment_result.get("reports", {}).get("formats", {})
        semantic_analysis = reports.get("semantic_analysis", {})
        semantic_insights = semantic_analysis.get("cross_cutting_insights", "")
    
    if semantic_insights:
        if isinstance(semantic_insights, list):
            for insight in semantic_insights:
                st.markdown(f"- {insight}")
        else:
            st.markdown(semantic_insights)
    else:
        st.info("No cross-dimensional insights found.")

def find_criterion_name(assessment_result: Dict[str, Any], criterion_id: str) -> str:
    """Find the name of a criterion by its ID."""
    # Look in framework data
    framework = assessment_result.get("framework", {})
    for dimension in framework.get("dimensions", []):
        for criterion in dimension.get("criteria", []):
            if criterion.get("id") == criterion_id:
                return criterion.get("name", criterion_id)
    
    # Look in scorecard
    scorecard = assessment_result.get("scorecard", {})
    for dimension in scorecard.get("dimensions", []):
        for criterion in dimension.get("criteria", []):
            if criterion.get("id") == criterion_id:
                return criterion.get("name", criterion_id)
    
    return criterion_id  # Fallback if not found

def find_dimension_for_criterion(assessment_result: Dict[str, Any], criterion_id: str) -> str:
    """Find the dimension name for a criterion by its ID."""
    # Look in framework data
    framework = assessment_result.get("framework", {})
    for dimension in framework.get("dimensions", []):
        dimension_name = dimension.get("name", "")
        for criterion in dimension.get("criteria", []):
            if criterion.get("id") == criterion_id:
                return dimension_name
    
    # Look in scorecard
    scorecard = assessment_result.get("scorecard", {})
    for dimension in scorecard.get("dimensions", []):
        dimension_name = dimension.get("name", "")
        for criterion in dimension.get("criteria", []):
            if criterion.get("id") == criterion_id:
                return dimension_name
    
    return "Unknown"  # Fallback if not found

def display_evidence_analysis(assessment_result: Dict[str, Any]):
    """
    Display evidence analysis and statistics.
    
    Args:
        assessment_result: Assessment result data
    """
    st.markdown("## Evidence Analysis")
    
    # Extract evidence report and statistics
    evidence_report = assessment_result.get("reports", {}).get("formats", {}).get("evidence_report", {})
    statistics = assessment_result.get("statistics", {})
    
    # Display evidence metrics
    total_evidence = statistics.get("total_evidence", 0)
    evidence_per_criterion = statistics.get("evidence_per_criterion", 0)
    average_confidence = statistics.get("average_confidence", 0)
    
    evidence_categories = {}
    
    # Look for evidence categories in statistics
    if "evidence_categories" in statistics:
        evidence_categories = statistics["evidence_categories"]
    
    # Alternative source for evidence categories
    viz_data = assessment_result.get("reports", {}).get("formats", {}).get("visualization_data", {})
    if not evidence_categories and "evidence_distribution" in viz_data:
        for dim_data in viz_data.get("evidence_distribution", []):
            if "evidence_categories" in dim_data:
                for category, count in dim_data["evidence_categories"].items():
                    if category not in evidence_categories:
                        evidence_categories[category] = 0
                    evidence_categories[category] += count
    
    # Create evidence summary section
    if total_evidence > 0:
        st.markdown(f"### {total_evidence} Total Evidence Items Collected")
        
        # Create category visualization
        if evidence_categories:
            # Prepare data for chart
            category_data = []
            for category, count in evidence_categories.items():
                if category != "total":  # Skip total count
                    # Determine category type and subtype
                    if "_" in category:
                        category_type, subtype = category.split("_", 1)
                        category_data.append({
                            "Category": category_type.title(),
                            "Subtype": subtype.title(),
                            "Count": count
                        })
                    else:
                        category_data.append({
                            "Category": category.title(),
                            "Subtype": "General",
                            "Count": count
                        })
            
            if category_data:
                df = pd.DataFrame(category_data)
                
                # Create grouped bar chart
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X('Category:N', title='Evidence Category'),
                    y=alt.Y('Count:Q', title='Number of Evidence Items'),
                    color=alt.Color('Subtype:N', scale=alt.Scale(scheme='category10')),
                    tooltip=['Category:N', 'Subtype:N', 'Count:Q']
                ).properties(
                    title='Evidence by Category and Subtype',
                    height=300
                )
                
                st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("No evidence items were collected during this assessment. This suggests an issue with the extraction process.")
    
    # Display evidence map if available
    evidence_map = evidence_report.get("evidence_map", {})
    
    if evidence_map:
        st.markdown("### Evidence Distribution by Dimension and Criterion")
        
        # Summarize evidence by dimension
        dimension_evidence = []
        for dimension_id, dimension_data in evidence_map.items():
            dimension_name = dimension_data.get("name", dimension_id)
            
            # Count total evidence in this dimension
            total_dimension_evidence = 0
            for criterion_data in dimension_data.get("criteria", {}).values():
                total_dimension_evidence += len(criterion_data.get("evidence", []))
            
            dimension_evidence.append({
                "Dimension": dimension_name,
                "Evidence Count": total_dimension_evidence
            })
        
        # Create bar chart
        if dimension_evidence:
            df = pd.DataFrame(dimension_evidence)
            
            chart = alt.Chart(df).mark_bar().encode(
                y=alt.Y('Dimension:N', sort='-x', title=None),
                x=alt.X('Evidence Count:Q', title='Evidence Count'),
                color=alt.Color('Evidence Count:Q', scale=alt.Scale(scheme='blueorange')),
                tooltip=['Dimension:N', 'Evidence Count:Q']
            ).properties(
                title='Evidence by Dimension',
                height=300
            )
            
            st.altair_chart(chart, use_container_width=True)
        
        # Create expandable sections for each dimension's evidence
        for dimension_id, dimension_data in evidence_map.items():
            dimension_name = dimension_data.get("name", dimension_id)
            criteria_data = dimension_data.get("criteria", {})
            
            # Count total evidence in this dimension
            total_dimension_evidence = 0
            for criterion_data in criteria_data.values():
                total_dimension_evidence += len(criterion_data.get("evidence", []))
            
            with st.expander(f"{dimension_name} - {total_dimension_evidence} evidence items", expanded=False):
                # Display criteria in this dimension
                for criterion_id, criterion_data in criteria_data.items():
                    criterion_name = criterion_data.get("name", criterion_id)
                    evidence_list = criterion_data.get("evidence", [])
                    
                    if evidence_list:
                        st.markdown(f"**{criterion_name}**: {len(evidence_list)} evidence items")
                        
                        # Optional: Display a sample evidence item
                        if evidence_list:
                            with st.expander("Sample Evidence", expanded=False):
                                for i, evidence in enumerate(evidence_list[:3]):  # Show up to 3 samples
                                    text = evidence.get("text", "No text")
                                    relevance = evidence.get("relevance_level", "Unknown")
                                    sentiment = evidence.get("sentiment", "Neutral")
                                    
                                    st.markdown(
                                        f"""
                                        <div style="border-left: 3px solid {'#00CC96' if sentiment == 'Positive' else '#FF6B6B' if sentiment == 'Negative' else '#888888'}; 
                                                padding: 10px; margin-bottom: 10px; background-color: #2E3440;">
                                            <div style="font-style: italic;">{text}</div>
                                            <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 0.8rem; color: #A0A0A0;">
                                                <div>Relevance: {relevance}</div>
                                                <div>Sentiment: {sentiment}</div>
                                            </div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
    else:
        st.info("Detailed evidence map not available in this assessment.")

def display_assessment_types(assessment_result: Dict[str, Any]):
    """
    Display assessment type analysis with direct vs. inferred breakdown.
    
    Args:
        assessment_result: Assessment result data
    """
    st.markdown("## Assessment Type Analysis")
    
    # Get scorecard for ratings
    scorecard = assessment_result.get("scorecard", {})
    dimensions = scorecard.get("dimensions", [])
    
    # Collect criteria with assessment types
    criteria_assessments = []
    
    for dimension in dimensions:
        dimension_name = dimension.get("name", "")
        
        for criterion in dimension.get("criteria", []):
            criterion_name = criterion.get("name", "")
            criterion_id = criterion.get("id", "")
            rating = criterion.get("rating")
            assessment_type = criterion.get("assessment_type", "unknown")
            confidence = criterion.get("confidence", None)
            
            criteria_assessments.append({
                "Dimension": dimension_name,
                "Criterion": criterion_name,
                "ID": criterion_id,
                "Rating": rating,
                "Assessment Type": assessment_type.title(),
                "Confidence": confidence
            })
    
    if not criteria_assessments:
        st.info("No assessment type information available.")
        return
    
    # Create chart showing assessment types
    df = pd.DataFrame(criteria_assessments)
    
    # Count by assessment type
    assessment_type_counts = df["Assessment Type"].value_counts().reset_index()
    assessment_type_counts.columns = ["Assessment Type", "Count"]
    
    # Assessment type pie chart
    if not assessment_type_counts.empty:
        pie_chart = alt.Chart(assessment_type_counts).mark_arc().encode(
            theta=alt.Theta(field="Count", type="quantitative"),
            color=alt.Color('Assessment Type:N', scale=alt.Scale(
                domain=['Direct', 'Inferred', 'Insufficient_Evidence'],
                range=['#00CC96', '#FFA15A', '#888888']
            )),
            tooltip=['Assessment Type:N', 'Count:Q']
        ).properties(
            title='Assessment Types Distribution',
            width=300,
            height=300
        )
        
        # Rating by assessment type
        if not df.empty and 'Rating' in df.columns:
            # Remove rows with NA ratings
            rating_df = df.dropna(subset=['Rating'])
            
            if not rating_df.empty:
                # Convert ratings to strings for grouping
                rating_df["Rating String"] = rating_df["Rating"].astype(str)
                
                # Count ratings by assessment type
                rating_counts = rating_df.groupby(["Assessment Type", "Rating String"]).size().reset_index(name='Count')
                
                rating_chart = alt.Chart(rating_counts).mark_bar().encode(
                    x=alt.X('Rating String:N', title='Rating'),
                    y=alt.Y('Count:Q', title='Number of Criteria'),
                    color=alt.Color('Assessment Type:N', scale=alt.Scale(
                        domain=['Direct', 'Inferred'],
                        range=['#00CC96', '#FFA15A']
                    )),
                    tooltip=['Assessment Type:N', 'Rating String:N', 'Count:Q']
                ).properties(
                    title='Ratings by Assessment Type',
                    width=400,
                    height=300
                )
                
                # Display charts side by side
                col1, col2 = st.columns(2)
                
                with col1:
                    st.altair_chart(pie_chart, use_container_width=True)
                
                with col2:
                    st.altair_chart(rating_chart, use_container_width=True)
            else:
                # Just show the pie chart if no ratings
                st.altair_chart(pie_chart, use_container_width=True)
    
    # Table of assessments with types
    st.markdown("### Assessment Details by Type")
    
    # Tabs for different assessment types
    assessment_tabs = st.tabs(["All Assessments", "Direct Assessments", "Inferred Assessments", "Insufficient Evidence"])
    
    with assessment_tabs[0]:
        # All assessments
        if not df.empty:
            # Format the confidence column
            if 'Confidence' in df.columns:
                df['Confidence'] = df['Confidence'].apply(
                    lambda x: f"{float(x):.2f}" if x is not None and not pd.isna(x) else "N/A"
                )
            
            # Format the rating column
            if 'Rating' in df.columns:
                df['Rating'] = df['Rating'].apply(
                    lambda x: f"{float(x):.1f}" if x is not None and not pd.isna(x) else "N/A"
                )
            
            st.dataframe(df, use_container_width=True)
    
    with assessment_tabs[1]:
        # Direct assessments
        direct_df = df[df["Assessment Type"] == "Direct"]
        if not direct_df.empty:
            st.dataframe(direct_df, use_container_width=True)
        else:
            st.info("No direct assessments found.")
    
    with assessment_tabs[2]:
        # Inferred assessments
        inferred_df = df[df["Assessment Type"] == "Inferred"]
        if not inferred_df.empty:
            st.dataframe(inferred_df, use_container_width=True)
        else:
            st.info("No inferred assessments found.")
    
    with assessment_tabs[3]:
        # Insufficient evidence
        insufficient_df = df[df["Assessment Type"] == "Insufficient_Evidence"]
        if not insufficient_df.empty:
            st.dataframe(insufficient_df, use_container_width=True)
        else:
            st.info("No assessments with insufficient evidence.")

def display_strategy_analysis(assessment_result: Dict[str, Any]):
    """
    Display assessment strategy information.
    
    Args:
        assessment_result: Assessment result data
    """
    st.markdown("## Assessment Strategy")
    
    # Extract strategy information
    strategy = assessment_result.get("strategy", {})
    
    if not strategy:
        st.info("No strategy information available in this assessment.")
        return
    
    # Basic strategy info
    strategy_type = strategy.get("strategy_type", "Unknown")
    rationale = strategy.get("rationale", "")
    
    # Chunking info
    chunking_strategy = strategy.get("chunking_strategy", {})
    chunking_method = chunking_strategy.get("method", "Unknown")
    chunk_size = chunking_strategy.get("size", "N/A")
    chunk_overlap = chunking_strategy.get("overlap", "N/A")
    
    # Agent info
    agents = strategy.get("agents", [])
    processing_sequence = strategy.get("processing_sequence", [])
    
    # Display strategy overview
    st.markdown("### Strategy Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Strategy Type:** {strategy_type}")
        st.markdown(f"**Chunking Method:** {chunking_method}")
        if chunking_method == "fixed_size":
            st.markdown(f"**Chunk Size:** {chunk_size} characters")
            st.markdown(f"**Chunk Overlap:** {chunk_overlap} characters")
    
    with col2:
        st.markdown(f"**Total Agents:** {len(agents)}")
        st.markdown(f"**Processing Sequence:** {', '.join(processing_sequence)}")
    
    if rationale:
        st.markdown(f"**Rationale:** {rationale}")
    
    # Display agent information
    if agents:
        st.markdown("### Agent Configuration")
        
        # Extract agent types
        agent_types = [agent.get("agent_type", "unknown") for agent in agents]
        
        # Count by agent type
        agent_type_counts = {}
        for agent_type in agent_types:
            if agent_type.startswith("extractor"):
                agent_type_counts["extractor"] = agent_type_counts.get("extractor", 0) + 1
            else:
                agent_type_counts[agent_type] = agent_type_counts.get(agent_type, 0) + 1
        
        # Display agent counts
        agent_count_html = "<div style='display: flex; gap: 15px; margin-bottom: 15px;'>"
        
        for agent_type, count in agent_type_counts.items():
            agent_count_html += f"""
            <div style="flex: 1; text-align: center; background-color: #1F2937; padding: 10px; border-radius: 5px;">
                <div style="font-weight: 600;">{count}</div>
                <div style="font-size: 0.9rem;">{agent_type.title()}</div>
            </div>
            """
        
        agent_count_html += "</div>"
        
        st.markdown(agent_count_html, unsafe_allow_html=True)
        
        # Show agent details in expanders
        for i, agent in enumerate(agents):
            agent_type = agent.get("agent_type", "unknown")
            with st.expander(f"{agent_type} Details", expanded=False):
                # Configuration
                st.markdown("**Configuration:**")
                st.json(agent.get("configuration", {}))
                
                # Instructions
                instructions = agent.get("instructions", "")
                if instructions:
                    st.markdown("**Instructions:**")
                    st.markdown(f"```\n{instructions}\n```")

def main():
    """Main function for the assessment viewer."""
    # Page title
    st.title("🧠 Assessment Viewer")
    st.markdown(
        """
        Comprehensive view of assessment results with visibility into the semantic layer, 
        evidence collection process, and assessment types.
        """
    )
    
    # Load selected assessment
    assessment_result = display_assessment_selection()
    
    if not assessment_result:
        # No assessment selected, display help text
        st.info("Select an assessment from the list above to view results.")
        return
    
    # Create tabs for different analysis views
    analysis_tabs = st.tabs([
        "Overview", 
        "Semantic Layer", 
        "Evidence Analysis", 
        "Assessment Types",
        "Strategy Analysis"
    ])
    
    with analysis_tabs[0]:
        # Overview tab
        display_overview(assessment_result)
    
    with analysis_tabs[1]:
        # Semantic Layer tab
        display_semantic_layer(assessment_result)
    
    with analysis_tabs[2]:
        # Evidence Analysis tab
        display_evidence_analysis(assessment_result)
    
    with analysis_tabs[3]:
        # Assessment Types tab
        display_assessment_types(assessment_result)
    
    with analysis_tabs[4]:
        # Strategy Analysis tab
        display_strategy_analysis(assessment_result)
    
    # Add download button for the full assessment
    st.download_button(
        "Download Full Assessment",
        data=json.dumps(assessment_result, indent=2),
        file_name="assessment_result.json",
        mime="application/json"
    )

if __name__ == "__main__":
    main()