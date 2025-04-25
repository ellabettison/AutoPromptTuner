import argparse
import ast
import asyncio
import importlib.util
import itertools
import json
import random
import sys

from custom_converters.converter import Converter
from map_elites import MAPElites
from model_caller.gemini_caller import GeminiCaller
from model_caller.gpt_caller import GPTCaller
from model_caller.model_caller import ModelCaller
from prompt_testing.prompt_tester import PromptTester
from prompt_testing.prompt_tester_object_comparison import PromptTesterObjectSimilarity, Evaluator
from solution_generator.solution_generator import GenerateSolution


default_categories = {
    "Specification Detail": ["Simple", "Medium", "Extremely Detailed"],
   # "Formality Level": ["Informal", "Neutral", "Formal"],
    # "Directness": ["Direct", "Indirect"],
    # "Voice": ["Active", "Passive"],
    "Use of Examples": ["No Example", "One Example", "Many Examples"],
    #"Explicitness of Field Naming": ["Explicit", "Implicit"],
    "Conciseness": ["Short", "Medium", "Long"],
   # "Instruction Style": ["Imperative", "Descriptive"],
    "Target Audience": ["Human", "Machine-Oriented"],
    # "Degree of Redundancy": ["Minimal", "Redundant"]
}

base_problem_definition = open("data/problem_definition/person_parsing.txt")

def run_map_elites(model_caller: ModelCaller, prompt_tester: PromptTester, base_problem_definition: str, categories: list[str], rounds: int, min_spaces_with_solutions:int):
    solution_generator = GenerateSolution(model_caller, base_problem_definition)
    map_elites_runner = MAPElites(solution_generator,prompt_tester, categories, min_spaces_with_solutions)
    asyncio.run(map_elites_runner.initialise_solutions(base_problem_definition, min_spaces_with_solutions))
    map_elites_runner.output_current_status()
    for i in range(rounds):
        asyncio.run(map_elites_runner.run_mutation_and_replacement())
        map_elites_runner.output_current_status()

def parse_dict(arg):
    """Parses a key-value pair list into a dictionary."""
    try:
        return ast.literal_eval(arg)
    except (ValueError, SyntaxError):
        raise argparse.ArgumentTypeError("Invalid dictionary format. Use a proper key-value pair syntax.")

def load_class_from_file(file_path, class_name):
    """Dynamically loads a class from a given file."""
    spec = importlib.util.spec_from_file_location("module.name", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["module.name"] = module
    spec.loader.exec_module(module)
    return getattr(module, class_name)

def to_camel_case(snake_str):
    return "".join(x.capitalize() for x in snake_str.lower().split("_"))

def parse_args_and_run_map_elites():
    parser = argparse.ArgumentParser(description="Run a function with command-line arguments.")
    parser.add_argument("-f", "--fields_to_ignore", type=str, nargs="+", help="List of fields to ignore", default=[
        "FirstNameShortestDiminutives",
        "TransliteratedName",
        "Misc",
        "IsNonLatin",
        "PresentedName"
    ])
    parser.add_argument("-m", "--model", type=str, help="Model to use, from 'GPT' or 'Gemini'. Defaults to Gemini", default="Gemini")
    parser.add_argument("-w", "--weights", type=parse_dict, help="Fields to weight higher, formatted as a dictionary of string to float, e.g. {\"FirstName\":1.5}", default="""{                                                                                                                                                         "FamilyName": 2,
    "TopLevelBrand": 4,
    "LowLevelBrand": 2,
    "LegalSuffixes": 1.5,
    "Id":0
    }""")
    parser.add_argument("-d", "--problem_definition", type=str, help="Name of base problem definition file, e.g. \"person_parsing.txt\"", default="person_parsing.txt",required=True)
    parser.add_argument("-i", "--input_data", type=str, help="Name of input data file within folder, e.g. \"person_names_input.json\"", default="person_names_input.json",required=True)
    parser.add_argument("-o", "--output_data", type=str, help="Name of expected output data file within folder, e.g. \"non_latin_labelled_person_parses.json\"", default="non_latin_labelled_person_parses.json",required=True)
    parser.add_argument("-c", "--categories", type=parse_dict, help="Dictionary of search space categories and values, e.g. {\"Specification Detail\": [\"Simple\", \"Medium\", \"Extremely Detailed\"]}", default=json.dumps(default_categories))
    parser.add_argument("-t", "--train_num", type=int, help="Number of examples to use for training, e.g. 600", default=600)
    parser.add_argument("-n", "--num_rounds", type=int, help="Number of rounds to iterate for", default=30)
    parser.add_argument("-s", "--min_spaces", type=int, help="Minimum number of search spaces which should have solutions, a larger number means a wider range of solutions", default=10)
    parser.add_argument("--input_converter", type=str, help="Name of input converter class file", default="person_parse_input_converter")
    parser.add_argument("--output_converter", type=str, help="Name of output converter class file", default="org_parse_converter")


    args = parser.parse_args()
    model_caller = GeminiCaller()
    if args.model.lower() == "gpt":
        model_caller = GPTCaller()

    with open(f"data/input_data/{args.input_data}", "r") as f:
        input_data = f.readlines()
    with open(f"data/expected_output_data/{args.output_data}", "r") as f:
        output_data = json.load(f)
    with open(f"data/problem_definition/{args.problem_definition}", "r") as f:
        problem_definition = f.read()

    fields_to_ignore = args.fields_to_ignore
    fields_higher_weightings = args.weights
    train_split = args.train_num
    categories = args.categories
    num_rounds = args.num_rounds
    min_spaces_with_solutions = args.min_spaces

    combinations = [
        "\n".join(f"{key}: {value}" for key, value in zip(categories.keys(), values))
        for values in itertools.product(*categories.values())
    ]
    combinations = random.choices(combinations, k=min(len(combinations), 20))

    output_converter = Converter
    if args.output_converter:
        output_converter_file = "custom_converters/"+args.output_converter+".py"
        output_converter = load_class_from_file(output_converter_file, to_camel_case(args.output_converter))

    input_converter = Converter
    if args.input_converter:
        input_converter_file = "custom_converters/"+args.input_converter+".py"
        input_converter = load_class_from_file(input_converter_file, to_camel_case(args.input_converter))

    prompt_tester = PromptTesterObjectSimilarity(model_caller, input_data, output_data, Evaluator(fields_to_ignore, fields_higher_weightings), output_converter(), input_converter(), train_split=train_split)
    run_map_elites(model_caller, prompt_tester, problem_definition, combinations, num_rounds, min_spaces_with_solutions)


if __name__ == '__main__':
    parse_args_and_run_map_elites()
