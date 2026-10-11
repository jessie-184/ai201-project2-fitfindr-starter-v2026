"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },

    # ── Criterion 3: five different matching queries. ──
    # Check that the first search result, the selected item, and the new_item
    # passed to suggest_outfit and create_fit_card are the same in every try.
    # None of these has lst_001 (the first listing in the file) as its top result.
    {
        # Top result: 90s Track Jacket (lst_004).
        "name": "state q1 track jacket",
        "query": "90s track jacket in size M",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Top result: 90s Silk Slip Dress (lst_013).
        "name": "state q2 slip dress",
        "query": "silk slip dress in midi length under $40",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Top result: Platform Sneakers (lst_019).
        "name": "state q3 platform sneakers",
        "query": "platform sneakers size 8",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Top result: Corduroy Wide-Leg Pants (lst_005).
        "name": "state q4 corduroy pants",
        "query": "corduroy pants",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Top result: Leather Belt (lst_014).
        "name": "state q5 leather belt",
        "query": "leather belt",
        "wardrobe": "example",
        "criterion": 3,
    },

    # ── Criterion 4: three different items, one per platform. ──
    # Judge tries 1-3 of each item (9 cards total, as the criterion specifies).
    {
        # Graphic Tee, $24 on depop.
        "name": "fit card item A graphic tee (depop)",
        "query": "graphic tee under $30",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        # Denim Jacket, $42 on poshmark.
        "name": "fit card item B denim jacket (poshmark)",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        # Oversized Flannel Shirt, $22 on thredUp (mixed-case platform name).
        "name": "fit card item C flannel (thredUp)",
        "query": "flannel shirt",
        "wardrobe": "example",
        "criterion": 4,
    },

    # ── Criterion 5: five size/price edge queries. ──
    # Check every returned listing with the separate terminal check, since the
    # report only shows the top 3 titles.
    {
        # "classic" tags the US 9 sneakers and US 8.5 boots; a substring bug
        # ("s" in "us 9") would pull them in.
        "name": "filter size S excludes US 9",
        "query": "classic size S",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # Three XL items are tagged vintage; a substring bug ("l" in "xl")
        # would include them.
        "name": "filter size L excludes XL",
        "query": "vintage size L",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # S/M tops exist and should appear.
        "name": "filter size M includes S/M",
        "query": "top size M",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # The Bootleg Graphic Tee costs exactly $24.00 and should be included.
        "name": "filter price boundary inclusive",
        "query": "graphic tee under $24",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # Size given as a word; the parser should map "medium" to "M".
        "name": "filter size word medium",
        "query": "jacket size medium",
        "wardrobe": "example",
        "criterion": 5,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
