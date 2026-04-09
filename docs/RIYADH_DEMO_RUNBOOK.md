# Riyadh Demo Runbook

Use this runbook to prepare the app for a customer demo of a Riyadh-based law
practice, then wipe the demo data afterward.

## What The Demo Loads

The admin-only demo seed creates a deterministic operational dataset for the
current workspace and organisation:

- 8 Riyadh-focused clients across companies, organisations, and individuals
- 14 Saudi matters across litigation, corporate, employment, compliance, and
  enforcement work
- linked office documents visible in the `Documents` area and inside case detail
- case notes, timeline events, deadlines, and Amin case briefings

The dataset is designed to make these routes feel populated end to end:

- `home`
- `clients`
- `clients/[id]`
- `cases`
- `cases/[id]`
- `documents`

## Admin Controls

Only users with the `ADMIN` workspace role can load or wipe the demo dataset.
The controls are available on:

- `Clients` page
- `Cases` page

The existing buttons remain the control surface:

- `Load Demo Data`
- `Wipe Demo Data`

## Recommended Demo Flow

1. Sign in as an admin user.
2. Open `Clients` or `Cases`.
3. Click `Load Demo Data`.
4. Wait for the success notice confirming the Riyadh dataset counts.
5. Present the product in this order:
   - `home` for the overview and urgent matters
   - `clients` for the client mix
   - a corporate client detail page
   - `cases` for matter breadth and filters
   - a case detail page for notes, timeline, and linked documents
   - `documents` for the office-document workspace

## Refreshing The Dataset

If the demo dataset already exists, clicking `Load Demo Data` refreshes it to
the canonical Riyadh dataset. This is safe for seeded records because the
backend wipes the existing demo dataset first and then recreates it.

## Wiping After The Demo

1. Return to `Clients` or `Cases`.
2. Click `Wipe Demo Data`.
3. Confirm the success notice showing the removed counts.

The wipe flow removes seeded:

- demo cases
- orphaned demo clients
- seeded office documents
- seeded notes and timeline events via case cascade

It is designed to leave non-demo workspace data untouched.
