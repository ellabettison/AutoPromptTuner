import asyncio
import json
from difflib import SequenceMatcher
from rich.progress import Progress

from custom_converters.converter import Converter
from model_caller.model_caller import ModelCaller
from prompt_testing.prompt_tester import PromptTester


class Evaluator:
    def __init__(self, fields_to_ignore: list[str], fields_weightings: dict[str, float]):
        self.fields_to_ignore = fields_to_ignore
        self.fields_weightings = fields_weightings

    def get_score_for_object(self, actual_output: dict, expected_output: dict) -> tuple[float, dict, dict]:
        total_penalty = 0.0
        field_scores = {}
        list_field_metrics = {}

        all_keys = set(actual_output.keys()).union(set(expected_output.keys()))
        total_fields = len(all_keys)

        for key in all_keys:
            if key in self.fields_to_ignore:
                continue
            actual_value = actual_output.get(key)
            expected_value = expected_output.get(key)
            if not isinstance(expected_value, list):
                if expected_value is None:
                    expected_value = []
                else:
                    expected_value = [expected_value]
            if not isinstance(actual_value, list):
                if actual_value is None:
                    actual_value = []
                else:
                    actual_value = [actual_value]
            metrics = self.compare_lists(actual_value, expected_value)
            list_field_metrics[key] = metrics
            penalty = metrics["false_positives"] + metrics["false_negatives"]
            total_penalty += penalty
        
        overall_score = max(0.0, 1.0 - (total_penalty / total_fields))
        return overall_score, field_scores, list_field_metrics

    def compare_lists(self, actual_list, expected_list):
        try:
            actual_set, expected_set = set([str(item) for item in actual_list]), set([str(item) for item in expected_list])
            true_positives = len(actual_set & expected_set)
            false_positives = len(actual_set - expected_set)
            false_negatives = len(expected_set - actual_set)
            true_negatives = 0
        except Exception as e:
            print("Exception:", e)
            print("Actual list:", actual_list)
            print("Expected list:", expected_list)
            return {
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": 1,
                "true_negatives": 0
            }

        return {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "true_negatives": true_negatives
        }

class PromptTesterObjectSimilarity(PromptTester):
    batch_size = 10
    def __init__(self, model_caller: ModelCaller, input_data:list[str], expected_outputs:list[dict], evaluator: Evaluator, output_converter: Converter, input_converter: Converter, train_split):
        super().__init__(model_caller, input_data, expected_outputs, output_converter, input_converter, train_split)
        self.evaluator = evaluator

    async def get_scores_for_solutions(self, prompts, progress, j):
        tasks = [asyncio.create_task(self.get_prompt_score(prompt, progress, j, i)) for i, prompt in enumerate(prompts)]
        return await asyncio.gather(*tasks)

    async def call_model_and_update_progress(self, prompt, inp_out, progress, sub_progress_task):
        res = await self.model.call_model_cached(
            "", prompt,
            '\n'.join([json.dumps(self.input_converter.convert(inp[1]["PresentedName"] if inp[1]["PresentedName"] is not None else ""), indent=4) for inp in inp_out]),
            temperature=0.0, max_length=5_000
        )
        progress.update(sub_progress_task, advance=1)
        return res

    async def get_prompt_score(self, prompt, progress, j, i):
        total_score = 0.0
        field_score_sums = {}
        field_count = {}
        list_field_metrics_sums = {}
        worst_score = 1
        worst_out = None

        input_output_batches = list(self.batch_list(list(zip(self.input_data, self.expected_outputs)), self.batch_size))

        sub_progress_task = progress.add_task(f"[red]Evaluating prompt {i} for search space {j}...", total=len(input_output_batches))

        tasks = [
            asyncio.create_task(self.call_model_and_update_progress(prompt, inp_out, progress, sub_progress_task))
            for inp_out in input_output_batches
        ]

        results = await asyncio.gather(*tasks)

        for result, inp_out in zip(results, input_output_batches):
            stripped_result = self.get_outer_curly_bracket_value(result)
            try:
                result_obj = json.loads(stripped_result)
            except Exception as e:
                # print()
                print(f"Could not parse result: {e}")
                # print(f"result: \n{stripped_result}\n{result}")
                continue

            converted = self.output_converter.convert(result_obj)

            for (res, (i, expected)) in zip(converted, inp_out):
                expected_converted = self.output_converter.reverse_convert_single_parse(expected)
                if res is None:
                    object_score = 0
                    field_scores = {}
                    list_field_metrics = {}
                else:
                    object_score, field_scores, list_field_metrics = self.evaluator.get_score_for_object(res, expected_converted)
                if object_score < worst_score:
                    worst_score = object_score
                    worst_out = expected_converted
                    print("actual:")
                    print(res)
                    print("expected_converted:")
                    print(worst_out)
                    print()
                total_score += object_score

                for field, score in field_scores.items():
                    field_score_sums[field] = field_score_sums.get(field, 0) + score
                    field_count[field] = field_count.get(field, 0) + 1

                for field, metrics in list_field_metrics.items():
                    if field not in list_field_metrics_sums:
                        list_field_metrics_sums[field] = metrics
                    else:
                        for key in metrics:
                            list_field_metrics_sums[field][key] += metrics[key]

        num_inputs = float(len(self.input_data))
        average_field_scores = {}

        for field in field_score_sums:
            average_field_scores[field] = field_score_sums[field] / field_count[field]

        for field, metrics in list_field_metrics_sums.items():
            tp, fp, fn = metrics["true_positives"], metrics["false_positives"], metrics["false_negatives"]
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            average_field_scores[field] = f1_score

        return (
            (sum(average_field_scores.values()) / len(average_field_scores)) if (len(average_field_scores)> 0) else 0,
            average_field_scores,
            worst_out
        )

    def batch_list(self, lst, batch_size):
        return [lst[i:i + batch_size] for i in range(0, len(lst), batch_size)]

    def get_outer_curly_bracket_value(self, s):
        # Initialize a variable to store the result
        result = ''
        # Flag to indicate if we're inside the outer curly brackets
        inside_outer = False
        # Counter to track the nesting level of curly brackets
        brace_count = 0
        
        if s is None:
            return result

        for char in s:
            if char == '{':
                if brace_count == 0:
                    inside_outer = True
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    inside_outer = False
                    break

            if inside_outer:
                result += char

        return result+"}"