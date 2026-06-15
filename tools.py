"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str

Stretch tools:
    assess_price(item)                             → str
    get_trending_styles(top_n)                     → list[str]
"""

import os
from collections import Counter

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    keywords = set(description.lower().split())

    scored_listings = []
    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue

        if size is not None and size.upper() not in listing["size"].upper():
            continue

        search_text = (
            f"{listing['title']} {listing['description']} "
            f"{' '.join(listing['style_tags'])}"
        ).lower()

        score = sum(1 for keyword in keywords if keyword in search_text)

        if score > 0:
            scored_listings.append((score, listing))

    scored_listings.sort(key=lambda x: x[0], reverse=True)
    return [listing for _, listing in scored_listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    item_title = new_item.get("title", "item")
    item_colors = ", ".join(new_item.get("colors", []))
    item_tags = ", ".join(new_item.get("style_tags", []))
    item_category = new_item.get("category", "piece")

    # Inject trending styles so the LLM can lean into relevant ones
    trending = get_trending_styles()
    trend_note = f"Currently trending styles: {', '.join(trending)}. Lean into whichever apply to this item."

    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        prompt = f"""You are a fashion stylist. A user is considering buying this thrifted item:

        Title: {item_title}
        Category: {item_category}
        Colors: {item_colors}
        Style: {item_tags}

        {trend_note}

        They don't have their wardrobe details yet. Suggest 2-3 general outfit ideas for this item.
        Be specific about what types of pieces would pair well (e.g., "dark jeans", "white sneakers", "leather jacket").
        Include one concrete styling tip (e.g., "roll the sleeves" or "tuck it in").
        Keep it casual and authentic, as if giving advice to a friend."""
    else:
        wardrobe_list = "\n".join(
            f"- {item['name']} ({item['category']}) — colors: {', '.join(item['colors'])}, style: {', '.join(item['style_tags'])}"
            for item in wardrobe_items
        )

        prompt = f"""You are a fashion stylist. A user is considering buying this thrifted item:

        Title: {item_title}
        Category: {item_category}
        Colors: {item_colors}
        Style: {item_tags}

        {trend_note}

        Here's their existing wardrobe:
        {wardrobe_list}

        Suggest 1-2 complete outfits using the new item with specific pieces from their wardrobe.
        Name the exact pieces by their names.
        Explain why these pieces complement the new item (color, style, silhouette).
        Include one concrete styling tip (e.g., "tuck the front corner" or "roll the sleeves").
        Keep it casual and authentic."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    client = _get_groq_client()

    item_title = new_item.get("title", "item")
    item_price = new_item.get("price", 0)
    item_platform = new_item.get("platform", "depop")

    outfit_text = (outfit or "").strip()

    if outfit_text:
        prompt = f"""You are a fashion influencer writing an Instagram/TikTok caption for a thrifted OOTD post.

        Item: {item_title}
        Price: ${item_price}
        Platform: {item_platform}

        Styling notes: {outfit_text}

        Write a 2-3 sentence casual, authentic caption for this fit. Include:
        - The item name and price naturally in the caption
        - The platform (e.g., "off depop", "from thredUp")
        - At least one specific styling detail from the notes
        - A casual, conversational tone (like you're sharing with a friend)

        Examples style:
        - "thrifted this vintage tee off depop for $24 and honestly it's perfect with my baggy jeans 🖤"
        - "just scored this dress from thredUp for $18 and the fit is insane"

        Write ONLY the caption, no extra text."""
    else:
        prompt = f"""You are a fashion influencer writing a brief Instagram/TikTok caption for a thrifted item post.

        Item: {item_title}
        Price: ${item_price}
        Platform: {item_platform}

        Write a 1-2 sentence casual caption mentioning the item, price, and platform. Be authentic and conversational.
        Write ONLY the caption, no extra text."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=150,
        temperature=0.9,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


# ── Stretch tool: get_trending_styles ─────────────────────────────────────────

def get_trending_styles(top_n: int = 5) -> list[str]:
    """
    Return the top N trending style tags by frequency across all listings.

    Data source: style_tag counts from data/listings.json — no external API.

    Args:
        top_n: Number of top tags to return (default 5).

    Returns:
        List of style tag strings, most frequent first.
    """
    listings = load_listings()
    all_tags = [tag for listing in listings for tag in listing.get("style_tags", [])]
    return [tag for tag, _ in Counter(all_tags).most_common(top_n)]


# ── Stretch tool: assess_price ────────────────────────────────────────────────

def assess_price(item: dict) -> str:
    """
    Compare the listing's price against comparable listings in the dataset.

    Comparables are listings in the same category that share at least one
    style tag. Falls back to all same-category listings if no overlap exists.

    Args:
        item: A listing dict from search_listings().

    Returns:
        A plain-text price assessment string with label, range, average,
        and percentile. Never raises — returns a fallback string if the
        comparable set is empty.
    """
    listings = load_listings()
    category = item.get("category", "")
    item_tags = set(item.get("style_tags", []))
    item_price = item.get("price", 0)

    # Prefer same category + at least 1 shared style tag
    comparables = [
        l for l in listings
        if l["id"] != item["id"]
        and l["category"] == category
        and set(l.get("style_tags", [])) & item_tags
    ]

    # Fall back to same category only
    if not comparables:
        comparables = [
            l for l in listings
            if l["id"] != item["id"] and l["category"] == category
        ]

    if not comparables:
        return f"${item_price:.0f} — not enough comparable listings to assess."

    prices = [l["price"] for l in comparables]
    avg = sum(prices) / len(prices)
    # % of comparables that cost MORE than this item
    pct_cheaper = int(sum(1 for p in prices if p > item_price) / len(prices) * 100)

    if pct_cheaper >= 70:
        label = "great deal 🟢"
    elif pct_cheaper >= 40:
        label = "fair price 🟡"
    else:
        label = "on the higher end 🔴"

    return (
        f"${item_price:.0f} — {label}\n"
        f"Compared to {len(comparables)} similar {category} listings:\n"
        f"  Range:   ${min(prices):.0f} – ${max(prices):.0f}\n"
        f"  Average: ${avg:.0f}\n"
        f"  Better priced than {pct_cheaper}% of comparable listings."
    )
