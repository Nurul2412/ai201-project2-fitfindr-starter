"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

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

    # Keywords from the search description, lowercased for case-insensitive overlap.
    keywords = set(description.lower().split())

    results = []
    for listing in listings:
        # Filter by price ceiling (inclusive).
        if max_price is not None and listing["price"] > max_price:
            continue

        # Filter by size — case-insensitive partial match so "M" matches "S/M".
        if size is not None:
            listing_size = (listing.get("size") or "").lower()
            if size.lower() not in listing_size:
                continue

        # Score by keyword overlap across the listing's text fields.
        text_parts = [
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            " ".join(listing.get("style_tags") or []),
            " ".join(listing.get("colors") or []),
            listing.get("brand") or "",
        ]
        listing_words = set(" ".join(text_parts).lower().split())
        score = len(keywords & listing_words)

        # Drop listings with no relevant matches.
        if score == 0:
            continue

        results.append((score, listing))

    # Sort by score, highest first, and return just the listing dicts.
    results.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in results]


# ── Tool 4 (Additional Tool): compare_price ───────────────────────────────────

def compare_price(new_item: dict) -> str:
    """
    Compare the selected item's price against similar listings.
    Returns a short string saying whether the price is a good deal,
    fair price, or overpriced.
    """
    if not new_item or "price" not in new_item:
        return "Not enough info to compare the price with."

    listings = load_listings()

    selected_id = new_item.get("id")
    selected_price = float(new_item.get("price", 0))
    selected_category = str(new_item.get("category", "")).lower()
    selected_tags = set(tag.lower() for tag in new_item.get("style_tags") or [])

    comparable_listings = []

    for item in listings:
        if item.get("id") == selected_id:
            continue

        score = 0

        item_category = str(item.get("category", "")).lower()
        item_tags = set(tag.lower() for tag in item.get("style_tags") or [])

        if item_category == selected_category:
            score += 2

        tag_overlap = selected_tags.intersection(item_tags)
        score += len(tag_overlap)

        if score >= 2 and "price" in item:
            comparable_listings.append(item)

    if not comparable_listings:
        return "Not enough similar listings were found to judge the price fairly."

    prices = [float(item["price"]) for item in comparable_listings]
    average_price = sum(prices) / len(prices)

    if selected_price < average_price * 0.90:
        verdict = "good deal"
    elif selected_price <= average_price * 1.10:
        verdict = "fair price"
    else:
        verdict = "overpriced"

    return (
        f"Price check: {verdict}.\n"
        f"This item is ${selected_price:.2f}. "
        f"Similar listings average around ${average_price:.2f}, "
        f"based on {len(comparable_listings)} comparable item(s)."
    )


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

    item_label = new_item.get("title") or new_item.get("description") or "this item"
    item_lines = [
        f"- Title: {new_item.get('title', 'Unknown')}",
        f"- Category: {new_item.get('category', 'Unknown')}",
        f"- Style tags: {', '.join(new_item.get('style_tags') or []) or 'n/a'}",
        f"- Colors: {', '.join(new_item.get('colors') or []) or 'n/a'}",
        f"- Size: {new_item.get('size', 'n/a')}",
    ]
    item_block = "\n".join(item_lines)

    items = wardrobe.get("items") or []

    if not items:
        # Empty wardrobe: ask for general styling ideas, no specific pieces.
        prompt = (
            f"A user is considering buying this thrifted item:\n{item_block}\n\n"
            "They have not shared any wardrobe items yet. Give general styling "
            "advice for this piece: what kinds of items pair well with it, what "
            "vibe or occasions it suits, and a couple of complete outfit ideas. "
            "Keep it clear and concise."
        )
    else:
        # Format wardrobe pieces so the LLM can reference them by name.
        wardrobe_lines = []
        for w in items:
            name = w.get("title") or w.get("name") or "item"

            category = w.get("category")
            colors = ", ".join(w.get("colors") or [])
            style_tags = ", ".join(w.get("style_tags") or [])
            notes = w.get("notes")

            details_parts = []

            if category:
                details_parts.append(category)

            if colors:
                details_parts.append(colors)

            if style_tags:
                details_parts.append(f"styles: {style_tags}")

            if notes:
                details_parts.append(f"notes: {notes}")

            details = ", ".join(details_parts)

            wardrobe_lines.append(
                f"- {name}" + (f" ({details})" if details else "")
            )

        wardrobe_block = "\n".join(wardrobe_lines)

        prompt = (
            f"A user is considering buying this thrifted item:\n{item_block}\n\n"
            f"Here is their current wardrobe:\n{wardrobe_block}\n\n"
            f"Suggest 1-2 complete outfits that style '{item_label}' with specific "
            "pieces from their wardrobe, referring to each piece by name. Keep it "
            "clear and concise."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are FitFindr, a friendly personal stylist.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


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
    - Feel casual and authentic (like a real personal OOTD post, not an ad)
    - Naturally mention the item name; optionally reference the brand, platform,
      colors, or category if it fits
    - Never mention the price
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # 1. Guard against an empty or whitespace-only outfit string.
    if not outfit or not outfit.strip():
        return (
            "Outfit not found — there's no outfit suggestion to turn into a fit "
            "card. Run suggest_outfit() first, then pass its result here."
        )

    client = _get_groq_client()

    # 2. Build a prompt with the item details and the outfit suggestion.
    item_name = new_item.get("title") or new_item.get("description") or "this item"
    brand = new_item.get("brand") or "unknown brand"
    platform = new_item.get("platform") or "an online marketplace"

    item_lines = [
        f"- Name: {item_name}",
        f"- Brand: {brand}",
        f"- Platform: {platform}",
        f"- Category: {new_item.get('category', 'Unknown')}",
        f"- Colors: {', '.join(new_item.get('colors') or []) or 'n/a'}",
        f"- Style tags: {', '.join(new_item.get('style_tags') or []) or 'n/a'}",
    ]
    item_block = "\n".join(item_lines)

    prompt = (
        f"Here is a thrifted find someone just styled:\n{item_block}\n\n"
        f"Here is the outfit they put together with it:\n{outfit}\n\n"
        "Write a caption for this look that sounds like a real personal "
        "Instagram/TikTok OOTD post — something an actual person would write "
        "about their own outfit, NOT a thrift haul ad or product listing.\n"
        "Rules:\n"
        "- Keep it to 2-4 sentences.\n"
        f"- Naturally mention the item name ({item_name}).\n"
        "- Optionally reference the brand, platform, colors, or category only "
        "if it fits naturally — don't force any of them in.\n"
        "- Do NOT mention price or how much it cost.\n"
        "- Capture the vibe of the outfit in specific, concrete terms.\n"
        "- Use at most 0-1 emoji, and avoid hashtag spam.\n"
        "- Vary your sentence structure — don't reuse the same openers or "
        "rhythm, and make captions for different outfits feel distinctly "
        "different.\n"
        "Return only the caption text."
    )

    # 3. Call the LLM. Higher temperature than suggest_outfit (0.7) so captions
    #    feel fresh and different for each outfit.
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a stylist who writes fun, shareable "
                    "social media captions for thrifted outfits."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=1.1,
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    new_item = search_listings(
        "vintage graphic tee",
        max_price=50
    )[0]

    outfit = (
        "Style the Vintage Levi's 501 Jeans with a white oversized hoodie, "
        "Black Converse sneakers, and a silver chain necklace for a laid-back "
        "streetwear look."
    )

    print(create_fit_card(outfit, new_item))