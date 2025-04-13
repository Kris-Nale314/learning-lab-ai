"""
Framework Assessment Workbench - Main Application

This is the main entry point for the Framework Assessment Workbench application.
It sets up the environment and initializes the Streamlit application.
"""

import os
import sys
import logging
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Ensure utils is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import path utilities
from utils import path_utils

# Configure logging
def setup_logging():
    """Configure application logging."""
    log_dir = path_utils.get_path("logs")
    
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"app_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Set specific loggers to different levels if needed
    logging.getLogger("learning-lab-ai").setLevel(logging.DEBUG)
    
    logger = logging.getLogger("learning-lab-ai.app")
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger

# Load environment variables
def load_environment():
    """Load environment variables from .env file."""
    # Look for .env file in project root
    env_path = path_utils.get_project_root() / ".env"
    
    # Load environment variables from .env file
    load_dotenv(dotenv_path=env_path)
    
    # Check if OPENAI_API_KEY is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not found in environment variables.")
        return False
    
    # Store API key in session state without displaying it
    st.session_state.api_key = api_key
    
    # Get optional environment variables
    model = os.getenv("MODEL", "gpt-3.5-turbo")
    token_budget = int(os.getenv("TOKEN_BUDGET", "50000"))
    
    # Store in session state
    st.session_state.model = model
    st.session_state.token_budget = token_budget
    
    logger.info(f"Environment loaded. Using model: {model}")
    return True

# Initialize the application
def init_app():
    """Initialize the application environment."""
    # Set up page config
    st.set_page_config(
        page_title="Framework Assessment Workbench",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state if needed
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.document = None
        st.session_state.framework = None
        st.session_state.strategy = None
        st.session_state.assessment_results = None
    
    # Initialize sidebar
    with st.sidebar:
        st.title("🧠 Learning Lab AI")
        
        # Only show model selector if environment variables loaded successfully
        if hasattr(st.session_state, "model"):
            # Model selection (with environment default)
            model_options = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
            default_index = 0
            if st.session_state.model in model_options:
                default_index = model_options.index(st.session_state.model)
            
            selected_model = st.selectbox(
                "Model", 
                model_options, 
                index=default_index, 
                key="model_selection"
            )
            
            # Update session state if user changed the model
            if selected_model != st.session_state.model:
                st.session_state.model = selected_model
                logger.info(f"Model changed to: {selected_model}")
        
        # Add configuration options
        st.sidebar.markdown("## Configuration")
        
        # Token budget slider (with environment default)
        if hasattr(st.session_state, "token_budget"):
            default_thousands = st.session_state.token_budget // 1000
            token_budget = st.slider(
                "Token Budget (thousands)",
                min_value=10,
                max_value=200,
                value=default_thousands,
                step=10,
                help="Maximum tokens to use for assessment"
            )
            
            # Update session state if user changed the budget
            if token_budget * 1000 != st.session_state.token_budget:
                st.session_state.token_budget = token_budget * 1000
                logger.info(f"Token budget changed to: {st.session_state.token_budget}")
        
        # Add version info
        st.sidebar.markdown("---")
        st.sidebar.caption("Framework Assessment Workbench")
        st.sidebar.caption("Version 0.1.0")

# Main function
def main():
    """Main application entry point."""
    # Setup logging first
    global logger
    logger = setup_logging()
    
    # Ensure all directories exist
    path_utils.ensure_dirs()
    
    # Load environment variables
    env_loaded = load_environment()
    
    # Initialize app
    init_app()
    
    # Display homepage
    st.title("🧠 Learning Lab AI: Framework Assessment Workbench")
    st.markdown(
        """
        > "AI is a tool for decision-making. It's also a product of decisions."
        
        ## 🔍 What is this?
        
        The Framework Assessment Workbench is an experimental laboratory for exploring how AI 
        can transform unstructured documents into structured insights. It demonstrates advanced 
        document intelligence techniques focused on **framework-guided assessment** - evaluating 
        content against structured criteria you define.
        
        ## 💼 How to Use
        
        1. Navigate to the **Framework Builder** page to create or upload an assessment framework
        2. Go to the **Document Assessment** page to upload and assess documents
        3. Explore results in the **Results Explorer**
        4. Experiment with different strategies in the **Experiment Lab**
        
        ## 🚀 Getting Started
        
        Use the sidebar navigation to access the different modules of the workbench.
        """
    )
    
    # Check for API key
    if not env_loaded:
        st.warning(
            "OPENAI_API_KEY not found in environment variables. "
            "Please add it to your .env file to use the application."
        )
        
        # Show .env example
        with st.expander("How to set up your .env file"):
            st.code(
                """
                # Create a file named .env in the project root directory with these contents:
                OPENAI_API_KEY=your_openai_api_key_here
                
                # You can also add other configuration options:
                # MODEL=gpt-4
                # TOKEN_BUDGET=50000
                """
            )
    
    # Check if we have sample frameworks
    framework_files = path_utils.list_files("frameworks", ".json")
    if not framework_files:
        # Create a sample framework
        try:
            create_sample_framework()
            st.info("Created a sample assessment framework to help you get started.")
        except Exception as e:
            logger.error(f"Failed to create sample framework: {str(e)}")

def create_sample_framework():
    """Create a sample framework for demonstration."""
    import json
    
    # Check if sample already exists
    sample_path = path_utils.get_file_path("frameworks", "sample_framework.json")
    if sample_path.exists():
        return
    
    # Create a simple sample framework
    sample_framework = {
        "id": "sample_framework",
        "name": "Sample Assessment Framework",
        "description": "A sample framework for demonstration purposes",
        "dimensions": [
            {
                "id": "dimension_1",
                "name": "Content Quality",
                "description": "Assessment of overall content quality",
                "criteria": [
                    {
                        "id": "criterion_1_1",
                        "name": "Clarity",
                        "question": "How clear and understandable is the content?",
                        "scoring_method": "scale_1_5",
                        "scoring_definitions": {
                            "1": "Very unclear, difficult to understand",
                            "2": "Somewhat unclear, requires effort to understand",
                            "3": "Moderately clear, some parts could be improved",
                            "4": "Mostly clear and understandable",
                            "5": "Extremely clear and easy to understand"
                        }
                    },
                    {
                        "id": "criterion_1_2",
                        "name": "Completeness",
                        "question": "How complete and comprehensive is the content?",
                        "scoring_method": "scale_1_5",
                        "scoring_definitions": {
                            "1": "Very incomplete, missing critical information",
                            "3": "Moderately complete, covers main points",
                            "5": "Highly complete, covers all aspects in detail"
                        }
                    }
                ]
            },
            {
                "id": "dimension_2",
                "name": "Structure",
                "description": "Assessment of document organization and structure",
                "criteria": [
                    {
                        "id": "criterion_2_1",
                        "name": "Organization",
                        "question": "How well is the content organized?",
                        "scoring_method": "scale_1_5",
                        "scoring_definitions": {
                            "1": "Poorly organized, difficult to follow",
                            "3": "Adequately organized, generally logical flow",
                            "5": "Extremely well organized, perfect logical flow"
                        }
                    },
                    {
                        "id": "criterion_2_2",
                        "name": "Formatting",
                        "question": "Is the document properly formatted?",
                        "scoring_method": "evidence_based",
                        "evidence_requirements": {
                            "description": "Evidence of proper formatting, headings, lists, etc."
                        }
                    }
                ]
            }
        ],
        "scoring_methods": {
            "scale_1_5": {"min": 1, "max": 5, "step": 1, "display": "numeric"},
            "evidence_based": {"type": "evidence_collection", "display": "list"}
        }
    }
    
    # Save the sample framework
    path_utils.save_framework(sample_framework)
    logger.info("Created sample framework")

if __name__ == "__main__":
    logger = None  # Will be initialized in main()
    main()