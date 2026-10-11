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

- **What it does:** Filters the listings by an optional size and price ceiling, then ranks what's left by keyword overlap with the user's description. A listing must match at least one keyword in its title, category, style tags, colors, or brand to be included; matches in the description only affect ranking, and words right after "no," "not," or "without" are ignored.
- **Inputs:** `description` (str), keywords describing the item; `size` (str or None), where None skips size filtering; `max_price` (float or None), an inclusive ceiling where None skips price filtering. A size matches if it equals a whole `/`-separated part of the listing's size, or a single word within one, case-insensitive, never as a substring. So `"M"` matches `"S/M"`, `"W30"` matches `"W30 L30"`, but `"S"` does not match `"US 9"` and `"L"` does not match `"XL"`.
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

**Branch rule:** If `search_listings` returns an empty list, write a message into `session["error"]` that names what was searched and what the user could change (use fewer or more general keywords, try a different size or leave it out, or raise the max price), then end the loop without calling `suggest_outfit` or `create_fit_card`. Otherwise, set `session["selected_item"]` to the first result (the best keyword match, since `search_listings` sorts
highest score first) and continue to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent` (query parsing in `agent.py::parse_query`, the no-results message in `agent.py::_no_results_message`)

**How the loop runs:** `run_agent` is a `while` loop over named steps (`parse` → `search` → `select` → `outfit` → `fit_card` → `done`). Each pass runs one step and chooses the next step from what that step put in the session. The only branch is after `search`: an empty result goes straight to `done`. Every pass increments a counter and calls `trace.check_iterations(count)`, which stops the run if it ever exceeds `MAX_ITERATIONS` in `config.py`.

**How the query is parsed:** Regex, with no model call, so the same query always produces the same filters and parsing can be tested on its own.
- `max_price`: the number after "under", "below", "less than", "max", or "up to", with or without `$`, or a bare `$30`. If none is found, `None` (no price filter).
- `size`: the token after the word "size", e.g. `M`, `S/M`, `XL`, `US 9`, `10`. "small", "medium", "large", and "extra large" become `S`, `M`, `L`, and `XL`. If none is found, `None` (no size filter).
- `description`: the query with the price and size phrases removed, leading filler ("I want", "looking for", "a", "the") stripped, and punctuation removed. If nothing is left, search returns `[]` and the error message asks the user to describe the item.

**What moves through the session:** One dict, created by `new_session()` at the start of `run_agent` and returned at the end. Each tool reads its inputs from the session and writes its result back, so no value is passed directly from one call to the next. Fields fill in this order:
1. `query` (str) and `wardrobe` (dict): set when the session is created
2. `parsed` (dict): `description` (str), `size` (str or None), `max_price` (float or None)
3. `search_results` (list of listing dicts): from `search_listings`, possibly `[]`
4. *Branch.* If `search_results` is empty: `error` (str), then stop. The later fields stay `None`.
5. `selected_item` (listing dict): `search_results[0]`
6. `outfit_suggestion` (str): from `suggest_outfit(session["selected_item"], session["wardrobe"])`
7. `fit_card` (str): from `create_fit_card(session["outfit_suggestion"], session["selected_item"])`

The user types the query once. The selected item goes from the session into both later tools and is never asked for again. Callers check `session["error"]` first: if it isn't `None`, the run ended early.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
# Happy Path
$ python app.py ask 'vintage graphic tee under $30'

# Output: 
  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:
Outfit 1: Effortless 90s streetwear
Pair the graphic tee with your baggy straight-leg jeans and chunky white sneakers. Layer your vintage black denim jacket on top and finish with the black crossbody bag. 
Vibe: Casual, skate-inspired street style with authentic retro attitude.

Outfit 2: Edgy grunge contrast
Tuck the tee into your wide-leg khaki trousers, wearing the brown leather belt at the waist. Add your black combat boots for footwear. Note: This outfit is complete using only your existing wardrobe pieces, but a silver chain necklace would add extra detail if you had one.
Vibe: Cool, utilitarian grunge mixing faded graphics with structured earth tones.

  Fit card: Found this absolute gem on depop for only $24 and immediately had to throw on my baggy jeans and chunky sneakers for the ultimate 90s skate vibe. The worn-in cotton feels so authentic and makes the effortless streetwear look come together with zero effort. #thriftfind #streetwear

```

```
# No Match
$ python app.py ask 'designer ballgown size XXS under $5'

# Output:
No listings matched 'designer ballgown' (size XXS, under $5). Try fewer or more general keywords, a different size (or no size), or a higher max price.

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
Pair the Vintage Levi's 501 Jeans with the White ribbed tank top and Black cropped zip hoodie for a balanced silhouette. Add the Chunky white sneakers and Black crossbody bag to complete the look.
Vibe: Casual, 90s-inspired street style that keeps it comfortable and cool.

Outfit 2: Cozy Casual
Combine the Vintage Levi's 501 Jeans with the Oversized grey crewneck sweatshirt and Brown leather belt. Finish the outfit with the Black combat boots. 
Vibe: Laid-back and textured, perfect for cooler days.

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
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"

# Output:
Score of a lifetime scoring these vintage Levi's 501s on depop for just $38. Threw them on with some fresh white sneakers for the ultimate off-duty streetwear vibe. I am never taking these off. #vintage #denim

```

---

## How I Used AI

**Moment 1**

- *What I asked for:* I ran `search_listings('graphic tee', max_price=30)` and asked Claude to double-check whether the output was correct.
- *What came back:* Claude confirmed the filtering and ranking worked (all prices ≤ $30, the best tee match first), but pointed out three false positives at the bottom of the results: cargo pants whose description mentions "a long tee," a mesh top described as good for layering "under a graphic tee," and a crewneck whose description says "No graphics." My keyword match counted a word anywhere in the description, and it couldn't tell that "no" negates "graphics."
- *What I changed:* I changed `search_listings` so a listing must match at least one query word in its title, category, style tags, colors, or brand to be included. Description matches now only add to the score, and words right after "no," "not," or "without" are ignored. The same query went from 7 results to 4, all of them actual tees or graphic tops. I also updated the `search_listings` line in my Tool Inventory to describe the new rule.

**Moment 2**

- *What I asked for:* After building `suggest_outfit` and `create_fit_card`, I asked Claude for more commands to test them beyond the single example in each docstring.
- *What came back:* For `suggest_outfit`, Claude suggested running it with an empty wardrobe (`{'items': []}`) to check the general-advice path, and printing `get_example_wardrobe()` to confirm every piece the model named was one I actually own. For `create_fit_card`, it gave a shell loop to run the same input three times. All three captions came back word-for-word identical. Claude checked my `config.py`, saw `TEMPERATURE` was already 0.9, and identified the cache as the cause: `CACHE_ENABLED` is on by default, so runs two and three were getting the first answer back from `.cache`.
- *What I changed:* I reran the three-caption test with `AI201_CACHE=0` in front of the command instead of editing `config.py`, so caching stays on while I build and saves quota. The three captions came out different and all passed my criterion 4 checks. The empty-wardrobe test returned general advice as intended, and every wardrobe piece the model named was in my wardrobe. The one issue I found was that the model flagged socks as a missing item, so I narrowed that instruction in the prompt to visible pieces like shoes, layers, and accessories.

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
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item every later tool received (Try k = query k) | 5 of 5 queries | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is grounded in the listing and varies (each try = 3 cards, one per item) | ≥8 of 9 cards, 3 of 3 items distinct | PASS (3/3) | PASS (3/3) | PASS (3/3) | PASS (3/3), not counted | PASS (3/3), not counted | MET (9/9 cards, 3/3 items distinct) |
| 5. Search results respect the size and price asked for (Try k = query k) | 5 of 5 queries, 0 wrong listings | PASS | PASS | PASS | PASS | PASS | MET (5/5, 0 of 17 listings wrong) |

All runs come from `python run_eval.py --label before` (caching off, temperature
0.9). The full log is in `results/run_2026-10-11_0234_before.md`.

How the Try columns map to each criterion:
- **Criteria 1 and 2:** one scenario each, and the Try columns are its five runs.
- **Criterion 3:** the criterion specifies 5 different queries, so Try k is
  query k (track jacket, slip dress, platform sneakers, corduroy pants, leather
  belt). A query passes only if all five of its runs pass. The trace shows
  titles rather than ids, and every title in the data is unique, so I checked
  that the first search result (step 2), the selected item (step 3), and the
  `new_item` passed to `suggest_outfit` and `create_fit_card` (steps 4–5)
  matched (see the unit 4 revision in `criteria.md`).
- **Criterion 4:** the criterion specifies 3 cards per item (9 total), so the
  verdict uses tries 1–3. `run_eval.py` runs every scenario five times, and
  tries 4–5 also passed every check (6/6 cards), but they aren't counted toward
  the verdict because the criterion was written for 9 cards. Each card was
  checked for 2–4 sentences (not counting hashtags), the listing's price
  (`$24`, `$42`, `$22`), its platform name (case-insensitive), and no other
  dollar amount.
- **Criterion 5:** the criterion specifies 5 edge queries, so Try k is query k.
  It also requires checking every returned listing, but the run log only shows
  the top 3 titles and no sizes, so I verified each listing's size and price
  with a separate check that calls `agent.py::parse_query` and
  `search_listings` via `mcp_client.call_tool`. Search is deterministic, so all
  five runs of each query returned the same results.

**Real output from one try**, pasted as text, naming the file and function
that produced it:

**Criterion 1:** "matching query completes," Try 1, produced by
`run_eval.py::main` running `agent.py::run_agent`:

```
- stopped early: no
- selected_item: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
- search_results: 10

Fit card:
scored this 2003 tour tee on depop for $24 and I'm obsessed with how soft it is. paired it with wide-leg khaki trousers and combat boots for that edgy grunge contrast vibe. #thriftfind #streetwear

Trace:
[1] parse_query
      in:  vintage graphic tee under $30
      out: description='vintage graphic tee', size=None, max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey, Y2K Baby Tee — Butterfly Print … +7 more
      →    branch: 10 results, continuing
[3] select_item
      in:  10 results
      out: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
      →    first result = best keyword match
[4] suggest_outfit
      in:  new_item=Graphic Tee — 2003 Tour Bootleg Style, wardrobe=10 items
      out: Outfit 1: Effortless 90s Streetwear Pair the graphic tee with your Baggy straight-leg jeans and Chunky white s…
[5] create_fit_card
      in:  outfit=(514 chars), new_item=Graphic Tee — 2003 Tour Bootleg Style
      out: scored this 2003 tour tee on depop for $24 and I'm obsessed with how soft it is. paired it with wide-leg khaki…
```

**Criterion 2:** "impossible query stops early," Try 1, produced by
`run_eval.py::main` running `agent.py::run_agent`:

```
- stopped early: yes — No listings matched 'designer ballgown' (size XXS, under $5). Try fewer or more general keywords, a different size (or no size), or a higher max price.
- selected_item: (none)
- search_results: 0

Trace:
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit
```

**Criterion 3:** "state q4 corduroy pants," Try 1, produced by
`run_eval.py::main` running `agent.py::run_agent`. The same item appears at
steps 2, 3, 4, and 5:

```
[1] parse_query
      in:  corduroy pants
      out: description='corduroy pants', size=None, max_price=None
[2] search_listings (via MCP)
      in:  description='corduroy pants', size=None, max_price=None
      out: 2 items: Corduroy Wide-Leg Pants — Rust, Low-Rise Cargo Pants — Khaki
      →    branch: 2 results, continuing
[3] select_item
      in:  2 results
      out: Corduroy Wide-Leg Pants — Rust ($32.0, depop)
      →    first result = best keyword match
[4] suggest_outfit
      in:  new_item=Corduroy Wide-Leg Pants — Rust, wardrobe=10 items
      out: Outfit 1: 70s Earthy Casual Pair the corduroy wide-leg pants with the white ribbed tank top tucked in for a hi…
[5] create_fit_card
      in:  outfit=(709 chars), new_item=Corduroy Wide-Leg Pants — Rust
      out: Just scored these gorgeous rust cords for $32 on depop and I am never taking them off. Styled them with an ove…
```

**Criterion 4:** the Try 1 fit card for each item, produced by
`tools.py::create_fit_card`, called from `agent.py::run_agent` under
`run_eval.py::main`:

```
Item A, graphic tee ($24, depop):
Finally scored this absolute grail of a 2003 tour bootleg tee on depop for just $24 and I'm obsessed. I threw it on with some baggy straight-leg jeans and chunky white sneakers for the ultimate casual, cool, and undeniably retro vibe. #thriftfind #streetwear

Item B, denim jacket ($42, Poshmark):
Scored this vintage Wrangler jacket on Poshmark for only $42 and I'm obsessed with the cropped fit. I styled it for a high-contrast double denim look with baggy dark-wash jeans and chunky sneakers for the ultimate streetwear vibe. #ThriftFind #DenimOnDenim

Item C, flannel ($22, thredUp):
Scored this vintage Woolrich flannel on thredUp for just $22 and I am obsessed with the skater-inspired grunge look. Threw it on open over a ribbed tank and baggy jeans for the ultimate effortless 90s fit. #thriftfind #grungefashion
```

**Criterion 5:** every returned listing for the five queries, produced by
`agent.py::parse_query` and `search_listings` via `mcp_client.call_tool`:

```
classic size S -> size = 'S' | max_price = None | 1 results
    lst_007 | size = 'S' | $ 42.0 | Denim Jacket — Light Wash, Cropped

vintage size L -> size = 'L' | max_price = None | 5 results
    lst_010 | size = 'L' | $ 40.0 | Vintage Windbreaker — Color Block Purple/Teal
    lst_015 | size = 'L' | $ 26.0 | Vintage Graphic Hoodie — Faded Black
    lst_018 | size = 'M/L' | $ 38.0 | Vintage Linen Blazer — Cream
    lst_033 | size = 'L' | $ 19.0 | Vintage Band Tee — Faded Grey
    lst_006 | size = 'L' | $ 24.0 | Graphic Tee — 2003 Tour Bootleg Style

top size M -> size = 'M' | max_price = None | 7 results
    lst_017 | size = 'S/M' | $ 15.0 | Mesh Long-Sleeve Top — Black
    lst_023 | size = 'S/M' | $ 22.0 | Crochet Halter Top — Cream
    lst_002 | size = 'S/M' | $ 18.0 | Y2K Baby Tee — Butterfly Print
    lst_020 | size = 'M' | $ 16.0 | Henley Long Sleeve — Washed Burgundy
    lst_024 | size = 'M' | $ 18.0 | Vintage Polo Shirt — Forest Green
    lst_029 | size = 'M' | $ 28.0 | Silk Button-Down — Sage Green
    lst_030 | size = 'M' | $ 25.0 | Vintage Knit Vest — Argyle Brown/Cream

graphic tee under $24 -> size = None | max_price = 24.0 | 3 results
    lst_006 | size = 'L' | $ 24.0 | Graphic Tee — 2003 Tour Bootleg Style
    lst_002 | size = 'S/M' | $ 18.0 | Y2K Baby Tee — Butterfly Print
    lst_033 | size = 'L' | $ 19.0 | Vintage Band Tee — Faded Grey

jacket size medium -> size = 'M' | max_price = None | 1 results
    lst_004 | size = 'M' | $ 45.0 | 90s Track Jacket — Navy/White Stripe
```

---

## Verdicts and Diagnoses

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | All five tries report "stopped early: no," show all five trace steps, and end with a fit card. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | All five tries stopped at step 2 with `[] (empty)`, had no outfit or fit card, and printed a message naming the keywords, size, and price to change. |
| 3 | The item search found is the item every later tool received | 5 of 5 queries | MET (5/5) | Checked by title, per the unit 4 revision in `criteria.md`: for all five queries, in every run, the first search result (step 2), the selected item (step 3), and the `new_item` passed to `suggest_outfit` and `create_fit_card` (steps 4–5) were the same listing. None of the five was `lst_001`, the first listing in the file. |
| 4 | The fit card is grounded in the listing and varies | ≥8 of 9 cards, 3 of 3 items distinct | MET (9/9, 3/3) | All nine cards from tries 1–3 had 2–3 sentences, the exact price, the platform name, and no other dollar amount. No item had two identical cards. |
| 5 | Search results respect the size and price asked for | 5 of 5 queries, 0 wrong listings | MET (5/5, 0 of 17) | I checked all 17 returned listings. None had a non-matching size or a price over the ceiling: no US shoes for S, no XL for L, S/M included for M, the $24.00 tee included at the $24 boundary, and "medium" parsed as `M`. |

**Diagnoses**

No criterion missed, so there is no miss to diagnose. The run did surface a real
failure that none of my five criteria measured.

**Outfits claim the user doesn't own pieces they do own.** In 10 of 70 outfit
suggestions (14%), `suggest_outfit` said or implied the outfit needed something
already in the wardrobe. For example, track jacket q1 Try 1 said the outfit
"needs a pair of shoes… which are not currently in your wardrobe," when the
wardrobe has chunky white sneakers and black combat boots. Jacket size medium
Try 4 said it "would benefit from a simple belt, which you don't currently
own," when the wardrobe has a brown leather belt. Belts (5 runs) and shoes
(2 runs) account for most of them. Another 6 runs said an outfit "needs" a bag
or jacket the user owns, without directly claiming they don't own one.

- **Place:** the model's output, in `tools.py::suggest_outfit`.
- **Mechanism:** the wardrobe prompt tells the model, "If an outfit needs a
  visible piece they don't own… say so explicitly." That rule invites a
  missing-item note on almost every outfit, and the model often adds one even
  though the owned piece is listed in the same prompt. The tool and the session
  passed the right wardrobe (`wardrobe=10 items` at step 4 in every trace), so
  the data was there; the prompt asks for a judgment the model frequently gets
  wrong. Belts and shoes are near the end of the wardrobe list, which may be
  why they're missed most.

Smaller issues from the same run:
- **Socks rule broken once.** Platform sneakers Try 5 said the outfit needs "a
  pair of socks since they are not in your inventory," despite the prompt rule
  not to mention socks.
- **Markdown in plain-text output.** Slip dress tries 3 and 5 used `**bold**`,
  even though the prompt asks for plain text.
- **Fit card framing.** Track jacket q1 Try 1 said "I just listed it over on my
  poshmark," as if the user were selling the item.
- **Parser leftover.** "90s track jacket in size M" parsed to the description
  `'90s track jacket in'`. It's harmless, because `_tokens` drops "in" as a
  stopword, but `parse_query` doesn't strip "in" before "size."

**Pattern:** all five criteria test the loop's plumbing (the branch, the
session, search filters) or the structure of the fit card. None of them checks
whether the outfit advice is accurate about the user's wardrobe, which is where
the real failure was.

**Were my targets too low?** Partly. Criteria 2, 3, and 5 test deterministic
code (the branch, the session handoff, and the search filters), so 5 of 5 was
the right target, and the only way to miss was a real bug. They did their job:
they would have caught a substring size match, a hardcoded item, or a loop that
didn't stop. Criterion 1's 4-of-5 allowance turned out to be generous, since all
five tries passed. But my criteria were low in a different way: they set no
bar at all for the quality of the model's output. Criterion 4 checks the fit
card's structure (sentence count, price, platform) but not whether what it says
is true, and no criterion checks `suggest_outfit` at all. That's why the agent
"met" everything while telling users in 10 of 70 runs that they lacked a piece
they own.

**The criterion I'd tighten: criterion 1.** It counts a run as complete as long
as all three tools return something, so an outfit that wrongly says "you don't
own a belt" still passes. A tightened version:

> Across all completed runs in the eval, at least 67 of 70 outfit suggestions
> (about 95%) name only pieces from the user's wardrobe plus the new item, and
> none claims an owned piece is missing.

Against this run, that would be **MISSED (60 of 70)**. This is the failure I'm
targeting in the improvement step.

---

## Loop Trace

Each run below is printed by the `trace.step()` calls in `agent.py::run_agent`,
one per loop step. The search step is labeled `(via MCP)` because
`search_listings` is called through `mcp_client.call_tool`.

**Happy path**

```
$ python app.py ask 'denim jacket under $50' --trace
[1] parse_query
      in:  denim jacket under $50
      out: description='denim jacket', size=None, max_price=50.0
[2] search_listings (via MCP)
      in:  description='denim jacket', size=None, max_price=50.0
      out: 6 items: Denim Jacket — Light Wash, Cropped, 90s Track Jacket — Navy/White Stripe, High-Waisted Denim Shorts — Cutoff … +3 more
      →    branch: 6 results, continuing
[3] select_item
      in:  6 results
      out: Denim Jacket — Light Wash, Cropped ($42.0, poshmark)
      →    first result = best keyword match
[4] suggest_outfit
      in:  new_item=Denim Jacket — Light Wash, Cropped, wardrobe=10 items
      out: Outfit 1: Double Denim Streetwear Vibe: Casual streetwear with a cool contrast. Pair the new light wash denim …
[5] create_fit_card
      in:  outfit=(579 chars), new_item=Denim Jacket — Light Wash, Cropped
      out: Scored this amazing vintage Wrangler jacket for just $42 on Poshmark, and I'm obsessed with the structuredsho…

2 model calls this session, 849 prompt + 203 output tokens
```

**Empty search**

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit

  No listings matched 'designer ballgown' (size XXS, under $5). Try fewer or more general keywords, a different size (or no size), or a higher max price.

0 model calls this session
```

The empty-search trace stops at step 2, while the happy path runs all five
steps. The branch after `search_listings` sees `[]`, writes the message into
`session["error"]`, and ends the loop, so neither model-calling tool runs.


**On the MCP move:** I moved `search_listings` behind an MCP server. In
`mcp_server.py`, I registered it with FastMCP's `@mcp.tool()` decorator,
importing the real implementation from `tools.py` under an alias so the
registered function doesn't call itself. Its description states each input's
type and units (`max_price` is an inclusive ceiling in US dollars), how size
matching works, the fields in each returned listing, and that it returns an
empty list when nothing matches. The type hints match my Tool Inventory, so
FastMCP published `description` as a required string and `size` and
`max_price` as optional. In `agent.py::run_agent`, I replaced the direct
`search_listings(...)` call in the `search` step with
`call_tool("search_listings", {...})` from `mcp_client.py`, and removed the
direct import.

Nothing behaved differently afterward. `'vintage graphic tee under $30'`
returned the same top result as in unit 3 (Graphic Tee — 2003 Tour Bootleg
Style, $24 on depop), and `'designer ballgown size XXS under $5'` still stopped
with the same error message and 0 model calls. That second run shows an empty
result still comes back through MCP as an empty list, not `None` or a string,
so the branch still fires. The only visible change is that each search is a
little slower, because `call_tool` starts and stops the server on every call.


### Failure modes

I triggered each failure on purpose and recorded what the agent said.

**1. Empty search.** Query: `'designer ballgown size XXS under $5'` (the run
shown above under Empty search). The branch was already in place from unit 3,
so no new handler was needed. The agent stopped before `suggest_outfit` and
printed: *"No listings matched 'designer ballgown' (size XXS, under $5). Try
fewer or more general keywords, a different size (or no size), or a higher max
price."*

**2. Empty wardrobe.** `suggest_outfit` already returns general styling advice
when `wardrobe["items"]` is empty, so no new handler was needed. The agent
completed all five steps:

```
$ python app.py ask 'vintage graphic tee under $30' --empty-wardrobe --trace
(running with an empty wardrobe)
[1] parse_query
      in:  vintage graphic tee under $30
      out: description='vintage graphic tee', size=None, max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey, Y2K Baby Tee — Butterfly Print … +7 more
      →    branch: 10 results, continuing
[3] select_item
      in:  10 results
      out: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
      →    first result = best keyword match
[4] suggest_outfit
      in:  new_item=Graphic Tee — 2003 Tour Bootleg Style, wardrobe=0 items
      out: Outfit 1: 90s Grunge Casual. Pair the tee with relaxed-fit, light-wash distressed denim and chunky black comba…
[5] create_fit_card
      in:  outfit=(590 chars), new_item=Graphic Tee — 2003 Tour Bootleg Style
      out: Found this sick 2003 tour tee on depop for only $24 and immediately had to lean into the 90s grunge aesthetic …

2 model calls this session, 496 prompt + 192 output tokens
```

The outfit suggested general pieces ("relaxed-fit, light-wash distressed
denim," "an oversized flannel shirt") without claiming the user owns them. One
quirk: the fit card then called them "my trusty combat boots," writing a
suggested piece as if the user already owned it.

**3. Model unavailable.** I changed one character of `GEMINI_API_KEY` in
`.env` and ran a query I hadn't asked before, so the answer couldn't come from
the cache. Before this milestone, `app.py`'s catch-all would have printed the
raw exception (`ModelUnavailable: ...`) without telling the user what to do. I
added a handler in `agent.py::run_agent` that catches `ModelUnavailable` around
both `suggest_outfit` and `create_fit_card`, writes a message into
`session["error"]`, and stops the loop:

```
$ python app.py ask 'platform sneakers size 8' --trace
[1] parse_query
      in:  platform sneakers size 8
      out: description='platform sneakers', size='8', max_price=None
[2] search_listings (via MCP)
      in:  description='platform sneakers', size='8', max_price=None
      out: 1 items: Platform Sneakers — White Chunky Sole
      →    branch: 1 results, continuing
[3] select_item
      in:  1 results
      out: Platform Sneakers — White Chunky Sole ($48.0, poshmark)
      →    first result = best keyword match
[4] suggest_outfit
      in:  new_item=Platform Sneakers — White Chunky Sole, wardrobe=10 items
      out: ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh k…
      →    model unreachable, stopping

  Found Platform Sneakers — White Chunky Sole, but couldn't reach the model to suggest outfits. Check that the API key in .env is correct and that you're online, then try again.

1 model calls this session
```

Search still worked because it doesn't call the model. The run stopped at
`suggest_outfit` with a message naming what broke and what to do, with no stack
trace, and it didn't go on to call `create_fit_card`. I restored a valid key
afterward.


---

## The Improvement

**What I changed:** One prompt instruction in `tools.py::suggest_outfit`, in
the wardrobe branch. I replaced:

> "If an outfit needs a visible piece they don't own, such as shoes, a layer,
> or an accessory, say so explicitly rather than inventing it. Don't mention
> basics like socks or underwear."

with:

> "…and build each outfit entirely from those pieces plus the new item. Do not
> add notes about pieces the user doesn't own or that an outfit is missing."

Nothing else changed: same scenarios, same temperature, caching off, five
tries each.

**Which failure it was meant to fix:** the one my diagnosis found. In 10 of 70
before-run outfit suggestions, the model told the user an outfit needed
something they already own, most often a belt or shoes. The mechanism was the
"say so if they don't own it" instruction, which invited a missing-item note
the model often got wrong. Removing the instruction removes the opportunity
for that error.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item every later tool received (Try k = query k) | 5 of 5 queries | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is grounded in the listing and varies (each try = 3 cards, one per item) | ≥8 of 9 cards, 3 of 3 items distinct | PASS (3/3) | PASS (3/3) | PASS (3/3) | PASS (3/3), not counted | PASS (3/3), not counted | MET (9/9 cards, 3/3 items distinct) |
| 5. Search results respect the size and price asked for (Try k = query k) | 5 of 5 queries, 0 wrong listings | PASS | PASS | PASS | PASS | PASS | MET (5/5, 0 of 17 listings wrong) |

Same mapping as the before-run. Full log: `results/run_2026-10-11_0324_after.md`.

**Before vs. after:**

| Measure | Before | After |
|---|---|---|
| Criteria met | 5 of 5 | 5 of 5 |
| Outfits wrongly claiming an owned piece is missing | 10 of 70 | 0 of 70 |
| Borderline "needs a bag/jacket" notes (owned) | 6 of 70 | 0 of 70 |
| Socks mentioned | 1 of 70 | 0 of 70 |
| Proposed tightened criterion 1 (≥67 of 70 outfits accurate) | MISSED (60/70) | MET (70/70) |

**Did it help, and how do I know:** Yes. Running the same search on the
after-run log found no missing-item notes in any of the 70 outfit suggestions,
down from 10 wrong claims and 6 borderline ones. All five criteria stayed met,
so the change didn't break anything they measure. I also checked for the
opposite risk, the model inventing pieces the user doesn't own now that it
can't flag missing ones, and found none.

The change had costs:
- The agent no longer points out genuinely useful missing pieces. In the
  before-run, it correctly suggested adding a bralette under the sheer mesh
  top, and that advice is gone.
- Some outfits became terser, sometimes just "jeans + boots + bag" with no full
  sentence.
- The `**bold**` formatting from the before-run also disappeared. I didn't
  target that, so I'm reporting it as an observation, not something the change
  was designed to fix.


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
