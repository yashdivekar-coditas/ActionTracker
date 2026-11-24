# Duplicates merge on Owner plus fuzzy task wording; Done is sticky

The same Action Item reappears across weekly meetings with reworded text ("Priya N. to send revised quote to Acme — by Friday" vs "Priya to send the revised quote to Acme by Friday"). We treat two items as Duplicates when their Owners match and their task text is similar after stripping punctuation, filler words and the due phrase. On merge the latest Meeting Date's Due Date wins, every Source is kept, and Done never reverts: a later `[ ]` cannot reopen an item ticked `[x]` or marked done by `actiontrack done`. Item ids stay stable across re-ingest.

## Considered Options

- Exact text match: predictable, but leaves the reworded repeats as separate items.
- Owner + meeting series: misses repeats across different meetings.

## Consequences

A similarity threshold can occasionally merge two genuinely different tasks by the same Owner; the threshold is tuned against the sample notes and every merge keeps its Sources so it can be audited.
