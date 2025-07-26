**Agatha: A Multi-Model AI Consensus System**

Inspired by the prescient insights of Minority Report's most gifted precog, Agatha brings together the collective intelligence of today's leading AI models to tackle complex questions. Rather than relying on a single AI's perspective, Agatha orchestrates a sequential pipeline where Google's Gemini grounds the discussion with real-time data, Anthropic's Claude Opus provides deep analytical reasoning, and OpenAI's GPT-4o-mini performs rapid fact-checking and proofreading, before Google's Gemini Pro synthesizes the final consensus. Like its namesake who could see what others missed, this system surfaces both agreement and crucial divergences between models, delivering not just answers but a richer understanding of where AIs align, disagree, and why it matters.

**Processing Pipeline:**
1. **Google Gemini 2.5 Flash** with grounding gets fresh data/facts
2. **Anthropic Claude Opus** receives Flash's response for deep analysis
3. **OpenAI GPT-4o-mini** fact-checks and proofreads both responses
4. **Google Gemini 2.5 Pro** synthesizes all three, identifies consensus and conflicts

**Key Features:**
- Context accumulation (each model sees previous outputs)
- Fact-informed reasoning (grounded data flows through pipeline)
- Built-in verification layer via GPT-4o-mini
- Consensus detection with disagreement flagging
- "Minority report" alerts when models strongly diverge
- Response synthesis highlighting areas of agreement/disagreement
- Confidence scoring from each model

**Technical Stack:**
- Python for API orchestration  
- Simple web UI for queries and results visualization
- JSON response format with model attributions

**MVP Functionality:**
- Submit complex question → sequential processing → verification → final synthesis
- Display individual model responses alongside final answer
- Track model agreement patterns over time
- "Divergence points" tracked at each step