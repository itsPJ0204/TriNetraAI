import React, { useState } from 'react';
import { ExternalLink, Clock, Search, Layers, Calendar, AlertTriangle, ChevronRight } from 'lucide-react';
import { API_BASE_URL } from '../services/api';

// ─── Tile thumbnail with fallback ────────────────────────────────────────────
function TileThumbnail({ tile, size = 'sm' }) {
  const [imgError, setImgError] = useState(false);
  const dim = size === 'sm' ? 'w-14 h-14' : 'w-20 h-20';

  const rawPath = tile?.image_path || tile?.filepath || '';
  const cleanPath = rawPath.replace(/\\/g, '/').replace(/^\/+/, '');
  const isTif = cleanPath.toLowerCase().endsWith('.tif') || cleanPath.toLowerCase().endsWith('.tiff');
  const imgUrl = cleanPath
    ? (isTif ? `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(cleanPath)}` : `${API_BASE_URL}/${cleanPath}`)
    : null;

  return (
    <div className={`${dim} rounded-lg overflow-hidden border border-cyan-500/20 bg-slate-800/60 shrink-0 flex items-center justify-center`}>
      {imgUrl && !imgError ? (
        <img
          src={imgUrl}
          alt={tile?.id || 'tile'}
          className="w-full h-full object-cover"
          onError={() => setImgError(true)}
        />
      ) : (
        <Layers className="w-5 h-5 text-slate-600" />
      )}
    </div>
  );
}

// ─── Score badge ──────────────────────────────────────────────────────────────
function ScoreBadge({ score }) {
  if (score == null) return null;
  const pct = score > 1 ? Math.round(score) : Math.round(score * 100);
  const color = pct >= 85 ? 'text-emerald-400 border-emerald-400/30' :
                pct >= 65 ? 'text-cyan-400 border-cyan-400/30' :
                            'text-amber-400 border-amber-400/30';
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 border rounded-full ${color}`}>
      {pct}%
    </span>
  );
}

// ─── Search Results Card ──────────────────────────────────────────────────────
function SearchCard({ results, onSelectTile }) {
  const tiles = results.tiles || results.results || [];
  if (!tiles.length) return (
    <div className="px-3 py-2 text-xs text-slate-400 flex items-center gap-2">
      <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
      No matching tiles found in archive.
    </div>
  );

  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">
        {tiles.length} Result{tiles.length !== 1 ? 's' : ''} · {results.query ? `"${results.query}"` : 'Image Match'}
      </p>
      {tiles.slice(0, 4).map((tile, i) => (
        <button
          key={tile?.tile_id || tile?.id || i}
          onClick={() => (tile?.tile_id || tile?.id) && onSelectTile?.(tile.tile_id || tile.id)}
          className="w-full flex items-center gap-2.5 px-2.5 py-2
                     bg-[#071428]/70 hover:bg-cyan-500/10
                     border border-cyan-500/15 hover:border-cyan-400/40
                     rounded-xl transition-all duration-150 cursor-pointer text-left group"
        >
          <TileThumbnail tile={tile} size="sm" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-slate-200 truncate group-hover:text-cyan-200">
              {tile?.tile_id || tile?.id || tile?.tile_name || `Tile ${i + 1}`}
            </p>
            <p className="text-[10px] text-slate-500 truncate">
              {tile?.date || tile?.dateIso || ''}
              {tile?.crs ? ` · ${tile.crs}` : ''}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            <ScoreBadge score={tile?.score} />
            <ChevronRight className="w-3 h-3 text-slate-600 group-hover:text-cyan-400 transition-colors" />
          </div>
        </button>
      ))}
    </div>
  );
}

// ─── Change Detection Card ─────────────────────────────────────────────────────
function ChangeCard({ results, onNavigate }) {
  const report = results.report || results;
  const count = report?.target_count ?? report?.detected_targets?.length ?? 0;
  const mode  = report?.mode_used || 'dual-engine';
  const pct   = typeof report?.changed_area_pct === 'number'
    ? report.changed_area_pct.toFixed(1) : '—';

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Changes', value: count, color: count > 0 ? 'text-red-400' : 'text-emerald-400' },
          { label: 'Area %',  value: `${pct}%`, color: 'text-amber-400' },
          { label: 'Engine',  value: mode === 'BIT' ? 'Neural BIT' : 'Classical', color: 'text-cyan-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="flex flex-col items-center py-2.5 bg-[#071428]/70 border border-cyan-500/15 rounded-xl">
            <span className={`text-base font-black ${color}`}>{value}</span>
            <span className="text-[10px] text-slate-500 mt-0.5">{label}</span>
          </div>
        ))}
      </div>
      {onNavigate && (
        <button
          onClick={() => onNavigate('temporal-analysis')}
          className="w-full flex items-center justify-center gap-1.5 py-2
                     bg-emerald-500/10 hover:bg-emerald-500/20
                     border border-emerald-500/20 hover:border-emerald-400/50
                     text-emerald-400 text-xs font-semibold rounded-xl transition-all cursor-pointer"
        >
          <ExternalLink className="w-3 h-3" />
          Open in Temporal Analysis
        </button>
      )}
    </div>
  );
}

// ─── Tile List Card ────────────────────────────────────────────────────────────
function TileListCard({ results }) {
  const tiles = results.tiles || [];
  const count = results.count || tiles.length;
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">
        Archive — {count} Tile{count !== 1 ? 's' : ''}
      </p>
      {tiles.slice(0, 5).map((t, i) => (
        <div key={t?.tile_id || t?.id || i} className="flex items-center gap-2 px-2.5 py-1.5 bg-[#071428]/70 border border-cyan-500/10 rounded-lg">
          <Layers className="w-3 h-3 text-cyan-500/60 shrink-0" />
          <span className="text-[11px] text-slate-300 truncate flex-1">{t?.tile_id || t?.id || t?.tile_name || `tile_${i + 1}`}</span>
          <span className="text-[10px] text-slate-600 shrink-0">{t?.date || ''}</span>
        </div>
      ))}
      {count > 5 && (
        <p className="text-[10px] text-slate-500 px-1">...and {count - 5} more</p>
      )}
    </div>
  );
}

// ─── Temporal Info Card ────────────────────────────────────────────────────────
function TemporalCard({ results, onNavigate }) {
  const dates = results.available_dates || [];
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">
        {dates.length} Acquisition Epoch{dates.length !== 1 ? 's' : ''}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {dates.map(d => (
          <span key={d} className="flex items-center gap-1 px-2 py-1 bg-[#071428]/70 border border-violet-500/20 rounded-lg text-[10px] text-violet-300 font-mono">
            <Calendar className="w-2.5 h-2.5" />
            {d}
          </span>
        ))}
      </div>
      {onNavigate && (
        <button
          onClick={() => onNavigate('temporal-analysis')}
          className="w-full flex items-center justify-center gap-1.5 py-2
                     bg-violet-500/10 hover:bg-violet-500/20
                     border border-violet-500/20 hover:border-violet-400/50
                     text-violet-400 text-xs font-semibold rounded-xl transition-all cursor-pointer"
        >
          <Clock className="w-3 h-3" />
          Open Temporal Analysis
        </button>
      )}
    </div>
  );
}

// ─── Image Description Card (with similar tiles) ──────────────────────────────
function DescriptionCard({ results, onSelectTile }) {
  const similar = results.similar_tiles || [];
  return (
    <div className="space-y-2">
      {similar.length > 0 && (
        <>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">
            {similar.length} Similar Tile{similar.length !== 1 ? 's' : ''} Found
          </p>
          {similar.slice(0, 3).map((tile, i) => (
            <button
              key={tile?.tile_id || tile?.id || i}
              onClick={() => (tile?.tile_id || tile?.id) && onSelectTile?.(tile.tile_id || tile.id)}
              className="w-full flex items-center gap-2.5 px-2.5 py-2
                         bg-[#071428]/70 hover:bg-amber-500/10
                         border border-amber-500/15 hover:border-amber-400/40
                         rounded-xl transition-all duration-150 cursor-pointer text-left group"
            >
              <TileThumbnail tile={tile} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-200 truncate group-hover:text-amber-200">
                  {tile?.tile_id || tile?.id || tile?.tile_name || `Similar ${i + 1}`}
                </p>
              </div>
              <ScoreBadge score={tile?.score} />
            </button>
          ))}
        </>
      )}
    </div>
  );
}

// ─── Main Router ──────────────────────────────────────────────────────────────
export default function AssistantResultCard({ results, action, onNavigate, onSelectTile }) {
  if (!results || results.error) return null;

  const containerCls = `p-3 bg-[#040e1e]/80 border border-cyan-500/15 rounded-xl space-y-2 text-left`;

  switch (action) {
    case 'SEARCH_TEXT':
    case 'SEARCH_IMAGE':
      return (
        <div className={containerCls}>
          <SearchCard results={results} onSelectTile={onSelectTile} />
          {results.type !== 'image_description' && (
            <button
              onClick={() => onNavigate?.('semantic-search')}
              className="w-full flex items-center justify-center gap-1.5 py-1.5
                         bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/15
                         hover:border-cyan-400/40 text-cyan-400 text-[11px] font-semibold
                         rounded-lg transition-all cursor-pointer"
            >
              <Search className="w-3 h-3" />
              View in Search Results
            </button>
          )}
        </div>
      );

    case 'DESCRIBE_IMAGE':
      return results.similar_tiles?.length > 0 ? (
        <div className={containerCls}>
          <DescriptionCard results={results} onSelectTile={onSelectTile} />
        </div>
      ) : null;

    case 'CHANGE_DETECT':
      return (
        <div className={containerCls}>
          <ChangeCard results={results} onNavigate={onNavigate} />
        </div>
      );

    case 'LIST_TILES':
      return (
        <div className={containerCls}>
          <TileListCard results={results} />
        </div>
      );

    case 'TEMPORAL_QUERY':
      return (
        <div className={containerCls}>
          <TemporalCard results={results} onNavigate={onNavigate} />
        </div>
      );

    default:
      return null;
  }
}
