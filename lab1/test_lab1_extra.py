import subprocess
import unittest


class TestLab1Extra(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            ['cc', '-std=c17', '-Wpedantic', '-Wall', '-O2', '-c', '-o', 'pipe.o', 'pipe.c'],
            capture_output=True, text=True)
        if result.returncode != 0:
            cls.make = False
            return
        result = subprocess.run(
            ['cc', 'pipe.o', '-o', 'pipe'],
            capture_output=True, text=True)
        cls.make = result.returncode == 0

    @classmethod
    def tearDownClass(cls):
        subprocess.run(['rm', '-f', 'pipe.o', 'pipe'], capture_output=True)

    def test_single_command(self):
        self.assertTrue(self.make, msg='build failed')
        cl_result = subprocess.run('pwd', capture_output=True, shell=True)
        pipe_result = subprocess.check_output(('./pipe', 'pwd'))
        self.assertEqual(cl_result.stdout, pipe_result,
            msg=f"Single command: expected {cl_result.stdout} but got {pipe_result}.")

    def test_no_args(self):
        self.assertTrue(self.make, msg='build failed')
        pipe_result = subprocess.run('./pipe', capture_output=True)
        self.assertEqual(pipe_result.returncode, 22,
            msg=f"No args should exit with EINVAL (22), got {pipe_result.returncode}.")

    def test_bogus_first(self):
        self.assertTrue(self.make, msg='build failed')
        pipe_result = subprocess.run(('./pipe', 'bogus', 'ls'),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertTrue(pipe_result.returncode,
            msg='Bogus first argument should cause nonzero return code.')
        self.assertNotEqual(pipe_result.stderr, b'',
            msg='Error should be reported to standard error.')

    def test_two_commands(self):
        self.assertTrue(self.make, msg='build failed')
        cl_result = subprocess.run('ls | wc', capture_output=True, shell=True)
        pipe_result = subprocess.check_output(('./pipe', 'ls', 'wc'))
        self.assertEqual(cl_result.stdout, pipe_result,
            msg=f"Two commands: expected {cl_result.stdout} but got {pipe_result}.")

    def test_eight_commands(self):
        self.assertTrue(self.make, msg='build failed')
        cl_result = subprocess.run(
            'ls | cat | cat | cat | cat | cat | cat | wc',
            capture_output=True, shell=True)
        pipe_result = subprocess.check_output(
            ('./pipe', 'ls', 'cat', 'cat', 'cat', 'cat', 'cat', 'cat', 'wc'))
        self.assertEqual(cl_result.stdout, pipe_result,
            msg=f"Eight commands: expected {cl_result.stdout} but got {pipe_result}.")

    def test_stdout_passthrough(self):
        self.assertTrue(self.make, msg='build failed')
        cl_result = subprocess.run('ls', capture_output=True, shell=True)
        pipe_result = subprocess.check_output(('./pipe', 'ls'))
        self.assertEqual(cl_result.stdout, pipe_result,
            msg=f"stdout passthrough: expected {cl_result.stdout} but got {pipe_result}.")


if __name__ == '__main__':
    unittest.main()
