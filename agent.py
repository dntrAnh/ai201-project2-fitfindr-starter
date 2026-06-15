"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card, assess_price


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "price_assessment": None,    # string returned by assess_price (stretch)
        "retry_note": None,          # set when auto-retry loosened constraints
        "error": None,               # set if the interaction ended early
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_query(query: str) -> tuple[str, str | None, float | None]:
    """Parse a natural language query into (description, size, max_price)."""
    price_match = re.search(
        r"(?:under|below|max|up to)\s*\$?(\d+(?:\.\d+)?)", query, re.IGNORECASE
    )
    max_price = float(price_match.group(1)) if price_match else None

    size_match = re.search(r"\bsize\s+([A-Z0-9/]+)\b", query, re.IGNORECASE)
    size = size_match.group(1).upper() if size_match else None

    description = re.sub(
        r"(under|below|max|up to)\s*\$?\d+(?:\.\d+)?", "", query, flags=re.IGNORECASE
    )
    description = re.sub(r"\bsize\s+\S+", "", description, flags=re.IGNORECASE)
    description = re.sub(
        r"\b(looking for|i want|find me|i need)\b", "", description, flags=re.IGNORECASE
    )
    description = description.strip(" ,.")
    return description, size, max_price


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse query
    description, size, max_price = _parse_query(query)
    session["parsed"] = {"description": description, "size": size, "max_price": max_price}

    # Step 3: Call search_listings, auto-retry with loosened constraints on empty
    results = search_listings(description, size=size, max_price=max_price)

    if not results and size is not None:
        results = search_listings(description, size=None, max_price=max_price)
        if results:
            session["retry_note"] = (
                f"No results for size {size} — showing results for any size instead."
            )
            size = None

    if not results and max_price is not None:
        loosened = round(max_price * 1.5)
        results = search_listings(description, size=size, max_price=loosened)
        if results:
            session["retry_note"] = (
                f"No results under ${int(max_price)} — "
                f"showing results up to ${loosened} instead."
            )
            max_price = float(loosened)

    if not results:
        first_keyword = description.split()[0] if description.split() else description
        results = search_listings(first_keyword, size=None, max_price=None)
        if results:
            session["retry_note"] = (
                f"No exact matches — showing results for '{first_keyword}' "
                f"with all filters removed."
            )

    session["search_results"] = results

    if not results:
        size_hint = f" in size {size}" if size else ""
        price_hint = f" under ${int(max_price)}" if max_price else ""
        session["error"] = (
            f"No listings found for '{description}'{size_hint}{price_hint}. "
            f"Try broadening your search: remove the size filter, increase your "
            f"budget, or search for a different style."
        )
        return session

    # Step 4: Select top result
    session["selected_item"] = results[0]

    # Step 4b: Assess price (stretch)
    session["price_assessment"] = assess_price(session["selected_item"])

    # Step 5: Suggest outfit (trend-aware)
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    # Step 6: Create fit card
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: Return completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found:            {session['selected_item']['title']}")
        print(f"Price assessment: {session['price_assessment']}")
        print(f"Retry note:       {session['retry_note']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path (impossible query) ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"fit_card is None: {session2['fit_card'] is None}")

    print("\n\n=== Auto-retry path (tight price, has size) ===\n")
    session3 = run_agent(
        query="vintage jacket size S under $10",
        wardrobe=get_example_wardrobe(),
    )
    if session3["error"]:
        print(f"Error: {session3['error']}")
    else:
        print(f"Found:      {session3['selected_item']['title']}")
        print(f"Retry note: {session3['retry_note']}")
