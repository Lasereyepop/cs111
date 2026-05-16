# Hash Hash Hash

I implemented two thread-safe versions of a chained hash table using `pthread_mutex_t`. The base hash table is serial. Version 1 prioritizes correctness using one global mutex for the whole table. Version 2 improves concurrency by using one mutex per hash table bucket.

## Building

```shell
make
```

## Running

```shell
./hash-table-tester -t 8 -s 50000

Generation: 190,153 usec
Hash table base: 2,583,532 usec
  - 0 missing
Hash table v1: 11,360,731 usec
  - 0 missing
Hash table v2: 903,394 usec
  - 0 missing
```

## First Implementation

In the `hash_table_v1_add_entry` function, I added single mutex to the hash_table_v1 struct.

The function locks the mutex before finding the bucket needed, searching the list, updating an existing entry or inserting a new one.
It then unlocks the mutex before returning in either: the key already exists or when the new list entry is added.
This is the correct approach because only one thread should be able to view or modify any bucket list at a time, preventing race conditions on the SLIST pointers.

I also initialized the mutex in `hash_table_v1_create`, check all mutex return values, exit with pthread error code on failure and destroy the mutex
in `hash_table_v1_destroy`

### Performance

```shell
./hash-table-tester -t 4 -s 50000

Generation: 101,463 usec
Hash table base: 469,761 usec
  - 0 missing
Hash table v1: 2,374,300 usec
  - 0 missing
Hash table v2: 202,521 usec
  - 0 missing
```

Version 1 is much slower than the base version. This is as expected because v1 serializes all hash table insertions with one lock used globally,
so only one worker thread can execute the critical section at a time. It also has extra thread overhead compared to the base due to pthread creation, joining, scheduling and mutex lock/unlock overhead.
Since the base version runs without this thread overhead, v1 can be correct but slower.

## Second Implementation

In the `hash_table_v2_add_entry` function, I added one mutex to each hash_table_entry so that each hash bucket has its own lock.

The function first computes the target bucket for the key and then locks that bucket's mutex. While holding on to that lock, it searches the bucket's linked list, updates the value if the key already exists or inserts a new list entry if the key is not present.
It unlocks the bucket before returning in both the update and insert cases.

I did it like this because all operations that read or modify a bucket's SLIST are protected by that bucket's mutex. Two threads that access the same bucket cannot race with each other.
Because of this, two threads that access different buckets can run concurrently because they use different mutexes.

I initialize every bucket mutex in hash_table_v2_create, check all mutex return values, exit with the pthread error code on failure and destroy every bucket mutex in hash_table_v2_destroy.

### Performance

```shell
./hash-table-tester -t 4 -s 50000

Generation: 99,443 usec
Hash table base: 471,312 usec
  - 0 missing
Hash table v1: 2,440,744 usec
  - 0 missing
Hash table v2: 211,766 usec
  - 0 missing
```

v2 is faster than v1 because it does not use one singular lock for everything. Instead, it only serializes operations that target the same hash bucket.
This allows insertions into different buckets to proceed with parallelism.

Compared to base, v2 can be faster when there are enough threads and CPU cores because work is distributed across bucket locks. However, I have found that the speedup is not always perfectly proportional or linear.
Some operations still serialize when multiple keys hash to the same bucket and each insertion still performs a linked-list search within its bucket.
There is also overhead from thread scheduling and memory allocation.

In my tests, v2 consistently produced 0 missing entries and was faster than v1. This shows that the per-bucket locking strategy is correct and allows more parallelism than the single-lock v1 implementation.

## Cleaning up

```shell
make clean
```

Removes the generated object files and executables

