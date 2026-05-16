#include "hash-table-base.h"
#include "hash-table-v1.h"
#include "hash-table-v2.h"

#include <argp.h>
#include <assert.h>
#include <locale.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>

#define BYTES_PER_STRING 8
#define STRESS_KEYS 100
#define STRESS_ITERATIONS 5000

char *entries;

struct arguments {
  uint32_t threads;
  uint32_t size;
};

static struct argp_option options[] = {
    {"threads", 't', "NUM", 0, "Number of threads."},
    {"size", 's', "NUM", 0, "Size per thread."},
    {0}};

static uint32_t parse_uint32_t(const char *string) {
  uint32_t current = 0;
  uint8_t i = 0;
  while (true) {
    char c = string[i];
    if (c == 0)
      break;
    if (i == 10)
      exit(EINVAL);
    if (c < 0x30 || c > 0x39)
      exit(EINVAL);

    uint8_t digit = (c - 0x30);
    if (i == 9) {
      if (current > 429496729)
        exit(EINVAL);
      else if (current == 429496729 && digit > 5)
        exit(EINVAL);
    }
    current = current * 10 + digit;
    ++i;
  }
  return current;
}

static error_t parse_opt(int key, char *arg, struct argp_state *state) {
  struct arguments *arguments = state->input;
  switch (key) {
  case 't':
    arguments->threads = parse_uint32_t(arg);
    break;
  case 's':
    arguments->size = parse_uint32_t(arg);
    break;
  }
  return 0;
}

static struct arguments arguments;
static char *data;
static char stress_data[STRESS_KEYS][BYTES_PER_STRING];

static size_t get_global_index(uint32_t thread, uint32_t index) {
  return thread * arguments.size + index;
}

static char *get_string(size_t global_index) {
  return data + (global_index * BYTES_PER_STRING);
}

static unsigned long usec_diff(struct timeval *a, struct timeval *b) {
  unsigned long usec;
  usec = (b->tv_sec - a->tv_sec) * 1000000;
  usec += b->tv_usec - a->tv_usec;
  return usec;
}

static struct hash_table_v1 *hash_table_v1;
static struct hash_table_v2 *hash_table_v2;

/* --- Standard Workloads --- */

void *run_v1(void *arg) {
  uint32_t thread = (uintptr_t)arg;
  for (uint32_t j = 0; j < arguments.size; ++j) {
    size_t global_index = get_global_index(thread, j);
    char *string = get_string(global_index);
    hash_table_v1_add_entry(hash_table_v1, string, global_index);
  }
  return NULL;
}

void *run_v2(void *arg) {
  uint32_t thread = (uintptr_t)arg;
  for (uint32_t j = 0; j < arguments.size; ++j) {
    size_t global_index = get_global_index(thread, j);
    char *string = get_string(global_index);
    hash_table_v2_add_entry(hash_table_v2, string, global_index);
  }
  return NULL;
}

/* --- Stress Test Workloads --- */

void *run_v1_stress(void *arg) {
  uint32_t thread = (uintptr_t)arg;
  for (int iter = 0; iter < STRESS_ITERATIONS; ++iter) {
    for (int i = 0; i < STRESS_KEYS; ++i) {
      hash_table_v1_add_entry(hash_table_v1, stress_data[i], thread);
    }
  }
  return NULL;
}

void *run_v2_stress(void *arg) {
  uint32_t thread = (uintptr_t)arg;
  for (int iter = 0; iter < STRESS_ITERATIONS; ++iter) {
    for (int i = 0; i < STRESS_KEYS; ++i) {
      hash_table_v2_add_entry(hash_table_v2, stress_data[i], thread);
    }
  }
  return NULL;
}

/* --- Main Execution --- */

int main(int argc, char *argv[]) {
  arguments.threads = 4;
  arguments.size = 25000;

  static struct argp argp = {options, parse_opt};
  argp_parse(&argp, argc, argv, 0, 0, &arguments);

  setlocale(LC_ALL, "en_US.UTF-8");

  data = calloc(arguments.threads * arguments.size, BYTES_PER_STRING);
  struct timeval start, end;

  printf("==========================================\n");
  printf("   PHASE 1: STANDARD PERFORMANCE TEST     \n");
  printf("==========================================\n");

  gettimeofday(&start, NULL);
  srand(42);
  for (uint32_t i = 0; i < arguments.threads; ++i) {
    for (uint32_t j = 0; j < arguments.size; ++j) {
      size_t global_index = get_global_index(i, j);
      char *string = get_string(global_index);
      for (uint32_t k = 0; k < (BYTES_PER_STRING - 1); ++k) {
        int r = rand() % 52;
        string[k] = (r < 26) ? (r + 0x41) : (r + 0x47);
      }
      string[BYTES_PER_STRING - 1] = 0;
    }
  }

  /* Pre-generate stress test keys */
  for (int i = 0; i < STRESS_KEYS; ++i) {
    snprintf(stress_data[i], BYTES_PER_STRING, "STR%04d", i);
  }

  gettimeofday(&end, NULL);
  printf("Data Generation: %'lu usec\n\n", usec_diff(&start, &end));

  /* --- BASE TEST --- */
  struct hash_table_base *hash_table_base = hash_table_base_create();
  gettimeofday(&start, NULL);
  for (uint32_t i = 0; i < arguments.threads; ++i) {
    for (uint32_t j = 0; j < arguments.size; ++j) {
      size_t global_index = get_global_index(i, j);
      hash_table_base_add_entry(hash_table_base, get_string(global_index),
                                global_index);
    }
  }
  gettimeofday(&end, NULL);
  printf("Hash table base: %'lu usec\n", usec_diff(&start, &end));

  size_t missing = 0;
  size_t corrupted = 0;
  for (uint32_t i = 0; i < arguments.threads; ++i) {
    for (uint32_t j = 0; j < arguments.size; ++j) {
      size_t global_index = get_global_index(i, j);
      if (!hash_table_base_contains(hash_table_base,
                                    get_string(global_index))) {
        ++missing;
      } else if (hash_table_base_get_value(hash_table_base,
                                           get_string(global_index)) !=
                 global_index) {
        ++corrupted;
      }
    }
  }
  printf("  - %'lu missing, %'lu corrupted values\n", missing, corrupted);
  hash_table_base_destroy(hash_table_base);

  pthread_t *threads = calloc(arguments.threads, sizeof(pthread_t));

  /* --- V1 TEST --- */
  hash_table_v1 = hash_table_v1_create();
  gettimeofday(&start, NULL);
  for (uintptr_t i = 0; i < arguments.threads; ++i)
    pthread_create(&threads[i], NULL, run_v1, (void *)i);
  for (uintptr_t i = 0; i < arguments.threads; ++i)
    pthread_join(threads[i], NULL);
  gettimeofday(&end, NULL);
  printf("Hash table v1  : %'lu usec\n", usec_diff(&start, &end));

  missing = corrupted = 0;
  for (uint32_t i = 0; i < arguments.threads; ++i) {
    for (uint32_t j = 0; j < arguments.size; ++j) {
      size_t global_index = get_global_index(i, j);
      if (!hash_table_v1_contains(hash_table_v1, get_string(global_index)))
        ++missing;
      else if (hash_table_v1_get_value(
                   hash_table_v1, get_string(global_index)) != global_index)
        ++corrupted;
    }
  }
  printf("  - %'lu missing, %'lu corrupted values\n", missing, corrupted);

  /* --- V2 TEST --- */
  hash_table_v2 = hash_table_v2_create();
  gettimeofday(&start, NULL);
  for (uintptr_t i = 0; i < arguments.threads; ++i)
    pthread_create(&threads[i], NULL, run_v2, (void *)i);
  for (uintptr_t i = 0; i < arguments.threads; ++i)
    pthread_join(threads[i], NULL);
  gettimeofday(&end, NULL);
  printf("Hash table v2  : %'lu usec\n", usec_diff(&start, &end));

  missing = corrupted = 0;
  for (uint32_t i = 0; i < arguments.threads; ++i) {
    for (uint32_t j = 0; j < arguments.size; ++j) {
      size_t global_index = get_global_index(i, j);
      if (!hash_table_v2_contains(hash_table_v2, get_string(global_index)))
        ++missing;
      else if (hash_table_v2_get_value(
                   hash_table_v2, get_string(global_index)) != global_index)
        ++corrupted;
    }
  }
  printf("  - %'lu missing, %'lu corrupted values\n\n", missing, corrupted);

  printf("==========================================\n");
  printf("   PHASE 2: CONCURRENT UPDATE DEADLOCK    \n");
  printf("==========================================\n");
  printf("Forcing %d threads to simultaneously update %d keys %d times...\n",
         arguments.threads, STRESS_KEYS, STRESS_ITERATIONS);

  /* V1 Stress */
  for (uintptr_t i = 0; i < arguments.threads; ++i)
    pthread_create(&threads[i], NULL, run_v1_stress, (void *)i);
  for (uintptr_t i = 0; i < arguments.threads; ++i)
    pthread_join(threads[i], NULL);
  printf("Hash table v1  : Survived deadlock check.\n");
  hash_table_v1_destroy(hash_table_v1);

  /* V2 Stress */
  for (uintptr_t i = 0; i < arguments.threads; ++i)
    pthread_create(&threads[i], NULL, run_v2_stress, (void *)i);
  for (uintptr_t i = 0; i < arguments.threads; ++i)
    pthread_join(threads[i], NULL);
  printf("Hash table v2  : Survived deadlock check.\n");
  hash_table_v2_destroy(hash_table_v2);

  printf("\nAll tests complete.\n");

  free(threads);
  free(data);

  return 0;
}
