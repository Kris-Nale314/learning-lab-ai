"""
01_Framework_Assessment - Streamlined assessment page for Framework Assessment Workbench

This page provides a clean, consistent interface for assessing documents against frameworks,
with proper error handling and result display.
"""

import os
import sys
import asyncio
import json
import streamlit as st
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Ensure core modules are in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core components
from core.models.document import Document
from core.execution import StrategyExecutor
from core.models.customllm import CustomLLM

# Import utilities
from utils import path_utils
from utils import ui_components
from utils import ui_styles
from utils import ui_progress
from utils import ui_results

# Configure the page
st.set_page_config(
    page_title="Framework Assessment",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom styles
ui_styles.apply_styles()

def main():
    """Main application function for framework assessment."""
    # Page header
    st.title("🧠 Framework Assessment")
    st.markdown(
        """
        Assess a document against a structured framework using our AI system. 
        The system will analyze your document, extract relevant evidence, and provide a structured assessment 
        with clear distinction between direct and inferred findings.
        """
    )
    
    # Check for API key
    if not hasattr(st.session_state, "api_key") or not st.session_state.api_key:
        st.warning(
            "OpenAI API key not found. Please add it to your .env file "
            "or configure it in the app settings."
        )
        return
    
    # Initialize tabs for workflow
    tabs = st.tabs(["Assess New Document", "View Previous Assessments"])
    
    with tabs[0]:
        # Framework selection
        framework = display_framework_selection()
        
        # Document upload
        document = display_document_upload()
        
        # Assessment options
        options = display_assessment_options()
        
        # Add assessment button and handle assessment process
        start_col, _ = st.columns([1, 3])
        with start_col:
            start_assessment = st.button(
                "Start Assessment", 
                key="start_assessment_btn", 
                type="primary", 
                disabled=not (framework and document),
                help="Start the assessment process",
                use_container_width=True
            )
        
        if start_assessment:
            if not framework:
                st.error("Please select a framework before starting assessment.")
                return
                
            if not document:
                st.error("Please upload or paste a document before starting assessment.")
                return
            
            # Create a container for progress tracking
            progress_container = st.container()
            with progress_container:
                st.markdown("### Assessment Progress")
                
                # Create a progress tracker
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Run assessment process
                try:
                    # Define a helper function to run the async code
                    def run_async_assessment():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            return loop.run_until_complete(
                                perform_assessment(
                                    document, 
                                    framework, 
                                    options, 
                                    progress_callback=lambda p, msg: update_progress(progress_bar, status_text, p, msg)
                                )
                            )
                        finally:
                            loop.close()
                    
                    # Run the async function
                    assessment_result = run_async_assessment()
                    
                    # Store result in session state for later access
                    st.session_state.assessment_result = assessment_result
                    
                    # Display results
                    with st.container():
                        display_assessment_results(assessment_result)
                    
                except Exception as e:
                    st.error(f"Assessment failed: {str(e)}")
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
        
        # Display previously computed results if available
        elif hasattr(st.session_state, "assessment_result"):
            display_assessment_results(st.session_state.assessment_result)
    
    with tabs[1]:
        # Display previous assessments
        display_previous_assessments()

def update_progress(progress_bar, status_text, progress, message):
    """Update progress indicators."""
    progress_bar.progress(progress)
    status_text.markdown(f"**Status:** {message}")

async def perform_assessment(document, framework, options, progress_callback=None):
    """
    Perform document assessment with progress updates.
    
    Args:
        document: Document to assess
        framework: Assessment framework
        options: Assessment options
        progress_callback: Optional callback for progress updates
        
    Returns:
        Assessment result
    """
    # Initialize LLM
    llm = CustomLLM(
        api_key=st.session_state.api_key,
        model=st.session_state.model
    )
    
    # Initialize strategy executor
    executor = StrategyExecutor(
        llm=llm,
        document=document,
        framework=framework,
        options=options
    )
    
    # Set up progress tracking if callback provided
    if progress_callback:
        # Track progress updates from executor
        def track_progress():
            last_stage = None
            last_progress = 0
            
            while True:
                # Get current stage and progress
                current_stage = executor.context.current_stage
                current_progress = executor.context.progress
                
                # Get stage message if available
                stage_message = "Processing..."
                if current_stage and current_stage in executor.context.stages:
                    stage_message = executor.context.stages[current_stage].get("message", "Processing...")
                
                # Only update if changed
                if current_stage != last_stage or abs(current_progress - last_progress) > 0.01:
                    progress_callback(current_progress, stage_message)
                    last_stage = current_stage
                    last_progress = current_progress
                
                # Exit if complete
                if current_progress >= 0.99:
                    progress_callback(1.0, "Assessment complete")
                    break
                    
                time.sleep(0.5)
        
        # Start progress tracking in a separate thread
        import threading
        progress_thread = threading.Thread(target=track_progress)
        progress_thread.daemon = True
        progress_thread.start()
    
    try:
        # Get strategy preview first
        strategy_preview = await executor.get_strategy_preview()
        
        # Execute assessment
        result = await executor.execute()
        
        # Make sure strategy is included
        if "strategy" not in result:
            result["strategy"] = strategy_preview
            
        # Save result to file
        output_path = path_utils.save_assessment_result(result)
        
        # Add file path to result
        result["output_path"] = str(output_path)
        
        return result
    except Exception as e:
        st.error(f"Error during assessment execution: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "scorecard": {},
            "reports": {"formats": {}},
            "warnings": [],
            "errors": [{"message": str(e)}]
        }

def display_assessment_results(assessment_result):
    """
    Display assessment results with clear visual organization.
    
    Args:
        assessment_result: Assessment result data
    """
    # Check if result has error
    if "error" in assessment_result and assessment_result["error"]:
        st.error(f"Assessment failed: {assessment_result['error']}")
        return
        
    # Get scorecard and metadata
    scorecard = assessment_result.get("scorecard", {})
    metadata = assessment_result.get("metadata", {})
    
    # Display overall assessment summary
    st.markdown("## Assessment Results")
    
    # Create metrics for key results
    overall_rating = scorecard.get("overall_rating")
    framework_name = metadata.get("framework_name", "Framework")
    document_name = metadata.get("document_name", "Document")
    
    # Format overall rating for display
    rating_display = "N/A"
    if overall_rating is not None:
        try:
            rating_display = f"{float(overall_rating):.1f}"
        except (ValueError, TypeError):
            rating_display = str(overall_rating)
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Overall Rating", rating_display)
    with col2:
        st.metric("Framework", framework_name)
    with col3:
        st.metric("Document", document_name)
    
    # Display executive summary if available
    executive_summary = scorecard.get("executive_summary", "")
    if executive_summary:
        st.markdown("### Executive Summary")
        st.markdown(executive_summary)
    
    # Display key strengths and improvements
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Key Strengths")
        for strength in scorecard.get("key_strengths", []):
            st.markdown(f"- {strength}")
    
    with col2:
        st.markdown("### Key Improvements")
        for improvement in scorecard.get("key_improvements", []):
            st.markdown(f"- {improvement}")
    
    # Display dimension results
    st.markdown("### Dimension Results")
    
    # Create tabs for each dimension
    dimensions = scorecard.get("dimensions", [])
    if dimensions:
        dimension_names = [dim.get("name", f"Dimension {i+1}") for i, dim in enumerate(dimensions)]
        dimension_tabs = st.tabs(dimension_names)
        
        for i, dimension in enumerate(dimensions):
            with dimension_tabs[i]:
                display_dimension_results(dimension)
    else:
        st.info("No dimension results available.")
    
    # Add download buttons for assessment results
    st.markdown("### Download Assessment")
    col1, col2 = st.columns(2)
    
    with col1:
        # Download full JSON
        st.download_button(
            "Download Full Assessment (JSON)",
            data=json.dumps(assessment_result, indent=2),
            file_name="assessment_result.json",
            mime="application/json"
        )
    
    with col2:
        # Download scorecard only
        st.download_button(
            "Download Scorecard (JSON)",
            data=json.dumps(scorecard, indent=2),
            file_name="assessment_scorecard.json",
            mime="application/json"
        )

def display_dimension_results(dimension):
    """Display results for a single dimension."""
    # Get dimension data
    dimension_name = dimension.get("name", "Unknown Dimension")
    dimension_rating = dimension.get("average_rating")
    dimension_summary = dimension.get("summary", "")
    
    # Format dimension rating
    rating_display = "N/A"
    if dimension_rating is not None:
        try:
            rating_display = f"{float(dimension_rating):.1f}"
        except (ValueError, TypeError):
            rating_display = str(dimension_rating)
    
    # Display dimension summary
    st.markdown(f"**Average Rating:** {rating_display}")
    
    if dimension_summary:
        st.markdown(f"**Summary:** {dimension_summary}")
    
    # Display strengths and weaknesses
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Strengths")
        for strength in dimension.get("strengths", []):
            st.markdown(f"- {strength}")
    
    with col2:
        st.markdown("#### Weaknesses")
        for weakness in dimension.get("weaknesses", []):
            st.markdown(f"- {weakness}")
    
    # Display criteria
    st.markdown("#### Criteria Assessments")
    
    criteria = dimension.get("criteria", [])
    if not criteria:
        st.info("No criteria assessments available for this dimension.")
        return
    
    # Create a dataframe for criteria
    criteria_data = []
    
    for criterion in criteria:
        # Get criterion data
        criterion_name = criterion.get("name", "Unknown")
        criterion_rating = criterion.get("rating")
        rationale = criterion.get("rationale", "")
        assessment_type = criterion.get("assessment_type", "Unknown")
        
        # Format rating safely
        rating_display = "N/A"
        if criterion_rating is not None:
            try:
                rating_display = f"{float(criterion_rating):.1f}"
            except (ValueError, TypeError):
                rating_display = str(criterion_rating)
        
        # Add to data
        criteria_data.append({
            "Criterion": criterion_name,
            "Rating": rating_display,
            "Assessment Type": assessment_type.replace("_", " ").title(),
            "Rationale": rationale
        })
    
    # Display criteria as dataframe
    if criteria_data:
        df = pd.DataFrame(criteria_data)
        st.dataframe(df, use_container_width=True)

def display_framework_selection():
    """
    Display framework selection options and return the selected framework.
    
    Returns:
        Selected framework or None if no framework selected
    """
    with ui_components.card_container("Framework Selection"):
        # List available frameworks
        framework_files = path_utils.list_files("frameworks", ".json")
        framework_names = []
        
        for file_path in framework_files:
            try:
                with open(file_path, "r") as f:
                    framework = json.load(f)
                    name = framework.get("name", file_path.stem)
                    framework_names.append((name, file_path.name))
            except Exception as e:
                st.warning(f"Failed to load framework {file_path.name}: {str(e)}")
        
        # Sort by name
        framework_names.sort(key=lambda x: x[0])
        
        # Add framework options
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Create list of names for selectbox
            framework_options = [name for name, _ in framework_names]
            if not framework_options:
                st.info("No frameworks available. Please create a framework first.")
                ui_components.end_card_container()
                return None
                
            selected_index = 0
            
            # Find previously selected framework if exists
            if hasattr(st.session_state, "selected_framework_name"):
                if st.session_state.selected_framework_name in framework_options:
                    selected_index = framework_options.index(st.session_state.selected_framework_name)
            
            selected_framework_name = st.selectbox(
                "Select Assessment Framework",
                options=framework_options,
                index=selected_index,
                key="framework_selector"
            )
            
            # Store selection in session state
            st.session_state.selected_framework_name = selected_framework_name
            
            # Find the file for the selected framework
            selected_file = None
            for name, file_name in framework_names:
                if name == selected_framework_name:
                    selected_file = file_name
                    break
            
            if selected_file:
                # Load the framework
                try:
                    framework = path_utils.load_json("frameworks", selected_file)
                    st.session_state.framework = framework
                except Exception as e:
                    st.error(f"Failed to load framework: {str(e)}")
                    ui_components.end_card_container()
                    return None
            else:
                st.error("Failed to find selected framework file")
                ui_components.end_card_container()
                return None
        
        with col2:
            st.write("")
            st.write("")
            if st.button("Create New Framework", key="create_framework_btn"):
                st.session_state.current_page = "02_Framework_Builder"
                st.rerun()
        
        # Display framework info
        if hasattr(st.session_state, "framework"):
            framework = st.session_state.framework
            
            # Count dimensions and criteria
            dimension_count = len(framework.get("dimensions", []))
            criteria_count = sum(len(dimension.get("criteria", [])) for dimension in framework.get("dimensions", []))
            
            # Create metrics
            metrics = [
                {"label": "Dimensions", "value": dimension_count},
                {"label": "Criteria", "value": criteria_count},
                {"label": "Framework ID", "value": framework.get("id", "unknown")}
            ]
            
            ui_components.metric_row(metrics)
            
            # Display framework description if available
            description = framework.get("description")
            if description:
                st.markdown(f"**Description:** {description}")
            
            # Display framework structure preview
            if st.checkbox("Explore Framework Structure", key="explore_framework"):
                display_framework_structure(framework)
            
    ui_components.end_card_container()
    return framework

def display_framework_structure(framework):
    """
    Display interactive framework structure preview.
    
    Args:
        framework: Framework data
    """
    st.markdown("### Framework Structure")
    
    # Create tabs for structure views
    structure_tabs = st.tabs(["Dimension View", "Criterion Overview"])
    
    with structure_tabs[0]:
        # Display dimensions and criteria in a tree structure
        for i, dimension in enumerate(framework.get("dimensions", [])):
            dim_name = dimension.get("name", f"Dimension {i+1}")
            dim_id = dimension.get("id", "")
            
            with st.expander(dim_name, expanded=False):
                # Display dimension description if available
                description = dimension.get("description", "")
                if description:
                    st.markdown(f"*{description}*")
                
                # Display criteria
                criteria = dimension.get("criteria", [])
                
                if criteria:
                    # Create dataframe for criteria
                    criteria_data = []
                    
                    for criterion in criteria:
                        crit_name = criterion.get("name", "")
                        crit_id = criterion.get("id", "")
                        crit_question = criterion.get("question", "")
                        scoring_method = criterion.get("scoring_method", "")
                        
                        criteria_data.append({
                            "Criterion": crit_name,
                            "ID": crit_id,
                            "Question": crit_question,
                            "Scoring Method": scoring_method
                        })
                    
                    # Display as table
                    st.dataframe(pd.DataFrame(criteria_data), use_container_width=True)
                else:
                    st.info(f"No criteria defined for {dim_name}")
    
    with structure_tabs[1]:
        # Create a table view of all criteria
        all_criteria = []
        
        for dimension in framework.get("dimensions", []):
            dim_name = dimension.get("name", "")
            dim_id = dimension.get("id", "")
            
            for criterion in dimension.get("criteria", []):
                crit_name = criterion.get("name", "")
                crit_id = criterion.get("id", "")
                crit_question = criterion.get("question", "")
                
                all_criteria.append({
                    "Dimension": dim_name,
                    "Dimension ID": dim_id,
                    "Criterion": crit_name,
                    "Criterion ID": crit_id,
                    "Question": crit_question
                })
        
        if all_criteria:
            # Display as searchable table
            st.dataframe(pd.DataFrame(all_criteria), use_container_width=True)
        else:
            st.info("No criteria found in this framework.")

def display_document_upload():
    """
    Display document upload options and return the uploaded document.
    
    Returns:
        Uploaded document or None if no document uploaded
    """
    uploaded_document = None
    
    with ui_components.card_container("Document Upload"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # File uploader
            uploaded_file = st.file_uploader(
                "Upload a document to assess", 
                type=["txt", "md", "rst", "csv", "json"],
                key="document_uploader"
            )
            
            # Check if a file was uploaded
            if uploaded_file is not None:
                # Process the file
                try:
                    uploaded_document = Document.from_uploaded_file(uploaded_file)
                    st.session_state.document = uploaded_document
                    st.success(f"Document uploaded successfully: {uploaded_file.name}")
                except Exception as e:
                    st.error(f"Failed to process document: {str(e)}")
            
            # Alternative: text input
            if not uploaded_file:
                st.markdown("#### Or paste document text")
                document_text = st.text_area(
                    "Paste document text here",
                    height=150,
                    key="document_text",
                    help="Paste the document text to assess"
                )
                
                if document_text:
                    try:
                        filename = "pasted_document.txt"
                        if "paste_filename" in st.session_state:
                            filename = st.session_state.paste_filename
                            
                        uploaded_document = Document.from_text(document_text, filename=filename)
                        st.session_state.document = uploaded_document
                    except Exception as e:
                        st.error(f"Failed to process document text: {str(e)}")
        
        with col2:
            # Document name field for pasted text
            paste_filename = st.text_input(
                "Document Name (for pasted text)",
                value="document.txt",
                key="paste_filename",
                help="Enter a name for the pasted document"
            )
        
        # Display document info if available
        if hasattr(st.session_state, "document") and st.session_state.document is not None:
            document = st.session_state.document
            summary = document.get_summary()
            
            # Create metrics
            metrics = [
                {"label": "Words", "value": summary.get("word_count", 0)},
                {"label": "Characters", "value": summary.get("character_count", 0)},
                {"label": "Est. Tokens", "value": summary.get("estimated_tokens", 0)}
            ]
            
            ui_components.metric_row(metrics)
            
            # Display document preview with tabs
            preview_tabs = st.tabs(["Text Preview", "Document Analysis"])
            
            with preview_tabs[0]:
                # Text preview
                preview_length = min(len(document.text), 2000)
                preview_text = document.text[:preview_length]
                if len(document.text) > preview_length:
                    preview_text += "..."
                    
                st.code(preview_text, language=None)
            
            with preview_tabs[1]:
                # Document analysis
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Document Type:** " + summary.get("document_type", "Unknown"))
                    st.markdown("**Content Structure:** " + summary.get("content_structure", "General text"))
                
                with col2:
                    st.markdown("**Entity Type:** " + summary.get("primary_entity", {}).get("type", "Unknown"))
                    st.markdown("**Entity Name:** " + summary.get("primary_entity", {}).get("name", "Unknown"))
                
                # Show keywords if available
                keywords = summary.get("keywords", [])
                if keywords:
                    st.markdown("**Keywords:** " + ", ".join(keywords))
    
    ui_components.end_card_container()
    return uploaded_document

def display_assessment_options():
    """
    Display assessment options with streamlined controls.
    
    Returns:
        Dictionary of assessment options
    """
    options = {}
    
    with ui_components.card_container("Assessment Options"):
        # Create tabs for option categories
        option_tabs = st.tabs(["Model & Output", "Evidence Options", "Advanced Options"])
        
        with option_tabs[0]:
            col1, col2 = st.columns(2)
            
            with col1:
                # Model options
                model_options = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
                default_index = 0
                if hasattr(st.session_state, "model") and st.session_state.model in model_options:
                    default_index = model_options.index(st.session_state.model)
                
                selected_model = st.selectbox(
                    "Language Model",
                    options=model_options,
                    index=default_index,
                    key="model_selector",
                    help="Select the language model to use for assessment"
                )
                
                # Store selection in session state
                st.session_state.model = selected_model
                options["model"] = selected_model
                
                # Report type
                report_type = st.selectbox(
                    "Report Type",
                    options=["scorecard", "comprehensive", "detailed", "executive"],
                    index=0,
                    key="report_type",
                    help="Select the type of report to generate"
                )
                options["report_type"] = report_type
            
            with col2:
                # Assessment type options
                include_evidence = st.checkbox(
                    "Include Evidence", 
                    value=True, 
                    key="include_evidence",
                    help="Include evidence references in the assessment"
                )
                options["include_evidence"] = include_evidence
                
                include_confidence = st.checkbox(
                    "Include Confidence Scores", 
                    value=True, 
                    key="include_confidence",
                    help="Include confidence scores in the assessment"
                )
                options["include_confidence"] = include_confidence
                
                # Inference option
                infer_missing = st.checkbox(
                    "Infer Missing Assessments", 
                    value=True, 
                    key="infer_missing",
                    help="Attempt to assess criteria even without direct evidence"
                )
                options["infer_missing"] = infer_missing
                
                # Assessment reliability labeling
                show_assessment_types = st.checkbox(
                    "Show Assessment Types", 
                    value=True, 
                    key="show_assessment_types",
                    help="Clearly label direct vs. inferred assessments"
                )
                options["include_assessment_types"] = show_assessment_types
        
        with option_tabs[1]:
            # Evidence extraction options
            col1, col2 = st.columns(2)
            
            with col1:
                # Extraction strategy options
                extraction_strategy = st.selectbox(
                    "Extraction Strategy",
                    options=["semantic", "balanced", "detailed", "efficient"],
                    index=0,
                    key="extraction_strategy",
                    help="Select the evidence extraction strategy"
                )
                options["extraction_strategy"] = extraction_strategy
                
                # Evidence thresholds
                confidence_threshold = st.slider(
                    "Evidence Confidence Threshold",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.3,
                    step=0.05,
                    key="confidence_threshold",
                    help="Minimum confidence level for evidence"
                )
                options["confidence_threshold"] = confidence_threshold
            
            with col2:
                # Evidence categorization
                st.markdown("**Evidence Categorization**")
                
                relevance_levels = st.multiselect(
                    "Relevance Levels",
                    options=["Direct", "Indirect", "Contextual", "Implied"],
                    default=["Direct", "Indirect", "Contextual"],
                    key="relevance_levels",
                    help="Types of evidence relevance to collect"
                )
                options["relevance_levels"] = relevance_levels
                
                sentiment_types = st.multiselect(
                    "Sentiment Types",
                    options=["Positive", "Negative", "Neutral"],
                    default=["Positive", "Negative", "Neutral"],
                    key="sentiment_types",
                    help="Types of evidence sentiment to collect"
                )
                options["sentiment_types"] = sentiment_types
        
        with option_tabs[2]:
            # Advanced options
            col1, col2 = st.columns(2)
            
            with col1:
                # Parallel processing options
                max_concurrent = st.slider(
                    "Max Concurrent Extractors",
                    min_value=1,
                    max_value=5,
                    value=3,
                    step=1,
                    help="Maximum number of extractors to run in parallel"
                )
                options["max_concurrent"] = max_concurrent
                
                # Combined evaluation option
                use_combined_evaluation = st.checkbox(
                    "Use Combined Evaluation", 
                    value=True, 
                    key="use_combined_evaluation",
                    help="Evaluate related criteria together for consistency"
                )
                options["use_combined_evaluation"] = use_combined_evaluation
            
            with col2:
                # Chunking options
                chunking_method = st.selectbox(
                    "Chunking Method",
                    options=["auto", "fixed_size", "paragraph", "semantic"],
                    index=0,
                    key="chunking_method",
                    help="Method for dividing the document into chunks"
                )
                options["chunking_method"] = chunking_method
                
                if chunking_method == "fixed_size":
                    chunk_size = st.slider(
                        "Chunk Size",
                        min_value=1000,
                        max_value=15000,
                        value=8000,
                        step=1000,
                        help="Size of each document chunk in characters"
                    )
                    options["chunk_size"] = chunk_size
                elif chunking_method == "semantic":
                    semantic_overlap = st.slider(
                        "Semantic Overlap",
                        min_value=0.0,
                        max_value=0.5,
                        value=0.1,
                        step=0.05,
                        help="Semantic overlap between chunks"
                    )
                    options["semantic_overlap"] = semantic_overlap
    
    ui_components.end_card_container()
    return options

def display_previous_assessments():
    """Display previous assessment results that the user can reload."""
    with ui_components.card_container("Previous Assessments"):
        # List assessment output files
        assessment_files = path_utils.list_files("outputs", ".json")
        
        if not assessment_files:
            st.info("No previous assessments found.")
            ui_components.end_card_container()
            return
        
        # Sort by modification time (newest first)
        assessment_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Create a table of assessments
        data = []
        for file_path in assessment_files[:10]:  # Show the 10 most recent
            try:
                # Get file info
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                file_size = file_path.stat().st_size / 1024  # Size in KB
                
                data.append({
                    "File": file_path.name,
                    "Date": mtime.strftime("%Y-%m-%d %H:%M"),
                    "Size": f"{file_size:.1f} KB",
                    "Path": file_path
                })
            except Exception as e:
                st.warning(f"Failed to load assessment {file_path.name}: {str(e)}")
        
        # Display as a table
        if data:
            # Create a dataframe for display
            df = pd.DataFrame(data)
            # Drop the Path column for display
            display_df = df.drop(columns=["Path"])
            
            # Show the table
            st.dataframe(display_df, use_container_width=True)
            
            # Add a load button
            cols = st.columns([3, 1])
            
            with cols[0]:
                selected_indices = st.selectbox(
                    "Select assessment to load",
                    options=range(len(data)),
                    format_func=lambda i: f"{data[i]['File']} - {data[i]['Date']}",
                    key="assessment_selector"
                )
            
            with cols[1]:
                if st.button("Load Assessment", key="load_assessment_btn"):
                    selected_path = data[selected_indices]["Path"]
                    try:
                        # Load the selected assessment
                        with open(selected_path, "r") as f:
                            assessment_result = json.load(f)
                        
                        # Store in session state
                        st.session_state.assessment_result = assessment_result
                        
                        st.success(f"Loaded assessment: {selected_path.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load assessment: {str(e)}")
    
    ui_components.end_card_container()

def initialize_session_state():
    """Initialize session state for the assessment page."""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.document = None
        st.session_state.framework = None
        st.session_state.assessment_result = None
    
    # Set default model if not already set
    if "model" not in st.session_state:
        st.session_state.model = "gpt-3.5-turbo"

if __name__ == "__main__":
    initialize_session_state()
    main()