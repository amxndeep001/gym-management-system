# Gym Management System

A Django + SQLite implementation of my Database Modelling and Design labs for a Gym Management System:
Lab 1 (ER model), Lab 2a (EER specialization), Lab 2b (relational mapping and SQL) and Lab 3 (normalization to BCNF).
Scope: gyms and fitness centres managing their daily operations.

## Setup

Requires Python 3.8+. `requirements.txt` installs Django 4.2 LTS on Python 3.8–3.12 and Django 5.2 LTS on Python 3.13+.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux / macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_gym
python manage.py runserver
```

Open http://127.0.0.1:8000 and log in with **admin / admin123**. You land on the Home page.

### Sample data: `seed_gym`

```bash
python manage.py seed_gym          # idempotent: safe to run again
python manage.py seed_gym --reset  # delete all gym data, then reseed
```

The command:

- creates the `admin / admin123` login if it doesn't exist.
- loads the exact Lab 2b sample rows: branches 1–5, staff 101–113 and their subtypes, equipment 201–205, plans 301–305, members 401–410 and their tiers, payments 501–510 and their subtypes, lockers, classes, schedules, attendance, feedback, workout and diet plans, and maintenance.
- adds generated demo data with a fixed random seed, so every run produces the same data. That's 30 more members joining over the last 6 months, a payment in each mode every month, four weeks of attendance within class capacity, more feedback, and a few Accessories (`Other` category) equipment items.

### Tests

```bash
python manage.py test gym
```

The tests cover the CHECK constraints, PROTECT deletes, overlapping member tiers, the subtype discriminator rule, the Equipment subtype form, the list filters, navigation (Home redirect, section pages, hidden subtype pages), the Gym Progress helper, and the seed command.

## Usage

### Navigation

A sticky top navbar runs across every page. On small screens it collapses into a hamburger menu, and the current section is underlined in orange.

| Navbar link | URL | What it opens |
|-------------|-----|---------------|
| Brand / **Home** | `/home/` | The landing page after login (`/` redirects here). It has a welcome banner with **Add Member** and **Record Payment**, four KPI cards with "vs last month" trends, the Gym Progress chart, a quick access tile per section, today's classes, and memberships expiring in the next 15 days. |
| **Analytics** | `/analytics/` | The detailed view: Gym Progress chart, KPIs, revenue by payment mode, members per plan, and member tiers |
| **Branch & Staff** | `/section/branch_staff/` | Cards for Branches and Staff, then *Staff Specializations (Disjoint, Total)*: Trainers, Receptionists, Managers, Maintenance Staff |
| **Equipment** | `/section/equipment/` | Count cards (Total, Cardio, Strength, Accessories, maintenance cost this month), then Equipment and Equipment Maintenance |
| **Membership & Members** | `/section/membership/` | Membership Plans and Members |
| **Payments** | `/section/payments/` | Payments |
| **Classes & Attendance** | `/section/classes/` | Gym Classes, Class Schedules, Attendance |
| **Others** | `/section/others/` | Lockers, Feedback, Workout Plans, Diet Plans |

The navbar is built from `NAV_SECTIONS` in `gym/views.py`. A context processor (`gym/context_processors.py`) passes it to every template.

### Section pages and CRUD lists

Each card on a section page shows a live record count and opens that table's list at `/dashboard/?entity=<key>&action=list`. The list, create and edit pages keep the section's sub-categories as a pill row at the top, so you can switch between siblings directly.

**Staff subtypes** (Trainers, Receptionists, Managers, Maintenance Staff) can be viewed and edited only. In place of an Add button they show a hint, e.g. *"To add a Trainer, add a Staff member with role Trainer"*. It opens the Staff form with the role already selected (`?entity=staff&action=create&role=Trainer`). The Staff list has a **Role details** column with each member's subtype attributes.

**Subtypes as filters.** Members, Equipment and Payments have no separate subtype pages in the navigation. Instead, their list pages have filter buttons with counts. A caption names the specialization constraint, and an extra column shows the subtype's attributes:

| List | Filter buttons (query parameter) | Constraint | Extra column |
|------|----------------------------------|------------|--------------|
| Members | All · Standard · Premium · Both · No tier (`?tier=standard\|premium\|both\|none`) | Overlapping + Partial | Tier: Standard / Premium badges, max visits, assigned trainer. Also an Active / Expired status. |
| Equipment | All · Cardio · Strength · Accessories (`?category=Cardio\|Strength\|Other`) | Disjoint + Partial | Specs: max speed and incline levels, or weight stack and max load |
| Payments | All · Cash · Card · Online (`?mode=Cash\|Card\|Online`) | Disjoint + Total | Details: receipt no, card type and last 4, or gateway and transaction ID |

The old subtype screens (e.g. `?entity=cash_payment`) still work by URL, but nothing links to them.

**Forms.** The Staff, Payment and Equipment forms show the chosen role, mode or category's subtype fields in the same form. Members get tier checkboxes. Subtype fields fade in and out as the choice changes, and the superclass and subtype rows are saved in one `transaction.atomic()`.

### Other pages

| Page | URL | What it shows |
|------|-----|---------------|
| Member profile | `/member/<id>/` | Every relationship for one member. Member names in lists link here. |
| Login | `/login/` | Split screen with a gym image on one side and the sign-in card on the other |

## Report section → where it's implemented

| Report section | Implementation |
|----------------|----------------|
| Lab 1: entities and relationships (ER diagram) | `gym/models.py`: one model per entity, with foreign keys for 1:N. `Locker.member` is a `OneToOneField` (1:1). Attendance links Member and Class_Schedule (M:N). |
| Lab 1: relationships in practice | Member profile page (`templates/gym/member_profile.html`) |
| Lab 2a: STAFF, Disjoint + Total | `StaffForm` (`gym/forms.py`) saves the staff row and exactly one subtype row in `transaction.atomic()`. `Trainer.clean()` and the other subtypes check `staff.role`. |
| Lab 2a: PAYMENT, Disjoint + Total | `PaymentForm` works the same way, using `mode` as the discriminator |
| Lab 2a: EQUIPMENT, Disjoint + Partial | `EquipmentForm` (a `PartialSpecializationForm`) saves the equipment row and its Cardio or Strength row in `transaction.atomic()`. Changing the category deletes the old subtype row. `Other`, shown as **Accessories**, has no subtype (partial); only its display label was renamed (no-op migration `0004`). `CardioEquipment.clean()` and `StrengthEquipment.clean()` require the matching category. |
| Lab 2a: MEMBER, Overlapping + Partial | `MemberForm` has a checkbox per tier (not a dropdown), so a member can have Standard, Premium, both or neither. Member and tier rows are saved in one `transaction.atomic()`. |
| Lab 2a: shared-primary-key inheritance | Each subtype's `OneToOneField(..., primary_key=True)` to its superclass |
| Lab 2b: sample INSERT statements | `gym/management/commands/seed_gym.py` |
| Lab 2b: join queries | The member profile and analytics pages show the same joins through the ORM |
| Lab 3: domain constraints | `Meta.constraints`: `CheckConstraint` for fee, salary, amount and capacity > 0, and rating between 1 and 5. `UniqueConstraint` on branch phone. Migration `0002`. |
| Lab 3: deletion anomaly | `Member.plan` and `Member.branch` use `on_delete=PROTECT`. A blocked delete shows a friendly message. |
| Lab 3: BCNF relations | One table per relation, each determined only by its primary key. Derived values like `Member.expiry_date` and `is_active` are computed properties, not stored columns. |

## Corrections to report data

- **Receptionists 104 and 110.** The Lab 2b INSERT into `Receptionist` listed staff 104 and 110. Both are maintenance staff (role `Maintenance`, with rows in `Maintenance_Staff`), and STAFF is a disjoint specialization. Only 102, 106 and 108 are seeded as receptionists.
- **Missing cash payment rows.** Payments 501, 505 and 509 have mode `Cash`, but the report had no `Cash_Payment` rows. PAYMENT is a total specialization, so the seed adds cash rows with generated receipt numbers (`RCPT-2026-0501`, `RCPT-2026-0505`, `RCPT-2026-0509`).
- **Workout plan duration.** The sample values (45, 60, 75) are stored as days.

## Project structure

```
gym/
  models.py                  entities, subtypes, constraints
  forms.py                   CRUD forms, incl. superclass + subtype forms
  views.py                   NAV_SECTIONS, home, section pages, CRUD dashboard, analytics, member profile
  context_processors.py      exposes the navbar sections to every template
  management/commands/seed_gym.py
  tests.py
templates/gym/
  app_base.html              top navbar layout
  home.html  section.html    Home page, section landing pages
  cells/  partials/          extra list columns, Gym Progress chart
  dashboard.html  analytics.html  member_profile.html  login.html
```
