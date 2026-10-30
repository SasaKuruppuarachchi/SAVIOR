# M2b validity audit (verify)

valid = clean exit + trajectory + FINAL fallback_latest = fallback_empty = late = 0 + n_in_core = 0 + poses >= same-offset openvins poses - 1

| method | runs | valid | sync ok | pose rule ok | fallbacks | late | n_in_core | no FINAL |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| savior_edge | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |

**Total: 0 / 2 valid.**

Pose-count difference openvins - method (runs): 

## Invalid runs

| seq | method | run | status | poses | openvins poses | FINAL | fb latest | fb empty | late | in core |
|---|---|---|---|--:|--:|---|--:|--:|--:|--:|
| aisles_t1_L2 | savior_edge | run_07 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_03 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
