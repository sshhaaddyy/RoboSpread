# Best Browser MCP for Claude Code on macOS (2026)

**Date:** 2026-04-20
**Question:** What is the best MCP server for controlling a Chrome browser from Claude Code in 2026? Compared Chrome DevTools MCP, Playwright MCP, Puppeteer MCP, BrowserMCP, and notable alternatives, evaluated on feature completeness, stability, maintainership, install friction on macOS, token efficiency, and best-fit task type (everyday web-automation vs deep debugging).

**User context:** macOS, Vite React dev server on :5173, occasional scraping, React rendering / network debugging, Anthropic Pro/Max subscription.

## Angles researched

1. Chrome DevTools MCP deep-dive [standard]
2. Playwright MCP deep-dive [standard]
3. Puppeteer MCP deep-dive [standard]
4. BrowserMCP + alternatives (Stagehand, Browserbase, Selenium, AgentQL, Skyvern) [standard]
5. Task-fit recommendation for the user's actual setup [deep]

*(Dropped: ecosystem-signals angle.)*

---

## TL;DR

**Install two, not one.** Use `claude --chrome` (native extension, included with your Pro/Max plan) as the daily driver for `localhost:5173` UI checks, and add **Chrome DevTools MCP** on-demand for deep network/perf debugging. Skip a third MCP unless you hit a wall — but if you do, **Playwright MCP** is the repeatable-scraping/automation pick. Puppeteer MCP is dead; don't install it.

> **Addendum caveat (see §Addendum):** Chrome DevTools MCP does **not** expose React DevTools panels — no component tree, no render profiler. It only exposes raw CDP / V8 (heap, CPU traces, network, Lighthouse). If your React debug case is "which component re-rendered and why," the MCP won't solve it directly; use `evaluate_script` + `__REACT_DEVTOOLS_GLOBAL_HOOK__` as a workaround, or fall back to opening native Chrome DevTools by hand.

## Feature matrix

| Server | Feature completeness | Stability | Maintainership | macOS install | Token efficiency | Best-fit |
|---|---|---|---|---|---|---|
| **Chrome DevTools MCP** | 29 tools across 6 categories; perf traces, heap snapshots, Lighthouse, CDP. **No React DevTools.** | Active, pre-1.0 (v0.21.0, Apr 1 2026); 77 open issues. **#1094 closed as not planned** — long `--autoConnect` sessions still drop. | Google Chrome team (Bynens/Hablich), 36k stars | Low-med: `npx` or `brew`; Chrome path auto-detect can fail (#889) | Moderate; pagination on network/console; `take_snapshot` large on SPAs | Deep debugging (perf, memory, network waterfall, Lighthouse) |
| **Playwright MCP** | Most complete: 25+ tools, cookies, storageState auth, route mocking, trace/video | ~release every 2–3 days; v0.0.70 Apr 1 2026; depends on `playwright-core@1.56.0-alpha` | Microsoft, 31.1k stars, 23 open issues | Low: `npx @playwright/mcp@latest`, bundles Chromium | Heavy: ~4.2k tokens schemas + 3.8–50k snapshots; 8-step run ~89–114k tokens | Authenticated automation ≤10–15 steps, scraping with session reuse |
| **Puppeteer MCP (reference)** | Narrow: navigate/click/eval/screenshot; no network, no cookies | Archived May 29 2025, "NO SECURITY GUARANTEES" | Abandoned; best fork `merajmehrabi` (439 stars, Mar 2025) | Medium: 170MB Chromium download | Low — screenshots + DOM only | Superseded; avoid |
| **BrowserMCP** | Playwright-like surface via user's real Chrome profile (logged-in sessions) | 6.4k stars, 100k+ extension installs; repo partially opaque ("can't build standalone") | Hobbyist/small team | Low: extension + local bridge | Not benchmarked in briefs | Authenticated everyday automation on your real profile |
| **Stagehand / Browserbase** | 6 AI-intent tools (act/observe/extract) | v3.0.0 Mar 31 2026, 3.3k stars | Browserbase Inc. | Zero local install (hosted SHTTP option) | Heavy: secondary LLM per action | Cloud agents, CI — not local dev |
| **Selenium MCP** | ~18 tools; Chrome+FF+Edge+Safari | v0.2.3 Feb 23 2026, 387 stars | Angie Jones + 9 contributors | Med (WebDriver setup) | Verbose, no a11y shortcut | Cross-browser QA only |
| **Skyvern / AgentQL** | Vision-native / extraction-only specialists | Active | OSS teams | Varies | Heavy | Hostile-site RPA / pure extraction |
| **`claude --chrome`** (native) | Shares live Chrome session; cookies/auth; localhost demo is Anthropic's flagship example | Beta; service-worker disconnects on long sessions | Anthropic, direct plan only (not Bedrock/Vertex) | Lowest: one CLI flag | ~10k tokens/page | Day-to-day dev-server verification with your logged-in state |

## Chrome DevTools MCP vs Playwright MCP — the real tradeoff

Not substitutes:

- **Chrome DevTools MCP *debugs* a browser** (traces, heap, source-mapped stacks, Lighthouse, `performance_analyze_insight`). Nothing else in the landscape matches this. Overkill for scraping. **But: no React DevTools panels.**
- **Playwright MCP *drives* a browser** (structured a11y-tree actions, storageState auth persistence, route mocking, multi-tab, self-healing tests). Best on automation breadth, pays for it in tokens — 8-step run ~89–114k tokens. Microsoft's separate `@playwright/cli` is ~4× leaner (~27k) if shell invocation is OK.

Steve Kinney's framing: they are complementary, not competing.

## Why `claude --chrome` is your daily driver

Your primary loop is "I changed a component, does localhost:5173 look right?" Anthropic's own docs demo exactly this. `claude --chrome`:
- Shares your live Chrome session (auth, cookies, DevTools state) — no bridge overhead.
- Costs ~10k tokens/page — comparable to Chrome DevTools MCP, lighter than Playwright MCP snapshots.
- Requires only your Pro/Max direct plan.

It does **not** replace Chrome DevTools MCP's profiling, and it's still beta with service-worker disconnection issues on long sessions. Escalate to Chrome DevTools MCP when perf/heap/network-waterfall depth is needed.

## Recommendation

1. **Enable `claude --chrome`** — daily driver for localhost:5173 verification. Zero install friction.
2. **Add Chrome DevTools MCP** (`npx chrome-devtools-mcp@latest` or `brew install chrome-devtools-mcp`) — turn on when you need heap snapshots, Lighthouse, or network-waterfall analysis. **Use short-lived sessions** (issue #1094 won't be fixed); keep it disabled otherwise to save the ~18k tool-def tokens.
3. **Add Playwright MCP later** only when you hit a repeatable scraping or authenticated-automation task `claude --chrome` can't handle. `npx @playwright/mcp@latest`.
4. **Do not install Puppeteer MCP.** Reference archived May 2025; forks thin; superseded on every axis.

## Trade-offs / risks

- `claude --chrome` is **beta**; long sessions drop connections.
- Chrome DevTools MCP bug **#1094 closed as not planned** — `--autoConnect` approval-prompt spam on long sessions is permanent. Mitigation: restart the MCP process per debug task.
- **No React DevTools panels** anywhere in the ecosystem. For component-tree / render-profiler work, use native Chrome DevTools by hand, or `evaluate_script` + `__REACT_DEVTOOLS_GLOBAL_HOOK__` internals (brittle across React versions).
- Playwright MCP depends on `playwright-core@1.56.0-alpha` — yellow flag for prod; fine for local dev.
- `claude --chrome` requires the Anthropic direct plan; won't work on Bedrock/Vertex.

## Gaps remaining

- No hard numbers on `take_snapshot` payload sizes for large SPAs.
- BrowserMCP's full tool surface not publicly enumerable (private monorepo).
- PinchTab / Perplexity Comet MCP status unverified.
- Reliability of `evaluate_script` + fiber introspection as a React-debug workaround has no community write-up.

## Addendum (gap-close)

**React DevTools integration:** Confirmed absent. Chrome DevTools MCP's 29 tools cover input/nav/emulation/perf/network/debug at raw CDP level. `evaluate_script` + `take_memory_snapshot` are the deepest primitives. No roadmap item for React-specific panels. The Components tab and Profiler tab from browser React DevTools are not exposed. Workaround: call `evaluate_script` against `__REACT_DEVTOOLS_GLOBAL_HOOK__` / `__reactFiber*` internals — hand-crafted, brittle across React versions.

**Issue #1094 status:** **Closed as not planned.** No fix merged. v0.21.0 changelog (April 1, 2026) does not mention autoConnect stability. Sibling issues #1149 (Claude Code plugin) and #1184 (CLI autoConnect) confirm the problem persists. Mitigation: short-lived MCP sessions — restart per debug task.

**Confidence:** High on both gaps.

## Sources

- https://github.com/ChromeDevTools/chrome-devtools-mcp
- https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md
- https://github.com/ChromeDevTools/chrome-devtools-mcp/issues/889
- https://github.com/ChromeDevTools/chrome-devtools-mcp/issues/1094
- https://github.com/ChromeDevTools/chrome-devtools-mcp/issues/1149
- https://github.com/ChromeDevTools/chrome-devtools-mcp/issues/1184
- https://github.com/ChromeDevTools/chrome-devtools-mcp/releases
- https://developer.chrome.com/blog/chrome-devtools-mcp
- https://github.com/microsoft/playwright-mcp
- https://github.com/microsoft/playwright-mcp/issues/1113
- https://github.com/microsoft/playwright-mcp/issues/1216
- https://github.com/microsoft/playwright-mcp/issues/1233
- https://github.com/microsoft/playwright-mcp/releases
- https://playwright.dev/docs/getting-started-mcp
- https://github.com/modelcontextprotocol/servers-archived
- https://github.com/modelcontextprotocol/servers-archived/tree/main/src/puppeteer
- https://github.com/merajmehrabi/puppeteer-mcp-server
- https://www.npmjs.com/package/puppeteer-mcp-server
- https://www.pulsemcp.com/servers/modelcontextprotocol-puppeteer
- https://community.latenode.com/t/how-to-run-puppeteer-with-installed-chrome-on-macos/6747
- https://github.com/BrowserMCP/mcp
- https://browsermcp.io/
- https://github.com/browserbase/mcp-server-browserbase
- https://www.browserbase.com/mcp
- https://github.com/angiejones/mcp-selenium
- https://github.com/tinyfish-io/agentql-mcp
- https://github.com/Skyvern-AI/skyvern
- https://code.claude.com/docs/en/chrome
- https://stevekinney.com/writing/driving-vs-debugging-the-browser
- https://dev.to/minatoplanb/i-tested-every-browser-automation-tool-for-claude-code-heres-my-final-verdict-3hb7
- https://www.ytyng.com/en/blog/ai-browser-automation-tools-comparison-2026
- https://lalatenduswain.medium.com/playwright-mcp-vs-claude-in-chrome-which-browser-testing-tool-should-you-use-in-2026-e502bee0067a
- https://testcollab.com/blog/playwright-cli
- https://ayyaztech.com/blog/chrome-devtools-mcp-vs-claude-in-chrome-vs-playwright
- https://scrolltest.medium.com/playwright-mcp-burns-114k-tokens-per-test-the-new-cli-uses-27k-heres-when-to-use-each-65dabeaac7a0
- https://www.morphllm.com/comparisons/playwright-vs-puppeteer
- https://www.skyvern.com/blog/browser-automation-mcp-servers-guide/
- https://www.pulsemcp.com/servers/chrome-devtools
- https://developer.tenten.co/how-to-install-chrome-devtools-mcp-on-macos

---
*Brief generated 2026-04-20 via /research fan-out → fan-in (5 angles, 1 gap-close round).*
