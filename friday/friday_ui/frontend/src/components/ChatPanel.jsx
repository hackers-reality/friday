import React, { useState, useRef, useEffect } from 'react';

export default function ChatPanel({ messages, onSend, isTyping }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSend(input.trim());
      setInput('');
    }
  };

  const suggestions = [
    'Status report',
    'What tools do you have?',
    'Memory status',
    'Hello',
  ];

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-icon">&#9673;</span>
        <span>COMMAND INTERFACE</span>
        <span className="chat-status">{isTyping ? 'PROCESSING...' : 'READY'}</span>
      </div>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <span className="msg-role">{msg.role === 'user' ? 'YOU' : 'FRIDAY'}</span>
            <span className="msg-text">{msg.text}</span>
          </div>
        ))}
        {isTyping && (
          <div className="chat-msg assistant typing">
            <span className="msg-role">FRIDAY</span>
            <span className="msg-dots"><span>.</span><span>.</span><span>.</span></span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-suggestions">
        {suggestions.map((s, i) => (
          <button key={i} className="suggestion-btn" onClick={() => onSend(s)}>
            {s}
          </button>
        ))}
      </div>
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter command..."
          disabled={isTyping}
        />
        <button type="submit" disabled={isTyping || !input.trim()}>
          SEND
        </button>
      </form>
    </div>
  );
}
