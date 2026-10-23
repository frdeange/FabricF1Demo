# Salesforce Data 360 to Fabric OneLake: integration and reconstruction

[Documentation](../README.md) | [Runbooks](README.md) |
[Salesforce source](../../sources/salesforce/README.md)

Documentation package: [#33](https://github.com/frdeange/FabricF1Demo/issues/33).
Source ownership: [#20](https://github.com/frdeange/FabricF1Demo/issues/20);
downstream projections: [#4](https://github.com/frdeange/FabricF1Demo/issues/4).

This runbook preserves the procedure and findings from the project's live
Salesforce CRM -> Salesforce Data 360 -> Microsoft Fabric investigation.
Salesforce screens may still say **Data Cloud**; Fabric labels the shortcut
source **Salesforce Data360**. These names refer to the surfaces used below,
not to a promise that every Salesforce edition enables them.

The qualified path uses an **Organizational account in Microsoft Entra**,
an outbound Salesforce **Data Share Target**, a **Data Share** containing
explicitly selected Data Lake Objects, and native table shortcuts inside
an existing schema of a schema-enabled Fabric Lakehouse.

**Critical finding:** for the Organizational-account connection tested here,
the Salesforce target's **Service Account ID** worked when populated with the
**Entra user Object ID of the account authenticating the Fabric connection**.
It was not the Salesforce user ID, SAML application's client ID, or an
arbitrarily created service principal. This is an empirical result for this
authentication mode, not a universal definition for every connector mode.

## Contents

- [1. Scope and evidence boundary](#1-scope-and-evidence-boundary)
- [2. Architecture and authentication boundaries](#2-architecture-and-authentication-boundaries)
- [3. Prerequisites and approval gates](#3-prerequisites-and-approval-gates)
- [4. Configuration worksheet](#4-configuration-worksheet)
- [5. Prepare and reconcile Salesforce CRM](#5-prepare-and-reconcile-salesforce-crm)
- [6. Ingest CRM objects into Data 360](#6-ingest-crm-objects-into-data-360)
- [7. Configure the OneLake Data Share Target](#7-configure-the-onelake-data-share-target)
- [8. Create and link the outbound Data Share](#8-create-and-link-the-outbound-data-share)
- [9. Create the Fabric connection and table shortcuts](#9-create-the-fabric-connection-and-table-shortcuts)
- [10. Verify the complete data path](#10-verify-the-complete-data-path)
- [11. Optional Salesforce web SSO](#11-optional-salesforce-web-sso)
- [12. Troubleshooting and investigation findings](#12-troubleshooting-and-investigation-findings)
- [13. Operations, governance and cost](#13-operations-governance-and-cost)
- [14. Rollback and reconstruction](#14-rollback-and-reconstruction)
- [15. Evidence and handoff checklist](#15-evidence-and-handoff-checklist)
- [16. References and documentation traps](#16-references-and-documentation-traps)

## 1. Scope and evidence boundary

### What has been demonstrated

The investigation established all of these as distinct milestones:

1. Nine synthetic CRM objects were reconciled in Salesforce CRM.
2. Their Data 360 data streams became active and reported successful ingestion.
3. An active Microsoft OneLake outbound target was configured.
4. The Fabric connector's previous HTTP 401 changed to HTTP 200 after the
   Organizational-account user identity was bound in that target.
5. An empty successful listing was explained by the absence of linked shares,
   not by a need for another login.
6. A Data Share containing exactly nine selected DLOs was created and linked.
7. Fabric discovered that share and its nine DLO directories.
8. Nine shortcuts were created within `Tables/dbo`, preserving the DLO names.
9. Actual Fabric table previews were checked, separately from successful
   metadata listing and shortcut creation. See the evidence table below.

The successfully tested environment used a Developer Edition Salesforce org
with the required Data 360 and OneLake-sharing feature available, plus an
existing small Fabric capacity and schema-enabled Lakehouse. This does **not**
establish universal free access, a production entitlement, minimum SKU
requirements, or acceptable performance for a different tenant or workload.

### What has not been qualified

- A clean-environment, unattended reconstruction.
- Salesforce service-principal authentication in the Fabric connector.
- A minimum-privilege Salesforce permission-set recipe.
- Automatic credential renewal, identity replacement or offboarding behavior.
- Production SLA, throughput, refresh latency, concurrency or capacity sizing.
- Full deletion/update propagation semantics across the entire path.
- SQL analytics endpoint, Direct Lake, semantic model or app consumption merely
  because a Lakehouse preview works.
- Cross-tenant scenarios, every Salesforce data space or arbitrary DMO sharing.

This is operational documentation, not an exported Salesforce metadata package,
an infrastructure module, a seed adapter, or authorization to deploy anything.
No Oracle/SAP configuration or Silver/Gold processing is part of this procedure.
The separate Oracle mirrored database must remain untouched by this runbook.

## 2. Architecture and authentication boundaries

### Direction of data access

```text
Synthetic fixture and approved Salesforce-native mapping
    |
    v
Salesforce CRM standard/custom objects
    |
    | Salesforce CRM connector and Data 360 data streams
    v
Data 360 Data Lake Objects (DLOs)
    |
    | Explicit outbound Data Share
    | Linked Microsoft OneLake Data Share Target
    v
Fabric Salesforce Data360 connection
    |
    | Microsoft Entra Organizational-account authentication
    v
Fabric Lakehouse / Tables / dbo / <DLO-name>  [native shortcuts]
    |
    v
Read verification, then separately owned downstream projections
```

The target/share authorizes exposure of the Salesforce data. The shortcut is
created in Fabric and accesses that shared data. The target is not an
instruction to build a reverse-direction Salesforce ingestion connection
that reads an existing Fabric table.

### Three independent identity concerns

| Boundary | Purpose | What success does not prove |
| --- | --- | --- |
| Salesforce CRM -> Data 360 connection | Authorizes ingestion of CRM objects into DLOs | DLOs are not automatically shared with Fabric |
| Entra -> Salesforce SAML web SSO | Lets a person enter Salesforce through Entra | Does not authorize the Fabric connector's data access |
| Fabric connection -> Data 360 outbound target/share | Authenticates the reader and exposes selected DLOs | Does not create shortcuts or prove data reads succeed |

The Fabric Organizational-account sign-in opens Microsoft Entra. It is not
expected to open the Salesforce username/password page. Matching email strings
or completing Salesforce SSO is not a substitute for configuring the target
with the correct reader identity and linking a share.

### Vocabulary

| Term | Meaning in this procedure |
| --- | --- |
| CRM object | Source standard/custom Salesforce object, such as Account or F1Consent__c |
| Data stream | Data 360 ingestion configuration and execution state |
| DLO | Data Lake Object containing ingested source records |
| DMO | Data Model Object used by Data 360 modeling; not required for this tested DLO-only share |
| Data Share | Named outbound collection of explicitly selected objects |
| Data Share Target | Receiving identity/platform configuration linked to a share |
| Fabric connection | Saved endpoint, source tenant setting and authentication binding |
| Shortcut | OneLake reference to the shared source; not a separately seeded Bronze table |
| Schema | Container such as dbo in a schema-enabled Lakehouse |

## 3. Prerequisites and approval gates

### Salesforce side

Before opening a sharing wizard, qualify and record:

| Requirement | Required evidence |
| --- | --- |
| Authorized org | Approved org/edition, owner, allowed synthetic data use and recovery route |
| Data 360 access | Data Cloud/Data 360 application opens with the intended operator |
| CRM connection | Approved Salesforce CRM source connection is present and can enumerate the required objects |
| API and storage | Current edition entitlements, quotas, limits, retention and inactivity terms are checked |
| Source schema/data | Required objects and fields exist; fixture totals and reference keys reconcile |
| Ingestion rights | Operator can inspect, deploy/activate and refresh the scoped data streams |
| Sharing rights | Operator can create Data Shares/Targets and link them |
| OneLake feature | Microsoft OneLake is available as an outbound target type |
| Cost approval | Initial ingestion, ongoing refresh and any sharing/query credits are approved |
| Data-use approval | Exact objects/fields and receiving readers are approved before publishing |

The qualified org exposed a **Data Share for OneLake** feature under
Setup -> Beta Features. The user enabled it during the investigation.
Availability, naming, terms and licensing may change. If it is absent, obtain
confirmation from the org owner/Salesforce; do not assume a generic trial has it.
Enabling a beta or accepting terms is a separate approval, not an incidental
step that an operator or agent should silently perform.

The tested operator had broad pre-existing administrator/Data Cloud access.
Those rights were sufficient, but are not proven minimum requirements.
Do not grant a new broad role just because a control is missing.

### Microsoft side

| Requirement | Required evidence |
| --- | --- |
| Entra tenant | Correct receiving tenant and approved reader account are known |
| Reader identity | Exact account authenticating the Fabric saved connection is identified |
| Object ID | That account's Entra user Object ID is read from the correct directory |
| Fabric access | Operator can open the intended workspace and create shortcuts in its Lakehouse |
| Capacity | Existing compatible, running capacity with approved budget is assigned to the workspace |
| Lakehouse | Correct item exists; schema mode and destination schema are checked |
| Connector | Salesforce Data360 source is visible in the New shortcut dialog |
| Region | Destination region and cross-region processing consequences are approved |
| Authentication | Organizational-account sign-in succeeds under applicable tenant policies |
| Recovery | Scope of shortcut removal and share revocation is agreed in advance |

The existing project environment used a small Fabric capacity in its approved region.
No larger capacity, VM, gateway, pipeline or Spark notebook was needed to
establish this native shortcut path. That observation is not a sizing guarantee
or a claim that queries have no compute/credit cost.

### Stop conditions

Stop before mutation if the target org/workspace, account, data scope,
region/budget or rollback is unclear. Also stop if a step requires:

- A new identity, application, secret, role grant or admin consent.
- Sharing unrelated objects, broad org data or real personal records.
- Replacing an existing connection or share used by another workload.
- A full refresh/rebuild instead of the approved incremental operation.
- Deleting source records, DLOs, a Lakehouse or another package's resources.

Do not treat HTTP 401/403 as permission to expand access.

## 4. Configuration worksheet

Keep real bindings in an approved private operational record, not this public
repository, issue comments, screenshots or example scripts.

| Placeholder | Meaning and acquisition | Not interchangeable with |
| --- | --- | --- |
| `<salesforce-crm-origin>` | Approved Salesforce CRM/My Domain origin | Data 360 instance endpoint |
| `<salesforce-org-id>` | Org identifier from Salesforce; may have 15/18-character forms | Entra tenant ID |
| `<data360-primary-tenant-id>` | Exact primary tenant value shown by Salesforce's OneLake target UI | Bare Salesforce org ID |
| `<data360-instance-url>` | Exact Data 360 endpoint shown by that UI | Lightning origin, setup origin or region label |
| `<entra-tenant-id>` | Receiving Microsoft Entra directory GUID | Azure subscription ID |
| `<reader-upn>` | Approved Organizational-account sign-in name | Object ID or Salesforce username |
| `<reader-user-object-id>` | Object ID of that Entra user in the receiving tenant | Application/client ID or service principal Object ID |
| `<workspace-id>` | Approved Fabric destination workspace ID | Capacity ID |
| `<lakehouse-id>` | Existing Bronze Lakehouse item ID | SQL analytics endpoint ID |
| `<connection-name>` | Descriptive saved Fabric connection name | A different connection merely selected by default |
| `<target-api-name>` | Salesforce Data Share Target API name | Data Share API name |
| `<share-api-name>` | Salesforce Data Share API name exposed in Fabric | Its human-readable label |
| `<destination-schema>` | Existing schema, dbo in the qualified run | Tables root |

The primary tenant value observed in the successful connection had the form
`core/prod/<salesforce-org-id>`. Copy the actual value displayed by Salesforce;
do not synthesize it from an org ID or assume the prefix is universal.
The successful Fabric connection used this **full primary tenant value**.
An earlier bare-org-ID connection failed, but the target was missing then;
the experiment did not isolate bare versus full ID with an otherwise identical
working target. Therefore, use the known-working full value without claiming
that every bare org ID must fail.

### Read the Entra user Object ID

In the Entra portal, use the intended directory -> Users -> exact reader
account -> Object ID. Verify the tenant as well as the sign-in name.

If an already authenticated, authorized Azure CLI session is available,
this is a read-only alternative:

```powershell
az account show --query '{tenantId:tenantId}' --output json --only-show-errors
az ad user show --id "<reader-upn>" `
  --query '{id:id,userPrincipalName:userPrincipalName}' `
  --output json --only-show-errors
```

The `id` returned by `az ad user show` is the candidate user Object ID.
The first command reports the CLI account context; it is a sanity check, not
proof that the Fabric browser signed in to that same account. Verify both.
If the lookup is denied, ask an authorized directory operator for the value;
do not request directory-wide permissions merely to bypass the lookup failure.

Do not create an application registration to obtain a convenient GUID.
An app/client ID, enterprise application's Object ID, Salesforce user ID,
SAML Federation ID and user Object ID describe different identities.

## 5. Prepare and reconcile Salesforce CRM

This runbook starts from authorized CRM schema and source data. It does not
reconstruct the custom objects or seed all records from scratch.
The source package owns that implementation; the logical
[canonical contracts](../canonical-business-data-contracts.md) and generated
fixture alone are not a Salesforce metadata deployment.

Use stable external IDs and the canonical crosswalk. Do not join by email or
display name. Keep consent separate from purchase and opportunity state.
Use synthetic data only; preserve provenance and fixture/run identifiers.

### Qualified source and DLO inventory

These are the project's observed names and fixture totals. They are examples
to reconcile against a chosen fixture version, not platform-mandated counts.
Another CRM connection may produce a different suffix than `_Home`.

| CRM object | Data 360 DLO API name | Expected fixture rows |
| --- | --- | ---: |
| Account | Account_Home__dll | 438 |
| Contact | Contact_Home__dll | 514 |
| Campaign | Campaign_Home__dll | 12 |
| Opportunity | Opportunity_Home__dll | 288 |
| Case | Case_Home__dll | 40 |
| F1Consent__c | F1Consent_c_Home__dll | 400 |
| F1CampaignTouch__c | F1CampaignTouch_c_Home__dll | 372 |
| F1SponsorshipAgreement__c | F1SponsorshipAgreement_c_Home__dll | 12 |
| F1SponsorshipCommitment__c | F1SponsorshipCommitment_c_Home__dll | 12 |
| **Total** | **Nine explicitly scoped DLOs** | **2,088** |

Custom source names and generated DLO names are not identical:
`F1Consent__c` became `F1Consent_c_Home__dll`. Select by the actual DLO API name
and object type, not by a loosely matching label or an unrelated standard DMO.

## 6. Ingest CRM objects into Data 360

### 6.1 Inventory first

In the Data Cloud application, open **Data Streams**.
Spanish labels observed: **Transmisiones de datos**.
Select the complete **All Data Streams** view and clear any search/filter.

**Recently Viewed = 0 is not an empty inventory.** The org already had
preconfigured streams and DLOs that were absent from Recent views.
Inspect existing streams by source object and connection before creating more.

For each of the nine scoped objects, record:

- Source connector and exact source object.
- Stream name, state and most recent execution.
- DLO API name, category, primary key and event timestamp if applicable.
- Total records, not just records processed in the last run.
- Refresh mode, full-refresh schedule and filters.

Do not activate every preconfigured stream. Only the nine objects in the
approved scope are needed for this path.

### 6.2 Reuse suitable existing streams

Account, Contact and Campaign already had streams in the qualified org.
They were initially inactive/unrun. After approval:

1. Open the individual stream.
2. Activate it using a confirmation whose action and target are consistent.
3. Request the approved incremental refresh once.
4. Wait for the execution to reach a terminal successful state.
5. Reconcile the total records with CRM.

The bulk activation dialog once had an activation title but deletion wording.
It was canceled. Individual activation dialogs were used instead.
Never confirm contradictory/destructive wording just because another part
of a modal appears benign.

### 6.3 Create only missing streams

For a missing scoped object:

1. Choose **New Data Stream -> Salesforce CRM**.
2. Select the approved existing CRM connection, verifying its actual org.
3. Locate the required standard/custom objects.
4. Recheck the final selection after using search filters.
5. Preserve required source fields; the qualified run used the wizard's
   default selected source fields.
6. Set the category/key/timestamp and refresh options deliberately.
7. Review the destination data space and filters.
8. Deploy once; verify the deployment result and resulting stream state.

The observed configuration for the six newly created streams was:

| Source | Category | Key/time treatment |
| --- | --- | --- |
| Case | Other | Default source Case ID |
| Opportunity | Other | Default source Opportunity ID |
| F1Consent__c | Other | Default source Record ID |
| F1SponsorshipAgreement__c | Other | Default source Record ID |
| F1SponsorshipCommitment__c | Other | Default source Record ID |
| F1CampaignTouch__c | Engagement | Default Record ID; event time `OccurredAt_c` |

Spanish category labels: **Otros**, **Implicación**.
`OccurredAt_c` is the event time selected in the Data 360 wizard; do not
substitute CreatedDate just to satisfy the field requirement.
Confirm the exact selectable field name in a newly reconstructed org.

For those six streams, the qualified run selected:

- Data space: `default`.
- Refresh mode: upsert (Spanish UI: **Alterar**).
- Full-refresh interval: None (**Ninguno**).
- Filters: none.
- One approved incremental refresh per stream after provisioning.

The newly deployed streams became active automatically in that run.
Some controls remained unavailable while provisioning; wait rather than
repeatedly deploying or submitting refreshes.

### 6.4 Reconcile ingestion

Wait until all scoped streams are active and their latest execution is
successful. Compare **Total Records** with the fixture totals.
The latest-processed metric sometimes showed N+1 while the total showed N;
the investigation used total records for reconciliation.

An initial execution history displayed full replacement even though the
operator requested incremental refresh. Record the operation requested and
the platform's actual initial-load behavior separately. Do not describe an
initial incremental request as proof of incremental-only storage behavior.

No new DMO mappings were required for this tested DLO-only outbound path.
Successful ingestion alone is still **not** successful Fabric integration.

## 7. Configure the OneLake Data Share Target

### 7.1 Find the correct outbound surface

Open Data Cloud -> **Data Share Targets**.
Spanish: **Destinos de colaboraciones de datos**.
The navigation item may be under **Show more navigation items**
(**Mostrar más elementos de navegación**).

Salesforce object route used by the UI:
`/lightning/o/ExtDataShareTarget/home`.
The similarly guessed `DataShareTarget` route was wrong and produced an
access-looking error. A nonexistent/wrong route is not evidence that a role
grant is required.

Use **All Data Share Targets**, not Recently Viewed, to identify existing
targets. Reuse only a target whose platform, tenant, reader and ownership
match the approved scope. Do not overwrite an unrelated target.

### 7.2 Create the scoped target

Choose New -> **Microsoft OneLake**.
The options load asynchronously. An early snapshot showed Snowflake and
Databricks only; OneLake appeared after loading/scrolling.
Wait and inspect the complete list before diagnosing entitlement failure.

Populate:

| Field | Value |
| --- | --- |
| Label | Descriptive English label, e.g. `F1 OneLake reader` |
| API Name | Unique Salesforce-compatible API name |
| Azure Tenant ID | `<entra-tenant-id>` |
| Service Account ID | `<reader-user-object-id>` for the tested Organizational-account mode |

The successful investigation retained the exploratory label
`F1 OneLake identity test`. A future reconstruction can choose a clearer
operational label; the name itself did not solve authentication.
Do not rename a live target or alter its identity as an unapproved cleanup.

Record the Data 360 primary tenant ID and instance endpoint shown by the
OneLake target wizard in the private worksheet. Those are the source values
to use in the Fabric connection.

No client secret, Fabric workspace ID or Lakehouse ID was requested by this
outbound target form. Do not add reverse-direction federation requirements
to fill a gap in this form.

Save only after identity/access approval. Then read back the saved record:

- Platform is Microsoft OneLake.
- State is Active.
- Tenant and Service Account ID exactly match the approved values.
- Related shares are visible, even if initially zero.

### 7.3 Interpret the identity test correctly

With the target present and the reader's user Object ID configured, the
existing full-tenant Organizational-account connection changed from:

```text
Subject and Issuer in the token does not match with target (HTTP 401)
```

to a successful HTTP 200 listing.

At that point the listing was empty because no Data Share was linked.
This proved a useful authentication/authorization milestone, not data
availability or completion. Do not keep changing passwords, SSO claims,
app registrations or permissions once identity works and the next missing
layer is an unlinked share.

## 8. Create and link the outbound Data Share

### 8.1 Inventory and create

Open **Data Shares** (**Colaboraciones de datos**), not Data Share Targets.
The observed Salesforce object route was
`/lightning/o/ExtDataShare/home`.
Use **All Data Shares** and inspect candidates before creating duplicates.

Choose New -> create from scratch, then enter:

- Label: `F1 Demo Salesforce Bronze` in the qualified run.
- API name: `F1_Demo_Salesforce_Bronze`.
- Data space: the same one containing the scoped DLOs (`default` here).
- Description explaining the synthetic source scope and Bronze destination.

Salesforce requires acknowledgment that administrators/privileged users in
the receiving organization may view/query the records exposed by the share,
including underlying DLO records when DMOs are shared.
Obtain explicit data-sharing approval before accepting this acknowledgment.

### 8.2 Select exactly the approved DLOs

On the object-selection screen, choose **Data Lake Objects**
(**Objetos de lago de datos**).
Select exactly the nine DLO API names in the inventory table.
Do not use Select All: the org contains unrelated preconfigured DLOs/DMOs.

Check both name and **Data Lake Object** type. For example, a standard
Account DMO is not the source `Account_Home__dll`.

Save, then verify:

- Share is Active and Outbound.
- Object count is 9.
- The saved object list matches all nine approved names.
- No unrelated object was selected through a retained search/filter state.

### 8.3 Link the target explicitly

On the Data Share record, select **Link/Unlink Data Share Target**
(**Vincular/Desvincular destino de colaboración de datos**).
Select the approved Microsoft OneLake target and save.

Allow the UI/backend to finish updating, then read the Data Share's
**Data Share Targets** tab again. Verify one linked target, the expected
name and an Active link state. Reopening the selection dialog should show
that target selected; cancel without changes if using it only as a readback.

Creating a target and creating a share are not enough: the explicit link
is necessary. The target's Related Shares tab also provides an independent
way to check this relationship.

## 9. Create the Fabric connection and table shortcuts

### 9.1 Select the destination schema before the wizard

Open the approved schema-enabled Bronze Lakehouse.
Expand **Tables -> dbo** (or the approved existing schema).
Use that schema's context menu -> **New table shortcut**.

**Do not start from the generic Tables-root shortcut entry point for this
table-by-table selection.** In the investigation, root-level DLO shortcuts
were interpreted as schemas, with unidentified contents rather than usable
tables. The correction required removing those references and recreating
them under dbo; Salesforce data and the share were unchanged.

The decisive check is the wizard preview:

```text
Correct:   <lakehouse> > Tables/dbo
Incorrect for these table shortcuts: <lakehouse> > Tables
```

A schema shortcut is a distinct concept, not inherently invalid. The mistake
here was treating one DLO table directory as an entire schema.
This runbook qualifies individual table shortcuts only.

### 9.2 Authenticate the saved connection

Choose **Salesforce Data360**.
Allow external-source options to finish loading if it is not initially shown.

For a new connection:

1. Use `<data360-instance-url>`, not the Salesforce CRM login/My Domain URL.
2. In the connector's Salesforce tenant/org identifier field, use the exact
   `<data360-primary-tenant-id>` from Salesforce.
3. Select **Organizational account**.
4. Sign in to Entra as `<reader-upn>`.
5. Confirm this is the account whose user Object ID was saved in the target.
6. Save/create only the intended connection with a descriptive name.

The qualified UI also offered **Service principal**, but that mode was not
tested. Do not copy the user-Object-ID recipe into a daemon design without
separately qualifying its target identity and authentication requirements.

The connection dialog may recognize an existing connection for an identical
source and switch to it automatically. A typed new name does not prove a new
connection was created. Always recheck the actual selected saved connection.
The investigation kept a separate, clearly labeled full-tenant test connection
to avoid confusing it with the earlier bare-org-ID connection.

For an existing connection:

- Select the exact approved saved connection, not the first similar name.
- Inspect endpoint and tenant settings if identity errors persist.
- Reauthenticate/update credentials only when needed and approved.
- Re-select it if the UI clears the dropdown after an authentication callback.

Do not collect access tokens, cookies, authorization codes or full network
headers as debugging artifacts.

### 9.3 List and select the shared tables

Choose Next to request a listing.
The share API name, `F1_Demo_Salesforce_Bronze` here, should appear as a
top-level bucket/directory.

Open it and verify that exactly the nine expected DLO directories are present.
Select those nine directories individually.
Do not select the whole share as a single table, unrelated data or subfolders
inside an individual DLO.

Next -> review the shortcut preview:

- Target type is Salesforce Data360.
- Location is `<lakehouse> > Tables/dbo`.
- Nine expected names and source paths are shown.
- There are no collisions or unexpected existing shortcuts.
- Each item is pending creation, not already reported as complete.

Preserve DLO names for direct source traceability in Bronze.
Renaming is optional design work, not necessary for successful integration.
Any later curated names belong to the owning projection package.

Create once and wait for terminal completion. Verify all nine references
appear as **tables under dbo**, not sibling schemas beside dbo.

## 10. Verify the complete data path

### Separate the acceptance levels

| Level | Evidence | Insufficient substitute |
| --- | --- | --- |
| CRM ready | Source counts/keys reconcile | Fixture files alone |
| DLO ready | Active streams, successful ingestion and DLO totals | Stream configuration exists |
| Reader accepted | Successful connector listing | SAML web login |
| Data exposed | Linked active target/share and nine listed DLOs | Active target with zero shares |
| References created | Nine table shortcuts under dbo | Wizard's Next button succeeds |
| Data readable | Actual table rows/schema read successfully | HTTP 200 metadata or explorer names |
| Downstream ready | Separate SQL/model/app tests | Lakehouse preview alone |

For each table, click the table and wait for the preview to finish.
Record its terminal result, shown rows, column count and duration.
For these fixture sizes below the preview limit, the UI's shown-row totals
can be compared with source totals. For larger datasets, a preview cap is not
a complete row count: use a separately verified count query.

Do not repeatedly refresh an apparently slow query. Metadata listing and
preview execution are different workloads. Preserve diagnostics privately,
try a bounded UI reload/reopen if appropriate, and record whether it resolves
the issue without changing identities or source data.

### Observed Fabric read evidence

The following records the investigation's verification, not a clean rebuild
or a claim that a SQL endpoint query has executed:

| Shortcut under dbo | Expected rows | Fabric preview rows | Fabric columns | Read status |
| --- | ---: | ---: | ---: | --- |
| Account_Home__dll | 438 | 438 | 73 | Succeeded |
| Contact_Home__dll | 514 | 514 | 76 | Succeeded |
| Campaign_Home__dll | 12 | 12 | 50 | Succeeded |
| Opportunity_Home__dll | 288 | 288 | 53 | Succeeded |
| Case_Home__dll | 40 | 40 | 55 | Succeeded |
| F1Consent_c_Home__dll | 400 | 400 | 30 | Succeeded |
| F1CampaignTouch_c_Home__dll | 372 | Not verified | Not verified | Failed: TableNotFound; exposed format-conversion log reports SYSTEM failure |
| F1SponsorshipAgreement_c_Home__dll | 12 | 12 | 30 | Succeeded |
| F1SponsorshipCommitment_c_Home__dll | 12 | 12 | 33 | Succeeded |

Eight successful previews reconcile to **1,716 rows**. The remaining 372
CampaignTouch rows are present in the reconciled source/DLO inventory, but
their Fabric read is **not yet qualified**. Its initial preview remained
running for more than nine minutes without a terminal result. A browser
reload and a subsequent table-scoped Refresh did not establish success;
the latter restarted the displayed timer but was still running after five
minutes before returning **Unable to load table view**. The error-details
panel reported HTTP 400, **TableNotFound**. No identity, permission or
source-data change was made for this isolated read problem.

### CampaignTouch: metadata visibility versus format-conversion failure

Read-only **View files** inspection of that shortcut succeeded. Its root
contained `data`, `metadata` and `_delta_log`. The `_delta_log` directory
listed an initial JSON transaction file, a CRC file, `_staged_commits`
and `latest_conversion_log.txt`.

Opening `_delta_log/latest_conversion_log.txt` in Fabric's file viewer
reported:

```text
OneLake Table Format Conversion Details
Status:          Failed
Latest Metadata: N/A
Error Category:  SYSTEM
Error Details:   Conversion failed. Please retry later.
                If the issue persists, contact support attaching
                the content of this log.
```

This is concrete evidence of a failed format-conversion step in the exposed
source, not another connector-login failure. It explains why successful
directory listing is insufficient; it does not identify the underlying
cause of the conversion's generic SYSTEM error. In particular, the evidence
does not establish that the Engagement category or event-time field caused it.
The presence of `_delta_log` and an initial JSON file alone did not establish
a usable table.

For this failure pattern, inspect the exposed conversion log before changing
Fabric identities or recreating CRM data. Preserve the original diagnostic
and correlation references privately, follow supported retry guidance, and
escalate a persistent conversion failure to the platform owner/support.
Do not edit generated Delta/Iceberg metadata, remove `_staged_commits`, delete
the source or repeatedly trigger source reloads as an undocumented repair.
The remaining read-acceptance gate stays open until CampaignTouch actually
returns its expected 372 rows.

Generated/system fields mean CRM, wizard-selected source field, DLO and Fabric
column counts can differ. The observed Fabric column counts above are a
reconstruction baseline, not a portable contract. Check actual field names and
types before downstream transformations; displayed names can be normalized.

### Optional SQL reconciliation after endpoint qualification

If these shortcuts are registered and queryable through the intended SQL
analytics endpoint, this read-only T-SQL is a useful independent check:

```sql
SELECT 'Account' AS source_object, COUNT_BIG(*) AS row_count
FROM dbo.Account_Home__dll
UNION ALL SELECT 'Contact', COUNT_BIG(*) FROM dbo.Contact_Home__dll
UNION ALL SELECT 'Campaign', COUNT_BIG(*) FROM dbo.Campaign_Home__dll
UNION ALL SELECT 'Opportunity', COUNT_BIG(*) FROM dbo.Opportunity_Home__dll
UNION ALL SELECT 'Case', COUNT_BIG(*) FROM dbo.Case_Home__dll
UNION ALL SELECT 'F1Consent', COUNT_BIG(*) FROM dbo.F1Consent_c_Home__dll
UNION ALL SELECT 'F1CampaignTouch', COUNT_BIG(*) FROM dbo.F1CampaignTouch_c_Home__dll
UNION ALL SELECT 'F1SponsorshipAgreement', COUNT_BIG(*)
FROM dbo.F1SponsorshipAgreement_c_Home__dll
UNION ALL SELECT 'F1SponsorshipCommitment', COUNT_BIG(*)
FROM dbo.F1SponsorshipCommitment_c_Home__dll;
```

This query is a verification recipe, **not recorded SQL execution evidence**.
An independent SQL-tool attempt could not execute because that tool lacked
authentication. That is separate from the working browser/shortcut identity.
The authenticated browser SQL endpoint was also inspected: it displayed
an empty-warehouse state before and after one metadata-sync attempt.
No count query was executed there. That observation does not establish
whether the cause is registration delay, format/type compatibility or another
endpoint limitation; do not call SQL consumption qualified or manufacture
replacement tables to hide the gap.
If tables are not yet visible in the endpoint, inspect registration/sync state
and supported types before granting rights or creating replacement tables.

After counts, check representative keys, timestamps, source provenance,
crosswalk fields and consent values against the approved synthetic fixture.
A count match alone does not validate business semantics or deletion handling.
Never publish raw record exports or tenant-specific query diagnostics.

## 11. Optional Salesforce web SSO

Web SSO was explored during the investigation, but is **not established as a
prerequisite** for this native shortcut. It should not be added to the shortest
reconstruction path merely because it happened before the working target test.

The tested SAML setup linked Entra to an **existing** Salesforce user through
the Salesforce Federation ID. It did not require a new Salesforce user,
JIT provisioning, SCIM or changing the Salesforce username.
Local Salesforce login was retained as a recovery path.

In the tested Entra enterprise application:

- NameID source was `user.userprincipalname`.
- The initial NameID format was Email address.
- The actual correction was **Email address -> Unspecified**.
- The source expression was already correct; do not misreport changing it.

Salesforce's SAML Validator initially confirmed issuer, audience, recipient,
time and signature checks but could not map the opaque Subject to a user.
After the approved format correction, web login reached the existing
Salesforce user and its Data 360 access.

A SAML request's NameIDPolicy and claim behavior can affect the returned
Subject. Diagnose the actual assertion mapping using the validator rather
than blindly changing certificates or broad user permissions.
Do not paste a complete assertion or authentication response into Git/issues.

Reauthenticating the Fabric connection after this successful SSO still gave
HTTP 401. The later outbound-target identity binding, not SAML login success
alone, was the decisive connector breakthrough.

Any replication of SSO needs separate approval for the specific enterprise
application, claim change, user mapping and retained recovery access.
Do not grant admin consent or create secrets for an optional SSO experiment.

### Optional SSO configuration worksheet and sequence

Keep the following values private and distinct from the outbound-sharing
worksheet. They describe web authentication, not the Fabric connection:

| Setting | Where to obtain it / qualified treatment |
| --- | --- |
| Salesforce My Domain | Read the approved org's deployed My Domain; do not use the Data 360 instance URL |
| SAML Identifier / Entity ID | Use the value expected by that Salesforce SAML configuration; the tested configuration used its My Domain root |
| Reply / ACS URL and sign-on URL | Verify against that org's SAML configuration; the tested Entra configuration used the My Domain root |
| Entra issuer | Copy the enterprise application's SAML setup value, not its application/client ID |
| Entra SAML login URL | Copy the application's SAML login URL; do not substitute a generic OAuth authorization endpoint |
| Signing certificate / federation metadata | Use the same enterprise application's current metadata and signing certificate; record expiry/rotation ownership privately |
| NameID source and format | Tested values: `user.userprincipalname` and Unspecified |
| Existing Salesforce Federation ID | Match the intended user's emitted NameID, without renaming the Salesforce username |
| SAML identity mapping | Federation ID matched to the Subject/NameID |
| Assignment and recovery | Only the approved reader was assigned; the local Salesforce login page was retained |

With approval for this optional identity change:

1. Inventory existing enterprise applications and Salesforce SAML settings.
   Do not modify an unrelated connector's OAuth resource application.
2. Configure the approved Salesforce enterprise application for SAML using
   the actual org's Identifier, Reply and sign-on values. Do not assume that
   a generic gallery default is valid for every My Domain.
3. Transfer its federation metadata/signing information through the approved
   administrative channel to Salesforce Setup -> Single Sign-On Settings.
   Verify issuer, login URL, certificate and Entity ID after import.
4. Configure mapping to the existing Salesforce user's Federation ID.
   The qualified path did not enable JIT provisioning or single logout.
5. Set that user's Federation ID to the intended NameID value and verify
   the Entra account assignment. These are access/identity changes requiring
   their own approval.
6. In My Domain authentication configuration, expose the intended SSO option
   while retaining the local login page and an authorized recovery session.
7. Test in a separate browser context. If mapping fails, use Salesforce's
   SAML Validator to distinguish signature/issuer/audience/time failures from
   a valid assertion whose Subject does not identify the intended user.
8. Apply only the approved correction. In this investigation, changing the
   NameID format to Unspecified resolved the opaque-Subject mapping failure;
   no new Salesforce user, password reset or extra Data Cloud role was needed.
9. Verify both successful web sign-in and access to the intended Data 360
   application. Then test the Fabric connector independently.

Metadata imported during the investigation was normalized to UTF-8 without
a byte-order mark. Treat that as an observed import preparation, not a
universal SAML requirement. Never put the tenant-specific metadata,
assertion, certificate bindings or actual identity values in the public repo.

## 12. Troubleshooting and investigation findings

| Symptom | Interpretation/check | Scoped next action |
| --- | --- | --- |
| Salesforce Recently Viewed shows zero streams/shares/targets | Not a full inventory | Switch to All, clear search and inspect existing records |
| OneLake or Salesforce source option absent immediately | Options may still be loading or below the fold | Wait, inspect/scroll, then check feature entitlement if still absent |
| Organizational-account dialog opens Microsoft login | Expected Entra authentication | Use the approved reader; do not expect Salesforce login |
| Generic HTTP 401 / Not Authorized | Authentication/target/source settings not yet aligned | Check actual selected connection, instance endpoint, primary tenant, Entra tenant and reader Object ID |
| Subject and Issuer do not match target | Observed target/reader binding failure | Compare target tenant and reader user Object ID with the signed-in connection |
| Reauthentication succeeds but listing remains 401 | Fresh credentials do not create sharing authorization | Inspect target/share configuration instead of cycling logins |
| HTTP 200 and No results found | Reader accepted but no visible share, potentially no linked share | Check exact Data Share -> target link and active state |
| Share visible but wrong/missing objects | Wrong data space, object selection, link or loading state | Inspect the saved share's object list and DLO readiness |
| Target active with Related Shares = 0 | Target exists but exposes no linked share | Create/reuse the scoped share and explicitly link it |
| DLO names appear beside dbo as schemas | Wrong destination level for table shortcuts | Use approved correction: remove only those references and recreate inside dbo |
| Unidentified contents in a new schema shortcut | A DLO directory was treated as a schema | Do not assume data corruption or repair Salesforce; inspect shortcut placement |
| Actual table preview remains running | Metadata success is not query completion | Capture nonsecret diagnostics; bounded reopen/reload; keep read acceptance pending |
| TableNotFound despite a listed shortcut and readable folders | Table registration or source format conversion may have failed | Inspect View files -> _delta_log/latest_conversion_log.txt when present; preserve diagnostics and follow supported recovery |
| Exposed conversion log reports Failed / SYSTEM / Latest Metadata N/A | Observed CampaignTouch format-conversion failure; detailed cause unspecified | Follow supported retry/support guidance; do not edit generated metadata or broaden permissions |
| Stream provisioning/refresh running | Source lifecycle operation is not finished | Wait for terminal state; do not duplicate refresh/deploy requests |
| Latest processed count differs from total | Different metrics, observed N+1 vs N | Reconcile total records and actual downstream rows |
| Login can enter Salesforce but Fabric fails | Independent identity boundaries | Diagnose connector/target authorization, not just SAML |
| Saved connection selector clears after callback | UI selection state changed | Reselect the exact approved connection before Next |
| Unexpected connection name after new-source entry | UI reused an existing matching connection | Inspect actual saved binding before changing it |
| Access-looking error on guessed Salesforce URL | Object route may be wrong | Use actual ExtDataShare/ExtDataShareTarget navigation before considering permissions |
| Bulk activation dialog mentions deletion | Contradictory action text | Cancel and use coherent, scoped individual activation |
| External tool requires authentication | Tool connection is separate from browser identity | Authenticate that tool through its configured client if needed; do not change Salesforce access |

### Efficient diagnostic order

Use the failing layer to choose the next check:

1. **No CRM rows:** source qualification/mapping/seed problem.
2. **CRM rows but empty DLO:** stream state, source selection, execution or quota.
3. **DLOs populated but HTTP 401:** source settings and target identity.
4. **HTTP 200 but no share:** Data Share/target link and exposure.
5. **Share visible but references wrong:** selected objects/destination schema.
6. **Correct shortcuts but read failure:** query/format/endpoint diagnostics.
7. **Preview works but app fails:** separately owned serving/consumer path.

Do not jump from step 3 to broad permission grants or from step 6 to rebuilding
the source without evidence. Keep one controlled change per identity experiment
and record its before/after result.

### Browser automation lessons

Prefer browser-scoped DevTools automation when the user is working in parallel.
Do not take foreground control as a workaround for slow UI loading.
Inspect current controls before acting; old element references can be stale.

In the observed Fabric build, the Lakehouse iframe was rendered with a
presentation role and omitted its content from accessibility snapshots despite
being visible. A temporary local title/removal of that role exposed the tree.
This was a browser-only accessibility adjustment, not a cloud setting or
required integration step. Restore temporary DOM adjustments afterward.

Some checkbox inputs in Salesforce/Fabric are visually hidden behind custom
controls, so generic fill/check tools timed out. Inspect the exact row/label
and verify checked state after interaction. Do not select global checkboxes
across hidden wizard steps. Read back the saved nine-object scope.

Do not bypass CAPTCHA, certificate warnings, MFA or access-denied policy.
Never extract tokens to build an undocumented authentication workaround.

## 13. Operations, governance and cost

### Security boundary

Salesforce's Data Share documentation warns that Data 360 governance policies
are not automatically applied to shared data in the external destination.
Do not assume Salesforce consent rules, row filters or masking remain enforced
in Fabric just because the DLO originates in Data 360.

Review receiving workspace/item permissions and consumer identities explicitly.
The tested target's reader account binding is not a complete Fabric
authorization model. A downstream application must receive only the data
and permissions its use case requires.

Sharing a DMO can expose underlying DLO records; the wizard acknowledgment is
not cosmetic. This run used explicit DLOs, avoiding an assumption that a
modeled DMO is necessarily a narrower security boundary.

### Credential lifecycle

The qualified connection is user-backed Organizational-account authentication.
For an operational demo, record privately:

- Reader and connection owner, with a responsible human contact.
- Entra policies relevant to interactive authentication and renewal.
- How to identify the saved connection and target without publishing GUIDs.
- Approved reauthentication and revocation procedures.
- Consumer dependencies before an account is disabled or replaced.

If the reader changes, its Object ID changes even when a sign-in name looks
similar. Treat target rebinding and connection replacement as access changes.
Service principal/managed identity conversion requires separate qualification;
do not present the interactive demo configuration as unattended production auth.

### Freshness and credits

CRM -> Data 360 ingestion is still a data movement/refresh stage. The native
Fabric shortcut avoids a separately orchestrated copy into Bronze for this
path; it does not imply that the whole architecture has no ingestion,
storage, execution, network or credit costs.

Monitor CRM API limits, Data 360 ingestion/refresh/sharing usage, Fabric
capacity load and query latency. Recheck current product terms.
Avoid repeated initial loads, full-refresh schedules and impatient retries.
No cost, throughput or latency benchmark was established by the investigation.

### Changes and schema evolution

New CRM fields/objects do not automatically become an approved public share
scope. Inspect stream schema and sharing behavior before accepting changes.
Capture baseline columns and downstream expectations. Reconcile inserts,
updates, inactivation and deletion with separately approved synthetic tests.

Do not infer deletion propagation from a successful initial count. A future
lifecycle test must define the source change, expected DLO transition,
expected Fabric result, timing, evidence and recovery first.

Keep the source ownership and canonical business invariants in #20/#18 and
the projection logic in #4. This runbook does not make Bronze ready for every
consumer or permit direct app ownership of source-native tables.

## 14. Rollback and reconstruction

### Non-destructive failure handling

Before creation, canceling a wizard leaves no shortcut; verify that explicitly.
Once a target/share/connection is saved, do not assume closing the page rolls
it back. Inventory persistent objects after an interrupted operation.
Successful asynchronous creation requires a terminal readback.

### Correct a misplaced shortcut

The investigation's approved correction was:

1. Identify the exact nine newly created root-level shortcut references.
2. Obtain approval to remove those references only.
3. Remove each misplaced schema shortcut, not dbo or the Lakehouse.
4. Verify dbo remains and the misplaced references are gone.
5. Start New table shortcut from dbo.
6. Reuse the existing connection/share; reselect the same nine DLO directories.
7. Confirm `Tables/dbo` in the preview before Create.
8. Verify table placement and actual reads.

Removing a shortcut does not delete its source data, but removing a real table,
schema or item is a different operation. Inspect the exact object kind and
confirmation before acting. Never use recursive cleanup, wildcard deletion or
automatic orphan removal.

### Revoke exposure or retire the integration

Revocation is an access change and requires explicit approval.
First inventory consumers and saved connection dependencies.
Decide whether the objective is to remove a Fabric reference, revoke a
particular reader's exposure, stop CRM ingestion or retire the whole source:
these are different actions.

Use the supported UI to unlink the exact target from the share when that is
the approved revocation. Verify the link is gone and perform a scoped access
test. Do not assume immediate revocation semantics or cache invalidation
without testing them. Do not delete DLOs/streams to solve a shortcut problem.

Only remove unused targets, shares or connections after ownership and
dependencies are checked. Preserve private evidence needed for reconstruction.
Do not disable local Salesforce recovery login or modify SSO as shortcut
cleanup. Do not touch the independent Oracle/SAP paths.

### Shortest reconstruction sequence

With fresh approvals and a private worksheet:

1. Confirm org entitlements, feature availability, quotas and budget.
2. Confirm CRM schema/data and the fixture's version/counts.
3. Reuse/create only the nine approved streams; finish and reconcile ingestion.
4. Identify the actual Fabric Organizational-account reader and its Entra
   tenant/user Object ID.
5. Create/reuse the OneLake outbound target with those identity values.
6. Copy the displayed Data 360 endpoint/full primary tenant into the worksheet.
7. Create/reuse the scoped DLO-only share; link it to that target.
8. Open the existing Fabric Lakehouse schema, then New table shortcut.
9. Create/reuse the correctly bound saved connection.
10. List share -> select nine DLOs -> verify Tables/dbo -> Create.
11. Read every table, reconcile counts/keys and retain private evidence.
12. Qualify the intended downstream engine separately.

Optional web SSO is not inserted as an unexplained prerequisite.
No new app registration, secret or broad permission grant is part of the
verified Organizational-account reconstruction recipe.

## 15. Evidence and handoff checklist

Keep this public checklist free of actual environment bindings:

- [ ] Approved source/destination/identity/region/budget/rollback recorded privately.
- [ ] Current edition/feature/credit terms checked, not assumed from this demo.
- [ ] CRM totals, keys, references and fixture version recorded.
- [ ] Complete stream inventory inspected; only scoped streams changed.
- [ ] Nine streams active with successful terminal executions and matching totals.
- [ ] DLO names/data space verified; no unrelated DMO selected.
- [ ] Target platform/tenant/reader Object ID read back from saved configuration.
- [ ] Share active, Outbound, nine objects, exact target linked and Active.
- [ ] Fabric saved connection's endpoint/full primary tenant/reader verified.
- [ ] Share and nine DLO directories listed successfully.
- [ ] Preview location is Tables/dbo before creation.
- [ ] Nine shortcuts are tables under dbo, with no stray root schema shortcuts.
- [ ] Every table returns actual rows/schema; counts reconcile, total 2,088 for this fixture.
- [ ] Slow/failed reads and bounded recovery attempts recorded, not reported passed.
- [ ] Downstream SQL/model/app and lifecycle propagation remain separate acceptance gates.
- [ ] No token/assertion/cookie/secret/tenant binding/raw record appears in Git or issue evidence.
- [ ] Operator/connection ownership and recovery procedure handed off privately.
- [ ] Clean-environment reconstruction status is stated honestly.

For each live read, retain privately the table name, timestamp, engine, terminal
status, count/columns, duration and nonsecret correlation reference if needed.
Do not publish full HAR files or screenshots containing account/resource details.

Documentation changes should pass the repository's credential-free checks:

```powershell
python -m scripts.validate_repo
python -m unittest discover -s tests -p "test_*.py" -v
git diff --check
```

Passing these checks validates repository consistency, not Salesforce
entitlements or end-to-end cloud reconstruction.
Do not commit, push or open a PR without the repository's explicit approval
and independent actual-diff review gate.

## 16. References and documentation traps

- [Salesforce Data Shares](https://help.salesforce.com/s/articleView?id=data.c360_a_data_shares.htm&type=5):
  sharing concepts, acknowledgment and governance implications.
- [Microsoft OneLake shortcuts](https://learn.microsoft.com/en-us/fabric/onelake/onelake-shortcuts):
  general shortcut concepts; not proof of Salesforce-specific field semantics.
- [Lakehouse schemas](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-schemas):
  destination schema concepts and table organization.
- [Microsoft SAML claims customization](https://learn.microsoft.com/en-us/entra/identity-platform/saml-claims-customization):
  optional SAML NameID diagnosis, not connector authorization instructions.
- [Salesforce Microsoft Fabric OneLake connection](https://developer.salesforce.com/docs/data/data-cloud-int/guide/c360-a-set-up-microsoftfabriconelake-connection.html):
  **reverse direction**, Salesforce reading Fabric. Do not transplant its
  app-secret/workspace requirements into this outbound-share procedure.

During investigation, an announcement's getting-started link led to that
reverse-direction guide. A guessed Salesforce-shortcut-specific Microsoft
Learn URL returned 404. Generic connector blogs and search summaries also
mixed the two directions. Check the actual data flow and authentication
surface before treating a source as applicable.

Where public documentation did not establish the Organizational-account
Service Account ID semantics, this runbook explicitly labels the observed
successful experiment instead of claiming a vendor-wide guarantee.
Revalidate release-specific availability and behavior before reuse.
