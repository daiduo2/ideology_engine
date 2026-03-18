"""Base LLM client interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Make a structured call to LLM and parse JSON response."""
        pass

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
        import json
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
        import json
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
        import json
        from .prompts.generate_report import SYSTEM_PROMPT

        user_message = f"""
Protocol: {json.dumps(protocol, ensure_ascii=False)}

Final State: {json.dumps(state, ensure_ascii=False)}

Evidence: {json.dumps(evidence, ensure_ascii=False)}
"""
        return self._call_llm(SYSTEM_PROMPT, user_message, temperature=0.4)

    @staticmethod
    def _extract_json_from_response(content: str) -> str:
        """Extract JSON from markdown code blocks or plain text."""
        import re

        content = content.strip()

        # Try to find JSON in code blocks
        json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        matches = re.findall(json_pattern, content)
        if matches:
            return matches[0].strip()

        # Try to find JSON object/array by matching braces
        # Look for the outermost JSON object
        brace_pattern = r'(\{[\s\S]*\}|\[[\s\S]*\])'
        matches = re.search(brace_pattern, content)
        if matches:
            return matches.group(1).strip()

        # Fallback: strip markdown and return
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    @staticmethod
    def _safe_json_parse(content: str) -> Dict[str, Any]:
        """Safely parse JSON with error recovery.

        Attempts to fix common JSON errors before giving up.
        """
        import json
        import re

        # First try normal parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to fix common errors
        fixed_content = content

        # Fix 1: Remove trailing commas before } or ]
        fixed_content = re.sub(r',\s*}', '}', fixed_content)
        fixed_content = re.sub(r',\s*]', ']', fixed_content)

        # Fix 2: Fix missing commas between array/object elements
        # This is harder - look for } followed by { without comma
        fixed_content = re.sub(r'(\}|\])\s*(\{|\[)', r'\1,\2', fixed_content)

        # Fix 3: Remove control characters
        fixed_content = ''.join(char for char in fixed_content if ord(char) >= 32 or char in '\n\r\t')

        # Try parsing again
        try:
            return json.loads(fixed_content)
        except json.JSONDecodeError as e:
            # If still failing, try to extract just the first valid JSON object
            try:
                # Find first { and matching }
                start = fixed_content.find('{')
                if start != -1:
                    brace_count = 0
                    for i, char in enumerate(fixed_content[start:], start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                return json.loads(fixed_content[start:i+1])
            except:
                pass
            raise e
