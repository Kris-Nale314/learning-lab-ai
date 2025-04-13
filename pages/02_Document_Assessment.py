"""
Document Assessment - Framework Assessment Workbench

An enhanced page that showcases parallel extractors and structured scorecard output.
Fixed to handle None values in ratings.
"""

import asyncio
import json
import logging
import streamlit as st
from typing import Dict, Any

# Import core components
from core.models.customllm import CustomLLM
from core.models.document import Document
from core.execution import StrategyExecutor

# Import utilities
from utils import path_utils

# Configure logging
logger = logging.getLogger("learning-lab-ai.pages.document_assessment")

def main():
    """Main function for the Document Assessment page."""
    st.title("📄 Document Assessment")
    
    # Sidebar: Load settings and framework
    with st.sidebar:
        st.header("Assessment Settings")
        
        # Framework selection
        frameworks = path_utils.list_frameworks()
        if not frameworks:
            st.warning("No frameworks found")
            return
            
        framework_options = {f["name"]: f for f in frameworks}
        
        # Default to earnings call framework if available
        default_framework = "Corporate Earnings Call Assessment Framework"
        default_index = 0
        if default_framework in framework_options:
            default_index = list(framework_options.keys()).index(default_framework)
        
        selected_framework = st.selectbox(
            "Framework", 
            list(framework_options.keys()),
            index=default_index,
            key="framework_select"
        )
        
        # Assessment options
        st.subheader("Options")
        infer_missing = st.checkbox("Infer missing values", value=True)
        include_evidence = st.checkbox("Include evidence", value=True)
        parallel_extraction = st.checkbox("Use parallel extraction", value=True)
        
        # Advanced options
        with st.expander("Advanced Options"):
            max_extractors = st.slider(
                "Max Parallel Extractors", 
                min_value=1, 
                max_value=10, 
                value=5,
                help="Maximum number of extractors to run in parallel"
            )
            
            report_type = st.selectbox(
                "Report Type",
                ["scorecard", "executive", "detailed", "comprehensive"],
                index=0,
                help="Type of report to generate"
            )
        
        # Model info
        st.subheader("Model Settings")
        model_info = st.session_state.get("model", "gpt-3.5-turbo")
        st.info(f"Using model: {model_info}")
    
    # Main area: Document upload and assessment
    st.header("1. Upload Document")
    
    # Document input options
    doc_tab1, doc_tab2 = st.tabs(["Upload File", "Paste Text"])
    
    with doc_tab1:
        uploaded_file = st.file_uploader("Upload a document", type=["txt", "pdf", "docx"])
        if uploaded_file:
            try:
                document = Document.from_uploaded_file(uploaded_file)
                st.session_state.document = document
                st.success(f"Loaded: {document.filename} ({document.estimated_tokens:,} tokens)")
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
    
    with doc_tab2:
        text_input = st.text_area("Paste document text", height=200, key="text_input")
        if text_input and st.button("Process Text", key="process_btn"):
            try:
                document = Document.from_text(text_input)
                st.session_state.document = document
                st.success(f"Document processed: {document.estimated_tokens:,} tokens")
            except Exception as e:
                st.error(f"Error processing text: {str(e)}")
    
    # Run assessment section
    st.header("2. Run Assessment")
    
    if not st.session_state.get("document"):
        st.warning("Please upload or paste a document first")
        return
        
    # Get selected framework
    if not selected_framework or selected_framework not in framework_options:
        st.warning("Please select a framework")
        return
        
    framework = framework_options[selected_framework]
    
    # Setup options
    options = {
        "user_options": {
            "infer_missing": infer_missing,
            "include_evidence": include_evidence,
            "parallel_extraction": parallel_extraction,
            "max_extractors": max_extractors,
            "report_type": report_type
        }
    }
    
    # Run button
    if st.button("Run Assessment", key="run_btn", type="primary"):
        st.session_state.assessment_started = True
        
        # Setup progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Function to run assessment
        async def run_assessment():
            try:
                # Get API key from session state
                api_key = st.session_state.get("api_key")
                if not api_key:
                    st.error("API key not found")
                    return None
                
                # Initialize LLM
                model = st.session_state.get("model", "gpt-3.5-turbo")
                llm = CustomLLM(api_key=api_key, model=model)
                
                # Initialize executor
                document = st.session_state.document
                executor = StrategyExecutor(llm, document, framework, options)
                
                # Setup progress tracking
                def update_progress():
                    import threading
                    import time
                    
                    def progress_updater():
                        while True:
                            if hasattr(executor, "context"):
                                progress = executor.context.progress
                                progress_bar.progress(progress)
                                
                                current_stage = executor.context.current_stage or "initializing"
                                stage_data = executor.context.stages.get(current_stage, {})
                                message = stage_data.get("message", f"Processing {current_stage}")
                                status_text.info(f"{current_stage.replace('_', ' ').title()}: {message}")
                                
                                if progress >= 1.0:
                                    break
                            time.sleep(0.5)
                    
                    thread = threading.Thread(target=progress_updater)
                    thread.daemon = True
                    thread.start()
                
                update_progress()
                
                # Execute assessment pipeline
                with st.spinner("Running assessment..."):
                    # First run planning - show strategy preview
                    strategy = await executor.plan()
                    
                    # Display strategy info
                    strategy_preview = await executor.get_strategy_preview()
                    st.session_state.strategy_preview = strategy_preview
                    
                    # Then execute full pipeline
                    result = await executor.execute(strategy)
                    
                    # Save results
                    output_path = path_utils.save_assessment_result(result)
                    
                    # Store in session state
                    st.session_state.assessment_result = result
                    st.session_state.result_path = str(output_path)
                    
                    # Show success message
                    st.success("Assessment completed!")
                    
                    return result
            
            except Exception as e:
                st.error(f"Error during assessment: {str(e)}")
                logger.error(f"Assessment error: {str(e)}", exc_info=True)
                return None
        
        # Run the assessment
        result = asyncio.run(run_assessment())
        
        if result:
            st.session_state.show_results = True
    
    # Display results if available
    if st.session_state.get("show_results") and st.session_state.get("assessment_result"):
        st.header("3. Assessment Results")
        
        # Display strategy info if available
        if st.session_state.get("strategy_preview"):
            strategy_preview = st.session_state.strategy_preview
            with st.expander("Strategy Information", expanded=False):
                st.write(f"**Strategy Type:** {strategy_preview.get('strategy_type', 'unknown')}")
                st.write(f"**Parallel Extractors:** {strategy_preview.get('total_extractors', 0)}")
                st.write(f"**Chunking Method:** {strategy_preview.get('chunking', {}).get('method', 'unknown')}")
                st.write(f"**Processing Sequence:** {', '.join(strategy_preview.get('processing_sequence', []))}")
        
        result = st.session_state.assessment_result
        
        # Show overall assessment
        overall = result.get("overall_assessment", {})
        overall_rating = overall.get("average_rating")
        
        # Handle None values
        if overall_rating is not None:
            st.metric("Overall Rating", f"{overall_rating:.1f}")
        else:
            st.metric("Overall Rating", "N/A")
        
        # Get the scorecard from reports if available
        reports = result.get("reports", {}).get("formats", {})
        scorecard = reports.get("scorecard")
        
        if not scorecard:
            # Attempt to construct a basic scorecard from the results
            scorecard = {
                "overall_rating": overall_rating,
                "dimensions": []
            }
            
            for dimension_id, dimension_data in result.get("dimension_summaries", {}).items():
                dimension_entry = {
                    "id": dimension_id,
                    "name": dimension_data.get("dimension_name", dimension_id),
                    "average_rating": dimension_data.get("average_rating"),
                    "criteria": []
                }
                
                # Get criteria for this dimension
                for criterion_id, criterion_data in result.get("assessments", {}).get(dimension_id, {}).get("criteria", {}).items():
                    criterion_entry = {
                        "id": criterion_id,
                        "rating": criterion_data.get("rating"),
                        "rationale": criterion_data.get("rationale", "")
                    }
                    dimension_entry["criteria"].append(criterion_entry)
                
                scorecard["dimensions"].append(dimension_entry)
        
        # Display structured scorecard
        st.subheader("Assessment Scorecard")
        
        # Overall section
        with st.container():
            # Safe handling of None value
            rating_display = f"{overall_rating:.1f}/5.0" if overall_rating is not None else "N/A"
            st.markdown(f"### Overall Assessment: {rating_display}")
            
            # Key strengths and improvements
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Key Strengths")
                strengths = overall.get("key_strengths", [])
                if strengths:
                    for strength in strengths:
                        st.markdown(f"- {strength}")
                else:
                    st.write("No key strengths identified")
                    
            with col2:
                st.markdown("#### Areas for Improvement")
                improvements = overall.get("key_improvements", [])
                if improvements:
                    for improvement in improvements:
                        st.markdown(f"- {improvement}")
                else:
                    st.write("No areas for improvement identified")
        
        # Display dimension ratings
        st.markdown("### Dimension Ratings")
        
        # Create dimension tabs
        if "dimensions" in scorecard and scorecard["dimensions"]:
            dimension_names = [dim.get("name", f"Dimension {i}") for i, dim in enumerate(scorecard["dimensions"])]
            dimension_tabs = st.tabs(dimension_names)
            
            # Fill each dimension tab with criteria
            for i, (tab, dimension) in enumerate(zip(dimension_tabs, scorecard["dimensions"])):
                with tab:
                    # Safe handling of None value for dimension rating
                    dim_rating = dimension.get("average_rating")
                    dim_rating_display = f"{dim_rating:.1f}" if dim_rating is not None else "N/A"
                    st.markdown(f"#### {dimension.get('name')} - Rating: {dim_rating_display}")
                    
                    # Display criteria in a table
                    if "criteria" in dimension and dimension["criteria"]:
                        criteria_data = []
                        
                        for criterion in dimension["criteria"]:
                            criterion_name = criterion.get("name", criterion.get("id", "Unknown"))
                            rating = criterion.get("rating")
                            # Handle None rating
                            rating_display = f"{rating:.1f}" if rating is not None else "N/A"
                            confidence = criterion.get("confidence", "N/A")
                            # Handle None confidence
                            confidence_display = f"{confidence:.2f}" if confidence is not None else "N/A"
                            
                            criteria_data.append({
                                "Criterion": criterion_name,
                                "Rating": rating_display,
                                "Confidence": confidence_display
                            })
                        
                        st.dataframe(criteria_data, use_container_width=True)
                        
                        # Display criterion details
                        for criterion in dimension["criteria"]:
                            criterion_name = criterion.get("name", criterion.get("id", "Unknown"))
                            rating = criterion.get("rating")
                            # Handle None rating
                            rating_display = f"{rating:.1f}" if rating is not None else "N/A"
                            rationale = criterion.get("rationale", "No rationale provided")
                            
                            with st.expander(f"{criterion_name} - Rating: {rating_display}"):
                                st.markdown("**Rationale:**")
                                st.write(rationale)
                                
                                # Show evidence if available
                                if "evidence" in criterion and criterion["evidence"]:
                                    st.markdown("**Evidence:**")
                                    for evidence in criterion["evidence"]:
                                        st.markdown(f"- {evidence.get('text', 'No text')}")
                    else:
                        st.write("No criteria assessed for this dimension")
        else:
            st.write("No dimension data available in the scorecard")
        
        # Option to view full report
        st.markdown("### Additional Reports")
        report_options = [key for key in reports.keys() if key != "scorecard"]
        
        if report_options:
            selected_report = st.selectbox("Select Report Type", report_options)
            
            if selected_report and selected_report in reports:
                report_data = reports[selected_report]
                
                # Display selected report
                if selected_report == "executive_summary":
                    st.markdown("## Executive Summary")
                    st.markdown(report_data.get("executive_summary", ""))
                    
                    # Display recommendations
                    st.markdown("### Recommendations")
                    recommendations = report_data.get("recommendations", [])
                    for rec in recommendations:
                        st.markdown(f"- {rec}")
                        
                elif selected_report == "detailed_assessment":
                    st.markdown("## Detailed Assessment")
                    st.markdown(report_data.get("introduction", ""))
                    
                    # Display each dimension
                    for dimension in report_data.get("dimensions", []):
                        st.markdown(f"### {dimension.get('name')}")
                        st.markdown(dimension.get("summary", ""))
                        
                elif selected_report == "visualization_data":
                    st.markdown("## Visualization Data")
                    
                    # Show radar chart data if possible
                    radar_data = report_data.get("radar_chart", [])
                    if radar_data:
                        st.markdown("### Dimension Ratings")
                        radar_df = {
                            "Dimension": [item.get("dimension") for item in radar_data],
                            "Rating": [item.get("rating") for item in radar_data]
                        }
                        st.dataframe(radar_df)
                        
                    # Show heatmap data
                    heatmap_data = report_data.get("heatmap", [])
                    if heatmap_data:
                        st.markdown("### Criterion Ratings Heatmap")
                        heatmap_df = {
                            "Dimension": [item.get("dimension") for item in heatmap_data],
                            "Criterion": [item.get("criterion") for item in heatmap_data], 
                            "Rating": [item.get("rating") for item in heatmap_data]
                        }
                        st.dataframe(heatmap_df)
        
        # Download results
        if st.button("Download Full Results"):
            result_json = json.dumps(result, indent=2)
            st.download_button(
                label="Download JSON",
                data=result_json,
                file_name="assessment_results.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()