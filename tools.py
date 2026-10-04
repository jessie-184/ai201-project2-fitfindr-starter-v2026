"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings
import re


# ── Tool 1: search_listings ───────────────────────────────────────────────────
_STOPWORDS = {"a", "an", "the", "and", "or", "for", "with", "in", "of", "to",
              "i", "want", "need", "looking", "some"}


def _tokens(text: str) -> set[str]:
    """Lowercase words, stopwords removed, simple plural 's' stripped (tees -> tee)."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w
            for w in words if w not in _STOPWORDS}


def _size_matches(requested: str, listing_size) -> bool:
    """Match a whole '/'-separated part ('S/M' -> 's', 'm'; 'US 9' -> 'us 9'),
    or a single word within a part ('9' matches 'US 9'). Never a substring,
    so 'S' does not match 'US 9' and 'L' does not match 'XL'."""
    if not listing_size:
        return False
    req = " ".join(requested.lower().split())
    for part in str(listing_size).lower().split("/"):
        part = " ".join(part.split())
        if req == part or req in part.split():
            return True
    return False


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    query = _tokens(description or "")
    if not query:
        return []

    scored = []
    for item in load_listings():
        if max_price is not None:
            price = item.get("price")
            if price is None or price > max_price:  # inclusive ceiling
                continue
        if size and not _size_matches(size, item.get("size")):
            continue

        # Structured fields: a match here is a real signal
        structured = " ".join([
            item.get("title") or "",
            item.get("category") or "",
            " ".join(item.get("style_tags") or []),
            " ".join(item.get("colors") or []),
            item.get("brand") or "",  # brand is often None
        ])
        core_overlap = query & _tokens(structured)
        if not core_overlap:
            continue  # matched only in free-text description, or not at all

        # Description: supporting evidence only, with negated words removed
        desc_text = re.sub(r"\b(?:no|not|without)\s+\w+", " ",
                           item.get("description") or "", flags=re.IGNORECASE)
        overlap = core_overlap | (query & _tokens(desc_text))

        # One point per matched keyword, plus a bonus point if it's in the title
        score = len(overlap) + len(query & _tokens(item.get("title") or ""))
        scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:config.SEARCH_RESULT_LIMIT]]

# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────
def _describe_listing(item: dict) -> str:
    """Readable summary of a listing for the prompt. Skips brand when it's None."""
    parts = [
        f"Item: {item.get('title', 'unknown item')}",
        f"Category: {item.get('category', 'unknown')}",
        f"Style tags: {', '.join(item.get('style_tags') or []) or 'none'}",
        f"Colors: {', '.join(item.get('colors') or []) or 'unknown'}",
        f"Size: {item.get('size', 'unknown')}",
        f"Condition: {item.get('condition', 'unknown')}",
        f"Description: {item.get('description', '')}",
    ]
    if item.get("brand"):
        parts.append(f"Brand: {item['brand']}")
    return "\n".join(parts)


def _describe_wardrobe_item(piece) -> str:
    """One line per wardrobe piece, without assuming its field names."""
    if isinstance(piece, dict):
        fields = []
        for key, value in piece.items():
            if key == "id" or value in (None, "", []):
                continue
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            fields.append(f"{key}: {value}")
        return "- " + "; ".join(fields)
    return f"- {piece}"

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_text = _describe_listing(new_item)
    pieces = (wardrobe or {}).get("items") or []

    if not pieces:
        prompt = (
            "A shopper is considering this thrifted item but hasn't shared their "
            "wardrobe.\n\n"
            f"{item_text}\n\n"
            "Give general styling advice: suggest one or two complete outfits built "
            "around this item, naming the kinds of pieces that would pair well "
            "(bottoms, shoes, layers, accessories) and the overall vibe of each. "
            "Keep it under 150 words, in plain text."
        )
    else:
        wardrobe_text = "\n".join(_describe_wardrobe_item(p) for p in pieces)
        prompt = (
            "A shopper is considering this thrifted item:\n\n"
            f"{item_text}\n\n"
            "Here is what they already own:\n"
            f"{wardrobe_text}\n\n"
            "Suggest one or two outfits that combine the new item with specific "
            "pieces from their wardrobe, naming each owned piece clearly. Only use "
            "pieces from the list above. If an outfit needs a visible piece they "
            "don't own, such as shoes, a layer, or an accessory, say so explicitly "
            "rather than inventing it. Don't mention basics like socks or "
            "underwear. Give each outfit a one-line vibe description. Keep it under "
            "150 words, in plain text."
        )

    response = generate(prompt)
    if not response or not response.strip():
        # Spec requires a non-empty string, even if the model returns nothing
        return (f"Couldn't generate outfit ideas for {new_item.get('title', 'this item')} "
                "right now. Try running it again.")
    return response.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────
def _format_price(price) -> str:
    """$24 for whole numbers, $24.50 otherwise, so the caption matches criterion 4."""
    if price is None:
        return "an unlisted price"
    price = float(price)
    return f"${price:.0f}" if price.is_integer() else f"${price:.2f}"

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "Can't write a fit card without an outfit — run suggest_outfit first."

    price_text = _format_price(new_item.get("price"))
    platform = new_item.get("platform") or "a thrift app"

    prompt = (
        "Write a caption someone would actually post on social media about a "
        "thrift find they just styled.\n\n"
        f"{_describe_listing(new_item)}\n"
        f"Price: {price_text}\n"
        f"Platform: {platform}\n\n"
        "How they styled it:\n"
        f"{outfit.strip()}\n\n"
        "Rules:\n"
        "- 2 to 4 sentences, casual and first-person, like a real post, not a "
        "product description.\n"
        f"- Mention the item, the price written exactly as {price_text}, and the "
        "platform, each exactly once.\n"
        "- Do not mention any other dollar amount.\n"
        "- Be specific about the vibe of the outfit; pick one look from the "
        "styling notes rather than listing everything.\n"
        "- You may end with up to 2 hashtags. No other text before or after the "
        "caption."
    )

    response = generate(prompt)
    if not response or not response.strip():
        return (f"Couldn't write a fit card for {new_item.get('title', 'this item')} "
                "right now. Try running it again.")
    return response.strip()