# Research — Mock Audit Agent

Compiled 2026-10-14; restructured by kickoff 2026-10-15. Evidence behind [handover.md](handover.md) and [PRD.md](PRD.md).
---

## 1. Domain primer

### 1.1 Audit landscape

An audit is an independent check that a claim is true ("our numbers are accurate", "we protect your data") so others can rely on it without checking it themselves.

**Why companies get audited**

- **Customers demand it.** Enterprise buyers ask SaaS vendors for a SOC 2 report before signing. This is the biggest driver in Hyperproof's market.
- **Law and regulation.** Audited financials for public companies; mandatory rules in health, finance, payments and government.
- **Investors, boards and insurers** want assurance against fraud, breaches and surprises.
- **Finding problems early.** Internal audit catches weak controls before a regulator, attacker or customer does.

**By who performs it**

| Type | Who | Purpose |
| --- | --- | --- |
| Internal audit | Company's own audit team, reporting to the board's audit committee | Find and fix weaknesses; no public report |
| External audit | Independent outside firm | An opinion outsiders can trust |
| Regulatory audit | Government regulator | Check legal compliance; can lead to fines |

**By what is examined:** financial, compliance/IT/security (Hyperproof's world), operational, plus tax, ESG, quality and others.

**Compliance audits Hyperproof customers face**

| Audit | Proves | Performed by | Asked for by |
| --- | --- | --- | --- |
| SOC 2 (Type I / II) | Customer data is protected; controls operate | Licensed CPA firms only | B2B customers, mainly US |
| SOC 1 | Controls over customers' financial reporting work | CPA firms | Customers' financial auditors |
| ISO 27001 | A security management system is in place (certification) | Accredited certification bodies | Customers, especially Europe and Australia |
| PCI DSS | Card payment data is protected | Qualified Security Assessors | Card networks, processors |
| HIPAA | Health data is protected | Consultants or CPA firms (no official certification) | US healthcare clients |
| FedRAMP | Cloud service safe for US government | Accredited 3PAOs | US federal agencies |
| CMMC | Defence contractors protect sensitive data | Accredited C3PAOs | US Department of Defense |

Companies usually face several of these each year with heavily overlapping evidence. Hyperproof's core value is mapping evidence once and reusing it. The Mock Audit Agent is the internal dress rehearsal before the CPA firm arrives.

---

### 1.2 Controls

A **control** is a specific, testable thing a company does to reduce a risk: who does what, how often, and what proof it leaves.

| Layer | Example |
| --- | --- |
| Risk | A former employee keeps access and steals data |
| Requirement (framework) | SOC 2 CC6.3: remove access when no longer needed |
| Control (company) | IT disables a leaver's accounts within 24h of HR notice |
| Evidence | HR termination list + Okta deactivation timestamps |

Controls are classified as preventive, detective or corrective; manual or automated; and by frequency (continuous, daily, weekly, quarterly, annual, or event-driven). Automated controls are tested with far fewer samples, often one. Companies typically run 50–150+ controls, and one control can satisfy several frameworks.

---

### 1.3 How a SOC 2 Type II audit works

- **SOC 2** is an AICPA attestation scored against the Trust Services Criteria. Security (Common Criteria CC1–CC9) is mandatory; Availability, Confidentiality, Processing Integrity and Privacy are optional.
- **Type I** checks controls are *designed* properly at a point in time. **Type II** also checks *operating effectiveness* across an observation period, typically 3–12 months.
- **Design gap vs operating gap:** a design gap means the control could not prevent the risk even if done perfectly; an operating gap means a well-designed control was not performed as described.
- **PBC / document request list:** the auditor's list of evidence requests.

**How auditors test a control**

1. **Inquiry:** ask the owner how it works. This alone never proves operating effectiveness.
2. **Observation:** watch it performed.
3. **Inspection:** examine evidence for a sample. System-generated records carry the most weight.
4. **Re-performance:** redo the control and compare.

**Population and sampling (the core of Type II)**

1. **Population:** every time the control should have operated in the period. It is a list, not the evidence itself, and must cover the entire period.
2. **Completeness:** checked first, often by reconciling to an independent source (e.g. HR terminations vs identity-provider deactivations). An incomplete population invalidates the sample.
3. **Sample:** sized by frequency, risk and whether the control is automated.
4. **Test each item end to end.** A failure is an **exception**; the auditor may extend the sample.

**Typical sample sizes over 12 months** (auditor judgment; ranges vary by firm)

| Control frequency | Typical sample |
| --- | --- |
| Annual | 1 |
| Quarterly | 2–4 (often all 4) |
| Monthly | 2–5 |
| Weekly | 5–15 |
| Daily / continuous | 20–40 |
| Automated (any frequency) | 1 |

**Exceptions and write-ups.** Most reports with minor exceptions still get an unqualified opinion; pervasive ones can lead to a qualified opinion. Findings follow: **condition** (what was found), **criteria** (the requirement broken), **cause**, **effect** (the risk) and **recommendation**.

**Where exceptions happen.** A 2024 benchmark study found the top causes were business approvals/reviews (16.5%), user access reviews (15.6%), terminations (12%) and change management (11.7%). Common patterns: emergency hotfixes with no ticket, and the same person writing and approving a change.

---
---

## 2. Prior-art seed

| Product | What it does | Table stakes | Overkill for this demo | UX patterns worth copying | How we differ |
| --- | --- | --- | --- | --- | --- |
| **Hyperproof** | Discover, Validate, Advise and Act agents; AI Guided Experiences (Mar 2026): Suggested Links, Evidence Collection and Validation. AI runs on Azure OpenAI | Evidence linked to controls; human approves AI output | Integrations, multi-framework crosswalks | AI suggests, user validates; actions logged per user | We extend item-level validation into a full audit simulation with measured accuracy |
| **Thoropass** (Mar 2026) | Agents that route evidence (Smart Sort), check completeness and timing (First Pass), test evidence at volume (Audit Copilot), QC deliverables (Reviewer AI); markets a "mock audit forecast" | Completeness and timing checks on evidence | An in-house audit team; attestation | A "forecast" view of audit risk before fieldwork | Theirs serves their own auditors; ours is customer-side and pre-audit, inside the GRC tool |
| **Vanta** | AI Agent (June 2025) evaluates evidence against audit requirements | Evidence evaluation against requirements | Policy drafting, questionnaires | Agent embedded across the platform | No population, sampling or auditor-style findings |
| **Drata** | AI evidence validation flags gaps before an auditor does | Gap flagging before audit | Agent governance features | Flags shown next to the control | Same as Vanta |
| **Comp AI** | Open-source compliance platform; agents collect evidence | Automated evidence collection | Device agent, 270+ integrations | Open-source, inspectable agents | Collection, not audit simulation |

**Our differentiators:** thinks in populations and samples; asks walkthrough-style follow-ups; writes findings in auditor format with cited evidence; measured accuracy (recall and precision against known gaps).
---

## 3. Novelty

**Medium.** The category exists: Thoropass markets a mock-audit forecast, and every major GRC platform now validates evidence with AI. No public tool simulates populations, sampling and auditor-style findings on the customer side **with measured accuracy**, which is the angle this demo owns. Demand signal: in Thoropass's 2026 survey, 91% said they must resubmit audit evidence at least sometimes because of miscommunication or shifting auditor expectations.
---

## 4. Data notes

**Ledgerly** (fictional B2B invoicing SaaS): about 120 employees; 30 hires and 18 terminations in the period; Okta, AWS, GitHub, Jira, a vulnerability scanner, an LMS and an HR export. Observation period 1 Jan–31 Dec 2026. About 900 production deployments, 52 weekly scans, 4 quarterly reviews, 6 incidents, 15 vendors (5 critical).

**Generated files:** `controls.yaml`, `policies/*.md`, `exports/*.csv|json` (HR roster, Okta users and system log, IAM admins, GitHub PRs, deploy log, scanner results, Jira tickets, LMS completions, vendor register), `artifacts/` (review sign-off sheets, restore test report, 2–3 screenshots), `answers.yaml` (scripted owner answers), `answer_key.yaml`.

**Planted gaps (answer key)** — severities follow the rules in [architecture.md](architecture.md) §6; control risk in brackets.

| # | Control (risk) | Planted gap | Gap type | Severity |
| --- | --- | --- | --- | --- |
| G1 | C2 (high) | 2 of 18 terminated users deactivated after 5 and 9 days | operating | high (11% > 10%) |
| G2 | C2 (high) | 1 HR termination missing from the population provided | population_completeness | high |
| G3 | C3 (high) | Q3 access review has no reviewer sign-off | missing_evidence | high |
| G4 | C5 (high) | 1 AWS admin not on the reviewed admin list | population_completeness | high |
| G5 | C6 (high) | 4 PRs merged with the author as the only approver | segregation_of_duties | high |
| G6 | C7 (moderate) | 2 hotfix deploys with no ticket or retro approval | population_completeness | moderate |
| G7 | C8 (moderate) | No scan results for 3 consecutive weeks in August | frequency_gap | moderate |
| G8 | C8 (moderate) | 1 critical vulnerability open 47 days | sla_breach | moderate |
| G9 | C10 (moderate) | 3 new hires completed training after 30 days | operating | moderate |
| G10 | C12 (moderate) | Restore test report dated before the period | evidence_out_of_period | moderate |

Controls **C1, C4, C9, C11 are clean** to test false positives.

**Noise to add (so it isn't too easy):** inconsistent name formats between HR and Okta, mixed time zones, a suspended-then-deleted account that is *not* a gap (suspension same day), an approved emergency change that *is* compliant, a scan run late in the same week (not a gap), and one realistic-looking screenshot.

---
---

## 5. Technical notes

### 5.1 Design review (2026-10-14)

- **Product:** worth building. GRC leads find exceptions early; control owners get precise asks; auditors get cleaner populations. Main people-risk is **false confidence**, so the report shows coverage and never a pass badge.
- **Technical:** code for counting and the LLM for judgment is right; mandatory citations plus a code citation check guard against invented findings.
- **LLM-as-judge bias:** judges favour outputs from their own model family. One study found judges can be over 50% more likely to wrongly pass a failing rubric item when the output is their own, and ensembling judges reduces but does not remove the bias. **So the skeptic runs on a different model family from the tester.**
- **Synthetic data:** if too clean, high recall is meaningless. Noise, clean controls and re-planted variants are essential.
- **Architecture:** schema in, schema out, async runs and registries fit well. Watch-out: don't turn five weeks into framework-building. Keep registries as plain dicts.

---

### 5.2 OpenRouter cost and limits (checked 2026-10-15)

- Example cheap tester candidate: Qwen 3.5-122B (A10B) on OpenRouter lists about US$0.26 per million input tokens and US$2.08 per million output tokens, with function calling and structured output ([source](https://www.getmaxim.ai/bifrost/llm-cost-calculator/provider/openrouter/model/qwen3.5-122b-a10b)). The architect picks the actual model.
- Free (`:free`) models: 20 requests/minute; 50/day under US$10 of lifetime credit purchases, 1,000/day at US$10 or more; failed requests can count toward the daily limit ([source](https://www.truefoundry.com/es/blog/openrouter-rate-limits-your-free-tier-depends-on-what-youve-already-paid)). Not used: Chirag chose paid cheap models throughout.
- Rough cost estimate (unmeasured): a full 12-control audit ≈ 1M input + 60k output tokens → about US$0.30–0.50 at Qwen-class prices. To be measured in the MVP notebook.
---

## 6. Sources

- [Hyperproof AI product page](https://hyperproof.io/product/hyperproof-ai/)
- [Hyperproof AI Guided Experiences press release, Mar 2026](https://www.prnewswire.com/news-releases/hyperproof-launches-ai-guided-experiences-at-rsa-conference-2026-to-transform-compliance-operations-302723168.html)
- [Hyperproof AI-native TPRM press release, Apr 2026](https://www.prnewswire.com/news-releases/hyperproof-redefines-third-party-risk-management-with-new-ai-native-evidence-based-solution-302753162.html)
- [Hyperproof press page](https://hyperproof.io/press/)
- [Thoropass: Using AI to rethink audit, Mar 2026](https://www.thoropass.com/blog/using-ai-to-rethink-some-of-audits-most-pressing-challenges)
- [Thoropass 2026 State of Audit and Compliance Report (Business Wire)](https://www.businesswire.com/news/home/20260325860369/en/Thoropass-Releases-2026-State-of-Audit-And-Compliance-Report-AI-Emerges-as-the-Top-Compliance-and-Audit-Risk)
- [Torii: 7 AI compliance tools 2026](https://www.toriihq.com/articles/seven-tools-to-manage-ai-compliance)
- [Comp AI](https://trycomp.ai/)
- [SOC 2 compliance automation history](https://guptadeepak.com/rewired/grc/compliance-automation/)
- [Best SOC 2 compliance platforms 2026](https://devtoollab.com/blog/best-soc2-compliance-automation-platforms)
- [Strike Graph: SOC 2 Type 2 population and sampling guide](https://help.strikegraph.com/articles/4056301-soc-2-type-2-population-and-sampling-guide)
- [CertPro: SOC 2 evidence requirements](https://certpro.com/?p=320534)
- [CertPro: audit sample size](https://certpro.com/?p=320357)
- [Linford & Co: test of controls](https://linfordco.com/?p=3668)
- [CBIZ: 2024 SOC benchmark study](https://www.cbiz.com/insights/article/the-evolution-of-soc-reporting-final-insights-from-the-2024-soc-benchmark-study-part-three)
- [soc2auditors.org: SOC 2 audit checklist](https://soc2auditors.org/insights/soc-2-audit-checklist)
- [Pombal et al.: Self-preference bias in rubric-based evaluation](https://arxiv.org/pdf/2604.06996)
- [Wataoka et al.: Self-preference bias in LLM-as-a-judge](https://arxiv.org/html/2410.21819v1)
- Living project doc (Claude Docs): https://claude.ai/code/artifact/cc06b2ff-8676-47d2-bdb9-3de1f130b07d
- [OpenRouter Qwen 3.5-122B pricing (getmaxim.ai)](https://www.getmaxim.ai/bifrost/llm-cost-calculator/provider/openrouter/model/qwen3.5-122b-a10b)
- [OpenRouter free-tier rate limits (TrueFoundry)](https://www.truefoundry.com/es/blog/openrouter-rate-limits-your-free-tier-depends-on-what-youve-already-paid)

