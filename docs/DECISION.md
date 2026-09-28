# Operational Decision Thresholds & Multi-Tier Escalation Protocol

> [!WARNING]
> **Synthetic Data Disclosure**: All decision thresholds, alert burden figures, and cross-validation numbers in this document are derived and evaluated on **physics-simulated synthetic data** (grounded in real geographic profiles of Uttarkashi district, Uttarakhand). No operational historical landslide sensor records were fabricated.

---

## 1. Operational Tier Architecture

The Early Warning System translates continuous calibrated landslide probabilities into four discrete operational decision tiers aligned with **National Disaster Management Authority (NDMA)** and **National Disaster Response Force (NDRF)** emergency response ladders:

```
[Normal Operations] ----> [WATCH (Yellow)] ----> [WARNING (Orange)] ----> [EVACUATE (Red)]
                          Top 2.0% Risk         Top 0.5% Risk           Top 0.1% Conformal Gated
                          (Preparedness)        (Staging / Pre-position) (Immediate Movement)
```

| Decision Tier | Target Population Burden | Trigger Mechanism | Operational Meaning & Immediate Directives |
| :--- | :--- | :--- | :--- |
| **NONE** | Bottom 98.0% | $P < P_{\text{watch}}$ | Normal conditions. Background weather and sensor ingestion active. |
| **WATCH** (Advisory) | Top 2.0% ($P \ge 0.0146$) | $P \ge P_{\text{watch}}$ | **Situational Preparedness**: District Emergency Operation Centre (DEOC) alerted; field volunteers monitor high-risk slopes and drainage channels. |
| **WARNING** (Alert) | Top 0.5% ($P \ge 0.0180$) | $P \ge P_{\text{warning}}$ | **Active Staging**: NDRF / SDRF units pre-positioned; shelter managers prepare facilities; vulnerable households notified via SMS/IVR. |
| **EVACUATE** (Action) | Top 0.1% ($P_{\text{lower}} \ge 0.1509$) | $P_{\text{lower}} \ge P_{\text{evacuate}}$ | **Immediate Evacuation**: Multi-channel sirens, cell broadcasts, and door-to-door volunteer sweeps activated. Citizens move along designated evacuation routes to safe shelters. |

---

## 2. Derivation of Calibration-Split Percentile Thresholds

In severe class-imbalance regimes (~0.16% base rate prevalence), conventional classification thresholds (e.g. 0.50 or 0.80) are fatal design flaws: an isotonic-calibrated model outputs a median probability $< 0.002$ and a 99th percentile $\approx 0.018$. Under fixed $P \ge 0.50$, the system would remain silent across all monsoon emergencies.

Therefore, operational decision thresholds are derived strictly from the **empirical quantiles of the time-ordered 2022 calibration split** (175,200 hourly instances across 20 training settlements):

$$\begin{aligned}
P_{\text{watch}} &= Q_{98.0}(P_{\text{calib}}) = \mathbf{0.014637} \quad (\text{Top } 2.0\% \text{ risk density}) \\
P_{\text{warning}} &= Q_{99.5}(P_{\text{calib}}) = \mathbf{0.018041} \quad (\text{Top } 0.5\% \text{ risk density}) \\
P_{\text{evacuate}} &= Q_{99.9}(P_{\text{calib}}) = \mathbf{0.150943} \quad (\text{Top } 0.1\% \text{ risk density})
\end{aligned}$$

---

## 3. Conformal Lower-Bound Gating for Evacuation Escalation

False alarms in early warning systems incur severe penalties: alert fatigue causes public non-compliance ("crying wolf"), while unwarranted community evacuations cause economic disruption, transport hazards, and shelter overcrowding.

To prevent erratic spikes from triggering irreversible evacuations, the system enforces **Conformal Lower-Bound Gating**:

$$\text{Tier} = \begin{cases}
\mathbf{EVACUATE}, & \text{if } P_{\text{lower}} \ge P_{\text{evacuate}} \\
\mathbf{WARNING}, & \text{if } P_{\text{calibrated}} \ge P_{\text{warning}} \quad (\text{and } P_{\text{lower}} < P_{\text{evacuate}}) \\
\mathbf{WATCH}, & \text{if } P_{\text{calibrated}} \ge P_{\text{watch}} \quad (\text{and } P_{\text{calibrated}} < P_{\text{warning}}) \\
\mathbf{NONE}, & \text{otherwise}
\end{cases}$$

### Why Conformal Lower-Bound Gating is Essential:
1. **Uncertainty-Gated Action**: Point probability estimates $P_{\text{calibrated}}$ can be inflated by epistemic noise in extreme, unseen storm conditions.
2. **Guaranteed Conservatism**: An evacuation order is issued only when the non-parametric Venn-Abers **lower bound** $P_{\text{lower}}$ exceeds the critical threshold ($P_{\text{lower}} \ge 0.1509$). If the model is uncertain (wide interval $[0.08, 0.22]$), the system holds at **WARNING**, staging emergency responders without needlessly displacing vulnerable villagers.

---

## 4. Test Set Alert Burden & Operational Verification

Evaluated strictly out-of-sample on the **2023 holdout test set** (43,800 hourly records across 5 unseen settlements: `VIL_UTK_21` to `VIL_UTK_25`):

### Discrete Tier Counts (43,800 Hours)
- **EVACUATE**: 44 hours (0.10% of total hours)
- **WARNING**: 285 hours (0.65% of total hours)
- **WATCH**: 307 hours (0.70% of total hours)
- **NONE**: 43,164 hours (98.55% of total hours)

### Cumulative Operational Alert Burden & Skill

| Operational Level | Criteria | Alerts Fired (5 Villages, 2023) | Alert Burden (Alerts / Village / Year) | True Positives (TP) | False Alarms (FP) | Missed Events (FN) | Cumulative POD (Recall) | Cumulative FAR (False Alarm) | Critical Success Index (CSI) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EVACUATE** | $P_{\text{lower}} \ge 0.1509$ | **44** | **8.8** | 18 | 26 | 72 | 20.00% | **59.09%** | **0.1552** |
| **WARNING** | $P \ge 0.0180 \lor \text{Evac}$ | **329** | **65.8** | 32 | 297 | 58 | 35.56% | **90.27%** | **0.0827** |
| **WATCH** | $P \ge 0.0146 \lor \text{Warn}$ | **636** | **127.2** | 40 | 596 | 50 | 44.44% | **93.71%** | **0.0583** |

### Key Operational Insights:
1. **Dramatic FAR Reduction via Conformal Gating**: At the WATCH tier, False Alarm Ratio is 93.71%. At the WARNING tier, FAR is 90.27%. However, when escalating to EVACUATE using conformal lower-bound gating ($P_{\text{lower}} \ge 0.1509$), the False Alarm Ratio plummets to **59.09%**, and CSI peaks at **0.1552** (a 2.6x improvement over WATCH).
2. **Realistic Operational Alert Load**: High-level EVACUATE sirens fire on average only **8.8 hours per village per year** (~1 to 2 distinct monsoon storm episodes), preventing alert fatigue while successfully catching the peak danger hours.
3. **Escalation Hierarchy**: WATCH captures 44.4% of pre-failure storm hours well in advance (127 hours/village/year), providing ample window for staged disaster mobilization before immediate evacuation sirens are sounded.

---

## 5. Per-Village Bayes-Optimal Cost Modeling & Assumptions

A single uniform threshold across an entire mountainous district assumes identical societal vulnerability and disruption costs across all settlements. In reality, a remote hilltop hamlet with difficult terrain faces high evacuation disruption, whereas a riverside settlement with concentrated vulnerable citizens faces severe life-safety consequences from missed warnings.

### 5.1 Relative Societal Cost Assumptions

> [!IMPORTANT]
> **Explicit Assumption Disclosure**:  
> The cost formulas below represent **relative dimensionless modeling units**, NOT monetary values, currency figures, or official insurance assessments. They reflect explicit operational risk weights chosen to represent relative harms.

For each village $v$, the relative loss functions are defined as:

$$\begin{aligned}
C_{\text{miss}}(v) &= \Big(\text{Population} \times 1.0 + \text{Vulnerable Population} \times 2.5\Big) \times \Big(1.0 + f_{\text{slope}} + f_{\text{stream}}\Big) \\
C_{\text{false\_alarm}}(v) &= \text{Population} \times \Big(0.05 + 0.10 \times \text{Fatigue Rate} + f_{\text{disruption}}\Big)
\end{aligned}$$

Where:
- **Demographic Vulnerability Weight (2.5x)**: Prioritizes settlements with higher concentrations of elderly, disabled, or isolated residents.
- **Hillslope Terrain Factor ($f_{\text{slope}}$)**: $f_{\text{slope}} = 1.0 + \max\left(0.0, \frac{\text{Slope} - 25^\circ}{15^\circ}\right)$. Steep slopes ($>25^\circ$) amplify gravitational shear velocity and runout hazard.
- **Fluvial Proximity Factor ($f_{\text{stream}}$)**: $f_{\text{stream}} = 1.0 + \max\left(0.0, \frac{100\text{m} - \text{Distance to Stream}}{100\text{m}}\right)$. Settlements within 100m of active drainage channels face heightened debris-flow toe scour.
- **Historical Alert Fatigue Rate**: Baseline $0.20$, representing compliance degradation from past false alarms.
- **Evacuation Disruption Index ($f_{\text{disruption}}$)**: Measures physical difficulty of evacuation (e.g. $0.12$–$0.15$ in high-altitude remote settlements vs $0.08$ in accessible valley settlements).

### 5.2 Bayes-Optimal Decision Threshold ($p^*$)

Under expected utility theory, the optimal threshold $p^*$ minimizing expected societal loss satisfies:

$$p^*_{\text{raw}} = \frac{C_{\text{false\_alarm}}}{C_{\text{false\_alarm}} + C_{\text{miss}}}$$

Because isotonic-calibrated probabilities on rare events (~0.16% base rate) are small, unconstrained thresholds could trigger continuous alerts or remain silent. The operational threshold is clipped to:

$$p^* = \text{clip}\Big(p^*_{\text{raw}}, \quad 0.005, \quad 0.250\Big)$$

### 5.3 Annual Alert Burden Constraint

To guarantee operational feasibility for emergency responders, each village has a configurable cap on maximum annual alert episodes ($B_{\text{max}}$, default: 15 episodes/year). If historical calibration-split probabilities produce alerts exceeding $B_{\text{max}}$, the threshold is adjusted upward to the $(1 - B_{\text{max}} / 8760)$ empirical quantile.

---

## 6. Episode-Level Evaluation Framework

In real-world emergency management, responders and communities do not treat consecutive alert hours as isolated, independent events. Alerts separated by short lulls are part of a continuous **emergency episode**.

### 6.1 Consecutive Alert Episode Merging (Gap $\le$ 6 Hours)
- Consecutive alert hours with an inter-alert interval $\le 6$ hours are merged into a single coordinated emergency episode $[t_{\text{start}}, t_{\text{end}}]$.
- The active protection window extends to $t_{\text{end}} + 6\text{h}$ (matching the 6-hour prediction lead time).
- **Hit (True Positive Episode)**: A ground truth landslide failure occurring within $[t_{\text{start}}, t_{\text{end}} + 6\text{h}]$ marks the episode as a hit.
- **False Alarm Episode**: An alert episode with zero landslide failures within its window.
- **Lead Time**: Computed as $(t_{\text{landslide\_event}} - t_{\text{alert\_start}})$ in hours for all detected failure episodes.

---

## 7. Administrative API & Audit Logging

District emergency administrators can inspect and adjust per-village operational thresholds via dedicated REST endpoints:
- `GET /api/v1/thresholds/{village_id}`: Retrieves active thresholds, relative cost parameters, and modification audit history.
- `PUT /api/v1/thresholds/{village_id}`: Adjusts thresholds with strict Pydantic range validation ($0.001 \le p \le 0.999$, $\text{watch} < \text{warning} < \text{evacuate}$, $\text{cost} > 0$).
- **Audit Trail**: Every modification logs `modified_by`, timestamp, operational reason, previous values, and updated values in an immutable JSON history log.

