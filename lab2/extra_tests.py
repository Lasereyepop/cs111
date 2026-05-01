import os
import pathlib
import subprocess
import tempfile
import textwrap
import unittest


class TestRoundRobinComprehensive(unittest.TestCase):
    LAB_DIR = pathlib.Path(__file__).resolve().parent

    @classmethod
    def setUpClass(cls):
        # Compile the program once before running any tests
        print("Compiling rr.c...")
        result = subprocess.run(
            ["make"],
            capture_output=True,
            text=True,
            cwd=cls.LAB_DIR,
        )
        if result.returncode != 0:
            print("Compilation failed!")
            print(result.stderr)
            cls.compiled = False
        else:
            cls.compiled = True

    @classmethod
    def tearDownClass(cls):
        # Clean up the compiled binary
        subprocess.run(["make", "clean"], capture_output=True, text=True, cwd=cls.LAB_DIR)

    def run_scheduler(self, content, quantum):
        """Helper method to create a temp file, run the C program, and parse output."""
        if not self.compiled:
            self.fail("Compilation failed, skipping test.")

        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write(textwrap.dedent(content).strip() + "\n")
            f.flush()
            temp_name = f.name

        try:
            result = subprocess.check_output(
                ["./rr", temp_name, str(quantum)], stderr=subprocess.STDOUT, cwd=self.LAB_DIR
            ).decode()
            lines = [line for line in result.split("\n") if line.strip()]

            wait_time = float(lines[0].split(":")[1].strip())
            resp_time = float(lines[1].split(":")[1].strip())
            return wait_time, resp_time
        except subprocess.CalledProcessError as e:
            self.fail(
                f"Program crashed with exit code {e.returncode}. Output:\n{e.output.decode()}"
            )
        except IndexError:
            self.fail(f"Could not parse output correctly. Raw output:\n{result}")
        finally:
            os.remove(temp_name)

    def assert_metrics(self, test_name, content, quantum, expected_wait, expected_resp):
        """Helper to run the assertion and format the error message nicely."""
        with self.subTest(test=test_name, quantum=quantum):
            actual_wait, actual_resp = self.run_scheduler(content, quantum)

            error_msg = f"""
            Failed: {test_name} (Quantum = {quantum})
            Expected Wait: {expected_wait:.2f} | Actual Wait: {actual_wait:.2f}
            Expected Resp: {expected_resp:.2f} | Actual Resp: {actual_resp:.2f}
            """
            self.assertAlmostEqual(actual_wait, expected_wait, places=2, msg=error_msg)
            self.assertAlmostEqual(actual_resp, expected_resp, places=2, msg=error_msg)

    # ==========================================
    # TEST CASES
    # ==========================================

    def test_01_lab_baseline(self):
        """The standard test case provided in the lab spec."""
        content = """
        4
        1, 0, 7
        2, 2, 4
        3, 4, 1
        4, 5, 4
        """
        # Testing multiple quantums against known good averages
        expected_results = {
            1: (5.50, 0.75),
            2: (5.00, 1.50),
            3: (7.00, 2.75),
            4: (4.50, 3.25),
            5: (5.50, 3.25),
            6: (6.25, 4.00),
        }
        for q, (exp_wait, exp_resp) in expected_results.items():
            self.assert_metrics("Lab Baseline", content, q, exp_wait, exp_resp)

    def test_02_lab_requeue_edge_case(self):
        """The user-provided edge case for arrival and requeue timing."""
        content = """
        4
        1, 0, 7
        2, 3, 4
        3, 4, 1
        4, 6, 4
        """
        expected_results = {
            1: (5.00, 0.75),
            2: (5.25, 1.50),
            3: (6.50, 2.25),
            4: (4.00, 2.75),
            5: (4.50, 3.25),
            6: (5.75, 3.50),
        }
        for q, (exp_wait, exp_resp) in expected_results.items():
            self.assert_metrics("Requeue Edge Case", content, q, exp_wait, exp_resp)

    def test_02b_unsorted_input_order(self):
        """Same baseline workload as the lab, but intentionally out of arrival order."""
        content = """
        4
        4, 5, 4
        1, 0, 7
        3, 4, 1
        2, 2, 4
        """
        expected_results = {
            1: (5.50, 0.75),
            2: (5.00, 1.50),
            3: (7.00, 2.75),
            4: (4.50, 3.25),
            5: (5.50, 3.25),
            6: (6.25, 4.00),
        }
        for q, (exp_wait, exp_resp) in expected_results.items():
            self.assert_metrics("Unsorted Input Order", content, q, exp_wait, exp_resp)

    def test_03_single_process(self):
        """A single process arriving late. Tests idle CPU fast-forwarding."""
        content = """
        1
        1, 100, 5
        """
        # Regardless of quantum, wait and resp should be 0 since it's the only process
        self.assert_metrics("Single Process", content, 2, 0.00, 0.00)
        self.assert_metrics("Single Process", content, 10, 0.00, 0.00)

    def test_04_simultaneous_arrivals(self):
        """Multiple processes arriving at the exact same tick. Tests queue insertion loops."""
        content = """
        3
        1, 0, 3
        2, 0, 3
        3, 0, 3
        """
        # Q=2. Order: P1(0-2), P2(2-4), P3(4-6), P1(6-7), P2(7-8), P3(8-9)
        # Wait: P1(7-3=4), P2(8-3=5), P3(9-3=6) -> Avg 15/3 = 5.0
        # Resp: P1(0), P2(2), P3(4) -> Avg 6/3 = 2.0
        self.assert_metrics("Simultaneous Arrivals", content, 2, 5.00, 2.00)

    def test_05_micro_quantum(self):
        """Quantum = 1. Forces maximum possible context switching."""
        content = """
        3
        1, 0, 3
        2, 1, 2
        3, 2, 1
        """
        # Q=1.
        # T=0: P1. T=1: Q=[P2, P1], P2 runs. T=2: Q=[P1, P3, P2], P1 runs.
        # Wait avg: 2.0, Resp avg: 0.33
        self.assert_metrics("Micro Quantum (Q=1)", content, 1, 2.00, 0.33)

    def test_06_fcfs_behavior(self):
        """Quantum is larger than all bursts. Should behave identically to FCFS."""
        content = """
        3
        1, 0, 4
        2, 1, 4
        3, 2, 4
        """
        # Q=10. P1(0-4), P2(4-8), P3(8-12)
        # Wait: P1(0), P2(3), P3(6) -> Avg 3.0
        # Resp: P1(0), P2(3), P3(6) -> Avg 3.0
        self.assert_metrics("FCFS Behavior (Large Q)", content, 10, 3.00, 3.00)

    def test_07_idle_gaps(self):
        """Processes arrive, finish, and the CPU goes completely idle before the next arrives."""
        content = """
        2
        1, 0, 2
        2, 10, 2
        """
        # Q=2. P1 runs 0-2. CPU idles 2-10. P2 runs 10-12.
        # Both wait 0, respond in 0.
        self.assert_metrics("Idle CPU Gaps", content, 2, 0.00, 0.00)

    def test_08_cascading_tie_breakers(self):
        """
        Continuous edge case: A new process arrives at the EXACT moment
        the previous process finishes its quantum.
        Ensures strict queue ordering (New arrivals BEFORE preempted process).
        """
        content = """
        4
        1, 0, 4
        2, 2, 2
        3, 4, 2
        4, 6, 2
        """
        # Q=2
        # T=0: P1 starts.
        # T=2: P1 Q-ends. P2 arrives. Queue must be [P2, P1]. P2 starts.
        # T=4: P2 ends. P3 arrives. Queue must be [P1, P3]. P1 starts.
        # T=6: P1 ends. P4 arrives. Queue must be [P3, P4]. P3 starts.
        # Wait avg: 1.50, Resp avg: 1.00
        self.assert_metrics("Cascading Tie Breakers", content, 2, 1.50, 1.00)


if __name__ == "__main__":
    unittest.main(verbosity=2)
