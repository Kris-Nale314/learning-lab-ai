"""
Document Assessment - Framework Assessment Workbench

A simplified page that focuses on core functionality: loading a document,
selecting a framework, and running an assessment.
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
        selected_framework = st.selectbox(
            "Framework", 
            list(framework_options.keys()),
            key="framework_select"
        )
        
        # Assessment options
        st.subheader("Options")
        infer_missing = st.checkbox("Infer missing values", value=True)
        include_evidence = st.checkbox("Include evidence", value=True)
        
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
            "include_evidence": include_evidence
        }
    }
    
    # Run button
    if st.button("Run Assessment", key="run_btn"):
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
                    # First run planning
                    strategy = await executor.plan()
                    
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
        
        result = st.session_state.assessment_result
        
        # Show overall assessment
        overall = result.get("overall_assessment", {})
        overall_rating = overall.get("average_rating")
        
        if overall_rating is not None:
            st.metric("Overall Rating", f"{overall_rating:.1f}")
        
        # Show assessment text
        assessment_text = overall.get("assessment", "")
        if assessment_text:
            st.subheader("Executive Summary")
            st.write(assessment_text)
        
        # Option to view full results
        if st.button("View Full Report", key="view_report_btn"):
            st.session_state.view_full_report = True
            # Redirect to results page or expand full report

if __name__ == "__main__":
    main()