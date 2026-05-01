# You Spin Me Round Robin

This program simulates a RR CPU scheduler for a set of processes. It then computes and prints the average waiting time and repsonse time using the provided quantum length in the CLI.

## Building

```shell
make
```

This creates the executable rr.

## Running

cmd for running:

```shell
./rr <input-file> <quantum>
```

- <input-file> is the path to the input file which has information on the processes
- <quantum> is the RR time quantum (positive integer)

The input file should contain the following information:

1. Number of processes on the first line
2. One process per line in this format: pid, arrival_time, burst_time

Example:
4
1, 0, 3
2, 2, 5
3, 4, 4
4, 5, 6

The program prints:

- Average waiting time
- Average response time

results

```shell
./rr processes.txt 3

Average waiting time: 7.00
Average response time: 2.75
```

The results were obtained by passing in processes.txt with a quantum of 3.

## Cleaning up

```shell
make clean
```
