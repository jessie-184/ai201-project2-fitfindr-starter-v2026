# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

FitFindr is a thrifting agent: you describe what you're looking for in one
sentence, like "a vintage graphic tee under $30, size M," and it searches the
listings for the best match within your size and budget. It then suggests one
or two outfits built around that item using pieces from your wardrobe, or
general styling ideas if your wardrobe is empty. Finally, it writes a short,
post-ready caption for the find that mentions its price and platform. If
nothing matches your search, it stops and tells you what to loosen instead of
guessing.

---

## Tool Inventory

### `search_listings`

- **What it does:** Filters the listings data by an optional size and price ceiling, then ranks what's left by keyword overlap with the user's description and returns the best matches.
- **Inputs:** `description` (str), keywords describing the item; `size` (str or None), where None skips size filtering; `max_price` (float or None), an inclusive ceiling where None skips price filtering. Size matching is case-insensitive and token-based: the listing's size is split on `/` and whitespace, and it matches only if one token equals the requested size exactly. So `"M"` matches `"S/M"` and `"M"`, but `"S"` does not match `"US 9"`, and `"L"` does not match `"XL"`.
- **Returns:** A list of up to `config.SEARCH_RESULT_LIMIT` listing dicts, sorted by keyword score (highest first). Each dict has `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), and `platform`.
- **When it has nothing:** Returns an empty list `[]`. The agent loop checks for `[]` and tells the user nothing matched, suggesting they loosen the size or price.

### `suggest_outfit`

- **What it does:** Calls the model to suggest one or two outfits built around a thrifted item, using pieces from the user's wardrobe when there are any.
- **Inputs:** `new_item` (dict), a listing dict as returned by `search_listings`; `wardrobe` (dict), with an `items` key holding a list of wardrobe item dicts (the list may be empty).
- **Returns:** A non-empty string with one or two outfit suggestions. When the wardrobe has items, each outfit names specific pieces the user already owns alongside `new_item`.
- **When it has nothing:** If `wardrobe["items"]` is empty, it still returns a non-empty string: general styling advice for the item (what it pairs well with, what vibe it suits). It never returns `""` and never raises.

### `create_fit_card`

- **What it does:** Calls the model to write a short, post-style caption about the find and the outfit it's styled in.
- **Inputs:** `outfit` (str), the suggestion string from `suggest_outfit`; `new_item` (dict), the listing dict for the item.
- **Returns:** A 2–4 sentence caption string that reads like a social post. It mentions the item, its `price`, and its `platform` once each and is specific about the vibe. Output varies between runs because temperature is above 0 and caching is off.
- **When it has nothing:** If `outfit` is empty or whitespace-only, it returns the string `"Can't write a fit card without an outfit — run suggest_outfit first."` instead of raising or calling the model.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, write a message into
`session["message"]` that repeats the description, size, and max price that were
searched, then return the session immediately. `suggest_outfit` and
`create_fit_card` are not called. Otherwise, take the first result (the highest
keyword score, since `search_listings` sorts best match first), store it as
`session["selected_item"]`, call `suggest_outfit(selected_item, wardrobe)`, then
call `create_fit_card(outfit, selected_item)`, and return the session.

**Where it lives:** `agent.py::run_agent` (query parsing in `agent.py::parse_query`)

**How the query is parsed:** Regex, no model call, so the same query always
produces the same filters and the parsing can be tested directly.
- `max_price`: the number after "under", "below", "less than", "max", or
  "up to", with or without `$`, or a bare `$30`. If absent, `None` (no price filter).
- `size`: the token after the word "size", e.g. `M`, `S/M`, `XL`, `US 9`, `10`.
  "small", "medium", "large", and "extra large" are converted to `S`, `M`, `L`,
  and `XL`. If absent, `None` (no size filter).
- `description`: the query with the price and size phrases removed, leading
  filler ("I want", "looking for", "a", "the") stripped, and punctuation removed.
  If the description ends up empty, the search returns `[]` and the branch rule
  handles it.

**What moves through the session:** ** One dict, created at the start of
`run_agent` and returned at the end. Fields are added in this order:
1. `query` (str): the raw user input
2. `description` (str), `size` (str or None), `max_price` (float or None): from `parse_query`
3. `results` (list of listing dicts): from `search_listings`, possibly `[]`
4. *Branch.* If `results` is empty: `message` (str), then stop.
5. `selected_item` (listing dict): `results[0]`
6. `wardrobe` (dict with an `items` list): passed into `run_agent`, or
   `get_example_wardrobe()` if none is given
7. `outfit` (str): from `suggest_outfit(selected_item, wardrobe)`
8. `fit_card` (str): from `create_fit_card(outfit, selected_item)`

The user types the query once. `selected_item` goes into both later tools
straight from the session and is never asked for again.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

# Output:
[{'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, 
{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k','vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, 
{'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck.Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, 
{'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but addsto the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]

```


```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"

# Output:
Outfit 1: Effortless Streetwear
Pair the Vintage Levi's 501 Jeans with the White ribbed tank top and the Black cropped zip hoodie layered on top. Finish the look with the Chunky white sneakers and the Black crossbody bag.
Vibe: Casual, 90s-inspired street style that lets the vintage denim shine.

Outfit 2: Cozy Classic
Tuck the Oversized grey crewneck sweatshirt into the Vintage Levi's 501 Jeans, secured with the Brown leather belt. Add the Black combat boots for footwear. Note: This outfit requires socks, which are not currently in your wardrobe.
Vibe: Relaxed, everyday comfort with a rugged edge.

```


```
# Empty Wardrobe Case
$ python -c "from tools import suggest_outfit; from utils.data_loader import load_listings; print(suggest_outfit(load_listings()[0], {'items': []}))"

# Output:
Outfit 1: Casual Streetwear
Pair the 501s with an oversized graphic tee, a vintage leather bomber jacket, and classic white leather sneakers. Add a canvas cross-body bag and a silver chain necklace. The vibe is effortlessly cool and grounded in retro street style.

Outfit 2: Elevated Casual
Tuck a fitted ribbed black turtleneck into the jeans, layered under an oversized beige trench coat. Finish with black leather loafers and a structured shoulder bag. The vibe is polished yet relaxed, blending tailored warmth with timeless denim.

```

```
$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
