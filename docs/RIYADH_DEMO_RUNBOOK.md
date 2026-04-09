# KSA Demo Runbook

Use this runbook to prepare the app for a customer demo of a fictional but
authentically Saudi law-firm workspace, then wipe the seeded data afterward.

## What The Demo Loads

The admin-only demo seed creates a deterministic operational dataset for the
current workspace and organisation:

- 11 clients across Riyadh, Jeddah, Khobar, Madinah, Makkah, Buraydah, Tabuk,
  and Abha
- 22 Saudi matters across litigation, corporate, compliance, employment,
  dispute strategy, and enforcement
- linked office documents in DOCX, XLSX, PPTX, and PDF formats
- case notes, timeline events, deadlines, and Amin case briefings

The seeded portfolio is designed to make these routes feel populated end to end:

- `home`
- `clients`
- `clients/[id]`
- `cases`
- `cases/[id]`
- `documents`
- `documents/[id]`

## Admin Controls

Only users with the `ADMIN` workspace role can load or wipe the demo dataset.
The controls are available only in the admin section:

1. Open the admin rail.
2. Go to `Demo Data`.
3. Use `Load Demo Data` or `Wipe Demo Data`.

No demo-data controls remain on the `Clients` or `Cases` pages.

## Recommended Demo Flow

1. Sign in as an admin user.
2. Open `Admin` -> `Demo Data`.
3. Click `Load Demo Data`.
4. Wait for the success notice confirming the KSA dataset counts.
5. Present the product in this order:
   - `home` for the overview and urgent matters
   - `clients` for the Saudi client mix
   - a corporate client detail page
   - `cases` for matter breadth and lifecycle states
   - an active case detail page for notes, timeline, and linked documents
   - a closed case detail page to show historical matters
   - `documents` for the office-document workspace and seeded PDFs

## Refreshing The Dataset

If the demo dataset already exists, clicking `Load Demo Data` refreshes it to
the canonical KSA dataset. This is safe for seeded records because the backend
wipes the existing demo dataset first and then recreates it.

## Wiping After The Demo

1. Return to `Admin` -> `Demo Data`.
2. Click `Wipe Demo Data`.
3. Confirm the success notice showing the removed counts.

The wipe flow removes seeded:

- demo cases
- orphaned demo clients
- seeded office documents and their storage objects
- seeded notes and timeline events via case cascade

It is designed to leave non-demo workspace data untouched.
