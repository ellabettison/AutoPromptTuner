import math
import random
from itertools import combinations
import tkinter as tk
from tkinter import scrolledtext

from prompt_testing.prompt_tester import PromptTester
import math
import random
import tkinter as tk
from itertools import combinations
from tkinter import scrolledtext

from prompt_testing.prompt_tester import PromptTester


class PromptTesterRLHF(PromptTester):
    user_system_prompt = """
    Imagine you are a user going to an LLM for advice. Respond briefly as the user to the following chat history, finishing with [accept], [reject] or [more info], based on your response to the LLM's advice:
    """

    initial_user_system_prompt = """
    Imagine you are a user going to an LLM for advice. Ask the LLM for advice on a brief, specific scenario in the following category:
    """

    def get_user_response(self, chat_history: str, system_prompt: str=user_system_prompt):
        user_response = self.model.call_model(
            system_prompt=system_prompt,
            user_prompt=chat_history + "\n\nUser: ",
            max_length=200
        )
        return user_response

    def get_llm_response(self, chat_history: str, prompt: str):
        llm_response = self.model.call_model(
            system_prompt=prompt,
            user_prompt=chat_history + "\n\nLLM: ",
            max_length=200
        )
        return llm_response

    def get_conversation_for_solutions(self, prompt: str, first_user_input: str, iters: int=5, chat_history: str = "") -> str:
        chat_history = f"{chat_history}"
        user_question = self.model.call_model(system_prompt=self.initial_user_system_prompt, user_prompt=first_user_input)
        chat_history += f"\n\nUser: {user_question}"
        for i in range(iters):
            llm_response = self.get_llm_response(chat_history, prompt)
            chat_history +=  f"\n\nLLM: {llm_response}"

            user_response = self.get_user_response(chat_history)
            chat_history += f"\n\nUser: {user_response}"


        # print(f"Chat: \n{chat_history}")
        return chat_history


    def get_conversation_for_solutions_all_inputs(self, prompt: str) -> str:
        full_chat = ""
        for user_input in self.input_data:
            conversation = self.get_conversation_for_solutions(prompt, user_input, iters=1)
            full_chat += conversation
        return full_chat


    def get_scores_for_solutions(self, prompts: list[str]) -> list[float]:
        # print(f"\nTesting scores for the following prompts: {'\n'.join(prompts)}\n")
        results_for_prompts = [self.get_conversation_for_solutions_all_inputs(prompt) for prompt in prompts]

        # final_scores = run_chat_comparison(results_for_prompts)
        final_scores = self.get_elo_scores_for_prompts(prompts , results_for_prompts)
        return final_scores

    def get_elo_scores_for_prompts(self, prompts: list[str], results: list[str]) -> list[float]:
        num_results = len(results)
        elo_scores = {i: 1000 for i in range(num_results)}
        num_comparisons = math.ceil(math.log2(num_results) * num_results)
        matchups = random.sample(list(combinations(range(num_results), 2)), min(num_comparisons, len(results) * (len(results) - 1) // 2))

        def display_comparison(prompt1, prompt2, result1, result2, idx1, idx2, i):
            def select_winner(winner_idx):
                nonlocal elo_scores
                if winner_idx == 0:
                    elo_scores[idx1], elo_scores[idx2] = elo_update(elo_scores[idx1], elo_scores[idx2], 1)
                else:
                    elo_scores[idx1], elo_scores[idx2] = elo_update(elo_scores[idx1], elo_scores[idx2], 0)
                root.quit()
                root.destroy()

            root = tk.Tk()
            root.title(f"Chat History Comparison {i}/{len(matchups)}")
            root.geometry("1000x800")

            frame1 = tk.Frame(root)
            frame1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            frame2 = tk.Frame(root)
            frame2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

            text1 = scrolledtext.ScrolledText(frame1, wrap=tk.WORD, width=50, height=40, font=("Arial", 10))
            text1.pack(fill=tk.BOTH, expand=True)
            text2 = scrolledtext.ScrolledText(frame2, wrap=tk.WORD, width=50, height=40, font=("Arial", 10))
            text2.pack(fill=tk.BOTH, expand=True)

            def colorize_chat(text_widget, chat, prompt):
                text_widget.insert(tk.END, f"System Prompt: {prompt}\n")
                text_widget.insert(tk.END, chat + "\n")
                start_idx = "1.0"
                while True:
                    start_idx = text_widget.search("User:", start_idx, stopindex=tk.END)
                    if not start_idx:
                        break
                    end_idx = text_widget.search(f"LLM:", start_idx, stopindex=tk.END)
                    if end_idx == "":
                        end_idx = text_widget.index(tk.END)
                    text_widget.tag_add("user", start_idx, end_idx)
                    start_idx = end_idx

                start_idx = "1.0"
                while True:
                    start_idx = text_widget.search("LLM:", start_idx, stopindex=tk.END)
                    if not start_idx:
                        break
                    end_idx = text_widget.search(f"User:", start_idx, stopindex=tk.END)
                    # end_idx = text_widget.index(f"{start_idx} User:")
                    if end_idx == "":
                        end_idx = text_widget.index(tk.END)
                    text_widget.tag_add("llm", start_idx, end_idx)
                    start_idx = end_idx

                text_widget.tag_config("user", foreground="blue")
                text_widget.tag_config("llm", foreground="green")
                text_widget.config(state=tk.DISABLED)

            colorize_chat(text1, result1, prompt1)
            colorize_chat(text2, result2, prompt2)

            button1 = tk.Button(frame1, text="Select This Chat", command=lambda: select_winner(0))
            button1.pack()
            button2 = tk.Button(frame2, text="Select This Chat", command=lambda: select_winner(1))
            button2.pack()

            root.mainloop()

        for i, (idx1, idx2) in enumerate(matchups):
            display_comparison(prompts[idx1], prompts[idx2], results[idx1], results[idx2], idx1, idx2, i)

        return [elo_scores[i] for i in range(num_results)]
    
def elo_update(rating1, rating2, outcome, k=32):
    """Update Elo ratings based on match outcome."""
    expected1 = 1 / (1 + 10 ** ((rating2 - rating1) / 400))
    expected2 = 1 - expected1

    new_rating1 = rating1 + k * (outcome - expected1)
    new_rating2 = rating2 + k * (1 - outcome - expected2)

    return new_rating1, new_rating2

class ChatComparisonGUI:
    def __init__(self, master, results, update_callback):
        self.master = master
        self.results = results
        self.update_callback = update_callback
        self.current_pair = 0
        self.scores = {i: 1000 for i in range(len(results))}
        self.matchups = random.sample(
            list(combinations(range(len(results)), 2)),
            min(math.ceil(math.log2(len(results)) * len(results)), len(results) * (len(results) - 1) // 2)
        )

        self.label = tk.Label(master, text="Select the better chat history:")
        self.label.pack()

        self.text1 = tk.Text(master, wrap="word", height=15, width=50)
        self.text1.pack(side=tk.LEFT, padx=10, pady=10)

        self.text2 = tk.Text(master, wrap="word", height=15, width=50)
        self.text2.pack(side=tk.RIGHT, padx=10, pady=10)

        self.button1 = tk.Button(master, text="Select Left", command=lambda: self.record_choice(1))
        self.button1.pack(side=tk.LEFT, padx=5, pady=5)

        self.button2 = tk.Button(master, text="Select Right", command=lambda: self.record_choice(2))
        self.button2.pack(side=tk.RIGHT, padx=5, pady=5)

        self.display_next_matchup()

    def display_next_matchup(self):
        if self.current_pair < len(self.matchups):
            idx1, idx2 = self.matchups[self.current_pair]
            self.text1.delete("1.0", tk.END)
            self.text1.insert(tk.END, self.results[idx1])
            self.text2.delete("1.0", tk.END)
            self.text2.insert(tk.END, self.results[idx2])
        else:
            self.master.quit()

    def record_choice(self, choice):
        idx1, idx2 = self.matchups[self.current_pair]
        if choice == 1:
            self.scores[idx1], self.scores[idx2] = elo_update(self.scores[idx1], self.scores[idx2], 1)
        else:
            self.scores[idx1], self.scores[idx2] = elo_update(self.scores[idx1], self.scores[idx2], 0)

        self.current_pair += 1
        self.display_next_matchup()

    def get_final_scores(self):
        return [self.scores[i] for i in range(len(self.results))]


def run_chat_comparison(results):
    root = tk.Tk()
    app = ChatComparisonGUI(root, results, None)
    root.mainloop()
    return app.get_final_scores()

