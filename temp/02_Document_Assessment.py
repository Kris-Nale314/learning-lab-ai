"""
01_Assess_Framework - Main assessment page for Framework Assessment Workbench
OLD SCRIPT - GREAT SCORECARD UI
This is the primary page for assessing documents against frameworks using
the enhanced multi-agent architecture with improved UI integration.
"""

import os
import sys
import asyncio
import json
import streamlit as st
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

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

# Initialize UI
ui_components.initialize_ui()

async def run_assessment(document, framework, options):
    """
    Run the assessment process asynchronously.
    
    Args:
        document: Document to assess
        framework: Framework to assess against
        options: Assessment options
    
    Returns:
        Tuple of (UI-ready assessment results, strategy preview)
    """
    try:
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
        
        # Initialize progress tracker for the executor
        progress_tracker = ui_progress.create_executor_progress_tracker(executor)
        progress_tracker.start_tracking()
        
        # Get strategy preview
        strategy_preview = await executor.get_strategy_preview()
        
        # Execute assessment and get UI-ready results
        ui_ready_result = await executor.execute()
        
        # Stop progress tracking
        progress_tracker.stop()
        
        # Save result to file
        output_path = path_utils.save_assessment_result(ui_ready_result)
        st.success(f"Assessment results saved to {output_path.name}")
        
        return ui_ready_result, strategy_preview
    except Exception as e:
        st.error(f"Assessment failed: {str(e)}")
        # Create basic error result
        error_result = {
            "error": str(e),
            "status": "failed",
            "scorecard": {},
            "reports": {"formats": {}},
            "warnings": [],
            "errors": [{"message": str(e), "stage": "execution"}]
        }
        return error_result, None

def display_framework_selection():
    """
    Display framework selection options and return the selected framework.
    
    Returns:
        Selected framework or None if no framework selected
    """
    with st.expander("Framework Selection", expanded=True):
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
                    return None
            else:
                st.error("Failed to find selected framework file")
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
            
            return framework
    
    return None

def display_document_upload():
    """
    Display document upload options and return the uploaded document.
    
    Returns:
        Uploaded document or None if no document uploaded
    """
    uploaded_document = None
    
    with st.expander("Document Upload", expanded=True):
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
            
            # Display document preview (without an expander)
            st.markdown("##### Document Preview")
            preview_length = min(len(document.text), 2000)
            st.markdown(f"```\n{document.text[:preview_length]}\n" + 
                       ("..." if len(document.text) > preview_length else "") + 
                       "\n```")
            
            return document
    
    return uploaded_document

def display_assessment_options():
    """
    Display assessment options and return the selected options.
    
    Returns:
        Dictionary of assessment options
    """
    options = {}
    
    with st.expander("Assessment Options", expanded=False):
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
            
            # Report type
            report_type = st.selectbox(
                "Report Type",
                options=["scorecard", "comprehensive", "detailed", "executive"],
                index=0,
                key="report_type",
                help="Select the type of report to generate"
            )
            options["report_type"] = report_type
            
            # Add to document options
            include_evidence = st.checkbox(
                "Include Evidence", 
                value=True, 
                key="include_evidence",
                help="Include evidence references in the assessment"
            )
            options["include_evidence"] = include_evidence
        
        with col2:
            # Extraction strategy options
            extraction_strategy = st.selectbox(
                "Extraction Strategy",
                options=["balanced", "detailed", "efficient"],
                index=0,
                key="extraction_strategy",
                help="Select the evidence extraction strategy"
            )
            options["extraction_strategy"] = extraction_strategy
            
            # Confidence threshold
            confidence_threshold = st.slider(
                "Confidence Threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.05,
                key="confidence_threshold",
                help="Minimum confidence level for evidence"
            )
            options["confidence_threshold"] = confidence_threshold
            
            # Add to document options
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
        
        # Advanced options section - not inside an expander
        st.markdown("##### Advanced Options")
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
        
        return options

def display_previous_assessments():
    """Display previous assessment results that the user can reload."""
    st.subheader("Previous Assessments")
    
    # List assessment output files
    assessment_files = path_utils.list_files("outputs", ".json")
    
    if not assessment_files:
        st.info("No previous assessments found.")
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
    if data:
        st.write("Recent assessments:")
        
        # Create a dataframe for display
        import pandas as pd
        df = pd.DataFrame(data)
        # Drop the Path column for display
        display_df = df.drop(columns=["Path"])
        
        # Show the table
        st.dataframe(display_df, use_container_width=True)
        
        # Add a load button
        selected_indices = st.multiselect(
            "Select assessment to load",
            options=range(len(data)),
            format_func=lambda i: f"{data[i]['Framework']} - {data[i]['Date']}"
        )
        
        if selected_indices and st.button("Load Selected Assessment"):
            selected_path = data[selected_indices[0]]["Path"]
            try:
                # Load the selected assessment
                with open(selected_path, "r") as f:
                    assessment_result = json.load(f)
                
                # Store in session state
                st.session_state.assessment_result = assessment_result
                
                # Extract strategy if available
                strategy_preview = assessment_result.get("strategy")
                if strategy_preview:
                    st.session_state.strategy_preview = strategy_preview
                
                st.success(f"Loaded assessment: {selected_path.name}")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to load assessment: {str(e)}")

def main():
    """Main application function for framework assessment."""
    # Page header
    st.title("🧠 Framework Assessment")
    st.markdown(
        """
        Assess a document against a structured framework using our advanced AI system.
        Upload a document, select a framework, and get a comprehensive assessment.
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
        # Display framework selection and document upload
        framework = display_framework_selection()
        document = display_document_upload()
        
        # Display assessment options
        options = display_assessment_options()
        
        # Add assessment button and handle assessment process
        start_assessment = st.button(
            "Start Assessment", 
            key="start_assessment_btn", 
            type="primary", 
            disabled=not (framework and document),
            help="Start the assessment process"
        )
        
        if start_assessment:
            if not framework:
                st.error("Please select a framework before starting assessment.")
                return
                
            if not document:
                st.error("Please upload or paste a document before starting assessment.")
                return
            
            # Create a spinner while assessment is running
            with st.spinner("Running assessment. This may take a few minutes..."):
                try:
                    # Define a helper function to run the async code
                    def run_async_assessment():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            return loop.run_until_complete(run_assessment(document, framework, options))
                        finally:
                            loop.close()
                    
                    # Run the async function
                    ui_ready_result, strategy_preview = run_async_assessment()
                    
                    # Store results in session state
                    st.session_state.assessment_result = ui_ready_result
                    st.session_state.strategy_preview = strategy_preview
                    
                    # Display results
                    ui_results.display_assessment_results(ui_ready_result, strategy_preview)
                    
                except Exception as e:
                    st.error(f"Assessment failed: {str(e)}")
        
        # Display previously computed results if available
        elif hasattr(st.session_state, "assessment_result"):
            ui_results.display_assessment_results(
                st.session_state.assessment_result,
                st.session_state.strategy_preview if hasattr(st.session_state, "strategy_preview") else None
            )
    
    with tabs[1]:
        # Display previous assessments
        display_previous_assessments()

if __name__ == "__main__":
    main()