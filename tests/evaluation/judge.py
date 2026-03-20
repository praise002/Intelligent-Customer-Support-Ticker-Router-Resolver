

import json
from typing import Dict, List

from decouple import config
from langchain_groq import ChatGroq
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_openai import ChatOpenAI

from tests.evaluation.judge_prompts import (
    JUDGE_EVALUATION_PROMPT,
    JUDGE_SYSTEM_PROMPT,
    format_retrieved_docs,
)


class LLMJudge:
    """LLM-as-a-Judge evaluator for response quality"""
    
    def __init__(self):
        """Initialize judge with available LLM provider"""
        self.llm = self._get_llm()
    
    def _get_llm(self):
        """Get LLM provider (same logic as main system)"""
        
        # Try NVIDIA first
        nvidia_key = config("NVIDIA_API_KEY", default=None)
        if nvidia_key:
            return ChatNVIDIA(
                model="meta/llama-3.1-405b-instruct",
                api_key=nvidia_key,
                temperature=0.0  # Deterministic for evaluation
            )
        
        # Try Groq second
        groq_key = config("GROQ_API_KEY", default=None)
        if groq_key:
            return ChatGroq(
                model="llama-3.3-70b-versatile",
                api_key=groq_key,
                temperature=0.0
            )
        
        # Fall back to OpenAI
        openai_key = config("OPENAI_API_KEY", default=None)
        if openai_key:
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=openai_key,
                temperature=0.0
            )
        
        raise ValueError("No LLM API key found for judge")
    
    def evaluate_response(
        self,
        ticket_subject: str,
        ticket_description: str,
        retrieved_docs: List,
        llm_response: str
    ) -> Dict:
        """
        Evaluate AI response quality using LLM judge.
        
        Returns:
            {
                "tone_empathy": 0.85,
                "response_quality": 0.80,
                "faithfulness": 0.90,
                "groundedness": 0.95,
                "overall": 0.875,
                "reason": "Response is helpful and grounded",
                "pass": True
            }
        """
        
        # Format documents for prompt
        docs_text = format_retrieved_docs(retrieved_docs)
        
        # Build evaluation prompt
        evaluation_prompt = JUDGE_EVALUATION_PROMPT.format(
            subject=ticket_subject,
            description=ticket_description,
            retrieved_docs=docs_text,
            llm_response=llm_response
        )
        
        # Get judge evaluation
        messages = [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": evaluation_prompt}
        ]
        
        try:
            response = self.llm.invoke(messages)
            result_text = response.content.strip()
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            evaluation = json.loads(result_text)
            
            # Validate structure
            required_keys = [
                "tone_empathy", "response_quality",
                "faithfulness", "groundedness",
                "overall", "reason", "pass"
            ]
            
            for key in required_keys:
                if key not in evaluation:
                    raise ValueError(f"Missing required key: {key}")
            
            return evaluation
            
        except Exception as e:
            print(f"⚠️ Judge evaluation failed: {e}")
            # Return default failing scores
            return {
                "tone_empathy": 0.0,
                "response_quality": 0.0,
                "faithfulness": 0.0,
                "groundedness": 0.0,
                "overall": 0.0,
                "reason": f"Evaluation failed: {str(e)}",
                "pass": False
            }
    
    def evaluate_batch(self, tickets: List[Dict]) -> List[Dict]:
        """
        Evaluate multiple tickets.
        
        Args:
            tickets: [
                {
                    "ticket_id": "TKT-001",
                    "subject": "...",
                    "description": "...",
                    "retrieved_docs": [...],
                    "llm_response": "..."
                }
            ]
        
        Returns:
            List of evaluation results with ticket_id
        """
        
        results = []
        
        for ticket in tickets:
            evaluation = self.evaluate_response(
                ticket_subject=ticket["subject"],
                ticket_description=ticket["description"],
                retrieved_docs=ticket["retrieved_docs"],
                llm_response=ticket["llm_response"]
            )
            
            evaluation["ticket_id"] = ticket["ticket_id"]
            results.append(evaluation)
        
        return results
    
    def get_aggregate_scores(self, evaluations: List[Dict]) -> Dict:
        """Calculate aggregate statistics across evaluations"""
        
        if not evaluations:
            return {}
        
        total = len(evaluations)
        
        return {
            "total_evaluated": total,
            "avg_tone_empathy": sum(e["tone_empathy"] for e in evaluations) / total,
            "avg_response_quality": sum(e["response_quality"] for e in evaluations) / total,
            "avg_faithfulness": sum(e["faithfulness"] for e in evaluations) / total,
            "avg_groundedness": sum(e["groundedness"] for e in evaluations) / total,
            "avg_overall": sum(e["overall"] for e in evaluations) / total,
            "pass_rate": sum(1 for e in evaluations if e["pass"]) / total,
            "fail_rate": sum(1 for e in evaluations if not e["pass"]) / total
        }        
        
# TODO: judge auto-resolve and maybe human review