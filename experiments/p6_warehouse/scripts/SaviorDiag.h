// P3a/P5 diagnostic build only (NOT part of the SAVIOR fork): logging of feature fates to $SAVIOR_DIAG_FILE.
#pragma once
#include <cstdio>
#include <cstdlib>
namespace ov_msckf {
inline FILE *savior_diag() {
  static FILE *f = []() -> FILE * {
    const char *p = std::getenv("SAVIOR_DIAG_FILE");
    if (!p || !*p)
      return nullptr;
    FILE *ff = std::fopen(p, "w");
    if (ff)
      std::fprintf(ff, "# T,t,init,cam,id,u,v | M/SD,t,featid,status,n_meas,chi2,thr | SU,t,featid,status,n_meas,chi2,thr | C,t,featid,n_meas\n");
    return ff;
  }();
  return f;
}
} // namespace ov_msckf
