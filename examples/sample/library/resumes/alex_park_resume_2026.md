# Alex Park
Portland, OR · alex.park@example.com · (555) 010-3344
Backend Systems | Distributed Infrastructure | Observability | Platform Engineering

Staff engineer with 11 years building backend systems at consumer-health and robotics companies. Personally shipped an internal feature-flag service used by 200+ engineers. Maintainer of an open-source pagination library with 2k GitHub stars. Speaker at PyCon US 2025 on incident-response tooling.

## Professional Experience

**Lumen Health, Inc.**
*Staff Software Engineer; March 2022 to present*

- Led the API platform team (12 engineers) responsible for the company's public REST and GraphQL surface. Owned the multi-year roadmap, the on-call rotation, and the SLO/SLI program.
- Personally designed and built the internal feature-flag service (`switchboard`) used by 200+ engineers across 40+ services. Reduced bad-deploy rollback time from 18 minutes to 90 seconds.
- Directed the team that built the cross-region data-sync pipeline (4 engineers, 7 months); reviewed the design and approved the production launch.
- Drove the migration from monolith to event-driven services for the patient-records subsystem; cut P95 read latency from 380ms to 95ms.
- Established the company's first formal incident-response runbook; reduced mean-time-to-resolution by 42% over two quarters.
- Mentored 6 mid-level engineers into senior roles. Reviewer on the architecture council.

**Nimbus Robotics**
*Senior Software Engineer; July 2018 to February 2022*

- Directed the team that built the fleet telemetry pipeline (Kafka, Flink, Snowflake) ingesting 30M events per day from 800 robots. Defined the schema-evolution strategy.
- Personally wrote the on-board diagnostic agent (Rust) shipped on every fleet device.
- Designed the simulation harness that let test engineers run regression suites without physical robots.
- On-call lead for the platform team; established SLOs and a postmortem culture.

**Crate & Bakery**
*Backend Engineer; January 2015 to June 2018*

- Built the order-routing service that powered the company's first national fulfillment network.
- Owned the payments integration with Stripe, Adyen, and PayPal.

## Open Source

- **paginate-cursor**: Python library for cursor-based pagination over SQL and Elasticsearch. 2.1k GitHub stars. Maintainer since 2020.

## Talks & Publications

- "Incident-response tooling that engineers actually use", PyCon US 2025.
- "Schema evolution without downtime", InfoQ guest article, 2023.

## Education

**B.S. in Computer Science**, State University (2014). Magna cum laude.
