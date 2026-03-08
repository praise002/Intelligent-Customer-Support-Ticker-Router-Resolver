"""
LangGraph Workflow for Ticket Processing 
State machine for intelligent ticket routing with LangChain-compatible components
"""

from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
import time


class TicketState(TypedDict):
    """State for ticket processing workflow"""
    ticket: Dict
    retrieved_docs: List[Dict]
    llm_response: str
    llm_confidence: float
    confidence_signals: Dict
    action: str
    reasoning: str
    processing_time: float
    error: str
    
class TicketWorkflow:
    def __init__(
        self,
        vector_store_manager,
        llm_generator,
        confidence_calculator
    ):
        """
        Initialize workflow with all required components
        
        Args:
            vector_store_manager: VectorStoreManager instance (LangChain Chroma)
            llm_generator: LLMGenerator instance (NVIDIA/Groq)
            confidence_calculator: ConfidenceCalculator instance
        """
        self.vs_manager = vector_store_manager
        self.llm_gen = llm_generator
        self.conf_calc = confidence_calculator
        
        # Pass embedding function to confidence calculator
        # This enables semantic similarity calculation
        if hasattr(self.vs_manager, 'embeddings'):
            self.conf_calc.embedding_function = self.vs_manager.embeddings
            print("✅ Embedding function linked to confidence calculator")
        else:
            print("⚠️ No embedding function found in vector store manager")
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        workflow = StateGraph(TicketState)
        
        # Add nodes (processing steps)
        workflow.add_node("retrieve", self.retrieve_context)
        workflow.add_node("generate", self.generate_response)
        workflow.add_node("calculate_confidence", self.calculate_confidence)
        workflow.add_node("apply_overrides", self.apply_safety_overrides)
        
        # Define edges (workflow flow)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", "calculate_confidence")
        workflow.add_edge("calculate_confidence", "apply_overrides")
        workflow.add_edge("apply_overrides", END)
        
        return workflow.compile()
    
    def retrieve_context(self, state: TicketState) -> TicketState:
        """
        Node 1: Retrieve relevant documents from vector store
        Uses LangChain's similarity_search under the hood
        """
        ticket = state['ticket']
        query = f"{ticket.get('subject', '')} {ticket.get('description', '')}"
        
        print(f"[Retrieve] Searching for: {ticket.get('subject', 'Unknown')[:50]}...")
        
        try:
            # Use vector store manager's search (handles LangChain internally)
            retrieved_docs = self.vs_manager.search(query, top_k=5)
            state['retrieved_docs'] = retrieved_docs
            
            avg_score = sum(d['relevance_score'] for d in retrieved_docs) / len(retrieved_docs) if retrieved_docs else 0
            print(f"[Retrieve] Found {len(retrieved_docs)} docs (avg relevance: {avg_score:.2f})")
            
        except Exception as e:
            state['error'] = f"Retrieval error: {str(e)}"
            state['retrieved_docs'] = []
            print(f"[Retrieve] ❌ Error: {str(e)}")
        
        return state
    
    def generate_response(self, state: TicketState) -> TicketState:
        """
        Node 2: Generate LLM response using retrieved context
        Works with both NVIDIA and Groq LLMs
        """
        print("[Generate] Creating response with LLM...")
        
        try:
            result = self.llm_gen.generate_response(
                state['ticket'],
                state['retrieved_docs']
            )
            
            state['llm_response'] = result['response']
            state['llm_confidence'] = result['llm_confidence']
            
            print(f"[Generate] ✅ Response generated")
            print(f"[Generate]    LLM self-confidence: {result['llm_confidence']:.2f}")
        
        except Exception as e:
            state['error'] = f"Generation error: {str(e)}"
            state['llm_response'] = "Error generating response. Please escalate to human support."
            state['llm_confidence'] = 0.0
            print(f"[Generate] ❌ Error: {str(e)}")
        
        return state
    
    def calculate_confidence(self, state: TicketState) -> TicketState:
        """
        Node 3: Calculate multi-signal confidence score
        Uses LangChain embeddings for semantic similarity if available
        """
        print("[Confidence] Calculating multi-signal confidence...")
        
        try:
            result = self.conf_calc.calculate_confidence(
                response=state['llm_response'],
                retrieved_docs=state['retrieved_docs'],
                llm_output={'confidence': state['llm_confidence']}
            )
            
            state['confidence_signals'] = result['signals']
            state['action'] = result['action']
            state['reasoning'] = result['reasoning']
            
            signals = result['signals']
            print(f"[Confidence] Signals breakdown:")
            print(f"              Retrieval Quality:    {signals['retrieval_quality']:.3f} (40% weight)")
            print(f"              Semantic Similarity:  {signals['semantic_similarity']:.3f} (40% weight)")
            print(f"              LLM Confidence:       {signals['llm_confidence']:.3f} (20% weight)")
            print(f"              ────────────────────────────────")
            print(f"              Final Confidence:     {signals['final_confidence']:.3f}")
            print(f"[Confidence] Decision: {result['action'].upper()}")
        
        except Exception as e:
            state['error'] = f"Confidence calculation error: {str(e)}"
            state['action'] = 'escalate'
            state['reasoning'] = 'Error in confidence calculation - escalating for safety'
            state['confidence_signals'] = {
                'retrieval_quality': 0.0,
                'semantic_similarity': 0.0,
                'llm_confidence': 0.0,
                'final_confidence': 0.0
            }
            print(f"[Confidence] ❌ Error: {str(e)}")
        
        return state
    
    def apply_safety_overrides(self, state: TicketState) -> TicketState:
        """
        Node 4: Apply safety rules that can override confidence scores
        Ensures critical tickets are never auto-resolved
        """
        print("[Safety] Applying safety overrides...")
        
        try:
            confidence_result = {
                'signals': state['confidence_signals'],
                'action': state['action'],
                'reasoning': state['reasoning']
            }
            
            # Apply overrides
            overridden = self.conf_calc.apply_safety_overrides(
                state['ticket'],
                confidence_result
            )
            
            # Update state if action changed
            if overridden['action'] != state['action']:
                print(f"[Safety] 🚨 Override triggered!")
                print(f"[Safety]    {state['action']} → {overridden['action']}")
                print(f"[Safety]    Reason: {overridden['reasoning']}")
                
                state['action'] = overridden['action']
                state['reasoning'] = overridden['reasoning']
                state['confidence_signals'] = overridden['signals']
            else:
                print(f"[Safety] ✅ No overrides needed")
        
        except Exception as e:
            state['error'] = f"Safety override error: {str(e)}"
            print(f"[Safety] ❌ Error: {str(e)}")
        
        return state
    
    def process_ticket(self, ticket: Dict) -> Dict:
        """
        Process a single ticket through the complete workflow
        
        Args:
            ticket: Ticket dict with subject, description, priority, etc.
        
        Returns:
            Final state dict with all processing results
        """
        
        start_time = time.time()
        
        # Initialize state
        initial_state = {
            'ticket': ticket,
            'retrieved_docs': [],
            'llm_response': '',
            'llm_confidence': 0.0,
            'confidence_signals': {},
            'action': '',
            'reasoning': '',
            'processing_time': 0.0,
            'error': ''
        }
        
        # Run workflow
        print(f"\n{'='*70}")
        print(f"🎫 Processing Ticket: {ticket.get('ticket_id', 'Unknown')}")
        print(f"{'='*70}")
        print(f"Subject: {ticket.get('subject', 'No subject')}")
        print(f"Priority: {ticket.get('priority', 'medium')}")
        print(f"{'='*70}")
        
        final_state = self.workflow.invoke(initial_state)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        final_state['processing_time'] = processing_time
        
        # Print summary
        print(f"\n{'─'*70}")
        print(f"✅ PROCESSING COMPLETE")
        print(f"{'─'*70}")
        print(f"Time:       {processing_time:.2f}s")
        print(f"Action:     {final_state['action'].upper()}")
        print(f"Confidence: {final_state['confidence_signals'].get('final_confidence', 0):.2%}")
        print(f"Reasoning:  {final_state['reasoning']}")
        
        if final_state.get('error'):
            print(f"⚠️ Errors:  {final_state['error']}")
        
        print(f"{'='*70}\n")
        
        return final_state
    
    def process_batch(self, tickets: List[Dict]) -> Dict:
        """
        Process multiple tickets and return summary statistics
        
        Args:
            tickets: List of ticket dicts
        
        Returns:
            Dict with results list and summary statistics
        """
        
        results = []
        
        print(f"\n🔄 Starting batch processing of {len(tickets)} tickets...\n")
        
        for i, ticket in enumerate(tickets, 1):
            print(f"[Batch {i}/{len(tickets)}]")
            result = self.process_ticket(ticket)
            results.append(result)
        
        # Calculate summary statistics
        summary = {
            'total_tickets': len(tickets),
            'auto_resolved': sum(1 for r in results if r['action'] == 'auto_resolve'),
            'human_review': sum(1 for r in results if r['action'] == 'human_review'),
            'escalated': sum(1 for r in results if r['action'] == 'escalate'),
            'avg_processing_time': sum(r['processing_time'] for r in results) / len(results) if results else 0,
            'avg_confidence': sum(r['confidence_signals'].get('final_confidence', 0) for r in results) / len(results) if results else 0,
            'errors': sum(1 for r in results if r.get('error'))
        }
        
        # Print batch summary
        print(f"\n{'='*70}")
        print(f"📊 BATCH PROCESSING SUMMARY")
        print(f"{'='*70}")
        print(f"Total Tickets:        {summary['total_tickets']}")
        print(f"  ✅ Auto-Resolved:   {summary['auto_resolved']} ({summary['auto_resolved']/summary['total_tickets']*100:.1f}%)")
        print(f"  ⚠️  Human Review:    {summary['human_review']} ({summary['human_review']/summary['total_tickets']*100:.1f}%)")
        print(f"  🚨 Escalated:       {summary['escalated']} ({summary['escalated']/summary['total_tickets']*100:.1f}%)")
        print(f"Average Confidence:   {summary['avg_confidence']:.2%}")
        print(f"Average Time:         {summary['avg_processing_time']:.2f}s")
        if summary['errors'] > 0:
            print(f"⚠️ Errors:            {summary['errors']}")
        print(f"{'='*70}\n")
        
        return {
            'results': results,
            'summary': summary
        }

if __name__ == "__main__":
    print("LangGraph workflow module loaded successfully")
    print("✅ Ready for LangChain-compatible vector stores and embeddings")