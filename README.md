# 🧠 Learning Lab AI: Framework Assessment Workbench

> "AI is a tool for decision-making. It's also a product of decisions."

## 🔍 What is this?

The Framework Assessment Workbench is an experimental laboratory for transforming unstructured documents into structured insights using advanced document intelligence techniques. It evaluates content against structured criteria you define, going beyond simple keyword search to provide comprehensive framework-guided assessment.

<p align="center">
  <img src="docs/images/screenLab1.png" alt="Learning Lab AI Interface" width="80%"/>
</p>

## 💡 Strategic Design Philosophy

This project demonstrates how effective AI systems should be built to deliver sustainable value:

### 🎯 Decision Enhancement, Not Just Automation
AI systems create the most value when enhancing human decision-making rather than simply automating processes. This workbench:
- Augments analytical capabilities while preserving human judgment
- Creates multi-resolution information layers matching how people make decisions
- Makes assessment frameworks explicit and modifiable to preserve domain expertise

### 🌱 Design for Evolution, Not Static Deployment
Effective AI systems must evolve continuously as technology and requirements change:
- Components can be independently upgraded through modular architecture 
- Processing strategies adapt dynamically to different document types
- Experimentation interface allows comparing approaches to optimize results

## 🏗️ Technical Architecture: Strategic Multi-Agent Orchestration

<p align="center">
  <img src="docs/images/logicLearningLabAI.png" alt="Learning Lab AI Architecture" width="80%"/>
</p>

### Key Components

#### 🤖 Meta Planner Agent
- Analyzes document structure, content, and framework complexity
- Designs custom processing strategy including:
  - Optimal chunking method (fixed, semantic, paragraph-based)
  - Extractor configuration and specialization
  - Evidence categorization criteria
  - Processing sequence and dependencies

#### 🧠 Shared Context Protocol
- Central collaboration mechanism for all agents
- Evidence traceability from conclusions back to source
- Token usage optimization across processing steps
- Transparent agent collaboration and decision records

#### 🔍 Specialized Extractors
- Configurable extraction techniques (direct, semantic, inference-based)
- Evidence categorization with relevance and sentiment analysis
- Confidence scoring for extracted evidence
- Parallel processing with specialized focus areas

#### ⚖️ Enhanced Evaluator
- Direct vs. inferred assessment distinction
- Evidence-based confidence calibration
- Rating justification with traceability
- Dimension and cross-criteria insights

## 🛠️ Technical Innovations

### Evidence Categorization Matrix

The system implements sophisticated evidence categorization beyond binary relevance:

| Relevance Level | Description | Assessment Impact |
|-----------------|-------------|-------------------|
| **Direct** | Explicitly addresses the criterion | Strongest weight in assessment |
| **Indirect** | Implicitly relates to the criterion | Moderate weight in assessment |
| **Contextual** | Provides important context | Supplementary information |
| **Implied** | Suggests without stating | Weak inference support |

Combined with sentiment analysis, this creates rich evidence classification for confident assessments.

### Dynamic Chunking Strategy

Different documents require different chunking approaches:

```python
def _design_chunking_strategy(self, document_size: int, document_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Design optimal chunking strategy based on document characteristics."""
    # Default configuration
    strategy = {
        "method": "fixed_size",
        "size": 8000,
        "overlap": 200,
        "rationale": "Standard fixed-size chunking for general documents"
    }
    
    # Adjust based on document size
    if document_size < 15000:
        # Small document - use a single large chunk
        strategy["method"] = "fixed_size"
        strategy["size"] = document_size
        strategy["overlap"] = 0
        strategy["rationale"] = "Document is small enough to process as a single chunk"
    elif document_size > 100000:
        # Very large document - use semantic chunking
        strategy["method"] = "semantic"
        strategy["rationale"] = "Large document requires semantic chunking to maintain context"
    else:
        # Check document structure
        structure = document_analysis.get("content_structure", "").lower()
        
        if "dialogue" in structure or "transcript" in structure:
            # Dialogue or transcript - use paragraph-based chunking
            strategy["method"] = "paragraph"
            strategy["rationale"] = "Dialogue structure benefits from paragraph-based chunking"
            
    return strategy
```

### Direct vs. Inferred Assessment Protocol

One of the most significant innovations is explicit handling of assessment types:

```python
async def _evaluate_criterion(self, dimension_id: str, criterion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Evaluate a criterion with clear distinction between direct and inferred assessments."""
    # Get consolidated evidence
    consolidated_evidence = self._get_consolidated_evidence(dimension_id, criterion_id)
    
    # Check if direct assessment is justified
    if consolidated_evidence and consolidated_evidence.get("direct_assessment_justified") == "YES":
        # Create direct assessment
        assessment = await self._create_evidence_based_assessment(
            dimension_id, criterion, consolidated_evidence
        )
        assessment["assessment_type"] = "direct"
        
    # If inference is allowed but direct not justified
    elif self.infer_missing:
        # Create inferred assessment
        assessment = await self._create_inferred_assessment(
            dimension_id, criterion, consolidated_evidence
        )
        if assessment:
            assessment["assessment_type"] = "inferred"
            
    # No assessment possible
    else:
        assessment = {
            "assessment_type": "insufficient_evidence",
            "rating": None
        }
        
    return assessment
```

This distinction is critical for transparency about assessment reliability.

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

The workbench allows you to experiment with different approaches:

- **Extraction Strategies**: Compare direct vs. semantic extraction techniques
- **Chunking Approaches**: Test impact of chunk size and overlap on assessment quality
- **Evaluation Methods**: Compare direct vs. inference-based assessment
- **Token Optimization**: Explore efficiency tradeoffs in processing strategies

## 💼 Real-World Applications

### Organizational Assessment
- Evaluate documents against maturity models or compliance frameworks
- Identify gaps and strengths in organizational documentation
- Automate consistency checks in complex regulations

### Meeting Analysis
- Analyze transcripts against agenda frameworks
- Verify that all required topics were addressed
- Identify missing discussion points for follow-up

### Content Evaluation
- Evaluate research papers against methodological standards
- Check educational content against curriculum requirements
- Validate marketing materials against brand guidelines

## 🧪 Why I Build Experimental AI Systems

Building systems like this workbench provides insights that can't be gained from theory alone:

1. **Emergent Challenges**: Complex issues only become visible during implementation
2. **Architecture Testing**: Understanding real-world performance of different patterns
3. **Integration Learning**: Discovering how components interact in unexpected ways
4. **Practical Limits**: Finding boundaries of what current LLM technology can achieve
5. **User Experience**: Learning how humans interact with AI-generated assessments

> "The difference between theory and practice is greater in practice than in theory."

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*The Framework Assessment Workbench is an experimental tool designed to explore advanced document intelligence techniques and demonstrate strategic AI system design principles.*