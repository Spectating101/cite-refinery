# YZU Problem Commons Conversion Pilot V0.1

Date: 2026-09-09

Status: **active conversion experiment**

This playbook converts the existing YZU social-responsibility ecosystem into the first real Problem Commons institutional pilot. It does not ask YZU to invent a new behavior. YZU already collects field needs, funds student social-action proposals, operates USR/USR Hub projects, accepts sponsorship and in-kind support, and reports social-impact outcomes.

## Existing YZU surfaces we can plug into

### 1. Field matching (場域媒合) — primary problem-supply feed

YZU's Sustainability Development and Social Responsibility Center already describes its field-matching page as a platform for collecting needs from communities, schools, nonprofits and public/private bodies and connecting them with faculty/students.

Current page:
https://esdg.yzu.edu.tw/index.php/tw/2025-11-28-08-49-26

Center contact published by YZU:
- csdusr@saturn.yzu.edu.tw
- (03)463-8800 ext. 2034 / 2038

Problem Commons wedge:

`field need listing -> owner-confirmed Problem -> bounded Project Brief(s) -> solver/resource matching -> reviewed output -> owner receipt -> outcome/reuse record`

### 2. Student autonomous social-participation funding — first internal solver/funding lane

YZU's student social-participation support program has two relevant modes:
- student team action proposal with funding up to NTD 50,000;
- year-round "problem idea" submissions that may receive a NTD 1,000 reward if successfully matched to an implementing team.

Source:
https://announce.yzu.edu.tw/index.php/tw/so/sd/5

Problem Commons wedge: turn a raw "problem idea" into a higher-quality owner-reviewed Problem and Project Brief before matching, and make the resulting project eligible for the existing student funding route where appropriate.

### 3. Sponsorship / ESG resource path

YZU publicly asks companies, alumni and the public to support social-responsibility programs through designated donations, equipment, technology support and manpower. The Sustainability Center coordinates technical/manpower cooperation.

Source:
https://esdg.yzu.edu.tw/index.php/tw/2024-12-05-05-59-24

Problem Commons wedge: Commons records the Project's actual resource need; Public-Good qualifies external resource/program matches; YZU remains the institutional recipient/authority for any real sponsorship or support.

### 4. USR / USR Hub operating programs — repeat problem-owner cohorts

Current YZU social-responsibility portfolio includes two fourth-phase core USR programs and six USR Hub programs across international/bilingual education, intergenerational technology/health, cultural preservation, digital heritage, agriculture, health/food safety, humanitarian assistance and circular economy.

Sources:
https://www.yzu.edu.tw/index.php/tw/social
https://esdg.yzu.edu.tw/media/attachments/2026/04/01/114--6-65.pdf

These teams are better pilot candidates than generic cold outreach because they already have:
- external field partners;
- students and faculty;
- recurring unresolved operational/research needs;
- project budgets/staff;
- reporting obligations;
- incentives to demonstrate social impact.

### 5. Impact reporting / SROI — institutional reporting value

YZU is currently using SROI in fourth-phase USR impact evaluation and has published a dedicated 114-year evaluation framework. Problem Commons should not replace SROI. It can provide better upstream provenance for what problem existed, what work happened, what changed, and what evidence supports the claimed outcome.

Source:
https://esdg.yzu.edu.tw/media/attachments/2026/03/04/114-yzu-usr-sroi-report.pdf

## First live conversion case

Source: YZU Field Matching — `桃園中壢 | 課後輔導班學習支持` / 永豐靈糧堂課後輔導班.

The public listing reports:
- 14 primary-school children currently served;
- concern about increased learning-support demand as several children enter junior high;
- demand for one-to-one/small-group support;
- recurring tutoring and short English/science/programming activities as possible collaboration modes;
- stable venue, instructors, class management and child-safety procedures;
- weekday operating windows.

The source also leaves important unknowns:
- whether the need is still current;
- actual tutoring-capacity gap;
- learning/outcome baseline;
- preferred collaboration mode;
- compensation/funding state;
- geographic inconsistency between the page heading and listed street address.

Repository intake:
`pilot/intake/yzu-yongfeng-after-school.v0.1.json`

This intake is **not owner-confirmed**. It must stay candidate/restricted and all proposed child-facing work stays blocked until owner/safeguarding review.

## Pilot owner queue

Priority order:

### Tier 0 — institutional operator

**YZU Sustainability Development and Social Responsibility Center**

Ask for a bounded pilot using existing field-matching/USR demand rather than asking for a platform purchase.

Pilot ask:
- nominate 3 problem owners / field partners;
- provide 5-10 raw needs/listings;
- allow Commons to return owner-review packs and Project Briefs;
- no public launch requirement;
- no integration requirement in cycle 1.

### Tier 1 — current core USR programs

1. **寰宇文化領航** — deep-rooted international/bilingual education program; current public materials identify 黃郁蘭 as project lead.
2. **跨代智慧共創：設計思考引領科技與幸福** — intergenerational AI/IoT/education/health program; high fit for multiple research/engineering subproblems.

Use these as repeat-owner tests because each already contains multiple field partners and workstreams.

### Tier 2 — USR Hub programs

- 文化織影：龍岡地區多元文化傳播與產業創新
- 永續共創，百年大溪之數位雙生
- 永續農田共生未來
- 全齡健康促進與食品安全
- 亞洲國際人道援助
- 綠色循環經濟 / 衣循智選

The objective is not to onboard all six. Select whichever teams can provide an unresolved condition plus an owner willing to review the resulting Problem.

### Tier 3 — external field owners

Start with existing field-matching listings because the owner has already expressed a need to YZU. Do not infer Problem Commons consent; request confirmation through the Center/owner before publication or solver work.

## First-cycle operating sequence

1. **Ingest** raw owner statement/listing into `problem-owner-intake/v0.1`.
2. **Generate** candidate/restricted Problem Packet automatically.
3. **Owner review**: current/stale? correct/misframed? missing constraints? preferred outcome?
4. **Curator reframe** and admit only surviving Problems.
5. **Classify work** using Commons Stage Profiles.
6. **Generate Project Briefs** with effort, skills, credentials, outputs, funding/volunteer state and reviewer.
7. **Choose distribution lane**: social-participation funding, course/service-learning, independent project, RA, USR team, or later sponsored work.
8. **Solver attempt** with minimum founder coaching.
9. **Owner/reviewer acceptance** of useful outputs.
10. **Record continuation**: new work, next stage, capability reuse, or close/reframe.

## Hard conversion metrics

First owner cohort:
- >=3 independent problem owners;
- >=10 raw needs received;
- >=5 owner-confirmed/reframed Problems survive;
- median curator time per surviving Problem recorded;
- >=1 owner supplies a second Problem/continuation.

First solver cohort:
- >=20 independent sessions;
- >=5 serious attempts;
- >=2 outputs judged useful/accepted by an external owner/reviewer;
- coaching burden recorded explicitly.

Economic proof:
- >=1 Project uses an existing YZU funding/course/USR/sponsor/in-kind path;
- a resource match is not counted until a real award/commitment/support receipt exists.

Compounding proof:
- >=1 later Problem searches for and reuses a capability from an earlier Problem;
- compare search+adaptation cost against rebuild estimate.

## Pitch boundary

Do not pitch:
- a global marketplace;
- autonomous problem solving;
- replacement for YZU's USR system;
- replacement for SROI;
- grant database;
- guaranteed student participation;
- guaranteed funding.

Pitch the smallest verifiable value:

> "You already collect real field needs and run social-participation/USR projects. We can test whether a structured Problem layer makes those needs easier to verify, decompose, match to students/researchers, resource, review and carry forward across semesters—while preserving the evidence needed for impact reporting."

## Stop/build rule

Do not add another core ontology or marketplace subsystem during this pilot unless a real owner/solver workflow cannot be completed without it. Every new feature must point to a recorded conversion failure it fixes.
