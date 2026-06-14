import React, { useState, useRef, useEffect } from 'react';

export default function ChatPanel({ messages, onSend, isTyping }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e);
    }
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const suggestions = [
    'What is your status?',
    'Show me the tools',
    'How is the memory?',
    'Tell me about the agents',
    'Run a health check',
    'Show the git status',
    'Scan for security issues',
    'What workflows are available?',
  ];

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-title">
          <span className="chat-icon">💬</span>
          <span>COMMAND INTERFACE</span>
        </div>
        <div className="chat-info">
          <span className="chat-count">{messages.length} messages</span>
          <span className="chat-ws-status">WebSocket {isTyping ? 'Thinking...' : 'Ready'}</span>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-welcome">
            <div className="welcome-orb">FRIDAY</div>
            <div className="welcome-text">Good evening, sir. All systems operational. How may I assist you tonight?</div>
            <div className="welcome-suggestions">
              {suggestions.map((s, i) => (
                <button key={i} className="suggestion-btn" onClick={() => onSend(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <div className="msg-avatar">
              {msg.role === 'user' ? '👤' : '🤖'}
            </div>
            <div className="msg-content">
              <div className="msg-header">
                <span className="msg-role">{msg.role === 'user' ? 'YOU' : 'FRIDAY'}</span>
                <span className="msg-time">{formatTime(msg.time)}</span>
              </div>
              <div className="msg-text">{msg.text}</div>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="chat-msg assistant typing">
            <div className="msg-avatar">🤖</div>
            <div className="msg-content">
              <div className="msg-header">
                <span className="msg-role">FRIDAY</span>
              </div>
              <div className="msg-text">
                <span className="msg-dots">
                  <span>.</span><span>.</span><span>.</span>
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a command or ask anything..."
          className="chat-textarea"
        />
        <button type="submit" className="chat-send" disabled={!input.trim()}>
          <span>▶</span>
        </button>
      </form>
    </div>
  );
}
