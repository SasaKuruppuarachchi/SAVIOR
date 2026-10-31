# SAVIOR project page (gh-pages branch)

Static site for https://sasakuruppuarachchi.github.io/SAVIOR/ . Plain HTML, CSS and JS, no build step, no external
libraries, no tracking. The paper is under review; every number on the page is quoted from the manuscript
(`savior_v2.tex`, `savior_supp.tex`).

## Layout
- `index.html`, `assets/` (CSS, JS), `.nojekyll`
- `media/*.mp4` + `*-poster.jpg`: videos (H.264, yuv420p, faststart); `media/teaser.gif`: small GIF for the README of the code repo
- `media/fig/`: figures copied unchanged from `paper/figures/*.png`
- `media/promo/`: crops of `fig_promotion.png` (panels 1-7 and the legend) for the association-tree animation
- `media/env/`, `media/people/`: stills from the SAVIOR-Warehouse raw cam0 images, small author portraits
- `media/hero-bg.jpg`: blurred crop of one frame of the teaser clip, used as the decorative hero background

## How the media were made
Scripts are outside this branch, in `/home/sasa/workspace/SAVIOR_site_tools/` (not part of the site). Everything ran in
Docker (`savior:humble-cuda12.8` for Python/OpenCV/matplotlib, `linuxserver/ffmpeg:version-6.1.1-cli` for H.264/GIF).
Sources were mounted read-only.
- `teaser.mp4`/`teaser.gif`: sw03_t3_L3, frames 1805-2044, Y-Cls (`yolo_naive`) | SAVIOR (`sens_fix1`) masks of `off_0.0`, overlaid on cam0 (red = 255).
- `masks.mp4`: sw03_t3_L2, frames 1795-2094: camera | Y-Cls | SAVIOR | `oracle_moving_ext` (red 255, orange 192).
- `levels.mp4`: sw03_t3_L0..L3, frames 1050-1349, raw cam0, same frame index at each level (identical poses).
- `envs.mp4`: fw01/sw01/ms01/wx01 at L2, frames 600-799, raw cam0.
- `trajectory.mp4`: sw03_t3_L3 run_01 (offset 0.0) of `openvins` and `sens_fix1` vs ground truth, position+yaw alignment as in the evaluation, 4x speed; matplotlib with the paper style.
- Mask stamps equal the cam0 file names (integer ns), so frames are matched by name.
- Only SAVIOR-Warehouse frames (our own dataset) are used for videos; no third-party frames.
