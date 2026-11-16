# Performance Under Pressure in T20 Cricket: Methodology & Rajasthan Royals IPL 2027 Auction Strategy

[![GitHub Pages](https://img.shields.io/badge/Live_Dashboard-GitHub_Pages-d81b60?style=for-the-badge&logo=github)](https://github.com)
[![Methodology Report](https://img.shields.io/badge/Report-Publication_PDF-1a237e?style=for-the-badge&logo=adobeacrobatreader)](docs/methodology_report.pdf)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Matches Analyzed](https://img.shields.io/badge/Matches-842-059669?style=for-the-badge)](#)
[![Deliveries Analyzed](https://img.shields.io/badge/Deliveries-199%2C029-2563eb?style=for-the-badge)](#)

A publication-grade sports analytics system that measures how batters and bowlers perform in high-pressure match situations compared with their baseline levels across **842 matches** and **199,029 regular deliveries** in the **IPL (2022–2026)** and **T20 Internationals (2022–2026)**.

---

## 🌐 Live Interactive Dashboard & Reports

* **Live GitHub Pages Dashboard:** [View Live Interactive Dashboard](https://github.com)
* **Publication-Grade Methodology Report (PDF):** [`docs/methodology_report.pdf`](docs/methodology_report.pdf) *(1.69 MB, exactly 9 pages, print-optimized)*
* **Interactive Methodology Report (HTML):** [`docs/methodology_report.html`](docs/methodology_report.html)
* **Full Markdown Report:** [`docs/methodology_report.md`](docs/methodology_report.md)
* **Master Bowlers Rankings (CSV):** [`rankings/rankings_bowlers_master.csv`](rankings/rankings_bowlers_master.csv)
* **Master Batters Rankings (CSV):** [`rankings/rankings_batters_master.csv`](rankings/rankings_batters_master.csv)

---

## 📐 The 5-Pillar Architectural Framework

1. **Phase-Normalized Dynamic Pressure Index (P-NPI):**
   $$\text{P-NPI} = S_{\text{wkt}}^{\text{phase}} + S_{\text{rr}} + 15.0$$
   * Normalizes crisis states per match phase: losing 2 wickets inside the Powerplay awards **40 crisis points**, recognizing that facing new-ball swing during early collapses is an acute pressure state.
   * Eliminates death-overs finisher bias, providing top-order anchors hundreds of verified crisis deliveries.
   * $\text{P-NPI} \ge 50$ defines **High Pressure (HP)**, accounting for **34.3% of all deliveries**.
2. **Competition Tier Weighting ($W_{\text{tier}}$):**
   * Prevents associate league anomalies from outranking multi-season elite competition:
     * IPL Matches: **1.30x**
     * Tier-1 Bilaterals & ICC World Cups: **1.10x**
     * Associate Tournaments: **0.75x**
3. **Cumulative Value Above Replacement:**
   * **High-Pressure Runs Saved (Bowlers):** Run suppression below the global high-pressure benchmark of **8.03 rpo**.
   * **High-Pressure Runs Added (Batters):** Run generation above the global high-pressure benchmark of **126.4 strike rate**.
4. **Resistance to Drop-Off (Anti-Fragility):**
   * $\text{Drop-Off}_{\text{bat}} = \frac{\text{HP Strike Rate}}{\text{LP Strike Rate}}$ ($> 1.0$ indicates positive acceleration under pressure).
   * $\text{Drop-Off}_{\text{bowl}} = \frac{\text{LP Economy}}{\text{HP Economy}}$ ($> 1.0$ indicates tighter suppression under crisis).
5. **Dual Master & Role-Segregated Dropdown Leaderboards:**
   * Provides both a global Master Top 10 and dedicated positional rankings (Top-Order Anchors, Middle-Order Engines, Death Finishers; Powerplay Bowlers, Middle Spin/Choke, Death Specialists).

---

## 🏆 Master Top 10 Rankings

### Master Top 10 High-Pressure Bowlers
*Global High-Pressure Bowling Economy Benchmark: **8.03 rpo**.*

| Rank | Player | Matches | Balls Bowled | Overall Econ | HP Balls | HP Econ *(vs 8.03 avg)* | Drop-Off Ratio | HP Runs Saved | Primary Role | Pressure Rating |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---:|
| **1** | **Sunil Narine** | 67 | 1,553 | 6.92 | 608 | **6.08** | 1.31 | **+257.2** | Middle-Overs Choke / Spin | **100.0** |
| **2** | **Jasprit Bumrah** | 75 | 1,780 | 7.16 | 860 | **6.75** | 0.57 | **+224.5** | Powerplay Strike Bowler | **96.5** |
| **3** | **Rashid Khan** | 122 | 2,780 | 7.48 | 1,277 | **7.17** | 0.72 | **+205.5** | Middle-Overs Choke / Spin | **93.0** |
| **4** | **Mitchell Santner** | 83 | 1,793 | 7.30 | 789 | **6.23** | 1.04 | **+276.0** | Middle-Overs Choke / Spin | **91.5** |
| **5** | **Varun Chakravarthy** | 95 | 2,182 | 7.94 | 1,069 | **7.14** | 0.86 | **+191.1** | Middle-Overs Choke / Spin | **86.0** |
| **6** | **Kuldeep Yadav** | 89 | 1,965 | 7.87 | 782 | **6.89** | 1.10 | **+180.9** | Middle-Overs Choke / Spin | **83.5** |
| **7** | **Akeal Hosein** | 79 | 1,734 | 7.60 | 612 | **6.75** | 1.18 | **+146.9** | Middle-Overs Choke / Spin | **78.0** |
| **8** | **Axar Patel** | 136 | 2,707 | 7.88 | 1,154 | **7.51** | 0.86 | **+117.3** | Middle-Overs Choke / Spin | **73.0** |
| **9** | **Mustafizur Rahman** | 71 | 1,646 | 7.62 | 884 | **7.27** | 0.40 | **+113.7** | Death Overs Specialist | **71.0** |
| **10** | **Shaheen Shah Afridi** | 47 | 1,036 | 7.89 | 526 | **6.83** | 0.52 | **+106.9** | Powerplay Strike Bowler | **68.5** |

---

### Master Top 10 High-Pressure Batters
*Global High-Pressure Batting Strike Rate Benchmark: **126.4**.*

| Rank | Player | Matches | Balls Faced | Overall SR | HP Balls | HP SR *(vs 126.4 avg)* | Drop-Off Ratio | HP Runs Added | Primary Role | Pressure Rating |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---:|
| **1** | **Tim David** | 98 | 1,293 | 168.4 | 735 | **166.1** | 0.97 | **+364.9** | Death Finisher | **100.0** |
| **2** | **Suryakumar Yadav** | 139 | 2,848 | 161.1 | 1,061 | **150.3** | 0.88 | **+316.7** | Middle-Order Engine | **94.2** |
| **3** | **Nicholas Pooran** | 115 | 2,091 | 148.2 | 957 | **148.2** | 0.94 | **+269.9** | Middle-Order Engine | **88.5** |
| **4** | **David Miller** | 81 | 1,338 | 142.8 | 764 | **150.4** | 1.04 | **+241.0** | Middle-Order Engine | **85.0** |
| **5** | **Andre Russell** | 57 | 785 | 159.7 | 537 | **160.0** | 1.15 | **+235.9** | Middle-Order Engine | **84.2** |
| **6** | **Heinrich Klaasen** | 72 | 1,480 | 159.7 | 634 | **152.7** | 0.84 | **+223.0** | Middle-Order Engine | **82.5** |
| **7** | **Rovman Powell** | 100 | 1,651 | 138.6 | 1,005 | **144.1** | 1.07 | **+220.4** | Middle-Order Engine | **81.9** |
| **8** | **Dinesh Karthik** | 61 | 683 | 156.5 | 468 | **157.7** | 0.80 | **+190.1** | Death Finisher | **76.5** |
| **9** | **Naman Dhir** | 46 | 603 | 164.5 | 262 | **180.9** | 1.25 | **+176.4** | Middle-Order Engine | **74.0** |
| **10** | **Abhishek Sharma** | 134 | 2,436 | 177.8 | 472 | **156.4** | 0.83 | **+173.6** | Top-Order Anchor / PP | **73.5** |

---

## 🎯 Rajasthan Royals IPL 2027 Auction Strategy

### Tactical Gaps & Reinforcement Matrix
1. **Mitchell Santner (Priority 1 — Spin Choke & Batting Depth):** Concedes an elite 6.23 rpo under pressure (+276.0 runs saved). Provides the exact middle-overs spin restriction needed on the large square boundaries of Sawai Mansingh Stadium (Jaipur), with lower-order batting at #8.
2. **Tim David (Priority 1 — Death Finisher):** Striking at 166.1 under acute crisis (+364.9 runs added). Slots at #6 alongside Shimron Hetmyer and Dhruv Jurel to eliminate late-chase stalling.
3. **Mustafizur Rahman / Matheesha Pathirana (Death Bowling Masters):** Solves RR's death leakage (overs 17–20) alongside Sandeep Sharma.
4. **Naman Dhir (Domestic Target):** Highest crisis acceleration in India (180.9 HP SR, 1.25 Drop-Off ratio).

### Projected "Pressure-Proof" Playing XI (IPL 2027)
1. **Yashasvi Jaiswal** (Retained • 170.7 HP SR • Anti-Fragile)
2. **Phil Salt / Jos Buttler** (Target/Retained • 164.4 HP SR Enforcer)
3. **Sanju Samson (C & WK)** (Retained • Franchise Anchor)
4. **Riyan Parag** (Retained • Middle Phase Spin Destroyer)
5. **Naman Dhir / Shimron Hetmyer** (Target/Retained • 180.9 HP SR Accelerator)
6. **Tim David** (Auction Target • Rank 1 Finisher, +364.9 runs)
7. **Dhruv Jurel** (Retained • Death Runner & Finisher)
8. **Mitchell Santner** (Auction Target • Rank 4 Bowler, +276.0 runs saved)
9. **Sandeep Sharma** (Retained • Elite Yorker Specialist)
10. **Mustafizur Rahman / Matheesha Pathirana** (Auction Target • 7.27 HP Econ)
11. **Avesh Khan / Kuldeep Sen** (Retained/Target • Express Hit-the-Deck)

---

## 📁 Repository Structure

```
├── index.html                   # Live Interactive Dashboard (GitHub Pages Entrypoint)
├── docs/                        # GitHub Pages Deployment Directory
│   ├── index.html               # Mirrored interactive dashboard
│   ├── methodology_report.html  # Interactive Methodology Report
│   ├── methodology_report.pdf   # Publication-grade 9-page PDF report
│   ├── methodology_report.md    # Markdown report source
│   ├── charts/                  # High-resolution analytical figures
│   └── rankings/                # CSV leaderboards
├── src/                         # Python Pipeline Source Code
│   ├── data_loader.py           # Ball-by-ball ingestion & match mapping
│   ├── pressure_index.py        # P-NPI mathematical model
│   ├── player_metrics.py        # Value above replacement calculations
│   ├── generate_final_solution.py
│   ├── generate_aesthetic_report.py
│   └── update_all_formal.py
├── charts/                      # Exported visualization figures
├── rankings/                    # Master & role-segregated CSV files
├── .gitignore                   # Standard clean gitignore
└── README.md                    # Project documentation
```

---

## 🚀 Running the Pipeline Locally

```bash
# 1. Install dependencies
pip install pandas numpy matplotlib

# 2. Run the full pressure system & generate reports
python3 src/generate_final_solution.py

# 3. Update formal reports & PDF
python3 src/update_all_formal.py
```

Published by **Antigravity Cricket Research** • Based on 199,029 regular deliveries across 842 matches.
