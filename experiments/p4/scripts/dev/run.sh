set -e
H=$1; I=$2; cd $H
FLAGS="-std=c++17 -O2 -I/usr/include/eigen3 -I/usr/include/opencv4"
LIBS="-L/usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu/libopencv_core.so.4.5d /usr/lib/x86_64-linux-gnu/libopencv_imgproc.so.4.5d /usr/lib/x86_64-linux-gnu/libopencv_video.so.4.5d /usr/lib/x86_64-linux-gnu/libopencv_calib3d.so.4.5d /usr/lib/x86_64-linux-gnu/libopencv_features2d.so.4.5d -lboost_system -lboost_filesystem -lboost_thread -lboost_date_time -lpthread"
g++ $FLAGS -I$I/ov_core/include compat_harness.cpp -o h -L$I/ov_core/lib -lov_core_lib -Wl,-rpath,$I/ov_core/lib $LIBS
for s in none lr; do
  for m in off gate0 compat0 compat_dyn; do ./h $m $s f_${m}_$s.txt; done
  for m in gate0 compat0; do
    if cmp -s f_off_$s.txt f_${m}_$s.txt; then r="IDENTICAL"; else r="DIFFERENT ($(diff f_off_$s.txt f_${m}_$s.txt | grep -c '^<') rows differ)"; fi
    echo "static=$s: off vs $m: $r ($(wc -l < f_off_$s.txt) feature rows)"
  done
done
