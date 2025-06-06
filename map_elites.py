import asyncio
import json

from rich.console import Console
from rich.progress import Progress, TimeElapsedColumn, TaskProgressColumn, MofNCompleteColumn
from rich.table import Table
import itertools
import random
import numpy as np

from prompt_testing.prompt_tester import PromptTester
from solution_generator.solution_generator import GenerateSolution


class MAPElites:
    def __init__(self, solution_generator: GenerateSolution, prompt_tester: PromptTester, search_space_definitions: list[str], min_spaces_with_solutions=5, num_crossovers=3):
        self.solution_generator = solution_generator
        self.prompt_tester = prompt_tester
        self.search_space_definitions = search_space_definitions
        self.best_solution_per_space = {}
        self.best_score_per_space = {}
        self.best_field_score_per_space = {}
        self.worst_example_by_field ={}
        self.initial_prompt_score = 0
        self.initial_prompt_score_per_space = {}
        self.min_spaces_with_solutions = min_spaces_with_solutions
        self.previous_best_score_per_space = {}
        self.previous_best_field_scores = {}
        self.num_crossovers = min(num_crossovers, len(self.best_score_per_space))
        self.console = Console()

    async def initialise_solutions(self, base_solution, num_solutions=5):
        with Progress(*Progress.get_default_columns(),
                      TimeElapsedColumn(),
                      MofNCompleteColumn()
                      )  as progress:
            task = progress.add_task("[blue]Evaluating initial prompt...", total=1)
            initial_scores = (await self.prompt_tester.get_scores_for_solutions([base_solution], progress, 1))[0]
            progress.update(task, advance=1)
        self.initial_prompt_score = initial_scores[0]
        self.initial_prompt_score_per_space = initial_scores[1]

        async def generate_solution(space, progress, task):
            solution = await self.solution_generator.generate_solution_for_search_space(space)
            progress.update(task, advance=1)
            return solution

        with Progress(*Progress.get_default_columns(),
                      TimeElapsedColumn(),
                      MofNCompleteColumn()
                      ) as progress:
            task = progress.add_task("[cyan]Generating initial solutions...", total=min(num_solutions, len(self.search_space_definitions)))
            solution_tasks = [generate_solution(space, progress, task) for space in random.choices(self.search_space_definitions, k=min(num_solutions, len(self.search_space_definitions)))]
            initial_solutions = await asyncio.gather(*solution_tasks)

        await self.evaluate_and_update_solutions(list(itertools.chain.from_iterable(initial_solutions)))

    async def run_mutation_and_replacement(self):
        mutated_solutions = await self.mutate_solutions()
        crossover_solutions = await self.crossover_solutions()
            
        await self.evaluate_and_update_solutions(mutated_solutions+crossover_solutions+ list(itertools.chain.from_iterable(self.best_solution_per_space.values())))

    async def evaluate_and_update_solutions(self, solutions):
        search_spaces_of_solutions = await self.get_search_space_of_solutions(solutions)

        solutions = await self.generate_extra_solutions(search_spaces_of_solutions, solutions)

        await self.evaluate_solutions(solutions, search_spaces_of_solutions)

    async def get_search_space_of_solutions(self, solutions):

        with (Progress(*Progress.get_default_columns(),
                       TimeElapsedColumn(),
                       MofNCompleteColumn()
                       )
              as progress):
            task = progress.add_task("[magenta]Determining search spaces...", total=len(solutions))
            search_spaces_of_solutions = await asyncio.gather(
                *[self.get_search_space(solution, progress, task) for solution in solutions]
            )
        return search_spaces_of_solutions

    async def get_search_space(self, solution, progress, task):
        space = await self.solution_generator.get_search_space_of_solution(self.search_space_definitions, solution)
        progress.update(task, advance=1)
        return space

    async def evaluate_solutions(self, solutions, search_spaces_of_solutions):
        async def get_scores(search_spaces_of_solutions, space, p, t, j):
            indices_of_solutions_in_space = [i for i in range(len(search_spaces_of_solutions)) if search_spaces_of_solutions[i] == space]
            se = [solutions[i] for i in indices_of_solutions_in_space] + (self.best_solution_per_space.get(space, []))

            if len(se) == 0:
                return [], se

            score_task = asyncio.create_task(self.prompt_tester.get_scores_for_solutions(se, p, j))

            sd = await score_task

            p.update(t, advance=1)
            return sd, se
        
        with Progress(*Progress.get_default_columns(),
                      TimeElapsedColumn(),
                      MofNCompleteColumn()
                      ) as progress:
            task = progress.add_task("[yellow]Evaluating solutions...", total=len(solutions))
            tasks = [asyncio.create_task(get_scores(search_spaces_of_solutions, space, progress, task, j)) for j, space in
                     enumerate(self.search_space_definitions)]
            results = await asyncio.gather(*tasks)

            for (scores_data, solutions_to_evaluate), space in zip(results, self.search_space_definitions):
                if scores_data is None:
                    continue
                scores = [data[0] for data in scores_data]
                scores_by_field = [data[1] for data in scores_data]
                examples_by_field = [data[2] for data in scores_data]

                if scores:
                    sorted_indexes = np.argsort(scores)
                    best_index = sorted_indexes[-1]
                    if space not in self.best_score_per_space or scores[best_index] > self.best_score_per_space[space]:
                        self.best_solution_per_space[space] = [solutions_to_evaluate[best_index]]
                        self.best_score_per_space[space] = scores[best_index]
                        if len(scores) > 1 and (scores[sorted_indexes[-1]] - scores[sorted_indexes[-2]] < 0.01):
                            self.best_solution_per_space[space].append(solutions_to_evaluate[sorted_indexes[-2]])
                    
                        self.best_field_score_per_space[space] = scores_by_field[best_index]
                        self.worst_example_by_field[space] = examples_by_field[best_index]

    async def generate_extra_solutions(self, search_spaces_of_solutions, solutions):
        search_spaces_to_generate_for = random.choices(self.search_space_definitions, k=(
                                                                    max(0, self.min_spaces_with_solutions - len(set(search_spaces_of_solutions))) + 2
        )
                                                       )
        new_sols = []
        with Progress(*Progress.get_default_columns(),
                      TimeElapsedColumn(),
                      MofNCompleteColumn()
                      ) as progress:
            sol = progress.add_task(f"[magenta]Generating solution for empty search spaces...",
                                    total=len(search_spaces_to_generate_for))
            for space in search_spaces_to_generate_for:
                new_sols += await self.solution_generator.generate_solution_for_search_space(space)
                progress.update(sol, advance=1)
        solutions += new_sols
        
        with Progress(*Progress.get_default_columns(),
                      TimeElapsedColumn(),
                      MofNCompleteColumn()
                      ) as progress:
            task = progress.add_task("[magenta]Determining search spaces for new solutions...", total=len(new_sols))
            search_spaces_of_solutions += await asyncio.gather(
                *[self.get_search_space(solution, progress, task) for solution in new_sols]
            )
        return solutions

    async def mutate_solutions(self) -> list[str]:
        async def mutate(solution,bad_example):
            return await self.solution_generator.mutate_solution(solution, bad_example)

        solutions_to_mutate = list(itertools.chain.from_iterable(self.best_solution_per_space.values()))
        with Progress(*Progress.get_default_columns(),
                      TimeElapsedColumn(),
                      MofNCompleteColumn()
                      )  as progress:
            task = progress.add_task("[green]Running mutations...", total=len(solutions_to_mutate))
            mutations = await asyncio.gather(*[mutate(solution, random.choices(list(set([json.dumps(obj, indent=4) for obj in self.worst_example_by_field.values()])), k=5)) for solution in solutions_to_mutate])
            progress.update(task, advance=len(solutions_to_mutate))

        return list(itertools.chain.from_iterable(mutations))

    async def crossover_solutions(self) -> list[str]:
        async def crossover(solution1,solution2):
            return await self.solution_generator.crossover_solutions(solution1, solution2)

        solutions_to_mutate = list(itertools.chain.from_iterable(self.best_solution_per_space.values()))
        with Progress(*Progress.get_default_columns(),
                      TimeElapsedColumn(),
                      MofNCompleteColumn()
                      )  as progress:
            task = progress.add_task("[green]Running crossover...", total=len(solutions_to_mutate))
            mutations = await asyncio.gather(*[crossover(random.choice(solutions_to_mutate),random.choice(solutions_to_mutate)) for _ in range(self.num_crossovers)])
            progress.update(task, advance=len(solutions_to_mutate))

        return list(itertools.chain.from_iterable(mutations))

    def output_current_status(self):
        self.console.clear()

        table = Table(title="MAP-Elites Status")
        table.add_column("Category", style="cyan")
        table.add_column("Best Prompt", style="magenta")
        table.add_column("Best Score", style="green")
        table.add_column("Δ Base Score", style="yellow")
        table.add_column("Δ Previous Best", style="blue")

        for category, prompt in self.best_solution_per_space.items():
            best_score = self.best_score_per_space.get(category, 0.0)
            initial_score = self.initial_prompt_score
            score_diff = best_score - initial_score
            previous_best_score = getattr(self, "previous_best_score_per_space", {}).get(category, initial_score)
            prev_score_diff = best_score - previous_best_score

            diff_color = "green" if score_diff >= 0 else "red"
            prev_diff_color = "green" if prev_score_diff >= 0 else "red"
            
            print(prompt)

            table.add_row(category, prompt[0][:300] + "...", f"{best_score:.4f}",
                          f"[{diff_color}]{score_diff:+.4f}[/]",
                          f"[{prev_diff_color}]{prev_score_diff:+.4f}[/]")

            with open(f"prompts/best_prompt_{category}.txt", "w") as f:
                f.write(prompt[0])

        self.console.print(table)

        field_table = Table(title="Field-wise Scores")
        field_table.add_column("Field", style="magenta")
        field_table.add_column("Score", style="green")
        field_table.add_column("Δ Base Diff", style="yellow")
        field_table.add_column("Δ Previous Best", style="blue")

        sorted_solution_indexes = sorted(self.best_score_per_space.items(), key=lambda item: item[1], reverse=True)
        best_solution_space = sorted_solution_indexes[0][0]
        best_solution_score_per_field = self.best_field_score_per_space[best_solution_space]

        initial_field_scores = self.initial_prompt_score_per_space
        previous_field_scores = getattr(self, "previous_best_field_scores", initial_field_scores)

        for field, score in best_solution_score_per_field.items():
            initial_score = initial_field_scores.get(field, 0.0)
            score_diff = score - initial_score
            prev_score = previous_field_scores.get(field, initial_score)
            prev_score_diff = score - prev_score

            diff_color = "green" if score_diff > 0 else ("red" if score_diff < 0 else "yellow")
            prev_diff_color = "green" if prev_score_diff > 0 else ("red" if prev_score_diff < 0 else "yellow")
            score_colour = "green" if score > 0.95 else ("red" if score < 0.8 else "yellow")

            field_table.add_row(field, f"[{score_colour}]{score:.4f}",
                                f"[{diff_color}]{score_diff:+.4f}[/]",
                                f"[{prev_diff_color}]{prev_score_diff:+.4f}[/]")

        self.console.print(field_table)

        with open("prompts/best_prompt.txt", "w") as f:
            f.write(self.best_solution_per_space[best_solution_space][0])

        if len(sorted_solution_indexes) > 1:
            with open("prompts/second_best_prompt.txt", "w") as f:
                f.write(self.best_solution_per_space[sorted_solution_indexes[1][0]][0])

        if len(sorted_solution_indexes) > 2:
            with open("prompts/third_best_prompt.txt", "w") as f:
                f.write(self.best_solution_per_space[sorted_solution_indexes[2][0]][0])

        if len(sorted_solution_indexes) > 3:
            with open("prompts/fourth_best_prompt.txt", "w") as f:
                f.write(self.best_solution_per_space[sorted_solution_indexes[3][0]][0])

        if len(sorted_solution_indexes) > 4:
            with open("prompts/fifth_best_prompt.txt", "w") as f:
                f.write(self.best_solution_per_space[sorted_solution_indexes[4][0]][0])

        # Store previous best scores for future comparison
        self.previous_best_score_per_space = self.best_score_per_space.copy()
        self.previous_best_field_scores = best_solution_score_per_field.copy()

