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
  pid_t pids[argc];

  for (int i = 1; i < argc; i++) {
    int pipe_fds[2];
    int is_last = (i == argc - 1);

    if (!is_last) {
      if (pipe(pipe_fds) == -1)
        exit(errno);
    }

    pid_t pid = fork();
    if (pid == -1)
      exit(errno);

    // Child
    if (pid == 0) {
      if (in_fd != STDIN_FILENO) {
        if (dup2(in_fd, STDIN_FILENO) == -1)
          exit(errno);
        close(in_fd);
      }

      if (!is_last) {
        if (dup2(pipe_fds[1], STDOUT_FILENO) == -1)
          exit(errno);
        close(pipe_fds[1]);
        close(pipe_fds[0]);
      }

      execlp(argv[i], argv[i], (char *)NULL);

      perror("Execution Failed");
      errno = EINVAL;
      exit(errno);
    } else { // Parent
      pids[i] = pid;

      if (in_fd != STDIN_FILENO)
        close(in_fd);

      if (!is_last) {
        close(pipe_fds[1]);
        in_fd = pipe_fds[0];
      }
    }
  }

  int final_status = 0;

  for (int i = 1; i < argc; i++) {
    int status;
    waitpid(pids[i], &status, 0);

    if (WIFEXITED(status) && WEXITSTATUS(status) != 0)
      final_status = WEXITSTATUS(status);
  }

  return final_status;
}
