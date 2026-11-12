#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/* A data/compute workload without a population of hot small functions. */
__attribute__((noinline, noclone))
uint64_t compute(uint64_t seed, unsigned long n) {
  uint64_t a[128];
  for (unsigned i = 0; i < 128; ++i)
    a[i] = seed + i;
  for (unsigned long k = 0; k < n * 8; ++k)
    for (unsigned i = 0; i < 128; ++i) {
      a[i] = (a[i] ^ a[(i + 37) & 127]) * 6364136223846793005ULL + k;
      a[i] ^= a[(i + 13) & 127] >> 11;
    }
  uint64_t sum = 0;
  for (unsigned i = 0; i < 128; ++i)
    sum += a[i];
  return sum;
}

int main(int argc, char **argv) {
  unsigned long n = argc > 1 ? strtoul(argv[1], 0, 10) : 100000;
  printf("%llu\n", (unsigned long long)compute(1, n));
  return 0;
}
