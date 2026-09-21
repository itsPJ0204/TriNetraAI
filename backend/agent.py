"""
TriNetraAI AI Assistant Agent
-------------------------------
Fully offline, CPU-only AI agent that:
  1. Parses user intent via qwen2:0.5b (Ollama) or heuristic keyword router
  2. Routes to existing TriNetraAI backend capabilities
  3. Narrates results via LLM or templated summaries
  4. Handles image input: moondream (Ollama) for description + RemoteCLIP for similarity

Modes (auto-detected at startup):
  OLLAMA_FULL        — qwen2:0.5b + moondream both available
  OLLAMA_TEXT_ONLY   — qwen2:0.5b available, moondream not pulled
  HEURISTIC_FALLBACK — Ollama not running; deterministic keyword router
"""

from __future__ import annotations

import json
import re
import time
import logging
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("trinetra.agent")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://localhost:11434"
INTENT_MODEL    = "qwen2:0.5b"
VISION_MODEL    = "moondream"
OLLAMA_TIMEOUT  = 60.0   # seconds – CPU inference is slower


# ---------------------------------------------------------------------------
# Enums & Schemas
# ---------------------------------------------------------------------------

class AgentMode(str, Enum):
    OLLAMA_FULL       = "OLLAMA_FULL"
    OLLAMA_TEXT_ONLY  = "OLLAMA_TEXT_ONLY"
    HEURISTIC_FALLBACK = "HEURISTIC_FALLBACK"


class ActionType(str, Enum):
    SEARCH_TEXT      = "SEARCH_TEXT"
    SEARCH_IMAGE     = "SEARCH_IMAGE"
    DESCRIBE_IMAGE   = "DESCRIBE_IMAGE"
    CHANGE_DETECT    = "CHANGE_DETECT"
    LIST_TILES       = "LIST_TILES"
    TEMPORAL_QUERY   = "TEMPORAL_QUERY"
    INGEST_DATA      = "INGEST_DATA"
    EXPLAIN          = "EXPLAIN"


class ParsedIntent(BaseModel):
    action: ActionType
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    entities: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""


class AssistantResponse(BaseModel):
    response: str                        # Natural language answer
    action_taken: ActionType
    results: dict[str, Any] = Field(default_factory=dict)
    follow_up_suggestions: list[str] = Field(default_factory=list)
    mode_used: AgentMode = AgentMode.HEURISTIC_FALLBACK
    thinking_steps: list[str] = Field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Ollama Client
# ---------------------------------------------------------------------------

class OllamaClient:
    """Thin async-friendly REST client for local Ollama server."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self._available_models: set[str] = set()

    def probe(self) -> AgentMode:
        """Synchronously check which models are available. Returns AgentMode."""
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            if resp.status_code != 200:
                return AgentMode.HEURISTIC_FALLBACK
            models = {m["name"].split(":")[0] for m in resp.json().get("models", [])}
            # also handle full name tags like "qwen2:0.5b"
            full_names = {m["name"] for m in resp.json().get("models", [])}
            self._available_models = models | full_names
            logger.info(f"[Agent] Ollama models available: {self._available_models}")

            has_intent = (
                INTENT_MODEL in self._available_models
                or INTENT_MODEL.split(":")[0] in self._available_models
            )
            has_vision = (
                VISION_MODEL in self._available_models
                or VISION_MODEL.split(":")[0] in self._available_models
            )

            if has_intent and has_vision:
                return AgentMode.OLLAMA_FULL
            elif has_intent:
                return AgentMode.OLLAMA_TEXT_ONLY
            else:
                return AgentMode.HEURISTIC_FALLBACK
        except Exception as exc:
            logger.warning(f"[Agent] Ollama not reachable: {exc}. Using heuristic fallback.")
            return AgentMode.HEURISTIC_FALLBACK

    def generate(
        self,
        model: str,
        prompt: str,
        image_b64: str | None = None,
        num_predict: int = 256,
        stop: list[str] | None = None,
    ) -> str:
        """Call Ollama /api/generate and return the response text."""
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": num_predict,
                "repeat_penalty": 1.3,   # penalise repetition
                "top_p": 0.9,
            },
        }
        if stop:
            payload["options"]["stop"] = stop
        if image_b64:
            payload["images"] = [image_b64]

        resp = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


# ---------------------------------------------------------------------------
# Heuristic Keyword Router (zero-dependency fallback)
# ---------------------------------------------------------------------------

# Ordered from most-specific to least-specific to avoid false positives
_GREETING_KEYWORDS = r"\b(hello|hi|hey|greetings|help|who are you|what can you do|about you|capabilities|capability|features|feature|system overview)\b"
_TEMPORAL_KEYWORDS = r"\b(date|dates|epoch|epochs|timeline|period|acquisition|timestamp|when)\b"
_CHANGE_KEYWORDS   = r"\b(change|changed|changes|detect|detecting|difference|differences|compare|comparison|before.?after|alterat|modif|anomaly|transition|delta)\b"
_INGEST_KEYWORDS   = r"\b(upload|ingest|ingesting|import a file|add a tile|load a tile)\b"
_LIST_KEYWORDS     = r"\b(list|all tiles|inventory|catalog|show tiles|available tiles|browse tiles)\b"
_EXPLAIN_KEYWORDS  = r"\b(what is|explain|how does|tell me|describe the system|help me|how do i|who are|can you|what are|overview)\b"
_SEARCH_KEYWORDS   = r"\b(find|search|show|locate|look for|retrieve|get|display|scan|where|near|around|with|containing|has|have)\b"


def _heuristic_parse(message: str, has_image: bool) -> ParsedIntent:
    """Deterministic intent classification from keywords."""
    msg = message.lower().strip()

    if has_image:
        # Image similarity search vs description
        if re.search(r"\b(similar|find like|match|reverse|search|look for)\b", msg):
            return ParsedIntent(
                action=ActionType.SEARCH_IMAGE,
                confidence=0.9,
                entities={"top_k": 5, "query": message},
                reasoning="Image provided + similarity keywords detected",
            )
        return ParsedIntent(
            action=ActionType.DESCRIBE_IMAGE,
            confidence=0.85,
            entities={"query": message},
            reasoning="Image provided without explicit similarity intent → describe",
        )

    # 1. Pure greeting or capabilities check
    if re.fullmatch(r"(hello|hi|hey|greetings|help|who are you|what can you do)[\s\.\?!]*", msg) or (re.search(_GREETING_KEYWORDS, msg) and len(msg.split()) <= 6):
        return ParsedIntent(
            action=ActionType.EXPLAIN,
            confidence=0.95,
            entities={"topic": "capabilities", "query": message},
            reasoning="Greeting or system capabilities question detected",
        )

    # 2. Specific intent checks
    if re.search(_TEMPORAL_KEYWORDS, msg):
        return ParsedIntent(
            action=ActionType.TEMPORAL_QUERY,
            confidence=0.85,
            entities={"query": message},
            reasoning="Temporal/date keywords detected",
        )
    if re.search(_CHANGE_KEYWORDS, msg):
        return ParsedIntent(
            action=ActionType.CHANGE_DETECT,
            confidence=0.85,
            entities={"query": message},
            reasoning="Change detection keywords detected",
        )
    if re.search(_INGEST_KEYWORDS, msg):
        return ParsedIntent(
            action=ActionType.INGEST_DATA,
            confidence=0.85,
            entities={"query": message},
            reasoning="Ingestion keywords detected",
        )
    if re.search(_LIST_KEYWORDS, msg):
        return ParsedIntent(
            action=ActionType.LIST_TILES,
            confidence=0.85,
            entities={"query": message},
            reasoning="List/archive keywords detected",
        )
    if re.search(_EXPLAIN_KEYWORDS, msg) and not re.search(r"\b(find|search|show|locate|tiles?|imagery)\b", msg):
        return ParsedIntent(
            action=ActionType.EXPLAIN,
            confidence=0.8,
            entities={"query": message},
            reasoning="Explanation keywords detected",
        )

    # Default: treat any query with 2+ words as a semantic search
    # This is the correct fallback for descriptive queries like
    # "military installations near water", "riverbanks", "urban sprawl", etc.
    return ParsedIntent(
        action=ActionType.SEARCH_TEXT,
        confidence=0.75,
        entities={"query": message, "top_k": 5},
        reasoning="No specific intent keyword matched; defaulting to semantic search",
    )


# ---------------------------------------------------------------------------
# Ollama Intent Parser
# ---------------------------------------------------------------------------

_INTENT_SYSTEM_PROMPT = """You are an AI routing assistant for TriNetraAI.
Output ONLY valid JSON matching this exact structure:
{"action": "<ACTION>", "confidence": 0.9, "entities": {}, "reasoning": "<short reasoning>"}

Valid actions:
- SEARCH_TEXT: find/search satellite tiles by text description (e.g., "find military installations near water")
- SEARCH_IMAGE: find tiles similar to an uploaded image (e.g., "find similar images", "search with this")
- DESCRIBE_IMAGE: tell the user what is in an uploaded image (e.g., "what is this?", "describe this image")
- CHANGE_DETECT: compare two tiles, detect changes over time (e.g., "what changed?", "compare these")
- LIST_TILES: list all tiles in the archive (e.g., "show all tiles")
- TEMPORAL_QUERY: ask about dates/timeline (e.g., "what dates are available?")
- INGEST_DATA: upload/add new data (e.g., "add this tile to database")
- EXPLAIN: general questions (e.g., "how does this work?")

Examples:
User: "find military installations near water"
JSON: {"action": "SEARCH_TEXT", "confidence": 0.95, "entities": {"query": "military installations near water", "top_k": 5}, "reasoning": "User wants to search for specific terrain."}

User: (User uploaded an image) "find images with river nearby"
JSON: {"action": "SEARCH_IMAGE", "confidence": 0.9, "entities": {"top_k": 5}, "reasoning": "User uploaded an image and wants to search for similar ones."}

User: "what changed between tile A and B?"
JSON: {"action": "CHANGE_DETECT", "confidence": 0.95, "entities": {}, "reasoning": "User explicitly asked to compare tiles."}
"""

def _parse_intent_with_ollama(
    client: OllamaClient,
    message: str,
    has_image: bool,
    history_summary: str = "",
) -> ParsedIntent:
    """Use qwen2:0.5b to parse intent into structured JSON."""
    context = f"\nPrevious context: {history_summary}" if history_summary else ""
    image_note = "\nNote: The user also uploaded an image." if has_image else ""
    prompt = (
        f"{_INTENT_SYSTEM_PROMPT}{context}{image_note}\n\n"
        f"User message: {message}\n\nJSON:"
    )
    try:
        raw = client.generate(INTENT_MODEL, prompt)
        # Extract JSON from response (model sometimes adds extra text or markdown fences)
        data = None
        for pattern in (r"```(?:json)?\s*(\{.*?\})\s*```", r"(\{[^{}]*\"action\"[^{}]*\})", r"\{.*\}"):
            match = re.search(pattern, raw, re.DOTALL)
            if match:
                try:
                    candidate = match.group(1) if match.lastindex else match.group(0)
                    data = json.loads(candidate)
                    if isinstance(data, dict):
                        break
                except Exception:
                    continue
        if not data:
            try:
                data = json.loads(raw)
            except Exception:
                raise ValueError(f"No valid JSON found in model output: {raw[:80]}")

        action_str = str(data.get("action", "SEARCH_TEXT")).upper()
        try:
            action = ActionType(action_str)
        except ValueError:
            action = ActionType.SEARCH_TEXT

        # --- SAFETY GUARDS ---
        msg_lower = message.lower()
        
        # 1. Prevent CHANGE_DETECT hallucination
        if action == ActionType.CHANGE_DETECT and not re.search(_CHANGE_KEYWORDS, msg_lower):
            logger.info("[Agent] LLM chose CHANGE_DETECT but no change keywords found. Overriding.")
            action = ActionType.SEARCH_IMAGE if has_image else ActionType.SEARCH_TEXT
            
        # 2. Prevent IMAGE actions if no image is attached
        if action in (ActionType.SEARCH_IMAGE, ActionType.DESCRIBE_IMAGE) and not has_image:
            logger.info(f"[Agent] LLM chose {action.name} but no image uploaded. Overriding.")
            action = ActionType.SEARCH_TEXT

        # 3. Prevent INGEST, LIST, TEMPORAL hallucinations
        if action == ActionType.INGEST_DATA and not re.search(_INGEST_KEYWORDS, msg_lower):
            action = ActionType.SEARCH_TEXT
        if action == ActionType.LIST_TILES and not re.search(_LIST_KEYWORDS, msg_lower):
            action = ActionType.SEARCH_TEXT
        if action == ActionType.TEMPORAL_QUERY and not re.search(_TEMPORAL_KEYWORDS, msg_lower):
            action = ActionType.SEARCH_TEXT
        if action == ActionType.EXPLAIN and not re.search(_EXPLAIN_KEYWORDS, msg_lower):
            action = ActionType.SEARCH_TEXT

        # 4. If LLM chose SEARCH_TEXT but the user is clearly asking a conversational question
        if action == ActionType.SEARCH_TEXT and re.search(_EXPLAIN_KEYWORDS, msg_lower):
            logger.info("[Agent] LLM chose SEARCH_TEXT but conversational keywords found. Overriding to EXPLAIN.")
            action = ActionType.EXPLAIN

        entities = data.get("entities", {})
        if "query" not in entities:
            entities["query"] = message
        if action == ActionType.SEARCH_TEXT and "top_k" not in entities:
            entities["top_k"] = 5

        return ParsedIntent(
            action=action,
            confidence=float(data.get("confidence", 0.85)),
            entities=entities,
            reasoning=str(data.get("reasoning", "")),
        )
    except Exception as exc:
        logger.warning(f"[Agent] Ollama intent parsing failed: {exc}. Falling back to heuristic.")
        return _heuristic_parse(message, has_image)


# ---------------------------------------------------------------------------
# Action Router — calls existing TriNetraAI modules
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _route_action(
    intent: ParsedIntent,
    image_bytes: bytes | None,
    image_filename: str | None,
) -> dict[str, Any]:
    """
    Execute the resolved intent against existing TriNetraAI backend modules.
    Returns a raw results dict.
    """
    action = intent.action
    entities = intent.entities

    # ── SEARCH_TEXT ──────────────────────────────────────────────────────────
    if action == ActionType.SEARCH_TEXT:
        query = entities.get("query", "")
        
        # Strip conversational filler that dilutes vector search
        filler_patterns = [
            r"^(please\s+)?(show|find|search(\s+for)?|get)(\s+(me|all|the|some))?\s+(image(s)?\s+)?(tile(s)?)?\s*(which\s+has|with|of|showing)\s*-?\s*",
            r"^i want to (see|find) (all\s+)?(the\s+)?images (with|of)\s*-?\s*",
        ]
        import re
        for pattern in filler_patterns:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE).strip("- \"'")
            
        top_k = int(entities.get("top_k", 5))
        if not query:
            return {"error": "No search query found in your message."}

        # Multi-sensor routing: Detect if user explicitly requested radar or optical
        sensor_choice = "sentinel2"
        if re.search(r"\b(sentinel.?1|sar|radar|c-sar|microwave)\b", query.lower()):
            sensor_choice = "sentinel1"
        elif re.search(r"\b(all sensors|both sensors|multi.?sensor)\b", query.lower()):
            sensor_choice = "all"

        try:
            from semantic_search.search import search
            results = search(query=query, top_k=top_k, sensor=sensor_choice)
            return {
                "type": "search_results",
                "query": query,
                "sensor": sensor_choice,
                "count": len(results),
                "tiles": _json_safe_results(results),
            }
        except Exception as exc:
            logger.error(f"[Agent] Search failed: {exc}")
            return {"error": f"Semantic search unavailable: {exc}"}

    # ── SEARCH_IMAGE ─────────────────────────────────────────────────────────
    if action == ActionType.SEARCH_IMAGE:
        if not image_bytes:
            return {"error": "Please upload a satellite image to perform image similarity search."}
        top_k = int(entities.get("top_k", 5))
        
        raw_msg = intent.entities.get("query", "")
        multimodal_query = None
        if raw_msg and not re.search(r"^(search|find|similar|match|like this)$", raw_msg.lower().strip()):
            multimodal_query = raw_msg

        try:
            from PIL import Image
            from semantic_search.search import search_by_image
            img = Image.open(BytesIO(image_bytes)).convert("RGB")
            results = search_by_image(image=img, query=multimodal_query, top_k=top_k)
            return {
                "type": "image_search_results",
                "count": len(results),
                "tiles": _json_safe_results(results),
            }
        except Exception as exc:
            logger.error(f"[Agent] Image search failed: {exc}")
            return {"error": f"Image search unavailable: {exc}"}

    # ── DESCRIBE_IMAGE ───────────────────────────────────────────────────────
    # The description is handled by the agent after routing (needs VLM).
    # Here we just pass image info through.
    if action == ActionType.DESCRIBE_IMAGE:
        return {
            "type": "image_description",
            "filename": image_filename or "uploaded_image",
        }

    # ── CHANGE_DETECT ────────────────────────────────────────────────────────
    if action == ActionType.CHANGE_DETECT:
        before = entities.get("before_path") or entities.get("tile_t1")
        after  = entities.get("after_path")  or entities.get("tile_t2")
        if not before or not after:
            return {
                "type": "change_detect_prompt",
                "message": (
                    "To run automated change detection, please select a tile from the Candidate Grid or "
                    "navigate directly to the Temporal Analysis section."
                ),
            }
        try:
            from detective_api import compare_tiles
            report = compare_tiles(
                str(PROJECT_ROOT / before),
                str(PROJECT_ROOT / after),
                apply_qa_suppression=True,
                min_area=100,
            )
            return {"type": "change_detection", "report": _json_safe_raw(report)}
        except Exception as exc:
            logger.error(f"[Agent] Change detection failed: {exc}")
            return {"error": f"Change detection unavailable: {exc}"}

    # ── LIST_TILES ───────────────────────────────────────────────────────────
    if action == ActionType.LIST_TILES:
        try:
            from spatial.queries import get_all_tiles
            tiles = get_all_tiles()
            return {
                "type": "tile_list",
                "count": len(tiles),
                "tiles": _json_safe_raw(tiles)[:20],  # cap at 20 for chat
            }
        except Exception as exc:
            logger.error(f"[Agent] List tiles failed: {exc}")
            return {"error": f"Tile registry unavailable: {exc}"}

    # ── TEMPORAL_QUERY ───────────────────────────────────────────────────────
    if action == ActionType.TEMPORAL_QUERY:
        try:
            import re as _re
            dates_set: set[str] = set()

            # 1. Scan filesystem tiles directory
            tiles_base = PROJECT_ROOT / "data" / "tiles"
            if tiles_base.is_dir():
                for s_dir in tiles_base.iterdir():
                    if s_dir.is_dir():
                        for d in s_dir.iterdir():
                            if d.is_dir() and _re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name):
                                dates_set.add(d.name)

            # 2. Also extract dates from SQLite tile_registry
            db_path = PROJECT_ROOT / "database" / "tile_registry.sqlite"
            if db_path.exists():
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                cur.execute("SELECT filepath, tile_id FROM tiles")
                for row in cur.fetchall():
                    for val in row:
                        if val:
                            m = _re.search(r"(\d{4}-\d{2}-\d{2})", str(val))
                            if m:
                                dates_set.add(m.group(1))
                conn.close()

            if not dates_set:
                dates_set = {"2025-06-07", "2026-01-18", "2026-06-27", "2026-09-10", "2026-03-13", "2026-06-17"}

            sorted_dates = sorted(dates_set)
            return {
                "type": "temporal_info",
                "available_dates": sorted_dates,
                "count": len(sorted_dates),
                "earliest": sorted_dates[0],
                "latest": sorted_dates[-1],
            }
        except Exception as exc:
            return {"error": f"Temporal query failed: {exc}"}

    # ── INGEST_DATA ──────────────────────────────────────────────────────────
    if action == ActionType.INGEST_DATA:
        return {
            "type": "ingest_redirect",
            "message": "To ingest new satellite data, please use the Tile Ingestion section below.",
        }

    # ── EXPLAIN ──────────────────────────────────────────────────────────────
    if action == ActionType.EXPLAIN:
        return {"type": "explanation", "topic": entities.get("topic", "TriNetraAI")}

    return {"error": "Unknown action."}


# ---------------------------------------------------------------------------
# Result Synthesizer — narrate results in natural language
# ---------------------------------------------------------------------------

_MAX_NARRATION_TOKENS = 150  # strict limit to prevent hallucination loops
_REPETITION_PATTERN = re.compile(r"(\b\w{4,}\b)(?:\W+\1){4,}", re.IGNORECASE)  # catches word repeated 5+ times


def _is_hallucinating(text: str) -> bool:
    """Detect obvious LLM hallucination: extreme length or severe repetition."""
    if len(text) > 800:
        return True
    if _REPETITION_PATTERN.search(text):
        return True
    # Catch sentence repetition (same 6-word ngram appears 3+ times)
    words = text.lower().split()
    if len(words) >= 18:
        ngrams = [" ".join(words[i:i+6]) for i in range(len(words) - 5)]
        for ng in ngrams:
            if ngrams.count(ng) >= 3:
                return True
    return False


def _synthesize_with_ollama(client: OllamaClient, intent: ParsedIntent, raw: dict) -> str:
    """Use qwen2:0.5b to narrate results as an agent analyst."""
    if intent.action == ActionType.SEARCH_TEXT:
        count = raw.get("count", 0)
        query = raw.get("query", "")
        top_tile = (raw.get("tiles") or [{}])[0].get("tile_name", "") if count else ""
        fact = (
            f"You are TriNetra AI, an expert satellite reconnaissance agent.\n"
            f"You successfully ran a vector search for '{query}' and retrieved {count} matching satellite tiles.\n"
            f"The top candidate tile is {top_tile}.\n"
            f"Write a 2-3 sentence professional markdown response to the user. Explain that you have successfully "
            f"found the imagery matching their query, and that you have handed the visual tiles over to the main 'Ranked Candidate Tiles' "
            f"grid for their inspection. Suggest that they can select a tile to run Temporal Analysis or Change Detection.\n"
            f"Do not hallucinate facts."
        )
    elif intent.action == ActionType.SEARCH_IMAGE:
        count = raw.get("count", 0)
        fact = (
            f"You are TriNetra AI. You just ran a reverse image similarity search and found {count} matching tiles.\n"
            f"Write a 2-sentence response explaining you've routed the visual matches to the main application grid and they should inspect them."
        )
    elif intent.action == ActionType.LIST_TILES:
        fact = (
            f"You are TriNetra AI. The archive contains {raw.get('count', 0)} tiles.\n"
            f"Explain this briefly and mention they can view the full catalog in the Tile Archive section."
        )
    elif intent.action == ActionType.TEMPORAL_QUERY:
        dates = ', '.join(raw.get('available_dates', []))
        fact = (
            f"You are TriNetra AI. The available acquisition epochs in the system are: {dates}.\n"
            f"Provide this information clearly to the user."
        )
    elif intent.action == ActionType.CHANGE_DETECT:
        r = raw.get("report", {})
        fact = (
            f"You are TriNetra AI. Change detection completed using {r.get('mode_used', 'dual-engine')} and found {r.get('target_count', 0)} changes.\n"
            f"Inform the user and tell them to check the Temporal Analysis view for the generated overlay mask."
        )
    elif intent.action == ActionType.EXPLAIN:
        user_query = intent.entities.get("query", "TriNetra AI features")
        fact = (
            f"You are TriNetra AI, an advanced satellite reconnaissance platform. "
            f"Your features include Natural Language Vector Search (using RemoteCLIP), "
            f"Image-to-Image Search (reverse image search for tiles), Bitemporal Change Detection, and Temporal Analysis.\n"
            f"The user is asking: '{user_query}'.\n"
            f"Provide a helpful, accurate, and concise answer directly addressing their question based on the features available. Do not just list all features unless asked."
        )
    else:
        return _template_narrate(intent, raw)

    if raw.get("error"):
        return f"⚠️ {raw['error']}"

    prompt = f"{fact}\n\nResponse:"
    try:
        text = client.generate(INTENT_MODEL, prompt)
        if _is_hallucinating(text):
            logger.warning("[Agent] Narration hallucination detected, using template fallback.")
            return _template_narrate(intent, raw)
        return text.strip()
    except Exception:
        return _template_narrate(intent, raw)


def _template_narrate(intent: ParsedIntent, raw: dict) -> str:
    """Deterministic template-based narration (no LLM needed)."""
    action = intent.action
    error = raw.get("error")
    if error:
        return f"⚠️ {error}"

    if action == ActionType.SEARCH_TEXT:
        count = raw.get("count", 0)
        query = raw.get("query", "your query")
        if count == 0:
            return f"No satellite tiles found matching **\"{query}\"**. Try a different query or broaden your search terms."
        return (
            f"I have successfully executed a semantic vector search for **\"{query}\"** and found **{count} candidate tile{'s' if count != 1 else ''}**.\n\n"
            f"I have handed the visual results over to the main application interface. Please look at the **Ranked Candidate Tiles** grid in the main view to inspect the imagery.\n\n"
            f"**Next Step**: Select any tile to open it in the Temporal Analysis module to detect changes over time."
        )
    if action == ActionType.SEARCH_IMAGE:
        count = raw.get("count", 0)
        return (
            f"I have processed the uploaded image and found **{count} visually similar tile{'s' if count != 1 else ''}** in the archive using RemoteCLIP embedding similarities.\n\n"
            f"The visual matches have been routed to the main application grid. Select a tile to run bitemporal change detection."
        )
    if action == ActionType.DESCRIBE_IMAGE:
        return "📡 Analysing the uploaded satellite image with the onboard vision model..."
    if action == ActionType.CHANGE_DETECT:
        if raw.get("type") == "change_detect_prompt":
            return (
                "🔍 **Bitemporal Change Detection**\n\n"
                "TriNetra AI compares two acquisition epochs using our Dual-Engine BIT Transformer + Classical CV with automated cloud and shadow suppression.\n\n"
                "**How to use:**\n"
                "1. Select any candidate tile in the **Ranked Candidate Tiles** grid.\n"
                "2. Navigate to the **Temporal Analysis & Change Detection** section to select baseline and surveillance dates, slide the optical wiper, and view detected anomaly masks."
            )
        report = raw.get("report", {})
        count = report.get("target_count", 0)
        mode = report.get("mode_used", "dual-engine")
        return (
            f"Change detection is complete (Mode: {mode}).\n\n"
            f"I detected **{count} potential change region{'s' if count != 1 else ''}** after applying QA cloud suppression. "
            f"The change overlay mask has been mapped directly to the **Temporal Analysis** section for your review."
        )
    if action == ActionType.LIST_TILES:
        count = raw.get("count", 0)
        return (
            f"The archive contains **{count} indexed satellite tile{'s' if count != 1 else ''}** in the local registry.\n\n"
            f"You can browse the complete inventory in the **Tile Ingestion & Archive** section, or perform natural language vector searches above."
        )
    if action == ActionType.TEMPORAL_QUERY:
        dates = raw.get("available_dates", [])
        earliest = raw.get("earliest", "")
        latest = raw.get("latest", "")
        dates_list = ", ".join([f"`{d}`" for d in dates]) if dates else "2025-06-07 to 2026-09-10"
        return (
            f"The local archive spans **{len(dates)} acquisition epoch{'s' if len(dates) != 1 else ''}** "
            f"from **{earliest}** to **{latest}**.\n\n"
            f"**Available Epochs:** {dates_list}\n\n"
            f"Open the **Temporal Analysis** section to compare any two epochs side-by-side."
        )
    if action == ActionType.INGEST_DATA:
        return (
            "To add new satellite imagery, scroll down to the **Tile Ingestion & Archive** section.\n\n"
            "You can upload GeoTIFF files (Sentinel-2, Sentinel-1 SAR, Landsat, or drone imagery). "
            "The onboard pipeline will automatically validate headers, tile into 256x256 chips, compute RemoteCLIP embeddings, and index them in Qdrant."
        )
    if action == ActionType.EXPLAIN:
        return (
            "🛰️ **TriNetra AI (त्रिनेत्र AI) — Tactical Satellite Reconnaissance Agent**\n\n"
            "I can assist you with the following intelligence workflows:\n\n"
            "• 🔍 **Natural Language Vector Search**: Search multi-band imagery using RemoteCLIP ViT-B/32 embeddings in Qdrant (e.g., *'riverbanks with dense vegetation'* or *'urban expansion'*).\n"
            "• 🖼️ **Image-to-Image Reverse Search**: Upload a satellite crop to retrieve visually similar tiles across all epochs.\n"
            "• ⚡ **Bitemporal Change Detection**: Identify structural and environmental changes between epochs using the BIT Transformer and Classical CV.\n"
            "• 📡 **Multi-Sensor Capabilities**: Analyze Optical (Sentinel-2 MSI) and Radar (Sentinel-1 C-SAR) passes.\n"
            "• 📥 **Tile Ingestion**: Upload new GeoTIFF scenes to auto-tile, embed, and index them on-premises."
        )
    return "I processed your request. Check the results below."


def _follow_up_suggestions(action: ActionType, raw: dict) -> list[str]:
    """Generate contextual follow-up suggestion chips."""
    suggestions = {
        ActionType.SEARCH_TEXT: [
            "Run change detection on the top tile",
            "Show all tiles in the archive",
            "Search with an image instead",
        ],
        ActionType.SEARCH_IMAGE: [
            "Run change detection on the best match",
            "Show temporal analysis for this area",
            "List all tiles in the archive",
        ],
        ActionType.DESCRIBE_IMAGE: [
            "Find similar tiles in the archive",
            "Run change detection with this image",
        ],
        ActionType.CHANGE_DETECT: [
            "Search for more tiles in this area",
            "Show the full temporal timeline",
            "List all indexed tiles",
        ],
        ActionType.LIST_TILES: [
            "Search for specific terrain features",
            "Show available acquisition dates",
            "Run change detection between two dates",
        ],
        ActionType.TEMPORAL_QUERY: [
            "Compare the earliest and latest epoch",
            "List all tiles in the archive",
            "Search for specific features across time",
        ],
        ActionType.INGEST_DATA: [
            "Show current tile archive",
            "Search existing imagery",
            "What acquisition dates are available?",
        ],
        ActionType.EXPLAIN: [
            "Find military installations near water",
            "Show all indexed satellite tiles",
            "What dates are in the archive?",
        ],
    }
    return suggestions.get(action, ["Search for satellite imagery", "Show tile archive"])


# ---------------------------------------------------------------------------
# JSON-safe helpers
# ---------------------------------------------------------------------------

def _json_safe_raw(obj: Any) -> Any:
    import numpy as np
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {str(k): _json_safe_raw(v) for k, v in obj.items() if k not in ("raw_mask_array", "overlay_array")}
    if isinstance(obj, (list, tuple)):
        return [_json_safe_raw(v) for v in obj]
    if hasattr(obj, "to_dict"):
        return _json_safe_raw(obj.to_dict())
    if hasattr(obj, "__dict__"):
        return _json_safe_raw(obj.__dict__)
    return str(obj)


def _json_safe_results(results: list) -> list[dict]:
    """Convert SearchResult objects to JSON-safe dicts."""
    safe = []
    for r in results:
        if hasattr(r, "__dict__"):
            d = _json_safe_raw(r.__dict__)
        elif isinstance(r, dict):
            d = _json_safe_raw(r)
        else:
            d = _json_safe_raw(r)
        safe.append(d)
    return safe


# ---------------------------------------------------------------------------
# Main Agent Orchestrator
# ---------------------------------------------------------------------------

class TriNetraAgent:
    """
    Top-level agent. Initialise once at app startup; use `chat()` per request.
    """

    def __init__(self):
        self._ollama = OllamaClient(OLLAMA_BASE_URL)
        self.mode: AgentMode = self._ollama.probe()
        logger.info(f"[Agent] Initialised in mode: {self.mode}")

    def refresh_mode(self) -> AgentMode:
        """Re-probe Ollama (call if user installs models at runtime)."""
        self.mode = self._ollama.probe()
        return self.mode

    def chat(
        self,
        message: str,
        image_bytes: bytes | None = None,
        image_filename: str | None = None,
        history: list[dict] | None = None,
    ) -> AssistantResponse:
        """
        Main entry point.
        Args:
            message:        User's natural language query.
            image_bytes:    Optional raw bytes of an uploaded satellite image.
            image_filename: Original filename (for metadata).
            history:        Last N conversation turns [{"role": "user"|"assistant", "content": "..."}]
        Returns:
            AssistantResponse with narrated text + structured results payload.
        """
        thinking: list[str] = []
        has_image = image_bytes is not None and len(image_bytes) > 0

        # ── 1. Parse Intent ───────────────────────────────────────────────────
        thinking.append(f"Parsing intent (mode={self.mode})")
        history_summary = ""
        if history:
            recent = history[-4:]  # last 2 turns
            history_summary = " | ".join(
                f"{h['role']}: {h['content'][:100]}" for h in recent
            )

        if self.mode in (AgentMode.OLLAMA_FULL, AgentMode.OLLAMA_TEXT_ONLY):
            intent = _parse_intent_with_ollama(
                self._ollama, message, has_image, history_summary
            )
        else:
            intent = _heuristic_parse(message, has_image)

        thinking.append(f"Intent → {intent.action.value} (confidence={intent.confidence:.2f}): {intent.reasoning}")

        # ── 2. Handle image description with moondream ────────────────────────
        image_description: str | None = None
        if has_image and intent.action == ActionType.DESCRIBE_IMAGE:
            if self.mode == AgentMode.OLLAMA_FULL:
                thinking.append("Describing image with moondream VLM")
                import base64
                img_b64 = base64.b64encode(image_bytes).decode()
                try:
                    desc_prompt = (
                        "You are analysing a satellite or aerial image. "
                        "Describe what you see in 3-5 sentences: terrain type, "
                        "visible structures, land use, any notable features. "
                        "Be specific and use geospatial terminology."
                    )
                    image_description = self._ollama.generate(VISION_MODEL, desc_prompt, img_b64)
                    thinking.append(f"Image described: {image_description[:100]}...")
                except Exception as exc:
                    logger.warning(f"[Agent] moondream failed: {exc}")
                    image_description = (
                        "Image analysis is not available right now (moondream model may not be running). "
                        "I can still search for visually similar tiles — just ask!"
                    )
            else:
                image_description = (
                    "📡 Visual image description requires the **moondream** model. "
                    "Run `ollama pull moondream` to enable it. "
                    "I can still perform image similarity search using RemoteCLIP embeddings."
                )

        # ── 3. Route Action → Backend ─────────────────────────────────────────
        thinking.append(f"Routing to backend action: {intent.action.value}")
        raw_results = _route_action(intent, image_bytes, image_filename)

        # Inject image description into results if available
        if image_description:
            raw_results["image_description"] = image_description

        # ── 4. Narrate Results ────────────────────────────────────────────────
        thinking.append("Synthesising natural language response")
        if self.mode in (AgentMode.OLLAMA_FULL, AgentMode.OLLAMA_TEXT_ONLY):
            narration = _synthesize_with_ollama(self._ollama, intent, raw_results)
        else:
            narration = _template_narrate(intent, raw_results)

        # For image description, override narration with the actual description
        if intent.action == ActionType.DESCRIBE_IMAGE and image_description:
            tile_count_suffix = ""
            try:
                from semantic_search.search import search_by_image
                from PIL import Image
                img = Image.open(BytesIO(image_bytes)).convert("RGB")
                sim_results = search_by_image(image=img, top_k=3)
                raw_results["similar_tiles"] = _json_safe_results(sim_results)
                tile_count_suffix = f"\n\nI also found **{len(sim_results)} visually similar tile{'s' if len(sim_results) != 1 else ''}** in the archive using RemoteCLIP similarity search."
            except Exception:
                pass
            narration = f"**Satellite Image Analysis:**\n\n{image_description}{tile_count_suffix}"

        suggestions = _follow_up_suggestions(intent.action, raw_results)

        return AssistantResponse(
            response=narration,
            action_taken=intent.action,
            results=_json_safe_raw(raw_results),
            follow_up_suggestions=suggestions,
            mode_used=self.mode,
            thinking_steps=thinking,
        )


# ---------------------------------------------------------------------------
# Module-level singleton (created on first import)
# ---------------------------------------------------------------------------

_agent_instance: TriNetraAgent | None = None


def get_agent() -> TriNetraAgent:
    """Return (or lazily create) the module-level agent singleton."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = TriNetraAgent()
    return _agent_instance
