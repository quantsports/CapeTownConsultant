Project Guidelines — CapeTownConsultant

Purpose
- This repository provides a production-ready, asynchronous autonomous personal assistant with web search, research, and persistence capabilities. The entry point is main.py with a simple CLI.

Configuration & Environment
- Environment variables are loaded from .env via python-dotenv at import time.
- Never hard-fail at import if an API key is missing. The app must degrade gracefully and report status at runtime.
  - OpenAI, Pinecone, SerpAPI, Perplexity, and Google Search keys are optional. Missing keys should only disable their related tools.
- The CLI has a config command that displays the availability of each provider.

Tooling Lifecycle (Requirements for adding or modifying a tool)
When adding a new tool, ensure all of the following are implemented consistently:
1. ToolType enum: Add an entry with the lowercase string value used everywhere.
2. Validation: Update ToolExecutor.validate_tool_call to check required parameters.
3. SearchEngine method (or appropriate service): Implement the async method that performs the network call, honoring timeouts and rate limits, and returns a ToolResult.
4. Function definitions: Add the JSON schema for the tool in AutonomousAgent._get_function_definitions so the model can call it.
5. Execution wiring: Add a branch in ToolExecutor.execute to call the concrete implementation.
6. Rate limiting: Use aiolimiter with existing or new limiters to avoid provider throttling (reuse an existing limiter when practical to minimize changes).
7. Error handling: On misconfiguration or provider errors, return ToolResult(success=False, error=...) with a clear message; never raise unhandled exceptions out of the tool method.
8. Citations: When fetching information from the web, populate the citations list with the URLs that contributed to the answer.

Error Handling & Resilience
- Use ToolResult for all tool responses; prefer clear error strings over exceptions.
- Wrap external calls with tenacity retry using exponential backoff and respect Config.MAX_RETRIES and Config.TIMEOUT_SECONDS.
- Avoid raising exceptions at module import time for missing configuration.

Coding Standards
- Remove unused imports and keep dependencies minimal.
- Prefer type hints throughout; keep public interfaces stable.
- Keep functions small, single-responsibility, and name them descriptively.
- Maintain consistent JSON schemas for function-calling tools.

Rate Limiting
- Configure per-provider AsyncLimiter instances using values from Config when available. Reuse an existing limiter if adding a new one would create unnecessary complexity.

Persistence & Memory
- Profiles persist under ./data/profiles. Access via ProfileManager and avoid direct file I/O elsewhere.
- Vector memory relies on Pinecone; the app should operate without it if keys are missing (tools should surface errors gracefully).

Citations & Answers
- When tool results are used, citations should be collected and formatted as [1], [2] in the final response.
- Combine multiple sources when appropriate and be concise yet accurate.

CLI Behavior
- Commands: exit, clear, config. Avoid adding stateful commands that break stateless usage.
- Do not prompt for API keys in the CLI. Rely on environment variables and report status via config.

Testing & Validation
- On code changes, ensure main.py imports without throwing, even with no .env configured.
- Prefer small integration checks using python -c 'import main'.

Notes for This Repository
- The google_search tool is implemented using Google Custom Search JSON API. It requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID. If missing, it returns a structured configuration error via ToolResult.
- SerpAPI and Google search tools are mutually independent; either may be configured or both.
