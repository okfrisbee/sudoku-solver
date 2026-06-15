import unittest

from solvers.naive import solve_naive


SOLVED_4X4 = "1 2 3 4 3 4 1 2 2 1 4 3 4 3 2 1"


def pattern_solution(size: int) -> list[int]:
    box = int(size**0.5)
    return [
        ((row * box + row // box + col) % size) + 1
        for row in range(size)
        for col in range(size)
    ]


class NaiveSolverTests(unittest.TestCase):
    def test_solves_4x4_puzzle(self):
        result = solve_naive("1 0 3 0 0 4 0 2 2 0 4 0 0 3 0 1")

        self.assertTrue(result.solved)
        self.assertEqual(result.solution, SOLVED_4X4)

    def test_solves_tokenized_16x16_puzzle(self):
        solved = pattern_solution(16)
        puzzle = solved.copy()
        puzzle[0] = 0

        result = solve_naive(puzzle)

        self.assertTrue(result.solved)
        self.assertEqual(result.solution, " ".join(map(str, solved)))

    def test_rejects_non_square_box_size(self):
        result = solve_naive([0] * 36)

        self.assertEqual(result.status, "failed")
        self.assertIn("perfect square", result.error)

    def test_rejects_duplicate_in_larger_board(self):
        puzzle = pattern_solution(16)
        puzzle[1] = puzzle[0]

        result = solve_naive(puzzle)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "Invalid board state.")


if __name__ == "__main__":
    unittest.main()
