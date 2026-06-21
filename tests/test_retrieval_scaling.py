import unittest

from scripts.benchmark_graph_retrieval_scaling import run_benchmark


class RetrievalScalingTests(unittest.TestCase):
    def test_synthetic_graph_retrieval_scales_to_5x_mvp_size(self):
        results = run_benchmark(
            multipliers=[1, 3, 5],
            queries=[
                "who works in slovakia",
                "who knows erp",
                "who works with api",
                "who is petras boss",
            ],
        )

        self.assertEqual([1, 3, 5], [row["multiplier"] for row in results])
        self.assertEqual([678, 2034, 3390], [row["nodes"] for row in results])
        self.assertEqual([1103, 3309, 5515], [row["relationships"] for row in results])

        for row in results:
            self.assertLess(row["index_build_seconds"], 5.0)
            self.assertLess(row["p95_evidence_ms"], 250.0)
            self.assertLess(row["p95_answer_ms"], 1500.0)

    def test_larger_graph_has_predictable_linear_growth(self):
        one_x, five_x = run_benchmark(
            multipliers=[1, 5],
            queries=["who works in slovakia", "who knows erp"],
        )

        self.assertEqual(one_x["nodes"] * 5, five_x["nodes"])
        self.assertEqual(one_x["relationships"] * 5, five_x["relationships"])

        build_ratio = five_x["index_build_seconds"] / max(one_x["index_build_seconds"], 0.0001)
        self.assertLess(build_ratio, 12.0)


if __name__ == "__main__":
    unittest.main()
