import { useState, useRef, useEffect } from 'react';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5263';

// Define types for messages
type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
};

// Loading dots component for typing indicator
const TypingIndicator = () => (
  <div className="typing-indicator">
    <span></span>
    <span></span>
    <span></span>
  </div>
);

// Login screen component
const LoginScreen = ({ 
  username, 
  password, 
  setUsername, 
  setPassword, 
  handleLogin, 
  loginError 
}: { 
  username: string; 
  password: string; 
  setUsername: (val: string) => void; 
  setPassword: (val: string) => void; 
  handleLogin: (e: React.FormEvent) => void; 
  loginError: string; 
}) => (
  <div className="login-screen">
    <div className="login-card">
      <div className="login-header">
        <h1>Enterprise RAG</h1>
        <p>Secure Knowledge Assistant</p>
      </div>
      <form onSubmit={handleLogin} className="login-form">
        <div className="input-group">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            placeholder="Enter your username"
            required
          />
        </div>
        <div className="input-group">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Enter your password"
            required
          />
        </div>
        {loginError && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {loginError}
          </div>
        )}
        <button type="submit" className="login-button">
          Sign In
        </button>
        <div className="demo-credentials">
          <small>Demo: admin / password</small>
        </div>
      </form>
    </div>
  </div>
);

// Main chat application component
function App() {
  // Authentication state
  const [token, setToken] = useState<string | null>(localStorage.getItem('jwt_token'));
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('password');
  const [loginError, setLoginError] = useState('');

  // Chat and upload state
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    if (token) {
      inputRef.current?.focus();
    }
  }, [token]);

  // Handle login submission
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) throw new Error('Invalid credentials');
      
      const data = await response.json();
      setToken(data.token);
      localStorage.setItem('jwt_token', data.token);
    } catch (error) {
      setLoginError('Login failed. Please check your credentials.');
    }
  };

  // Handle logout
  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem('jwt_token');
    setMessages([]);
  };

  // Handle file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/document/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });

      if (response.status === 401) {
        handleLogout();
        alert('Session expired. Please log in again.');
        return;
      }

      if (!response.ok) throw new Error('Upload failed');
      alert(`✅ ${file.name} uploaded successfully!`);
    } catch (error) {
      alert('❌ Failed to upload document.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Handle sending messages
  const handleSend = async () => {
    if (!inputValue.trim() || !token) return;

    const userMessage: Message = { 
      id: Date.now().toString(), 
      role: 'user', 
      content: inputValue,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: userMessage.content })
      });

      if (response.status === 401) {
        handleLogout();
        alert('Session expired. Please log in again.');
        return;
      }

      const data = await response.json();
      const botMessage: Message = { 
        id: data.id || Date.now().toString(), 
        role: 'assistant', 
        content: data.content,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        id: 'error', 
        role: 'assistant', 
        content: '⚠️ Connection error. Please try again.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Return login screen if not authenticated
  if (!token) {
    return (
      <LoginScreen
        username={username}
        password={password}
        setUsername={setUsername}
        setPassword={setPassword}
        handleLogin={handleLogin}
        loginError={loginError}
      />
    );
  }

  // Main chat interface
  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <h1>Enterprise RAG</h1>
          <span className="status-badge">
            <span className="status-dot"></span>
            Connected
          </span>
        </div>
        
        <div className="header-right">
          <div className="upload-wrapper">
            <input
              type="file"
              accept=".pdf"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="file-input"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="upload-button">
              {isUploading ? (
                <>
                  <span className="upload-spinner"></span>
                  Uploading...
                </>
              ) : (
                <>
                  <span className="upload-icon">📄</span>
                  Upload Document
                </>
              )}
            </label>
          </div>
          
          <button onClick={handleLogout} className="logout-button">
            Logout
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="chat-main">
        {/* Messages area */}
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-icon">💬</div>
              <h2>Welcome to Enterprise RAG</h2>
              <p>Ask questions about your documents or get help with company policies</p>
            </div>
          ) : (
            <div className="messages-list">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`message-item ${msg.role}`}
                >
                  <div className="message-avatar">
                    {msg.role === 'user' ? '👤' : '🤖'}
                  </div>
                  <div className="message-content-wrapper">
                    <div className={`message-bubble ${msg.role}`}>
                      <div className="message-text">{msg.content}</div>
                      {msg.timestamp && (
                        <div className="message-time">{msg.timestamp}</div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="message-item assistant">
                  <div className="message-avatar">🤖</div>
                  <div className="message-content-wrapper">
                    <div className="message-bubble assistant loading">
                      <TypingIndicator />
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="input-container">
          <div className="input-wrapper">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Type your question here..."
              disabled={isLoading}
              className="chat-input"
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !inputValue.trim()}
              className="send-button"
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </div>
          <div className="input-hint">
            Press Enter to send • Shift+Enter for new line
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
