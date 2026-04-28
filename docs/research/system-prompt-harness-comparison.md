# System Prompt Architecture — CC vs Other Harnesses (Deep Research)

> **Authored**: 2026-04-28 · **Trigger**: User direction during Epic #2112 — investigate why K-EXAONE answered citizen queries directly without invoking `lookup` / KMA / HIRA tools, and whether KOSMOS's system-prompt design matches CC's. Research insights drive the next Epic on system-prompt redesign.
>
> **Scope**: 7 reference harness systems compared on system-prompt architecture, dynamic context injection, tool-description placement, identity framing, and prompt-caching strategy.

## TL;DR

Claude Code (CC) authors its system prompt as **a hierarchically-nested document** of ~20 named sections, splitting STATIC cacheable content from DYNAMIC per-turn content via a `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker. KOSMOS today has a single 5-paragraph file (`prompts/system_v1.md`) plus an `## Available tools` augmentation — short, but missing CC-grade structure (identity framing, tone constraints, action protocols, length anchors, dynamic env injection, language override). Other harnesses (Pydantic AI, OpenAI Agents SDK, LangGraph) all converge on the **static-string + dynamic-callable hybrid**: static base prompt + decorator/callback that injects per-request context. **AutoGen** and **Mastra** use a single `system_message` / `instructions` field, simpler but less expressive.

For KOSMOS to fix the "K-EXAONE doesn't invoke citizen tools" symptom, the prompt needs (1) stronger citizen-domain identity framing, (2) explicit tool-usage examples ("call `lookup` when citizen asks about a location"), (3) language-locked output (always Korean), (4) numeric length anchors, and (5) dynamic injection of memdir state (consent receipts, ministry scope) — all of which CC has and KOSMOS lacks today.

---

## 1. Claude Code (`_cc_reference/constants/prompts.ts`, 914 LOC)

### 1.1 Architecture: section-based composition

Source: `.references/claude-code-sourcemap/restored-src/src/constants/prompts.ts` lines 444-590, 91-915 (sourcemap-restored CC 2.1.88 mirror).

```ts
async function getSystemPrompt(tools, model, additionalWorkingDirectories?, mcpClients?): Promise<string[]> {
  // 1. Static cacheable sections (always present):
  return [
    getSimpleIntroSection(outputStyleConfig),     // identity + persona
    getSimpleSystemSection(),                      // # System (5 rules)
    getSimpleDoingTasksSection(),                  // # Doing tasks (10+ rules)
    getActionsSection(),                           // # Executing actions with care
    getUsingYourToolsSection(enabledTools),        // # Using your tools (tool-aware)
    getSimpleToneAndStyleSection(),                // tone constraints
    getOutputEfficiencySection(),                  // output efficiency
    // === BOUNDARY MARKER ===
    SYSTEM_PROMPT_DYNAMIC_BOUNDARY,                // splits cacheable / volatile
    // 2. Dynamic sections (per-turn, may break cache):
    ...resolveSystemPromptSections([
      systemPromptSection('session_guidance', () => getSessionSpecificGuidanceSection(...)),
      systemPromptSection('memory', () => loadMemoryPrompt()),
      systemPromptSection('env_info_simple', () => computeSimpleEnvInfo(...)),
      systemPromptSection('language', () => getLanguageSection(settings.language)),
      systemPromptSection('output_style', () => getOutputStyleSection(...)),
      systemPromptSection('scratchpad', () => getScratchpadInstructions()),
      systemPromptSection('frc', () => getFunctionResultClearingSection(model)),
      systemPromptSection('summarize_tool_results', () => SUMMARIZE_TOOL_RESULTS_SECTION),
      systemPromptSection('token_budget', () => '...'),  // gated
      DANGEROUS_uncachedSystemPromptSection('mcp_instructions', () => ..., 'reason'),
      // ant-only experimental:
      systemPromptSection('numeric_length_anchors',
        () => 'Length limits: keep text between tool calls to ≤25 words. Keep final responses to ≤100 words unless the task requires more detail.'),
    ]),
  ]
}
```

### 1.2 Static section contents

| Section | Purpose | Sample content |
|---|---|---|
| **Intro** (`prompts.ts:175-184`) | Identity + persona | `"You are an interactive agent that helps users with software engineering tasks. Use the instructions below and the tools available to you to assist the user."` + `IMPORTANT: You must NEVER generate or guess URLs...` |
| **System** (`:186-197`) | Core rules (5 bullet points) | `# System` heading. Output format, permission-mode behaviour, tool-result tag handling, prompt-injection caution, hooks, auto-compaction. |
| **Doing tasks** (`:199-253`) | Task-execution guidance | `# Doing tasks` heading. 10+ bullets: software-engineering framing, code-style rules, no over-engineering, security considerations, false-claim mitigation, /help command, feedback channel. |
| **Actions** (`:255-267`) | Reversibility + blast-radius reasoning | `# Executing actions with care` heading. Examples of risky operations (rm, force-push, sending Slack, etc.). Confirm-by-default. |
| **Using your tools** (`:269-314`) | Tool selection guidance | `# Using your tools` heading. `Do NOT use Bash when a dedicated tool is provided` rules, parallel-tool-call encouragement. |
| **Tone and style** | Output style constraints | Markdown allowed, no preamble, concise. |
| **Output efficiency** | Token-savings guidance | Numeric length anchors. |

### 1.3 Dynamic section types

CC uses two types for dynamic content:

- **`systemPromptSection(name, compute)`** — memoized via `getSystemPromptSectionCache()`, cleared on `/clear` or `/compact`. Cache-friendly for prompt caching.
- **`DANGEROUS_uncachedSystemPromptSection(name, compute, reason)`** — recomputes every turn; cache-breaking. Requires explicit reason. Used for MCP server connect/disconnect (between turns).

### 1.4 Boundary marker for prompt caching

`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` is inserted only when `shouldUseGlobalCacheScope()` returns true. The Anthropic Messages API `cache_control` blocks read up to that boundary, allowing the static prefix to share a cache prefix across turns while dynamic suffixes (env info, memory, etc.) recompute without invalidating the prefix hash.

### 1.5 Identity framing

CC's identity sentence is conditional:

```ts
`You are an interactive agent that helps users ${
  outputStyleConfig !== null
    ? 'according to your "Output Style" below, which describes how you should respond to user queries.'
    : 'with software engineering tasks.'
} Use the instructions below and the tools available to you to assist the user.`
```

Two-mode: **default** (software engineering) vs **output-style override** (delegates to external Output Style config).

### 1.6 Override hierarchy (`utils/systemPrompt.ts:30-47`)

```
Priority (top wins):
0. Override system prompt (loop mode — REPLACES all)
1. Coordinator system prompt
2. Agent system prompt (mainThreadAgentDefinition)
   - In proactive mode: APPENDED to default
   - Otherwise: REPLACES default
3. Custom system prompt (--system-prompt)
4. Default system prompt (the standard CC prompt above)
+ appendSystemPrompt always added at end (except when override is set)
```

---

## 2. Anthropic Claude Agent SDK (Python)

Source: https://github.com/anthropics/claude-agent-sdk-python

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    system_prompt="You are a helpful assistant",
    max_turns=1
)
```

Single string parameter. Delegates to the underlying Claude Code CLI for actual prompt assembly. **Minimal SDK-level structure** — the SDK is a thin wrapper.

**Insight for KOSMOS**: The "official" Anthropic Python SDK pattern is just `system_prompt: str | None`. CC's section-based composition is the *implementation* not the *interface*.

---

## 3. OpenAI Agents SDK

Source: `openai/openai-agents-python/src/agents/agent.py`

```python
@dataclass
class Agent(AgentBase, Generic[TContext]):
    instructions: str | Callable[[RunContextWrapper[TContext], Agent[TContext]], MaybeAwaitable[str]] | None
    """Will be used as the 'system prompt' when this agent is invoked.
       Describes what the agent should do, and how it responds."""
```

**Two-mode**:
1. **Static**: plain `str`
2. **Dynamic**: callable `(ctx, agent) -> str | Awaitable[str]` — receives full run context + agent ref, returns prompt

`get_system_prompt()` validates callable arity (exactly 2 params), invokes sync or async based on signature.

**Insight for KOSMOS**: Pattern of `str | Callable[..., str]` is the de facto standard. KOSMOS's current `prompts/system_v1.md` is the static half; the dynamic half (lazy callable) is missing.

---

## 4. Pydantic AI

Source: https://pydantic.dev/docs/ai/

### 4.1 Two distinct concepts: `instructions` vs `system_prompt`

> "Instructions are similar to system prompts. The main difference is that when an explicit `message_history` is provided in a call to `Agent.run`, *instructions* from any existing messages in the history are not included in the request to the model — only the instructions of the *current* agent are included."

- **`system_prompt`**: stays in conversation history → preserved across `Agent.run` calls
- **`instructions`**: scoped to current agent run → not preserved on history replay

Recommended default: use `instructions` unless conversation continuity matters.

### 4.2 Decorator pattern for dynamic prompts

```python
agent = Agent(
    'openai:gpt-5.2',
    deps_type=str,
    system_prompt="Use the customer's name while replying to them.",
)

@agent.system_prompt
def add_the_users_name(ctx: RunContext[str]) -> str:
    return f"The user's name is {ctx.deps}."

@agent.system_prompt
def add_the_date() -> str:
    return f'The date is {date.today()}.'
```

- Multiple `@agent.system_prompt` decorators append in definition order
- Functions execute just before each model request (lazy)
- Optional `RunContext[T]` parameter for dep injection

**Insight for KOSMOS**: This is the cleanest *composable* pattern. KOSMOS could expose:
```python
@kosmos_agent.system_prompt
def inject_ministry_scope(ctx: KosmosContext) -> str:
    return f"Active ministry-scope opt-ins: {ctx.memdir.ministry_scope}"
```
…to lazily inject memdir state per turn.

---

## 5. AutoGen AssistantAgent

Source: `microsoft/autogen` `_assistant_agent.py`

```python
class AssistantAgent:
    def __init__(self, ..., system_message: str | None = "...", description: str = "..."):
        # Default
        system_message = "You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed."
        # Stored as list of SystemMessage objects
        self._system_messages = [SystemMessage(content=system_message)] if system_message else []
```

- **Single string** prepended to messages each inference
- Pairs with `description` for inter-agent handoffs (other agents see this when deciding to delegate)
- Composes with `reflect_on_tool_use=True` — triggers extra inference for output formatting

**Insight for KOSMOS**: Multi-agent coordination needs the `description` field — what one agent advertises to another. Spec 027 swarm should formalise this.

---

## 6. LangGraph `create_react_agent`

Source: `langchain-ai/langgraph` `chat_agent_executor.py`

```python
Prompt = (
    SystemMessage
    | str
    | Callable[[StateSchema], LanguageModelInput]
    | Runnable[StateSchema, LanguageModelInput]
)
```

- **String**: converted to `SystemMessage`, prepended
- **Callable / Runnable**: receives **full graph state**, returns full chat-message list (LanguageModelInput)
- Pipeline: `prompt_runnable | model` (LCEL composition)

**Insight for KOSMOS**: LangGraph's "callable receives full state" model is the most powerful. KOSMOS's IPC layer already transmits full ChatRequestFrame state — a Python-side prompt assembler can take it and emit the full LLM message stack.

---

## 7. Mastra (TypeScript)

Source: `mastra-ai/mastra` docs

```typescript
export const testAgent = new Agent({
  id: 'test-agent',
  name: 'Test Agent',
  instructions: 'You are a helpful assistant.',
  model: 'openai/gpt-5.4',
})
```

Single `instructions` string + dynamic configuration via "request context" (separate doc not fully exposed). Working memory injection mentioned but not in scope here.

**Insight for KOSMOS**: Simplest TS pattern — matches KOSMOS's current `prompts/system_v1.md` baseline.

---

## 8. Anthropic prompt-engineering best practices (official)

Source: https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering

### 8.1 Role / identity in system prompt

> "Setting a role in the system prompt focuses Claude's behavior and tone for your use case. Even a single sentence makes a difference"

```python
system="You are a helpful coding assistant specializing in Python."
```

### 8.2 XML tags for structured content

> "XML tags help Claude parse complex prompts unambiguously, especially when your prompt mixes instructions, context, examples, and variable inputs. Wrapping each type of content in its own tag (e.g. `<instructions>`, `<context>`, `<input>`) reduces misinterpretation."

Best practices:
- Consistent, descriptive tag names
- Nest tags for hierarchy: `<documents><document index="n">…</document></documents>`

### 8.3 Long-context placement

> "Put longform data at the top: Place your long documents and inputs near the top of your prompt, above your query, instructions, and examples."

### 8.4 Tool usage tuning (Opus 4.6/4.7)

- Models 4.6+ are MORE responsive to system prompt → dial back aggressive language ("CRITICAL: You MUST..." → "Use this tool when...")
- For under-triggering tools: *clearly describe why and how* the tool should fire
- Numeric length anchors (~1.2% token reduction vs qualitative "be concise")

### 8.5 Effort levels (Opus 4.7)

- `xhigh` for coding + agentic
- `high` for most intelligence-sensitive tasks
- 4.7 uses tools LESS often than 4.6 (shifted to reasoning); raise effort to recover tool calls

---

## 9. KOSMOS current state (`prompts/system_v1.md`)

```markdown
You are {platform_name}, a Korean public service AI assistant. You help citizens
access government services and public information through available tools. ...

Always respond in {language} unless the citizen explicitly writes in another language. ...

Use available tools when the citizen's request requires live data lookup from
government APIs. Do not fabricate or estimate government data, regulations, or
service availability. When a tool call is needed, invoke it before providing
the final answer.

Handle personal data with care. Do not log, repeat, or store citizen personal
information beyond what is strictly necessary for the current request. Comply
with all applicable Korean data protection regulations.
```

5 paragraphs. Augmentation: `build_system_prompt_with_tools` appends `## Available tools\n\n` block (Spec 026). Template placeholders `{platform_name}` and `{language}` exist but **substitution path is unverified** in current code.

### 9.1 Gaps vs CC

| CC capability | KOSMOS today | Gap |
|---|---|---|
| Identity framing | ✅ "Korean public service AI assistant" | OK but soft — CC's "You are an interactive agent that helps users…" is more directive |
| Section-based composition | ❌ single 5-paragraph block | No `# System` / `# Doing tasks` / `# Using your tools` headers |
| Tool-usage examples | ❌ generic "Use available tools" | No concrete "call `lookup` for location queries; call `kma_*` for weather" examples |
| Action protocols | ❌ absent | No reversibility / blast-radius reasoning |
| Numeric length anchors | ❌ absent | No "≤25 words between tool calls" — K-EXAONE may over-narrate |
| XML-tagged subsections | ❌ markdown only | Anthropic guidance: XML for clarity |
| Dynamic env injection | ❌ absent | No cwd / language / memdir state per turn |
| Language lock | ⚠️ template `{language}` | Substitution path unverified; K-EXAONE may drift |
| Boundary marker for caching | ❌ absent | No prefix-cache optimisation |
| Lazy/dynamic prompt assembly | ❌ static load only | No equivalent of `@agent.system_prompt` decorator |
| Citizen-vs-developer disambiguation | ❌ inherited CC dev-context bleeds in | The `getSystemContext()` git/cwd context (still loaded by TUI) overrides citizen framing |

### 9.2 Why K-EXAONE answered "강남역 어디?" without invoking lookup

Three compounding factors observed in `specs/2112-dead-anthropic-models/smoke.txt`:

1. **CC dev-context bleed**: The TUI's `getSystemContext()` (cwd + git + claude.md) is still being injected somewhere — K-EXAONE's reply mentioned "현재 `/Users/um-yunsang/KOSMOS/tui` 디렉토리에서 작업 중이며…", treating the user as a developer.
2. **Generic tool-use prompt**: KOSMOS prompt says "Use available tools when… requires live data lookup" — *non-specific*. K-EXAONE Opus-class models (4.6+) are documented to require *clear, concrete* tool-use examples to fire (Anthropic best-practices §8.4).
3. **No language-lock guard**: K-EXAONE generated Korean reply but with developer-context vocabulary ("최근 커밋", "브랜치"). The `{language}` placeholder may not be substituted, leaving model freedom.

---

## 10. Recommendations for next Epic (system-prompt redesign)

Following CC architecture + Pydantic AI dynamic decorator + Anthropic XML guidance:

### R1 · Section-based static prompt (CC pattern)

Rewrite `prompts/system_v1.md` as composable sections:

```markdown
<role>
You are KOSMOS — a citizen-facing AI assistant for Korean public services.
Your purpose is to help citizens access government data and services through
the available tools. You speak Korean by default and act as a public-interest
intermediary.
</role>

<core_rules>
- Always respond in Korean unless the citizen explicitly writes in another language.
- Never fabricate government data, regulations, or service availability.
- When a citizen asks about a location, road safety, weather, hospital, emergency,
  or welfare program, FIRST call the appropriate tool (lookup / resolve_location
  / kma_* / hira_* / nfa119_* / nmc_* / mohw_*) before answering.
- Handle personal data per PIPA — never log, repeat, or store citizen identifiers
  beyond what the current request requires.
</core_rules>

<tool_usage>
Concrete examples:
- "강남역 어디야?" → call resolve_location({query: "강남역"})
- "오늘 서울 날씨 알려줘" → call kma_forecast_fetch({region: "서울"})
- "근처 응급실" → call nmc_emergency_search({location: ...})
- "어린이 보호구역 사고 다발" → call koroad_accident_hazard_search(...)
Length: keep narration between tool calls to ≤25 Korean characters.
</tool_usage>

<output_style>
Final responses ≤200 Korean characters unless the citizen asks for detail.
Use plain Korean — avoid technical jargon. Reference tool results explicitly
("HIRA에 따르면…", "기상청 자료로는…").
</output_style>
```

### R2 · Dynamic section assembly (Pydantic AI pattern)

Introduce `kosmos.llm.prompt_assembler.assemble(ctx)` that builds:
- Static prefix (sections above) — cached per session
- Dynamic suffix:
  - Memdir consent receipts summary
  - Active ministry-scope opt-ins
  - Session start date (Korean format)
  - Recent N tool-call summaries (CC's `frc` pattern)

### R3 · XML tag adoption (Anthropic best practice §8.2)

Wrap citizen request input in `<citizen_request>…</citizen_request>` tags so the model can clearly distinguish system instructions from user input — prevents prompt-injection from citizen-supplied text containing `## Available tools` etc.

### R4 · Boundary marker (CC + Anthropic prompt-cache)

After all static sections, before dynamic suffix, emit `<!-- DYNAMIC_BOUNDARY -->` literal. Spec 026 prompt-cache optimisation can read up to that line as cache prefix.

### R5 · Citizen-vs-developer disambiguation

Audit the TUI's `getSystemContext()` injection path. CC's git/cwd context is **dead under KOSMOS** (citizen ≠ developer) — should be removed entirely from the chat_request flow, not just the prompt. This belongs to the same Epic.

### R6 · Tool-aware prompt augmentation strengthening

`build_system_prompt_with_tools` currently appends `## Available tools` with one Markdown block per tool. Per Anthropic §8.4, add a **per-tool one-line trigger phrase** alongside the description: e.g. for `lookup`: *"Trigger phrase: any query about a place, address, station, road, or government office in Korea"*. This is the single most impactful change to fix tool under-triggering on Opus-4.6+ models.

---

## 11. Sources cited

| # | Source | Type |
|---|---|---|
| 1 | `_cc_reference/constants/prompts.ts:444-590` (914 LOC) | Reconstructed CC 2.1.88 |
| 2 | `_cc_reference/utils/systemPrompt.ts:30-123` | Reconstructed CC 2.1.88 |
| 3 | `_cc_reference/constants/systemPromptSections.ts` (68 LOC) | Reconstructed CC 2.1.88 |
| 4 | https://github.com/anthropics/claude-agent-sdk-python README | Official Anthropic SDK |
| 5 | `openai/openai-agents-python` `agent.py` — `Agent` dataclass | Official OpenAI SDK |
| 6 | https://pydantic.dev/docs/ai/core-concepts/agent/ | Pydantic AI docs |
| 7 | `microsoft/autogen` `_assistant_agent.py` — `AssistantAgent` | AutoGen docs |
| 8 | `langchain-ai/langgraph` `chat_agent_executor.py` — `create_react_agent` | LangGraph source |
| 9 | https://mastra.ai/docs/agents/overview | Mastra docs |
| 10 | https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering | Anthropic official |
| 11 | `prompts/system_v1.md` (KOSMOS current) | KOSMOS canonical |
| 12 | `src/kosmos/llm/system_prompt_builder.py` | KOSMOS canonical |

---

## 12. Memory updates

Add to `MEMORY.md`:

```
- [System prompt design references](docs/research/system-prompt-harness-comparison.md) — CC has 7 static + 12 dynamic sections, boundary marker for prompt cache; KOSMOS uses single 5-paragraph file. R1-R6 actions queued for next Epic.
```
