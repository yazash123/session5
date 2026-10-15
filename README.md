# Session 5: risk impact scoring

The House of the People "Where does each risk land?" page, running on its own with Firebase in place of claude.ai.

- **Live page:** https://yazash123.github.io/session5/ (group links: add `#g1` to `#g17`)
- **In Webflow:** paste `webflow-embed.html` into one Code Embed in a full-width section (not a Container). Group links work on the Webflow address too, for example `…/your-page#g5`.

## Files

| file | what it is |
|---|---|
| `index.html` | the page. Built from the claude.ai artifact, so don't hand-edit it; rebuild instead. |
| `firebase-config.js` | the Firebase web config. Public by design. |
| `firestore.rules` | paste into Firestore → Rules. Anyone can read and submit well-formed scores; nobody can delete from the page. |
| `webflow-embed.html` | the one Webflow embed. |

## What changed from the artifact

- `window.claude.use('db')` is Firestore (compat SDK 10.14.1 from gstatic). `downloads` saves the CSV in the browser.
- Each member listens only to their own group's scores. Only the **All groups** tab listens to everyone. That keeps reads well inside the free tier with about 100 people.
- **Clear all** is switched off on the page. To clear, go to the Firebase console → Firestore → `subs` → ⋮ → **Delete collection**.
- The organiser password is in the page source, so treat the CSV as readable by anyone with the link.

## Data

One document per person, group and risk in `subs`: `{name, group, risk, s: {area: -1..3}, at}`. Resubmitting overwrites it.
