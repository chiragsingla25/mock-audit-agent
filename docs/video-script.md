# Mock Audit Agent — 2-minute walkthrough (script)

Target length: 2:00. Screen recording of the local app and the showcase, with a voiceover. Timings are approximate.

**0:00–0:15 · The problem**
*Screen: showcase home.*
"Before a SOC 2 Type II audit, teams find out what the auditor will flag only when fieldwork starts. This is a mock auditor that predicts those exceptions early, from the same evidence, and shows its work."

**0:15–0:35 · How it works**
*Screen: the architecture diagram in the README.*
"Code runs every check on the full population, so counts, dates and severity are never left to a model. A cheap Qwen model judges what code flags, using three tools: read a record, read a policy, ask the control owner. A DeepSeek model from a different family challenges every finding. Then a person approves or dismisses."

**0:35–1:05 · Running an audit**
*Screen: local app. Start an audit on Ledgerly base, and the 12 control cards progress.*
"Twelve controls across a fictional company's year of evidence: offboarding, access reviews, change management, vulnerability SLAs. It takes a few minutes and costs about a cent and a half."
*Open C2-timeliness.*
"Two terminated users kept access past 24 hours. One left on a Friday at 6pm and was suspended Monday at 9am, 63 clock hours. Here are the HR and Okta rows it cited, and every step it took."

**1:05–1:25 · Judgment, not just rules**
*Screen: the "Not raised" list, then C2-timeliness-E1083.*
"Rules alone flag this person too. The agent checked the records, found an employee-to-contractor conversion the policy explicitly allows, and dismissed it with a citation. There are four traps like this; the agent dismissed all four."

**1:25–1:45 · Measured, not asserted**
*Screen: the comparison table on the showcase.*
"Every run is scored by code against an answer key with ten planted gaps. The agent found every gap in every run, with no false positives, across three datasets and three repeat runs. A rules-only baseline found eight of ten and raised all four traps."

**1:45–2:00 · Close**
*Screen: the report with "Not an audit opinion".*
"It's a readiness forecast, never an audit opinion: there's no pass badge. The data is synthetic, and the next step is a practitioner's review. Code, evaluation and every published run are linked below."
