# tests/test_failure_modes.py

"""
Milestone 5: Test Every Failure Mode Deliberately

These tests intentionally trigger failure cases:
1. search_listings returns zero results
2. suggest_outfit receives an empty wardrobe
3. create_fit_card receives an empty outfit string
4. compare_price receives bad/missing data or no comparable listings

The goal is NOT to make the program crash.
The goal is to prove the agent recovers gracefully.
"""

from tools import search_listings, suggest_outfit, create_fit_card, compare_price


# Fake item used for testing tools that need a selected listing
FAKE_ITEM = {
    "id": "test-001",
    "title": "Vintage Graphic Tee",
    "description": "A faded vintage graphic tee with streetwear style",
    "category": "tops",
    "style_tags": ["vintage", "graphic", "streetwear"],
    "size": "M",
    "condition": "Good",
    "price": 25.00,
    "colors": ["black", "white"],
    "brand": "Test Brand",
    "platform": "Depop",
}


def test_search_listings_no_results_returns_empty_list():
    """
    Failure mode:
    User searches for something impossible.

    Expected:
    search_listings should return [] instead of crashing.
    """

    results = search_listings(
        description="designer ballgown",
        size="XXS",
        max_price=5
    )

    assert results == []


def test_suggest_outfit_empty_wardrobe_returns_fallback_string():
    """
    Failure mode:
    User has an empty wardrobe.

    Expected:
    suggest_outfit should return helpful styling advice,
    not crash and not return an empty string.
    """

    empty_wardrobe = {"items": []}

    result = suggest_outfit(FAKE_ITEM, empty_wardrobe)

    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_create_fit_card_empty_outfit_returns_fallback_string():
    """
    Failure mode:
    create_fit_card receives an empty outfit string.

    Expected:
    It should return a helpful fallback caption or error message,
    not crash.
    """

    result = create_fit_card("", FAKE_ITEM)

    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_compare_price_missing_item_returns_fallback_string():
    """
    Failure mode:
    compare_price receives no selected item.

    Expected:
    It should return a helpful fallback message instead of crashing.
    """

    result = compare_price(None)

    assert isinstance(result, str)
    assert len(result.strip()) > 0
    assert "not enough" in result.lower() or "missing" in result.lower()


def test_compare_price_no_comparable_listings_returns_fallback(monkeypatch):
    """
    Failure mode:
    compare_price cannot find similar listings.

    Expected:
    It should return a fallback message saying there is not enough data.
    """

    # Fake listings that are not similar to FAKE_ITEM
    fake_listings = [
        {
            "id": "shoe-001",
            "title": "Running Shoes",
            "category": "shoes",
            "style_tags": ["athletic", "running"],
            "price": 80.00,
        },
        {
            "id": "bag-001",
            "title": "Leather Tote Bag",
            "category": "accessories",
            "style_tags": ["minimal", "formal"],
            "price": 50.00,
        },
    ]

    # Replace load_listings() temporarily so this test controls the data
    monkeypatch.setattr("tools.load_listings", lambda: fake_listings)

    result = compare_price(FAKE_ITEM)

    assert isinstance(result, str)
    assert len(result.strip()) > 0
    assert "not enough" in result.lower() or "similar" in result.lower()