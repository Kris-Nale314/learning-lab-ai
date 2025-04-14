"""
UI Results Display - Enhanced display for Framework Assessment Workbench

Improved display of assessment results with clear distinction between assessment types,
professional styling, and better evidence categorization visualization.
"""

import json
import streamlit as st
import pandas as pd
import altair as alt
from typing import Dict, Any, List, Optional, Callable, Tuple, Union

from utils import ui_components
from utils import ui_styles

def display_assessment_results(result, strategy_preview):
    """
    Display assessment results with enhanced styling and assessment type distinction.
    
    Args:
        result: Assessment result data in UI-ready format
        strategy_preview: Strategy preview data
    """
    if not result:
        st.info("No assessment results available.")
        return
    
    # Add a success message if no errors
    if "error" not in result and not result.get("errors"):
        # Don't show success message here - progress tracker already shows it
        pass
    
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
    
    # Get the scorecard - now we expect it to be in a standard location
    scorecard = result.get("scorecard")
    
    # Display assessment in tabs
    result_tabs = st.tabs(["Scorecard", "Evidence Summary", "Assessment Details", "Visualizations"])
    
    with result_tabs[0]:  # Scorecard tab
        display_scorecard(scorecard)
    
    with result_tabs[1]:  # Evidence Summary tab
        display_evidence_summary(result)
        
    with result_tabs[2]:  # Assessment Details tab
        display_assessment_details(result, strategy_preview)
        
    with result_tabs[3]:  # Visualizations tab
        display_visualizations(result)
    
    # Add download button for full results
    st.download_button(
        "Download Full Results",
        data=json.dumps(result, indent=2),
        file_name="assessment_result.json",
        mime="application/json"
    )

def display_scorecard(scorecard: Dict[str, Any]):
    """
    Display a structured assessment scorecard with enhanced styling.
    
    Args:
        scorecard: Scorecard data
    """
    if not scorecard:
        st.info("No scorecard data available.")
        return
    
    # Display scorecard title
    st.markdown(f"## {scorecard.get('title', 'Assessment Scorecard')}")
    
    # Overall metrics
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
    
    # Get assessment reliability and types
    assessment_types = scorecard.get("assessment_types", {})
    direct_count = assessment_types.get("direct", 0)
    inferred_count = assessment_types.get("inferred", 0)
    insufficient_count = assessment_types.get("insufficient_evidence", 0)
    assessment_reliability = scorecard.get("assessment_reliability", "Unknown")
    
    # Display metrics in a 3-column layout
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Overall Rating with styling based on value
        if overall_rating is not None:
            color = ui_styles.rating_color(rating_display)
            st.markdown(
                f"""
                <div class="rating-card" style="border-left-color: {color};">
                    <div style="text-align: center; font-size: 2.5rem; color: {color};">{rating_display}</div>
                    <div style="text-align: center; font-weight: 600;">Overall Rating</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div class="rating-card">
                    <div style="text-align: center; font-size: 2.5rem; color: #888;">N/A</div>
                    <div style="text-align: center; font-weight: 600;">Overall Rating</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    with col2:
        # Assessment Reliability
        reliability_colors = {
            "High": "#00CC96",
            "Medium": "#FFA15A",
            "Low": "#EF553B",
            "Unknown": "#888888"
        }
        reliability_color = reliability_colors.get(assessment_reliability, "#888888")
        
        st.markdown(
            f"""
            <div class="rating-card" style="border-left-color: {reliability_color};">
                <div style="text-align: center; font-size: 1.5rem; color: {reliability_color};">{assessment_reliability}</div>
                <div style="text-align: center; font-weight: 600;">Assessment Reliability</div>
                <div style="text-align: center; font-size: 0.8rem; color: #888;">
                    Based on evidence quality
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        # Assessment Type Distribution
        total_count = direct_count + inferred_count + insufficient_count
        # Prevent division by zero
        safe_total = max(1, total_count)
        
        direct_percent = (direct_count / safe_total) * 100
        inferred_percent = (inferred_count / safe_total) * 100
        insufficient_percent = (insufficient_count / safe_total) * 100
        
        st.markdown(
            f"""
            <div class="rating-card">
                <div style="display: flex; justify-content: space-between; font-size: 0.9rem;">
                    <div style="color: #00CC96;">{direct_count} Direct</div>
                    <div style="color: #FFA15A;">{inferred_count} Inferred</div>
                    <div style="color: #888888;">{insufficient_count} N/A</div>
                </div>
                <div style="height: 8px; background-color: #e0e0e0; border-radius: 4px; margin: 8px 0;">
                    <div style="display: flex; height: 100%; border-radius: 4px;">
                        <div style="width: {direct_percent}%; 
                                 background-color: #00CC96; border-radius: 4px 0 0 4px;"></div>
                        <div style="width: {inferred_percent}%; 
                                 background-color: #FFA15A;"></div>
                        <div style="width: {insufficient_percent}%; 
                                 background-color: #888888; border-radius: 0 4px 4px 0;"></div>
                    </div>
                </div>
                <div style="text-align: center; font-weight: 600;">Assessment Types</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Display executive summary
    exec_summary = scorecard.get("executive_summary")
    if exec_summary:
        st.markdown("### Executive Summary")
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
        st.markdown("### Recommendations")
        for rec in recommendations:
            st.markdown(f"- {rec}")
    
    # Display dimensions accordion
    st.markdown("### Dimension Assessments")
    
    dimensions = scorecard.get("dimensions", [])
    if not dimensions:
        st.info("No dimension data available.")
        return
    
    # Create dimension accordions
    for dimension in dimensions:
        dim_name = dimension.get("name", "Unnamed Dimension")
        dim_rating = dimension.get("average_rating")
        
        # Format rating for display
        if dim_rating is not None:
            try:
                rating_val = float(dim_rating)
                rating_display = f"{rating_val:.1f}"
            except (ValueError, TypeError):
                rating_display = str(dim_rating)
        else:
            rating_display = "N/A"
        
        # Create dimension accordion
        with st.expander(f"{dim_name} - Rating: {rating_display}"):
            display_dimension(dimension)

def display_dimension(dimension: Dict[str, Any]):
    """
    Display dimension assessment in an enhanced format with assessment type indicators.
    
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
    
    # Display criteria with assessment type indicators
    criteria = dimension.get("criteria", [])
    if not criteria:
        st.info("No criteria data available for this dimension.")
        return
    
    st.markdown("#### Criteria Assessments")
    
    # Display each criterion in a card format with assessment type indicator
    for criterion in criteria:
        criterion_name = criterion.get("name", criterion.get("id", "Unknown"))
        rating = criterion.get("rating")
        assessment_type = criterion.get("assessment_type", "direct")
        
        if rating is not None:
            try:
                rating_val = float(rating)
                rating_display = f"{rating_val:.1f}"
            except (ValueError, TypeError):
                rating_display = str(rating)
        else:
            rating_display = "N/A"
        
        # Get confidence if available
        confidence = criterion.get("confidence", "N/A")
        if confidence not in (None, "N/A"):
            try:
                confidence_val = float(confidence)
                confidence_display = f"{confidence_val:.2f}"
            except (ValueError, TypeError):
                confidence_display = str(confidence)
        else:
            confidence_display = "N/A"
        
        # Determine badge style based on assessment type
        if assessment_type == "direct":
            badge_color = "#00CC96"  # Green for direct
            badge_text = "Direct"
        elif assessment_type == "inferred":
            badge_color = "#FFA15A"  # Orange for inferred
            badge_text = "Inferred"
        else:
            badge_color = "#888888"  # Gray for unknown/NA
            badge_text = "N/A"
        
        # Calculate card border color based on rating
        if rating is not None:
            border_color = ui_styles.rating_color(rating_display)
        else:
            border_color = "#888888"  # Gray for N/A
        
        # Criterion rationale
        rationale = criterion.get("rationale", "No rationale provided")
        
        # Display criterion card
        st.markdown(
            f"""
            <div class="criterion-card" style="border-left-color: {border_color}; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="font-weight: bold; font-size: 1.1em;">{criterion_name}</div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="background-color: {badge_color}; color: white; 
                               padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">
                            {badge_text}
                        </span>
                        <span style="background-color: {border_color}; color: white; 
                               padding: 2px 8px; border-radius: 12px; font-weight: bold;">
                            {rating_display}
                        </span>
                    </div>
                </div>
                <div style="margin-top: 5px; font-style: italic; color: #A0A0A0;">
                    {rationale}
                </div>
                <div style="display: flex; justify-content: flex-end; margin-top: 5px; font-size: 0.8em; color: #A0A0A0;">
                    Confidence: {confidence_display}
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )

def display_evidence_summary(result: Dict[str, Any]):
    """
    Display evidence summary with enhanced categorization.
    
    Args:
        result: Assessment result data
    """
    # Get evidence report from formats if available
    evidence_report = result.get("reports", {}).get("formats", {}).get("evidence_report")
    
    if not evidence_report:
        st.info("No evidence summary available for this assessment.")
        return
    
    # Display report title and introduction
    st.markdown(f"## {evidence_report.get('title', 'Evidence Report')}")
    st.markdown(evidence_report.get("introduction", ""))
    
    # Get evidence map and total count
    evidence_map = evidence_report.get("evidence_map", {})
    total_evidence = evidence_report.get("total_evidence", 0)
    
    # Display total evidence count
    st.markdown(f"**Total Evidence Items:** {total_evidence}")
    
    # Create visualization of evidence distribution by relevance and sentiment
    st.markdown("### Evidence Distribution")
    
    # Collect evidence category data
    category_data = []
    
    for dimension_id, dimension_data in evidence_map.items():
        dimension_name = dimension_data.get("name", dimension_id)
        
        for criterion_id, criterion_data in dimension_data.get("criteria", {}).items():
            criterion_name = criterion_data.get("name", criterion_id)
            
            # Get category counts
            evidence_by_category = criterion_data.get("evidence_by_category", {})
            
            for category, count in evidence_by_category.items():
                # Parse category to get relevance and sentiment
                if "_" in category:
                    relevance, sentiment = category.split("_", 1)
                    category_data.append({
                        "Dimension": dimension_name,
                        "Criterion": criterion_name,
                        "Relevance": relevance.title(),
                        "Sentiment": sentiment.title(),
                        "Count": count
                    })
    
    # Create dataframe from category data
    if category_data:
        category_df = pd.DataFrame(category_data)
        
        # Create relevance distribution chart
        relevance_chart = alt.Chart(category_df).mark_bar().encode(
            x=alt.X('sum(Count):Q', title='Evidence Count'),
            y=alt.Y('Relevance:N', title='Relevance Level'),
            color=alt.Color('Relevance:N', scale=alt.Scale(
                domain=['Direct', 'Indirect', 'Contextual', 'Implied'],
                range=['#00CC96', '#FFA15A', '#AB63FA', '#636EFA']
            )),
            tooltip=['Relevance:N', 'sum(Count):Q']
        ).properties(
            title='Evidence by Relevance Level',
            width=400,
            height=200
        )
        
        # Create sentiment distribution chart
        sentiment_chart = alt.Chart(category_df).mark_bar().encode(
            x=alt.X('sum(Count):Q', title='Evidence Count'),
            y=alt.Y('Sentiment:N', title='Sentiment'),
            color=alt.Color('Sentiment:N', scale=alt.Scale(
                domain=['Positive', 'Negative', 'Neutral'],
                range=['#00CC96', '#EF553B', '#636EFA']
            )),
            tooltip=['Sentiment:N', 'sum(Count):Q']
        ).properties(
            title='Evidence by Sentiment',
            width=400,
            height=200
        )
        
        # Display charts side by side
        col1, col2 = st.columns(2)
        with col1:
            st.altair_chart(relevance_chart, use_container_width=True)
        with col2:
            st.altair_chart(sentiment_chart, use_container_width=True)
    
    # Display evidence by dimension and criterion
    st.markdown("### Evidence by Dimension and Criterion")
    
    # Create dimension accordions
    for dimension_id, dimension_data in evidence_map.items():
        dimension_name = dimension_data.get("name", dimension_id)
        criteria_data = dimension_data.get("criteria", {})
        
        # Count total evidence in this dimension
        dimension_evidence_count = sum(
            len(criterion_data.get("evidence", []))
            for criterion_data in criteria_data.values()
        )
        
        with st.expander(f"{dimension_name} - {dimension_evidence_count} evidence items"):
            # Create criterion accordions
            for criterion_id, criterion_data in criteria_data.items():
                criterion_name = criterion_data.get("name", criterion_id)
                criterion_question = criterion_data.get("question", "")
                evidence_list = criterion_data.get("evidence", [])
                
                st.markdown(f"#### {criterion_name}")
                if criterion_question:
                    st.markdown(f"*Question: {criterion_question}*")
                
                st.markdown(f"**{len(evidence_list)} evidence items found**")
                
                # Create relevance/sentiment tabs for evidence
                if evidence_list:
                    # Group evidence by relevance
                    by_relevance = {}
                    for evidence in evidence_list:
                        relevance = evidence.get("relevance_level", "Direct")
                        if relevance not in by_relevance:
                            by_relevance[relevance] = []
                        by_relevance[relevance].append(evidence)
                    
                    # Create tabs for each relevance level
                    relevance_levels = [r for r in ["Direct", "Indirect", "Contextual", "Implied"] if r in by_relevance]
                    
                    if relevance_levels:
                        tabs = st.tabs(relevance_levels)
                        
                        for i, level in enumerate(relevance_levels):
                            with tabs[i]:
                                # Display evidence in this relevance level
                                for evidence in by_relevance[level]:
                                    display_evidence_item(evidence)

def display_evidence_item(evidence: Dict[str, Any]):
    """
    Display an evidence item with enhanced styling.
    
    Args:
        evidence: Evidence item data
    """
    # Get evidence data
    text = evidence.get("text", "No text")
    relevance = evidence.get("relevance", "")
    confidence = evidence.get("confidence")
    sentiment = evidence.get("sentiment", "Neutral")
    
    # Determine sentiment color
    sentiment_colors = {
        "Positive": "#00CC96",  # Green
        "Negative": "#EF553B",  # Red
        "Neutral": "#636EFA"    # Blue
    }
    sentiment_color = sentiment_colors.get(sentiment, "#636EFA")
    
    # Format confidence display
    if confidence is not None:
        try:
            confidence_val = float(confidence)
            confidence_display = f"{confidence_val:.2f}"
        except (ValueError, TypeError):
            confidence_display = str(confidence)
    else:
        confidence_display = "N/A"
    
    # Display evidence card
    st.markdown(
        f"""
        <div class="evidence-card" style="border-left-color: {sentiment_color};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="background-color: {sentiment_color}; color: white; 
                       padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">
                    {sentiment}
                </span>
                <span style="color: #A0A0A0; font-size: 0.8em;">
                    Confidence: {confidence_display}
                </span>
            </div>
            <div style="font-style: italic; margin-bottom: 8px; padding: 10px; 
                     background-color: rgba(0, 0, 0, 0.1); border-radius: 5px;">
                "{text}"
            </div>
            <div style="color: #A0A0A0; font-size: 0.9em;">
                {relevance}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def display_assessment_details(result: Dict[str, Any], strategy_preview: Optional[Dict[str, Any]]):
    """
    Display detailed assessment information and strategy.
    
    Args:
        result: Assessment result data
        strategy_preview: Strategy preview data
    """
    # Create tabs for different details
    details_tabs = st.tabs(["Assessment Strategy", "Assessment Metadata", "Assessment Statistics"])
    
    with details_tabs[0]:
        display_strategy_preview(strategy_preview)
    
    with details_tabs[1]:
        display_assessment_metadata(result)
    
    with details_tabs[2]:
        display_assessment_statistics(result)

def display_strategy_preview(strategy_preview: Optional[Dict[str, Any]]):
    """
    Display assessment strategy information.
    
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
        st.metric("Strategy Type", strategy_preview.get("strategy_type", "unknown"))
    
    with col2:
        extractor_count = strategy_preview.get("total_extractors", 0)
        st.metric("Extractors", extractor_count)
    
    with col3:
        chunking_method = strategy_preview.get("chunking", {}).get("method", "unknown")
        st.metric("Chunking Method", chunking_method)
    
    # Display rationale
    rationale = strategy_preview.get("rationale", "")
    if rationale:
        st.markdown("#### Strategy Rationale")
        st.markdown(rationale)
    
    # Display chunking info
    chunking = strategy_preview.get("chunking", {})
    if chunking:
        st.markdown("#### Chunking Strategy")
        
        # Create a formatted card for chunking info
        chunking_rationale = chunking.get("rationale", "")
        chunking_size = chunking.get("size", 0)
        chunking_overlap = chunking.get("overlap", 0)
        
        st.markdown(
            f"""
            <div class="info-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Method:</div>
                    <div>{chunking.get("method", "unknown")}</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Chunk Size:</div>
                    <div>{chunking_size} characters</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Overlap:</div>
                    <div>{chunking_overlap} characters</div>
                </div>
                <div style="margin-top: 10px; color: #A0A0A0; font-size: 0.9em;">
                    {chunking_rationale}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Display processing sequence
    sequence = strategy_preview.get("processing_sequence", [])
    if sequence:
        st.markdown("#### Processing Sequence")
        
        # Display as a horizontal sequence with arrows
        sequence_html = '<div style="display: flex; align-items: center; flex-wrap: wrap; gap: 5px;">'
        for i, step in enumerate(sequence):
            # Add arrow between steps
            if i > 0:
                sequence_html += '<div style="color: #A0A0A0; font-size: 1.2rem;">→</div>'
            
            # Add step with styling
            sequence_html += f'<div style="background-color: #2C3E50; padding: 8px 15px; border-radius: 15px;">{step}</div>'
        
        sequence_html += '</div>'
        st.markdown(sequence_html, unsafe_allow_html=True)
    
    # Display agent information
    agents = strategy_preview.get("agents", [])
    if agents:
        st.markdown("#### Agent Configuration")
        
        for i, agent in enumerate(agents):
            agent_type = agent.get("type", "unknown")
            
            with st.expander(f"{agent_type} Agent"):
                # Display agent configuration
                configuration = agent.get("configuration", {})
                instructions = agent.get("instructions", "")
                
                if configuration:
                    st.markdown("**Configuration:**")
                    st.json(configuration)
                
                if instructions:
                    st.markdown("**Instructions:**")
                    st.markdown(instructions)

def display_assessment_metadata(result: Dict[str, Any]):
    """
    Display assessment metadata.
    
    Args:
        result: Assessment result data
    """
    metadata = result.get("metadata", {})
    if not metadata:
        st.info("No metadata available.")
        return
    
    st.markdown("### Assessment Metadata")
    
    # Display key metadata
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Framework Information")
        
        st.markdown(
            f"""
            <div class="info-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Framework:</div>
                    <div>{metadata.get("framework_name", "Unknown")}</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Framework ID:</div>
                    <div>{metadata.get("framework_id", "unknown")}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown("#### Document Information")
        
        st.markdown(
            f"""
            <div class="info-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Document:</div>
                    <div>{metadata.get("document_name", "Unknown")}</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Document Length:</div>
                    <div>{metadata.get("document_length", 0):,} characters</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Display processing information
    st.markdown("#### Processing Information")
    
    processing_time = metadata.get("processing_time", 0)
    generated_at = metadata.get("generated_at", "Unknown")
    
    st.markdown(
        f"""
        <div class="info-card">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <div style="font-weight: 500;">Generated At:</div>
                <div>{generated_at}</div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <div style="font-weight: 500;">Processing Time:</div>
                <div>{processing_time:.2f} seconds</div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <div style="font-weight: 500;">Report Type:</div>
                <div>{metadata.get("report_type", "scorecard")}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def display_assessment_statistics(result: Dict[str, Any]):
    """
    Display assessment statistics.
    
    Args:
        result: Assessment result data
    """
    statistics = result.get("statistics", {})
    if not statistics:
        st.info("No statistics available.")
        return
    
    st.markdown("### Assessment Statistics")
    
    # Display key statistics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Coverage Statistics")
        
        total_criteria = statistics.get("total_criteria", 0)
        assessed_criteria = statistics.get("assessed_criteria", 0)
        assessment_coverage = statistics.get("assessment_coverage", 0)
        
        st.markdown(
            f"""
            <div class="info-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Total Criteria:</div>
                    <div>{total_criteria}</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Assessed Criteria:</div>
                    <div>{assessed_criteria}</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Coverage:</div>
                    <div>{assessment_coverage * 100:.1f}%</div>
                </div>
                <div style="margin-top: 10px; height: 8px; background-color: #e0e0e0; border-radius: 4px;">
                    <div style="height: 100%; width: {assessment_coverage * 100}%; 
                             background-color: #00CC96; border-radius: 4px;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown("#### Evidence Statistics")
        
        total_evidence = statistics.get("total_evidence", 0)
        evidence_per_criterion = statistics.get("evidence_per_criterion", 0)
        average_confidence = statistics.get("average_confidence", 0)
        
        st.markdown(
            f"""
            <div class="info-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Total Evidence:</div>
                    <div>{total_evidence}</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Evidence per Criterion:</div>
                    <div>{evidence_per_criterion:.2f}</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-weight: 500;">Average Confidence:</div>
                    <div>{average_confidence:.2f}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Display dimension statistics
    dimensions = statistics.get("dimensions", {})
    if dimensions:
        st.markdown("#### Dimension Statistics")
        
        dimension_stats = []
        for dimension_id, stats in dimensions.items():
            dimension_name = "Unknown"
            for dim in result.get("framework", {}).get("dimensions", []):
                if dim.get("id") == dimension_id:
                    dimension_name = dim.get("name", dimension_id)
                    break
            
            dimension_stats.append({
                "Dimension": dimension_name,
                "Total Criteria": stats.get("total_criteria", 0),
                "Assessed Criteria": stats.get("assessed_criteria", 0),
                "Coverage": stats.get("coverage", 0)
            })
        
        # Create dataframe
        if dimension_stats:
            stats_df = pd.DataFrame(dimension_stats)
            
            # Format coverage as percentage
            stats_df["Coverage"] = stats_df["Coverage"].apply(lambda x: f"{x * 100:.1f}%")
            
            # Display as table
            st.dataframe(stats_df, use_container_width=True)

def display_visualizations(result: Dict[str, Any]):
    """
    Display assessment visualizations.
    
    Args:
        result: Assessment result data
    """
    # Get visualization data
    viz_data = result.get("reports", {}).get("formats", {}).get("visualization_data", {})
    
    if not viz_data:
        st.info("No visualization data available.")
        return
    
    st.markdown("### Assessment Visualizations")
    
    # Create tabs for different visualizations
    viz_tabs = st.tabs(["Rating Breakdown", "Evidence Distribution", "Assessment Types"])
    
    with viz_tabs[0]:
        display_rating_visualizations(viz_data)
    
    with viz_tabs[1]:
        display_evidence_visualizations(viz_data)
    
    with viz_tabs[2]:
        display_assessment_type_visualizations(viz_data)

def display_rating_visualizations(viz_data: Dict[str, Any]):
    """
    Display rating visualizations.
    
    Args:
        viz_data: Visualization data
    """
    st.markdown("#### Ratings by Dimension")
    
    # Get radar chart data
    radar_data = viz_data.get("radar_chart", [])
    
    if radar_data:
        # Convert to dataframe
        radar_df = pd.DataFrame(radar_data)
        
        # Create horizontal bar chart
        radar_chart = alt.Chart(radar_df).mark_bar().encode(
            x=alt.X('rating:Q', title='Rating'),
            y=alt.Y('dimension:N', title=None, sort='-x'),
            color=alt.Color('rating:Q', scale=alt.Scale(scheme='blueorange'), legend=None),
            tooltip=['dimension:N', 'rating:Q']
        ).properties(
            height=300
        )
        
        # Display chart
        st.altair_chart(radar_chart, use_container_width=True)
    
    # Display rating distribution
    st.markdown("#### Rating Distribution")
    
    # Get rating distribution
    rating_dist = viz_data.get("rating_distribution", {})
    
    if rating_dist:
        # Convert to dataframe
        dist_data = [{"Rating": rating, "Count": count} for rating, count in rating_dist.items()]
        dist_df = pd.DataFrame(dist_data)
        
        # Create bar chart
        dist_chart = alt.Chart(dist_df).mark_bar().encode(
            x=alt.X('Rating:N', title='Rating'),
            y=alt.Y('Count:Q', title='Criteria Count'),
            color=alt.Color('Rating:N', scale=alt.Scale(scheme='blueorange')),
            tooltip=['Rating:N', 'Count:Q']
        ).properties(
            height=300
        )
        
        # Display chart
        st.altair_chart(dist_chart, use_container_width=True)
    
    # Display heatmap
    st.markdown("#### Rating Heatmap")
    
    # Get heatmap data
    heatmap_data = viz_data.get("heatmap", [])
    
    if heatmap_data:
        # Convert to dataframe
        heatmap_df = pd.DataFrame(heatmap_data)
        
        # Create heatmap
        heatmap_chart = alt.Chart(heatmap_df).mark_rect().encode(
            x=alt.X('criterion:N', title=None),
            y=alt.Y('dimension:N', title=None),
            color=alt.Color('rating:Q', scale=alt.Scale(scheme='blueorange'), legend=alt.Legend(title="Rating")),
            tooltip=['dimension:N', 'criterion:N', 'rating:Q']
        ).properties(
            width=400,
            height=300
        )
        
        # Display chart
        st.altair_chart(heatmap_chart, use_container_width=True)

def display_evidence_visualizations(viz_data: Dict[str, Any]):
    """
    Display evidence visualizations.
    
    Args:
        viz_data: Visualization data
    """
    st.markdown("#### Evidence by Dimension")
    
    # Get evidence distribution
    evidence_dist = viz_data.get("evidence_distribution", [])
    
    if evidence_dist:
        # Convert to dataframe
        dist_df = pd.DataFrame(evidence_dist)
        
        # Create bar chart
        dist_chart = alt.Chart(dist_df).mark_bar().encode(
            x=alt.X('evidence_count:Q', title='Evidence Count'),
            y=alt.Y('dimension:N', title=None, sort='-x'),
            color=alt.Color('evidence_count:Q', scale=alt.Scale(scheme='bluepurple'), legend=None),
            tooltip=['dimension:N', 'evidence_count:Q']
        ).properties(
            height=300
        )
        
        # Display chart
        st.altair_chart(dist_chart, use_container_width=True)
    
    # If we have evidence categories in the dimensions, show a breakdown
    category_data = []
    for dim_data in evidence_dist:
        dimension = dim_data.get("dimension", "Unknown")
        categories = dim_data.get("evidence_categories", {})
        
        # Add each category as a row
        for category, count in categories.items():
            if category != "total" and count > 0:  # Skip 'total' and zero counts
                category_type = category.split("_")[0] if "_" in category else category
                category_data.append({
                    "Dimension": dimension,
                    "Category": category_type.title(),
                    "Count": count
                })
    
    if category_data:
        st.markdown("#### Evidence by Category")
        
        # Convert to dataframe
        cat_df = pd.DataFrame(category_data)
        
        # Create grouped bar chart
        cat_chart = alt.Chart(cat_df).mark_bar().encode(
            x=alt.X('Dimension:N', title=None),
            y=alt.Y('Count:Q', title='Evidence Count'),
            color=alt.Color('Category:N', scale=alt.Scale(
                domain=['Direct', 'Indirect', 'Contextual', 'Positive', 'Negative', 'Neutral'],
                range=['#00CC96', '#FFA15A', '#636EFA', '#19D3F3', '#FF6692', '#B6E880']
            )),
            tooltip=['Dimension:N', 'Category:N', 'Count:Q']
        ).properties(
            height=300
        )
        
        # Display chart
        st.altair_chart(cat_chart, use_container_width=True)

def display_assessment_type_visualizations(viz_data: Dict[str, Any]):
    """
    Display assessment type visualizations.
    
    Args:
        viz_data: Visualization data
    """
    # Get assessment type distribution
    assessment_types = viz_data.get("assessment_type_distribution", [])
    
    if assessment_types:
        st.markdown("#### Assessment Type Distribution")
        
        # Convert to dataframe
        types_df = pd.DataFrame(assessment_types)
        
        # Create pie chart
        chart = alt.Chart(types_df).mark_arc().encode(
            theta=alt.Theta(field="count", type="quantitative"),
            color=alt.Color(field="type", type="nominal", scale=alt.Scale(
                domain=['direct', 'inferred', 'insufficient_evidence'],
                range=['#00CC96', '#FFA15A', '#888888']
            )),
            tooltip=['type:N', 'count:Q']
        ).properties(
            width=400,
            height=400,
            title='Assessment Types'
        )
        
        # Display chart
        st.altair_chart(chart, use_container_width=True)
    
    # Get rating by assessment type 
    rating_by_type = viz_data.get("rating_by_assessment_type", {})
    
    if rating_by_type:
        st.markdown("#### Ratings by Assessment Type")
        
        # Prepare data for visualization
        type_rating_data = []
        
        for assessment_type, ratings in rating_by_type.items():
            for rating, count in ratings.items():
                type_rating_data.append({
                    "Assessment Type": assessment_type.title(),
                    "Rating": rating,
                    "Count": count
                })
        
        if type_rating_data:
            # Convert to dataframe
            type_rating_df = pd.DataFrame(type_rating_data)
            
            # Create grouped bar chart
            type_rating_chart = alt.Chart(type_rating_df).mark_bar().encode(
                x=alt.X('Rating:N', title='Rating'),
                y=alt.Y('Count:Q', title='Criteria Count'),
                color=alt.Color('Assessment Type:N', scale=alt.Scale(
                    domain=['Direct', 'Inferred'],
                    range=['#00CC96', '#FFA15A']
                )),
                tooltip=['Assessment Type:N', 'Rating:N', 'Count:Q']
            ).properties(
                height=300
            )
            
            # Display chart
            st.altair_chart(type_rating_chart, use_container_width=True)
    
    # Create comparison metrics
    key_metrics = viz_data.get("key_metrics", {})
    
    if key_metrics:
        st.markdown("#### Assessment Reliability Metrics")
        
        # Extract metrics
        direct_percentage = key_metrics.get("direct_assessment_percentage", 0)
        reliability = key_metrics.get("assessment_reliability", "Unknown")
        
        # Display metrics in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Format percentage
            direct_pct_display = f"{direct_percentage * 100:.1f}%"
            st.metric("Direct Assessments", direct_pct_display)
        
        with col2:
            st.metric("Assessment Reliability", reliability)
        
        with col3:
            criteria_assessed = key_metrics.get("criteria_assessed", 0)
            st.metric("Criteria Assessed", criteria_assessed)
        
        # Display reliability explanation
        reliability_explanation = """
        Assessment reliability is determined by the percentage of criteria that were directly assessed based on clear evidence:
        - **High**: 80%+ direct assessments
        - **Medium**: 50-80% direct assessments
        - **Low**: <50% direct assessments
        
        Higher reliability indicates more of the assessment is backed by direct evidence rather than inference.
        """
        
        with st.expander("Understanding Assessment Reliability"):
            st.markdown(reliability_explanation)