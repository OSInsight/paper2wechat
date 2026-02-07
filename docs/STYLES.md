# Academic Styles Reference

This document explains the four core academic styles and when to use them.

## 1. Academic-Science

**Focus**: Scientific rigor, precise explanations, fundamental discoveries

**Tone**: Thoughtful, precise, methodology-focused

**Best For**:
- AI theory and algorithms
- Fundamental science papers
- Mathematical proofs and derivations
- Research with novel insights into how things work

**Example Opening**:
> In this groundbreaking research, scientists have discovered... By employing rigorous methodology... The implications are profound...

**Characteristics**:
- ✅ Emphasize the scientific method
- ✅ Explain technical concepts precisely
- ✅ Highlight collaborative/collaborative aspects
- ✅ Focus on "why this is important scientifically"

---

## 2. Academic-Tech

**Focus**: Technical insights, practical implications, developer perspective

**Tone**: Practical, insightful, implementation-focused

**Best For**:
- Tools, frameworks, libraries
- Engineering papers
- Software architecture papers
- Papers with clear coding/implementation takeaways

**Example Opening**:
> Here's a clever technical innovation that could change how we build... The implementation is elegant... You can start using it like this...

**Characteristics**:
- ✅ Explain with code examples
- ✅ Focus on "how to use this"
- ✅ Highlight performance improvements
- ✅ Connect to real development workflows

---

## 3. Academic-Trend

**Focus**: Emerging fields, innovation, future implications

**Tone**: Visionary, forward-looking, exciting

**Best For**:
- Breakthrough discoveries in new domains
- Papers entering emerging fields (e.g., early LLM papers)
- Paradigm-shifting research
- Papers about the future of a field

**Example Opening**:
> This is what the future looks like. Researchers have just opened a new frontier... What comes next is truly remarkable... This could reshape the entire field...

**Characteristics**:
- ✅ Emphasize paradigm shifts
- ✅ Discuss broader implications
- ✅ Connect to industry trends
- ✅ Focus on "this changes everything"

---

## 4. Academic-Applied

**Focus**: Real-world applications, practical value, ROI

**Tone**: Business-oriented, practical, impact-focused

**Best For**:
- Applied research with clear use cases
- Industry applications papers
- Papers about solving specific problems
- Research with commercial potential

**Example Opening**:
> This research solves a real problem affecting millions... Here's how it works in practice... Companies can implement this to... The ROI is significant...

**Characteristics**:
- ✅ Lead with the problem solved
- ✅ Show real-world examples
- ✅ Discuss economic/business impact
- ✅ Provide implementation guidance

---

## Choosing a Style

| Paper Type          | Best Style       | Why                               |
| ------------------- | ---------------- | --------------------------------- |
| New algorithm       | academic-science | Focus on rigor and discovery      |
| Framework paper     | academic-tech    | Focus on usage and implementation |
| AI breakthrough     | academic-trend   | Emphasize paradigm shift          |
| Medical application | academic-applied | Real-world health impact          |
| Climate science     | academic-science | Methodological rigor important    |
| DevOps tool         | academic-tech    | Developer perspective essential   |
| Foundation model    | academic-trend   | Emerging field significance       |
| Drug discovery      | academic-applied | Patient/business impact           |

---

## Style Adaptation Examples

### Same Paper, Different Styles

**Original (academic language)**:
> "We propose a novel attention mechanism that reduces computational complexity from O(n²) to O(n log n) while maintaining model expressiveness..."

**Academic-Science Style**:
> "We've discovered something new about how attention works. By rethinking the mechanism, we achieved something most thought impossible: maintaining full expressiveness while dramatically reducing computational cost. This required rigorous mathematical analysis of the underlying principles."

**Academic-Tech Style**:
> "Here's a clever optimization that cuts compute from O(n²) to O(n log n). If you're building large language models, this could halve your training time. Here's how to implement it..."

**Academic-Trend Style**:
> "This is a breakthrough moment for AI. We've cracked a problem that was fundamentally limiting model scale. This innovation could be the key that unlocks the next generation of even more capable AI systems."

**Academic-Applied Style**:
> "This saves real money. By reducing compute requirements, organizations can now build advanced models for less than half the cost. For companies running at scale, the financial impact is substantial."

---

## Implementation Notes

- Styles are implemented as system prompts in `prompts/academics-styles.md`
- Each style has its own tone, vocabulary, and structural preferences
- Styles can be combined or customized
- User feedback helps refine styles over time

---

See [CLAUDE.md](../CLAUDE.md) for more context on style design.
