# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## AI Usage

### Instance 1 — Implementing `search_listings` (Milestone 3)

**Input given to Claude:** The Tool 1 block from `planning.md` — specifically the description ("Loads all listings via `load_listings()` and filters them against user criteria"), the three typed input parameters (`description: str`, `size: str | None`, `max_price: float | None`), the return value spec (list of listing dicts sorted by relevance, empty list on no match), and the failure mode (return `[]`, never raise).

**What it produced:** A working implementation that called `load_listings()`, looped over listings to apply price and size filters, split the description into keywords, counted keyword matches across `title`, `description`, and `style_tags`, and sorted by score descending.

**What I changed before using it:** Two things. First, the model name in the Groq call was `mixtral-8x7b-32768` — that model has been decommissioned, so I updated it to `llama-3.3-70b-versatile`. Second, the size filter used exact equality (`listing["size"] == size`) which would miss cases like `"M"` not matching `"S/M"`. I changed it to a case-insensitive substring check (`size.upper() in listing["size"].upper()`).

---

### Instance 2 — Implementing `run_agent()` planning loop (Milestone 4)

**Input given to Claude:** The Planning Loop section (numbered 6-step conditional logic), the State Management section (session dict key table), and the Architecture diagram from `planning.md`. Also shared the `_new_session()` stub and the TODO comments in `agent.py`.

**What it produced:** A complete `run_agent()` function that initialized the session, parsed the query with regex, called `search_listings`, branched on empty results to set `session["error"]` and return early, then chained `suggest_outfit` and `create_fit_card` with state stored in the session dict at each step.

**What I changed before using it:** The `import re` was placed at the top of the file rather than inside the function body. I also tightened the size regex — the generated pattern matched too broadly (single letters like `"I"` or `"a"` from mid-sentence words), so I restricted it to only trigger on `"size X"` phrasing or known size tokens (`S`, `M`, `L`, `XL`, `W28`, etc.) as a dedicated capture group.

---

## Stretch Features

### Price Assessment

`assess_price(item)` in `tools.py` compares the listing's price against all other listings in the same **category** that share at least one **style tag** with the item. From that comparable set it computes the price range, average, and what percentile the listing falls in (e.g. "better priced than 75% of comparable listings"). The result is labelled **great deal**, **fair price**, or **on the higher end** based on percentile thresholds (≥70% → great deal, ≥40% → fair price, <40% → higher end). If no same-category listings share a style tag, it falls back to all same-category listings. The comparable set size is always shown so the user can judge confidence.

### Trend-Influenced Outfit Suggestions

`get_trending_styles()` in `tools.py` counts style-tag frequency across all 40 listings in `data/listings.json` and returns the top 5 most-listed tags (e.g. `vintage`, `streetwear`, `classic`, `y2k`, `earth tones`). The data source is the listings dataset itself — no external API. `suggest_outfit()` calls this function and injects the result into the LLM prompt: *"Currently trending styles in the dataset: vintage, streetwear, classic, y2k, earth tones — lean into whichever of these apply."* This means trend data visibly shapes the outfit suggestion; a y2k item during a y2k-trending period will get richer y2k-specific styling notes than it would otherwise.

### Auto-Retry on Zero Results

When `search_listings` returns an empty list, `run_agent()` attempts up to three progressively looser retries before giving up:

1. **Drop size filter** — retry with `size=None`, note: *"No results for size M — showing results for any size instead."*
2. **Raise price ceiling 50%** — retry with `max_price *= 1.5`, note: *"No results under $30 — showing results up to $45 instead."*
3. **First keyword only, no filters** — retry with only the first word of the description and no size/price constraints, note: *"No exact matches — showing results for 'vintage' with all filters removed."*

If all three retries still return nothing, the original no-results error message is set in `session["error"]`. On a successful retry `session["retry_note"]` is populated and shown to the user above the listing panel so they know what was adjusted.