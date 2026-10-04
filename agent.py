"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import config
import trace
import re
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }

# ── query parsing (regex) ─────────────────────────────────────────────────────

PRICE_RE = re.compile(
    r"(?:under|below|less than|max(?:imum)?|up to)\s*\$?\s*(\d+(?:\.\d+)?)|\$(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
SIZE_RE = re.compile(
    r"\bsize\s+(extra large|small|medium|large|us\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?|[a-z]{1,3}(?:/[a-z]{1,3})?)\b",
    re.IGNORECASE,
)
SIZE_WORDS = {"small": "S", "medium": "M", "large": "L", "extra large": "XL"}
FILLER_RE = re.compile(
    r"^\s*(?:(?:i\s+(?:want|need)|looking\s+for|find\s+me)\s+)?(?:(?:an?|the)\s+)?",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """Pull description, size, and max_price out of a plain-language query."""
    price_m = PRICE_RE.search(query)
    max_price = float(price_m.group(1) or price_m.group(2)) if price_m else None

    size_m = SIZE_RE.search(query)
    size = None
    if size_m:
        raw = size_m.group(1).strip()
        size = SIZE_WORDS.get(raw.lower()) or re.sub(r"(?i)^us\s*", "US ", raw).upper()

    desc = query
    for m in (price_m, size_m):
        if m:
            desc = desc.replace(m.group(0), " ")
    desc = FILLER_RE.sub("", desc)
    desc = re.sub(r"[^\w\s/-]", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip()

    return {"description": desc, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """Say what was searched and what the user could change."""
    desc, size, max_price = parsed["description"], parsed["size"], parsed["max_price"]
    if not desc:
        return ("I couldn't find any item keywords in your request. Try describing "
                "the item itself, e.g. 'vintage graphic tee under $30'.")

    searched = f"'{desc}'"
    filters = []
    if size:
        filters.append(f"size {size}")
    if max_price is not None:
        filters.append(f"under ${max_price:g}")
    if filters:
        searched += f" ({', '.join(filters)})"

    tips = ["fewer or more general keywords"]
    if size:
        tips.append("a different size (or no size)")
    if max_price is not None:
        tips.append("a higher max price")

    if len(tips) == 1:
        tip_text = tips[0]
    elif len(tips) == 2:
        tip_text = f"{tips[0]} or {tips[1]}"
    else:
        tip_text = f"{', '.join(tips[:-1])}, or {tips[-1]}"

    return f"No listings matched {searched}. Try {tip_text}."

# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    step = "parse"
    count = 0

    while step != "done":
        count += 1
        trace.check_iterations(count)

        if step == "parse":
            session["parsed"] = parse_query(session["query"])
            step = "search"

        elif step == "search":
            p = session["parsed"]
            session["search_results"] = search_listings(
                p["description"], size=p["size"], max_price=p["max_price"]
            )
            # THE BRANCH: decide the next step from what search returned
            if not session["search_results"]:
                session["error"] = _no_results_message(session["parsed"])
                step = "done"
            else:
                step = "select"

        elif step == "select":
            session["selected_item"] = session["search_results"][0]
            step = "outfit"

        elif step == "outfit":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe"]
            )
            step = "fit_card"

        elif step == "fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )
            step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
