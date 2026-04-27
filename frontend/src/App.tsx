import { useState } from 'react';
import type { Message } from './types/chat';
import './App.css';

function App() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: 'Hello! I am your Enterprise Helpdesk Assistant. How can I help you today?' }
  ]);
  const [input, setInput] = useState('');
  
  // NEW: State to track if we are waiting for an API response
  const [isLoading, setIsLoading] = useState(false);

  // Changed to an async function to handle network requests
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    // 1. Instantly display user's message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true); // Disable input and show loading indicator

    try {
      // 2. Make the actual HTTP call to the .NET Backend
      // NOTE: Verify that your .NET service is running on port 5263!
      const response = await fetch('http://localhost:5263/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage.content }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      // 3. Parse the JSON response from .NET and display it
      const data = await response.json();
      const aiMessage: Message = {
        id: data.id,
        role: data.role,
        content: data.content, // This content now originates from Python!
      };
      
      setMessages((prev) => [...prev, aiMessage]);

    } catch (error) {
      console.error("Failed to connect to the backend:", error);
      
      // Fallback message if network fails
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: '[System Error] Failed to connect to the server. Is .NET running?',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false); // Re-enable input
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h2>Enterprise RAG Helpdesk</h2>
      </header>

      <div className="message-list">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-wrapper ${msg.role}`}>
            <div className={`message-bubble ${msg.role}`}>
              {msg.content}
            </div>
          </div>
        ))}
        
        {/* NEW: Simple loading indicator */}
        {isLoading && (
          <div className="message-wrapper assistant">
            <div className="message-bubble assistant">
              <em>Thinking...</em>
            </div>
          </div>
        )}
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Type your question here..."
          className="chat-input"
          disabled={isLoading} // Prevent typing while waiting
        />
        <button 
          onClick={handleSend} 
          className="send-button" 
          disabled={isLoading} // Prevent multiple clicks
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default App;