"""
Multi-Signal Confidence Calculator (LangChain-Compatible Version)
Combines retrieval quality, semantic similarity, and LLM confidence
Works with both NVIDIA and SentenceTransformer embeddings via LangChain
"""

from typing import List, Dict
import numpy as np


class ConfidenceCalculator:
    def __init__(self, embedding_function=None):
        """
        Initialize confidence calculator
        
        Args:
            embedding_function: LangChain embedding function (optional)
                               Can be NVIDIAEmbeddings or SentenceTransformerEmbeddings
        """
        self.embedding_function = embedding_function
        
        # Confidence thresholds
        self.HIGH_THRESHOLD = 0.85
        self.MEDIUM_THRESHOLD = 0.60
        
    def calculate_retrieval_quality(self, retrieved_docs: List[Dict]) -> float:
        """
        Signal 1: How good are the retrieved documents?
        Average of relevance scores from vector search
        """
        if not retrieved_docs:
            return 0.0
        
        scores = [doc['relevance_score'] for doc in retrieved_docs]
        avg_score = np.mean(scores)
        
        # Normalize to 0-1 range
        return min(1.0, max(0.0, avg_score))
    
    def calculate_semantic_similarity(
        self,
        response: str,
        retrieved_docs: List[Dict]
    ) -> float:
        """
        Signal 2: Does the response match the retrieved documents?
        Measures if LLM stayed grounded in the provided context
        """
        if not retrieved_docs or not response:
            return 0.0
        
        try:
            # Combine all retrieved content
            context = " ".join([doc['content'] for doc in retrieved_docs])
            
            if self.embedding_function:
                # Use LangChain embedding function (works with NVIDIA or SentenceTransformer)
                response_embedding = self.embedding_function.embed_query(response)
                context_embedding = self.embedding_function.embed_query(context)
                
                # Calculate cosine similarity manually
                similarity = self._cosine_similarity(response_embedding, context_embedding)
            else:
                # Fallback: Simple token overlap if no embeddings available
                print("⚠️ No embedding function provided, using token overlap as fallback")
                similarity = self._token_overlap_similarity(response, context)
            
            # Normalize to 0-1 (cosine similarity is already -1 to 1)
            return (similarity + 1) / 2 if similarity <= 1 else similarity
            
        except Exception as e:
            print(f"⚠️ Error calculating semantic similarity: {e}")
            # Fallback to moderate confidence
            return 0.5
        
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        
        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0.0
        
        return dot_product / (norm_vec1 * norm_vec2)
    
    def _token_overlap_similarity(self, text1: str, text2: str) -> float:
        """
        Fallback similarity measure using token overlap
        Used when embedding function is not available
        """
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def extract_llm_confidence(self, llm_output: Dict) -> float:
        """
        Signal 3: LLM's self-assessed confidence
        Parse confidence from LLM response
        """
        # If LLM provides structured output with confidence
        if isinstance(llm_output, dict) and 'confidence' in llm_output:
            confidence = float(llm_output['confidence'])
            # Ensure it's in valid range
            return min(1.0, max(0.0, confidence))
        
        # If LLM output is a number
        if isinstance(llm_output, (int, float)):
            return min(1.0, max(0.0, float(llm_output)))
        
        # Default moderate confidence if unclear
        return 0.7
    
    def calculate_confidence(
        self,
        response: str,
        retrieved_docs: List[Dict],
        llm_output: Dict = None
    ) -> Dict:
        """
        Calculate final confidence score using all signals
        Returns confidence signals and routing decision
        
        Args:
            response: LLM-generated response text
            retrieved_docs: Documents retrieved from vector store
            llm_output: LLM output containing confidence (optional)
        
        Returns:
            Dict with signals, action, and reasoning
        """
        
        # Calculate individual signals
        retrieval_quality = self.calculate_retrieval_quality(retrieved_docs)
        semantic_similarity = self.calculate_semantic_similarity(response, retrieved_docs)
        llm_confidence = self.extract_llm_confidence(llm_output or {})
        
        # Weighted combination (as specified: 0.4, 0.4, 0.2)
        final_confidence = (
            0.4 * retrieval_quality +
            0.4 * semantic_similarity +
            0.2 * llm_confidence
        )
        
        # Determine action based on confidence thresholds
        if final_confidence >= self.HIGH_THRESHOLD:
            action = "auto_resolve"
            reasoning = f"High confidence ({final_confidence:.2f}) - auto-resolving ticket with provided solution"
        elif final_confidence >= self.MEDIUM_THRESHOLD:
            action = "human_review"
            reasoning = f"Medium confidence ({final_confidence:.2f}) - draft response created, flagging for human review"
        else:
            action = "escalate"
            reasoning = f"Low confidence ({final_confidence:.2f}) - escalating to senior support for manual handling"
        
        return {
            'signals': {
                'retrieval_quality': retrieval_quality,
                'semantic_similarity': semantic_similarity,
                'llm_confidence': llm_confidence,
                'final_confidence': final_confidence
            },
            'action': action,
            'reasoning': reasoning
        }
        
    def detect_critical_keywords(self, ticket_text: str) -> bool:
        """
        Additional safety check: detect critical keywords that should always escalate
        """
        critical_keywords = [
            # Legal/compliance
            'urgent', 'legal', 'lawsuit', 'attorney', 'lawyer', 'sue', 'suing',
            'compliance', 'regulation', 'regulatory',
            
            # Security/fraud
            'fraud', 'breach', 'security incident', 'data loss', 'hack', 'hacked',
            'stolen', 'unauthorized access', 'compromised',
            
            # Executive/media
            'ceo', 'executive', 'board', 'press', 'media', 'journalist',
            'reporter', 'news',
            
            # Critical severity
            'data deletion', 'lost data', 'deleted data', 'catastrophic',
            'emergency', 'critical outage', 'system down'
        ]
        
        text_lower = ticket_text.lower()
        
        detected_keywords = []
        for keyword in critical_keywords:
            if keyword in text_lower:
                detected_keywords.append(keyword)
        
        if detected_keywords:
            print(f"🚨 Critical keywords detected: {', '.join(detected_keywords)}")
            return True
        
        return False
    
    def apply_safety_overrides(
        self,
        ticket: Dict,
        confidence_result: Dict
    ) -> Dict:
        """
        Apply safety rules that override confidence scores
        Ensures critical tickets are never auto-resolved
        
        Args:
            ticket: Ticket data with subject, description, priority
            confidence_result: Initial confidence calculation result
        
        Returns:
            Modified confidence result with safety overrides applied
        """
        ticket_text = f"{ticket.get('subject', '')} {ticket.get('description', '')}"
        
        # Override 1: Critical keywords ALWAYS escalate
        if self.detect_critical_keywords(ticket_text):
            confidence_result['action'] = 'escalate'
            confidence_result['reasoning'] = "🚨 Critical keywords detected (legal/security/executive) - automatic escalation to senior support"
            confidence_result['signals']['final_confidence'] = 0.0
            return confidence_result
        
        # Override 2: Critical priority requires at minimum human review
        if ticket.get('priority') == 'critical':
            if confidence_result['action'] == 'auto_resolve':
                confidence_result['action'] = 'human_review'
                confidence_result['reasoning'] = "⚠️ Critical priority ticket - requires human verification before resolution"
                print("⚠️ Override: Critical priority requires human review")
                
        # Override 3: Very low retrieval quality = escalate
        # (Means we don't have good docs to answer this question)
        if confidence_result['signals']['retrieval_quality'] < 0.3:
            if confidence_result['action'] != 'escalate':
                confidence_result['action'] = 'escalate'
                confidence_result['reasoning'] = "📚 Low retrieval quality - insufficient documentation to answer confidently"
                print("⚠️ Override: Low retrieval quality triggers escalation")
        
        # Override 4: High priority with low-medium confidence = human review minimum
        if ticket.get('priority') == 'high':
            if confidence_result['signals']['final_confidence'] < 0.75:
                if confidence_result['action'] == 'auto_resolve':
                    confidence_result['action'] = 'human_review'
                    confidence_result['reasoning'] = "⚠️ High priority with moderate confidence - requiring human verification"
        
        return confidence_result
    
if __name__ == "__main__":
    # Test the confidence calculator without embeddings (fallback mode)
    calculator = ConfidenceCalculator()
    
    # Mock data
    mock_docs = [
        {
            'content': 'API keys must start with sk_test or sk_live. Regenerate keys in the dashboard under Developers > API keys.',
            'relevance_score': 0.92
        },
        {
            'content': 'Make sure there are no extra spaces in your API key. The key format is important.',
            'relevance_score': 0.88
        }
    ]
    
    mock_response = "To fix your API key issue, regenerate it in the Stripe dashboard under Developers > API keys. Make sure it starts with sk_test for test mode and has no extra spaces."
    
    mock_llm_output = {'confidence': 0.85}
    
    result = calculator.calculate_confidence(
        response=mock_response,
        retrieved_docs=mock_docs,
        llm_output=mock_llm_output
    )
    
    print("=" * 60)
    print("Confidence Calculation Test (No Embeddings - Fallback Mode)")
    print("=" * 60)
    print(f"Retrieval Quality:    {result['signals']['retrieval_quality']:.3f}")
    print(f"Semantic Similarity:  {result['signals']['semantic_similarity']:.3f}")
    print(f"LLM Confidence:       {result['signals']['llm_confidence']:.3f}")
    print(f"Final Confidence:     {result['signals']['final_confidence']:.3f}")
    print(f"Action:               {result['action']}")
    print(f"Reasoning:            {result['reasoning']}")
    print("=" * 60)
    
    # Test safety overrides
    critical_ticket = {
        'subject': 'URGENT: Customer claims data loss, legal team involved',
        'description': 'Enterprise client says their data was deleted. Their legal department has been contacted.',
        'priority': 'critical'
    }
    
    print("\n" + "=" * 60)
    print("Testing Safety Overrides with Critical Ticket")
    print("=" * 60)
    
    # Start with high confidence
    initial_result = {
        'signals': {
            'retrieval_quality': 0.9,
            'semantic_similarity': 0.9,
            'llm_confidence': 0.9,
            'final_confidence': 0.9
        },
        'action': 'auto_resolve',
        'reasoning': 'High confidence'
    }
    
    overridden_result = calculator.apply_safety_overrides(critical_ticket, initial_result)
    
    print(f"Original Action:      auto_resolve")
    print(f"Overridden Action:    {overridden_result['action']}")
    print(f"Reasoning:            {overridden_result['reasoning']}")
    print("=" * 60)
