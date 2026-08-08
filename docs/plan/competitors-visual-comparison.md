# Arian Competitor Analysis - Visual Comparison

**Date:** 2026-07-23  
**Status:** Complete  
**Analyst:** Mistral Vibe

---

## Table of Contents

1. [Market Overview Charts](#market-overview-charts)
2. [Adoption Metrics](#adoption-metrics)
3. [Feature Comparison Dashboard](#feature-comparison-dashboard)
4. [Technical Capabilities Matrix](#technical-capabilities-matrix)
5. [Token Reduction Benchmarks](#token-reduction-benchmarks)
6. [Integration Ecosystem](#integration-ecosystem)
7. [Arian Positioning Visuals](#arian-positioning-visuals)

---

## Market Overview Charts

### Market Share by Adoption (GitHub Stars)

```
Total Competitors Analyzed: 60+
Tier 1 (Deep Dive): 8 tools
Tier 2 (MCP Servers): 14 tools  
Tier 3-6 (Overview): 46 tools
```

#### Stars Distribution (Log Scale)
```
Aider (47.6k)          █████████████████████████████████ 47,600
Context7 (59.6k)       ██████████████████████████████████████ 59,600
Repomix (27.3k)        ████████████████████████                27,300
Claude Context (12.2k) ██████████████                          12,200
Gitingest (15.2k)      ████████████████                        15,200
Sigmap (599)           ████                                      599
TLDR (1,169)          ███████                                  1,169
Promptext (22)         █                                      22
```

#### Market Segmentation
```
┌─────────────────────────────────────────────────────────────┐
│                    COMPETITOR MARKET MAP                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  HIGH ADOPTION         Context7 (59.6k)   Aider (47.6k)     │
│  HIGH FEATURES          Repomix (27.3k)                       │
│                         Gitingest (15.2k)                     │
│                                                          Claude │
│                        Context (12.2k)                       │
│                                                              │
│  ┌─────────────────┬───────────────────────────────────┐   │
│  │                 │                               │       │   │
│  │  MEDIUM ADOPTION│          TECHNICAL INNOVATORS      │   │
│  │                 │                               │       │   │
│  │  Codanna (711)   │        Sigmap (599)                 │   │
│  │  SDL-MCP (449)   │        TLDR (1,169) ARCHIVED        │   │
│  │  Code Context    │        Probe, CodeGraph             │   │
│  │  Engine (368)    │                               │       │   │
│  │                 │                               │       │   │
│  └─────────────────┴───────────────────────────────────┘   │
│                                                              │
│  LOW ADOPTION          Promptext (22), ContextForge,       │
│  EMERGING              context-fabrica, Entroly, etc.      │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                    ARIAN POSITION                       │ │
│  │  █ Unique: Task-aware selection + Python AST           │ │
│  │  █ Gaps: MCP, Web UI, Multi-language                   │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Adoption Metrics

### Top 10 by GitHub Stars

| Rank | Tool | Stars | Forks | Category | Status |
|------|------|-------|-------|----------|--------|
| 1 | Context7 | 59,600 | 2,900 | Library Docs | Active |
| 2 | Aider | 47,600 | 4,700 | AI Pair Programming | Active |
| 3 | Repomix | 27,300 | 1,400 | Repo Context | Active |
| 4 | Gitingest | 15,200 | 1,100 | Repo Digest | Active |
| 5 | Claude Context | 12,200 | 903 | Vector Search | Active |
| 6 | Context Mode | 19,200 | N/A | Context Optimization | Active |
| 7 | Codesight | 1,200 | N/A | Universal Context | Active |
| 8 | TLDR | 1,169 | 115 | Deep Analysis | **ARCHIVED** |
| 9 | Octocode | 897 | N/A | Code Research | Active |
| 10 | Ref Tools MCP | 1,100 | N/A | Library Context | Active |

### Adoption Heatmap by Tier

```
Tier 1 (Direct Competitors):
├── High Adoption (10k+): Repomix, Gitingest, Aider, Context7, Claude Context
├── Medium Adoption (1k-10k): TLDR
└── Low Adoption (<1k): Sigmap, Promptext

Tier 2 (MCP Servers):
├── High Adoption (1k+): Context Mode, Codesight, Ref Tools, Octocode
├── Medium Adoption (100-1k): Codanna, SDL-MCP, DeepContext, Code Context Engine, MegaMemory, prompt-tower, ContextVC
└── Low Adoption (<100): ContextForge, ContextAtlas, ctxl, context-fabrica

Tier 3-6 (Overview): 46 tools, mostly <500 stars
```

---

## Feature Comparison Dashboard

### Core Feature Availability (Binary Matrix)

```
Legend: ✅ = Yes, ❌ = No, ⚠️ = Partial

Tools: [Arian][Repomix][Gitingest][Sigmap][Promptext][TLDR][Context7][Claude]
══════════════════════════════════════════════════════════

MULTI-FORMAT OUTPUT        ✅  ✅   ❌    ✅    ✅    ❌    ❌    ❌   
TOKEN COUNTING            ✅  ✅   ✅    ✅    ✅    ✅    ❌    ✅   
TOKEN BUDGET ENFORCEMENT  ✅  ⚠️   ⚠️   ⚠️    ✅    ✅    ❌    ⚠️   
COMPRESSION               ✅  ✅   ❌    ✅    ✅    ✅    ❌    ✅   
FILE SELECTION            ✅  ✅   ✅    ✅    ✅    ✅    ❌    ✅   
GIT INTEGRATION           ✅  ✅   ✅    ❌    ❌    ✅    ❌    ✅   
REMOTE REPOS              ✅  ✅   ✅    ❌    ❌    ⚠️    ❌    ✅   
SECURITY SCANNING         ❌  ✅   ❌    ❌    ❌    ❌    ❌    ❌   
MCP SERVER                ❌  ✅   ❌    ✅    ❌    ⚠️    ✅    ✅   
WEB INTERFACE             ❌  ✅   ✅    ❌    ❌    ❌    ✅    ❌   
BROWSER EXTENSION         ❌  ✅   ✅    ❌    ❌    ❌    ❌    ❌   
IDE INTEGRATION           ❌  ✅   ❌    ✅    ❌    ❌    ❌    ✅   

TASK-AWARE SELECTION      ✅  ❌   ❌    ❌    ❌    ❌    ❌    ❌  ← ARIAN UNIQUE
PYTHON AST ANALYSIS      ✅  ❌   ❌    ❌    ❌    ✅    ❌    ⚠️  ← ARIAN UNIQUE
MULTI-LEVEL COMPRESSION  ✅  ⚠️   ❌    ✅    ✅    ✅    ❌    ⚠️  
ARCHITECTURAL CLASSIFIC.  ✅  ❌   ❌    ❌    ❌    ⚠️    ❌    ❌  ← ARIAN UNIQUE
VERIFICATION/GROUNDING    ❌  ❌   ❌    ✅    ❌    ⚠️    ❌    ⚠️   
DETERMINISTIC OUTPUT      ⚠️  ⚠️   ⚠️    ✅    ⚠️    ⚠️    ⚠️    ⚠️   
```

### Feature Completeness Radar Chart

```
                  COMPETITOR FEATURE SCORE (0-100)
                        ╭───────────────╮
                   100  │   Repomix       │
                        │     ╭───╮     │
                        │    /     \    │
                        │   /       \   │
                   80   │  │  Sigmap  │  │ Context7
                        │   \       /   │
                        │    \     /    │
                   60   │     ╰───╯     │
                        │               │
                   40   │  Aider  ● Arian│
                        │               │
                        │  Gitingest    │
                   20   │               │
                        │ Claude Context│
                    0   ╰───────────────╯
                        Core  Int   Adv  Perf  Ecosys
                        Feats Ig    Feats

Legend: ● = Arian Position

Scoring (out of 25 each category):
- Core Features: Arian=18, Repomix=22, Sigmap=20, Gitingest=15
- Integration: Arian=8, Repomix=25, Sigmap=20, Gitingest=18
- Advanced Features: Arian=20, Repomix=12, Sigmap=25, Gitingest=8
- Performance: Arian=18, Repomix=15, Sigmap=25, Gitingest=20
- Ecosystem: Arian=5, Repomix=25, Sigmap=15, Gitingest=18
```

---

## Technical Capabilities Matrix

### Parsing & Analysis Capabilities

| Capability | Arian | Repomix | Gitingest | Sigmap | Promptext | TLDR | Claude Context |
|-----------|-------|---------|-----------|--------|-----------|------|--------------|
| **Python AST** | ✅ Deep | ❌ | ❌ | ❌ | ❌ | ✅ | ⚠️ |
| **Tree-sitter** | ❌ | ✅ | ❌ | ✅ 33 langs | ❌ | ✅ 16 langs | ✅ 12+ langs |
| **Multi-language** | ❌ Py only | ✅ | ✅ | ✅ 33 | ⚠️ Limited | ✅ 16 | ✅ 12+ |
| **AST Depth** | ✅ Very High | ⚠️ Medium | ⚠️ Low | ⚠️ Medium | ⚠️ Low | ✅ Very High | ⚠️ Medium |
| **Semantic Search** | ❌ | ❌ | ❌ | ⚠️ TF-IDF | ❌ | ✅ BGE | ✅ Hybrid |
| **Call Graph** | ⚠️ Basic | ❌ | ❌ | ⚠️ | ❌ | ✅ Full | ⚠️ |
| **Data Flow** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **5-Layer Analysis** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

### Compression Techniques Comparison

| Technique | Tool | Reduction | Quality Preservation | Speed | Deterministic |
|-----------|------|-----------|---------------------|-------|--------------|
| Signature Extraction | Sigmap | **96.8%** | Very High | Very Fast | ✅ Yes |
| 5-Layer AST | TLDR | 95% | Very High | Medium | ⚠️ |
| Index-based | Code Context Engine | 94% | High | Fast | ✅ |
| OR-Tools Optimization | RepoLens | 91% | High | Fast | ✅ |
| Tree-sitter | Repomix | ~70% | Medium | Fast | ⚠️ |
| PTX Format | Promptext | 25-60% | Medium | Very Fast | ✅ |
| Hybrid Vector | Claude Context | ~40% | High | Medium | ⚠️ |
| **4-Level Smart** | **Arian** | **Variable** | **High** | **Fast** | **⚠️** |

---

## Token Reduction Benchmarks

### Token Savings Comparison

```
TOKEN REDUCTION LEADERS:
═════════════════════

Sigmap              ███████████████████████████████ 96.8%
TLDR                ████████████████████████████ 95.0%
Code Context Engine ██████████████████████████ 94.0%
context-router      █████████████████████████     91.0%
Promptext (TOON)    ██████████████████               60.0%
Promptext (PTX)     ██████████████                 30.0%
Repomix             ████████████                   ~70.0%
Arian               ████████████                     Variable
Claude Context      ████████                      ~40.0%
Gitingest           ████████                      95% (claimed)

Benchmark Notes:
- Sigmap: 21 repos tested, byte-stable, deterministic
- TLDR: Function context 21,000 → 175 tokens (99% savings)
- Repomix: ~70% with tree-sitter compression
- Arian: 4 levels, quality varies by compression level
```

### Quality vs. Reduction Trade-off

```
Quality Preservation
  ↑
  │             Sigmap ● (96.8%, Very High)
  │           TLDR ● (95%, Very High)
  │         Code Context Engine ● (94%, High)
  │       Arian ● (Variable, High)
  │     Repomix ● (~70%, Medium)
  │   Claude Context ● (~40%, High)
  │ Promptext ● (25-60%, Medium)
  └──────────────────────────────────▶
       Token Reduction (%)
```

---

## Integration Ecosystem

### MCP Server Adoption

```
MCP SERVER SUPPORT (85% of competitors)
════════════════════════

With MCP Server:  ✅
├── Repomix (20+ tools)
├── Sigmap (20 tools)
├── Context7
├── Claude Context
├── Codanna
├── SDL-MCP
├── DeepContext MCP
├── Code Context Engine
├── MegaMemory
├── prompt-tower
├── ContextForge (16+ tools)
├── ContextVC
├── ContextAtlas
├── ctxl (16 tools)
├── context-fabrica
├── Context Mode
├── Codesight
├── Octocode
├── Ref Tools MCP
└── Entroly

Without MCP Server: ❌
├── Aider (has plugin system)
├── Gitingest
├── Promptext
├── TLDR (archived)
└── Arian ⚠️ (CRITICAL GAP)
```

### MCP Tools Count Comparison

| Tool | MCP Tools | Notable Tools |
|------|-----------|---------------|
| Sigmap | 20 | read_context, search_signatures, get_map, verify_suggestion, get_routing, get_impact, etc. |
| Repomix | 20+ | MCP server, Claude Code plugins, slash commands, explorer |
| ContextForge | 16+ | Cross-session memory, multi-repo workflows |
| ctxl | 16 | .ctxl index system, multi-agent resolution |
| Context Mode | Multiple | Context window optimization, sandboxing |
| Codesight | Multiple | Universal AI context generation |
| Arian | 0 | **CRITICAL: Need to implement** |

### Integration Matrix

```
                    Claude  Cursor  VSCode  GitHub  Docker  Library
                    Code               Actions        API
═══════════════════════════════════════════════════
Repomix              ✅     ✅     ✅     ✅     ✅     ✅
Sigmap               ✅     ✅     ✅     ❌     ❌     ⚠️
Gitingest            ❌     ❌     ❌     ❌     ✅     ✅
Context7             ✅     ✅     ❌     ❌     ❌     ✅
Claude Context       ✅     ✅     ✅     ❌     ❌     ✅
Aider                ✅     ✅     ❌     ❌     ❌     ❌
Promptext            ❌     ❌     ❌     ❌     ❌     ✅ (Go)
TLDR                 ⚠️     ⚠️     ⚠️     ❌     ❌     ❌
Arian                ❌     ❌     ❌     ❌     ❌     ✅ (Python)
```

---

## Arian Positioning Visuals

### Competitive Advantage Matrix

```
                    UNIQUE DIFFERENTIATORS
                    ╭─────────────────────╮
                    │                     │
                    │   TASK-AWARE         │
                    │   FILE SELECTION      │
                    │   (Arian Only)        │
                    │                     │
                    │   PYTHON AST         │
    DIFFERENTIATION │   DEEP ANALYSIS      │ HIGH
                    │   (Arian Unique)      │
                    │                     │
                    │   4-LEVEL            │
                    │   COMPRESSION        │
                    │                     │
═══════════════════╪─────────────────────╪════════════
                    │                     │
                    │   TOKEN BUDGET       │
                    │   ENFORCEMENT        │
                    │   (Arian + Promptext)│
                    │                     │
                    │   ARCHITECTURAL      │
  TABLE STAKES     │   ROLE CLASSIFICATION │ MEDIUM
                    │   (Arian Only)        │
                    │                     │
                    │   MULTI-FORMAT       │
                    │   OUTPUT             │
                    └─────────────────────┘
                    LOW                    HIGH
                    TABLE STAKES
```

### Gap Analysis - What Arian Needs

```
CRITICAL GAPS (Address Immediately):
═══════════════════════════

1. MCP SERVER SUPPORT
   Impact: HIGH | Effort: MEDIUM | Priority: CRITICAL
   85% of competitors have this - table stakes
   Required for Claude Code, Cursor integration

2. WEB INTERFACE
   Impact: HIGH | Effort: MEDIUM | Priority: HIGH
   Repomix.com, Gitingest.com drive adoption
   Increases discoverability and user experience

3. MULTI-LANGUAGE SUPPORT
   Impact: HIGH | Effort: HIGH | Priority: HIGH
   Most competitors support 10+ languages
   Tree-sitter is industry standard

MEDIUM PRIORITY:
├── Security Scanning (Secretlint integration)
├── Git Integration Enhancement
└── Token Budget Messaging

LOW PRIORITY (Long-term):
├── Persistent Memory
├── Git-Native Context
├── Documentation Grounding
└── Semantic Search
```

### SWOT Analysis Visual

```
╔═══════════════════════════════════════════════════════╗
║                        ARIAN SWOT ANALYSIS                    ║
╠═══════════════════════════════════════════════════════╣
║  STRENGTHS (+)                                            ║
║  ├── Task-aware file selection (unique)                  ║
║  ├── Python AST deep analysis (rare)                      ║
║  ├── 4-level smart compression                           ║
║  ├── Architectural role classification                    ║
║  ├── Token budget enforcement (hard limit)               ║
║  ├── Merged/separate/grouped output                       ║
║  └── CLI + Python package                                 ║
╠═══════════════════════════════════════════════════════╣
║  WEAKNESSES (-)                                           ║
║  ├── No MCP server (85% competitors have this)             ║
║  ├── No web interface                                    ║
║  ├── Python-only (multi-language expected)               ║
║  ├── No security scanning                                ║
║  ├── No verification/grounding                           ║
║  ├── No Git-native integration                           ║
║  ├── No persistent memory                                ║
║  └── No optimization-based selection                      ║
╠═══════════════════════════════════════════════════════╣
║  OPPORTUNITIES (→)                                       ║
║  ├── MCP server first-mover (Python tools lagging)       ║
║  ├── Task-aware niche (no competitors)                    ║
║  ├── Python specialization (be the "Python expert")       ║
║  ├── Compression quality leadership                      ║
║  └── Partnership opportunities (Context7, etc.)          ║
╠═══════════════════════════════════════════════════════╣
║  THREATS (⚠️)                                             ║
║  ├── Repomix adding task-awareness → dominates           ║
║  ├── Sigmap adding Python AST → beats Arian technically    ║
║  ├── TLDR coming out of archive → strong competitor        ║
║  └── Market consolidation (big players acquiring)        ║
╚═══════════════════════════════════════════════════════╝
```

---

## Key Takeaways Visual Summary

### The Three Pillars Arian Must Build

```
╭─────────────────────────────────────────────────────────╮
│                 ARIAN'S PATH TO COMPETITIVENESS            │
├─────────────────┬─────────────────┬───────────────────┤
│  PILLAR 1        │  PILLAR 2        │  PILLAR 3          │
│  Integration     │  Language        │  Ecosystem         │
│                 │  Support         │                   │
├─────────────────┼─────────────────┼───────────────────┤
│  ✅ MCP Server   │  ✅ Multi-       │  ✅ Web Interface  │
│  ✅ Claude Code  │     language    │  ✅ GitHub Pages    │
│  ✅ Cursor       │  ✅ Tree-sitter  │  ✅ Hosted option   │
│  ✅ VSCode       │  ✅ 5+ languages │                   │
│  ✅ Other IDEs   │                 │                   │
└─────────────────┴─────────────────┴───────────────────┘
```

### Competitive Timeline

```
2026 Q3-Q4 (Next 90 Days):
├── MCP Server Implementation
├── Web Interface Launch
├── Multi-language Support (Phase 1)
└── Security Scanning Integration

2027 Q1-Q2 (Next 6 Months):
├── Multi-language Support (Phase 2: 10+ languages)
├── Enhanced Git Integration
├── MCP Tools Expansion (20+ tools)
└── Benchmarking Suite

2027 Q3-Q4 (6-12 Months):
├── Persistent Memory
├── Optimization-based Selection
├── Documentation Grounding
└── Semantic Search
```

---

## Appendix: Data Sources

- Primary: GitHub repository analysis (README, docs, source code)
- Metrics: GitHub Stars, Forks, Watchers (2026-07-23 snapshot)
- Benchmarks: Competitor documentation and published results
- Market data: Competitor websites, changelogs, release histories

---

*Generated by Mistral Vibe for Arian project. Visual charts are ASCII representations for markdown compatibility.*
