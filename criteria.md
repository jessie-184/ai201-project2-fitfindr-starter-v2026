# Acceptance criteria — FitFindr

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**

The query is parsed with regex and the search is a plain keyword-overlap match, so a phrasing the patterns don't expect (like "30 bucks max" or "medium-sized") can lose a filter or a keyword and change what comes back. Two of the three tools also call the model, so one run in five can reasonably fail for reasons outside my code. I'm not allowing more than one miss, because everything after the search is a fixed sequence with no other branches.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling `suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**

Everything on this path is deterministic: regex parsing, filtering, keyword scoring, and a check for an empty list. No model is called before the branch, so the same query takes the same path every time. A single miss here would mean a bug in my loop, not randomness, so anything less than 5 of 5 would be excusing a bug.

---

## 3. Something about state

Across 5 different matching queries, the `id` of `session["selected_item"]` equals the `id` of the first search result, and the same `id` is the one received by both `suggest_outfit` and `create_fit_card`, checked by logging the item's `id` at the start of each tool call — 5 of 5 queries. The agent also never asks the user to name or choose the item. At least 3 of the 5 queries must have a top result that is not the first listing in the data file.

**Why this target:**

Passing the item along is just handing a dict from the session to the next function, with no model involved, so it should never fail. Any mismatch is a bug. The rule about the top result not being the first listing in the file matters because the starter test commands use `load_listings()[0]`. A leftover hardcoded item would pass casual testing and only show up when the search actually picks something else.

---

## 4. Something about the fit card

For 3 different items, generate 3 fit cards each (9 cards total), with caching off. A card passes if it:
- is 2–4 sentences (hashtags and emojis don't count as sentences)
- contains the item's actual price (written as `$24` or `$24.00`) and its platform name
- contains no other dollar amount

At least 8 of 9 cards pass. Separately, for each item, no two of its 3 cards
are word-for-word identical — 3 of 3 items.

**Why this target:**

The words come from the model, so I can't require exact wording, but I can require that the facts come from the listing. I allow one miss in nine because the model sometimes formats a price oddly or drops the platform even when the prompt asks for it. The rule against other dollar amounts catches a made-up price, which is worse than a missing one. The identical-output check is 3 of 3 rather than allowing a miss because identical captions mean caching is on or temperature is 0.0. That's a config mistake, not model randomness.

---

## 5. Your choice

Across 5 queries that include a size, a price ceiling, or both, every returned listing has a price at or below the ceiling and a size that matches by my token rule — 5 of 5 queries, with zero wrong listings in any result. The five
queries must include:
- size S, where no "US 9" shoes appear
- size L, where no XL items appear
- size M, where "S/M" items do appear
- a price exactly equal to a listing's price, where that listing is included
- a size given as a word ("medium")

**Why this target:**

Filtering is deterministic code with no model involved, so one wrong listing
means a bug, not bad luck. I'm counting individual listings rather than whole
queries because a result with nine right items and one pair of shoes still
looks broken to the user. The specific queries target the failures the starter
code warns about (substring matches like "s" in "us 9" and "l" in "xl") plus
the edges of my own spec: an inclusive price limit and the size-word mapping
in my parser.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
