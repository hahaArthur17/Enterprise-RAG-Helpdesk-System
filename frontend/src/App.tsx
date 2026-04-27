import { useState } from 'react';
// FIX: Use 'import type' for TypeScript interfaces to prevent Vite/esbuild runtime errors
import type { Message } from './types/chat';
import './App.css';

function App() {
  // Initialize state with a greeting message
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: 'Hello! I am your Enterprise Helpdesk Assistant. How can I help you today?' }
  ]);
  const [input, setInput] = useState('');

  // Handle the logic for sending a message
  const handleSend = () => {
    // Prevent empty submissions
    if (!input.trim()) return;

    // 1. Append the user's message to the chat
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput(''); // Clear the input field

    // 2. Mock AI response (To be replaced with real API call in Day 5)
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'This is a mocked AI response. We will connect this to the real .NET API later.',
      };
      setMessages((prev) => [...prev, aiMessage]);
    }, 1000);
  };

  // Allow sending message by pressing the 'Enter' key
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

      {/* Chat message history area */}
      <div className="message-list">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-wrapper ${msg.role}`}>
            <div className={`message-bubble ${msg.role}`}>
              {msg.content}
            </div>
          </div>
        ))}
      </div>

      {/* Input area */}
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Type your question here..."
          className="chat-input"
        />
        <button onClick={handleSend} className="send-button">
          Send
        </button>
      </div>
    </div>
  );
}

export default App;