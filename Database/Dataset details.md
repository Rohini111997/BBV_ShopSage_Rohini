# ShopSage Datasets 

---

## Customer Dataset

**Dataset name:** `customers`
**File:** `data/customers.csv`
**Grain:** One row per registered guest (unique on `guest_id`)
**Purpose:** Master customer record powering ShopSage's personalization (memory),
order lookups (tools), and age-based safety checks (guardrails).


#### Schema

| # | Column | Type | Required | Description | Example |
|---|--------|------|----------|-------------|---------|
| 1 | `guest_id` | string | Yes | Primary key. Unique identifier for each guest. Format: `G` + 4-digit zero-padded sequence. | `G0042` |
| 2 | `name` | string | Yes | Guest's full name. | `Priya Sharma` |
| 3 | `age` | integer | Yes | Guest's age in years. Also used by guardrails — guests under 18 receive age-appropriate recommendations only. Range: 16–75. | `29` |
| 4 | `gender` | string | Yes | Self-reported gender. One of: `male`, `female`, `non-binary`, `prefer_not_to_say`. | `female` |
| 5 | `email` | string | Yes | Contact email. Used as the lookup key for order tracking and receipts. Unique per guest. | `priya.s@example.com` |
| 6 | `phone_number` | string | Yes | Contact phone in E.164-style format. Used for delivery notifications. | `+91-9812345678` |
| 7 | `city` | string | Yes | City of residence. Used for delivery estimates. | `Lucknow` |
| 8 | `state` | string | Yes | State of residence. Used for shipping estimates, tax, and regional availability. | `Uttar Pradesh` |
| 9 | `preferred_categories` | list[string] | Yes | 1–2 product categories the guest shops most. Pipe-separated in CSV. Allowed values: `Electronics`, `Home & Kitchen`, `Sports & Outdoors`, `Beauty & Personal Care`, `Toys & Games`. | `Electronics\|Sports & Outdoors` |
| 10 | `preferred_brands` | list[string] | Yes | Brands the guest gravitates toward, drawn from the catalog's brand list. Pipe-separated in CSV. | `Voltix\|TrailForge` |
| 11 | `budget_tier` | string | Yes | Spending band that caps default recommendations. One of: `budget` (≤ $60), `mid-range` (≤ $180), `premium` (≤ $600). | `mid-range` |
| 12 | `avoid_list` | list[string] | No | Negative preferences — things the guest does not want recommended. Pipe-separated; empty if none. | `fragranced products` |
| 13 | `signup_date` | date (ISO 8601) | Yes | Date the guest registered. Recent signups have thin history — the assistant should weight stated preferences over inferred ones. | `2024-11-03` |
| 14 | `loyalty_tier` | string | Yes | Loyalty program level. One of: `standard`, `silver`, `gold`. Gold members get free express shipping. | `gold` |

---
