# 🧠 Learning Lab AI: Framework Assessment Workbench

> "AI is a tool for decision-making. It's also a product of decisions."

## 🔍 What is this?

The Framework Assessment Workbench is an experimental laboratory for exploring how AI can transform unstructured documents into structured insights. It demonstrates advanced document intelligence techniques focused on **framework-guided assessment** - evaluating content against structured criteria you define.

Unlike traditional document analysis tools, this workbench is designed to experiment with different assessment strategies and measure their effectiveness. It's a platform for exploring the question: "What's the most effective way to extract and evaluate structured insights from unstructured text?"

<p align="center">
  <img src="docs/images/screenLab1.png" alt="Learning Lab AI Interface" width="80%"/>
</p>

## 💡 Core Design Philosophy

This workbench embodies a specific philosophy about effective AI system design:

### 1. Decision Enhancement, Not Just Automation

AI systems create sustainable value when they enhance human decision-making capabilities rather than simply automating existing processes. The workbench demonstrates this by:

- Focusing on augmenting analytical capabilities rather than replacing human judgment
- Creating multi-resolution information layers that match how people actually make decisions
- Preserving domain expertise by making assessment frameworks explicit and modifiable

### 2. Design for Evolution, Not Static Deployment

Effective AI systems must be designed from the start to evolve continuously as models, data, and requirements change:

- The multi-agent architecture allows components to be independently upgraded
- Processing strategies adapt dynamically to different document types and frameworks
- The experimental interface encourages comparing different approaches to find optimal strategies

### 3. Collaborative Development Across Disciplines

The workbench demonstrates how AI implementation requires bridging technical, business, and domain expertise:

- Framework definitions translate business objectives into technical assessment criteria
- The assessment interface makes technical processes transparent to non-technical users
- Results visualization focuses on business outcomes rather than technical metrics

### 4. Business Outcomes, Not Technical Metrics

The system begins with clearly defined business outcomes that drive technical decisions:

- Assessment metrics directly connect to business criteria rather than model performance
- The interface emphasizes practical insights rather than technical sophistication
- Confidence metrics and evidence tracing help users evaluate the reliability of results

<p align="center">
  <img src="docs/images/logicLearningLabAI.png" alt="Learning Lab AI" width="80%"/>
</p>

## ⚙️ Technical Architecture: Multi-Resolution AI

The workbench implements a "multi-resolution" approach to AI system design - matching different levels of AI complexity to specific tasks within the assessment pipeline:

### Resolution Level 1: Document Processing

Base-level statistical and rule-based techniques for document parsing, tokenization, and chunking that handle the fundamental document structure without requiring advanced models.

### Resolution Level 2: Targeted Extraction

Standard-resolution, task-specific information extraction that identifies relevant passages and extracts specific data points using focused models.

### Resolution Level 3: Contextual Evaluation

High-resolution models that understand context, perform nuanced evaluation against framework criteria, and generate human-readable assessments with proper reasoning.

### Resolution Level 4: Strategic Orchestration

Ultra-resolution meta-planning that determines the optimal assessment strategy based on document characteristics, framework complexity, and assessment goals.

This multi-resolution approach allows the system to:
- Allocate computational resources efficiently
- Apply appropriate levels of AI sophistication to different subtasks
- Balance performance against cost and latency requirements
- Evolve component capabilities independently as technology advances

## 🔬 Technical Implementation

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

## 🔬 Experimentation Capabilities

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

## 🔑 Guiding Principles for AI System Design

The Framework Assessment Workbench embodies several key principles that can be applied to any AI system design:

### 1. Match AI Resolution to Purpose

Not every task requires the most sophisticated AI approach. The workbench demonstrates how different "resolutions" of AI capability can be combined effectively, using simpler techniques where appropriate and more advanced models where complexity demands it.

### 2. Balance Technical Sophistication with Practical Value

The workbench focuses on delivering practical insights rather than pursuing technical sophistication for its own sake, demonstrating that effective AI isn't about having the most advanced models but about creating systems that enhance real-world decision-making.

### 3. Design for Continuous Evolution

The modular architecture and experimental approach reflect the understanding that AI systems must evolve continuously as technology, data, and requirements change, rather than being treated as static implementations.

### 4. Prioritize Decision Enhancement

By focusing on framework-guided assessment, the workbench demonstrates how AI can enhance human decision-making capabilities by providing structured insights that would be impractical to generate manually.

### 5. Create Multi-Resolution Information Access

The assessment results provide information at multiple levels of detail—from summary ratings to detailed evidence—matching how people naturally process information when making decisions.

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Acknowledgements

This project draws inspiration from the field of Decision Intelligence and the idea that AI systems should enhance human decision-making rather than replace it. The approach emphasizes precision in articulating assessment criteria and thoughtfulness in evaluating AI-generated insights.

---

*The Framework Assessment Workbench is an educational tool designed to explore advanced document intelligence techniques and foster thoughtful interaction with AI systems.*