# Multi-Agent AI Systems — Master Reference
Built while creating a real multi-agent stock research system. Every concept here was learned by hitting a real bug or asking a real question — not theory-first.

---

## PART 1 — CORE AI/LLM CONCEPTS

### API
A door between your code and an AI model sitting on a company's server. You send a request, it sends back a response. Without it, you cannot use the model programmatically.

### API Key
Your identity/password to use that door. Never hardcode it in your script — always load it from a `.env` file so it never gets committed to version control.

### System Instruction vs User Message
- **System instruction** = the agent's permanent role/identity, set once per call. "You are a fundamental analyst."
- **User message** = the specific task for this particular request. "Analyze INFY.NS."
- Same underlying model, different role each time → this is the entire mechanism behind "specialized agents."

### Response Object
What the API sends back. You extract `.text` (or similar) to get the readable output. Modern SDKs also return structured data like function-call requests, not just plain text.

### Model Selection
Different model names (e.g. `gemini-2.0-flash` vs `gemini-2.5-flash`) trade off speed, cost, and capability. Always check what's currently available/recommended — this changes over time.

---

## PART 2 — FUNCTION CALLING / TOOL USE (The Real "Agentic" Part)

### The Key Insight
Everything built with just system instruction + user message is **not yet agentic** — you're still the one deciding what happens. True agentic behavior means **the model decides for itself** which function to call, based on the question.

### How It Works
1. You write normal Python functions with clear docstrings.
2. You pass those functions to the model as `tools`.
3. The model reads each docstring to understand *when* to use that tool — the docstring is not a comment for humans, it's an instruction the model reads.
4. Based on the user's question, the model decides which tool(s) to call, in what order, and with what arguments.
5. The SDK executes the actual Python function, and the model uses the real returned data to write its answer.

### Why This Matters
This exact mechanism — function calling — is what powers every real "AI agent" product: Claude's computer use, ChatGPT plugins, AI coding assistants. Frameworks like CrewAI, LangChain, and AutoGen are built on top of this same primitive; they just hide the wiring.

### Multi-Step Tool Chaining
A model can call one tool, use its output as input to a second tool, all within a single turn — e.g., fetch a stock's sector first, then use that sector to look up an industry benchmark. This is called **tool orchestration** and is a step above single-tool calling.

---

## PART 3 — MULTI-AGENT ORCHESTRATION PATTERNS

### Sequential Handoff
One agent's text output becomes the next agent's input directly. Example: Fundamental Analyst's output + Technical Analyst's output both get fed as context into a Chief Analyst, who reasons over both.

### Orchestrator-Worker Pattern
A central controller function calls multiple specialized "worker" agents in sequence (or parallel), then combines their results. This is the architecture underneath almost every practical multi-agent system, regardless of framework.

### Not Every Agent Needs Tools
A synthesizer/manager agent (like a "Chief Analyst") often needs zero tools — its entire job is reasoning over text it's already been given. Giving it unnecessary tools wastes API calls and adds complexity for no benefit. Decide tool access per-agent, based on what that agent's job actually requires.

### AI Agent vs Agentic AI
- **AI Agent** = one LLM + a role + tools = one focused specialist.
- **Agentic AI** = a system of multiple agents that make decisions, call tools, and hand off results to each other with minimal manual orchestration.

---

## PART 4 — DATA ENGINEERING HYGIENE (Learned The Hard Way)

### Sanitize At The Boundary
Real-world data from any external source (APIs, scrapers, live feeds) is messy — missing values, `NaN`, `None`, occasionally malformed. **Always validate/clean data right before it crosses a system boundary** (e.g., before sending it to another API as JSON). `NaN` is valid in Python but is NOT valid JSON — sending it directly to an API causes a hard crash.

```python
def sanitize(data: dict) -> dict:
    clean = {}
    for key, value in data.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            clean[key] = "N/A"
        elif value is None:
            clean[key] = "N/A"
        else:
            clean[key] = value
    return clean
```

### Don't Trust The Last Row Of Live Data Blindly
`.iloc[-1]` grabs the most recent row unconditionally — but the most recent row in a live-updating dataset (like today's stock price) is often the least reliable, sometimes still `NaN` if the market hasn't updated yet. Filter for the last **valid** value instead:
```python
valid_values = series.dropna()
last_valid = valid_values.iloc[-1] if not valid_values.empty else fallback_value
```

### Fallback Chains
When one data source might be incomplete, have a backup source ready rather than letting the whole request fail:
```python
value = source_a.get("field") or source_b.get("other_field") or "N/A"
```

---

## PART 5 — ERROR HANDLING FOR EXTERNAL APIS

### The Three Errors That Actually Matter
| HTTP Code | Meaning | Fix |
|---|---|---|
| **429** RESOURCE_EXHAUSTED | You've hit YOUR usage quota (per-minute or per-day) | Wait, check quota dashboard, or rotate to a fresh key temporarily |
| **503** UNAVAILABLE | The provider's servers are overloaded on THEIR end | Retry with backoff — usually resolves within a minute |
| **400** INVALID_ARGUMENT | Your request was malformed (often bad/unsanitized data) | Fix the data being sent — retrying won't help |

### Retry With Exponential Backoff
Don't retry instantly — wait progressively longer between attempts, since instant retries just hit the same limit again:
```python
for attempt in range(max_retries + 1):
    try:
        return make_api_call()
    except TransientError:
        wait_time = 15 * (attempt + 1)
        time.sleep(wait_time)
```

### Diagnose, Don't Guess
Print or log the raw exception detail during debugging — don't rely purely on string-matching generic categories. The real Google API error message told us directly: *"Quota exceeded for metric: generate_content_free_tier_requests"* — that's a precise diagnosis, not a guess.

---

## PART 6 — ENVIRONMENT & TOOLING (Windows-Specific Lessons)

### Virtual Environments (venv)
An isolated bubble of Python packages, scoped to one project, so different projects can use different package versions without conflicting.
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Why Installs Kept Breaking
Microsoft Store-installed Python runs in a sandboxed wrapper that adds overhead and can behave unpredictably with heavy packages. A python.org install (with "Add to PATH" checked) avoids this entirely.

### Windows App Execution Aliases
Windows can keep a fake `python.exe` shortcut pointing to the Microsoft Store even after installing real Python elsewhere. Check Settings → Apps → Advanced app settings → App execution aliases, and disable `python.exe`/`python3.exe` there if the wrong interpreter keeps getting picked up.

### Verify Which Python Is Actually Running
```bash
python -c "import sys; print(sys.executable)"
```
(Note: PowerShell's `where` command is aliased to something else and won't reliably show this — use the line above instead.)

### Lock In Working Dependencies
```bash
pip freeze > requirements.txt
```
Run this whenever a setup is confirmed working — it becomes your restore point.

---

## PART 7 — GIT & GITHUB

### The Repo Creation Trap
If you create a GitHub repo **with README/.gitignore pre-checked**, GitHub creates a commit on the remote before you've pushed anything. Your local folder has a separate, unrelated commit history. Git refuses to push because the histories don't share a common ancestor — this causes the "merge unrelated histories" errors.

**Fix:** create new GitHub repos completely empty (no README, no .gitignore, no license checked) when you already have local code ready to push.

### How `.gitignore` Actually Works
- Only affects **untracked** files — files git has never committed before.
- Has **zero effect** on files already committed and pushed, even if added afterward.
- To stop tracking an already-committed sensitive file:
```bash
git rm --cached .env
git commit -m "Remove .env from tracking"
git push
```

### Never Commit Secrets
API keys, passwords, tokens — always in `.env`, always in `.gitignore`, from the very first commit. If a secret does leak, **rotating/regenerating the key** matters more than cleaning git history, since the leaked key is immediately useless once rotated.

---

## PART 8 — PROJECT-SPECIFIC LIMITATIONS TO REMEMBER

- **Industry PE benchmarks used here are static reference values**, not live-calculated data. Real live sector averages require a paid provider (Screener.in, Trendlyne, Bloomberg).
- **Sector classification comes from Yahoo Finance's own taxonomy**, which occasionally misclassifies companies (e.g., some equipment manufacturers get grouped under "Technology" rather than their actual industry). Any downstream comparison is only as good as this upstream label.
- **News sentiment is headline-based only**, not full-article analysis — a directional signal, not a rigorous score.
- **Free-tier API quotas** are limited daily and per-minute — heavy testing sessions can exhaust them; this is expected, not a bug.

---

## PART 9 — INTERVIEW-READY ONE-LINERS

| Concept | One-Line Answer |
|---|---|
| What is an AI agent? | An LLM given a specific role and access to tools to complete a task |
| What is function calling? | Giving a model callable functions with descriptions so it can decide when to use them itself |
| What's the difference between AI Agent and Agentic AI? | One agent with a role vs. a system of multiple agents coordinating and handing off work |
| Why sanitize data before sending to an API? | External data sources often contain nulls/NaNs that break strict JSON serialization |
| Why retry with backoff instead of immediately? | Instant retries hit the same rate limit again; backoff gives the limit window time to reset |
| What's a virtual environment? | An isolated set of installed packages scoped to one project, preventing version conflicts |
| Why does `.gitignore` sometimes "not work"? | It only blocks untracked files — it can't retroactively hide something already committed |
| What's the biggest limitation of this stock research system? | It relies on static reference benchmarks and upstream data classification, not live calculated financial data |
