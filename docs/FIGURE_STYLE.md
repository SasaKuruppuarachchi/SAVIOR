# SAVIOR figure style (follow the original JSEN paper)

All paper figures and graphs follow the style of the original paper's plots
(`ref/savior_paper/IEEE-JSEN-paper/figures/plots/`). Apply it with
`plt.style.use(<repo>/savior_eval/savior_eval/paper.mplstyle)`.

## Look
- **Background and fonts:** plain matplotlib on a white background, with a black full box frame (all four spines) and **no grid**. Sans-serif font (DejaVu Sans, matplotlib's default).
- **Labels:** each panel gets a short title in title case, e.g. "Root Mean Squared Error", "Relative Position Error". Axis labels are lower or sentence case with units in parentheses, e.g. `Error Position (m)`, `orientation error (deg)`, `sub-segment lengths (m)`, `dataset time (s)`.
- **Layout:** stacked panels share one x-axis meaning. Orientation goes on top and position below; the shared x label appears once, under the bottom panel.
- **Legends:** inside the axes, with a light rounded frame, top-centre or upper-left. Legend entries are short line samples.

## Colours (one fixed colour per method)
| method | colour |
|---|---|
| OpenVINS (baseline) | `blue` |
| SAVIOR (proposed, full) | `red` |
| ablation / naive / other variant | `black`, then `green`, `magenta`, `orange` |
| ground truth | `black` (thin) |

Use named pure colours as in the original, not a pastel palette. Keep the same colour for the same method in every figure of the paper.

## Scope: look vs content
The **visual identity** above is fixed: frame, no grid, fonts, and the colour per method. The **plot types and analyses are not limited to the original paper**. Use whatever current VIO and dynamic-SLAM publications use when it communicates the result better. Examples:
- **Success / robustness:** a cumulative distribution of ATE across all runs and sequences, i.e. the success-rate-vs-threshold curves used in recent robustness benchmarks; and failure-rate bars per dynamic level.
- **Many runs:** violin or strip (swarm) plots of per-offset ATE, paired-difference plots (per-run lines connecting baseline → method), and forest plots of effect size with 95 % CI per sequence/level.
- **Cross-sequence summaries:** heatmaps of relative ATE change (method × sequence) with a diverging blue–white–red map; and trend lines over dynamic level.
- **Mechanism plots:**
  - dynamic-share vs gain scatter with a fit and rho;
  - feature-fate stacked bars (used / chi²-rejected / triangulation-failed);
  - a feature-budget vs ATE scatter;
  - onset-latency histograms.
- **Trajectories:** top-down paths coloured by local error, plus the classic GT/OpenVINS/SAVIOR overlay.
- **System:** a per-stage timing breakdown (stacked bars, desktop vs Orin NX), an accuracy–runtime Pareto plot against other methods, and memory footprint.
- **Qualitative:** mask-overlay grids (raw / oracle / naive / SAVIOR) with a consistent overlay colour per mask class.

The classic plot types below stay available and should keep their original look.

## Plot types (classic, from the original paper)
- **Error over time (ATE / RMSE vs time):**
  - the mean is a solid line;
  - the Monte Carlo ±2σ bounds are **dotted lines in the same colour**, not filled bands.
- **RPE vs sub-segment length:**
  - **notched box plots**, unfilled, with box, whiskers and median all in the method colour;
  - grouped side by side per segment length;
  - no outlier markers (`showfliers=False`);
  - x ticks at the segment lengths.
- **Trajectories:** per-axis position (and yaw) vs time panels, plus a top-down XY panel. Ground truth thin black, OpenVINS blue, SAVIOR red with a thicker line.
- **Multi-scenario figures:** subfigure captions "(a) …", "(b) …" under the panels, as in the paper.

## Export
- PNG at 300 dpi for drafts and PDF (vector) for the paper.
- A single-column figure is about 3.5 in wide; a double-column figure is about 7.16 in wide.
- Size fonts so that they read at 8–9 pt after scaling into the column.
