"""
LLM Response Generator
Uses NVIDIA API with Groq as fallback
"""

import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try NVIDIA first, fallback to Groq
try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
    USE_NVIDIA = True
except ImportError:
    USE_NVIDIA = False
    print("NVIDIA AI Endpoints not available, will use Groq")

try:
    from groq import Groq
    USE_GROQ = True
except ImportError:
    USE_GROQ = False
    print("Groq not available")


class LLMGenerator:
    def __init__(self):
        self.nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        # Initialize LLM
        if USE_NVIDIA and self.nvidia_api_key:
            print("Using NVIDIA API")
            self.llm = ChatNVIDIA(
                model="meta/llama-3.1-70b-instruct",
                api_key=self.nvidia_api_key,
                temperature=0.2,
                max_tokens=1024
            )
            self.provider = "nvidia"
        elif USE_GROQ and self.groq_api_key:
            print("Using Groq API")
            self.client = Groq(api_key=self.groq_api_key)
            self.provider = "groq"
        else:
            raise ValueError("No LLM API credentials found. Set NVIDIA_API_KEY or GROQ_API_KEY")
    
    def create_support_prompt(
        self,
        ticket: Dict,
        retrieved_docs: List[Dict]
    ) -> str:
        """Create prompt for support ticket resolution"""
        
        # Format retrieved context
        context = ""
        for i, doc in enumerate(retrieved_docs, 1):
            source = doc['metadata'].get('title', 'Unknown')
            context += f"\n[Doc {i} - {source}]\n{doc['content']}\n"
        
        prompt = f"""You are a Stripe API support specialist. Your job is to help resolve customer support tickets accurately and helpfully.

CONTEXT FROM DOCUMENTATION:
{context}

CUSTOMER TICKET:
Subject: {ticket.get('subject', 'No subject')}

Description:
{ticket.get('description', 'No description')}

INSTRUCTIONS:
1. Analyze the ticket and the provided documentation
2. Provide a clear, helpful response that solves the customer's problem
3. Use ONLY information from the provided context - do not make up information
4. If the context doesn't contain enough information, say so clearly
5. Provide step-by-step instructions when applicable
6. Be professional and empathetic

After your response, rate your confidence in this solution on a scale of 0.0 to 1.0, where:
- 0.9-1.0: Very confident, exact match in documentation
- 0.7-0.89: Confident, good information available
- 0.5-0.69: Moderate confidence, some uncertainty
- Below 0.5: Low confidence, may need human review

Format your response as:
RESPONSE:
[Your helpful response here]

CONFIDENCE: [0.0 to 1.0]
EXPLANATION: [Brief explanation of your confidence rating]
"""
        return prompt
    
    def generate_response(
        self,
        ticket: Dict,
        retrieved_docs: List[Dict]
    ) -> Dict:
        """Generate response using LLM"""
        
        prompt = self.create_support_prompt(ticket, retrieved_docs)
        
        try:
            if self.provider == "nvidia":
                response = self.llm.invoke(prompt)
                response_text = response.content
            
            elif self.provider == "groq":
                response = self.client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=1024
                )
                response_text = response.choices[0].message.content
            
            # Parse response to extract confidence
            parsed = self._parse_response(response_text)
            
            return {
                'response': parsed['response'],
                'llm_confidence': parsed['confidence'],
                'explanation': parsed['explanation'],
                'raw_output': response_text
            }
        
        except Exception as e:
            print(f"Error generating response: {e}")
            return {
                'response': "I apologize, but I'm having trouble processing this ticket. Please escalate to a human agent.",
                'llm_confidence': 0.0,
                'explanation': f"Error: {str(e)}",
                'raw_output': ""
            }
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse LLM response to extract components"""
        
        # Default values
        response = response_text
        confidence = 0.7  # Default moderate confidence
        explanation = "No explanation provided"
        
        # Try to parse structured output
        if "RESPONSE:" in response_text:
            parts = response_text.split("CONFIDENCE:")
            response = parts[0].replace("RESPONSE:", "").strip()
            
            if len(parts) > 1:
                conf_part = parts[1].split("EXPLANATION:")
                try:
                    confidence = float(conf_part[0].strip())
                except:
                    pass
                
                if len(conf_part) > 1:
                    explanation = conf_part[1].strip()
        
        return {
            'response': response,
            'confidence': confidence,
            'explanation': explanation
        }


if __name__ == "__main__":
    # Test the generator
    generator = LLMGenerator()
    
    test_ticket = {
        'subject': 'API Key Not Working',
        'description': 'I regenerated my API key but now getting authentication errors.'
    }
    
    test_docs = [
        {
            'content': 'API keys must be regenerated in the Stripe Dashboard. After regeneration, update your application with the new key.',
            'metadata': {'title': 'API Key Management'}
        }
    ]
    
    result = generator.generate_response(test_ticket, test_docs)
    
    print("Generated Response:")
    print(result['response'])
    print(f"\nLLM Confidence: {result['llm_confidence']}")
    print(f"Explanation: {result['explanation']}")