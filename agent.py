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

from tools import search_listings, compare_price, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "price_comparison": None,     # string returned by compare_price
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── query parsing ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural language query.

    Uses simple regex/string logic. Handles phrasings such as:
        "looking for a vintage graphic tee under $30"
        "designer ballgown size XXS under $5"
        "vintage graphic tee under 30 size M"

    Returns a dict with keys: description (str), size (str | None),
    max_price (float | None).
    """
    text = query.strip()

    # max_price: "under $30", "under 30", "below $5", "less than 25"
    max_price = None
    price_match = re.search(
        r"(?:under|below|less than|max|up to)\s*\$?\s*(\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if price_match:
        max_price = float(price_match.group(1))

    # size: "size M", "size XXS" — recognized size tokens only.
    size = None
    size_match = re.search(
        r"size\s+(XXS|XS|S|M|L|XL|XXL|XXXL|\d{1,2})\b",
        text,
        flags=re.IGNORECASE,
    )
    if size_match:
        size = size_match.group(1).upper()

    # description: strip the matched price/size phrases and common filler words.
    description = text
    if price_match:
        description = description.replace(price_match.group(0), " ")
    if size_match:
        description = description.replace(size_match.group(0), " ")

    description = re.sub(
        r"\b(?:i'?m\s+)?(?:looking for|searching for|search for|find me|"
        r"find|want|need|show me)\b",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    # Drop leading articles and collapse whitespace.
    description = re.sub(r"^\s*(?:a|an|the)\s+", " ", description, flags=re.IGNORECASE)
    description = re.sub(r"\s+", " ", description).strip(" .,")

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


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

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().



        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1: Initialize the session — single source of truth for this run.
    session = _new_session(query, wardrobe)

    # Step 2: Parse the query into description, size, and max_price.
    session["parsed"] = _parse_query(query)
    description = session["parsed"]["description"]
    size = session["parsed"]["size"]
    max_price = session["parsed"]["max_price"]

    # Step 3: Search listings with the parsed parameters.
    session["search_results"] = search_listings(description, size, max_price)

    # Error path: no matching listings — end the interaction early.
    if not session["search_results"]:
        session["error"] = (
            "No matching items found for your search. Try a different style, "
            "a different size, or a higher price limit."
        )
        return session

    # Step 4: Select the top result as the item to style.
    session["selected_item"] = session["search_results"][0]

    # Tool 4: compare the selected item's price against similar listings.
    # Only runs when a listing was found — the no-results path returned above.
    session["price_comparison"] = compare_price(session["selected_item"])

    # Step 5: Suggest an outfit using the selected item and the wardrobe.
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    # Step 6: Turn the outfit suggestion into a shareable fit card.
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: Return the completed session.
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: vintage graphic tee under $30 ===\n")
    session = run_agent(
        query="vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    print("Selected item:")
    print(session["selected_item"])
    print("\nPrice comparison:")
    print(session["price_comparison"])
    print("\nOutfit suggestion:")
    print(session["outfit_suggestion"])
    print("\nFit card:")
    print(session["fit_card"])

    print("\n\n=== No results: designer ballgown size XXS under $5 ===\n")
    no_results = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print("error:", no_results["error"])
    print("price_comparison:", no_results["price_comparison"])
    print("fit_card:", no_results["fit_card"])
    # Prove the conditional loop held: no later tools ran on the no-results path.
    assert no_results["error"] is not None
    assert no_results["price_comparison"] is None
    assert no_results["fit_card"] is None
    print("\nOK: no-results path set error and skipped tools 2-4.")

