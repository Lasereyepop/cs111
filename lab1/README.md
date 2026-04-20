## UID: 306373879

## Pipe Up

This program takes in and executes each command line argument as a separate program and connects programs with Unix pipes, similar to using `|` in a shell.

## Building

```bash
make
```

This compiles `pipe.c` and builds the executable `pipe`.

## Running

Run the program by passing executable names as arguments:
`./pipe ls cat wc`

This is equivalent to:
`ls | cat | wc`

The first program reads from the parent process's standard input and the last program writes to the parent process's standard output. All programs write errors to standard error.

You can also run a single program:
`./pipe ls`

## Cleaning up

```bash
make clean
```

This removes the generated `pipe.o` and `pipe` files.
