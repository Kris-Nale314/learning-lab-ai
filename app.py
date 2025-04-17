"""
Framework Assessment Workbench - Main Application

A professional tool for transforming unstructured documents into structured insights
through AI-powered framework assessment.
"""

import os
import sys
import logging
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Set page config first (must be the first Streamlit command)
st.set_page_config(
    page_title="Document Insight Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure utils is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import path utilities
from utils import path_utils
from utils import ui_components
from utils import ui_styles
from utils import ui_progress

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
    logging.getLogger("document-insight").setLevel(logging.DEBUG)
    
    logger = logging.getLogger("document-insight.app")
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
    model = os.getenv("MODEL", "gpt-3.5-turbo")  # Default to 3.5 as requested
    token_budget = int(os.getenv("TOKEN_BUDGET", "50000"))
    
    # Store in session state
    st.session_state.model = model
    st.session_state.token_budget = token_budget
    
    logger.info(f"Environment loaded. Using model: {model}")
    return True

# Initialize the application
def init_app():
    """Initialize the application environment."""
    # Apply custom UI styles
    ui_styles.apply_styles()
    
    # Initialize session state if needed
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.document = None
        st.session_state.framework = None
        st.session_state.strategy = None
        st.session_state.assessment_results = None
        st.session_state.theme = "dark"  # Default to dark theme
    
    # Initialize sidebar
    with st.sidebar:
        st.title("📊 Multi-Agent Document Assessment Framwork")
        
        # Only show model selector if environment variables loaded successfully
        if hasattr(st.session_state, "api_key") and st.session_state.api_key:
            # Model selection (with environment default)
            model_options = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
            default_index = 0
            if st.session_state.model in model_options:
                default_index = model_options.index(st.session_state.model)
            
            selected_model = st.selectbox(
                "AI Model", 
                model_options, 
                index=default_index, 
                key="model_selection"
            )
            
            # Update session state if user changed the model
            if selected_model != st.session_state.model:
                st.session_state.model = selected_model
                logger.info(f"Model changed to: {selected_model}")
        
        # Add configuration header with some space
        st.sidebar.markdown("## Settings")
        
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
        st.sidebar.caption("Multi-Agent Document Assessment Framwork")
        st.sidebar.caption("Version 1.1.0")
        st.sidebar.caption("© 2025 Naleszkiewicz")

# Display homepage content
def display_homepage():
    """Display the main homepage content."""
    # Create a header with logo and title
    st.markdown(
        """
        <div style="display: flex; align-items: center; margin-bottom: 25px;">
            <div style="font-size: 3.5rem; margin-right: 20px;">📊</div>
            <div>
                <div style="font-size: 2.5rem; font-weight: 600;">Multi-Agent Document Assessment Framwork</div>
                <div style="color: #A0A0A0; font-size: 1.2rem;">Transform Documents into Structured Insights</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Primary value proposition
    st.markdown(
        """
        ## Enterprise Document Analysis
        
        Multi-Agent Document Assessment Framwork helps you extract structured insights from unstructured documents using advanced AI. 
        Compare documents against customizable frameworks, identify key insights, and generate comprehensive assessments.
        
        ### Key Benefits
        """
    )
    
    # Create metrics with the new UI components
    metrics = [
        {"label": "Structured Analysis", "value": "✓", "description": "Transform unstructured content into actionable insights"},
        {"label": "Custom Frameworks", "value": "✓", "description": "Create and use your own assessment frameworks"},
        {"label": "Evidence-Based", "value": "✓", "description": "All assessments linked directly to document evidence"}
    ]
    
    ui_components.metric_row(metrics)
    
    # Create feature cards
    st.markdown("## How It Works")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with ui_components.card_container("1. Create Framework"):
            st.markdown("📋")
            st.markdown(
                """
                Define your assessment criteria in a structured framework. 
                Use existing templates or create custom frameworks for your specific needs.
                """
            )
        ui_components.end_card_container()
        
    with col2:
        with ui_components.card_container("2. Upload Document"):
            st.markdown("📄")
            st.markdown(
                """
                Upload a document to be assessed against your framework.
                The system works with various document formats and content types.
                """
            )
        ui_components.end_card_container()
        
    with col3:
        with ui_components.card_container("3. Review Insights"):
            st.markdown("📊")
            st.markdown(
                """
                Get a comprehensive assessment with ratings, evidence, and structured insights.
                Export results or dig deeper into specific areas.
                """
            )
        ui_components.end_card_container()
    
    # Call to action
    st.markdown(
        """
        ## Get Started
        
        Use the sidebar navigation to access the main tools:
        
        - **Framework Assessment**: Assess documents against frameworks
        - **Pipeline Viewer**: Inspect the analysis process in detail
        - **Assessment Viewer**: Explore results with enhanced visualization
        """
    )
    
    # Sample images or information
    st.markdown("## Sample Framework Assessment")
    
    # Add a sample image or description
    st.markdown(
        """
        <div style="background-color: #1F2937; padding: 20px; border-radius: 10px; 
             border: 1px solid #3B4252; text-align: center; margin-top: 15px;">
            <div style="color: #E0E0E0; margin-bottom: 10px;">Sample Assessment Result</div>
            <div style="font-size: 4rem; color: #4F8BF9;">📊</div>
            <div style="color: #A0A0A0; font-style: italic; margin-top: 10px;">
                Upload a document to see a complete assessment with ratings, evidence, and recommendations.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

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
    display_homepage()
    
    # Check for API key
    if not env_loaded:
        st.warning(
            "OpenAI API Key not found in environment variables. "
            "Please add it to your .env file to use the application."
        )
        
        # Show .env example
        with st.expander("How to set up your .env file"):
            st.code(
                """
                # Create a file named .env in the project root directory with these contents:
                OPENAI_API_KEY=your_openai_api_key_here
                
                # You can also add other configuration options:
                # MODEL=gpt-4-turbo
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
        "name": "Content Quality Framework",
        "description": "A framework for assessing document content quality and structure",
        "dimensions": [
            {
                "id": "dimension_1",
                "name": "Content Quality",
                "description": "Assessment of overall content quality and clarity",
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
                        "name": "Accuracy",
                        "question": "How accurate is the information in the document?",
                        "scoring_method": "scale_1_5",
                        "scoring_definitions": {
                            "1": "Significant inaccuracies found",
                            "3": "Generally accurate with minor errors",
                            "5": "Highly accurate with verified information"
                        }
                    },
                    {
                        "id": "criterion_1_3",
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
                "name": "Document Structure",
                "description": "Assessment of document organization and formatting",
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
                        "question": "Is the document properly formatted with headings, sections, and visual aids?",
                        "scoring_method": "scale_1_5",
                        "scoring_definitions": {
                            "1": "Poor formatting, lacks structure",
                            "3": "Adequate formatting with basic structure",
                            "5": "Excellent formatting with clear hierarchy"
                        }
                    },
                    {
                        "id": "criterion_2_3",
                        "name": "Accessibility",
                        "question": "How accessible is the document for different readers?",
                        "scoring_method": "scale_1_5",
                        "scoring_definitions": {
                            "1": "Not accessible, difficult for many readers",
                            "3": "Moderately accessible with some barriers",
                            "5": "Highly accessible for diverse readers"
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