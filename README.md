# FitFindr — AI Secondhand Fashion Styling Agent

## Project Overview

FitFindr is an AI styling agent for secondhand fashion. The goal of the project is to help a user search for clothing listings, pick a good item, style it with pieces from their wardrobe, and create a short fit card caption that could be used for social media.

For my stretch feature, I added a price comparison tool. This checks whether the selected item looks like a good deal, a fair price, or overpriced compared to similar listings in the dataset.

The agent follows a fixed planning loop instead of randomly deciding what to do. It parses the user query, searches the listings, selects the best item, checks the price, suggests an outfit, and then creates a fit card.

---

## Tools

### Tool 1: `search_listings(description, size, max_price) -> list[dict]`

This tool searches through `listings.json` and returns clothing listings that match the user's request.

**Inputs:**

* `description` (`str`): The item or style the user is looking for, such as `"vintage graphic tee"` or `"track jacket"`.
* `size` (`str`): The size the user wants, such as `"S"`, `"M"`, `"L"`, or `None`.
* `max_price` (`float`): The highest price the user wants to pay.

**Output:**

The tool returns a list of matching listing dictionaries. Each listing can include fields like:

* `id`
* `title`
* `description`
* `category`
* `style_tags`
* `size`
* `condition`
* `price`
* `colors`
* `brand`
* `platform`

**How I used it:**

This is the first real tool the agent calls after parsing the user query. It filters by price and size, then scores listings based on how well the listing matches the user's description. The best matches are returned first.

If there are no matches, it returns an empty list instead of crashing.

---

### Tool 2: `suggest_outfit(new_item, wardrobe) -> str`

This tool takes the selected item and the user's wardrobe, then suggests an outfit.

**Inputs:**

* `new_item` (`dict`): The item selected from the search results.
* `wardrobe` (`dict`): The user's wardrobe data from `wardrobe_schema.json`.

**Output:**

The tool returns a string with an outfit suggestion and a short explanation of why the pieces work together.

**How I used it:**

This tool calls Groq with `llama-3.3-70b-versatile`. It sends the selected item and wardrobe information to the model so it can create a styling suggestion.

If the wardrobe is empty, the tool still returns general styling advice instead of failing.

---

### Tool 3: `create_fit_card(outfit, new_item) -> str`

This tool creates a short caption-style fit card for the outfit.

**Inputs:**

* `outfit` (`str`): The outfit suggestion from `suggest_outfit`.
* `new_item` (`dict`): The selected listing.

**Output:**

The tool returns a short caption that sounds like something someone could post on Instagram or TikTok.

**How I used it:**

This tool also calls Groq. It uses the outfit suggestion and selected item to create a short, casual caption.

If the outfit input is empty, the tool returns a fallback message instead of raising an error.

---

### Tool 4: `compare_price(new_item) -> str`

This is my extra credit stretch tool.

It compares the selected item's price to similar listings in `listings.json` and returns whether the item is a good deal, fair price, or overpriced.

**Inputs:**

* `new_item` (`dict`): The selected listing from `search_listings`.

**Output:**

The tool returns a string with one of these verdicts:

* `Good deal`
* `Fair price`
* `Overpriced`

It also explains the selected item's price, the average price of similar listings, and how many comparable items were used.

**How I used it:**

This tool does not call Groq. I made it deterministic because price comparison can be done directly using the dataset.

It loads all listings, looks for similar items based on category and overlapping style tags, calculates the average price of those comparable listings, and compares the selected item's price against that average.

If the selected item is missing or there are not enough similar listings, it returns a helpful fallback string.

---

## Planning Loop

The main planning loop is handled in `run_agent(query, wardrobe)` inside `agent.py`.

Here is the flow:

1. The user enters a query.
2. The agent parses the query into `description`, `size`, and `max_price`.
3. The agent calls `search_listings(description, size, max_price)`.
4. If no listings are found, the agent stops early and tells the user that no matching items were found.
5. If listings are found, the agent selects the first result because the search results are already sorted by relevance.
6. The selected item is passed into `compare_price(selected_item)`.
7. The same selected item is passed into `suggest_outfit(selected_item, wardrobe)`.
8. The outfit suggestion and selected item are passed into `create_fit_card(outfit_suggestion, selected_item)`.
9. The final output shows the selected item, price comparison, outfit suggestion, and fit card.

The conditional part of the loop is important. The agent does not keep going if `search_listings` returns no results. It stops early because the rest of the tools depend on having a selected item.

---

## State Management

I used a shared `session` dictionary to store the important information from each step.

The main values stored in the session are:

```python
session["query"]
session["parsed"]
session["search_results"]
session["selected_item"]
session["price_comparison"]
session["wardrobe"]
session["outfit_suggestion"]
session["fit_card"]
session["error"]
```

The session dictionary makes it easier to pass information between tools.

For example:

* The parsed query is used by `search_listings`.
* The best search result is saved as `session["selected_item"]`.
* `session["selected_item"]` is passed into `compare_price`.
* The selected item and wardrobe are passed into `suggest_outfit`.
* The outfit suggestion and selected item are passed into `create_fit_card`.

This way, each tool has the information it needs from the previous step.

---

## Error Handling

I tested failure modes on purpose because the agent should not crash when something goes wrong.

| Tool              | Failure Mode                     | What the Agent Does                                                     | Test Example                                                                         |
| ----------------- | -------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `search_listings` | No listings match the user query | Returns an empty list, and the agent stops early with a helpful message | I tested an impossible query like `"designer ballgown"`, size `"XXS"`, max price `5` |
| `suggest_outfit`  | Wardrobe is empty                | Returns general styling advice instead of crashing                      | I tested it with `{"items": []}`                                                     |
| `create_fit_card` | Outfit string is empty           | Returns a fallback caption/message instead of raising an exception      | I tested it with `create_fit_card("", selected_item)`                                |
| `compare_price`   | Selected item is missing         | Returns a fallback message saying there is not enough item information  | I tested it with `compare_price(None)`                                               |
| `compare_price`   | No comparable listings exist     | Returns a fallback message saying there is not enough similar data      | I tested this by monkeypatching `load_listings()` with unrelated fake listings       |

---

## Testing

I created tests for both normal behavior and failure behavior.

The test files are:

```text
tests/test_tools.py
tests/test_failure_mode.py
```

For Milestone 5, I created `test_failure_mode.py` to deliberately trigger error cases. These tests check that the tools return useful strings or empty lists instead of crashing.

I ran:

```bash
python -m pytest tests/test_failure_mode.py -v
```

The result was:

```text
5 passed
```

I also ran the full test suite with:

```bash
python -m pytest -v
```

---

## Example Interaction

Example user query:

```text
I'm looking for a vintage graphic tee under $30, size M. What is out there and how would I style it?
```

What the agent does:

1. Parses the query.
2. Searches `listings.json` for matching listings.
3. Selects the best listing.
4. Compares the selected item's price to similar listings.
5. Suggests an outfit using the user's wardrobe.
6. Creates a short fit card caption.
7. Displays everything in the Gradio app.

Example final output:

```text
Selected Item:
Graphic Tee - 2003 Tour Bootleg Style
Price: $24.00
Size: M
Condition: Good
Platform: Depop

Price Comparison:
Price Check: Good deal.
This item is $24.00. Similar listings average around $32.00, based on 3 comparable item(s).

Suggested Outfit:
Pair the vintage graphic tee with baggy jeans and chunky sneakers. The relaxed shape of the jeans matches the casual streetwear feel of the tee.

Fit Card:
Vintage tee, baggy denim, and clean sneakers. Easy streetwear fit.
```

---

## Spec Reflection

One way the spec helped me was that it forced me to think about the tools before writing the code. Instead of making one large function, I had to clearly decide what each tool takes in, what it returns, and what happens if it fails. That made the project easier to debug because I could test each tool separately.

One way my implementation changed from the original spec is that I added the fourth tool, `compare_price`, after the required three tools were already planned. Because of that, I had to update the planning loop and state management so the price comparison happens after the selected item is chosen but before the outfit is suggested.

Another small difference is naming. In some parts of my planning document, I refer to the selected listing as `new_item`, but in the code I store it as `session["selected_item"]`. They mean the same thing. I kept `selected_item` in the session because it is clearer when reading the agent flow.

---

## AI Usage

### AI usage example 1: Planning and design

I used ChatGPT to help think through the planning loop and the state management. I asked where the fourth tool should fit in the agent flow. The suggestion was to place the price comparison after the selected item is chosen and before the outfit suggestion.

I did not use an LLM call inside the price comparison tool itself. I decided that price comparison should be deterministic because the tool only needs to compare item prices from `listings.json`.

---

### AI usage example 2: Implementation support

I used Claude Code to help implement the tool functions in tools.py using the information I wrote in planning.md. After the first three tools were working, I added Tool 4 as a stretch feature for price comparison.

For Tool 4, I asked Claude Code to help update tools.py, agent.py, and app.py so the new tool would fit into the existing project flow. The price comparison tool was added after the agent selects an item from search_listings, but before the agent calls suggest_outfit and create_fit_card.

I reviewed the changes to make sure the planning loop still made sense.

After that, I reviewed the changes and made sure the tool:

* used `load_listings()`
* compared listings by category and style tag overlap
* saved the result in `session["price_comparison"]`
* displayed the price comparison in the Gradio UI
* returned fallback strings instead of crashing

---


While testing, I also ran into a Python import issue where pytest could not find `tools.py`. I fixed it by running the tests from the correct project folder and using:

```bash
python -m pytest tests/test_failure_mode.py -v
```

After fixing that, all five failure mode tests passed.

---

## How to Run the Project

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Add Groq API key

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_key_here
```

The `.env` file should not be committed to GitHub.

### 3. Run the app

```bash
python app.py
```

This starts the Gradio app locally.

### 4. Run tests

```bash
python -m pytest -v
```

---