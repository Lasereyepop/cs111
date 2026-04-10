# A Kernel Seedling

This repository contains a Loadable Kernel Module (LKM) for Linux that creates a virtual file at `/proc/count`. When read, this file dynamically calculates and outputs the current number of running processes on the system by iterating through the kernel's internal process list.

## Building

```shell
make
```

## Running

```shell
sudo insmod proc_count.ko
cat /proc/count
```

Results: 135
(Note: I ran multiple tests and this is what the number always settles to, but when usually when I first start running the program - it kind of fluctuates between 135-140. I don't think that this is an issue with my code, but rather a sign of how /proc is a "dynamic" filesystem.)

## Cleaning Up

```shell
sudo rmmod proc_count
make clean
```

## Testing

```python
python -m unittest
```

Result:
...

---

Ran 3 tests in 14.249s

OK

Report which kernel release version you tested your module on
(hint: use `uname`, check for options with `man uname`).
It should match release numbers as seen on https://www.kernel.org/.

```shell
uname -r -s -v
```

Linux 5.14.8-arch1-1 #1 SMP PREEMPT Sun, 26 Sep 2021 19:36:15 +0000
