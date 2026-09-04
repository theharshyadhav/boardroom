# BoardMind WebMCP Integration

## Overview

BoardMind uses WebMCP as a browser-side integration layer between compatible AI agents and the existing BoardMind application. It does not replace the FastAPI API, duplicate backend business logic, or create a second data model. Each WebMCP tool delegates to the same typed API helper used by the human-facing Next.js UI.

The implementation follows the current WebMCP Community Group draft available at <https://webmachinelearning.github.io/webmcp/>. WebMCP is an experimental browser capability, so the integration is optional and has no effect in browsers that do not expose `document.modelContext`.

## Architecture

```text
Compatible browser agent
          |
          | discovers registered tools
          v
Document.modelContext
          |
          | registerTool({ name, title, description, inputSchema, execute, annotations })
          v
frontend/src/lib/webmcp.ts
          |
          | delegates to typed functions
          v
frontend/src/lib/api.ts
          |
          | HTTPS requests
          v
FastAPI backend on Render
          |
          v
Existing deterministic analytics, narrative, simulation, and Boardroom services
```

`frontend/src/lib/webmcp.ts` owns only tool metadata, JSON Schemas, registration, and error normalization. `frontend/src/lib/api.ts` remains the single request helper. The backend remains the owner of authorization, validation, business rules, calculations, and persistence.

## Exposed Tools

| Tool | Backend capability | Mutates state |
| --- | --- | --- |
| `get_kpis` | `GET /api/kpis` | No |
| `get_events` | `GET /api/events` | No |
| `get_driver_tree` | `GET /api/driver-tree` | No |
| `get_evidence` | `GET /api/evidence/graph` | No |
| `get_recommendations` | `GET /api/recommendations` | No |
| `generate_summary` | `GET /api/summary` | No |
| `run_business_simulation` | `POST /api/simulate` | No |
| `get_agents` | `GET /api/agents` | No |
| `launch_boardroom_workflow` | `POST /api/boardroom/launch` | Yes |
| `get_boardroom_dashboard` | `GET /api/boardroom/dashboard` | No |
| `get_tasks` | `GET /api/boardroom/tasks` | No |
| `get_observability` | `GET /api/observability/summary` | No |
| `health_check` | `GET /api/health` | No |

The launch tool is registered with the current WebMCP `annotations.consequentialHint` signal because it starts a real workflow. Read-only tools use `annotations.readOnlyHint`.

## Tool Discovery

WebMCP discovery is performed by the browser agent, not by the application. The page registers tools into its document-level `ModelContext`; a compatible browser agent observes that model context and exposes the tools to its own agent runtime.

The WebMCP specification intentionally does not prescribe the wire format used by a browser agent. A browser may expose the registered definitions through its own MCP or function-calling bridge. Therefore, the application can guarantee correct WebMCP registration and browser-level discoverability, but whether a particular host such as ChatGPT's in-app browser currently surfaces WebMCP tools depends on that host's WebMCP implementation and rollout status.

For an in-page WebMCP consumer, the standards-defined verification is:

```js
const tools = await document.modelContext.getTools();
console.log(tools.map((tool) => tool.name));
```

A compatible browser should return all 13 BoardMind names listed above after registration resolves. The browser agent may use a separate implementation-defined observation path, as described in the WebMCP specification.

## Registration Flow

1. `frontend/src/app/layout.tsx` renders `AuthProvider`, the client-side application root.
2. `AuthProvider` imports `registerWebMcpTools` and invokes it from a `useEffect`, so registration starts once the document exists in the browser.
3. The module checks `typeof document` and the presence of `document.modelContext`. Unsupported browsers return without logging or changing application behavior.
4. A shared `registrationPromise` makes repeated calls from React development behavior or the existing Boardroom status panel idempotent. Only one registration sequence can run.
5. Each tool is registered with the official imperative API: `document.modelContext.registerTool(...)`.
6. Registration awaits each promise and logs the successful count as `Registered 13 WebMCP tools`.

Registration failures are isolated per tool and logged. A failed registration does not prevent the remaining tools from being attempted.

## Request Flow

When an agent invokes a discovered tool, the browser runs the registered `execute` callback in the BoardMind page context. The callback receives the agent's structured input object. The input schema describes the expected shape before invocation; the FastAPI backend remains the final authority for validation.

The callback then calls an existing method from `api`:

```text
agent input
  -> WebMCP inputSchema / execute callback
  -> api.kpis(), api.simulate(), api.launchProject(), etc.
  -> shared api request helper
  -> deployed FastAPI endpoint
```

No endpoint URL construction or second `fetch` implementation exists in the WebMCP module.

## Execution Flow

1. WebMCP parses and validates the tool input according to the registered JSON Schema.
2. The callback delegates to the corresponding typed API method.
3. The API helper performs the request and parses the backend JSON response.
4. Successful responses are returned unchanged as structured JSON objects or arrays.
5. If the request fails, response parsing fails, or the backend rejects the input, the wrapper returns a structured error object:

```json
{
  "ok": false,
  "error": "API /api/... failed: 500 ..."
}
```

This prevents rejected network promises from becoming uncaught tool exceptions while preserving a useful result for the agent. The backend's existing authorization and validation behavior is not bypassed.

## JSON Schema and Specification Compliance

Every registered tool supplies an object-valued `inputSchema` with JSON Schema-compatible `type`, `properties`, and, where needed, `required` members. Tool names use only permitted ASCII characters and remain well below the specification's 128-character limit. Each definition includes a non-empty `name`, `title`, `description`, and asynchronous `execute` callback.

The implementation uses the current imperative WebMCP shape:

```ts
document.modelContext.registerTool({
  name,
  title,
  description,
  inputSchema,
  execute,
  annotations,
});
```

The callback is compatible with the specification's `(inputObject, options)` signature; JavaScript allows the unused execution-options argument to be omitted. Tool cancellation and browser-level lifecycle handling remain under the browser's WebMCP implementation.

## Verification

The repository's frontend production build passes with the integration enabled:

```bash
cd frontend
npm run build
```

The build validates TypeScript compilation and Next.js production bundling. Actual ChatGPT in-app-browser discovery cannot be proven from the application repository alone because it requires a ChatGPT/browser runtime that exposes WebMCP. In a supporting browser, use `await document.modelContext.getTools()` to verify the complete registered set and invoke a read-only tool such as `health_check` to verify execution end to end.
