# Accuracy on non-failed runs (ATE posyaw <= 2 m)

| method | group | non-failed / runs | median ATE [m] | geometric mean [m] |
|---|---|---|---|---|
| OpenVINS | static | 120 / 120 | 0.076 | 0.079 |
| OpenVINS | low | 240 / 240 | 0.077 | 0.079 |
| OpenVINS | high | 228 / 240 | 0.129 | 0.150 |
| OpenVINS | all | 468 / 480 | 0.091 | 0.108 |
| SAVIOR-none (control) | static | 120 / 120 | 0.076 | 0.079 |
| SAVIOR-none (control) | low | 240 / 240 | 0.077 | 0.079 |
| SAVIOR-none (control) | high | 228 / 240 | 0.129 | 0.150 |
| SAVIOR-none (control) | all | 468 / 480 | 0.091 | 0.108 |
| Y-Cls | static | 119 / 120 | 0.106 | 0.107 |
| Y-Cls | low | 238 / 240 | 0.112 | 0.108 |
| Y-Cls | high | 235 / 240 | 0.130 | 0.134 |
| Y-Cls | all | 473 / 480 | 0.118 | 0.120 |
| SAVIOR | static | 120 / 120 | 0.079 | 0.081 |
| SAVIOR | low | 240 / 240 | 0.080 | 0.082 |
| SAVIOR | high | 239 / 240 | 0.092 | 0.095 |
| SAVIOR | all | 479 / 480 | 0.085 | 0.088 |
| O-Dyn+B | static | 120 / 120 | 0.076 | 0.079 |
| O-Dyn+B | low | 240 / 240 | 0.077 | 0.079 |
| O-Dyn+B | high | 240 / 240 | 0.080 | 0.081 |
| O-Dyn+B | all | 480 / 480 | 0.079 | 0.080 |
| O-Cls+B | static | 118 / 120 | 0.113 | 0.118 |
| O-Cls+B | low | 236 / 240 | 0.112 | 0.114 |
| O-Cls+B | high | 230 / 240 | 0.122 | 0.124 |
| O-Cls+B | all | 466 / 480 | 0.118 | 0.119 |
| SAVIOR-edge | static | 120 / 120 | 0.088 | 0.087 |
| SAVIOR-edge | low | 240 / 240 | 0.082 | 0.084 |
| SAVIOR-edge | high | 239 / 240 | 0.097 | 0.100 |
| SAVIOR-edge | all | 479 / 480 | 0.089 | 0.091 |
| VINS-Fusion | static | 120 / 120 | 0.106 | 0.107 |
| VINS-Fusion | low | 240 / 240 | 0.109 | 0.109 |
| VINS-Fusion | high | 240 / 240 | 0.146 | 0.165 |
| VINS-Fusion | all | 480 / 480 | 0.125 | 0.134 |
| VINS+zero (control) | static | 120 / 120 | 0.106 | 0.107 |
| VINS+zero (control) | low | 240 / 240 | 0.109 | 0.109 |
| VINS+zero (control) | high | 240 / 240 | 0.146 | 0.165 |
| VINS+zero (control) | all | 480 / 480 | 0.125 | 0.134 |
| VINS+SAVIOR | static | 120 / 120 | 0.117 | 0.116 |
| VINS+SAVIOR | low | 240 / 240 | 0.117 | 0.120 |
| VINS+SAVIOR | high | 240 / 240 | 0.142 | 0.143 |
| VINS+SAVIOR | all | 480 / 480 | 0.127 | 0.131 |
| VINS+Y-Cls | static | 120 / 120 | 0.138 | 0.135 |
| VINS+Y-Cls | low | 240 / 240 | 0.141 | 0.137 |
| VINS+Y-Cls | high | 240 / 240 | 0.163 | 0.164 |
| VINS+Y-Cls | all | 480 / 480 | 0.148 | 0.150 |
| VINS+O-Dyn+B | static | 120 / 120 | 0.106 | 0.107 |
| VINS+O-Dyn+B | low | 240 / 240 | 0.107 | 0.108 |
| VINS+O-Dyn+B | high | 240 / 240 | 0.117 | 0.120 |
| VINS+O-Dyn+B | all | 480 / 480 | 0.111 | 0.114 |
| VINS+O-Cls+B | static | 120 / 120 | 0.135 | 0.135 |
| VINS+O-Cls+B | low | 240 / 240 | 0.131 | 0.133 |
| VINS+O-Cls+B | high | 240 / 240 | 0.157 | 0.150 |
| VINS+O-Cls+B | all | 480 / 480 | 0.143 | 0.141 |
| DynaVINS (upstream) | static | 120 / 120 | 0.048 | 0.051 |
| DynaVINS (upstream) | low | 240 / 240 | 0.053 | 0.054 |
| DynaVINS (upstream) | high | 240 / 240 | 0.069 | 0.073 |
| DynaVINS (upstream) | all | 480 / 480 | 0.060 | 0.063 |
