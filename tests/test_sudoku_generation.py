import unittest

from board_utils import parse_board
from sudoku_generator import generate_pattern_solution, generate_puzzle
from sudoku_verifier import verify_puzzle


SOLVED_4X4 = "1 2 3 4 3 4 1 2 2 1 4 3 4 3 2 1"
SOLVED_9X9 = (
    "1 2 3 4 5 6 7 8 9 "
    "4 5 6 7 8 9 1 2 3 "
    "7 8 9 1 2 3 4 5 6 "
    "2 3 4 5 6 7 8 9 1 "
    "5 6 7 8 9 1 2 3 4 "
    "8 9 1 2 3 4 5 6 7 "
    "3 4 5 6 7 8 9 1 2 "
    "6 7 8 9 1 2 3 4 5 "
    "9 1 2 3 4 5 6 7 8"
)


class SudokuVerifierTests(unittest.TestCase):
    def test_solved_boards_are_unique(self):
        self.assertTrue(verify_puzzle(SOLVED_4X4).valid)
        self.assertTrue(verify_puzzle(SOLVED_9X9).valid)

    def test_solvable_mode_accepts_multiple_solution_board(self):
        result = verify_puzzle([0] * 16, mode="solvable")

        self.assertTrue(result.valid)
        self.assertEqual(result.solution_count, 1)
        self.assertIsNotNone(result.solution)

    def test_unique_mode_rejects_underconstrained_board(self):
        result = verify_puzzle([0] * 16, mode="unique")

        self.assertFalse(result.valid)
        self.assertEqual(result.solution_count, 2)
        self.assertEqual(result.error, "Sudoku has multiple solutions.")

    def test_invalid_boards_fail_verification(self):
        bad_length = verify_puzzle([1, 2, 3], mode="unique")
        bad_value = verify_puzzle([5] + [0] * 15, mode="unique")

        self.assertFalse(bad_length.valid)
        self.assertIn("perfect square", bad_length.error)
        self.assertFalse(bad_value.valid)
        self.assertIn("out of range", bad_value.error)


class SudokuGeneratorTests(unittest.TestCase):
    def test_generate_4x4_pattern_solution(self):
        solution = generate_pattern_solution(size=4, seed=123)
        values = parse_board(solution)

        self.assertEqual(len(values), 16)
        self.assertNotIn(0, values)
        self.assertTrue(verify_puzzle(solution, mode="unique").valid)

    def test_generate_4x4_solvable_puzzle_with_requested_clues(self):
        generated = generate_puzzle(size=4, clues=6, seed=123)

        self.assertEqual(generated.actual_clues, 6)
        self.assertEqual(generated.target_clues, 6)
        self.assertEqual(sum(1 for value in parse_board(generated.puzzle) if value), 6)
        self.assertTrue(generated.verification.valid)
        self.assertEqual(generated.verification.mode, "derived")

    def test_generate_9x9_smoke(self):
        generated = generate_puzzle(size=9, clues=80, seed=123)

        self.assertEqual(generated.actual_clues, 80)
        self.assertTrue(generated.verification.valid)


if __name__ == "__main__":
    unittest.main()
