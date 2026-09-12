import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bot, X, Send, Paperclip, Sparkles, ChevronDown,
  Minimize2, RotateCcw, Zap, Radio, AlertTriangle,
  Image as ImageIcon, Loader2
} from 'lucide-react';
import { chatWithAssistant, getAssistantHealth, refreshAssistantMode } from '../services/api';
import AssistantMessageBubble from './AssistantMessageBubble';

// ─── localStorage key ────────────────────────────────────────────────────────
const STORAGE_KEY = 'trinetra_ai_chat_history';
const MAX_STORED   = 40; // max messages to persist

// ─── Mode badge config ────────────────────────────────────────────────────────
const MODE_CONFIG = {
  OLLAMA_FULL:        { label: 'VLM Online',    color: 'text-emerald-400', dot: 'bg-emerald-400', pulse: true },
  OLLAMA_TEXT_ONLY:   { label: 'Text AI',       color: 'text-cyan-400',    dot: 'bg-cyan-400',    pulse: true },
  HEURISTIC_FALLBACK: { label: 'Heuristic Mode',color: 'text-amber-400',   dot: 'bg-amber-400',   pulse: false },
  offline:            { label: 'Backend Offline',color:'text-red-400',     dot: 'bg-red-400',     pulse: false },
};

// ─── Suggestion prompts shown on first open ───────────────────────────────────
const STARTER_SUGGESTIONS = [
  'Find military installations near water',
  'Show all indexed satellite tiles',
  'What acquisition dates are in the archive?',
  'Detect changes in the latest tile pair',
];

export default function AIAssistant({ onNavigate, onSearch, onSelectTile, onAgentAction, isOpen: externalIsOpen, onClose: externalOnClose }) {
  const [internalOpen, setInternalOpen] = useState(false);

  // Support both controlled (externalIsOpen) and uncontrolled usage
  const isOpen = externalIsOpen !== undefined ? externalIsOpen : internalOpen;
  const setIsOpen = (val) => {
    setInternalOpen(val);
    if (!val && externalOnClose) externalOnClose();
  };

  const [messages,   setMessages]   = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [inputText,  setInputText]  = useState('');
  const [attachedImage, setAttachedImage] = useState(null); // { file, previewUrl }
  const [isThinking, setIsThinking] = useState(false);
  const [mode,       setMode]       = useState('offline');
  const [modeDesc,   setModeDesc]   = useState('');
  const [sessionId]  = useState(() => `sess_${Date.now()}`);

  const bottomRef   = useRef(null);
  const inputRef    = useRef(null);
  const fileRef     = useRef(null);
  const dragRef     = useRef(null);

  // ── Persist messages to localStorage ───────────────────────────────────────
  useEffect(() => {
    try {
      const toStore = messages.slice(-MAX_STORED);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore));
    } catch { /* quota exceeded — ignore */ }
  }, [messages]);

  // ── Check assistant health on mount ────────────────────────────────────────
  useEffect(() => {
    getAssistantHealth().then(h => {
      setMode(h.mode || 'offline');
      setModeDesc(h.description || '');
    });
  }, []);

  // ── Scroll to bottom on new messages ───────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  // ── Focus input when panel opens ───────────────────────────────────────────
  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 300);
  }, [isOpen]);

  // ── History helper (last 6 turns for context) ──────────────────────────────
  const getHistory = () => messages.slice(-6).map(m => ({
    role:    m.role,
    content: m.content,
  }));

  // ── Send message ────────────────────────────────────────────────────────────
  const handleSend = useCallback(async (overrideText) => {
    const text = (overrideText ?? inputText).trim();
    if (!text && !attachedImage) return;
    if (isThinking) return;

    const userMsg = {
      id:        Date.now(),
      role:      'user',
      content:   text,
      image:     attachedImage?.previewUrl || null,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    const sentImage = attachedImage;
    setAttachedImage(null);
    setIsThinking(true);

    try {
      const resp = await chatWithAssistant(
        text,
        sentImage?.file || null,
        getHistory(),
        sessionId,
      );

      const aiMsg = {
        id:           Date.now() + 1,
        role:         'assistant',
        content:      resp.response || 'No response.',
        action:       resp.action_taken,
        results:      resp.results || {},
        suggestions:  resp.follow_up_suggestions || [],
        mode:         resp.mode_used,
        thinkingSteps:resp.thinking_steps || [],
        timestamp:    new Date().toISOString(),
      };

      setMessages(prev => [...prev, aiMsg]);

      // ── Drive main UI from AI response ──────────────────────────────────
      if (resp.results && onAgentAction) {
        if (resp.action_taken === 'SEARCH_TEXT' || resp.action_taken === 'SEARCH_IMAGE') {
           onAgentAction(resp.action_taken, {
             query: resp.results.query || text,
             tiles: resp.results.tiles || resp.results.results
           });
        } else if (resp.action_taken === 'CHANGE_DETECT') {
           onAgentAction(resp.action_taken, {
             tileId: resp.results.tiles?.[0]?.tile_id || null
           });
        }
      }
      // Update mode from response
      if (resp.mode_used) setMode(resp.mode_used);
    } catch (err) {
      setMessages(prev => [...prev, {
        id:        Date.now() + 1,
        role:      'assistant',
        content:   `⚠️ Error: ${err.message}`,
        action:    'EXPLAIN',
        results:   {},
        suggestions: ['Retry', 'Check backend server'],
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setIsThinking(false);
    }
  }, [inputText, attachedImage, isThinking, sessionId, onNavigate, onSearch, onSelectTile, onAgentAction]);

  // ── Key handler ─────────────────────────────────────────────────────────────
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── Image attach ─────────────────────────────────────────────────────────────
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const previewUrl = URL.createObjectURL(file);
    setAttachedImage({ file, previewUrl });
    e.target.value = '';
  };

  // ── Drag & drop ──────────────────────────────────────────────────────────────
  const handleDrop = (e) => {
    e.preventDefault();
    dragRef.current?.classList.remove('ring-2', 'ring-cyan-400');
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const previewUrl = URL.createObjectURL(file);
    setAttachedImage({ file, previewUrl });
  };
  const handleDragOver = (e) => {
    e.preventDefault();
    dragRef.current?.classList.add('ring-2', 'ring-cyan-400');
  };
  const handleDragLeave = () => {
    dragRef.current?.classList.remove('ring-2', 'ring-cyan-400');
  };

  // ── Clear history ────────────────────────────────────────────────────────────
  const clearHistory = () => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  };

  // ── Refresh Ollama mode ──────────────────────────────────────────────────────
  const handleRefresh = async () => {
    const h = await refreshAssistantMode();
    setMode(h.mode || mode);
    const health = await getAssistantHealth();
    setModeDesc(health.description || '');
  };

  const modeCfg = MODE_CONFIG[mode] || MODE_CONFIG['offline'];

  return (
    <>
      {/* ── Floating Orb Button (collapsed) ──────────────────────────────── */}
      {!isOpen && (
        <button
          id="ai-assistant-orb"
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 group flex items-center gap-2.5 px-4 py-3
                     bg-gradient-to-br from-cyan-500 via-sky-500 to-indigo-600
                     hover:from-cyan-400 hover:via-sky-400 hover:to-indigo-500
                     text-white rounded-2xl shadow-2xl shadow-cyan-500/40
                     hover:shadow-cyan-400/60 hover:scale-[1.06]
                     active:scale-[0.97] transition-all duration-200 cursor-pointer
                     border border-cyan-400/40"
          aria-label="Open TriNetra AI Assistant"
        >
          {/* Pulsing core */}
          <div className="relative flex items-center justify-center w-7 h-7">
            <span className="absolute w-7 h-7 rounded-full bg-cyan-300/30 animate-ping" />
            <Bot className="w-5 h-5 relative z-10" />
          </div>
          <span className="text-sm font-bold tracking-wide pr-0.5">TriNetra AI</span>
          <Sparkles className="w-3.5 h-3.5 text-cyan-200 opacity-80" />
        </button>
      )}

      {/* ── Sliding Right Panel ───────────────────────────────────────────── */}
      <aside
        className={`fixed top-0 right-0 bottom-0 z-50 w-full sm:w-[420px] flex flex-col
                    bg-[#030d1a]/95 backdrop-blur-3xl
                    border-l-2 border-cyan-400/40 shadow-[-20px_0_80px_rgba(0,229,255,0.15)]
                    transform transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
                    ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
        aria-hidden={!isOpen}
      >
        {/* ── Panel Header ────────────────────────────────────────────────── */}
        <div className="flex-none p-4 border-b border-cyan-500/20 bg-gradient-to-b from-[#0a1f3d]/80 to-transparent">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              {/* Bot icon with glow */}
              <div className="relative w-8 h-8 flex items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-600 shadow-lg shadow-cyan-500/30">
                <Bot className="w-4.5 h-4.5 text-white" />
              </div>
              <div>
                <h2 className="text-sm font-black text-white tracking-wide leading-tight">TriNetra Intelligence</h2>
                <p className="text-[10px] text-slate-400">AI Satellite Analyst</p>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {/* Refresh mode */}
              <button
                onClick={handleRefresh}
                title="Refresh AI mode"
                className="p-1.5 text-slate-400 hover:text-cyan-300 rounded-lg hover:bg-cyan-500/10 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              {/* Clear history */}
              <button
                onClick={clearHistory}
                title="Clear chat history"
                className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-red-500/10 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5 scale-x-[-1]" />
              </button>
              {/* Close */}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer"
                aria-label="Close AI assistant"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Mode badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-black/40 border border-cyan-500/20 rounded-xl">
            <span className={`w-2 h-2 rounded-full ${modeCfg.dot} ${modeCfg.pulse ? 'animate-pulse' : ''} shadow-sm`} />
            <span className={`text-[11px] font-bold ${modeCfg.color}`}>{modeCfg.label}</span>
            {mode === 'HEURISTIC_FALLBACK' && (
              <span className="text-[10px] text-slate-400 ml-1">— Run Ollama to enable VLM</span>
            )}
            {mode === 'OLLAMA_TEXT_ONLY' && (
              <span className="text-[10px] text-slate-400 ml-1">— Pull moondream for vision</span>
            )}
          </div>
        </div>

        {/* ── Messages Area ────────────────────────────────────────────────── */}
        <div
          className="flex-1 overflow-y-auto px-3 py-4 space-y-3 custom-scrollbar"
          ref={dragRef}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          {/* Empty state */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-6 py-8">
              <div className="relative flex items-center justify-center">
                <div className="absolute w-20 h-20 rounded-full bg-cyan-500/10 animate-ping" style={{ animationDuration: '3s' }} />
                <div className="relative w-16 h-16 flex items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500/20 to-indigo-600/20 border border-cyan-400/30">
                  <Bot className="w-8 h-8 text-cyan-400" />
                </div>
              </div>
              <div className="text-center px-4">
                <h3 className="text-white font-bold text-base mb-1">TriNetra Intelligence</h3>
                <p className="text-slate-400 text-xs leading-relaxed max-w-xs">
                  Ask me anything about your satellite archive. I can search imagery, detect changes, describe scenes, and guide you through the mission data.
                </p>
              </div>
              {/* Starter suggestions */}
              <div className="w-full grid grid-cols-1 gap-2 px-2">
                {STARTER_SUGGESTIONS.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(s)}
                    className="text-left px-3.5 py-2.5 rounded-xl bg-[#0a1f3d]/60 hover:bg-cyan-500/15
                               border border-cyan-500/20 hover:border-cyan-400/50
                               text-slate-300 hover:text-cyan-200 text-xs transition-all duration-150
                               cursor-pointer flex items-center gap-2"
                  >
                    <Sparkles className="w-3 h-3 text-cyan-400 shrink-0" />
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map(msg => (
            <AssistantMessageBubble
              key={msg.id}
              message={msg}
              onNavigate={onNavigate}
              onSelectTile={onSelectTile}
              onSuggestionClick={handleSend}
            />
          ))}

          {/* Thinking indicator */}
          {isThinking && (
            <div className="flex items-start gap-2.5 animate-fade-in">
              <div className="w-7 h-7 flex items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/30 to-indigo-600/30 border border-cyan-400/30 shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <div className="flex items-center gap-2 px-4 py-3 bg-[#0a1f3d]/70 border border-cyan-500/20 rounded-2xl rounded-tl-sm">
                <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                <span className="text-xs text-cyan-300 font-mono tracking-wider">ANALYSING</span>
                <span className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce"
                          style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* ── Image Preview Strip ──────────────────────────────────────────── */}
        {attachedImage && (
          <div className="flex-none mx-3 mb-2 flex items-center gap-2 p-2 bg-[#0a1f3d]/60 border border-cyan-500/20 rounded-xl">
            <img
              src={attachedImage.previewUrl}
              alt="Attached"
              className="w-12 h-12 rounded-lg object-cover border border-cyan-400/30"
            />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-slate-300 font-medium truncate">{attachedImage.file.name}</p>
              <p className="text-[10px] text-slate-500">{(attachedImage.file.size / 1024).toFixed(1)} KB</p>
            </div>
            <button
              onClick={() => setAttachedImage(null)}
              className="p-1 text-slate-400 hover:text-red-400 rounded-lg hover:bg-red-500/10 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ── Drop zone hint (when no image attached) ──────────────────────── */}
        {!attachedImage && (
          <div className="flex-none mx-3 mb-1 text-center">
            <p className="text-[10px] text-slate-600 flex items-center justify-center gap-1">
              <ImageIcon className="w-3 h-3" />
              Drag & drop a satellite image to analyse or find similar tiles
            </p>
          </div>
        )}

        {/* ── Input Area ──────────────────────────────────────────────────── */}
        <div className="flex-none p-3 border-t border-cyan-500/20 bg-[#020a14]/80">
          <div className="flex items-end gap-2 p-2 bg-[#0a1a2e]/80 border border-cyan-500/25
                          focus-within:border-cyan-400/60 rounded-2xl backdrop-blur-md
                          transition-all duration-200 shadow-inner shadow-black/20">
            {/* Attach image */}
            <button
              onClick={() => fileRef.current?.click()}
              title="Attach satellite image"
              className="p-2 text-slate-400 hover:text-cyan-300 rounded-xl hover:bg-cyan-500/10
                         transition-colors cursor-pointer self-end mb-0.5 shrink-0"
            >
              <Paperclip className="w-4 h-4" />
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/*,.tif,.tiff"
              className="hidden"
              onChange={handleFileChange}
            />

            {/* Text input */}
            <textarea
              ref={inputRef}
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your satellite archive..."
              rows={1}
              className="flex-1 bg-transparent text-white placeholder-slate-500 text-sm
                         resize-none focus:outline-none focus:ring-0 py-2 px-1 leading-relaxed
                         max-h-28 overflow-y-auto custom-scrollbar"
              style={{ minHeight: '36px' }}
            />

            {/* Send button */}
            <button
              onClick={() => handleSend()}
              disabled={isThinking || (!inputText.trim() && !attachedImage)}
              className="p-2.5 bg-gradient-to-br from-cyan-500 to-indigo-600 text-white
                         rounded-xl hover:from-cyan-400 hover:to-indigo-500
                         disabled:opacity-40 disabled:cursor-not-allowed
                         hover:scale-105 active:scale-95 transition-all duration-150
                         cursor-pointer shadow-lg shadow-cyan-500/30 shrink-0 self-end mb-0.5"
              aria-label="Send message"
            >
              {isThinking
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Send className="w-4 h-4" />
              }
            </button>
          </div>

          {/* Keyboard hint */}
          <p className="text-center text-[10px] text-slate-600 mt-1.5">
            Press <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-500 text-[9px]">Enter</kbd> to send · <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-500 text-[9px]">Shift+Enter</kbd> for new line
          </p>
        </div>
      </aside>

      {/* ── Backdrop ──────────────────────────────────────────────────────── */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm sm:hidden"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
    </>
  );
}
