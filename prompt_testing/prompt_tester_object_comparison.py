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
    def get_score_for_object(self, actual_output: dict, expected_output: dict) -> tuple[float, dict]:
        total_penalty = 0.0
        field_scores = {}

        all_keys = set(actual_output.keys()).union(set(expected_output.keys()))
        total_fields = len(all_keys)

        for key in all_keys:
            if key in self.fields_to_ignore:
                continue
            actual_value = actual_output.get(key)
            expected_value = expected_output.get(key)

            penalty = self.get_field_penalty(actual_value, expected_value)
            field_scores[key] = max(0.0, 1.0 - penalty)
            
            if key in self.fields_weightings:
                penalty *= self.fields_weightings[key]
            
            total_penalty += penalty

        overall_score = max(0.0, 1.0 - (total_penalty / total_fields))
        
        # if overall_score < 0.5:
        #     print(f"Expected: {expected_output}\nActual: {actual_output}\n\n")
        
        return overall_score, field_scores

    def get_field_penalty(self, actual, expected):
        if actual == expected:
            return 0
        if expected in [None, "", []] and actual in [None, "", []]:
            return 0
        if expected in [None, "", []] and actual not in [None, "", []]:
            return 1
        if actual in [None, "", []] and expected not in [None, "", []]:
            return 1
        if isinstance(actual, list) and isinstance(expected, list):
            result = self.compare_lists(actual, expected)
            return result
        if isinstance(actual, str) and isinstance(expected, str):
            result = 1 - SequenceMatcher(None, actual, expected).ratio()
            return result
        return 1

    def compare_lists(self, actual_list, expected_list):
        actual_set, expected_set = set(actual_list), set(expected_list)
        true_positives = len(actual_set & expected_set)
        false_positives = len(actual_set - expected_set)
        false_negatives = len(expected_set - actual_set)
    
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        return f1_score


class PromptTesterObjectSimilarity(PromptTester):
    batch_size = 10
    def __init__(self, model_caller: ModelCaller, input_data:list[str], expected_outputs:list[dict], evaluator: Evaluator, output_converter: Converter, input_converter: Converter, train_split):
        super().__init__(model_caller, input_data, expected_outputs, output_converter, input_converter, train_split)
        self.evaluator = evaluator

    async def get_scores_for_solutions(self, prompts: list[str], progress, j) -> list[(float, dict)]:
        # Start coroutines as tasks immediately
        tasks = [asyncio.create_task(self.get_prompt_score(prompt, progress, j, i)) for i, prompt in enumerate(prompts)]
    
        # Await their results concurrently
        return await asyncio.gather(*tasks)
    
    async def call_model_and_update_progress(self, prompt, inp_out, progress, sub_progress_task):
        # Ensure call_model_cached is truly async
        res = await self.model.call_model_cached(
            "", prompt,
            '\n'.join([json.dumps(self.input_converter.convert(inp[1]["PresentedName"]), indent=4) for inp in inp_out]),
            temperature=0.0, max_length=2_000
        )
    
        progress.update(sub_progress_task, advance=1)
        return res
    
    async def get_prompt_score(self, prompt, progress, j, i) -> (float, dict):
        total_score = 0.0
        field_score_sums = {}
        field_count = {}
    
        # Create a list of async tasks for batch processing
        input_output_batches = list(self.batch_list(list(zip(self.input_data, self.expected_outputs)), self.batch_size))
    
        sub_progress_task = progress.add_task(f"[red]Evaluating prompt {i} for search space {j}...", total=len(input_output_batches))
    
        # Start model calls as tasks immediately
        tasks = [
            asyncio.create_task(self.call_model_and_update_progress(prompt, inp_out, progress, sub_progress_task))
            for inp_out in input_output_batches
        ]
    
        # Await the results concurrently
        results = await asyncio.gather(*tasks)

        worst_score = 1
        worst_out = None
        # Process results
        for result, inp_out in zip(results, input_output_batches):
            stripped_result = self.get_outer_curly_bracket_value(result)
            try:
                result_obj = json.loads(stripped_result)
            except Exception as e:
                print(f"Could not parse result: {e}")
                continue
    
            converted = self.output_converter.convert(result_obj)
            
            for (res, (i, expected)) in zip(converted, [inp for inp in inp_out]):
                object_score, field_scores = self.evaluator.get_score_for_object(res, expected)
                if object_score < worst_score:
                    worst_score = object_score
                    worst_out = expected
                total_score += object_score
    
                for field, score in field_scores.items():
                    if field not in field_score_sums:
                        field_score_sums[field] = 0.0
                        field_count[field] = 0
                    field_score_sums[field] += score
                    field_count[field] += 1
    
        num_inputs = float(len(self.input_data))
        average_score = total_score / num_inputs
        average_field_scores = {field: field_score_sums[field] / field_count[field] for field in field_score_sums}
    
        return average_score, average_field_scores, worst_out

    def batch_list(self, lst, batch_size):
        return [lst[i:i + batch_size] for i in range(0, len(lst), batch_size)]

    def get_outer_curly_bracket_value(self, s):
        # Initialize a variable to store the result
        result = ''
        # Flag to indicate if we're inside the outer curly brackets
        inside_outer = False
        # Counter to track the nesting level of curly brackets
        brace_count = 0

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