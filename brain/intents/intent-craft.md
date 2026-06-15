---
name: intent-craft
kind: interest
one_line: A codebase that reads uniformly, idiomatically, minimally - low cognitive load forever.
negotiation: position="run aav-style / idiomatic rust / trim the fat / reuse the suite" -> interest="craftsmanship - a clean, consistent, durable artifact"
---

# Interest: CRAFT (consistency, idiom, minimal durable surface)

Arpad cares how the code *reads*, not just whether it runs. A uniform, idiomatic,
minimal codebase costs less to hold in your head every time you return to it. This is
the interest behind the whole `aav-style` / idiomatic-rust apparatus and the relentless
"trim the fat."

**Positions that serve this interest:**
- "use rust style in rust, ts style in ts. thats it"
- "idiomatic rust said NEVER do unwrap_or you idiot, why did you do that?"
- "trim the fat ... get to the damn point quick and concise. verbose doc comments tho"
- "any way to clean up code (net reduction of lines)?"
- "why is the csv using custom functions and not the ones defined in the suite?"
- "no clap, custom cli that you literally run using ./binary /path/to/folder"

**The interest behind them:** durable readability and low future cognitive load. Note
the *nuance*: terseness applies to inline comments and surface area, but **doc comments
and doc tests stay verbose** - docs are the durable interface; inline noise is debt.

**Tension to manage:** craft vs. velocity. He will pay review/style cost up front to
avoid rot. But "if no net reduction possible, dont force it" - don't manufacture churn
in craft's name. See [[principle-06-idiomatic-per-language]], [[principle-07-trim-fat-verbose-docs]].
