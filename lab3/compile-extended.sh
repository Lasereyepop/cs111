#!/bin/sh
gcc -std=gnu17 -pthread -Wall -O0 -pipe -fno-plt -fPIC -I. \
  hash-table-common.c hash-table-base.c hash-table-v1.c hash-table-v2.c \
  hash-table-tester-extended.c \
  -lrt -o hash-table-tester-extended
