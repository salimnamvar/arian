# Arian Competitors

**Last updated:** 2026-07-22 (updated with new competitors)

Arian generates LLM-optimized context from source code repositories — intelligently selecting, compressing, and organizing code so language models get the most relevant information within token limits.

## Competitor Landscape

### Tier 1 — Direct Competitors (Repo-to-LLM Context Tools)

| Tool | Stars | Language | Key Differentiator |
|------|-------|----------|--------------------|
| [Repomix](https://github.com/yamadashy/repomix) | 27.3k | TypeScript | Packs entire repo into single AI-friendly file. Tree-sitter compression, XML/MD/TXT output, MCP server, browser extension. Most popular in this space. |
| [Gitingest](https://github.com/coderamp-labs/gitingest) | 15.2k | Python | Replace "hub" with "ingest" in any GitHub URL. Web + CLI + Python package. Web interface, FastAPI backend. |
| [Aider (repo-map)](https://github.com/paul-gauthier/aider) | ~25k | Python | Built-in repo-map feature that generates ranked repository maps via tree-sitter + PageRank. Not standalone but widely used. |
| [Sigmap](https://github.com/manojmallick/sigmap) | 599 | JavaScript | 97% token reduction, zero deps, 33 languages, MCP server. Code signatures for AI grounding. |
| [promptext](https://github.com/1broseidon/promptext) | 22 | Go | Smart code context extractor. Token-aware, CLI tool for AI assistants. |
| [TLDR](https://github.com/parcadei/llm-tldr) | 1,169 | Python | 95% token savings, 5 analysis layers (structure, call graph, complexity, data flow, dependencies). Semantic search with embeddings. 16 languages. (Archived) |
| [Context7](https://github.com/upstash/context7) | 59.6k | TypeScript | Up-to-date code documentation for LLMs. Pulls latest docs for libraries/packages. MCP server, resolves "no-docs" problem. |
| [Claude Context](https://github.com/zilliztech/claude-context) | 12.2k | TypeScript | Code search MCP for Claude Code. Makes entire codebase the context for any coding agent. Vector search. |

### Tier 2 — Code Context MCP Servers

| Tool | Stars | Language | Key Differentiator |
|------|-------|----------|--------------------|
| [Codanna](https://github.com/bartolli/codanna) | 711 | Rust | Local code intelligence MCP server. Symbol search, call graphs, semantic search. |
| [SDL-MCP](https://github.com/GlitterKill/sdl-mcp) | 449 | TypeScript | Symbol Delta Ledger — policy-centered context budget layer. Symbol-graph intelligence + precision tools. |
| [DeepContext MCP](https://github.com/Wildcard-Official/deepcontext-mcp) | 275 | TypeScript | Symbol-aware semantic search for Claude Code/Codex. Vector database-backed. |
| [Code Context Engine](https://github.com/elara-labs/code-context-engine) | 368 | Python | 94% token savings. Index codebase, agents search instead of reading files. Works with Claude/Codex/Copilot/Cursor. |
| [MegaMemory](https://github.com/0xK3vin/MegaMemory) | 289 | TypeScript | Persistent project knowledge graph. Semantic search, in-process embeddings, web explorer. |
| [prompt-tower](https://github.com/backnotprop/prompt-tower) | 383 | TypeScript | VS Code extension. Context management for long-context LLMs, structured AI-XML context. |
| [ContextForge](https://github.com/Yabuku-xD/contextforge) | N/A | TypeScript | MCP server + CLI + Claude Code plugin. Mempalace layered memory, impact analysis, multi-repo workflows, session continuity. |
| [ContextVC](https://github.com/HaochengLu/contextvc) | 153 | Rust | Git-native context control plane. Agent memory as repo infrastructure, CI guard, pre-action gates, semantic merge. |
| [ContextAtlas](https://github.com/codefromkarl/ContextAtlas) | 29 | TypeScript | Hybrid retrieval (vector + FTS5), project memory, retrieval observability, cross-project hub. |
| [ctxl](https://github.com/szaher/contextual) | N/A | TypeScript | `.ctxl` index system, multi-agent conflict resolution, spec-kit bridge, PR context generation, 16 MCP tools. |
| [context-fabrica](https://github.com/TaskForest/context-fabrica) | 8 | Python | Governed memory with temporal recall, provenance-backed synthesis, knowledge graph, curated memory tiers. |
| [Context Mode](https://github.com/mksglu/context-mode) | 19.2k | TypeScript | Context window optimization for AI agents. Sandboxes tool output (98% reduction), persists session memory, enforces routing across 17 platforms via MCP + hooks. |
| [Codesight](https://github.com/Houseofmvps/codesight) | 1.2k | TypeScript | Universal AI context generator. Saves thousands of tokens per conversation in Claude Code, Cursor, Copilot, Codex. |
| [Octocode](https://github.com/bgauryy/octocode) | 897 | TypeScript | Code research platform for AI agents: local + GitHub search, LSP semantics, AST patterns, compact context. MCP or CLI. |
| [Ref Tools MCP](https://github.com/ref-tools/ref-tools-mcp) | 1.1k | TypeScript | Helping coding agents never make mistakes working with public/private libraries without wasting context window. |
| [Entroly](https://github.com/juyterman1000/entroly) | 428 | Python | Auditable context engineering for AI agents: context optimization, recoverable context compression, receipts, answer verification, MCP for Claude Code, Codex, OpenClaw. |

### Tier 3 — Code Indexing Tools

| Tool | Stars | Language | Key Differentiator |
|------|-------|----------|--------------------|
| [CodeGraph](https://github.com/codegraph-ai/CodeGraph) | 44 | C | Semantic graph of codebase — functions, classes, imports, call chains. 42 MCP tools, 38 languages, VS Code extension. |
| [srclight](https://github.com/srclight/srclight) | 52 | Python | Deep code indexing MCP server. Hybrid FTS5 + embedding search, call graphs, git blame/hotspots. 10 languages via tree-sitter. |
| [AiDex](https://github.com/CSCSoftware/AiDex) | 39 | TypeScript | MCP server for persistent code indexing. 50x less context than grep. |
| [codexray](https://github.com/iohub/codexray) | 59 | Rust | Repository-aware, knowledge-learning local MCP. Hybrid semantic + full-text engine. |
| [CodeStory](https://github.com/TheGreenCedar/CodeStory) | 33 | Rust | Codebase grounding engine. Preindexes code into knowledge graph, enriches with semantic context. |
| [LLM-Context-Manager](https://github.com/senoldogann/LLM-Context-Manager) | 61 | Rust | Knowledge Graph navigation, graph-RAG, blast radius analysis, call chain tracing. 8 languages via tree-sitter. |
| [Probe](https://github.com/probelabs/probe) | 665 | Rust | AI-friendly semantic code search engine. Combines ripgrep speed with tree-sitter AST parsing. Powers AI coding assistants with precise, context-aware code understanding. |
| [Code Review Graph](https://github.com/tirth8205/code-review-graph) | 25.2k | Python | Local-first code intelligence graph for MCP and CLI. Builds persistent map of codebase, benchmarked context reductions on reviews and large-repo workflows. |

### Tier 4 — Repo Flattening / Export Tools

| Tool | Stars | Language | Key Differentiator |
|------|-------|----------|--------------------|
| [ai-context](https://github.com/Tanq16/ai-context) | 176 | Go | CLI tool to produce MD context files from many sources. GitHub, YouTube, webpages, code. |
| [Gitingest Extension](https://github.com/coderamp-labs/gitingest-extension) | 223 | TypeScript | Browser extension for Gitingest — one-click repo extraction. |
| [cli-repo-to-prompt](https://github.com/yigitkonur/cli-repo-to-prompt) | 53 | TypeScript | Export any codebase to a single LLM-ready markdown prompt. |
| [CodeContext](https://github.com/DavidVeksler/CodeContext) | 20 | C# | CLI tool & MCP server that turns codebase into text for LLMs. |
| [pack-my-code](https://github.com/Water-Run/pack-my-code) | 9 | Lua | Tiny binary tool that packages project code for LLM consumption. |
| [repo2GPT](https://github.com/alexkorol/repo2GPT) | 10 | Python | Clone GitHub repo, flatten into file-tree + single consolidated code file. |
| [CodePrimer](https://github.com/codeprimer/codeprimer) | N/A | TypeScript | Generates context files for 10+ AI tools (Claude, Cursor, Copilot, Gemini, Windsurf, etc.). AST + LLM hybrid. |
| [Contexta](https://github.com/pablokaua03/contexta) | 8 | Python | GUI + CLI context packs. Task-aware, 5 compression modes, project fingerprinting, token guidance. |
| [Hierarchical Context Compressor](https://github.com/reyavir/hierarchical-context-compressor) | N/A | Python | Generates `agents.md` + `AGENTS.md` hierarchy via LLM. GitHub Actions support, template system. |
| [RepoLens](https://github.com/richardogoma/RepoLens) | N/A | Python | OR-Tools CP-SAT optimization for budgeted file selection. Coverage constraints, role labeling. |
| [tokmd](https://github.com/EffortlessMetrics/tokmd) | N/A | Rust | Deterministic receipts, policy gates, handoff bundles. Multi-surface: CLI, Rust, Python, Node, WASM. |
| [Flatcode](https://github.com/jaywang98/flatcode) | New | Python | Smart CLI tool to flatten project repository into single, token-efficient context file for LLM analysis. |
| [repo2txt](https://github.com/jimfilippou/repo2txt) | 20 | TypeScript | Dead simple CLI to convert any project folder into text file, useful for AI prompts. |
| [Repo-Prompt](https://github.com/Will282/repo-to-prompt) | 4 | Python | Converts local/remote Git repos into token-limited structured files for generative AI models. |
| [Repo Prompt](https://github.com/AIKEWA/repo-prompt) | 5 | Python | GPT-powered prompt generation, code auditing, cognitive AI support for local workflows. |
| [RepoRAG](https://github.com/ahammadnafiz/RepoRAG) | 5 | Python | Interactive tool for GitHub repository prompt generation and RAG workflows. |

### Tier 5 — Code Indexing / Search MCPs

| Tool | Stars | Language | Key Differentiator |
|------|-------|----------|--------------------|
| [ai-code-context-helper](https://github.com/sansan0/ai-code-context-helper) | 235 | Python | Desktop tool (tkinter). Visualize project structure, export files for AI assistants. |
| [context-router](https://github.com/mohankrishnaalavala/context-router) | 10 | Python | Memory-aware context engine. 91% fewer tokens, 17/18 rank-1 across 6 OSS projects. |
| [deep-init](https://github.com/deepfusionlabs/deep-init) | 6 | Python | Claude Code plugin. Writes grounded, verified context — every claim checked against code. |
| [dummyIndex](https://github.com/MullaAhmed/dummyIndex) | 9 | Python | Persistent context engine for Claude Code. AST backbone + multi-agent council. |

### Tier 6 — Emerging Tools (MCP-focused)

| Tool | Stars | Language | Key Differentiator |
|------|-------|----------|--------------------|
| [Pydantic DeepAgents](https://github.com/vstorm-co/pydantic-deepagents) | 990 | Python | Open-source Claude Code alternative. Tool-calling, sandboxed execution, multi-agent teams, skills, checkpoints. |
| [Continuous Claude v3](https://github.com/parcadei/Continuous-Claude-v3) | 3.9k | Python | Context management with hooks, ledgers, handoffs. Agent orchestration with isolated context windows. |
| [Storybloq](https://github.com/Storybloq/storybloq) | 675 | TypeScript | Cross-session context for Claude Code. CLI + MCP server + /story skill tracking tickets, issues, handovers. |
| [OpenContext](https://github.com/0xranx/OpenContext) | 661 | JavaScript | Personal context store for AI agents — reuse existing coding agent CLI with built-in skills/tools. |
| [Overture](https://github.com/SixHq/Overture) | 627 | TypeScript | Visual execution plan mapping for AI coding agents as interactive flowchart before code generation. |

## Arian's Differentiators vs. Competitors

| Feature | Arian | Repomix | Gitingest | Sigmap | Context7 | Claude Context | Code Review Graph |
|---------|-------|---------|-----------|--------|----------|--------------|-------------------|
| **Task-aware file selection** | ✅ (bug_fix, feature, review, etc.) | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ (review focus) |
| **Token budget enforcement** | ✅ | ⚠️ (counting only) | ⚠️ (counting only) | ❌ | ❌ | ❌ | ✅ |
| **Smart compression (4 levels)** | ✅ Full → Signatures → Structure → Summary | ⚠️ Tree-sitter compression | ❌ | ⚠️ Code signatures | ❌ (doc focus) | ❌ | ✅ |
| **Python AST analysis** | ✅ Deep symbol extraction | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Architectural role classification** | ✅ (readme, test, domain, service, infra) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Merged/separate/grouped output** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **CLI + Python package** | ✅ | ✅ (CLI + npm + web) | ✅ (CLI + Python + web) | ✅ (CLI) | ✅ (MCP) | ✅ (MCP) | ✅ (MCP + CLI) |
| **MCP server** | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Web interface** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Browser extension** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

## Key Trends

1. **MCP server adoption** — Most competitors are adding Model Context Protocol servers for direct agent integration
2. **Tree-sitter everywhere** — Universal code parsing is table stakes
3. **Token reduction focus** — Sigmap (97%), Code Context Engine (94%), context-router (91%), TLDR (95%) all claim massive reductions
4. **Web interfaces** — Repomix and Gitingest both offer hosted web versions
5. **Multi-output formats** — XML, Markdown, JSON, plain text — flexibility matters
6. **Security checking** — Repomix integrates Secretlint; this is becoming expected
7. **Multi-tool context generation** — CodePrimer generates context for 10+ AI tools simultaneously
8. **Git-native context** — ContextVC treats agent memory as versioned repo infrastructure
9. **Persistent memory/session continuity** — ContextForge, ctxl, context-fabrica offer cross-session memory
10. **Hierarchical context** — HCC and Contexta generate per-directory context files
11. **Optimization-based selection** — RepoLens uses OR-Tools for budgeted file selection under constraints
12. **Documentation grounding** — Context7 (59.6k stars) pulls up-to-date docs for libraries, solving the "no-docs" problem
13. **Context window optimization** — Context Mode (19.2k stars) focuses on 98% reduction via sandboxing and output routing
14. **Semantic code search** — Probe and claude-context provide ripgrep-speed AST-aware search for agents
15. **Local-first graphs** — Code Review Graph and others use persistent knowledge graphs for codebase understanding

## Potential Gaps Arian Could Fill

- **MCP server** — Arian lacks one; most competitors now offer this
- **Web interface** — A hosted version would increase discoverability
- **Multi-language AST** — Currently Python-focused; expanding to JS/TS/Rust via tree-sitter would match competitors
- **Task-aware compression** — Unique selling point; competitors don't adapt compression to task type
- **Token budget as first-class feature** — Hard limit enforcement is rare and valuable
- **Multi-tool context generation** — CodePrimer generates for 10+ tools; Arian could target multiple AI tools
- **Persistent memory** — ContextForge and ctxl offer cross-session memory; Arian could add session continuity
- **Git-native integration** — ContextVC version-controls agent memory; Arian could integrate with git workflows
- **GUI/visual interface** — Contexta offers desktop GUI; Arian could add visual context building
- **Optimization-based selection** — RepoLens uses constraint optimization; Arian could adopt similar algorithms
- **Documentation grounding** — Context7 pulls up-to-date docs; Arian could integrate external docs
- **Semantic search engine** — Probe and claude-context offer ripgrep-speed AST search; Arian could add discovery workflow
