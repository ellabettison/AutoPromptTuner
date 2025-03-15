import json
import random
import re

from model_caller.model_caller import ModelCaller


class GenerateSolution:
    def __init__(self, model_caller: ModelCaller, base_solution: str):
        self.model_caller = model_caller
        self.base_solution = base_solution
        self.solution_generation_prompt = """
        You are tasked with creating a prompt that can be used to parse names in a list. The goal of this generated prompt is to correctly extract and categorize components of each name in the list. Your output should not be a parser or a solution, but a prompt that asks for parsing names according to the given specification.
        Please produce a prompt that would ask GPT to output the correct parse for each name, breaking it into these components.

        Your generated prompt should include:
        - Instructions on how the name should be split and categorized.
        - Examples for clarity, if necessary.
        - Clear guidelines for handling optional parts of names (e.g., when there is no middle name, how to handle titles or suffixes).
        
        Your task is to provide the best prompt that GPT can follow to parse a list of names according to the above criteria.
        Do not include the input names, the input names will be provided by the user.
        Surround each possible prompt with xml tags <prompt> </prompt>
        It should follow the given specification:
        """

    def get_solution_generation_from_search_space_prompt(self, specification: str, prompt: str):
        return f"""
        You are tasked with creating a prompt that can be used to parse names in a list. The goal of this generated prompt is to correctly extract and categorize components of each name in the list. 
        Your output should not be a parser or a solution, but a prompt that asks for parsing names according to the given specification.
        Please produce a prompt that would ask GPT to output the correct parse for each name, breaking it into these components.

        Your generated prompt should include:
        - Instructions on how the name should be split and categorized.
        - Examples for clarity, if necessary.
        - Clear guidelines for handling optional parts of names (e.g., when there is no middle name, how to handle titles or suffixes).
        
        The prompt itself should be written in the following style:
        {specification}
        
        Parsing task specification:
        {prompt}
        
        Your task is to provide the best prompt that GPT can follow to parse a list of names according to the above criteria.
        ONLY include the prompt to be provided to the model, do NOT include the given style above.
        Do not include the input names, the input names will be provided by the user.
        Surround the generated prompt with xml tags <prompt> </prompt>
        """

    def extract_prompts(self, text: str) -> list[str]:
        """Extracts prompts enclosed in <prompt> </prompt> tags from a given text."""
        return re.findall(r'<prompt>(.*?)</prompt>', text, re.DOTALL)


    def get_solution_mutation_prompt(self, example: list[str]) -> str:
        variance_types = [
            "The new prompt should be almost the same as the original.",
            "The new prompt should have a few changes but be mostly the same as the original.",
            "The new prompt should have significant changes from the original, including structurally.",
            "The new prompt should be extremely different from the original, changing structure and wording."
        ]
        solution_mutation_prompt = f"""
Create a variant on the following prompt, ensuring each prompt still follows the given specification. Surround the prompt with xml tags <prompt> </prompt>
{random.choice(variance_types)}
{('\nSpecification:\n' + self.base_solution+'\n') if random.random() > 0.5 else ''}
Ensure cases such as the following are solved correctly:
{{
    "NameParses":
        [{',\n'.join(example)}]
}}

Prompt to create variant for:
        """
        return solution_mutation_prompt

    def get_search_space_of_solution_prompt(self, search_space_definitions: list[str], solution: str):
        prompt = f"""
        Of the given categories, which does the following prompt best fall under?
        Respond with *only* a number corresponding to the category.
        Prompt:
        {solution}
        
        Categories:
        {'\n'.join([f"{i}. {search_space_definitions[i]}" for i in range(len(search_space_definitions))])}
        
        Category number of prompt:
        """
        return prompt


    async def generate_random_solution(self) -> list[str]:
        initial_solution = await self.model_caller.call_model(user_prompt=self.solution_generation_prompt + self.base_solution, chat_history="", system_prompt="", max_length=2_000)
        prompts = self.extract_prompts(initial_solution)
        return prompts

    async def mutate_solution(self, solution: str, example: list[str]) -> list[str]:
        # print(f"\nMutating solution: {solution[:200]}...")
        mutated_solution = await self.model_caller.call_model(user_prompt=self.get_solution_mutation_prompt(example) + solution, chat_history="", max_length=2_000)
        prompts = self.extract_prompts(mutated_solution)
        # print(f"Mutated solution:\n{'...\n'.join([p[:200] for p in prompts])}\n")
        return prompts

    async def generate_solution_for_search_space(self, search_space_definition: str) -> list[str]:
        # print(f"Generating solution for search space: {search_space_definition}")
        solution = await self.model_caller.call_model(user_prompt=self.get_solution_generation_from_search_space_prompt(search_space_definition, self.base_solution), max_length=2_000)
        prompts = self.extract_prompts(solution)
        # print(f"Solution for search space:{search_space_definition}\nPrompts: {'...\n'.join([p[:200] for p in prompts])}...\n<fin>")
        return prompts

    async def get_search_space_of_solution(self, search_space_definitions: list[str], solution: str) -> str | None:
        prompt = self.get_search_space_of_solution_prompt(search_space_definitions, solution)
        search_space_response = (await self.model_caller.call_model(user_prompt=prompt, chat_history="", max_length=10)).strip()
        if not search_space_response.isnumeric() or int(search_space_response) >= len(search_space_definitions):
            print(f"Invalid search space response: {search_space_response}")
            return None
        return search_space_definitions[int(search_space_response)]