"""
Enhanced UI Styles for Framework Assessment Workbench

Modernized styles for a professional, sleek UI appearance optimized for dark theme.
Includes animations, improved color palette, and responsive design elements.
"""

import streamlit as st

# Enhanced color palette (dark theme optimized)
COLORS = {
    # Primary palette
    "primary": "#4F8BF9",           # Main brand color (blue)
    "primary_light": "#6C9FFF",     # Lighter variant
    "primary_dark": "#3A77E6",      # Darker variant
    
    # Secondary colors
    "secondary": "#FF8C00",         # Secondary brand color (orange)
    "accent": "#8A2BE2",            # Accent color (purple)
    
    # Status colors
    "success": "#00CC96",           # Success/positive (green)
    "warning": "#FFBB28",           # Warning/caution (yellow)
    "danger": "#FF6B6B",            # Error/danger (red)
    "info": "#4F8BF9",              # Information (blue)
    
    # Neutrals
    "dark": "#1E1E1E",              # Background
    "card_bg": "#1F2937",           # Card background
    "panel": "#2E3440",             # Panel background
    "border": "#3B4252",            # Border color
    "divider": "rgba(59, 66, 82, 0.5)", # Divider lines
    
    # Text
    "text": "#E0E0E0",              # Primary text
    "text_secondary": "#A0A0A0",    # Secondary text
    "text_tertiary": "#707070",     # Tertiary text
    "text_disabled": "#505050",     # Disabled text
    
    # Miscellaneous
    "highlight": "#FFD866",         # Highlight color
    "elevation_1": "rgba(0, 0, 0, 0.1)", # Subtle shadow
    "elevation_2": "rgba(0, 0, 0, 0.2)", # Medium shadow
    "elevation_3": "rgba(0, 0, 0, 0.3)", # Strong shadow
}

# Rating color scale with smoother gradations
RATING_COLORS = {
    0: "#888888",  # N/A or undefined (gray)
    1: "#FF6B6B",  # Very poor (red)
    1.5: "#FF8067", # Poor-leaning (red-orange)
    2: "#FF9E72",  # Poor (orange)
    2.5: "#FFB760", # Below average (orange-yellow)
    3: "#FFD166",  # Average (yellow)
    3.5: "#C4E072", # Above average (yellow-green)
    4: "#8AC926",  # Good (light green)
    4.5: "#3EB489", # Very good (blue-green)
    5: "#00CC96",  # Excellent (green)
}

# Animation durations
ANIMATIONS = {
    "fast": "0.2s",
    "medium": "0.3s",
    "slow": "0.5s",
}

# Font settings
TYPOGRAPHY = {
    "font_family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif",
    "heading_weight": "600",
    "body_weight": "400",
    "code_font": "'Source Code Pro', 'Courier New', monospace",
}

# Spacing scale (in px)
SPACING = {
    "xs": "4px",
    "sm": "8px",
    "md": "16px",
    "lg": "24px",
    "xl": "32px",
    "xxl": "48px",
}

# Border radius scale
RADIUS = {
    "sm": "4px",
    "md": "8px",
    "lg": "12px", 
    "xl": "16px",
    "pill": "500px",
}

def apply_styles():
    """Apply enhanced CSS styles to the current page with animations and improved components."""
    st.markdown(
        f"""
        <style>
        /* Global styles */
        * {{
            box-sizing: border-box;
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        html, body, [data-testid="stAppViewContainer"] {{
            background-color: {COLORS["dark"]};
            color: {COLORS["text"]};
            font-family: {TYPOGRAPHY["font_family"]};
        }}
        
        /* Streamlit container adjustments */
        .main .block-container {{
            padding-top: 1rem;
            max-width: 1200px;
        }}
        
        /* Typography enhancements */
        h1, h2, h3, h4, h5, h6 {{
            font-family: {TYPOGRAPHY["font_family"]};
            font-weight: {TYPOGRAPHY["heading_weight"]};
            color: {COLORS["text"]};
            margin-bottom: {SPACING["md"]};
        }}
        
        .main h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            color: {COLORS["text"]};
            margin-bottom: {SPACING["lg"]};
            padding-bottom: {SPACING["sm"]};
            border-bottom: 2px solid {COLORS["border"]};
        }}
        
        .main h2 {{
            font-size: 1.8rem;
            color: {COLORS["text"]};
            margin-top: {SPACING["lg"]};
            margin-bottom: {SPACING["md"]};
            padding-bottom: {SPACING["xs"]};
        }}
        
        .main h3 {{
            font-size: 1.4rem;
            color: {COLORS["text"]};
            margin-top: {SPACING["md"]};
            margin-bottom: {SPACING["sm"]};
        }}
        
        .main h4 {{
            font-size: 1.2rem;
            color: {COLORS["text_secondary"]};
            margin-top: {SPACING["md"]};
            margin-bottom: {SPACING["sm"]};
        }}
        
        p, li, div {{
            color: {COLORS["text"]};
            font-weight: {TYPOGRAPHY["body_weight"]};
        }}
        
        /* Enhanced card styling */
        .enhanced-card {{
            border-radius: {RADIUS["lg"]};
            padding: {SPACING["lg"]};
            background-color: {COLORS["card_bg"]};
            box-shadow: 0 8px 16px {COLORS["elevation_3"]};
            margin-bottom: {SPACING["xl"]};
            border: 1px solid {COLORS["border"]};
            transition: all {ANIMATIONS["medium"]} ease;
        }}
        
        .enhanced-card:hover {{
            box-shadow: 0 12px 24px {COLORS["elevation_3"]};
            transform: translateY(-2px);
        }}
        
        /* Card header */
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: {SPACING["lg"]};
            border-bottom: 1px solid {COLORS["divider"]};
            padding-bottom: {SPACING["md"]};
        }}
        
        .card-icon {{
            font-size: 1.5rem;
            color: {COLORS["primary"]};
            margin-right: {SPACING["sm"]};
        }}
        
        /* Framework selection styled container */
        .framework-selection {{
            display: flex;
            align-items: center;
            gap: {SPACING["sm"]};
            margin-bottom: {SPACING["md"]};
        }}
        
        /* Enhanced metrics styling */
        .metrics-container {{
            display: flex;
            gap: {SPACING["md"]};
            margin-bottom: {SPACING["md"]};
        }}
        
        .metric-item {{
            flex: 1;
            background-color: {COLORS["panel"]};
            border-radius: {RADIUS["md"]};
            padding: {SPACING["md"]};
            text-align: center;
            border: 1px solid {COLORS["border"]};
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        .metric-item:hover {{
            border-color: {COLORS["primary"]};
            transform: translateY(-2px);
            box-shadow: 0 4px 8px {COLORS["elevation_2"]};
        }}
        
        .metric-value {{
            font-size: 1.8rem;
            font-weight: 600;
            color: {COLORS["text"]};
        }}
        
        .metric-label {{
            font-size: 0.9rem;
            color: {COLORS["text_secondary"]};
            margin-top: {SPACING["xs"]};
        }}
        
        /* Upload area styling */
        .upload-area {{
            border: 2px dashed {COLORS["border"]};
            border-radius: {RADIUS["lg"]};
            padding: {SPACING["xl"]};
            text-align: center;
            margin-bottom: {SPACING["lg"]};
            transition: all {ANIMATIONS["medium"]} ease;
        }}
        
        .upload-area:hover {{
            border-color: {COLORS["primary"]};
            background-color: rgba(79, 139, 249, 0.05);
        }}
        
        .upload-icon {{
            font-size: 2rem;
            color: {COLORS["text_secondary"]};
            margin-bottom: {SPACING["sm"]};
        }}
        
        /* Progress bar enhancements */
        .enhanced-progress {{
            height: 10px;
            background-color: rgba(79, 139, 249, 0.2);
            border-radius: {RADIUS["sm"]};
            margin-bottom: {SPACING["sm"]};
            overflow: hidden;
        }}
        
        .progress-value {{
            height: 100%;
            background-color: {COLORS["primary"]};
            border-radius: {RADIUS["sm"]};
            transition: width {ANIMATIONS["slow"]} ease;
        }}
        
        /* Enhanced button styling */
        .primary-button {{
            background-color: {COLORS["primary"]};
            color: white;
            border: none;
            padding: {SPACING["sm"]} {SPACING["md"]};
            border-radius: {RADIUS["md"]};
            font-weight: 500;
            cursor: pointer;
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        .primary-button:hover {{
            background-color: {COLORS["primary_dark"]};
            transform: translateY(-1px);
            box-shadow: 0 4px 8px {COLORS["elevation_2"]};
        }}
        
        /* Evidence item styling */
        .evidence-item {{
            border-left: 4px solid {COLORS["primary"]};
            padding: {SPACING["md"]};
            margin-bottom: {SPACING["md"]};
            background-color: {COLORS["panel"]};
            border-radius: 0 {RADIUS["md"]} {RADIUS["md"]} 0;
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        .evidence-item:hover {{
            box-shadow: 0 4px 8px {COLORS["elevation_2"]};
            transform: translateY(-2px);
        }}
        
        /* Rating badge */
        .rating-badge {{
            display: inline-block;
            padding: {SPACING["xs"]} {SPACING["md"]};
            border-radius: {RADIUS["pill"]};
            font-weight: 600;
            color: white;
            text-align: center;
        }}
        
        /* Tag styling */
        .tag {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: {RADIUS["pill"]};
            font-size: 0.8rem;
            margin-right: {SPACING["xs"]};
            margin-bottom: {SPACING["xs"]};
        }}
        
        /* Keyword cloud styling */
        .keyword-cloud {{
            display: flex;
            flex-wrap: wrap;
            gap: {SPACING["xs"]};
            margin-top: {SPACING["sm"]};
        }}
        
        .keyword-tag {{
            display: inline-block;
            background-color: rgba(79, 139, 249, 0.1);
            color: {COLORS["primary"]};
            padding: 5px 10px;
            border-radius: {RADIUS["pill"]};
            margin: 0 5px 5px 0;
            font-size: 0.9rem;
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        .keyword-tag:hover {{
            background-color: rgba(79, 139, 249, 0.2);
            transform: translateY(-2px);
        }}
        
        /* Animation for progress */
        @keyframes pulse {{
            0% {{
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(79, 139, 249, 0.7);
            }}
            
            70% {{
                transform: scale(1);
                box-shadow: 0 0 0 10px rgba(79, 139, 249, 0);
            }}
            
            100% {{
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(79, 139, 249, 0);
            }}
        }}
        
        .pulse {{
            animation: pulse 2s infinite;
        }}
        
        /* Header container styling */
        .header-container {{
            padding: {SPACING["lg"]} 0;
            border-bottom: 1px solid {COLORS["divider"]};
            margin-bottom: {SPACING["xl"]};
        }}
        
        /* Info box styling */
        .info-box {{
            background-color: rgba(79, 139, 249, 0.1);
            border-left: 4px solid {COLORS["primary"]};
            padding: {SPACING["md"]};
            border-radius: {RADIUS["md"]};
            margin: {SPACING["md"]} 0;
        }}
        
        .success-box {{
            background-color: rgba(0, 204, 150, 0.1);
            border-left: 4px solid {COLORS["success"]};
            padding: {SPACING["md"]};
            border-radius: {RADIUS["md"]};
            margin: {SPACING["md"]} 0;
        }}
        
        .warning-box {{
            background-color: rgba(255, 187, 40, 0.1);
            border-left: 4px solid {COLORS["warning"]};
            padding: {SPACING["md"]};
            border-radius: {RADIUS["md"]};
            margin: {SPACING["md"]} 0;
        }}
        
        .error-box {{
            background-color: rgba(255, 107, 107, 0.1);
            border-left: 4px solid {COLORS["danger"]};
            padding: {SPACING["md"]};
            border-radius: {RADIUS["md"]};
            margin: {SPACING["md"]} 0;
        }}
        
        /* Criterion card styling */
        .criterion-card {{
            border-left: 5px solid {COLORS["primary"]};
            background-color: {COLORS["panel"]};
            padding: {SPACING["md"]};
            border-radius: 0 {RADIUS["md"]} {RADIUS["md"]} 0;
            margin-bottom: {SPACING["md"]};
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        .criterion-card:hover {{
            box-shadow: 0 4px 12px {COLORS["elevation_3"]};
            transform: translateY(-2px);
        }}
        
        /* Status indicator styling */
        .status-indicator {{
            display: flex;
            align-items: center;
            margin-bottom: {SPACING["sm"]};
        }}
        
        .status-icon {{
            margin-right: {SPACING["sm"]};
        }}
        
        /* Timeline styling */
        .timeline {{
            position: relative;
            margin: {SPACING["xl"]} 0;
            padding-left: {SPACING["xl"]};
        }}
        
        .timeline::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 2px;
            background-color: {COLORS["border"]};
        }}
        
        .timeline-item {{
            position: relative;
            margin-bottom: {SPACING["lg"]};
        }}
        
        .timeline-item::before {{
            content: '';
            position: absolute;
            left: -{SPACING["xl"]};
            top: 5px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: {COLORS["primary"]};
            border: 2px solid {COLORS["dark"]};
        }}
        
        .timeline-content {{
            padding: {SPACING["md"]};
            background-color: {COLORS["panel"]};
            border-radius: {RADIUS["md"]};
            box-shadow: 0 2px 8px {COLORS["elevation_2"]};
        }}
        
        /* Streamlit component overrides */
        /* Buttons */
        .stButton > button {{
            border-radius: {RADIUS["md"]};
            border: 1px solid {COLORS["border"]};
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px {COLORS["elevation_2"]};
        }}
        
        /* Form inputs */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > div,
        .stTextArea > div > div > textarea {{
            background-color: {COLORS["panel"]};
            color: {COLORS["text"]};
            border: 1px solid {COLORS["border"]};
            border-radius: {RADIUS["md"]};
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        .stTextInput > div > div > input:focus,
        .stSelectbox > div > div > div:focus,
        .stTextArea > div > div > textarea:focus {{
            border: 1px solid {COLORS["primary"]};
            box-shadow: 0 0 0 2px rgba(79, 139, 249, 0.2);
        }}
        
        /* Checkbox */
        .stCheckbox > div > label > div[data-baseweb="checkbox"] > div {{
            background-color: {COLORS["panel"]};
            border-color: {COLORS["border"]};
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 2px;
            background-color: {COLORS["card_bg"]};
            border-radius: {RADIUS["md"]} {RADIUS["md"]} 0 0;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: {COLORS["panel"]};
            color: {COLORS["text_secondary"]};
            border-radius: {RADIUS["md"]} {RADIUS["md"]} 0 0;
            border: 1px solid {COLORS["border"]};
            border-bottom: none;
            padding: 8px 16px;
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {COLORS["primary"]};
            color: white;
        }}
        
        .stTabs [data-baseweb="tab-panel"] {{
            background-color: {COLORS["card_bg"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 0 {RADIUS["md"]} {RADIUS["md"]} {RADIUS["md"]};
            padding: 16px;
        }}
        
        /* Sliders */
        .stSlider > div > div > div > div {{
            background-color: {COLORS["primary"]};
        }}
        
        /* Expander */
        .streamlit-expanderHeader {{
            background-color: {COLORS["panel"]};
            border-radius: {RADIUS["md"]};
            border: 1px solid {COLORS["border"]};
            transition: all {ANIMATIONS["fast"]} ease;
        }}
        
        .streamlit-expanderHeader:hover {{
            background-color: rgba(79, 139, 249, 0.1);
        }}
        
        .streamlit-expanderContent {{
            background-color: {COLORS["card_bg"]};
            border: 1px solid {COLORS["border"]};
            border-top: none;
            border-radius: 0 0 {RADIUS["md"]} {RADIUS["md"]};
            padding: {SPACING["md"]};
        }}
        
        /* Data frames */
        .stDataFrame {{
            background-color: {COLORS["panel"]};
            border-radius: {RADIUS["md"]};
            overflow: hidden;
        }}
        
        .stDataFrame thead tr th {{
            background-color: {COLORS["card_bg"]};
            color: {COLORS["text"]};
        }}
        
        .stDataFrame tbody tr:nth-child(even) {{
            background-color: rgba(46, 52, 64, 0.5);
        }}
        
        .stDataFrame tbody tr:hover {{
            background-color: rgba(79, 139, 249, 0.1);
        }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {COLORS["dark"]};
            border-right: 1px solid {COLORS["border"]};
        }}
        
        /* Tooltips */
        div[data-baseweb="tooltip"] {{
            background-color: {COLORS["panel"]};
            border: 1px solid {COLORS["border"]};
            border-radius: {RADIUS["md"]};
            box-shadow: 0 4px 12px {COLORS["elevation_3"]};
        }}
        
        /* Scrollbars */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: {COLORS["dark"]};
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: {COLORS["border"]};
            border-radius: {RADIUS["pill"]};
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: {COLORS["primary"]};
        }}
        
        /* Card section separator */
        .card-section-separator {{
            height: 1px;
            background-color: {COLORS["divider"]};
            margin: {SPACING["lg"]} 0;
        }}
        
        /* Image styling */
        img {{
            border-radius: {RADIUS["md"]};
        }}
        
        /* Code snippets */
        code {{
            font-family: {TYPOGRAPHY["code_font"]};
            background-color: rgba(46, 52, 64, 0.5);
            padding: 2px 6px;
            border-radius: {RADIUS["sm"]};
            border: 1px solid {COLORS["border"]};
        }}
        
        pre {{
            background-color: {COLORS["panel"]};
            padding: {SPACING["md"]};
            border-radius: {RADIUS["md"]};
            border: 1px solid {COLORS["border"]};
            overflow-x: auto;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            border: none;
        }}

        /* Progress fade-in animation */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .fade-in {{
            animation: fadeIn {ANIMATIONS["medium"]} ease-in-out;
        }}
        
        /* Loader/spinner */
        .loader {{
            display: inline-block;
            width: 30px;
            height: 30px;
            border: 3px solid {COLORS["divider"]};
            border-radius: 50%;
            border-top-color: {COLORS["primary"]};
            animation: spin 1s ease-in-out infinite;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def rating_color(rating):
    """
    Get the color for a rating value with improved interpolation.
    
    Args:
        rating: Rating value (1-5)
        
    Returns:
        Color value
    """
    if rating is None or rating == "N/A":
        return COLORS["text_secondary"]
    
    try:
        rating_val = float(rating)
        
        # Handle exact matches
        if rating_val in RATING_COLORS:
            return RATING_COLORS[rating_val]
            
        # Handle values in between defined points via interpolation
        # Find the two closest defined points
        lower_key = None
        upper_key = None
        
        for key in sorted(RATING_COLORS.keys()):
            if key <= rating_val:
                lower_key = key
            if key >= rating_val and upper_key is None:
                upper_key = key
        
        # If we found bounds, interpolate between them
        if lower_key is not None and upper_key is not None and lower_key != upper_key:
            # Get the hex colors without the # prefix
            lower_color = RATING_COLORS[lower_key][1:]
            upper_color = RATING_COLORS[upper_key][1:]
            
            # Convert to RGB
            lr = int(lower_color[0:2], 16)
            lg = int(lower_color[2:4], 16)
            lb = int(lower_color[4:6], 16)
            
            ur = int(upper_color[0:2], 16)
            ug = int(upper_color[2:4], 16)
            ub = int(upper_color[4:6], 16)
            
            # Calculate interpolation factor
            factor = (rating_val - lower_key) / (upper_key - lower_key)
            
            # Interpolate RGB values
            r = int(lr + factor * (ur - lr))
            g = int(lg + factor * (ug - lg))
            b = int(lb + factor * (ub - lb))
            
            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
            
        # If we couldn't interpolate, use the closest defined color
        if lower_key is not None:
            return RATING_COLORS[lower_key]
        if upper_key is not None:
            return RATING_COLORS[upper_key]
            
        # Fallback to default color
        return COLORS["text_secondary"]
    except (ValueError, TypeError):
        return COLORS["text_secondary"]


def score_badge(score, text=None):
    """
    Generate HTML for a score badge with enhanced styling.
    
    Args:
        score: Score value (1-5)
        text: Optional text to display instead of score
        
    Returns:
        HTML string
    """
    if score is None:
        score_val = "N/A"
        bg_color = COLORS["text_secondary"]
    else:
        try:
            score_val = float(score)
            score_display = f"{score_val:.1f}"
            bg_color = rating_color(score_val)
        except (ValueError, TypeError):
            score_display = str(score)
            bg_color = COLORS["text_secondary"]
    
    display_text = text if text else score_display
    
    return f"""
    <span style="display: inline-block; background-color: {bg_color}; color: white; 
         font-weight: 600; padding: 4px 12px; border-radius: {RADIUS["pill"]};">
        {display_text}
    </span>
    """


def badge(text, style="primary"):
    """
    Generate HTML for a badge with enhanced styling.
    
    Args:
        text: Badge text
        style: Badge style (primary, secondary, success, warning, danger)
        
    Returns:
        HTML string
    """
    color = COLORS.get(style, COLORS["primary"])
    
    return f"""
    <span style="display: inline-block; background-color: {color}; color: white; 
         font-size: 0.8rem; font-weight: 500; padding: 2px 8px; 
         border-radius: {RADIUS["pill"]}; margin-right: 5px;">
        {text}
    </span>
    """


def info_box(title, content):
    """
    Generate HTML for an info box with enhanced styling.
    
    Args:
        title: Box title
        content: Box content
        
    Returns:
        HTML string
    """
    return f"""
    <div style="background-color: rgba(79, 139, 249, 0.1); border-left: 4px solid {COLORS["primary"]}; 
         padding: {SPACING["md"]}; border-radius: {RADIUS["md"]}; margin: {SPACING["md"]} 0;">
        <div style="font-weight: 500; margin-bottom: 5px; color: {COLORS["text"]};">{title}</div>
        <div style="color: {COLORS["text_secondary"]};">{content}</div>
    </div>
    """


def warning_box(title, content):
    """
    Generate HTML for a warning box with enhanced styling.
    
    Args:
        title: Box title
        content: Box content
        
    Returns:
        HTML string
    """
    return f"""
    <div style="background-color: rgba(255, 187, 40, 0.1); border-left: 4px solid {COLORS["warning"]}; 
         padding: {SPACING["md"]}; border-radius: {RADIUS["md"]}; margin: {SPACING["md"]} 0;">
        <div style="font-weight: 500; margin-bottom: 5px; color: {COLORS["text"]};">{title}</div>
        <div style="color: {COLORS["text_secondary"]};">{content}</div>
    </div>
    """


def error_box(title, content):
    """
    Generate HTML for an error box with enhanced styling.
    
    Args:
        title: Box title
        content: Box content
        
    Returns:
        HTML string
    """
    return f"""
    <div style="background-color: rgba(255, 107, 107, 0.1); border-left: 4px solid {COLORS["danger"]}; 
         padding: {SPACING["md"]}; border-radius: {RADIUS["md"]}; margin: {SPACING["md"]} 0;">
        <div style="font-weight: 500; margin-bottom: 5px; color: {COLORS["text"]};">{title}</div>
        <div style="color: {COLORS["text_secondary"]};">{content}</div>
    </div>
    """


def success_box(title, content):
    """
    Generate HTML for a success box with enhanced styling.
    
    Args:
        title: Box title
        content: Box content
        
    Returns:
        HTML string
    """
    return f"""
    <div style="background-color: rgba(0, 204, 150, 0.1); border-left: 4px solid {COLORS["success"]}; 
         padding: {SPACING["md"]}; border-radius: {RADIUS["md"]}; margin: {SPACING["md"]} 0;">
        <div style="font-weight: 500; margin-bottom: 5px; color: {COLORS["text"]};">{title}</div>
        <div style="color: {COLORS["text_secondary"]};">{content}</div>
    </div>
    """


def card(content, header=None, icon=None, rating=None):
    """
    Generate HTML for a card with enhanced styling.
    
    Args:
        content: Card content
        header: Optional card header
        icon: Optional icon for the header
        rating: Optional rating (1-5) for color indication
        
    Returns:
        HTML string
    """
    border_color = rating_color(rating) if rating is not None else COLORS["border"]
    icon_html = f'<div class="card-icon">{icon}</div>' if icon else ""
    header_html = """
    <div class="card-header">
        <div style="display: flex; align-items: center;">
            {icon}
            <h3>{header}</h3>
        </div>
    </div>
    """.format(icon=icon_html, header=header) if header else ""
    
    return f"""
    <div style="border-radius: {RADIUS["lg"]}; padding: {SPACING["lg"]}; 
         background-color: {COLORS["card_bg"]}; box-shadow: 0 8px 16px {COLORS["elevation_3"]}; 
         margin-bottom: {SPACING["lg"]}; border: 1px solid {COLORS["border"]}; 
         border-left: 5px solid {border_color}; transition: all {ANIMATIONS["medium"]} ease;">
        {header_html}
        {content}
    </div>
    """


def metric_card(label, value, description=None):
    """
    Generate HTML for a metric card with enhanced styling.
    
    Args:
        label: Metric label
        value: Metric value
        description: Optional description
        
    Returns:
        HTML string
    """
    description_html = f'<div style="color: {COLORS["text_secondary"]}; margin-top: 5px; font-size: 0.9rem;">{description}</div>' if description else ""
    
    return f"""
    <div style="background-color: {COLORS["panel"]}; border-radius: {RADIUS["md"]}; 
         padding: {SPACING["md"]}; text-align: center; border: 1px solid {COLORS["border"]};
         transition: all {ANIMATIONS["fast"]} ease;">
        <div style="font-size: 0.9rem; color: {COLORS["text_secondary"]}; margin-bottom: 5px;">{label}</div>
        <div style="font-size: 1.8rem; font-weight: 600; color: {COLORS["text"]};">{value}</div>
        {description_html}
    </div>
    """


def insight_box(title, items):
    """
    Generate HTML for an insight box with enhanced styling.
    
    Args:
        title: Box title
        items: List of insight items
        
    Returns:
        HTML string
    """
    items_html = ""
    for item in items:
        items_html += f"""
        <div style="display: flex; margin-bottom: 8px;">
            <div style="color: {COLORS["primary"]}; margin-right: 10px;">•</div>
            <div style="color: {COLORS["text"]};">{item}</div>
        </div>
        """
    
    return f"""
    <div style="background-color: {COLORS["panel"]}; border-radius: {RADIUS["md"]}; 
         padding: {SPACING["md"]}; border: 1px solid {COLORS["border"]}; margin-bottom: {SPACING["md"]};">
        <div style="font-weight: 500; margin-bottom: 10px; color: {COLORS["text"]};">{title}</div>
        <div>
            {items_html}
        </div>
    </div>
    """


def styled_table(headers, rows):
    """
    Generate HTML for a styled table with enhanced styling.
    
    Args:
        headers: List of header strings
        rows: List of row data lists
        
    Returns:
        HTML string
    """
    headers_html = ""
    for header in headers:
        headers_html += f"<th style='text-align: left; padding: 12px; background-color: {COLORS['panel']}; color: {COLORS['text']}; font-weight: 600;'>{header}</th>"
    
    rows_html = ""
    for i, row in enumerate(rows):
        row_bg = f"rgba(46, 52, 64, {0.5 if i % 2 == 0 else 0.3})"
        row_html = ""
        for cell in row:
            row_html += f"<td style='padding: 10px 12px; color: {COLORS['text']};'>{cell}</td>"
        rows_html += f"<tr style='background-color: {row_bg}; transition: all {ANIMATIONS['fast']} ease;'>{row_html}</tr>"
    
    return f"""
    <div style="overflow-x: auto; margin: {SPACING["md"]} 0; border-radius: {RADIUS["md"]}; border: 1px solid {COLORS["border"]};">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
            <thead>
                <tr>{headers_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """


def expandable_section(header, content, expanded=False):
    """
    Generate HTML for an expandable section with enhanced styling.
    
    Args:
        header: Section header
        content: Section content
        expanded: Whether the section is expanded by default
        
    Returns:
        HTML string
    """
    expanded_class = "active" if expanded else ""
    display_style = "block" if expanded else "none"
    arrow = "▼" if expanded else "▶"
    
    return f"""
    <div class="expandable-section {expanded_class}" style="margin-bottom: {SPACING["md"]};">
        <div class="expandable-header" style="display: flex; justify-content: space-between; 
             align-items: center; padding: {SPACING["md"]}; background-color: {COLORS["panel"]}; 
             border-radius: {RADIUS["md"]}; cursor: pointer; border: 1px solid {COLORS["border"]};">
            <div style="font-weight: 500; color: {COLORS["text"]};">{header}</div>
            <div class="expandable-arrow">{arrow}</div>
        </div>
        <div class="expandable-content" style="padding: {SPACING["md"]}; background-color: {COLORS["card_bg"]}; 
             border: 1px solid {COLORS["border"]}; border-top: none; display: {display_style}; 
             border-radius: 0 0 {RADIUS["md"]} {RADIUS["md"]};">
            {content}
        </div>
    </div>
    <script>
        // Add click event to expandable headers
        const headers = window.parent.document.querySelectorAll('.expandable-header');
        headers.forEach((header) => {{
            header.addEventListener('click', () => {{
                const parent = header.parentElement;
                parent.classList.toggle('active');
                const content = header.nextElementSibling;
                content.style.display = content.style.display === 'none' ? 'block' : 'none';
                const arrow = header.querySelector('.expandable-arrow');
                arrow.textContent = parent.classList.contains('active') ? '▼' : '▶';
            }});
        }});
    </script>
    """


def evidence_item(text, relevance=None, confidence=None, sentiment=None):
    """
    Generate HTML for an evidence item with enhanced styling.
    
    Args:
        text: Evidence text
        relevance: Optional relevance label
        confidence: Optional confidence score
        sentiment: Optional sentiment label
        
    Returns:
        HTML string
    """
    # Define colors for different relevance types
    relevance_colors = {
        "direct": COLORS["success"],
        "indirect": COLORS["secondary"],
        "contextual": COLORS["primary"],
        "implied": COLORS["accent"]
    }
    
    # Define colors for different sentiment types
    sentiment_colors = {
        "positive": COLORS["success"],
        "negative": COLORS["danger"],
        "neutral": COLORS["primary"]
    }
    
    # Determine border color based on relevance or sentiment
    border_color = COLORS["border"]
    if sentiment and sentiment.lower() in sentiment_colors:
        border_color = sentiment_colors[sentiment.lower()]
    elif relevance and relevance.lower() in relevance_colors:
        border_color = relevance_colors[relevance.lower()]
    
    # Format relevance badge if provided
    relevance_html = ""
    if relevance:
        relevance_color = relevance_colors.get(relevance.lower(), COLORS["primary"])
        relevance_html = f"""
        <span style="display: inline-block; background-color: {relevance_color}; color: white; 
             font-size: 0.8rem; padding: 2px 8px; border-radius: {RADIUS["pill"]}; margin-right: 5px;">
            {relevance.title()}
        </span>
        """
    
    # Format sentiment badge if provided
    sentiment_html = ""
    if sentiment:
        sentiment_color = sentiment_colors.get(sentiment.lower(), COLORS["primary"])
        sentiment_html = f"""
        <span style="display: inline-block; background-color: {sentiment_color}; color: white; 
             font-size: 0.8rem; padding: 2px 8px; border-radius: {RADIUS["pill"]}; margin-right: 5px;">
            {sentiment.title()}
        </span>
        """
    
    # Format confidence display if provided
    confidence_html = ""
    if confidence is not None:
        try:
            conf_val = float(confidence)
            confidence_html = f"""
            <span style="display: inline-block; color: {COLORS["text_secondary"]}; font-size: 0.8rem;">
                Confidence: {conf_val:.2f}
            </span>
            """
        except (ValueError, TypeError):
            confidence_html = f"""
            <span style="display: inline-block; color: {COLORS["text_secondary"]}; font-size: 0.8rem;">
                Confidence: {confidence}
            </span>
            """
    
    return f"""
    <div style="border-left: 4px solid {border_color}; padding: {SPACING["md"]}; 
         margin-bottom: {SPACING["md"]}; background-color: {COLORS["panel"]}; 
         border-radius: 0 {RADIUS["md"]} {RADIUS["md"]} 0; transition: all {ANIMATIONS["fast"]} ease;">
        <div style="font-style: italic; color: {COLORS["text"]}; margin-bottom: 10px; 
             padding: 10px; background-color: rgba(0, 0, 0, 0.1); border-radius: {RADIUS["md"]};">
            "{text}"
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                {relevance_html}
                {sentiment_html}
            </div>
            <div>
                {confidence_html}
            </div>
        </div>
    </div>
    """


def rating_badge(rating, max_rating=5):
    """
    Generate HTML for a rating badge with enhanced styling.
    
    Args:
        rating: Rating value (1-5)
        max_rating: Maximum possible rating
        
    Returns:
        HTML string
    """
    if rating is None or rating == "N/A":
        return f"""
        <span style="display: inline-block; background-color: {COLORS["text_secondary"]}; 
             color: white; font-weight: 600; padding: 4px 12px; border-radius: {RADIUS["pill"]};">
            N/A
        </span>
        """
    
    try:
        rating_val = float(rating)
        rating_color = rating_color(rating_val)
        
        return f"""
        <span style="display: inline-block; background-color: {rating_color}; 
             color: white; font-weight: 600; padding: 4px 12px; border-radius: {RADIUS["pill"]};">
            {rating_val:.1f}
        </span>
        """
    except (ValueError, TypeError):
        return f"""
        <span style="display: inline-block; background-color: {COLORS["text_secondary"]}; 
             color: white; font-weight: 600; padding: 4px 12px; border-radius: {RADIUS["pill"]};">
            {rating}
        </span>
        """


def progress_bar(value, max_value=1.0, color=None):
    """
    Generate HTML for a progress bar with enhanced styling.
    
    Args:
        value: Current progress value
        max_value: Maximum progress value
        color: Optional custom color
        
    Returns:
        HTML string
    """
    # Calculate percentage
    if max_value == 0:
        percentage = 0
    else:
        percentage = min(100, max(0, (value / max_value) * 100))
    
    # Determine color based on progress
    if color is None:
        if percentage < 30:
            bar_color = COLORS["danger"]
        elif percentage < 70:
            bar_color = COLORS["warning"]
        else:
            bar_color = COLORS["success"]
    else:
        bar_color = color
    
    return f"""
    <div style="margin: {SPACING["sm"]} 0;">
        <div style="height: 8px; background-color: rgba(255, 255, 255, 0.1); 
             border-radius: {RADIUS["pill"]}; overflow: hidden;">
            <div style="height: 100%; width: {percentage}%; background-color: {bar_color}; 
                 border-radius: {RADIUS["pill"]}; transition: width {ANIMATIONS["medium"]} ease;"></div>
        </div>
        <div style="text-align: right; font-size: 0.8rem; color: {COLORS["text_secondary"]}; margin-top: 2px;">
            {percentage:.1f}%
        </div>
    </div>
    """


def keyword_cloud(keywords):
    """
    Generate HTML for a keyword cloud with enhanced styling.
    
    Args:
        keywords: List of keyword strings
        
    Returns:
        HTML string
    """
    if not keywords:
        return ""
    
    keyword_html = ""
    for keyword in keywords:
        keyword_html += f"""
        <span style="display: inline-block; background-color: rgba(79, 139, 249, 0.1); 
             color: {COLORS["primary"]}; padding: 5px 10px; border-radius: {RADIUS["pill"]}; 
             margin: 0 5px 5px 0; font-size: 0.9rem; transition: all {ANIMATIONS["fast"]} ease;">
            {keyword}
        </span>
        """
    
    return f"""
    <div style="display: flex; flex-wrap: wrap; margin: {SPACING["md"]} 0;">
        {keyword_html}
    </div>
    """


def status_indicator(status, message=None):
    """
    Generate HTML for a status indicator with enhanced styling.
    
    Args:
        status: Status type (success, warning, error, info)
        message: Optional status message
        
    Returns:
        HTML string
    """
    # Define icons and colors for different status types
    status_config = {
        "success": {"icon": "✓", "color": COLORS["success"]},
        "warning": {"icon": "⚠️", "color": COLORS["warning"]},
        "error": {"icon": "✗", "color": COLORS["danger"]},
        "info": {"icon": "ℹ", "color": COLORS["primary"]},
        "pending": {"icon": "⏳", "color": COLORS["text_secondary"]},
    }
    
    # Get configuration for the specified status
    config = status_config.get(status.lower(), status_config["info"])
    message_html = f'<div style="color: {COLORS["text_secondary"]};">{message}</div>' if message else ""
    
    return f"""
    <div style="display: flex; align-items: center; margin: {SPACING["sm"]} 0;">
        <div style="background-color: rgba({','.join(str(int(config['color'][1:3], 16)) for c in config['color'][1:].strip('#'))}, 0.1); 
             border-radius: 50%; width: 24px; height: 24px; display: flex; 
             align-items: center; justify-content: center; margin-right: 10px;">
            <div style="color: {config['color']};">{config['icon']}</div>
        </div>
        <div>
            <div style="font-weight: 500; color: {COLORS["text"]};">{status.title()}</div>
            {message_html}
        </div>
    </div>
    """


def timeline_item(title, content, time=None, status=None):
    """
    Generate HTML for a timeline item with enhanced styling.
    
    Args:
        title: Item title
        content: Item content
        time: Optional time string
        status: Optional status (success, warning, error, info)
        
    Returns:
        HTML string
    """
    # Define colors for different status types
    status_colors = {
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "error": COLORS["danger"],
        "info": COLORS["primary"],
        "pending": COLORS["text_secondary"]
    }
    
    # Get color for the specified status
    dot_color = status_colors.get(status.lower() if status else None, COLORS["primary"])
    time_html = f'<div style="color: {COLORS["text_secondary"]}; font-size: 0.8rem;">{time}</div>' if time else ""
    
    return f"""
    <div style="position: relative; padding-left: 20px; margin-bottom: {SPACING["md"]};">
        <div style="position: absolute; left: 0; top: 6px; width: 10px; height: 10px; 
             border-radius: 50%; background-color: {dot_color};"></div>
        <div style="font-weight: 500; color: {COLORS["text"]};">{title}</div>
        {time_html}
        <div style="margin-top: 5px; color: {COLORS["text_secondary"]};">{content}</div>
    </div>
    """


def timeline(items):
    """
    Generate HTML for a timeline with enhanced styling.
    
    Args:
        items: List of dictionaries with title, content, time, and status keys
        
    Returns:
        HTML string
    """
    if not items:
        return ""
    
    items_html = ""
    for item in items:
        items_html += timeline_item(
            item.get("title", ""),
            item.get("content", ""),
            item.get("time"),
            item.get("status")
        )
    
    return f"""
    <div style="position: relative; margin: {SPACING["md"]} 0 {SPACING["md"]} 10px; padding-left: 20px;">
        <div style="position: absolute; left: 4px; top: 0; bottom: 0; width: 2px; background-color: {COLORS["border"]};"></div>
        {items_html}
    </div>
    """


def loading_spinner(text=None):
    """
    Generate HTML for a loading spinner with enhanced styling.
    
    Args:
        text: Optional loading text
        
    Returns:
        HTML string
    """
    text_html = f'<div style="margin-left: 15px; color: {COLORS["text"]};">{text}</div>' if text else ""
    
    return f"""
    <div style="display: flex; align-items: center; justify-content: center; padding: {SPACING["md"]};">
        <div style="width: 30px; height: 30px; border: 3px solid {COLORS["divider"]}; 
             border-radius: 50%; border-top-color: {COLORS["primary"]}; 
             animation: spin 1s ease-in-out infinite;"></div>
        {text_html}
    </div>
    <style>
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
    """


def empty_state(icon, title, description=None, button_text=None, button_link=None):
    """
    Generate HTML for an empty state with enhanced styling.
    
    Args:
        icon: Empty state icon
        title: Empty state title
        description: Optional description
        button_text: Optional button text
        button_link: Optional button link
        
    Returns:
        HTML string
    """
    description_html = f'<div style="color: {COLORS["text_secondary"]}; margin-top: 10px;">{description}</div>' if description else ""
    
    button_html = ""
    if button_text:
        if button_link:
            button_html = f"""
            <a href="{button_link}" style="display: inline-block; background-color: {COLORS["primary"]}; 
                color: white; border: none; padding: 8px 16px; border-radius: {RADIUS["md"]}; 
                font-weight: 500; text-decoration: none; margin-top: 15px; 
                transition: all {ANIMATIONS["fast"]} ease;">
                {button_text}
            </a>
            """
        else:
            button_html = f"""
            <button style="background-color: {COLORS["primary"]}; color: white; border: none; 
                    padding: 8px 16px; border-radius: {RADIUS["md"]}; font-weight: 500; 
                    cursor: pointer; margin-top: 15px; transition: all {ANIMATIONS["fast"]} ease;">
                {button_text}
            </button>
            """
    
    return f"""
    <div style="text-align: center; padding: {SPACING["xl"]} 0;">
        <div style="font-size: 3rem; color: {COLORS["primary"]}; margin-bottom: 15px;">{icon}</div>
        <div style="font-weight: 500; color: {COLORS["text"]}; margin-bottom: 10px; font-size: 1.2rem;">{title}</div>
        {description_html}
        {button_html}
    </div>
    """


def tab_group(tabs):
    """
    Generate HTML for a custom tab group with enhanced styling.
    
    Args:
        tabs: Dictionary mapping tab labels to content
        
    Returns:
        HTML string with JavaScript for tab switching
    """
    if not tabs:
        return ""
    
    # Generate unique ID for this tab group
    import random
    import string
    tab_group_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    # Generate tab headers
    headers_html = ""
    contents_html = ""
    
    for i, (label, content) in enumerate(tabs.items()):
        tab_id = f"tab-{tab_group_id}-{i}"
        content_id = f"content-{tab_group_id}-{i}"
        active = " active" if i == 0 else ""
        display = "block" if i == 0 else "none"
        
        headers_html += f"""
        <div id="{tab_id}" class="custom-tab{active}" 
             onclick="switchTab('{tab_group_id}', {i})"
             style="padding: 10px 20px; cursor: pointer; border-bottom: 2px solid {COLORS['border'] if i > 0 else COLORS['primary']}; 
                    color: {COLORS['text_secondary'] if i > 0 else COLORS['text']}; 
                    font-weight: {400 if i > 0 else 500}; transition: all {ANIMATIONS['fast']} ease;">
            {label}
        </div>
        """
        
        contents_html += f"""
        <div id="{content_id}" class="tab-content" 
             style="padding: 20px 0; display: {display};">
            {content}
        </div>
        """
    
    return f"""
    <div class="custom-tabs" style="margin: {SPACING["md"]} 0;">
        <div style="display: flex; border-bottom: 2px solid {COLORS['border']}; margin-bottom: 15px;">
            {headers_html}
        </div>
        <div class="tab-contents">
            {contents_html}
        </div>
    </div>
    <script>
        function switchTab(groupId, activeIndex) {{
            // Get all tabs and contents for this group
            const tabs = Array.from(document.querySelectorAll(`[id^="tab-${{groupId}}-"]`));
            const contents = Array.from(document.querySelectorAll(`[id^="content-${{groupId}}-"]`));
            
            // Update tabs
            tabs.forEach((tab, index) => {{
                if (index === activeIndex) {{
                    tab.classList.add('active');
                    tab.style.borderBottomColor = '{COLORS["primary"]}';
                    tab.style.color = '{COLORS["text"]}';
                    tab.style.fontWeight = '500';
                }} else {{
                    tab.classList.remove('active');
                    tab.style.borderBottomColor = '{COLORS["border"]}';
                    tab.style.color = '{COLORS["text_secondary"]}';
                    tab.style.fontWeight = '400';
                }}
            }});
            
            // Update contents
            contents.forEach((content, index) => {{
                content.style.display = index === activeIndex ? 'block' : 'none';
            }});
        }}
    </script>
    """


def tooltip(content, tooltip_text):
    """
    Generate HTML for custom tooltip with enhanced styling.
    
    Args:
        content: Main content
        tooltip_text: Tooltip text
        
    Returns:
        HTML string with JavaScript for tooltip
    """
    # Generate unique ID for this tooltip
    import random
    import string
    tooltip_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    return f"""
    <div class="tooltip-container" style="position: relative; display: inline-block;">
        <div class="tooltip-content">
            {content}
        </div>
        <div id="tooltip-{tooltip_id}" class="tooltip" 
             style="position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%);
                    background-color: {COLORS["panel"]}; color: {COLORS["text"]};
                    padding: 8px 12px; border-radius: {RADIUS["md"]}; font-size: 0.9rem;
                    box-shadow: 0 4px 12px {COLORS["elevation_3"]}; z-index: 100;
                    visibility: hidden; opacity: 0; transition: all {ANIMATIONS["fast"]} ease;
                    white-space: nowrap; pointer-events: none; margin-bottom: 5px;
                    border: 1px solid {COLORS["border"]};">
            {tooltip_text}
            <div style="position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
                       width: 0; height: 0; border-left: 5px solid transparent;
                       border-right: 5px solid transparent; border-top: 5px solid {COLORS["panel"]};"></div>
        </div>
    </div>
    <style>
        .tooltip-container:hover #tooltip-{tooltip_id} {{
            visibility: visible;
            opacity: 1;
        }}
    </style>
    """


def copy_to_clipboard(content, button_text="Copy", success_text="Copied!"):
    """
    Generate HTML for copy-to-clipboard functionality with enhanced styling.
    
    Args:
        content: Content to copy
        button_text: Text for the copy button
        success_text: Text to show on successful copy
        
    Returns:
        HTML string with JavaScript for copying
    """
    # Generate unique ID for this component
    import random
    import string
    component_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    return f"""
    <div style="position: relative;">
        <div id="content-{component_id}" style="display: none;">{content}</div>
        <button id="copy-button-{component_id}" 
                onclick="copyToClipboard('{component_id}')"
                style="background-color: {COLORS["panel"]}; color: {COLORS["text"]};
                       border: 1px solid {COLORS["border"]}; padding: 6px 12px;
                       border-radius: {RADIUS["md"]}; cursor: pointer;
                       font-size: 0.9rem; transition: all {ANIMATIONS["fast"]} ease;">
            {button_text}
        </button>
    </div>
    <script>
        function copyToClipboard(id) {{
            const content = document.getElementById(`content-${{id}}`).innerText;
            const button = document.getElementById(`copy-button-${{id}}`);
            const originalText = button.innerText;
            
            // Copy to clipboard
            navigator.clipboard.writeText(content).then(() => {{
                // Update button text on success
                button.innerText = '{success_text}';
                button.style.backgroundColor = '{COLORS["success"]}';
                button.style.color = 'white';
                
                // Reset after 2 seconds
                setTimeout(() => {{
                    button.innerText = originalText;
                    button.style.backgroundColor = '{COLORS["panel"]}';
                    button.style.color = '{COLORS["text"]}';
                }}, 2000);
            }}).catch(err => {{
                console.error('Failed to copy:', err);
                
                // Show error
                button.innerText = 'Error!';
                button.style.backgroundColor = '{COLORS["danger"]}';
                button.style.color = 'white';
                
                // Reset after 2 seconds
                setTimeout(() => {{
                    button.innerText = originalText;
                    button.style.backgroundColor = '{COLORS["panel"]}';
                    button.style.color = '{COLORS["text"]}';
                }}, 2000);
            }});
        }}
    </script>
    """


def code_block(code, language=None, show_copy=True):
    """
    Generate HTML for a code block with enhanced styling and copy functionality.
    
    Args:
        code: Code content
        language: Optional programming language for syntax highlighting
        show_copy: Whether to show copy button
        
    Returns:
        HTML string
    """
    # Escape HTML in code
    import html
    escaped_code = html.escape(code)
    
    # Language indicator
    language_html = f"""
    <div style="position: absolute; right: 15px; top: 10px; font-size: 0.8rem; 
         color: {COLORS["text_secondary"]}; background-color: rgba(0, 0, 0, 0.2);
         padding: 2px 8px; border-radius: {RADIUS["pill"]};">
        {language}
    </div>
    """ if language else ""
    
    # Copy button
    copy_html = ""
    if show_copy:
        copy_html = f"""
        <div style="position: absolute; right: 10px; top: 10px;">
            {copy_to_clipboard(code, "Copy", "Copied!")}
        </div>
        """
    
    return f"""
    <div style="position: relative; margin: {SPACING["md"]} 0;">
        <pre style="background-color: {COLORS["panel"]}; padding: {SPACING["md"]}; 
             border-radius: {RADIUS["md"]}; border: 1px solid {COLORS["border"]}; 
             overflow-x: auto; font-family: {TYPOGRAPHY["code_font"]}; font-size: 0.9rem;
             line-height: 1.5; tab-size: 4;">
<code style="color: {COLORS["text"]};">{escaped_code}</code></pre>
        {language_html if not show_copy else ""}
        {copy_html}
    </div>
    """


def notification(message, type="info", dismissible=True):
    """
    Generate HTML for a notification with enhanced styling.
    
    Args:
        message: Notification message
        type: Notification type (info, success, warning, error)
        dismissible: Whether the notification can be dismissed
        
    Returns:
        HTML string with JavaScript for dismissal
    """
    # Define icons and colors for different notification types
    notification_config = {
        "info": {"icon": "ℹ", "color": COLORS["primary"]},
        "success": {"icon": "✓", "color": COLORS["success"]},
        "warning": {"icon": "⚠️", "color": COLORS["warning"]},
        "error": {"icon": "✗", "color": COLORS["danger"]},
    }
    
    # Get configuration for the specified type
    config = notification_config.get(type.lower(), notification_config["info"])
    
    # Generate unique ID for this notification
    import random
    import string
    notification_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    # Dismiss button
    dismiss_html = ""
    if dismissible:
        dismiss_html = f"""
        <div style="margin-left: 15px; cursor: pointer;" 
             onclick="document.getElementById('notification-{notification_id}').style.display = 'none';">
            ✕
        </div>
        """
    
    return f"""
    <div id="notification-{notification_id}" 
         style="display: flex; align-items: center; justify-content: space-between;
                background-color: rgba({','.join(str(int(config['color'][i:i+2], 16)) for i in range(1, 7, 2))}, 0.1);
                border-left: 4px solid {config['color']}; padding: 12px 15px;
                border-radius: {RADIUS["md"]}; margin: {SPACING["md"]} 0;
                animation: fadeIn {ANIMATIONS["medium"]} ease-in-out;">
        <div style="display: flex; align-items: center;">
            <div style="color: {config['color']}; margin-right: 10px;">{config['icon']}</div>
            <div style="color: {COLORS["text"]};">{message}</div>
        </div>
        {dismiss_html}
    </div>
    """


def avatar(text, background_color=None, text_color=None, size=40):
    """
    Generate HTML for an avatar with enhanced styling.
    
    Args:
        text: Avatar text (usually initials)
        background_color: Optional background color
        text_color: Optional text color
        size: Avatar size in pixels
        
    Returns:
        HTML string
    """
    if background_color is None:
        background_color = COLORS["primary"]
    
    if text_color is None:
        text_color = "white"
    
    return f"""
    <div style="width: {size}px; height: {size}px; background-color: {background_color};
         border-radius: 50%; display: flex; align-items: center; justify-content: center;
         font-weight: 500; color: {text_color}; font-size: {size // 2.5}px;">
        {text}
    </div>
    """


def file_card(filename, size=None, type=None, icon=None):
    """
    Generate HTML for a file card with enhanced styling.
    
    Args:
        filename: File name
        size: Optional file size string
        type: Optional file type
        icon: Optional file icon
        
    Returns:
        HTML string
    """
    # Default icon based on file type
    if icon is None:
        if type:
            type_lower = type.lower()
            if "image" in type_lower or any(ext in filename.lower() for ext in [".jpg", ".jpeg", ".png", ".gif", ".svg"]):
                icon = "🖼️"
            elif "pdf" in type_lower or ".pdf" in filename.lower():
                icon = "📄"
            elif "spreadsheet" in type_lower or any(ext in filename.lower() for ext in [".xlsx", ".xls", ".csv"]):
                icon = "📊"
            elif "document" in type_lower or any(ext in filename.lower() for ext in [".doc", ".docx", ".txt", ".rtf"]):
                icon = "📝"
            elif "presentation" in type_lower or any(ext in filename.lower() for ext in [".ppt", ".pptx"]):
                icon = "📊"
            elif "zip" in type_lower or any(ext in filename.lower() for ext in [".zip", ".rar", ".7z"]):
                icon = "🗜️"
            elif "audio" in type_lower or any(ext in filename.lower() for ext in [".mp3", ".wav", ".ogg"]):
                icon = "🔊"
            elif "video" in type_lower or any(ext in filename.lower() for ext in [".mp4", ".mov", ".avi"]):
                icon = "🎬"
            else:
                icon = "📁"
        else:
            icon = "📁"
    
    # Format size if available
    size_html = f'<div style="color: {COLORS["text_secondary"]}; font-size: 0.8rem;">{size}</div>' if size else ""
    
    # Format type if available
    type_html = f'<div style="color: {COLORS["text_secondary"]}; font-size: 0.8rem;">{type}</div>' if type else ""
    
    return f"""
    <div style="display: flex; align-items: center; background-color: {COLORS["panel"]};
         border: 1px solid {COLORS["border"]}; border-radius: {RADIUS["md"]};
         padding: 10px 15px; margin: {SPACING["sm"]} 0;
         transition: all {ANIMATIONS["fast"]} ease;">
        <div style="font-size: 2rem; margin-right: 15px;">{icon}</div>
        <div style="flex-grow: 1;">
            <div style="font-weight: 500; color: {COLORS["text"]};">{filename}</div>
            <div style="display: flex; gap: 10px;">
                {size_html}
                {type_html}
            </div>
        </div>
    </div>
    """


def comparison_table(headers, rows, highlight_column=None):
    """
    Generate HTML for a comparison table with enhanced styling.
    
    Args:
        headers: List of header strings
        rows: List of row data lists
        highlight_column: Optional index of column to highlight
        
    Returns:
        HTML string
    """
    headers_html = ""
    for i, header in enumerate(headers):
        highlight = highlight_column is not None and i == highlight_column
        header_bg = COLORS["primary"] if highlight else COLORS["panel"]
        header_color = "white" if highlight else COLORS["text"]
        
        headers_html += f"""
        <th style="text-align: left; padding: 12px 15px; background-color: {header_bg};
                 color: {header_color}; font-weight: 600; border-bottom: 1px solid {COLORS["border"]};">
            {header}
        </th>
        """
    
    rows_html = ""
    for i, row in enumerate(rows):
        row_bg = f"rgba(46, 52, 64, {0.5 if i % 2 == 0 else 0.3})"
        row_html = ""
        
        for j, cell in enumerate(row):
            highlight = highlight_column is not None and j == highlight_column
            cell_bg = f"rgba(79, 139, 249, {0.1 if i % 2 == 0 else 0.05})" if highlight else "transparent"
            cell_html = f"""
            <td style="padding: 10px 15px; color: {COLORS["text"]}; background-color: {cell_bg};
                      border-bottom: 1px solid {COLORS["border"]};">
                {cell}
            </td>
            """
            row_html += cell_html
            
        rows_html += f"""
        <tr style="background-color: {row_bg}; transition: all {ANIMATIONS["fast"]} ease;">
            {row_html}
        </tr>
        """
    
    return f"""
    <div style="overflow-x: auto; margin: {SPACING["md"]} 0; 
         border-radius: {RADIUS["md"]}; border: 1px solid {COLORS["border"]};">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
            <thead>
                <tr>{headers_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """