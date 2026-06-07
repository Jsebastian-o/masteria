EXAMPLES = [
    {
        "meeting_summary": "The client needs a web-based inventory management platform...",
        "estimation": """
        ## Estimation: Inventory Management Platform

        ### Task breakdown:
        1. UI/UX Design: 40 hours
        2. Backend API (inventory CRUD): 60 hours
        3. Authentication and roles: 20 hours
        4. Dashboard with metrics: 30 hours
        5. Testing and QA: 25 hours

        **Total estimated: 175 hours**
        **Recommended team: 2 full-stack developers + 1 UX designer (part-time)**
        **Estimated duration: 6-8 weeks**
        """,
    },
    {
        "meeting_summary": """The client (Constructora Sudamericana) needs a unified web platform for the construction sector in Colombia. The system must integrate two functional blocks under a single centralized login:

        **Block A — Fiduciary Escrow Management:** Operational module to manage the full lifecycle of fiduciary escrows (Available → Reserved → Active → Closed/Liquidated → Cancelled), including property inventory by project, escrow-buyer linking, installment and payment tracking, delinquency alerts, and portfolio panel.

        **Block B — Corporate Employee Portal:** Self-service portal for all employees (100–300+) with automatic generation of employment certificates in PDF, corporate document repository by category, image gallery by albums, and company directory with search and filtering.

        The system requires 4 differentiated roles (General Administrator, HR Administrator, Fiduciary Operative, Employee), executive dashboard with KPIs, reports exportable to Excel/PDF, and an immutable audit log. No external integrations required in Phase 1.""",
        "estimation": """
        ## Estimation: Unified Fiduciary Escrow + Employee Portal System

        ### Task breakdown:
        1. **Phase 0 — Architecture, Setup and PDF Template:** 48 hours
        2. **Phase 1 — Fiduciary Core** (authentication, roles, projects, properties, escrows, buyers): 160 hours
        3. **Phase 2 — Payments and Portfolio** (payment plan, installments, alerts, portfolio dashboard): 120 hours
        4. **Phase 3 — Employee Portal** (PDF certificates, documents, gallery, directory): 180 hours
        5. **Phase 4 — Reports and Administration** (executive dashboard, reports, user management, audit): 100 hours
        6. **Phase 5 — QA, Deployment and Documentation:** 80 hours
        7. **Project Management:** 48 hours

        **Total estimated: 736 hours**

        **Tech stack:** React 18 + TypeScript / Ant Design · .NET 8 Web API · PostgreSQL 16 · Azure (App Service B2, Static Web Apps, Blob Storage, AD B2C, DB Flexible Server)

        **Recommended team:**
        - 1 Architect / Tech Lead (50%)
        - 1 .NET Backend Developer (100%)
        - 1 React Frontend Developer (100%)
        - 1 QA / Tester (50%)
        - 1 Project Manager (25%)

        **Estimated duration: 5 months (20 weeks) — Agile methodology with 2-week sprints**

        **Total year-1 investment:** COP $47,840,000 in development + ~USD $74/month in Azure infrastructure

        **Payment terms (milestones):** 30% upfront · 25% on Phase 1 delivery · 25% on Phase 3 delivery · 20% on production deployment

        **Includes:** 3 months post-launch support, CI/CD with GitHub Actions, key-user training, and technical documentation.
        """,
    },
]
