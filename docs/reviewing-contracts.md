# How to review `contracts.json`

`contracts.json` **is** the human gate (Constitution Principle I / FR-005). `generate`
emits code **only** for contracts you have marked `"review_status": "approved"`. Everything
else is silently skipped. Nothing ships that you did not personally approve.

Every contract comes out of `draft` as `needs_review`. `draft` never auto-approves.

---

## What "review" means depends on the site

This is the part that's easy to forget three weeks into the measurement window.

| Site category | Do you own it? | Does `generate` run? | So what is review *for*? |
| --- | --- | --- | --- |
| **1.** Your Shopify Partners dev store | **Yes** | **Yes** | **Ship quality.** This becomes live code on a real origin. Approve only what you'd be happy for a stranger's AI agent to invoke. |
| **2.** WebMCP demo apps (`webmcp-tools`) | No | No | **Benchmark.** Compare your draft against the site's *own* WebMCP annotations. Named it well? Found every parameter? |
| **3.** Real public sites | No | No | **Detector QA.** Judge whether crawl+draft produced something sensible from messy markup you didn't author. |

For categories 2 and 3 you change nothing and deploy nothing — the contract is an artifact of
the experiment, not a deliverable. **A contract you'd reject is still a useful result:** it
tells you what instrumenting that site would actually require.

> **⚠️ Already-instrumented sites flatter the drafter.** The WebMCP demo apps (category 2)
> already carry `toolname` / `tooldescription` / `toolparamdescription` attributes in their
> markup. Those attributes are in the HTML the drafter sees, so a near-perfect draft there
> proves only that the drafter *faithfully reads existing annotations* — not that it can
> *construct* a contract from scratch. The genuine test of the drafter is **category 3**:
> real, uninstrumented markup with no `toolname` attributes to copy. Don't let a category-2
> pass raise your confidence in drafting quality on uninstrumented sites.

**You cannot instrument a site you don't own.** `navigator.modelContext.registerTool()` only
registers tools for the page whose JS context it runs in. The snippet has to be on their page,
which means the owner deploys it. This is a hard constraint of WebMCP, not a policy we chose.
Never run `generate` for categories 2 and 3.

---

## Universal checks (every contract, every category)

- **`tool_name`** — snake_case, names the *action* (`submit_contact_form`, not `form1`).
- **`description`** — ≤300 chars, written for an **agent**, in the **site's language**. Says
  what the tool *does* and what happens as a result. (The `note` field, by contrast, is for
  **you** and is always English.)
- **`input_schema.properties`** — does it contain every parameter the action actually needs?
- **`input_schema.required`** — the parameters the agent *must* supply. Anything in
  `properties` but not in `required` is optional.
- **No secrets.** No tokens, keys, or internal IDs in any field (FR-007).
- **`api`** — `declarative` or `imperative`; see below.
- **`review_status`** — set to `approved` **only** when you'd accept an agent invoking this
  on a live site.

---

## The judgment calls you will actually hit

### 1. A search form (arrives flagged `low`)

Ask one question: **does submitting it navigate to a real results page, or does it filter a
dropdown in place?**

- Navigates to results → a genuinely useful agent tool. Consider approving.
- Filters live as you type → not a discrete action, no side effect, nothing to invoke. Reject.

Markup alone can't tell these apart (both use `role="search"`), which is why the detector
refuses to decide and hands it to you flagged rather than dropping it (clarify decision D7).

### 2. A cookie / consent banner (arrives flagged `low`)

**Always reject.** Accepting cookies is a consent decision on the end user's behalf. It is
not an action an agent should ever take, and registering it just adds noise to the tool list.

### 3. An empty `input_schema` on a button

```json
"properties": {}, "required": []
```

This is **not** a drafting failure. It's an accurate report that **the markup exposed no
parameters** — a bare `<button>` has no named inputs to derive them from.

**Never approve as-is.** An agent calling `add_to_cart` with no parameters cannot say *which*
product. Either:

- you own the site → add the parameters by hand and write the imperative `execute()` handler; or
- you don't → reject it, and record that this action can't be instrumented from markup alone.
  That finding is worth more than the contract was.

### 4. An ambiguous field (the `note` will tell you)

Draft flags things like *"'name' doesn't specify full name or first/last."* Resolve it in the
parameter description. Google's own bistro demo does exactly this:

> `name` → *"Customer's full name (min 2 chars)"*

Be that explicit. The agent has only the description to go on.

### 5. A misleading `tool_name` (read it, don't skim it)

The drafter builds names from the site's own words, and snake_case can collide with brands.
A real case: a `<button title="Chat with our AI Assistant">` produced `open_ai_chat_assistant`
— tokens `open / ai / chat / assistant` ("open the AI chat assistant"), **not** "OpenAI". The
derivation was innocent, but the name reads like a vendor integration. Rename anything whose
name could be misread (e.g. `toggle_chat_assistant`), and reject non-actions like chat toggles
outright.

---

## `declarative` vs `imperative`

Declarative is only *possible* when the browser can already see **both** the parameters and
the action. A `<form>` provides both for free; a `<button>` provides neither.

| Aspect | `declarative` | `imperative` |
| --- | --- | --- |
| **Use when** | The action *is* a form submit | No form, no named inputs, or custom logic |
| **How** | `toolname`/`tooldescription` on the `<form>`, `toolparamdescription` on inputs | `navigator.modelContext.registerTool({...})` with an `execute()` you write |
| **Parameters** | Derived by the browser from named inputs | You declare `inputSchema` explicitly |
| **JavaScript** | None | Yes — you write the handler |

A button contract with an empty schema **must** be imperative, and you must hand-write the
handler. Note (observed in Chrome 149, on our output *and* on Google's demo): a declarative
tool's `inputSchema.properties` comes back empty from `getTools()`. It still registers and is
callable; only the introspection view is affected. Imperative tools surface their schema.

---

## Approving

Edit the file, set the field, save:

```json
"review_status": "approved"
```

Then `generate` will emit code for it, list it in `.well-known/webmcp`, and skip everything
else. If nothing is approved, `generate` emits nothing and says so — which is the correct,
safe default.

---

## Reference: a well-formed contract

Google's `french-bistro` demo, recovered from its declarative attributes — a good target to
draft against:

| Field | Value |
| --- | --- |
| tool name | `book_table_le_petit_bistro` |
| description | *Initiates a dining reservation request at Le Petit Bistro. Accepts customer details, timing, and seating preferences.* |
| required | `name`, `phone`, `date`, `time`, `guests` |
| optional | `seating`, `requests` |

Note the parameter descriptions carry **format and constraints**, not just meaning:
*"Reservation date (YYYY-MM-DD). Must be today or future."*
