# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Loads all listings via `load_listings()` and filters them against the user's criteria. Returns a ranked list of matching listings, best match first.

**Input parameters:**
- `description` (str): Free-text keyword(s) to match against `title`, `description`, and `style_tags` fields (e.g., `"vintage graphic tee"`).
- `size` (str, optional): Exact size string to match against the listing's `size` field (e.g., `"M"`, `"W30 L30"`).
- `max_price` (float, optional): Upper bound matched against the listing's `price` field; listings with `price > max_price` are excluded.

**What it returns:**
A list of listing dicts, each containing: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str — one of `excellent`, `good`, `fair`), `price` (float), `colors` (list[str]), `brand` (str or None), `platform` (str — one of `depop`, `thredUp`, `poshmark`). List is sorted so the highest-relevance result is at index 0. Returns an empty list if nothing matches.

**What happens if it fails or returns nothing:**
If the returned list is empty, the agent sets an error message explaining what the user can adjust (e.g., "No listings found for 'vintage graphic tee' in size M under $30 — try raising your price or searching without a size filter.") and returns early. `suggest_outfit` and `create_fit_card` are not called.

---

### Tool 2: suggest_outfit

**What it does:**
Given a new listing item and the user's wardrobe, picks the best matching pieces from the wardrobe and returns a specific outfit suggestion with concrete styling tips.

**Input parameters:**
- `new_item` (dict): The listing selected from `search_listings` results — same fields as a listing dict (`id`, `title`, `category`, `style_tags`, `colors`, etc.).
- `wardrobe` (dict): A wardrobe object with a single key `"items"` containing a list of wardrobe item dicts. Each wardrobe item has: `id` (str), `name` (str), `category` (str), `colors` (list[str]), `style_tags` (list[str]), `notes` (str or None). Loaded via `get_example_wardrobe()` or `get_empty_wardrobe()` from `data_loader.py`.

**What it returns:**
A plain-text outfit suggestion string naming specific wardrobe pieces by their `name` field, explaining why they complement the new item (color, style, silhouette), and including at least one concrete styling tip (e.g., "tuck the front corner, roll the sleeves once").

**What happens if it fails or returns nothing:**
If `wardrobe["items"]` is empty, the agent generates a generic suggestion based solely on the new item's `style_tags` and `colors`, and appends a prompt: "Share your wardrobe for a more personalized suggestion." The flow continues to `create_fit_card` regardless.

---

### Tool 3: create_fit_card

**What it does:**
Takes the outfit suggestion and the new listing item and generates a short, first-person social media caption written in the voice of someone who just thrifted the piece — casual, specific, and share-ready.

**Input parameters:**
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`, naming the pieces and styling tips.
- `new_item` (dict): The selected listing dict, used to pull `title`, `price`, and `platform` for the caption (e.g., "depop for $22").

**What it returns:**
A single plain-text caption string: 1–3 sentences, first-person, conversational tone. References the specific item and at least one outfit detail. Example: *"thrifted this faded bootleg tee off depop for $24 and it was made for my baggy jeans 🖤 styled it tucked with chunky sneakers and I'm never taking it off"*.

**What happens if it fails or returns nothing:**
If `outfit` is an empty string or None, the agent falls back to generating a caption from `new_item` alone (title, price, platform). The fit card is always returned — there is no early-exit path from this tool.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

The planning loop runs once per user request and executes tools in a fixed sequence, with one conditional branch:

1. **Parse the user message** to extract `description`, `size` (optional), and `max_price` (optional). Call `search_listings(description, size, max_price)`.
2. **Check results:** If `results` is an empty list → set `error = "No listings found for <query>. Try adjusting your size or price."` and return the error message to the user. Stop here — do not proceed.
3. **If results is non-empty:** Set `session["selected_item"] = results[0]`. Call `suggest_outfit(new_item=session["selected_item"], wardrobe=get_example_wardrobe())`.
4. **Store the suggestion:** Set `session["outfit_suggestion"] = <returned string>`. (If the string is empty, store a fallback generic suggestion — do not stop.)
5. **Call `create_fit_card(outfit=session["outfit_suggestion"], new_item=session["selected_item"])`.**
6. **Store and return:** Set `session["fit_card"] = <returned string>`. Return the fit card string to the user.

The loop has no retry logic — each tool is called exactly once. The only early-exit is after `search_listings` returns empty.

---

## State Management

**How does information from one tool get passed to the next?**

The agent maintains a `session` dict for the duration of a single request. Keys written during execution:

| Key | Set after | Value |
|-----|-----------|-------|
| `selected_item` | `search_listings` returns non-empty | `results[0]` — the top-ranked listing dict |
| `outfit_suggestion` | `suggest_outfit` returns | The outfit suggestion string |
| `fit_card` | `create_fit_card` returns | The final caption string |

Each tool receives its inputs directly from the session rather than re-calling prior tools. No state persists between separate user requests.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Return exactly: *"No listings found for 'vintage graphic tee' in size M under $30. Try broadening your search: remove the size filter, increase your budget, or search for a different style. For example: 'vintage tee under $40'."* Do not call any further tools; return immediately to the user. |
| suggest_outfit | Wardrobe is empty (`items: []`) | Generate a suggestion based on the new item's `style_tags` and `colors` only. Example: *"This black graphic tee would look great with dark jeans and sneakers for a classic streetwear vibe. Tuck it slightly for shape."* Then append: *"💡 Tip: Share your wardrobe to get a personalized outfit suggestion!"* Continue to `create_fit_card` (do not stop). |
| create_fit_card | `outfit` input is empty or None | Build a minimal caption from `new_item` fields: *"just thrifted [TITLE] from [PLATFORM] for $[PRICE]!"* Example: *"just thrifted Graphic Tee — 2003 Tour Bootleg Style from depop for $24!"* Always returns a caption — there is no early-exit; the fit card is always shown. |

---

## Architecture

```
User query: "vintage graphic tee, size M, under $30, I wear baggy jeans + chunky sneakers"
    │
    ▼
Planning Loop
    │
    ├─► search_listings(description="vintage graphic tee", size="M", max_price=30.0)
    │       │
    │       │ results == []
    │       ├──────────────────────────────────────────────────────────────────────►  [STOP]
    │       │                                                          "No listings found.
    │       │                                                           Try adjusting size
    │       │                                                           or price." → user
    │       │ results == [item, ...]
    │       ▼
    │   Session: selected_item = results[0]
    │   (e.g. "Graphic Tee — 2003 Tour Bootleg Style, $24, depop")
    │       │
    ├─► suggest_outfit(new_item=selected_item, wardrobe=get_example_wardrobe())
    │       │
    │       │ wardrobe.items == []
    │       ├──► generic suggestion from new_item style_tags/colors only
    │       │    + "Share your wardrobe for better suggestions"
    │       │         │
    │       │ wardrobe.items non-empty
    │       ▼
    │   Session: outfit_suggestion =
    │   "Pair with your baggy straight-leg jeans and chunky white sneakers.
    │    Tuck the front corner slightly for shape."
    │       │
    └─► create_fit_card(outfit=outfit_suggestion, new_item=selected_item)
            │
            │ outfit == None or ""
            ├──► caption built from new_item title/price/platform only
            │
            │ outfit non-empty
            ▼
        Session: fit_card =
        "thrifted this 2003 bootleg tee off depop for $24 and it was made
         for my baggy jeans 🖤 tucked the front corner and I'm never taking it off"
            │
            ▼
        Return fit_card → user
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

For each tool, I'll give Claude the specific tool section from planning.md (name, description, inputs, return value, failure mode) plus the data loader utility guide. I'll ask it to implement the function in `tools.py`, assuming `load_listings()` is already imported.

- **search_listings**: Give Claude the Tool 1 block and ask it to filter listings by `description` (keyword match against title/description/style_tags), `size`, and `max_price`. Expect a function that returns a sorted list (highest relevance first) or an empty list. Verify by: (1) checking that empty input returns `[]`, (2) testing with `description="vintage jeans"` and expecting the Levi's listing first, (3) testing with `max_price=20.0` and confirming no items over $20 are returned.

- **suggest_outfit**: Give Claude the Tool 2 block and wardrobe_schema.json, and ask it to match new_item colors/style_tags against wardrobe items, pick 2–3 pieces, and return a sentence or two naming them with one styling tip. Verify by: (1) checking that an empty wardrobe returns a generic suggestion, (2) testing with a known item (e.g., "Vintage Levi's 501 Jeans") and the example wardrobe, expecting at least one piece name and one tip in the output.

- **create_fit_card**: Give Claude the Tool 3 block and ask it to build a first-person caption (1–3 sentences) referencing the new_item title/price/platform and the outfit description. Verify by: (1) checking that an empty outfit string still produces a caption, (2) testing with a real item and outfit suggestion, confirming the caption mentions the item and platform.

**Milestone 4 — Planning loop and state management:**

Give Claude the Planning Loop, State Management, and Architecture sections plus the complete error handling table. Ask it to implement the `run_agent(user_message: str)` function in `agent.py` that: (1) parses user input to extract description, size, max_price, (2) calls `search_listings` and handles empty results by returning an error early, (3) on success, calls `suggest_outfit` with the top result and the example wardrobe, (4) calls `create_fit_card` with the outfit suggestion and item, (5) returns the fit_card string.

Verify by: (1) tracing through with the example query and checking that the output is a reasonable caption, (2) testing with a query that yields no results and confirming the agent returns a helpful error message, (3) stepping through the code to confirm session keys are set in the right order and values flow correctly to the next tool.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1 — Parse and call search_listings:**
The planning loop parses the user message and extracts: `description="vintage graphic tee"`, `size=None`, `max_price=30.0`. Calls `search_listings("vintage graphic tee", size=None, max_price=30.0)`.

search_listings loads all listings via `load_listings()` and filters: keyword-matches "vintage graphic tee" across title/description/style_tags, excludes any with `price > 30.0`. Returns a sorted list:
```
[
  {id: "lst_006", title: "Graphic Tee — 2003 Tour Bootleg Style", price: 24.00, ...},
  {id: "lst_002", title: "Y2K Baby Tee — Butterfly Print", price: 18.00, ...}
]
```
(Assuming these are the only matches under $30 with "vintage" and "graphic tee" in their metadata.)

Session state: `selected_item = results[0]` = the 2003 Bootleg tee.

**Step 2 — Call suggest_outfit:**
The loop calls `suggest_outfit(new_item=session["selected_item"], wardrobe=get_example_wardrobe())`. The example wardrobe includes: baggy dark-wash jeans, chunky white sneakers, black denim jacket, oversized grey sweatshirt, black cropped zip hoodie, and others.

suggest_outfit matches the tee's tags (graphic tee, vintage, grunge, streetwear, black) against the wardrobe and selects the baggy jeans (streetwear, denim) and chunky sneakers (streetwear, chunky) as best matches. Returns:

```
"Pair this faded bootleg with your baggy dark-wash jeans and chunky white sneakers 
for a classic 90s streetwear look. Roll the sleeves once and tuck the front corner 
slightly for shape."
```

Session state: `outfit_suggestion = <string above>`.

**Step 3 — Call create_fit_card:**
The loop calls `create_fit_card(outfit=session["outfit_suggestion"], new_item=session["selected_item"])`. The tool uses the outfit description ("Pair this faded bootleg...") and the item metadata (title: "Graphic Tee — 2003 Tour Bootleg Style", price: 24.00, platform: "depop") to generate a casual caption.

Returns:
```
"thrifted this faded bootleg tee off depop for $24 and it was made for my baggy jeans 
and chunky sneakers 🖤 roll the sleeves once and tuck the corner — 90s vibes locked in"
```

Session state: `fit_card = <string above>`.

**Final output to user:**
The planning loop returns the fit_card string to the user:

> *"thrifted this faded bootleg tee off depop for $24 and it was made for my baggy jeans and chunky sneakers 🖤 roll the sleeves once and tuck the corner — 90s vibes locked in"*

The user sees exactly one piece of output: the caption, ready to copy and post.
