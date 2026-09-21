import React, { useState } from 'react';
import { Bot, User, ChevronDown, ChevronUp, ExternalLink, Layers, Clock, Search, Sparkles } from 'lucide-react';


// Format ISO timestamp to "HH:MM"
function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

// Render Markdown-lite: bold, bullet lists, newlines, inline code
function MarkdownText({ text }) {
  if (!text) return null;
  const lines = text.split('\n');
  return (
    <div className="space-y-1">
      {lines.map((line, li) => {
        // Bullet list
        if (line.trim().startsWith('- ') || line.trim().startsWith('• ')) {
          const content = line.replace(/^[\s\-•]+/, '');
          return (
            <p key={li} className="flex gap-1.5">
              <span className="text-cyan-400 shrink-0 mt-0.5">•</span>
              <InlineMd text={content} />
            </p>
          );
        }
        // Empty line → spacer
        if (!line.trim()) return <div key={li} className="h-1" />;
        return <p key={li}><InlineMd text={line} /></p>;
      })}
    </div>
  );
}

function InlineMd({ text }) {
  // Handle **bold**, `code`, and plain text
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return <code key={i} className="px-1 py-0.5 bg-slate-700/70 rounded text-cyan-300 text-[11px] font-mono">{part.slice(1, -1)}</code>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

// Action label mapping
const ACTION_LABELS = {
  SEARCH_TEXT:    { label: 'Semantic Search',     icon: Search,  color: 'text-cyan-400' },
  SEARCH_IMAGE:   { label: 'Image Similarity',    icon: Layers,  color: 'text-purple-400' },
  DESCRIBE_IMAGE: { label: 'Image Description',   icon: Sparkles,color: 'text-amber-400' },
  CHANGE_DETECT:  { label: 'Change Detection',    icon: Clock,   color: 'text-emerald-400' },
  LIST_TILES:     { label: 'Archive Query',        icon: Layers,  color: 'text-sky-400' },
  TEMPORAL_QUERY: { label: 'Temporal Query',      icon: Clock,   color: 'text-violet-400' },
  INGEST_DATA:    { label: 'Ingest Redirect',     icon: ExternalLink, color:'text-orange-400' },
  EXPLAIN:        { label: 'System Info',          icon: Bot,     color: 'text-slate-400' },
};

export default function AssistantMessageBubble({ message, onNavigate, onSelectTile, onSuggestionClick }) {
  const [showThinking, setShowThinking] = useState(false);
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex flex-col items-end gap-1 animate-fade-in">
        <div className="flex items-end gap-2 max-w-[85%]">
          {/* Message bubble */}
          <div className="px-4 py-3 bg-gradient-to-br from-slate-700/80 to-slate-800/80
                          border border-slate-600/40 rounded-2xl rounded-br-sm
                          text-sm text-slate-100 leading-relaxed">
            {message.image && (
              <img
                src={message.image}
                alt="Attached"
                className="w-40 h-28 object-cover rounded-lg mb-2 border border-slate-600/50"
              />
            )}
            {message.content && <span>{message.content}</span>}
          </div>
          {/* Avatar */}
          <div className="w-7 h-7 flex items-center justify-center rounded-xl bg-slate-700 border border-slate-600/50 shrink-0 mb-0.5">
            <User className="w-3.5 h-3.5 text-slate-300" />
          </div>
        </div>
        <span className="text-[10px] text-slate-600 mr-9">{formatTime(message.timestamp)}</span>
      </div>
    );
  }

  // AI message
  const actionMeta = ACTION_LABELS[message.action] || ACTION_LABELS.EXPLAIN;
  const ActionIcon = actionMeta.icon;
  const hasResults = message.results && Object.keys(message.results).length > 0
                     && !message.results.error
                     && message.results.type !== 'explanation'
                     && message.results.type !== 'ingest_redirect';

  return (
    <div className="flex flex-col items-start gap-1 animate-fade-in">
      <div className="flex items-start gap-2.5 max-w-[95%]">
        {/* Avatar */}
        <div className="w-7 h-7 flex items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/30 to-indigo-600/30 border border-cyan-400/30 shrink-0 mt-0.5">
          <Bot className="w-3.5 h-3.5 text-cyan-400" />
        </div>

        <div className="flex-1 min-w-0 space-y-2">
          {/* Bubble */}
          <div className="px-4 py-3 bg-[#0a1f3d]/70 border border-cyan-500/20
                          rounded-2xl rounded-tl-sm text-sm text-slate-200 leading-relaxed">
            {/* Action badge */}
            <div className="flex items-center gap-1.5 mb-2.5">
              <ActionIcon className={`w-3 h-3 ${actionMeta.color} shrink-0`} />
              <span className={`text-[10px] font-bold uppercase tracking-wider ${actionMeta.color}`}>
                {actionMeta.label}
              </span>
            </div>

            {/* Content */}
            <MarkdownText text={message.content} />

            {/* Thinking steps (collapsible) */}
            {message.thinkingSteps?.length > 0 && (
              <div className="mt-3">
                <button
                  onClick={() => setShowThinking(prev => !prev)}
                  className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-slate-400 transition-colors cursor-pointer"
                >
                  {showThinking ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  {showThinking ? 'Hide' : 'Show'} reasoning steps
                </button>
                {showThinking && (
                  <div className="mt-2 space-y-1 border-l-2 border-cyan-500/20 pl-2.5">
                    {message.thinkingSteps.map((step, i) => (
                      <p key={i} className="text-[10px] text-slate-500 font-mono">{step}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>



          {/* Follow-up suggestion chips */}
          {message.suggestions?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              {message.suggestions.slice(0, 3).map((s, i) => (
                <button
                  key={i}
                  onClick={() => onSuggestionClick?.(s)}
                  className="px-2.5 py-1 text-[10px] text-slate-300 hover:text-cyan-200
                             bg-[#0a1f3d]/50 hover:bg-cyan-500/15
                             border border-cyan-500/15 hover:border-cyan-400/40
                             rounded-full transition-all duration-150 cursor-pointer"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <span className="text-[10px] text-slate-600 ml-9">{formatTime(message.timestamp)}</span>
    </div>
  );
}
