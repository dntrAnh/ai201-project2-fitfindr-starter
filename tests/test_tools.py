"""
pytest tests for FitFindr tools.
Run with: pytest tests/test_tools.py -v
"""

import pytest
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ─────────────────────────────────────────────────────────────────────
# TOOL 1: search_listings
# ─────────────────────────────────────────────────────────────────────


class TestSearchListings:
    """Tests for search_listings tool."""

    def test_search_returns_results(self):
        """Test that search returns a list of results."""
        results = search_listings("vintage graphic tee", max_price=50)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_search_empty_results(self):
        """Test that impossible search returns empty list (no exception)."""
        results = search_listings("designer ballgown", size="XXS", max_price=5)
        assert results == []

    def test_search_price_filter(self):
        """Test that price filter excludes items over max_price."""
        results = search_listings("jacket", max_price=30.0)
        assert all(item["price"] <= 30.0 for item in results)

    def test_search_size_filter(self):
        """Test that size filter works (case-insensitive, partial match)."""
        results = search_listings("jeans", size="W30")
        assert all("W30" in item["size"].upper() for item in results)

    def test_search_keyword_scoring(self):
        """Test that results are sorted by relevance (best match first)."""
        results = search_listings("vintage graphic tee", max_price=50)
        # First result should have highest keyword match
        assert len(results) > 0
        first_item = results[0]
        # Should contain keywords from search
        text = f"{first_item['title']} {first_item['description']}".lower()
        assert any(kw in text for kw in ["vintage", "graphic", "tee"])

    def test_search_returns_full_listing_dict(self):
        """Test that each result has all required fields."""
        results = search_listings("vintage", max_price=50)
        required_fields = [
            "id", "title", "description", "category", "style_tags",
            "size", "condition", "price", "colors", "brand", "platform"
        ]
        assert all(all(field in item for field in required_fields) for item in results)

    def test_search_with_all_filters(self):
        """Test search with description, size, and price all specified."""
        results = search_listings("graphic tee", size="M", max_price=25.0)
        assert all(item["price"] <= 25.0 for item in results)
        assert all("M" in item["size"].upper() for item in results)


# ─────────────────────────────────────────────────────────────────────
# TOOL 2: suggest_outfit
# ─────────────────────────────────────────────────────────────────────


class TestSuggestOutfit:
    """Tests for suggest_outfit tool."""

    @pytest.fixture
    def sample_item(self):
        """Fixture providing a sample listing item."""
        results = search_listings("vintage graphic tee", max_price=30.0)
        return results[0]

    def test_suggest_outfit_with_populated_wardrobe(self, sample_item):
        """Test outfit suggestion with a populated wardrobe."""
        wardrobe = get_example_wardrobe()
        outfit = suggest_outfit(sample_item, wardrobe)

        assert isinstance(outfit, str)
        assert len(outfit) > 0
        # Should mention specific wardrobe pieces by name
        assert any(item["name"].lower() in outfit.lower() for item in wardrobe["items"])

    def test_suggest_outfit_with_empty_wardrobe(self, sample_item):
        """Test outfit suggestion with empty wardrobe (should not crash)."""
        empty_wardrobe = get_empty_wardrobe()
        outfit = suggest_outfit(sample_item, empty_wardrobe)

        assert isinstance(outfit, str)
        assert len(outfit) > 0
        # Should still provide generic suggestions
        assert "pair" in outfit.lower() or "wear" in outfit.lower()

    def test_suggest_outfit_returns_nonempty_string(self, sample_item):
        """Test that suggest_outfit always returns a non-empty string."""
        wardrobe = get_example_wardrobe()
        outfit = suggest_outfit(sample_item, wardrobe)

        assert isinstance(outfit, str)
        assert outfit.strip() != ""

    def test_suggest_outfit_includes_styling_tip(self, sample_item):
        """Test that suggestion includes at least one styling tip."""
        wardrobe = get_example_wardrobe()
        outfit = suggest_outfit(sample_item, wardrobe)
        outfit_lower = outfit.lower()

        # Should contain styling instructions
        styling_verbs = ["tuck", "roll", "layer", "pair", "combine", "wear"]
        assert any(verb in outfit_lower for verb in styling_verbs)


# ─────────────────────────────────────────────────────────────────────
# TOOL 3: create_fit_card
# ─────────────────────────────────────────────────────────────────────


class TestCreateFitCard:
    """Tests for create_fit_card tool."""

    @pytest.fixture
    def sample_item_and_outfit(self):
        """Fixture providing sample item and outfit suggestion."""
        results = search_listings("vintage graphic tee", max_price=30.0)
        item = results[0]
        wardrobe = get_example_wardrobe()
        outfit = suggest_outfit(item, wardrobe)
        return item, outfit

    def test_create_fit_card_with_outfit(self, sample_item_and_outfit):
        """Test caption generation with outfit suggestion."""
        item, outfit = sample_item_and_outfit
        caption = create_fit_card(outfit, item)

        assert isinstance(caption, str)
        assert len(caption) > 0
        # Should mention key words from item (LLM may paraphrase)
        caption_lower = caption.lower()
        item_words = item["title"].lower().split()
        assert any(word in caption_lower for word in item_words[:2])  # First 2 words

    def test_create_fit_card_with_empty_outfit(self, sample_item_and_outfit):
        """Test caption generation with empty outfit (fallback)."""
        item, _ = sample_item_and_outfit
        caption = create_fit_card("", item)

        assert isinstance(caption, str)
        assert len(caption) > 0
        # Should still mention the item (LLM may paraphrase)
        caption_lower = caption.lower()
        item_words = item["title"].lower().split()
        assert any(word in caption_lower for word in item_words[:2])  # First 2 words

    def test_create_fit_card_mentions_price(self, sample_item_and_outfit):
        """Test that caption includes the item price."""
        item, outfit = sample_item_and_outfit
        caption = create_fit_card(outfit, item)

        # Check for price (with or without .0 decimal)
        price = int(item["price"])
        assert f"${price}" in caption or str(price) in caption

    def test_create_fit_card_mentions_platform(self, sample_item_and_outfit):
        """Test that caption includes the platform (depop, thredUp, poshmark)."""
        item, outfit = sample_item_and_outfit
        caption = create_fit_card(outfit, item)

        platform = item["platform"].lower()
        assert platform in caption.lower()

    def test_create_fit_card_returns_nonempty_string(self, sample_item_and_outfit):
        """Test that create_fit_card always returns a non-empty string."""
        item, outfit = sample_item_and_outfit
        caption = create_fit_card(outfit, item)

        assert isinstance(caption, str)
        assert caption.strip() != ""

    def test_create_fit_card_with_none_outfit(self, sample_item_and_outfit):
        """Test caption generation with None outfit (fallback)."""
        item, _ = sample_item_and_outfit
        caption = create_fit_card(None, item)

        assert isinstance(caption, str)
        assert len(caption) > 0

    def test_create_fit_card_outputs_vary(self, sample_item_and_outfit):
        """Test that multiple calls with same input produce different captions (temperature > 0)."""
        item, outfit = sample_item_and_outfit
        captions = [create_fit_card(outfit, item) for _ in range(3)]

        # At least some captions should differ (with temperature=0.9)
        assert not all(c == captions[0] for c in captions), \
            "Captions should vary with temperature > 0"


# ─────────────────────────────────────────────────────────────────────
# END-TO-END: Full Flow
# ─────────────────────────────────────────────────────────────────────


class TestFullFlow:
    """Integration tests for the complete flow."""

    def test_full_flow_search_suggest_caption(self):
        """Test the complete flow: search → suggest → caption."""
        # Step 1: Search
        results = search_listings("vintage graphic tee", max_price=30.0)
        assert len(results) > 0

        item = results[0]

        # Step 2: Suggest outfit
        wardrobe = get_example_wardrobe()
        outfit = suggest_outfit(item, wardrobe)
        assert len(outfit) > 0

        # Step 3: Create fit card
        caption = create_fit_card(outfit, item)
        assert len(caption) > 0

        # Final caption should be coherent
        caption_lower = caption.lower()
        item_words = item["title"].lower().split()
        # Check that first few words from title appear in caption (LLM may paraphrase)
        assert any(word in caption_lower for word in item_words[:2])
