// REQUIRES: gwp_asan
// RUN: %clangxx_gwp_asan %s -o %t
// RUN: %expect_crash %run %t 2>&1 | FileCheck %s

// CHECK: GWP-ASan detected a memory error
// CHECK: Use after free occurred when accessing memory at:

#include <cstdlib>

int main() {
  char *Ptr = reinterpret_cast<char *>(malloc(10));

  for (unsigned i = 0; i < 10; ++i) {
    *(Ptr + i) = 0x0;
  }

  free(Ptr);
  volatile char x = *Ptr;
  return 0;
}
