# rpg_trajectory_evaluation — Python 3 port (SAVIOR)

Original: <https://github.com/uzh-rpg/rpg_trajectory_evaluation>
(Python 2, catkin). Copyright (c) 2018 Zichao Zhang, Robotics and Perception
Group, University of Zurich. MIT License (see `LICENSE`, unchanged).
`transformations.py` (C. Gohlke, BSD) and `associate_timestamps.py`
(adapted from the TUM RGB-D benchmark, BSD) keep their original headers.

Please cite: Z. Zhang, D. Scaramuzza, *A Tutorial on Quantitative Trajectory
Evaluation for Visual(-Inertial) Odometry*, IROS 2018.

Ported from the snapshot in `savior_ws/ref/rpg_trajectory_evaluation`.
The goal is **numerically identical results** to the original; this is
checked by `test/test_parity.py`, which runs the original sources (executed
from a temporary copy under Python 3, whose arithmetic is identical here: the
original uses explicit float division / `from __future__ import division`)
next to this port on synthetic data and on the EuRoC example results shipped
with the original repository.

## Files

| Port | Original |
|---|---|
| `align_trajectory.py`, `align_utils.py`, `associate_timestamps.py`, `compute_trajectory_errors.py`, `metrics.py`, `multiple_traj_errors.py`, `plot_utils.py`, `results_writer.py`, `trajectory.py`, `trajectory_loading.py`, `trajectory_utils.py`, `transformations.py` | `src/rpg_trajectory_evaluation/*.py` |
| `fn_constants.py` | `scripts/fn_constants.py` |
| `analyze_trajectory_single.py` | `scripts/analyze_trajectory_single.py` (console script `rpg-analyze-trajectory-single`) |
| `analyze_trajectories.py` | `scripts/analyze_trajectories.py` (console script `rpg-analyze-trajectories`) |
| `_colorama_compat.py` | new (optional colorama shim) |

Not ported: `scripts/add_path.py` (replaced by package imports),
`scripts/overall_odometry_errors.py` (broken upstream: imports names that do
not exist in `analyze_trajectories.py`), `scripts/change_eval_cfg_recursive.py`,
`scripts/recursive_clean_results_dir.py`, `scripts/dataset_tools/*` (ROS 1
bag tools; SAVIOR has its own converters), catkin `CMakeLists.txt`,
`package.xml`, `setup.py`.

## Every change

All changes in the code are also marked with a `[py3 port]` comment.

### Packaging / Python 3 mechanics (no behavioural effect)
1. Shebangs `python2` → `python3`.
2. Implicit relative imports (`import transformations as tf`,
   `from metrics import ...`) → package-relative imports
   (`from . import transformations as tf`, `from .metrics import ...`).
   No `catkin`/`rospkg`/`add_path` dependency.
3. `colorama` is optional (`_colorama_compat.py`: real colorama if
   installed, otherwise no-op colour codes; `RPG_NO_COLOR=1` disables).
4. `trajectory.py`: `if suffix is not '':` → `if suffix != '':` (identity
   comparison with a literal is a SyntaxWarning in py3; same result).
5. `analyze_trajectory_single.py`: `assert len(...) is 1` → `== 1`.
6. `transformations.py`: `numpy.array(x, copy=False)` → `numpy.asarray(x)`
   (identical in numpy 1.x, required for numpy >= 2); two docstrings made raw
   strings (invalid escape warnings); doctest `print x` → `print(x)`.
7. `align_trajectory.py`: `np.linalg.linalg.svd` → `np.linalg.svd` (same
   function; `np.linalg.linalg` is private in numpy 2).
8. `plot_utils.boxplot_compare` legend: the original drew an invisible
   (`alpha=0`) dummy line per data set into the current axes as legend
   handle and later hid it with a (py3-lazy, hence never executed)
   `map(lambda x: x.set_visible(False), ...)`. With current matplotlib this
   gives invisible legend entries and the dummy points (0..1, 1) distort the
   autoscaled axes. Replaced by `matplotlib.lines.Line2D` proxy artists
   (legend only; the plotted data are unchanged).
9. `analyze_trajectories.py`: `d[...].keys()` wrapped in `list()` (py3 dict
   views are not indexable; the original indexes `algorithms[i]`);
   `ruamel.yaml` → PyYAML `safe_load` (same data, insertion order kept).

### Plotting / environment
10. `plot_utils.py`: the matplotlib `Agg` backend is selected unless
    `MPLBACKEND` is set (headless containers). `rc('text', usetex=True)` and
    the Cardo font are only enabled with `RPG_USETEX=1` (no TeX in the
    container); without usetex, the `\%` in axis labels becomes `%`
    (`plot_utils.PCT`). Same for the `rc(...)` calls that were at the top of
    the two scripts.
11. `plot_utils.boxplot_compare`: `ax.boxplot(d, 0, '', ...)` →
    `ax.boxplot(d, notch=False, sym='', ...)` (positional use deprecated in
    recent matplotlib; same meaning).
12. Scripts: the `if __name__ == '__main__':` bodies are now `main(argv)`
    functions; module globals that the original functions read from the
    `__main__` scope (`args`, `FORMAT`, `datasets`, `datasets_labels`) are
    declared `global` in `main`. In `analyze_trajectory_single.py` the
    plotting part is factored out verbatim into `plot_single_results(...)`
    (figures are additionally closed after saving). The final
    `notify-send` call is skipped if the binary is missing. When no trial
    succeeds, the single-trajectory script now skips plotting instead of
    raising `NameError`.
13. `analyze_trajectories.py`: default `--results_dir`/`--output_dir` and the
    config directory are relative to the current working directory (the
    package has no `results/` folder); `config` may also be a path.

### API additions (defaults reproduce the original)
14. `Trajectory(..., max_diff=0.02, t_offset=0.0)`: the timestamp
    association tolerance (hard-coded 0.02 s in the original) and a time
    offset (hard-coded 0.0; added to the groundtruth stamps, as in TUM
    `associate`) are now parameters, forwarded through
    `trajectory_loading.load_stamped_dataset/load_estimate_and_associate(...,
    offset=0.0)`.
15. `Trajectory` accepts `align_type` `'posyaw'` and `'none'` in the
    constructor (the original asserted `['first_frame', 'sim3', 'se3']`, so
    `posyaw`/`none` were only reachable through `eval_cfg.yaml`, which still
    takes precedence exactly as before).
16. `analyze_trajectory_single.analyze_multiple_trials(..., **traj_kwargs)`
    forwards extra keyword arguments to `Trajectory`.

### Performance (identical output, verified by tests)
17. `associate_timestamps.associate`: the original builds all N·M candidate
    pairs in pure Python (intractable for long 200 Hz groundtruth). The port
    generates only candidates inside the ±max_diff window with a sorted
    search, then applies the *same* strict `< max_difference` criterion and
    the *same* greedy order (sorted by `(diff, idx_first, idx_second)`).
    The original is kept as `associate_reference`.
18. `trajectory_utils.compute_comparison_indices_length`: the original
    O(N²) Python loop is replaced by a vectorised search over the
    (monotone) distance-from-start array that returns the same index
    (first index with the minimal distance error, strict `< max_dist_diff`);
    a per-index `argmin` fallback is used for non-monotone input. The
    original is kept as `compute_comparison_indices_length_reference`.

## Upstream behaviours deliberately kept (be aware when reporting)
- `compute_comparison_indices_length` drops start indices without a match and
  `compute_relative_error` then pairs the *compacted* list with
  `enumerate(...)` indices. This is exact when the unmatched start indices are
  the trailing ones (the normal case: the last poses cannot reach length L),
  but misaligns pairs if a gap appears mid-trajectory (GT jump > 0.4 L).
- `compute_absolute_error`'s "scale drift" uses `np.diff(p, 0)` (the
  identity), i.e. it compares distances from the world origin, not segment
  lengths. It is reported as `scale` (rpg) but not used in SAVIOR tables.
- RPE is computed on the *unaligned* estimate (relative poses are
  alignment-invariant), with the sim3 scale applied to the estimated
  relative translation. `trans_perc` divides by the nominal length L, not
  the actual GT segment length.
- Statistics use `np.std` (population std, ddof=0).
- Sub-trajectory lengths from percentages are `truncate(pct * L_gt, 2)` with
  `L_gt` the length of the raw groundtruth (within the optional time
  window); in multi-trial mode the first successful trial's lengths are
  reused for all trials.
