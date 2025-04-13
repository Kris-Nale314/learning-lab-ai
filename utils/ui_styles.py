"""
UI Styles for Framework Assessment Workbench

Centralized styles for consistent UI appearance across the application.
Optimized for dark theme with professional styling.
"""

import streamlit as st

# Color palette (dark theme optimized)
COLORS = {
    "primary": "#4F8BF9",
    "secondary": "#FF8C00",
    "success": "#00CC96",
    "warning": "#FFBB28",
    "danger": "#FF6B6B",
    "light": "#2E3440",     # Darker background for cards in dark mode
    "dark": "#1E1E1E",      # Even darker for contrast
    "background": "#121212", # Page background in dark mode
    "text": "#E0E0E0",      # Light text for dark backgrounds
    "muted": "#A0A0A0",     # Muted text for dark backgrounds
    "highlight": "#FFD866",
    "card_bg": "#1F2937",   # Dark card background
    "border": "#3B4252",    # Subtle border color
}

# Rating colors - for visualizing scores
RATING_COLORS = {
    1: "#FF6B6B",  # Red
    2: "#FF9E72",  # Orange
    3: "#FFD166",  # Yellow
    4: "#8AC926",  # Light green
    5: "#00CC96",  # Green
}

# Typography styles
def apply_styles():
    """Apply CSS styles to the current page."""
    st.markdown(
        """
        <style>
        /* Dark theme optimized styling */
        .css-1adrfps, .css-z5fcl4 {
            padding-top: 2rem;
        }
        
        /* Main text and background colors - dark theme */
        .reportview-container {
            background-color: #121212;
            color: #E0E0E0;
        }
        
        /* Headers */
        .main h1 {
            font-size: 2.5rem;
            font-weight: 700;
            color: #4F8BF9;
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #2E3440;
        }
        
        .main h2 {
            font-size: 1.8rem;
            font-weight: 600;
            color: #E0E0E0;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            padding-bottom: 0.3rem;
        }
        
        .main h3 {
            font-size: 1.4rem;
            font-weight: 600;
            color: #D8DEE9;
            margin-top: 1.2rem;
            margin-bottom: 0.8rem;
        }
        
        .main h4 {
            font-size: 1.2rem;
            font-weight: 600;
            color: #C0C0C0;
            margin-top: 1rem;
            margin-bottom: 0.6rem;
        }
        
        /* Cards */
        .css-card {
            border-radius: 10px;
            padding: 20px;
            background-color: #1F2937;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            margin-bottom: 20px;
            border: 1px solid #3B4252;
        }
        
        .css-card-header {
            font-weight: 600;
            font-size: 1.1rem;
            margin-bottom: 10px;
            color: #4F8BF9;
        }
        
        /* Score pills */
        .score-pill {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.9rem;
            color: white;
            text-align: center;
            margin: 2px 4px;
        }
        
        .score-1 {
            background-color: #FF6B6B;
        }
        
        .score-2 {
            background-color: #FF9E72;
        }
        
        .score-3 {
            background-color: #FFD166;
            color: #333;
        }
        
        .score-4 {
            background-color: #8AC926;
        }
        
        .score-5 {
            background-color: #00CC96;
        }
        
        /* Badges */
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 0 4px;
        }
        
        .badge-primary {
            background-color: #4F8BF9;
            color: white;
        }
        
        .badge-secondary {
            background-color: #FF8C00;
            color: white;
        }
        
        .badge-success {
            background-color: #00CC96;
            color: white;
        }
        
        .badge-warning {
            background-color: #FFBB28;
            color: #333;
        }
        
        .badge-danger {
            background-color: #FF6B6B;
            color: white;
        }
        
        /* Cards with ratings - dark theme optimized */
        .rating-card {
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            background-color: #1F2937;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
            border-left: 5px solid #3B4252;
            transition: all 0.2s ease;
        }
        
        .rating-card:hover {
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.4);
            transform: translateY(-2px);
        }
        
        .rating-1 {
            border-left-color: #FF6B6B;
        }
        
        .rating-2 {
            border-left-color: #FF9E72;
        }
        
        .rating-3 {
            border-left-color: #FFD166;
        }
        
        .rating-4 {
            border-left-color: #8AC926;
        }
        
        .rating-5 {
            border-left-color: #00CC96;
        }
        
        /* Progress bar */
        .stProgress > div > div > div > div {
            background-color: #4F8BF9;
        }
        
        /* Metrics - dark theme optimized */
        .metric-container {
            background-color: #1F2937;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            margin-bottom: 15px;
            border-left: 4px solid #4F8BF9;
            display: flex;
            flex-direction: column;
            border: 1px solid #3B4252;
        }
        
        .metric-label {
            font-size: 0.85rem;
            color: #A0A0A0;
            margin-bottom: 5px;
        }
        
        .metric-value {
            font-size: 1.6rem;
            font-weight: 600;
            color: #E0E0E0;
        }
        
        /* Insights box - dark theme optimized */
        .insight-box {
            background-color: #2E3440;
            border-left: 4px solid #4F8BF9;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
        }
        
        .insight-title {
            font-weight: 600;
            margin-bottom: 8px;
            color: #E0E0E0;
        }
        
        /* Table styling - dark theme optimized */
        .styled-table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.3);
        }
        
        .styled-table thead tr {
            background-color: #4F8BF9;
            color: #ffffff;
            text-align: left;
            font-weight: bold;
        }
        
        .styled-table th,
        .styled-table td {
            padding: 12px 15px;
        }
        
        .styled-table tbody tr {
            border-bottom: thin solid #3B4252;
        }
        
        .styled-table tbody tr:nth-of-type(even) {
            background-color: #2E3440;
        }
        
        .styled-table tbody tr:last-of-type {
            border-bottom: 2px solid #4F8BF9;
        }
        
        /* Info box - dark theme optimized */
        .info-box {
            background-color: #2E3440;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #3B4252;
        }
        
        .info-box-title {
            color: #88C0D0;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        /* Warning box - dark theme optimized */
        .warning-box {
            background-color: #3B4252;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #4C566A;
        }
        
        .warning-box-title {
            color: #EBCB8B;
            font-weight: 600;
            margin-bottom: 5px;
        }

        /* Expandable section - dark theme optimized */
        .expandable {
            border: 1px solid #3B4252;
            border-radius: 8px;
            margin-bottom: 10px;
            overflow: hidden;
            background-color: #1F2937;
        }
        
        .expandable-header {
            padding: 12px 15px;
            background-color: #2E3440;
            cursor: pointer;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #E0E0E0;
        }
        
        .expandable-content {
            padding: 15px;
            border-top: 1px solid #3B4252;
            display: none;
            background-color: #1F2937;
        }
        
        .expandable.active .expandable-content {
            display: block;
        }
        
        /* Evidence item - dark theme optimized */
        .evidence-item {
            border-left: 3px solid #4F8BF9;
            padding: 10px 15px;
            margin-bottom: 10px;
            background-color: #2E3440;
            border-radius: 0 4px 4px 0;
        }
        
        .evidence-text {
            font-style: italic;
            color: #D8DEE9;
            margin-bottom: 5px;
        }
        
        .evidence-relevance {
            font-size: 0.85rem;
            color: #A0A0A0;
        }

        /* Animation for progress - dark theme optimized */
        @keyframes pulse {
            0% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(79, 139, 249, 0.7);
            }
            
            70% {
                transform: scale(1);
                box-shadow: 0 0 0 10px rgba(79, 139, 249, 0);
            }
            
            100% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(79, 139, 249, 0);
            }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }

        /* Streamlit native component overrides for dark theme */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > div,
        .stTextArea > div > div > textarea {
            background-color: #2E3440;
            color: #E0E0E0;
            border: 1px solid #3B4252;
        }

        .stTextInput > div > div > input:focus,
        .stSelectbox > div > div > div:focus,
        .stTextArea > div > div > textarea:focus {
            border: 1px solid #4F8BF9;
        }

        /* Make expanders match the dark theme */
        .streamlit-expanderHeader {
            background-color: #1F2937;
            color: #E0E0E0;
            border-radius: 4px;
        }

        .streamlit-expanderContent {
            background-color: #1F2937;
            color: #E0E0E0;
            border: 1px solid #3B4252;
            border-top: none;
            border-radius: 0 0 4px 4px;
        }

        /* Fix any remaining white backgrounds in stDataFrame */
        .stDataFrame {
            background-color: #1F2937;
        }

        .stDataFrame th {
            background-color: #2E3440;
            color: #E0E0E0;
        }

        .stDataFrame td {
            background-color: #1F2937;
            color: #E0E0E0;
        }

        /* Enhanced tabs styling for dark theme */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            background-color: #1F2937;
        }

        .stTabs [data-baseweb="tab"] {
            background-color: #2E3440;
            color: #A0A0A0;
            border-radius: 4px 4px 0 0;
            border: 1px solid #3B4252;
            border-bottom: none;
            padding: 8px 16px;
        }

        .stTabs [aria-selected="true"] {
            background-color: #3B4252;
            color: #E0E0E0;
        }

        .stTabs [data-baseweb="tab-panel"] {
            background-color: #1F2937;
            border: 1px solid #3B4252;
            border-radius: 0 4px 4px 4px;
            padding: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def rating_color(rating):
    """Get the color for a rating value."""
    if rating is None:
        return COLORS["muted"]
    
    try:
        rating_int = int(round(float(rating)))
        return RATING_COLORS.get(rating_int, COLORS["muted"])
    except (ValueError, TypeError):
        return COLORS["muted"]


def score_badge(score, text=None):
    """Generate HTML for a score badge."""
    if score is None:
        score_val = "N/A"
        score_class = ""
    else:
        try:
            score_val = f"{float(score):.1f}"
            score_int = int(round(float(score)))
            score_class = f" score-{score_int}"
        except (ValueError, TypeError):
            score_val = str(score)
            score_class = ""
    
    display_text = text if text else score_val
    return f'<span class="score-pill{score_class}">{display_text}</span>'


def badge(text, style="primary"):
    """Generate HTML for a badge."""
    return f'<span class="badge badge-{style}">{text}</span>'


def info_box(title, content):
    """Generate HTML for an info box."""
    return f"""
    <div class="info-box">
        <div class="info-box-title">{title}</div>
        <div>{content}</div>
    </div>
    """


def warning_box(title, content):
    """Generate HTML for a warning box."""
    return f"""
    <div class="warning-box">
        <div class="warning-box-title">{title}</div>
        <div>{content}</div>
    </div>
    """


def card(content, header=None, rating=None):
    """Generate HTML for a card with optional header and rating."""
    rating_class = f" rating-{int(round(float(rating)))}" if rating is not None else ""
    header_html = f'<div class="css-card-header">{header}</div>' if header else ""
    
    return f"""
    <div class="rating-card{rating_class}">
        {header_html}
        {content}
    </div>
    """


def metric_card(label, value, description=None):
    """Generate HTML for a metric card."""
    description_html = f'<div>{description}</div>' if description else ""
    return f"""
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {description_html}
    </div>
    """


def insight_box(title, items):
    """Generate HTML for an insight box with bullet points."""
    items_html = ""
    for item in items:
        items_html += f"<li>{item}</li>"
    
    return f"""
    <div class="insight-box">
        <div class="insight-title">{title}</div>
        <ul>
            {items_html}
        </ul>
    </div>
    """


def styled_table(headers, rows):
    """Generate HTML for a styled table."""
    headers_html = ""
    for header in headers:
        headers_html += f"<th>{header}</th>"
    
    rows_html = ""
    for row in rows:
        row_html = ""
        for cell in row:
            row_html += f"<td>{cell}</td>"
        rows_html += f"<tr>{row_html}</tr>"
    
    return f"""
    <table class="styled-table">
        <thead>
            <tr>{headers_html}</tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """


def expandable_section(header, content, expanded=False):
    """Generate HTML for an expandable section."""
    expanded_class = " active" if expanded else ""
    return f"""
    <div class="expandable{expanded_class}">
        <div class="expandable-header">
            {header}
            <span>▼</span>
        </div>
        <div class="expandable-content">
            {content}
        </div>
    </div>
    <script>
        // Add click event to all expandable headers
        const headers = window.parent.document.querySelectorAll('.expandable-header');
        headers.forEach((header) => {{
            header.addEventListener('click', () => {{
                const parent = header.parentElement;
                parent.classList.toggle('active');
                const arrow = header.querySelector('span');
                arrow.textContent = parent.classList.contains('active') ? '▼' : '▶';
            }});
        }});
    </script>
    """


def evidence_item(text, relevance=None, confidence=None):
    """Generate HTML for an evidence item."""
    confidence_html = ""
    if confidence is not None:
        try:
            conf_val = f"{float(confidence):.2f}"
            confidence_html = f" (Confidence: {conf_val})"
        except (ValueError, TypeError):
            pass
    
    relevance_html = ""
    if relevance:
        relevance_html = f'<div class="evidence-relevance">{relevance}{confidence_html}</div>'
    
    return f"""
    <div class="evidence-item">
        <div class="evidence-text">{text}</div>
        {relevance_html}
    </div>
    """


def rating_badge(rating, max_rating=5):
    """Generate HTML for a rating badge with appropriate color."""
    if rating is None:
        return '<span class="score-pill">N/A</span>'
    
    try:
        rating_val = float(rating)
        rating_int = min(max(int(round(rating_val)), 1), max_rating)
        return f'<span class="score-pill score-{rating_int}">{rating_val:.1f}</span>'
    except (ValueError, TypeError):
        return f'<span class="score-pill">{rating}</span>'


def get_css_class_for_rating(rating):
    """Get the CSS class for a rating value."""
    if rating is None:
        return ""
    
    try:
        rating_int = int(round(float(rating)))
        return f"rating-{rating_int}"
    except (ValueError, TypeError):
        return ""