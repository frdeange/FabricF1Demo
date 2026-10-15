# F1 Demo: Grand Prix Promoter and Fan Experience

## Status and objective

The plan is approved by the user. P0 created the public repository `frdeange/FabricF1Demo` on `main`, the English roadmap issue [#1](https://github.com/frdeange/FabricF1Demo/issues/1), and linked package issues #2–#15. The validation-only CI foundation for issue [#8](https://github.com/frdeange/FabricF1Demo/issues/8) is committed on branch `8-ci-cd-foundation` at `1455a224`; GitHub Actions passed. The unattended cloud-deployment pilot remains blocked pending approval and qualification of concrete resource targets, permissions, and budget. No cloud resources have been deployed.

Review after feedback: GitHub is the source of truth, and GitHub Actions orchestrates CI/CD from the first delivery; manual deployments must not be the normal route. Additional review: all partner-shareable deliverables and GitHub traceability are in English; specialized agents and model/effort choices are defined per phase, favoring capability without using oversized models or high reasoning for mechanical tasks.

The goal is to build a coherent demo with two apps on a shared Fabric foundation: the business and operations side of the promoter, and the fan race experience. Reuse patterns from FabricHubDemo without copying its assumptions about capacity, identities, licensing, or preview availability.

Explicit constraint: both experiences must run as managed Rayfin apps in Fabric and visibly demonstrate their value; they are not generic apps merely hosted elsewhere. Two independent Rayfin apps/items are agreed.

This English execution plan is the partner-shareable repository artifact; it excludes internal presentations, credentials, and non-redistributable data.

## Confirmed decisions

- The protagonist organization is a Grand Prix promoter and its circuit.
- Two views/apps are desired: an internal business app and an external race/fan app.
- Sources must contain relevant and related data.
- Sustainability comes first: avoid fragile trials, or make sure they can be reconstructed.
- SAP authenticity should be evaluated further before choosing SAP-shaped data.
- The development split across agents will be defined after the scope is settled.
- The user has corporate Fabric capacity and usable Azure subscription access. Concrete capacity, permissions, region, quotas, and budget have not been verified.
- The user considers a 30-day SAP window acceptable if the environment can be reconstructed easily. Do not dismiss S/4HANA advanced trial / CAL because of duration alone. Prioritize evaluating it as a real ERP source, subject to usage rights.
- The demo will be shown to customers or partners. The ordinary free CAL trial is not considered enabled for that use according to its FAQ; confirm demo rights through the applicable agreement before activating or presenting an SAP environment.
- User decision: Plan A uses a real SAP ERP obtained through a still-unknown route; Plan B mirrors the colleagues’ approach with a synthetic SAP source and qualified native Fabric processing. Do not block design while waiting for Plan A first. The design is approved; every deployment still requires concrete resources and qualified usage rights.
- The fan app must cover earlier races replayed as live-like flows and truly live races. The user sees potential for distinct packages and products attached to those experiences; the catalog remains pending.
- Payments are agreed to be simulated, with orders, entitlements, and simulated refunds/credits persisted. No payment gateway, no card storage, and no bank charges or refunds.
- Rayfin is a central part of the demo objective for both experiences. Hosting, authentication, typed APIs, operational data, business functions, and Fabric integration must all be visible and verifiable in the journey.
- The internal Hub must be a rich and complete experience comparable to the reference, not a simple admin console for the fan portal. The consumer portal has different content and UX. The user questioned the benefit of merging them and asked for a recommendation on topology and identities. Confirmed decision: two Rayfin apps, one connected business, separate experiences and permissions, with shared contracts and shared processes.
- Confirmed scope for the first full demo: the two apps and the six Hub areas described below, linked by business journeys. Delivery will be staged; the Hub will not be reduced to a minimal console and the portal will not be deferred.
- Out of scope for the first phase: real charges, broadcast video/radio, autonomous agent decisions, advanced financial planning, and production exploitation.
- Confirmed requirement: work in a GitHub repository and deploy through GitHub Actions with fabric-cicd, CLI/APIs, and CI/CD practices suitable for each resource type. Do not create or configure the repository, identities, or resources yet.
- Confirmed requirement: deliverables in English for sharing with partners across the region, including issues and labels. The conversation may continue in Spanish; do not introduce a second localization for the apps by default.
- User model criterion: prefer intelligence over cost, but match the model/effort to the actual difficulty and avoid over-sizing tasks.

## Delivery language

English is the default language for both applications and every partner-shareable artifact: UI copy, navigation, errors, product descriptions, fictional business records, documentation, architecture diagrams, demo scripts, setup/runbooks, and release notes. Code identifiers, necessary comments, agent briefs, and handoff reports are also authored in English. Proper names, API field names, and quoted source material should be preserved when changing them would hurt correctness.

GitHub issue titles/bodies, acceptance criteria, labels/descriptions, milestones if used, progress reports, commit subjects, PRs, and review packages are in English. This English execution plan and the agent playbook are intended for the approved repository; the separate Spanish working copy remains conversation material. English-language checks are part of review, not a new multilingual product feature. Sharing with partners does not authorize publishing internal reference material, licensed datasets, tenant details, or credentials.

## Evidence reviewed

### Local project

- Private local reference materials informed planning but are excluded from this public repository; their source files, filenames, paths, and extracted metadata are not reproduced here.
- No sports dataset has been qualified for redistribution or commercial demonstration; do not assume lap times are sufficient to reconstruct real coordinates.
- Any dataset used later requires legitimate access and separate validation of its schema, license, and coverage.
- No existing Fabric workspace or its infrastructure has been inspected.
- There is no local Rayfin project, no installed packages, and no documentation for a version chosen for this demo. No scaffolding has been done during planning.

### Public reference fredgis/FabricHubDemo

Reference revision identified during consolidation:
5ad08f4c3d6352408de84a96796b4bfdf393b23f.

Use it to evaluate reusable components while preserving licenses and attributions. The documents reviewed during research were inspected on main; the revision is a reproducible starting point, not a deployment verification.

- Real Oracle Free in a private VM, Windows gateway, mirroring, and documented insert/update/delete testing. Five master tables feed Raw through shortcuts.
- Real Salesforce with standard and custom objects seeded with fictional data. Native BPS ingestion, Silver, and cross-domain consolidation. The scripts use an authorized org; they do not prove the org is Developer Edition or a trial.
- SAP: synthetic generation and Datasphere-shaped landing, native mirroring/BPS, and documented publication of 22 domain tables and nine views. The documentation clarifies that the chosen S/4HANA profile does not prove a connected S/4HANA system.
- React/Rayfin cockpit with trusted server functions, transactional SQL, and outbox. Committed events pass through worker, Event Hubs, Eventstream, and Eventhouse. Analytical publication is asynchronous; do not equate click-through with Gold availability.
- Gold and ontology share keys. The read-only Data Agent uses the native graph; direct attachment of ontology v2 was blocked in that environment.
- Planning appears in the architecture, but is not considered a proven deployed capability.
- BPS/runtime incompatibility and manual native configuration steps existed. Do not promise fully automatic deployment or copy the recovery version.
- These are documented facts in the repository, not checks of the live environment.

### Rayfin: version evidence and design limits

package.json, package-lock.json, rayfin.yml, and the Rayfin skills included in the reference’s apps/cockpit were reviewed. The lockfile resolves CLI, guide, client, and auth-provider-fabric to 1.36.2. The documentation for that exact @microsoft/rayfin-guide version was read from the tarball resolved by the lockfile, without installing or running packages.

Documents consulted: index.md, known-limitations.md, auth/overview.md, auth/fabric.md, hosting/index.md, functions/index.md, app-backend/index.md, and the CLI connectors router category-a-entities.md. Also data/permissions.md and the reference’s operational schema to confirm per-user grants.

- Managed Fabric uses Entra SSO, MSSQL SQL, APIs, and managed hosting. Do not transfer local email/password authentication into the deployed Fabric app.
- It requires assigned capacity and the Fabric Apps workload enabled by an administrator. Having corporate capacity does not prove that Rayfin is enabled.
- Using the app and its APIs requires item permissions (Run and interact / Read and execute); do not solve this by granting access to the entire workspace.
- A workspace can contain multiple Rayfin items. Each item has its own endpoint and services; do not assume shared database, session, or authorization between apps.
- Functions separate identity: external access uses app identity tokens (the item owner's identity in this version), while access to the Rayfin database uses the caller's identity/permissions. Authorize each command and limit resources.
- Existing source connectors and app-owned entities are different mechanisms; the semantics of each connector live in its versioned package.
- The included connectors skill states that new Kusto connector authoring was on hold in that release. Consult the live catalog and the chosen version's guidance: do not promise Eventhouse, WebSocket, or push-subscription connectors without qualification.
- Local testing does not prove actual connector usage or deployed SSO. Validate data and authorization from the app in Fabric, not only from the developer CLI.
- Documented limits include no direct many-to-many and explicit pagination. Do not freeze entities or queries before reading the limits and APIs of the packages installed in the approved project.
- This evidence is from reference 1.36.2, not a statement about the latest release or the user tenant’s feature flags. Revalidate on start.
- The guide documents basic anonymous/authenticated roles and policies by user, row, field, and action. Business profiles (operator, support, finance, fan) require modeling and approved assignment; they do not appear automatically when creating a Rayfin item, and a frontend profile selector is not enough.
- The reference uses OperatorGrant/FlixyAccessGrant entities filtered by claims.sub so callers can read their own assignments; commands are re-authorized in functions. This does not mean callers can grant themselves privileges. It is prior art, not a solved multi-audience model: do not copy the broad internal-cockpit read permissions into our consumer experience.

## Source options and sustainability

| Option | Authenticity | Cost and continuity | Preliminary assessment |
| --- | --- | --- | --- |
| Self-managed Oracle AI Database Free | Real Oracle engine; fictional data owned by us | Free software; VM/hardware, storage, gateway, and operations are separate | Good candidate; fix the version admitted by mirroring before deployment |
| Salesforce Developer Edition | Real CRM, API, and owned objects | Free for development; small storage; current inactivity policy | Good candidate for a bounded sample, not for the full GP audience |
| Authorized SAP S/4HANA lab | Real ERP and real documents/processes with demo data | Existing or provisioned access/licensing; not proven free | Best authenticity if a sustainable environment is available |
| SAP S/4HANA advanced trial / CAL | Temporary real ERP | Official page says 30 days; cloud infrastructure and usage rights are separate | Priority candidate to evaluate per the user’s instruction; reproducibility and licensing are separate gates |
| SAP S/4HANA public basic trial | Shared ERP with predefined data | Temporary; no customization, master data, or BTP integration | Not suitable as the integrated source for this demo |
| ABAP Cloud Developer Trial 2025 | Real ABAP and HANA platform, not full S/4HANA ERP | Free for education/demo; initial three-month ABAP license renewable through the official process; HANA also requires follow-up | Pilot if we want to show extraction from ABAP, not to claim standard FI/SD processes |
| SAP HANA express | Real HANA engine; own tables and business logic | Free up to 32 GB RAM; infrastructure is separate | Database alternative, not a substitute for S/4HANA or proof of SAP BPS |
| SAP-shaped data and native Fabric route | Simulated source, real Fabric processing if qualified | Easy to regenerate; storage and Fabric are not free because of that | Similar to the reference; label it unambiguously |

Official ABAP container requirements: 4 CPU, 16 GB RAM for the environment and 150 GB disk on Linux; SAP recommends 32 GB RAM. It is not a lightweight container. License renewal does not equal deleting and rebuilding the system, but it depends on the terms and availability of the official service.

### CAL: finding and change of focus

Do not require indefinite persistence if the user accepts rebuilding the environment. The real S/4HANA candidate may be more suitable than building an ERP of our own on ABAP. Do not choose the template, size, or extraction route yet.

The official CAL FAQ states:

- The trial period starts when the trial agreement is accepted for the template; suspending the instance does not stop the period.
- The trial does not charge SAP license fees during the trial period, but Azure charges infrastructure.
- After expiration, it may be suspended without deleting resources or all their costs.
- Continuity requires a CAL subscription and the appropriate SAP product licenses.
- No authorization was found to restart the period by recreating instances. Technical reconstruction is not the same as renewing the trial right.
- The free trial excludes demonstrations to potential customers, workshops with employees/partners/customers, and commercial development/prototyping/PoC use. Confirm the intended use and the exact terms of the template; seek authorized test/demo rights if the scenario falls into those categories.

These restrictions do not mean CAL is unusable: they mean the free evaluation license may not be the right one for showing this demo. Do not activate the trial until the data contract, automation, and preflight are ready, so the window is not spent on preparation.

The CAL product page distinguishes the library subscription from the licenses of the SAP products contained in it: paying for CAL is not enough by itself. Its FAQ points to SAP for test/demo licenses. The library also advertises a Cloud ERP Private discovery package for test/demo/development aimed at eligible partners. These are routes to consult, not proven access or free use. Confirm with the agreement holder the right to use, external integration with Fabric, load own data, and demo to the intended audience.

If this route is authorized, reconstruction must cover two layers:

1. Provision SAP through a supported CAL template, with private configuration, Azure prerequisites, start/stop, and version/connectivity checks.
2. Rebuildable own configuration: only the strictly necessary company codes/sales organizations and master data, seeded through supported APIs with external keys, mappings, Fabric connections, and reconciliation tests.

Keep the business keys even if SAP SIDs, endpoints, identities, or document numbers change. Resolve those identifiers again on each deployment. Do not write directly to SAP tables just to fake processes: generate documents through supported business interfaces. Test deltas and full reconstruction from a new environment with valid rights. Validate separately any export and reuse of data produced under the evaluation license.

Salesforce: current documentation distinguishes DE and DE Legacy; current DE may be deleted after 45 days without login. Do not promise permanence or rely on API extraction keeping the org alive. Confirm the policy of the specific signup. The REST guide declares 5 MB of data storage. Measure real usage and keep the large-detail access and event history in another source.

Fabric trial lasts 60 days and the documentation excludes Copilot, Data Agent, and Trusted Workspace Access. It does not reproduce the reference in full. Available corporate capacity avoids buying another one, but it does not eliminate real consumption. An unallocated VM avoids compute, not disks and other persistent resources. Free software does not imply a complete free or maintenance-free solution.

## Agreed SAP strategy: Plan A / Plan B

### Plan A: real SAP ERP, provisioning and rights pending

The objective is to connect an authorized real S/4HANA for this audience and generate documents through supported business processes/APIs. The access path may be an existing lab or a CAL deployment with suitable rights; it has not been chosen or obtained. Evaluate version, extensibility, permissions, and extraction once a candidate exists. Do not promise a connector or BPS route before it has been qualified.

Specific deliverables: reusable configuration, idempotent loading of master data and own documents, an ingestion adapter, and a reconstruction runbook with tests. Obtaining and authorizing the environment is a separate external dependency.

### Plan B: reference approach, without claiming a connected ERP

Generate a consistent synthetic set of SAP domain documents and master data, with explicit source keys and representations. Adapt it to supported native input, such as the Datasphere-shaped landing used by the colleagues, and test mirroring/BPS and publication in our tenant.

The reference proves its own case, not universal compatibility for any generated schema. Run a small pilot before scaling the generator. Keep generated input, native jobs, processed output, and evidence separate. If a native piece is unavailable, state that and agree on another route; do not silently replace the processing.

### Shared contract and switching between plans

- Same business entities, canonical keys, granularities, and KPI definitions.
- Different source representations: do not force fictional SAP tables to exactly match each real release. Adapters normalize to the common contract.
- Apps consume service contracts and published models, not the simulator tables or direct SAP endpoints. Changing the source does not change the screens.
- Visible provenance label: connected ERP vs. simulated SAP scenario.
- Reconciliation tests per plan: documents and lines, amounts and currencies, states, keys, and relationships. Do not require internal SAP numbers to match exactly.
- Data from both plans is never mixed or summed: isolate runs/datasets and publish one identified version. Preserve source and freshness traceability.
- Preparing Plan B and the contract first does not mean abandoning Plan A.
- Do not develop both full adapters in parallel before the pilot and before an authorized A environment exists; avoid duplicated work and cost.

## Agreed functional scope

### Internal app: GP business and operations

Six areas, with their own design and comparable to the reference cockpit:

| Area | Content and relationship with other systems |
| --- | --- |
| Grand Prix business | Sales, commercial occupancy, amounts, costs, and event result with visible definitions |
| Products and hospitality | Tickets, digital passes, packages, pricing, availability, and reservations |
| Customers and marketing | Audiences, campaigns, preferences, and Salesforce consent |
| Sponsors | Accounts, opportunities, agreements, packages, and verifiable commitments; no invented ROI |
| Service and operations | Cases and incidents linked to customer, product, area, or race, compensations and credits |
| Business and data exploration | Real relationship graph, SAP documents, provenance/freshness, and query agent if qualified |

Do not confuse commercial occupancy sold with measured physical attendance: the latter requires synthetic access events identified as such. The financial result is a scenario metric with explicit included/excluded costs, not certified accounting. Design screens around questions and actions, not tables.

### Fan app: race and context

Standings, laps, gaps, pit stops, drivers, and comparisons; a map with positions only if an appropriate authorized source exists. Two modes are agreed: replay of recorded races emitted as a temporal flow, and real live races. Static history serves as additional query data, not as a substitute for replay. Do not claim real telemetry from invented interpolation.

Pending decision: public/anonymous or authenticated. Do not assume Fabric Apps supports public consumer access. Reframe this decision under the Rayfin constraint: for managed reference the identity is Entra and authorization is by item. A demo persona called fan does not imply a new B2C login system. Propose authorized accounts that represent fans; external/guest access only after validating real support, policies, permissions, and licenses. A hosting URL does not grant anonymous access to data or enable purchases without identity.

### Replay and live race

A common sports-events contract feeds the same experience and product access rules. Two separate adapters:

- Replay: authorized and cached dataset, reproduced at 1x with proposed pause/step/restart controls subject to scope. The interface always shows that it is replay and the original race/date.
- Live: enabled source, with visible latency and freshness, lost-connection handling, and resumption. Do not promise official service or guaranteed latency.
- Keep original event time, ingestion time, and playback clock separate, with run_id, sequence, and session/driver keys. Isolate executions so restarting a race does not duplicate analytical facts or commercial orders.
- Queries, aggregations, and agent answers must respect the playback instant; do not reveal final results while showing the current lap.
- Live is not marked qualified until a real authorized session test has been observed. If there is no active session, show it as unavailable; do not serve hidden replay.
- Telemetry and location are data, not broadcast video or radio/audio. Those contents and their rights are outside the base proposal.

FastF1 documents lap times, telemetry, and positioning and is a candidate for history. Coverage, data quality, licenses, and any actual race have not been verified. OpenF1 documents history from 2023 and subscription-based live. The website advertises EUR 9.90/month for personal Sponsor use; do not use that price as a budget or authorization for a commercial demo to customers/partners. For other uses, contact them about licenses. The code license does not grant data rights. Redistribute/exhibit permission must also be checked for replays.

### Proposed initial commercial catalog

Technical proposal to be turned into contracts: Replay Pass, Live Race Pass, and Weekend/VIP Bundle (replay + live + event hospitality). Define validity by race/event, included content, and entitlement state; do not assume recurring subscriptions. The names are demonstrative, not official F1 products or sale rights.

Persisted purchase creates order and access; the case in Salesforce and any refund/credit connect the fan experience to SAP A/B finance and internal analytics. Separate customer identity, consent, order, payment, fiscal document, and access. Do not equate fan app access purchase with a physical circuit ticket. Sync with the ERP by state and reconciliation; do not block access grant on an analytical Gold refresh.

Simulated payment is confirmed: a validated command persists the simulated result identified as such, the order, and its access right through a local transaction or a process with recoverable states. Use idempotency so retries do not create duplicate orders or access. A persisted credit does not claim a money refund; define its effect on access by compensation type. Keep audit and separate operational states from asynchronous analytical publication. In Plan A, the SAP document must be created through a supported interface and reconciled; failure is shown as pending/error, never as a created document. In Plan B, the equivalent remains labeled as a simulated scenario document.

### Master systems and data to prepare

| System of record | Source entities | Why it adds value to the story |
| --- | --- | --- |
| Real Oracle | Circuit, zone, product/SKU, bundle component, pricing, and commercial capacity | Catalog and inherited commercial rules that change via CDC |
| Real Salesforce | Contact/Account, Campaign, consent, Opportunity, agreement/commitment, and Case | Customer/sponsor relationship, campaigns, and service |
| SAP A or B | Mapped business partner, related ERP order, invoice/line, credit/line, supplier, purchase/cost, and cost center | Documents and costs linked to commercial operations |
| Operational persistence accessible through Rayfin | Commercial order/line, reservation, simulated payment, purchased entitlement, consumption session, support request, outbox, idempotent receipt, and audit | Operations executed by the apps, with recoverable states |
| Authorized sports source | Meeting/session, driver/team, lap, position, location, stint, stop, and track status, according to real coverage | Replay and live normalized to the same contract |

Oracle maintains the base capacity and availability; reserved and sold allocation is calculated in the transactional system, with concurrency control. Do not replicate a second mutable inventory without a synchronization rule. A support request may begin operationally and sync to Case; Salesforce keeps the CRM case and the app the synchronization link/state. A commercial order and an ERP order are different related documents, not two independent records to be summed as separate sales.

Fictional data is prepared first by a canonical generator and then sent to the system that must act as source. Use a deterministic manifest with seed, scenario version, stable external keys, provenance, and expected counts. Do not load Gold directly to simulate a nonexistent source integration. Real sports sessions are not invented: they are joined to a fictional commercial event with a mapping table and clear labeling.

Initial dataset is bounded to one reference race/session and its commercial event, including normal and exception scenarios. Expand sessions and volume after measuring. The CRM sample fits the real org quota and does not represent the full audience. Keep the high-volume access/telemetry data out of Salesforce.

Canonical contracts to close before splitting development:

- Event, RaceSession, Driver, CircuitZone, Product, BundleComponent, and Price.
- Party/Customer, SponsorAccount, Campaign, Consent, and CampaignTouch.
- CommercialOrder/Line, PaymentSimulation, Reservation, and Entitlement.
- CRMCase, Incident, SponsorshipAgreement/Commitment.
- ERPDocument/Line and DocumentLink, SupplierCost, and CostAllocation.
- RaceEventEnvelope, ReplayRun, and SourcePublication.

Each contract defines owner, key, granularity, currency/unit, timestamps, states, PII, allowed operations, Plan A/Plan B mappings, and valid/invalid examples. Keep PartyKey, EventKey, SessionKey, ProductKey, OrderKey, and CaseKey stable; do not use email as a shared key. Entra identity and CRM customer are linked by server-side assignment, not by a browser buyer selector. Amounts are in exact minor units, with separate currencies and explicit tax criteria. Invoice, simulated charge, and scenario revenue are not synonyms.

### Four acceptance journeys

1. Fan purchase: Oracle product/rate -> Rayfin order and access -> simulated result -> SAP A/B document -> Fabric consolidation -> Hub, with no duplicates.
2. Hospitality B2B: Salesforce account/opportunity -> package/reservation -> order and invoice -> allocated costs -> result by event and client in the Hub.
3. Complaint: fan request -> CRM case -> authorized Hub decision -> persisted credit and compensation -> explicit effect on access -> reconciliation.
4. Sponsorship: account/agreement -> commitments and costs -> related documents and follow-up. Distinguish contracted, invoiced, and fulfilled; do not infer causal ROI or conversion from simple exposure.

For the credit contract, propose full credit with revocation of unconsumed access and partial compensation without revocation; confirm this rule before implementation. Do not model bank payments or real settlements.

## Candidate architecture and criteria

Sources -> identified ingestion -> Raw/Silver -> shared Gold -> separate projections for apps, analytics, and, if available, ontology/agent. Apps write through an authorized transactional backend, not directly to Gold. Fan access is isolated from PII, sponsorship, and internal finance. Both frontends and their own services are deployed in Rayfin/Fabric. Do not replace Rayfin with external web hosting if a blocker appears: communicate it and resolve the enablement or adjust the scope with the user.

### Agreed Rayfin topology

Confirmed after clarifying the difference in content: two apps, one business domain. The previous suggestion of one item with two areas was a backend simplification, not a Rayfin limitation or a requirement to manage profiles together.

Two Rayfin items (GP Control and Fan Experience), with shared contracts and their own access limits. Choose a single system of record for orders/access/credits and a supported route for exchange or common access. Do not duplicate orders in two app databases or treat a Gold read as transactional synchronization. Validate that route before building both apps.

Agreed internal Hub: GP business, sales and revenue, hospitality and occupancy, sponsorship/campaigns, incidents and complaints, SAP documents/costs, entity and relationship exploration, provenance/freshness, data agent if available, and authorized demo- scenario controls. Prioritize complete journeys and then increase depth; do not reduce it to a CRUD table.

Proposed fan portal: race and package discovery, own purchases/access, replay/live experience, driver/comparison views, and own support. Design, navigation, and deployment can be independent from the Hub.

Share contracts, types, utilities, key system, Fabric projections, and integration tests—not necessarily menus, layouts, or visual components. Do not create an extra microservices backend by default. The shared persistence topology is decided by the supported preflight, not by assuming the two item databases are shared or that one app may freely write into the other.

### Identity and permissions in two apps

Three separate layers:

1. Entra identity establishes who the person is, with execution permissions in each item. Sharing identity does not mean reusing tokens/sessions manually or automatically enabling access to both apps.
2. Business profile assigned by administrator: fan, operator, support, finance, according to approved scope. The profile enables actions; it does not depend on a user-modifiable browser option.
3. Data permissions: fan sees only their own orders, accesses, and cases; support and finance see what is necessary for their role. Commands validate actor, ownership, state, and server-side authorization. Do not give the fan global Gold access.

Propose separate demo accounts for operator and fans and show both apps in separate browser sessions. One identity may have more than one assignment if authorized; do not implement customer impersonation to simplify the demo. Changing the view does not change the identity or grant privileges.

### Early gate: deployed Rayfin journey

Before developing the full catalog or animated map:

1. Confirm workspace/capacity, Rayfin workload, and chosen version.
2. Approve a minimal deployment with own test data and authorized accounts.
3. Test SSO and permissions with at least two fans and one operator: own access, denial of other people’s data, and denial of internal commands from the fan profile.
4. Test one persistent reliable operation (simulated order or minimum equivalent), one allowed Fabric connector/read, and its real render in the browser.
5. Test the temporal race contract from the Rayfin backend through the supported path. Measure freshness, polling frequency, latency, and CU; choose the performance budget with evidence before promising high-frequency updates.
6. Since there are two items, test that the order is visible and manageable from both experiences without duplication and with correct authorization before developing more modules.

Business functions must not become endless ingestion workers. Persistent ingestion/replay is a separate component, according to the qualified Fabric path; Rayfin consumes and executes app commands.

### What value Rayfin must prove for each journey

| Journey | Evidence of value |
| --- | --- |
| Access as fan or operator | Fabric hosting, SSO, and data/permission isolation |
| Browse catalog and buy package | TypeScript model, typed API, and server command with validation |
| View order and access after refresh | Real operational persistence, not browser session state |
| View consolidated business | Fabric data read with freshness and provenance |
| Handle incident and credit | Authorized function, audit, idempotency, and ERP A/B integration |
| Follow replay/live race | Rayfin consumption of temporal data through a qualified route with visible limits |

The result is not accepted just because the frontend compiles or works in Vite. It must run from its deployed Rayfin hosting and demonstrate the full flow.

Start with the most uncertain source and one vertical journey before deploying many artifacts. BPS and Fabric Apps remain subject to real tenant availability. Explicit and labeled fallback only; never silently replace native integration with files while claiming CDC or real SAP.

## Executable deliveries and todos

| ID | Delivery | Issue | Dependencies | Output and gate to advance |
| --- | --- | --- | --- | --- |
| P0 | Preparation and execution agreements | [#3](https://github.com/frdeange/FabricF1Demo/issues/3) | Plan approval | Agreed GitHub repository, reviewed instructions, roadmap and package issues in English, proposed/reviewed labels for approval, and default branch identified; DEV/DEMO destinations, identities, and budget approved before spending |
| PC | CI/CD foundation | [#8](https://github.com/frdeange/FabricF1Demo/issues/8) | P0 | Branch/PR CI and Actions workflows for provision/deployment, support matrix, unattended auth, and environment configuration; repeatable minimal deployment from a runner |
| P1 | Contracts and scenarios | [#5](https://github.com/frdeange/FabricF1Demo/issues/5) | P0 | Models, states, master data, and data manifest; four journeys described with verifiable inputs and outputs |
| P2 | Deployed Rayfin feasibility | [#9](https://github.com/frdeange/FabricF1Demo/issues/9) | PC, P1 | Two minimal items deployed from GitHub Actions, SSO/permissions, a single order visible across apps, Fabric read, and temporal consumption proven in browser; allowed version/path recorded |
| P3 | Oracle and Salesforce sources | [#2](https://github.com/frdeange/FabricF1Demo/issues/2) | P1, P2 | Real sources seeded, mappings and deltas qualified; Oracle insert/update/delete and supported CRM deletion/inactivation handling verified |
| P4 | SAP Plan B | [#6](https://github.com/frdeange/FabricF1Demo/issues/6) | P1, P2 | Native input/processing pilot, then scenario documents/controls; no claim of a connected ERP |
| P5 | History, replay, and live contract | [#7](https://github.com/frdeange/FabricF1Demo/issues/7) | P1, P2; rights and dataset before using sports data | Authorized race prepared, restartable temporal emitter, and live adapter; real live validation remains pending until a live session is enabled |
| P6 | Cross-source Fabric model | [#4](https://github.com/frdeange/FabricF1Demo/issues/4) | P3, P4 | Raw/Silver/Gold, quarantine, reconciliation, audience projections, and identified publication; integrate P5 once qualified |
| P7 | Fan portal | [#10](https://github.com/frdeange/FabricF1Demo/issues/10) | P2, P6; P5 for race | Catalog, own purchases/access, comparisons, replay/live, and support over real services |
| P8 | Promoter Hub | [#14](https://github.com/frdeange/FabricF1Demo/issues/14) | P2, P6 | Six areas and connected actions, graph with published relationships; add telemetry when P5 is available |
| P9 | Ontology and read agent | [#11](https://github.com/frdeange/FabricF1Demo/issues/11) | P6; native capability and functions enabled | Test sources and permissions; integrate into Hub without inferring unauthorized answers or actions |
| PA | SAP Plan A adapter | [#15](https://github.com/frdeange/FabricF1Demo/issues/15) | P1, P2 and SAP environment/license available | Real processes via supported API, qualified ingestion, reconciliation, and reconstruction; switch A/B without rebuilding frontends |
| P10 | Integration and reconstruction | [#13](https://github.com/frdeange/FabricF1Demo/issues/13) | P7, P8; P9 if enabled; live needed to accept live | Four complete journeys, no leaks/duplicates, measured performance, rebuild from Actions and a known Git revision; DEV/DEMO promotion rehearsed and evidenced |
| P11 | Review and delivery | [#12](https://github.com/frdeange/FabricF1Demo/issues/12) | P10 | Independent review, verified fixes, user review package, and mandatory pause before PR |

P3/P4/P5 can be split by contracts after P2. P7 and P8 are independent from each other once their dependencies are published. Do not wait for PA to deliver B. Do not mark requested live as complete if only replay was tested. P9 is conditional: if not enabled, record the limitation and agree scope instead of presenting a simulated assistant as a native agent. Do not parallelize heavy Spark/BPS work without checking capacity headroom.

## GitHub and CI/CD as part of the architecture

### Source of truth and environments

- One GitHub repository for code, contracts, Fabric definitions, IaC, migrations, secret-free configuration, workflows, and runbooks. P0 agrees owner/name and visibility, or reuses an existing repository. Do not run on a folder without Git.
- GitHub Flow, protected default branch, reviews, and required checks according to the available GitHub plan; no permanent dev/test/prod branches by default.
- Proposed two isolated DEV and DEMO destinations, each with its two apps and Fabric artifacts; they may share existing capacity if the budget and limits allow it. Do not treat DEMO as production for real consumers.
- GitHub Environments dev/demo separate bindings, secrets, and approvals. Confirm real support for reviewers/protections; if unavailable, use an explicit equivalent manual gate, not a fake protection.
- Each release identifies commit SHA, locked versions, artifact hashes, resource manifest, ID mappings, and dataset version. Promote only the revision that was already tested, never the latest floating HEAD.

### Which tool governs each surface

| Surface | Initial proposed tool | Boundary and condition |
| --- | --- | --- |
| Azure: required Oracle/gateway/worker/storage/network | Bicep and Azure CLI from Actions, with preview/what-if | Do not mix in Terraform by default; resources and roles require approval and visible cost |
| Fabric workspaces and connections | Manifests and supported REST/CLI, idempotent | Separate privileged bootstrap from routine deployment; check SP support per operation |
| Supported Fabric definitions | fabric-cicd with fixed version and explicit scope | Validate type and properties; deploy dependencies and verify rebinding, not copy DEV IDs |
| Rayfin apps and own models | Versioned Rayfin CLI from Actions | Full deployment supported per app/environment, including its functions through the documented route; do not hand its children to another deployer |
| DDL and serving contracts not managed by Rayfin | Versioned migrations/scripts by endpoint | Do not use Git sync as a data migration mechanism; changes must remain compatible and reconciled |
| Oracle and Salesforce metadata/seed; SAP scenarios | Official tools and idempotent scripts in separate jobs | Seed does not run on every deploy and does not reset live data; credentials are managed securely |
| BPS, permissions, secrets, and non-exportable bindings | Supported public API; manual bootstrap documented if none exists | Do not assume publishing definitions reproduces private connections/OAuth/metadata |

Current fabric-cicd documentation lists Lakehouse, Notebook, DataPipeline, Warehouse, Eventhouse/Eventstream, MirroredDatabase, Ontology, DataAgent, and other types; it does not list Rayfin AppBackend or the BPS launcher as supported types. Therefore fabric-cicd is not presented as a universal deployer.

Its publishes are full-scope, not based only on a Git diff: choose item-specific directories/types and exclude children managed by Rayfin/BPS. Do not run unpublish_all_orphan_items as automatic cleanup. PC records by type/operation and version: export/create/update, supported identity, dependencies, connections, rebinding, manual steps, and reconstruction test. The documentation list does not replace a test in this tenant.

The Rayfin 1.36.2 guide documents non-interactive SP login and pre-acquired token RAYFIN_TOKEN, as well as explicit workspace destinations. Federated authentication will be tested in PC/P2 before promising end-to-end support. Never allow a runner without a destination to create a workspace/trial by default.

Native AppBackend promotion is documented for compiled artifacts, but in that version it excludes functions and secrets. Do not use it as a shortcut that makes the whole app appear promoted. Recommended start: Actions and full CLI by environment from the same locked revision, recording the resulting artifacts. Do not claim binary identity between builds per environment if the CLI rebuilds. Resolve auth configuration and coordinates at runtime through the documented path to avoid DEMO consulting or authenticating against DEV.

### Fabric Git integration is not the universal deployer

GitHub Actions can deploy fabric-cicd from a checkout without connecting every workspace to Git or requiring a provider PAT for that reason.

Use native Git integration where it adds value for compatible item authorship, for example in a separate workspace/branch of authorship; export its changes to the working branch and review them, never writing directly to protected main.

One writer per artifact and destination: do not apply updateFromGit, fabric-cicd, and manual changes concurrently to the same items in the same workspace.

In a native Git flow, validate tenant switches, configured GitHub credential, current head, LRO, and final state without diffs. That Git credential is not the Azure/Fabric OIDC token. If needed, provision it with explicit permission, minimum scope, and rotation; do not promise a native GitHub connection without credentials.

### Planned workflows

| Workflow | Trigger and output |
| --- | --- |
| ci.yml | Branch push and PR: reproducible install/locks, lint, typecheck, tests, builds, contracts, definition/workflow validation; no cloud credentials or deployment from untrusted code |
| provision.yml | Approved workflow_dispatch: preview IaC, bootstrap of authorized resources/identity/connections, and readback; not on every push |
| deploy.yml | Reusable: exact revision + environment, preflight, definitions/DDL in order, both apps, bindings, health and smoke tests; authorized merge to default deploys DEV |
| preview.yml | Authorized manual execution of a trusted branch/SHA into DEV for review before creating PR, with URL and screenshots |
| promote-demo.yml | Protected execution after validating the same revision in DEV; GitHub Environment approval before modifying DEMO |
| seed-demo.yml | Manual, explicit scenario and environment; idempotent fictional data, manifest, and reconciliation; no implicit charges or deletions |
| verify.yml | Read-only: app health, permissions, sources/freshness, schema, and drift; reports without secrets |

The split can be implemented with reusable workflows to avoid duplicating steps. Do not create all of them as empty skeletons: PC delivers CI and minimal deploy; the others appear when their real capability exists.

Do not make the user’s pre-PR review depend on a pull_request workflow: the authorized branch preview lets the gate be satisfied before opening a PR. No workflow merges PRs automatically or skips user approval.

### Pipeline identity, state, and reliability

- Prefer GitHub OIDC -> Entra identity with federated trust scoped to repository/environment, without persistent SP secrets for Azure/Fabric when the APIs support it. fabric-cicd receives an explicit TokenCredential; do not depend on interactive defaults.
- Creating/authorizing identities, trust, and roles requires separately approved bootstrap. Apply least privilege, separate DEV/DEMO deployment and role management, and do not give Owner to every job.
- Prove that the owner/identity of each app after CI deployment still keeps the expected external access model in its functions. A correct SP login does not prove a caller can invoke the app or that the runtime token has SQL permission.
- No personal login caches or browser sessions copied into the runner. If a preview API needs user login, record the manual bootstrap and block; do not simulate unattended CI with developer credentials.
- No-secret variables by environment; secrets in approved Environments/Key Vault. Parameterize definitions with parameter.yml and Variable Library where supported. Do not assume Variable Library configures Rayfin runtime automatically.
- Pin actions by SHA and dependencies by lock; minimum permissions. Give id-token: write only to the authorized job; do not run fork PRs with secrets or use pull_request_target to execute their code with privileges.
- Serialize deployments by environment/workspace with concurrency; do not cancel a schema application halfway. Check active jobs before touching their items. LRO, transient retries with limits, and explicit errors; do not continue after failures.
- Use hosted runners for CI/control plane when enough. For private sources, use approved execution inside the network or an isolated ephemeral runner; do not open a public firewall so a job can seed Oracle/SAP.
- Git versions definitions, not tables, tokens, consents, or licenses. Store permitted data in storage with a manifest; do not bundle it in the SPA package.
- Schema changes should be compatible by expansion/contraction. Roll back code and definitions from a known release; data/schema need their own plan. No --force, no drop, no orphan cleanup, and no scenario reset by default.
- Each job publishes SHA/version, non-sensitive identifiers, URLs, deployment state, and sanitized results. Never upload .env, caches, tokens, or secret logs.

### CI/CD acceptance

From a clean runner and without a personal session, apply the approved revision in DEV, show both apps, and run the journey smoke test; repeat the deploy without duplicating items, resetting data, or changing target. Verify that DEMO does not reference DEV endpoints/IDs. Rehearse promotion and code recovery with compatible migrations. A manual modification in the destination must be detected as drift and resolved deliberately, not overwritten silently.

Technical smoke under SP does not replace isolation tests with real Entra users. Validate those in the browser with authorized sessions, without bringing personal caches into the runner. Where there is no export/readback for a definition, declare the drift-detection limit and test only the accessible properties.

### Proposed code structure

In the agreed repository, not in this non-Git folder by default:

- apps\\hub and apps\\fan: independent Rayfin projects, both from blankapp.
- packages\\contracts: shared types and validations, with no visual dependencies.
- sources\\oracle, sources\\salesforce, sources\\sap, and sources\\sports.
- fabric: ingestion, processing, projections, and native definitions.
- infra and scripts: provisioning, preflight, and idempotent reconstruction.
- .github\\workflows: CI/CD and reusable workflows; .github\\CODEOWNERS and protections when the repository/plan allows them.
- deploy: per-environment manifests, ownership inventory, parameterization, and orchestration; sensitive real values stay out of the repository.
- tests and docs: tests and directly related operations.
- AGENTS.md and docs\\engineering\\agent-playbook.md: agent instructions and briefs in English, adapted to repository conventions; reusable roles and limits, not a new agent per file.

The organization adapts to the chosen repository conventions. Do not create a component library or a microservices layer by default. Do not include local reference files or internal documents in commits or publications.

## Sustainability and proposed acceptance

- One order, one simulated payment result, one set of accesses, and one idempotent receipt after repeating the same request; no duplicates from retry.
- Fan A cannot access Fan B’s orders/cases/accesses or internal commands, even when directly calling APIs. Test backend and browser denial.
- Switching SAP A/B preserves contracts, does not mix publications, and does not alter UI journeys; each plan is validated separately against its source.
- Replay respects clock, pause/restart, and avoids spoilers; reordering, duplicates, gaps, and recovery from connection loss are tested with fixtures and permitted real events.
- Live qualifies in an authorized real session with observed latency; it is not declared delivered just because replay passed.
- Reconcile documents/lines, amounts by currency, credits, and included costs. Every metric identifies source/publication and distinguishes zero from not available.
- UI validation on desktop and mobile, keyboard, contrast, empty/loading/error states, and before/after captures from the real Rayfin render.
- UI, fictional scenario data, and shareable material must be consistently in English. Also review errors, empty states, captures, scripts, and GitHub content; translating the main navigation is not enough.
- Use builds, typecheck, lint, tests, and browser tests of the created projects; do not consider a build or a CLI query under admin identity sufficient.
- Declarative infrastructure, pinned versions, and secret-free configuration.
- Export Salesforce metadata and idempotent seed scripts with external keys.
- Preserve own data/SAP configuration and check expirations before demos.
- Rehearsed reconstruction, not merely documented; identify manual steps and licenses.
- Reproducible scenarios and permitted datasets cached for replay.
- Monitor freshness, rejections, duplicates, and quantity reconciliation.
- Laboratory start/stop with preflight and visible residual cost.
- Do not depend on repeatedly recreating trials or bypassing their terms.
- Separate connected experience from any replay/snapshot experience.
- Before spending, break down incremental cost of existing capacity, Oracle/gateway, storage, streaming/workers, SAP, and sports-data interface. Select SKU/schedules with real prices and quotas; do not budget everything as free.
- Measure load/freshness/CU with a minimal journey and set acceptance thresholds before scaling; there is not yet enough data to promise an SLA.

## Agent packages and model selection

No implementation agents have been launched. The current research is done directly; Auto selects the model for this conversation.

### Phase-specific agent roster

These are bounded role definitions, not a request to launch an agent for every row immediately. Reuse available specialist agents and skills; the coordinator owns decisions, dependencies, issue traceability, and acceptance, not duplicate implementation. All agent-produced deliverables and reports are in English.

| Phase / role | Runtime agent | Recommended model / effort | Assignment and acceptance evidence |
| --- | --- | --- | --- |
| P0 / Platform readiness | fabric-skills:FabricAdmin | gpt-5.4 / medium | Inventory approved capacity/workspaces, tenant prerequisites, access, and cost constraints; report readiness without granting permissions autonomously |
| P1 / Domain and contract architect | general-purpose | gpt-5.5 / high | Canonical keys, state machines, money/refund semantics, ownership, and four journeys; executable contracts and deterministic scenario manifest |
| PC / Release and CI/CD engineer | general-purpose | gpt-5.5 / high initially | Actions, OIDC, deployment ownership, environment isolation, and support matrix; repeatable unattended deployment from a clean runner |
| P2 / Rayfin identity and application architect | fabric-skills:FabricAppDev | gpt-5.5 / high | Two deployed Rayfin items, authorization, shared operational record, runtime identity, and Fabric reads; real browser and backend evidence |
| P3 / Oracle and Salesforce integration engineer | fabric-skills:FabricDataEngineer | gpt-5.5 / medium | Source schemas, idempotent fictional seeds, keys and ingestion/CDC; source-to-Fabric delta reconciliation, not direct Gold seeding |
| P4 / SAP scenario and integration engineer | fabric-skills:FabricDataEngineer | gpt-5.5 / medium | Plan B business documents, accounting invariants, and native ingestion pilot; provenance, reconciliation, and no claim of a connected ERP |
| PA / Real SAP adapter engineer | fabric-skills:FabricDataEngineer | gpt-5.5 / high initially | Authorized ERP interfaces and business processes, A/B contract parity, and reconstruction; start only after environment and rights are available |
| P5 / Racing data and streaming engineer | general-purpose | gpt-5.5 / medium | Authorized adapters, event/replay clocks, ordering, deduplication, and recovery; replay tests plus a real live session for live acceptance |
| P6 / Fabric analytics engineer | fabric-skills:FabricDataEngineer | gpt-5.5 / medium | Raw/Silver/Gold, quality, serving contracts, and financial reconciliation; cross-source totals and audience-specific projections |
| P7 / Fan experience engineer | fabric-skills:FabricAppDev | gpt-5.5 / medium | Complete English Rayfin fan UX against approved contracts: purchases, entitlements, racing, and support; accessibility and deployed journey evidence |
| P8 / Promoter hub engineer | fabric-skills:FabricAppDev | gpt-5.5 / medium | Six English Rayfin business areas and authorized operational commands; connected workflows, usable states, and rendered evidence, without rewriting ingestion |
| P9 / Ontology and grounded agent engineer | general-purpose | gpt-5.5 / medium | Native ontology/graph and read-only grounding using the owning skills; permissions, provenance, and no fabricated answers or autonomous writes |
| P10 / Integration and reliability engineer | general-purpose | gpt-5.5 / medium | Cross-app journeys, fault recovery, load/freshness, rebuild and promotion; measured evidence, explicit live limitations, and reproducible release |
| P11 / Independent reviewer | code-review | gpt-5.5 / high | Actual diff: correctness, regressions, security boundaries, scope, English deliverables, and repository rules; file-referenced findings and verification of fixes |

### Model selection and escalation

The models/efforts in the table are available in this session; they are recommendations, not actions already taken or agents already run.

The previous recommendation is revised: gpt-5.5 / medium is the baseline for substantial implementation packages, including both full apps, prioritizing capability and end-to-end coherence over the lowest possible cost. Do not assign a rich experience to a mini model by default.

High is reserved for contracts with monetary effects, identity boundaries, still-uncertain CI/CD bootstrap, unqualified real SAP, and independent review. After those risks are resolved, lower the same package to medium before continuing well-defined implementation. P0 uses gpt-5.4 / medium because inventory/readiness is less complex than designing the operational boundary.

The coordinator keeps the current Auto choice; if it delegates an unresolved architectural decision, the recommendation is gpt-5.5 / high, without claiming a change to the parent. For mechanical changes with closed acceptance checks, such as template adjustments, derived documentation, small fixtures, or repetitive tests, recommend gpt-5.4-mini / medium. Delegate with that explicit model only if the volume justifies an agent; direct simple actions do not need one. This lighter option does not decide authorization, transactions, architecture, or licensing.

Reassess at the end of planning and at each gate: do not automatically inherit the plan model/effort. Escalate gpt-5.5 from medium to high only for a concrete ambiguity or reproducible failure. Consider gpt-5.6-sol / high, also available, only if platform, identity, atomicity, or cross-cutting debugging problems persist after distinct attempts and documented evidence. Do not use xhigh/max or a larger model to reformat YAML or draft issues. If the approved model cannot be selected/delegated, communicate the limitation before implementing and give the exact selection; do not silently substitute it.

### Delegation and handoff contract

Each assignment has an issue and reference revision, bounded objective, inputs, frozen contracts, own files, dependencies, applicable skills, acceptance checks, model/effort, and stop condition. Its output in English includes changes, evidence, limitations, blockers, and the model/effort actually used. Do not ask the agent to make purchase, permission, or license decisions.

FabricAppDev receives the managed Rayfin constraint and the versioned documentation/skill corresponding to it; it does not replace that hosting with another stack. FabricDataEngineer uses the proprietary skills of each endpoint. The P9 specialist uses ontology/model-authoring skills, not a BI question-answer agent pretending to be an ontology author.

PC/P2 form a vertical pilot: they may share implementer and context so the same authentication is not investigated twice. Afterwards, P3/P4/P5 can move in parallel by contracts and with capacity awareness. P7/P8 can be split between two agents with separate files once P6 is available. P9 starts only when the native capability is qualified.

The coordinator integrates and verifies; it does not reassign the same investigation to another agent. P11 is independent of implementation. The reviewer lists verifiable findings or explicitly says that no problems were found; do not confuse a change summary with an independent review. Do not launch an agent per module, a full fleet, or massive workflows by default.

Before any PR: implement and validate, perform independent review, resolve findings, verify fixes with the reviewer, present diff/results and before/after UI previews/screenshots, and wait for explicit user approval. Plan approval does not satisfy that second checkpoint. Report the model/effort actually used and the coordinator’s validation.

## GitHub and pending blockers

The original project folder has no Git remote or default branch. The user authorized a public repository under `frdeange`; `frdeange/FabricF1Demo` now exists with default branch `main`. Work is isolated in a separate checkout and issue-linked branch. The parent roadmap and English package issues #2–#15 exist; no thematic labels were created (only existing generic labels were reused). The user authorized partner-shareable English project content, not internal reference documents. Concrete resource deployment remains subject to separate scope, permission, and budget gates. For UI, capture the real initial state when available and preserve evidence in the issue/PR with authorized durable URLs.

In P0, search for an existing issue for this deliverable and review labels. This repository started with no issues, templates, or fitting thematic labels. The parent roadmap issue #1 and package issues #2–#15 were created in English using the existing generic `documentation` and `enhancement` labels; no shared thematic labels were created without approval.

For this repository, the initial preparation is recorded in the roadmap and package issues before product implementation. Create a branch from the real default, with the issue number, and use Conventional Commits. Do not generate a PR until independent review and user approval of the result are complete; do not merge without explicit request.

For new UI, capture the real initial state after scaffold and before visual development; do not fabricate a screenshot of a previous nonexistent system.

### English GitHub issue and label traceability

Create or reuse one parent roadmap issue and one focused linked execution issue per meaningful package (P0, PC, P1-P11, and conditional PA), not per file or agent. The parent records the agreed scope, dependency graph, mandatory gates, and links. Execution issues include the goal, in/out of scope, dependencies, acceptance criteria, agent role, recommended model/effort, deployment impact, evidence, and external blockers. Record actual models and escalation in completion evidence. An issue is not complete because its agent returned; verify its acceptance first. Keep SAP rights and sports licensing blockers visible; do not close live delivery using replay evidence. Conditional work remains explicitly conditional.

Inspect existing repository labels before choosing a taxonomy. Reuse fitting labels; otherwise propose a small English thematic set covering platform, contracts, source integration, racing, fan experience, promoter hub, and validation. Include relevant emoji in the proposed thematic labels as required by the user’s workflow, and obtain explicit approval before creating or changing shared labels. Use native issue dependencies where supported; otherwise use explicit linked checklists. Do not require a separate project board or a paid feature for traceability.

The roadmap is not authorization to start every issue. Keep a single active deliverable per implementation conversation: before moving to a different issue, apply the user-level AGENTS.md scope checkpoint and recommend a new chat. A coordinated child for an already authorized package receives only its own scope and context; do not silently mix unrelated issues or publish source material. No additional issue is required merely for a review/fix within the active issue.

### Unresolved dependencies that must not be hidden

| Dependency | Consequence | Treatment in the plan |
| --- | --- | --- |
| Repository and publication scope | Public repository and roadmap/issues now exist; implementation is beginning | Preserve public-content boundaries; do not publish internal references |
| Workspace/region/quotas/budget and Rayfin enablement | No deployment has been qualified | Preflight and resource approval before spending/access changes |
| CI/CD by type and unattended authentication | Support documented partially, not qualified in tenant/runner | Gate PC/P2, per-operation matrix, OIDC where it works, and manual bootstrap declared where needed |
| Operational persistence between two items | No concrete path proven | Mandatory P2 gate; if it fails, resolve before P3-P8 |
| SAP Plan A source and test/demo rights | Cannot promise a real connected ERP | Advance through Plan B and prepare PA without pretending availability |
| Plan B BPS input and processing | Worked in the reference, not proven here | Pilot before scaling data or claiming native ingestion |
| Position/live licensing and coverage | No qualified provider for commercial use | P5; without permitted data, do not show or claim live delivery |
| Unvalidated local data | Schema, access rights, and coverage are not validated | Use only if legitimate access is obtained and legal/schema review succeeds; do not bypass access controls or assume coverage |
| Final catalog, amounts, and compensation rule | Affect states and generators | Decide in P1 before implementing them |

Approval of this plan does not authorize purchases, new subscriptions, permission changes, acceptance of terms, or publication of internal material. Each action requires the corresponding scope and authorization.

## Sources

- https://microsoft.github.io/fabric-cicd/latest/
- https://microsoft.github.io/fabric-cicd/latest/example/authentication/
- https://microsoft.github.io/fabric-cicd/latest/how_to/parameterization/
- https://learn.microsoft.com/fabric/cicd/cicd-overview
- https://learn.microsoft.com/fabric/fundamentals/understand-best-practices-fabric-cicd
- https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration
- https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect
- https://github.com/fredgis/FabricHubDemo
- https://github.com/fredgis/FabricHubDemo/blob/main/docs/ARCHITECTURE.md
- https://github.com/fredgis/FabricHubDemo/blob/main/docs/ORACLE.md
- https://github.com/fredgis/FabricHubDemo/blob/main/docs/SALESFORCE-BPS.md
- https://github.com/fredgis/FabricHubDemo/blob/main/sources/salesforce/Deploy-Crm.ps1
- https://github.com/fredgis/FabricHubDemo/blob/main/apps/cockpit/package-lock.json
- https://github.com/fredgis/FabricHubDemo/blob/main/apps/cockpit/rayfin/rayfin.yml
- https://github.com/fredgis/FabricHubDemo/blob/main/apps/cockpit/.agents/skills/rayfin/SKILL.md
- https://github.com/fredgis/FabricHubDemo/blob/main/apps/cockpit/.agents/skills/rayfin-functions/SKILL.md
- https://github.com/fredgis/FabricHubDemo/blob/main/apps/cockpit/.agents/skills/rayfin-connectors/SKILL.md
- https://ms-feed-25.pkgs.visualstudio.com/1es-public/_packaging/npm-public/npm/registry/@microsoft/rayfin-guide/-/rayfin-guide-1.36.2.tgz
  (includes app-backend/deploy.md, app-backend/deployment-pipelines.md, and
  cli/environment-variables.md: CI authentication and promotion limits).
- https://github.com/SAP-docs/abap-platform-trial-image/blob/main/README.md
- https://community.sap.com/t5/technology-blog-posts-by-sap/abap-cloud-developer-trial-2025-available-now/ba-p/14376009
- https://www.sap.com/products/erp/cloud-erp-private/trial.html
- https://pages.community.sap.com/topics/cloud-appliance-library/appliance-templates-faq/faq-trial-templates
- https://pages.community.sap.com/topics/cloud-appliance-library/appliance-templates-faq/faq-terms-conditions
- https://pages.community.sap.com/topics/cloud-appliance-library/appliance-templates-faq/faq-licenses
- https://cal.sap.com/
- https://www.sap.com/products/technology-platform/cloud-appliance-library.html
- https://www.sap.com/sea/products/erp/s4hana/trial.html
- https://www.sap.com/products/data-cloud/hana/express-trial.html
- https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/quickstart_dev_org.htm
- https://help.salesforce.com/s/articleView?id=Inactive-Salesforce-Developer-Edition-Orgs&language=en_US&type=1
- https://www.oracle.com/database/free/
- https://www.oracle.com/database/free/faq/
- https://learn.microsoft.com/en-us/fabric/fundamentals/fabric-trial
- https://docs.fastf1.dev/
- https://openf1.org/
- https://openf1.org/docs/

Public sources describe offers and policies; they do not prove this project’s access or eligibility/licenses. Confirm them during provisioning.
