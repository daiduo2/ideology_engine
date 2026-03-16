import json
import os
from typing import Dict, Any, List, Optional
from anthropic import Anthropic


class LLMClient:
    """Wrapper around Anthropic SDK for assessment engine needs."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-6"):
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Make a structured call to Claude and parse JSON response."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        content = message.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        return json.loads(content)

    def parse_response(
        self,
        protocol_summary: str,
        state_summary: str,
        user_answer: str,
    ) -> Dict[str, Any]:
        """Parse user response into structured observations."""
        from .prompts.parse_response import SYSTEM_PROMPT

        user_message = f"""
Protocol: {protocol_summary}

Current State: {state_summary}

User Answer: {user_answer}
"""
        return self._call_llm(SYSTEM_PROMPT, user_message)

    def extract_evidence(
        self,
        protocol: Dict[str, Any],
        observations: List[Dict[str, Any]],
        current_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract evidence from observations."""
        from .prompts.extract_evidence import SYSTEM_PROMPT

        user_message = f"""
Protocol: {json.dumps(protocol, ensure_ascii=False)}

Observations: {json.dumps(observations, ensure_ascii=False)}

Current State: {json.dumps(current_state, ensure_ascii=False)}
"""
        return self._call_llm(SYSTEM_PROMPT, user_message)

    def generate_question(
        self,
        target: Dict[str, Any],
        strategy: str,
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Generate next question based on target."""
        from .prompts.generate_question import SYSTEM_PROMPT

        user_message = f"""
Target: {json.dumps(target, ensure_ascii=False)}

Strategy: {strategy}

Conversation History: {json.dumps(conversation_history, ensure_ascii=False)}
"""
        return self._call_llm(SYSTEM_PROMPT, user_message, temperature=0.5)

    def generate_report(
        self,
        protocol: Dict[str, Any],
        state: Dict[str, Any],
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate final report."""
        from .prompts.generate_report import SYSTEM_PROMPT

        user_message = f"""
Protocol: {json.dumps(protocol, ensure_ascii=False)}

Final State: {json.dumps(state, ensure_ascii=False)}

Evidence: {json.dumps(evidence, ensure_ascii=False)}
"""
        return self._call_llm(SYSTEM_PROMPT, user_message, temperature=0.4)
