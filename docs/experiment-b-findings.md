# Experiment B — field findings

Observations from running the instrumenter against real sites that bear directly on the
go/no-go decision. This is the *point* of the experiment — record what the pipeline teaches
us about whether agent-invocable actions are reachable at all, not just whether the code runs.

---

## Finding 1 — The valuable action is usually a third-party SaaS widget in a cross-origin iframe

**Evidence:** `gct.lu/reservations/` (Grünewald Chef's Table, a real Luxembourg SMB restaurant,
crawled 2026-07-14).

The page's own markup (WordPress) contains only a **newsletter** form (`your-name`,
`your-email`, + a spam honeypot). The actual **reservation** flow — party size, date, time,
room, the "Réserver" button — lives entirely inside a **cross-origin `<iframe>`** served from
`bookings.zenchef.com` (Zenchef, a restaurant-booking SaaS). There's a second Zenchef iframe
(the floating widget) and a "Book a room" link to another SaaS, `reservations.cubilis.eu`.

**Why it matters — this is a structural barrier, not a detail:**

1. **The site owner cannot instrument it.** `navigator.modelContext.registerTool()` only
   registers tools in the page's *own* JavaScript context. The reservation UI is a *different
   origin* the owner doesn't control. GCT pasting a WebMCP snippet into their own page reaches
   the newsletter form and **nothing else**. Only **Zenchef** could add WebMCP to the widget.
2. **It isn't even form-shaped.** The widget is a Next.js app of `<button>`s
   (`data-testid="2guest-btn"`, day/slot/room buttons) — no declarative path; it would need
   imperative instrumentation written by the vendor.
3. **It's behind active bot-defense.** The widget loads **AWS WAF CAPTCHA**
   (`captcha-sdk.awswaf.com`, `challenge.js`). Even a perfectly-instrumented tool call would
   face bot-detection — the agent-vs-spam collision (see Finding 2), industrial-strength.

**Go/no-go implication.** A large share of real SMB "actions" (reservations, bookings, orders,
checkout) are **third-party SaaS widgets embedded via iframe** — Zenchef, Cubilis, OpenTable,
Shopify checkout, etc. For these, the concierge "paste a snippet on the SMB's site" model
**does not reach the most valuable action on the page.** The leverage point is not ~10,000
SMBs one at a time; it's the **~20 vertical SaaS vendors** whose widgets those SMBs embed.
That is a fundamentally different go-to-market:

- **Better** in that it's concentrated — win Zenchef, and every Zenchef restaurant is
  instrumented at once.
- **Harder** in that it removes the concierge's agency — you now need the SaaS vendor to say
  yes; you can't just paste code for a paying SMB.

**This should be measured deliberately** during Experiment B: of the target SMB sites, what
fraction of the *primary* action is (a) in the site's own markup vs (b) a cross-origin
third-party widget? That ratio is a direct input to whether AgentBridge sells to SMBs or to
platforms.

---

## Finding 2 — WebMCP tools and existing bot-defenses are on a collision course

**Evidence:** `gct.lu` newsletter form carries a **honeypot** field (`honeypot-885`, labelled
"Please leave this field empty") — a classic spam trap: a field humans never fill and bots do.
The Zenchef widget adds **AWS WAF CAPTCHA** on top.

An AI agent is, to a spam filter, a bot. Even a correct WebMCP tool that omits the honeypot may
be blocked by behavioural/timing bot-detection or an outright CAPTCHA. **Instrumenting the
action is necessary but not sufficient** — the invocation still has to survive defenses built
specifically to stop automated submissions. This is a real risk to *measured* invocation
volume and worth watching in the logs (successful registrations, but failed submissions).

---

## Finding 3 — "Already-instrumented" reference sites flatter the drafter

The WebMCP demo apps (category 2) already carry `toolname`/`tooldescription`/
`toolparamdescription` attributes, so a near-perfect draft there proves only that the drafter
faithfully *reads existing annotations* — not that it can *construct* a contract from
un-annotated markup. The genuine drafter test is a real, uninstrumented site. (Detail in
`docs/reviewing-contracts.md`.)

## Finding 4 — Booking widgets are SPAs that render after `load`

`salonkee.lu` (a SaaS salon-booking platform) serves its widget as an Angular single-page
app. Crawling with Playwright's `wait_until="load"` and extracting immediately found **2**
candidates — the static shell's Login button and a country selector. The actual service /
appointment UI hydrates *after* the load event: waiting for network idle instead surfaced
**88** buttons (including `make-appointment-button` and the per-service buttons).

This is a crawl-methodology gap, distinct from Finding 1: the actions here are real
same-origin `<button>`s the vendor *could* instrument — the crawler just extracted too
early. Any client-rendered target (which is most modern booking/checkout flows) hits this.
Note salonkee is again a *vendor* platform, reinforcing Finding 1's vendor-not-SMB thesis:
crawled directly it's same-origin, but embedded on a salon's own site it would be a
cross-origin iframe like Zenchef.

---

## Finding 5 — Shopify is already shipping a full WebMCP toolset across its storefronts (the go/no-go pivot)

**Evidence:** `en.nutri-bay.com` (a real Shopify nutrition store, crawled 2026-07-15). The page
carries a WebMCP origin-trial token whose decoded payload is
`{"origin":"https://cdn.shopify.com:443","feature":"WebMCP","isThirdParty":true,"expiry":1794873600}`
(expiry 2026-11-16). Running the storefront in Chrome 149 with WebMCP enabled and calling
`navigator.modelContext.getTools()` returns **10 live, Shopify-registered tools**:

`search_catalog`, `browse_store`, `get_product`, `show_variant`, `get_cart`, `update_cart`,
`cancel_cart`, `proceed_to_checkout`, `manage_orders`, `search_shop_policies_and_faqs`.

The token is **third-party, origin `cdn.shopify.com`** — i.e. it is injected by **Shopify's own
CDN scripts**, not by the merchant. The full commerce flow (search → product → cart → checkout
→ orders) is instrumented, and because the OT token enables the WebMCP API for Shopify's
scripts in production Chrome 149, **a real agent visiting any such store sees these 10 tools
today** — no merchant action required.

**Why it matters — this reshapes go/no-go more sharply than Finding 1.** Finding 1 said the
leverage point is the ~20 vertical SaaS vendors, not 10,000 SMBs. Finding 5 shows a **platform**
has already acted: Shopify (millions of merchants) has built a professional-grade WebMCP toolset
and is rolling it out storefront-wide. The core premise of Experiment B — *"instrument a handful
of test sites with WebMCP tools and measure invocation volume"* — is **partly overtaken** for the
entire Shopify segment: the instrumentation exists, done better than a concierge tool would, and
for free to the merchant. The same is likely to follow for other commerce platforms (Wix,
BigCommerce) and the booking SaaS vendors from Finding 1 (Zenchef, Salonkee).

**What this leaves for a third-party instrumenter (AgentBridge):** sites *not* on a platform
that is rolling out WebMCP — bespoke/custom builds — which are the minority and the hardest to
reach. The measurable question shifts from "can we instrument SMB sites?" to "**is there
residual demand once the platforms instrument their own merchants?**" and "**where does agent
traffic actually flow — platform-registered tools or anything else?**"

**Concrete Experiment B action:** the highest-signal measurement is no longer "instrument N test
sites and count." It is "**observe invocation volume on tools that already exist**" (Shopify's 10
tools on a store Arnaud can stand up as a Shopify Partners dev store — v1 target #1) and
"**quantify how much of the addressable web is already platform-instrumented**" (crawl a sample;
count sites carrying a `cdn.shopify.com` / platform WebMCP third-party token).

**Bonus (validates a tool detail):** this is the third independent site whose decoded OT feature
string is exactly `WebMCP` (french-bistro demo, Shopify's token). `_is_webmcp_feature` was
tightened from a substring heuristic to an exact match on the strength of it.

---

## Finding 6 — Supply is nascent, demand is unmeasurable-and-≈0: the metric can't be collected yet

**Evidence:** a batch WebMCP probe (crawl + `getTools()` in Chrome 149) of the announced I/O-2026
adopters, 2026-07-16:

| Platform | WebMCP origin-trial token | Live registered tools |
|---|---|---|
| **Shopify** (via `en.nutri-bay.com`) | yes | **10** (search_catalog … proceed_to_checkout) |
| Booking.com | no | 0 |
| Etsy | no | 0 |
| Instacart | no | 0 |
| Target | no | 0 |
| Expedia | no | 0 |
| Redfin | no | 0 |

(Caveat: homepages only, from an EU IP; deeper/logged-in pages may differ. But **no origin-trial
token means WebMCP is not enabled in production Chrome for that origin's scripts** regardless — so
these are not shipping tools to real users yet.) **Only Shopify has actually deployed; every other
announced adopter is announcement-only.** Live tool execution was confirmed on Shopify:
`search_catalog({catalog:{query:"caffeine gel"}})` returns structured products + agent "next
steps"; `get_cart` returns a structured empty cart. (API notes: `executeTool` takes the *tool
object* from `getTools()`, and arguments must be a JSON *string*.)

**Two structural limits on measuring demand (does anyone actually *invoke* these?):**

1. **Our logger only sees tools we instrument on sites we control.** `logger.js` runs where we
   inject it; we cannot inject into a third party's production pages, so we cannot observe real
   end-users' agent invocations on Shopify/booking.com/etc. *Supply* (who exposes tools) is
   crawlable at scale; *demand* (who calls them) is not — except on a property we own (inject a
   global `executeTool` shim → capture even the platform's own tool calls) or by driving an agent
   ourselves (synthetic, not organic).
2. **The consumer isn't live.** Gemini-in-Chrome's WebMCP support is "coming soon" (Chrome blog),
   so organic invocation volume is structurally ≈ 0 today for everyone.

**Go/no-go implication — this is the sharpest finding.** The core Experiment B metric, *real
agent-invocation volume*, **cannot be collected by anyone right now** — the supply side is one
platform deep and the demand side has no shipped consumer. So the honest answer to "are LLMs
already using WebMCP?" is **no, not yet, and it isn't yet measurable**. This reframes the build:
stand up and validate the measurement loop (US4–6) so it is ready the moment agents arrive, prove
it end-to-end with synthetic invocations, and treat "when do browser agents ship WebMCP
consumption, and does Shopify's lead widen or stay lonely?" as the real gating signal to re-check
on a cadence — not something to sit and wait on for 4–6 weeks now.

---

## Consequences for the tool (tracked as spec changes)

- **Crawl must descend into iframes** (Playwright can reach cross-origin frames) and **tag each
  candidate with its frame and whether the site owner can instrument it** — so a run *reports*
  "the primary action is a third-party Zenchef widget you cannot instrument" instead of
  silently missing the form. (FR-018; implemented after this finding was recorded.)
- The category-3 pass on `gct.lu` should be re-read once iframe-descent lands — the newsletter
  form we first drafted against was **not** the page's real action.
- **Crawl must wait for SPAs to settle before extracting** — wait for network idle (bounded,
  best-effort) after `load`, or client-rendered pages report only their shell. (FR-019;
  implemented after Finding 4.)
- **Origin-trial detection must decode the token, not just spot the meta tag.** salonkee's page
  carries an `origin-trial` token — but decoding it shows `feature:
  DisableThirdPartyStoragePartitioning3` (a Google/reCAPTCHA trial), not WebMCP. Reporting mere
  token *presence* as "already uses WebMCP" is a false positive that would corrupt the go/no-go
  read on any site embedding Google widgets. The tool now decodes each token's `feature` and
  only claims WebMCP on a match. (FR-017 tightened; the decoder must skip the 64-byte signature,
  whose random bytes can contain `{`/`}`.)
