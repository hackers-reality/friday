import React, { useState, useRef, useCallback, useEffect } from 'react';

export default function VoiceControl({ onVoice }) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [supported, setSupported] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [wakeMode, setWakeMode] = useState(false);
  const [lastActivity, setLastActivity] = useState(null);
  const recognitionRef = useRef(null);
  const autoRestartRef = useRef(true);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSupported(true);
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event) => {
        let finalText = '';
        let interimText = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const t = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalText += t;
          } else {
            interimText += t;
          }
        }
        setTranscript(interimText || finalText);
        setLastActivity(Date.now());

        if (finalText) {
          const lower = finalText.toLowerCase().trim();
          if (wakeMode) {
            if (lower.startsWith('friday') || lower.startsWith('hey friday') || lower.startsWith('ok friday')) {
              const cmd = lower.replace(/^(ok |hey )?friday[\s,]*/i, '').trim();
              if (cmd) onVoice(cmd);
            }
          } else {
            onVoice(finalText);
          }
        }
      };

      recognition.onerror = (event) => {
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          console.error('Speech error:', event.error);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        if (autoRestartRef.current && voiceEnabled) {
          setTimeout(() => {
            try {
              recognition.start();
              setIsListening(true);
            } catch (e) {}
          }, 100);
        }
      };

      recognitionRef.current = recognition;

      setTimeout(() => {
        try {
          recognition.start();
          setIsListening(true);
          autoRestartRef.current = true;
        } catch (e) {}
      }, 500);
    }
  }, [onVoice, wakeMode, voiceEnabled]);

  const toggleListening = useCallback(() => {
    if (!supported || !recognitionRef.current) return;

    if (isListening) {
      autoRestartRef.current = false;
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      autoRestartRef.current = true;
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (e) {}
    }
  }, [isListening, supported]);

  const toggleVoice = useCallback(() => {
    setVoiceEnabled(prev => {
      const next = !prev;
      if (!next && recognitionRef.current) {
        autoRestartRef.current = false;
        recognitionRef.current.stop();
        setIsListening(false);
      } else if (next && recognitionRef.current) {
        autoRestartRef.current = true;
        try {
          recognitionRef.current.start();
          setIsListening(true);
        } catch (e) {}
      }
      return next;
    });
  }, []);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.ctrlKey && e.key === 'm') {
        e.preventDefault();
        toggleListening();
      }
      if (e.ctrlKey && e.key === 'v') {
        e.preventDefault();
        toggleVoice();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [toggleListening, toggleVoice]);

  const statusText = isListening ? 'LISTENING' : isSpeaking ? 'SPEAKING' : 'STANDBY';

  return (
    <div className="voice-control">
      <button
        className={`voice-btn ${isListening ? 'listening' : ''} ${voiceEnabled ? 'enabled' : 'disabled'}`}
        onClick={toggleListening}
        title={voiceEnabled ? 'Always listening (Ctrl+M to toggle)' : 'Voice disabled (Ctrl+V to enable)'}
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
        {isListening && <span className="voice-ring" />}
      </button>

      <div className="voice-status">
        <span className={`voice-status-dot ${isListening ? 'active' : 'standby'}`} />
        <span className="voice-status-text">{statusText}</span>
      </div>

      {(isListening || transcript) && (
        <div className="voice-transcript">
          <span className="voice-text">{transcript || '...'}</span>
        </div>
      )}

      <button
        className={`voice-toggle ${voiceEnabled ? 'active' : ''}`}
        onClick={toggleVoice}
        title={voiceEnabled ? 'Voice ON (Ctrl+V)' : 'Voice OFF (Ctrl+V)'}
      >
        {voiceEnabled ? '🔊' : '🔇'}
      </button>

      <button
        className={`wake-btn ${wakeMode ? 'active' : ''}`}
        onClick={() => setWakeMode(p => !p)}
        title={wakeMode ? 'Wake word mode ON' : 'Direct mode ON'}
      >
        {wakeMode ? '🗣️' : '🎯'}
      </button>
    </div>
  );
}
