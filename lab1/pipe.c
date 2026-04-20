#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
  if (argc < 2) {
    errno = EINVAL;
    return errno;
  }

  int in_fd = STDIN_FILENO;
  int pipe_fds[2] = {-1, -1};
  pid_t pids[argc];
  int spawned_children = 0;

  for (int i = 1; i < argc; i++) {
    int is_last = (i == argc - 1);

    if (!is_last) {
      if (pipe(pipe_fds) == -1)
        goto cleanup;
    }

    pid_t pid = fork();
    if (pid == -1)
      goto cleanup;

    if (pid == 0) {
      if (in_fd != STDIN_FILENO) {
        if (dup2(in_fd, STDIN_FILENO) == -1)
          exit(errno);
        if (close(in_fd) == -1)
          exit(errno);
      }

      if (!is_last) {
        if (dup2(pipe_fds[1], STDOUT_FILENO) == -1)
          exit(errno);
        if (close(pipe_fds[1]) == -1)
          exit(errno);
        if (close(pipe_fds[0]) == -1)
          exit(errno);
      }

      execlp(argv[i], argv[i], (char *)NULL);

      int exec_errno = errno;
      perror("Execution Failed");

      if (exec_errno == ENOENT || exec_errno == EACCES ||
          exec_errno == ENOEXEC) {
        exit(EINVAL);
      }

      exit(exec_errno);
    } else {
      pids[i] = pid;
      spawned_children++;

      if (in_fd != STDIN_FILENO) {
        if (close(in_fd) == -1)
          goto cleanup;
      }

      if (!is_last) {
        if (close(pipe_fds[1]) == -1)
          goto cleanup;
        in_fd = pipe_fds[0];
        pipe_fds[0] = -1;
        pipe_fds[1] = -1;
      }
    }
  }

  int final_status = 0;

  for (int i = 1; i < argc; i++) {
    int status;
    if (waitpid(pids[i], &status, 0) == -1) {
      int saved_errno = errno;
      for (int j = i + 1; j < argc; j++) {
        if (waitpid(pids[j], NULL, 0) == -1) {
          perror("waitpid");
        }
      }
      exit(saved_errno);
    }

    if (WIFEXITED(status) && WEXITSTATUS(status) != 0) {
      final_status = WEXITSTATUS(status);
    }
  }

  return final_status;

cleanup: {
  int saved_errno = errno;

  if (in_fd != STDIN_FILENO) {
    if (close(in_fd) == -1)
      perror("close");
  }
  if (pipe_fds[0] != -1) {
    if (close(pipe_fds[0]) == -1)
      perror("close");
  }
  if (pipe_fds[1] != -1) {
    if (close(pipe_fds[1]) == -1)
      perror("close");
  }

  for (int j = 1; j <= spawned_children; j++) {
    if (waitpid(pids[j], NULL, 0) == -1)
      perror("waitpid");
  }

  exit(saved_errno);
}
}
