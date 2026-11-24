# Owner Groups instead of a single owner; ambiguous names become unconfirmed groups

An Action Item can have several Owners: "Anita & Rahul" and "Everyone"/"Team" (that meeting's attendees) form an Owner Group, and every member gets the item in their Follow-up. When a first name matches more than one attendee ("Priya" with Priya Nair and Priya Shah both present), the tool never guesses: all matches form an unconfirmed group, shown in each candidate's Follow-up under "Can you confirm whether this is yours?". The group is narrowed to one Person either by a later note naming them ("Priya N. to …") matching it as a Duplicate, or by a human with `actiontrack edit <id> --owner <name>`. "Someone"/"TBD" items are Unowned and appear in no Follow-up.

## Considered Options

- Store ambiguous items as unowned / skip them: loses the item or hides it from the only people who can claim it.
- Copy the item to each candidate as separate items: creates real duplicates that each need closing.

## Consequences

The model is one-to-many (item → owners) rather than a single owner column, and the CLI gains human-correction commands (`edit`, `merge`) beyond the brief's four.
