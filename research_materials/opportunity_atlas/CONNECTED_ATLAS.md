# Connected Opportunity Atlas — sources → mechanisms → implementation leads

This is the **connection layer** between existing atlas discovery inventories. Every relationship below is an AI-proposed, exact-description-anchored hypothesis. It is **not** proven interoperability, product market fit, a current procurement, a verified scientific causal finding or a target recommendation.

## What was and wasn't connected

Across 6 broad fields, the source linking pass proposed 3 possible components, 3 category-only alignments and 11 explicit technical mismatches. All have zero independently validated integrations and zero buyer commitments.

## Source-anchored relationships, including exclusions

### Energy Environment

Bounded sources: 3 published requirements; 18 repository descriptions; 5 optional model-generated research readings.

**Candidate Component** — [Italy – Energy-management services – Procedura aperta per la Gestione dei Vettori Energetici delle Aziende Sanitarie della Regione del Venet](https://ted.europa.eu/en/notice/-/detail/725724-2026) ↔ [u9n/dlms-cosem](https://github.com/u9n/dlms-cosem)

Mechanism: DLMS/COSEM is the international standard protocol (IEC 62056) for smart utility metering across electricity, thermal, and gas vectors. The library provides protocol parsing capabilities that could serve as a telemetry ingestion component for automated energy consumption tracking across healthcare facility assets.

Important mismatch: Addresses only low-level protocol frame parsing; it does not address comprehensive multi-site energy management, billing validation, utility contracting, or physical maintenance. Transfer is hindered by absence of enterprise telemetry integration, operational service support, and security certification for Italian public health IT infrastructure.

Next verification: Verify whether the library supports OBIS profile capture decoding and HDLC/TCP transport for gas and thermal sub-meters compliant with Italian healthcare facility metering standards.

Anchors: institutional description: *Gestione dei vettori energetici per Azienda ULSS n. 1 Dolomiti*; repository description: *A Python library for DLMS/COSEM*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

Repository documentation: [README at checked revision](https://github.com/u9n/dlms-cosem/blob/main/README.md) describes a Python DLMS/COSEM protocol library with APDU encoding/decoding, selective access, HDLC serial and TCP client transport. **Not demonstrated:** Meter installation, regulated Italian healthcare integration, multi-site energy operations, or a completed commercial product.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

**Wrong Fit** — [Sweden – Architectural, construction, engineering and inspection services – Tekniska konsulttjänster VVS](https://ted.europa.eu/en/notice/-/detail/723891-2026) ↔ [raghudeepika/urban-resource-cadastre-repository](https://github.com/raghudeepika/urban-resource-cadastre-repository)

Mechanism: Both assets superficially touch upon circular economy and material reuse in buildings, but the notice specifies HVAC/plumbing (VVS) engineering consultancy, whereas the repository applies computer vision to street-level imagery for exterior envelope facade material classification.

Important mismatch: Computer vision models trained on exterior street-level photographs cannot detect, inspect, or evaluate the condition and compliance of indoor HVAC, heating, ventilation, or sanitary piping components required by Swedish building regulations.

Next verification: Inspect the dataset taxonomy in the repository to confirm that classified classes are restricted to external facade surfaces (e.g., concrete, glass) and contain no mechanical or VVS installations.

Anchors: institutional description: *Konsulter ska i uppdrag stötta B att öka andelen återbrukat material.*; repository description: *building facade material detection*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

**Wrong Fit** — [Germany – Environmental monitoring for construction – A8 Albaufstieg - Bodenbaubegleitung (BBB)](https://ted.europa.eu/en/notice/-/detail/726035-2026) ↔ [DOI-USGS/EGRET](https://github.com/DOI-USGS/EGRET)

Mechanism: Both sit within environmental monitoring of infrastructure projects, but Bodenbaubegleitung (BBB) is on-site pedological soil protection supervision during highway earthworks, whereas EGRET provides statistical regression modeling (WRTDS) for river water quality and discharge time series.

Important mismatch: Fluvial statistical software cannot satisfy statutory on-site pedological monitoring, soil compaction mitigation, or earthmoving guidance required under German soil conservation regulations (BBodSchG/DIN 19639).

Next verification: Review package function exports to confirm the software lacks modules for soil mechanics, pedological surveys, or construction-phase geotechnical monitoring.

Anchors: institutional description: *A8 Albaufstieg - Bodenbaubegleitung (BBB)*; repository description: *analysis of long-term changes in water quality and streamflow*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

---

### Engineering

Bounded sources: 3 published requirements; 17 repository descriptions; 5 optional model-generated research readings.

**Implementation Category Only** — [Germany – Architectural, construction, engineering and inspection services – Klinikum Bayreuth_TMon IBM](https://ted.europa.eu/en/notice/-/detail/714960-2026) ↔ [FreeCAD/FreeCAD](https://github.com/FreeCAD/FreeCAD)

Mechanism: FreeCAD provides open-source 3D parametric computer-aided design modeling and basic Building Information Modeling (BIM) drafting modules that broadly align with the geometric modeling requirements of facility design for the operating building.

Important mismatch: Complex medical architecture requires certified DIN 13080 hospital functional space mapping and specialized engineering compliance tools not present in baseline FreeCAD, and the procurement calls for professional architectural planning services rather than standalone geometric software.

Next verification: Evaluate FreeCAD BIM/Arch workbench documentation to verify whether it can natively import and validate German clinical facility IFC4 spatial classification profiles.

Anchors: institutional description: *Gegenstand der Maßnahme ist der Neubau eines OP-Gebäudes südlich des bestehenden Klinikkomplexes.*; repository description: *Official source code of FreeCAD, a free and opensource multiplatform 3D parametric modeler.*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

**Wrong Fit** — [Finland – Repair, maintenance and associated services related to marine and other equipment – VENESATAMIEN HOITO](https://ted.europa.eu/en/notice/-/detail/723344-2026) ↔ [DOI-USGS/EGRET](https://github.com/DOI-USGS/EGRET)

Mechanism: Both domains involve aquatic environments, but EGRET conducts statistical regression analysis on long-term river discharge and chemical water quality rather than harbor infrastructure management.

Important mismatch: Total functional mismatch: hydrological time-series regressions cannot execute physical boat harbor upkeep, dock repairs, harbor fee oversight, or retail marina fuel dispensing operations.

Next verification: Inspect EGRET package export functions to confirm the codebase exclusively contains hydrological regression modeling without dock asset management or operational service workflows.

Anchors: institutional description: *Varkauden kaupungin venesatamien hoidon urakka sisältää urakka-asiakirjoissa esitettyjen pienvenesatamien ja laitureiden hoidon urakka-asiakirjojen mukaisesti.*; repository description: *An R-package for the analysis of long-term changes in water quality and streamflow*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

**Wrong Fit** — [Ireland – Building and facilities management services – M700.CN.1025 - Soft Facilities Management Services for MetroLink (TII)](https://ted.europa.eu/en/notice/-/detail/707304-2026) ↔ [apache/airflow](https://github.com/apache/airflow)

Mechanism: Topical overlap around task and workflow management, but Airflow orchestrates software data pipelines via directed acyclic graphs rather than on-site corporate facilities operations.

Important mismatch: Categorical disconnect: a programmatic batch compute scheduler cannot provide or coordinate physical human reception personnel, janitorial services, or office maintenance staff.

Next verification: Review the core Airflow operator library to verify absence of human physical resource dispatching or facilities management maintenance ticketing integrations.

Anchors: institutional description: *Staff requirements for the Coopers Cross Office including 2 x reception staff and 2 x facilities assistants.*; repository description: *Apache Airflow - A platform to programmatically author, schedule, and monitor workflows*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

---

### Investigation Finance

Bounded sources: 3 published requirements; 18 repository descriptions; 4 optional model-generated research readings.

**Wrong Fit** — [Luxembourg – Compliance software development services – Operational Risk Management Software](https://ted.europa.eu/en/notice/-/detail/404621-2026) ↔ [koala73/worldmonitor](https://github.com/koala73/worldmonitor)

Mechanism: Both systems provide situational monitoring and alerting capabilities, but WorldMonitor aggregates external geopolitical and infrastructure intelligence streams rather than internal institutional risk controls, risk and control self-assessments (RCSA), or operational incident records.

Important mismatch: Completely lacks internal corporate governance, risk, and compliance (GRC) workflows, audit trails, policy management, and institutional control frameworks required for European financial stability administration.

Next verification: Inspect WorldMonitor's repository schema to confirm whether it possesses internal incident logging and control assessment data models or strictly external OSINT and news feed parsing pipelines.

Anchors: institutional description: *Policies and procedure repository, Business processes / controls repository, RCSA, Operational risk incident management, Key risk indicators, Reporting.*; repository description: *AI-powered news aggregation, geopolitical monitoring, and infrastructure tracking in a unified situational awareness interface*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

**Wrong Fit** — [Ireland – Software package and information systems – UCC-2025-02 Provision of an Enterprise Risk Management Software System](https://ted.europa.eu/en/notice/-/detail/434418-2026) ↔ [openbq-org/OpenBB](https://github.com/openbq-org/OpenBB)

Mechanism: Tempting thematic alignment under the broader umbrella of financial and quantitative analytics, but OpenBB is designed for investment data analysis and quantitative modeling rather than institutional Enterprise Risk Management (ERM) tracking, risk appetite registers, or educational governance.

Important mismatch: Missing cloud-based enterprise governance modules, institutional risk matrices, role-based organizational compliance workflows, and multi-departmental administrative reporting.

Next verification: Examine OpenBB feature documentation to verify that endpoints target financial market/security telemetry rather than institutional risk registers and regulatory compliance forms.

Anchors: institutional description: *cloud-based software platform that supports UCC’s risk management objectives.*; repository description: *Open Data Platform for analysts, quants and AI agents.*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

**Wrong Fit** — [Ireland – Records management – Invitation to Tender (ITT) for the provision of an Integrated Board Governance and Risk Management Software S](https://ted.europa.eu/en/notice/-/detail/646960-2026) ↔ [apache/airflow](https://github.com/apache/airflow)

Mechanism: Airflow provides DAG-based programmatic task orchestration and monitoring across backend systems, but it is a developer data-engineering tool rather than an off-the-shelf business application for board governance and risk management.

Important mismatch: Lacks turn-key board management interfaces (such as meeting agenda compilation, resolution voting, and board pack distribution) and requires ongoing engineering orchestration rather than serving as an off-the-shelf business software package supporting non-technical administrative users.

Next verification: Review Airflow core plugins and webserver views to confirm the absence of board portal functionalities, secretarial meeting management, and compliance governance dashboards.

Anchors: institutional description: *integrated, off-the-shelf software solution comprising Board Governance and Risk Management functionality.*; repository description: *platform to programmatically author, schedule, and monitor workflows*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

---

### Knowledge Data

Bounded sources: 3 published requirements; 17 repository descriptions; 2 optional model-generated research readings.

**Candidate Component** — [Sweden – IT services: consulting, software development, Internet and support – Asset data platform- ADP](https://ted.europa.eu/en/notice/-/detail/718613-2026) ↔ [opendataloader-project/opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf)

Mechanism: The PDF parsing capability can address automated document ingestion and text/metadata extraction from contractor-submitted PDF documentation entering the airport document library.

Important mismatch: Addresses only document parsing; lacks technical CAD/drawing viewer capabilities, property portal UI, asset metadata hierarchies, access controls, and multi-airport enterprise operational support.

Next verification: Examine the repository's parser code to verify whether it handles large-format architectural drawings, vector layers, and fully offline on-premise execution without external cloud calls.

Anchors: institutional description: *library for all drawings and documents that operations and contractors may need in the work at the airport.*; repository description: *PDF Parser for AI-ready data. Automate PDF accessibility. Open-source.*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

Repository documentation: [README at checked revision](https://github.com/opendataloader-project/opendataloader-pdf/blob/main/README.md) describes PDF-to-JSON/Markdown/HTML parsing with local extraction and developer SDKs, plus an enterprise accessibility add-on. **Not demonstrated:** The on-prem Swedavia property-document portal, drawing/CAD semantics, asset records, staff permissions, service SLAs or existing procurement compliance.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

**Implementation Category Only** — [Sweden – IT services: consulting, software development, Internet and support – Asset data platform- ADP](https://ted.europa.eu/en/notice/-/detail/718613-2026) ↔ [ckan/ckan](https://github.com/ckan/ckan)

Mechanism: Provides a data management system (DMS) web architecture designed for cataloging, structuring, and sharing organizational datasets and associated technical document collections.

Important mismatch: CKAN is built primarily for public open-data catalogs and tabular datasets rather than physical airport facility management, CAD/engineering drawing workflows, or specialized property portal operations.

Next verification: Evaluate CKAN's extension ecosystem to determine if native extensions exist for engineering drawing version control, spatial facility hierarchies, and localized on-premise airport operational compliance.

Anchors: institutional description: *replace the current property portal. The system shall handle technical facility information and documentation of Swedavia's facilities*; repository description: *CKAN is an open-source DMS (data management system) for powering data hubs and data portals. CKAN makes it easy to publish, share and use data.*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Wrong Fit** — [Sweden – IT services: consulting, software development, Internet and support – Asset data platform- ADP](https://ted.europa.eu/en/notice/-/detail/718613-2026) ↔ [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)

Mechanism: Superficially aligns through parsing documentation and PDFs into structured knowledge, but the tool operates exclusively as a code intelligence and developer agent harness.

Important mismatch: Functionally inapplicable; built around source code AST parsing and developer CLI workflows rather than airport facility asset registers, maintenance documentation, or enterprise drawing repositories.

Next verification: Check repository parser implementations to verify that graph construction is strictly tied to programming language ASTs, developer configuration files, and software engineering schemas.

Anchors: institutional description: *The system shall handle technical facility information and documentation of Swedavia's facilities*; repository description: *Turn any codebase, with its docs, SQL schemas, configs, and PDFs, into a queryable knowledge graph.*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

Unlinked published requirements in this bounded comparison: ted:722526-2026, ted:703130-2026

---

### Physical Operations

Bounded sources: 3 published requirements; 13 repository descriptions; 5 optional model-generated research readings.

**Candidate Component** — [Malta – Analytical or scientific software development services – MAFA/CIO 3/2026 - Negotiated Procedure for the Procurement of Phase 3 Of Th](https://ted.europa.eu/en/notice/-/detail/606356-2026) ↔ [microsoft/farmvibes-ai](https://github.com/microsoft/farmvibes-ai)

Mechanism: FarmVibes.AI supplies geospatial machine learning pipelines designed to ingest satellite and remote-sensing data for agricultural classification tasks, which directly addresses the core model training and image inference layer required for automated crop identification.

Important mismatch: The repository is a general research and workflow orchestration platform rather than an operational EU/Maltese Integrated Administration and Control System (IACS) solution; it lacks integration with Maltese Land Parcel Identification Systems (LPIS), local crop ground-truth calibrations, and institutional deployment support.

Next verification: Examine the repository's workflow templates and model registry to determine whether preconfigured pipelines exist for Sentinel-2 parcel-level crop classification and land-cover boundary extraction.

Anchors: institutional description: *Procurement of Phase 3 Of The Ai Crop Identification System for MAFF*; repository description: *Multi-Modal GeoSpatial ML Models for Agriculture and Sustainability*.

Notice lifecycle: voluntary_ex_ante_notice. Source text match is not a current tender or an implementation result.

Repository documentation: [README at checked revision](https://github.com/microsoft/farmvibes-ai/blob/main/README.md) describes README documents multispectral/radar/satellite and weather data fusion pipelines with agricultural model-training and crop identification examples. **Not demonstrated:** A Malta-specific crop-identification service, regulatory IACS/LPIS integration, locally benchmarked crop classifier, availability to compete for an award/negotiated procurement.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

**Wrong Fit** — [Malta – Analytical or scientific software development services – MAFA/CIO 3/2026 - Negotiated Procedure for the Procurement of Phase 3 Of Th](https://ted.europa.eu/en/notice/-/detail/606356-2026) ↔ [Fields2Cover/Fields2Cover](https://github.com/Fields2Cover/Fields2Cover)

Mechanism: Both assets operate in digital agriculture, but Fields2Cover provides geometric coverage path planning and swath routing for autonomous field equipment, rather than earth observation computer vision or spectral classification for crop identification.

Important mismatch: Path planning algorithms cannot parse satellite or aerial imagery to identify crop types, leaving the buyer's computer vision and remote sensing requirements completely unaddressed.

Next verification: Check the API header files in Fields2Cover to confirm that modules focus exclusively on headland generators, path planners, and kinematic turn paths with no image classification or raster processing capabilities.

Anchors: institutional description: *Ai Crop Identification System for MAFF*; repository description: *coverage paths for autonomous agricultural vehicles*.

Notice lifecycle: voluntary_ex_ante_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

**Wrong Fit** — [Norway – Food, beverages, tobacco and related products – Food for commerical kitchens](https://ted.europa.eu/en/notice/-/detail/683922-2026) ↔ [dadaloop82/EverShelf](https://github.com/dadaloop82/EverShelf)

Mechanism: Both domains concern food supply management, but EverShelf is an end-user self-hosted inventory and pantry software application, whereas the procurement notice is for the physical wholesale delivery of food ingredients to municipal production kitchens.

Important mismatch: Software for barcode scanning and home pantries cannot satisfy physical commodity supply, cold-chain logistics, certified food safety transport, or municipal wholesale distribution obligations in Norway.

Next verification: Inspect EverShelf repository documentation and data schemas to verify that it functions solely as an inventory-tracking interface rather than an electronic B2B wholesale distribution and physical fulfillment system.

Anchors: institutional description: *contract for the supply of food products for commercial kitchens*; repository description: *smart pantry manager with AI expiry tracking, barcode scanning, smart shopping lists*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Caution:** The mismatch claims that the asset lacks or cannot perform something. That is NOT independently established by its README and needs a code-level check.

Unlinked published requirements in this bounded comparison: ted:593156-2026

---

### Public Services

Bounded sources: 3 published requirements; 18 repository descriptions; 5 optional model-generated research readings.

**Implementation Category Only** — [Ireland – IT services: consulting, software development, Internet and support – HSE 28439 - Restricted Procedure to procure a HSE Enterprise](https://ted.europa.eu/en/notice/-/detail/635530-2026) ↔ [apache/airflow](https://github.com/apache/airflow)

Mechanism: Airflow provides directed acyclic graph (DAG) scheduling to orchestrate multi-system data pipelines, aligning with general system integration and batch ETL workflows.

Important mismatch: An Enterprise Integration Platform as a Service (EiPaaS) requires real-time synchronous API routing, transactional messaging middleware, and health standard compliance (e.g., HL7/FHIR) rather than asynchronous batch workflow scheduling.

Next verification: Evaluate HSE interface specifications to determine if real-time transactional mediation is required, which Airflow's batch execution engine cannot natively support.

Anchors: institutional description: *support the HSE’s current heterogeneous integration landscape*; repository description: *platform to programmatically author, schedule, and monitor workflows*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

**Wrong Fit** — [Ireland – IT services: consulting, software development, Internet and support – HSE 28439 - Restricted Procedure to procure a HSE Enterprise](https://ted.europa.eu/en/notice/-/detail/635530-2026) ↔ [biopython/biopython](https://github.com/biopython/biopython)

Mechanism: Topical overlap around biology and health systems misleadingly suggests utility for national digital health infrastructure.

Important mismatch: Biopython is designed for molecular computational biology, bioinformatics sequences, and structural modeling, containing no capabilities for enterprise application integration, health record exchange, or service bus architecture.

Next verification: Review the Biopython codebase to verify that all modules target molecular sequence analysis (e.g., FASTA, GenBank, BLAST) rather than enterprise service integration or health data interchange standards.

Anchors: institutional description: *future digital health transformation*; repository description: *Official git repository for Biopython*.

Notice lifecycle: competition_notice. Source text match is not a current tender or an implementation result.

Unlinked published requirements in this bounded comparison: ted:723212-2026, ted:675938-2026

---

## Explicit limitations and next mapping layer

The public GitHub inventory was semantically audited on a subset only. Repo metadata cannot demonstrate a working feature. Official TED notice descriptions document *published requirements* but not an active tender or bidder eligibility. The small academic source selection is not comprehensive and its paraphrases were previously generated by another model.

Next: sample original technical docs or a small functional integration for each type of relation, expand primary problem data beyond public procurement, and map real institutional budget/maintainer constraints. **Do not prioritize a single market or start sending pitches from these candidate edges.**
