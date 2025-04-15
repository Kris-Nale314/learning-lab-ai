# 🧠 Learning Lab AI: Framework Assessment Workbench

> "AI is a tool for decision-making. It's also a product of decisions."

## 🔍 What is this?

The Framework Assessment Workbench is an experimental laboratory for exploring how AI can transform unstructured documents into structured insights. It demonstrates advanced document intelligence techniques focused on **framework-guided assessment** - evaluating content against structured criteria you define.

Unlike traditional document analysis tools, this workbench is designed to experiment with different assessment strategies and measure their effectiveness. It's a platform for exploring the question: "What's the most effective way to extract and evaluate structured insights from unstructured text?"

## 💡 Core Beliefs

We believe that AI tools should enhance human decision-making, not replace it. The most powerful applications happen when users can precisely articulate what they're looking for and thoughtfully evaluate AI-generated insights.

The true challenge isn't just building more powerful AI - it's designing systems that help users become more skilled "wishers" who can clearly define what they want and critically evaluate what they receive.

### Decision Intelligence at the Core

The Framework Assessment Workbench embodies the principles of decision intelligence:

1. **Strategic Value Articulation**: Instead of implementing AI for its own sake, we focus on clearly articulating what value we want to extract from documents.

2. **Context-Aware Processing**: Our multi-agent architecture adapts to the specific context of each assessment rather than applying one-size-fits-all approaches.

3. **Thoughtful Interaction**: The system encourages users to carefully define frameworks and critically evaluate results, avoiding the pitfall of uncritically trusting AI outputs.

4. **Precision in Expression**: Our framework-building capabilities help users precisely communicate assessment criteria to AI systems.

## ⚙️ How It Works

The workbench uses a flexible multi-agent architecture powered by LangChain with a novel approach:

1. **Dynamic Assessment Planning**: Rather than using a fixed pipeline, each assessment begins with a Meta Planner that designs a custom processing strategy based on the document and framework

2. **Configurable Agent Deployment**: Agents are configured and deployed according to the strategy, with customized instructions for each assessment

3. **Experimental Measurement**: Token usage, processing time, and quality metrics are tracked to compare different assessment approaches

4. **Interactive Exploration**: Users can review and modify assessment strategies, comparing different approaches to see what works best

<p align="center">
  <img src="docs/images/logicLearningLabAI.png" alt="Learning Lab AI" width="80%"/>
</p>

## 🔬 Technical Approach

The system implements several key innovations:

### Strategy-Driven Processing

Instead of a fixed pipeline, each assessment has a custom strategy that defines:
- Chunking approach (size, overlap, method)
- Extraction targets and techniques
- Evaluation criteria and methods
- Sequencing and dependencies between steps

### Configurable Agent Framework

The system uses configurable agents that adapt to different tasks:
- **Meta Planner**: Designs assessment strategies based on document and framework
- **Extractor**: Configurable information extraction with different techniques
- **Evaluator**: Flexible evaluation of criteria with configurable methods
- **Reporter**: Customizable report generation in different formats

### Shared Context Architecture

All agents collaborate through a shared context that enables:
- Evidence traceability from conclusions back to source text
- Token usage optimization across processing steps
- Transparent agent collaboration and decision records

## 🚀 Getting Started

```bash
# Clone the repository
git clone https://github.com/kris-nale314/learning-lab-ai.git
cd learning-lab-ai

# Install dependencies
pip install -r requirements.txt

# Set up your API key
export OPENAI_API_KEY=your_key_here

# Launch the app
streamlit run app.py
```

## 📁 Project Structure

```
learning-lab-ai/
├── app.py                     # Main Streamlit application
├── requirements.txt           # Dependencies
├── LICENSE                    # License file
├── README.md                  # Project readme
├── core/
│   ├── context.py             # Assessment context with collaboration capabilities
│   ├── execution.py           # Strategy execution engine
│   ├── agents/                # Agent implementations
│   │   ├── base.py            # Base agent class
│   │   ├── meta_planner.py    # Strategy planning agent
│   │   ├── extractor.py       # Configurable extraction agent  
│   │   ├── evaluator.py       # Configurable evaluation agent
│   │   └── reporter.py        # Configurable reporting agent
│   ├── models/                # Data models
│   │   ├── framework.py       # Framework model
│   │   ├── document.py        # Document model
│   │   ├── evidence.py        # Evidence model
│   │   ├── assessment.py      # Assessment result model
│   │   └── strategy.py        # Processing strategy model
│   └── processors/            # Document processing
│       ├── chunker.py         # Multiple chunking strategies
│       ├── strategy_executor.py # Strategy execution engine
│       └── token_optimizer.py # Token usage optimization
├── data/                      # Data directory
│   ├── samples/               # Sample documents
│   ├── frameworks/            # Framework definitions
│   ├── outputs/               # Saved assessment results
│   └── context/               # Stored context objects
├── utils/                     # Utility functions
│   ├── document_utils.py      # Document handling utilities
│   ├── visualization.py       # Visualization helpers
│   ├── ui_components.py       # Streamlit UI components
│   ├── ui_styles.py           # UI styling helpers
│   ├── ui_results.py          # Results display utilities
│   ├── ui_progress.py         # Progress tracking components
│   └── path_utils.py          # File path management
├── docs/                      # Documentation
│   ├── images/                # Architecture diagrams, logos
│   ├── concepts.md            # Concept explanations
│   └── usage.md               # Usage documentation
├── tests/                     # Test suite
└── pages/                     # Streamlit pages
    ├── 01_Assess_Framework.py   # Main assessment page
    ├── 02_Framework_Builder.py  # Framework definition
    ├── 03_Results_Explorer.py   # Results visualization
    └── 04_Experiment_Lab.py     # Experimentation
```

## 🔬 What You Can Explore

The workbench allows you to experiment with different approaches to framework assessment, focusing on the decision intelligence aspects of AI system design:

### From Buzzwords to Business Strategy

- Define frameworks that translate business goals into measurable criteria
- Experiment with different ways to articulate assessment criteria for AI
- Test how variations in framework structure impact assessment quality

### Extraction Strategies
- Compare direct vs. semantic extraction techniques
- Test targeted extraction for specific criteria
- Evaluate the impact of different extraction prompts

### Chunking Approaches
- Test the impact of chunk size and overlap on assessment quality
- Compare fixed-size vs. semantic chunking
- Explore specialized chunking for different content types

### Evaluation Methods
- Compare direct evaluation vs. inference-based assessment
- Test different confidence calibration approaches
- Measure the impact of evidence thresholds on ratings

### Token Optimization
- Explore efficiency tradeoffs in different processing strategies
- Compare batch processing vs. comprehensive analysis
- Measure the relationship between token usage and assessment quality

## 💼 Sample Use Cases

- **Organizational Readiness Assessment**: Evaluate documents against maturity frameworks
- **Meeting Analysis**: Assess if specific topics were adequately addressed
- **Policy Compliance**: Check documents against regulatory requirements
- **Research Quality Evaluation**: Assess papers against methodological standards
- **Project Documentation Review**: Identify risks and gaps in project documentation

## 🔑 Key Principles for AI System Design

The Framework Assessment Workbench embodies several key principles that can be applied to any AI system design:

### 1. Know When to Use AI

Not every problem requires AI. The workbench helps users determine when traditional automation (via explicit rules) is sufficient and when AI approaches are needed for problems too complex to solve with conventional methods.

### 2. Become a Skilled "Wisher"

The success of AI systems depends heavily on how well humans can articulate what they want. Our framework-building capabilities help users develop this skill by providing structure for expressing evaluation criteria.

### 3. Be an "Author of Meaning"

With generative AI systems capable of producing infinite possible outputs, the workbench helps users define what "good" looks like for their specific needs and develop metrics to evaluate success.

### 4. Inject Thoughtfulness

The system encourages critical evaluation of AI outputs by tracking confidence scores, providing evidence traceability, and visualizing assessment metrics, helping users avoid the trap of uncritical trust.

### 5. Prioritize Value Over Technology

The workbench focuses on the business value of insights rather than the technology itself, demonstrating how AI can be applied to previously "impossible" document analysis problems when value is clearly articulated.

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Acknowledgements

This project draws inspiration from the field of Decision Intelligence and the idea that AI systems should enhance human decision-making rather than replace it. The approach emphasizes precision in articulating assessment criteria and thoughtfulness in evaluating AI-generated insights.

---

*The Framework Assessment Workbench is an educational tool designed to explore advanced document intelligence techniques and foster thoughtful interaction with AI systems.*