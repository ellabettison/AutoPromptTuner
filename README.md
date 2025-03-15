# Automatic Prompt Tuner!

## Overview
The **Automated Prompt Tuner** is a system designed to iteratively optimize prompts using **MAP-Elites**, an evolutionary algorithm.

## Running the Tuner
To execute the tuning process, run the following command:

```sh
python run_map_elites.py -d <problem_definition_file> -i <input_data_file> -o <output_data_file>
```

Example:
```sh
python run_map_elites.py -d person_parsing.txt -i person_names_input.json -o non_latin_labelled_person_parses.json
```

## Required Files and Directories

### Input Data
- **Location:** `data/input_data/`
- **Format:** A text file where each line represents the input for a test case.
- **Example File:** `person_names_input.json`

### Output Data
- **Location:** `data/expected_output_data/`
- **Format:** A JSON file with a list of output data objects, where each corresponds to an input object.
- **Example File:** `non_latin_labelled_person_parses.json`

### Problem Definition
- **Location:** `data/problem_definition/`
- **Format:** A text file containing the problem definition.
- **Example File:** `person_parsing.txt`

### Custom Converters (Optional)
Custom converters can be used to transform input and output data formats.
They should implement the `Converter` class in `custom_converters/converter.py`
- **Input Converter:** Located in `custom_converters/`, the script should define a class for converting a line of input data in the file to the form to be provided to the model.
- **Output Converter:** Located in `custom_converters/`, the script should define a class for converting a batch of output data from the model to a list of the form provided in the output file.
- **Example Files:** `person_parse_input_converter.py`, `person_parse_converter.py`

## Command-line Arguments
The script provides several optional arguments to fine-tune the execution:

| Argument                   | Description | Default                                                                                         |
|----------------------------|-------------|-------------------------------------------------------------------------------------------------|
| `-f, --fields_to_ignore`   | Fields to ignore when evaluating outputs. | `["FirstNameShortestDiminutives", "Id", "ClientId", "TransliteratedName"]`                      |
| `-m, --model`              | Model to use (`GPT` or `Gemini`). | `Gemini`                                                                                        |
| `-w, --weights`            | Dictionary of fields to assign higher weight during evaluation. | `{ "FamilyName": 2, "FirstName": 2, "FamilyNamePrefixesRemoved": 1.5, "OtherGivenNames": 1.5 }` |
| `-d, --problem_definition` | Name of the problem definition file. | **Required**                                                                                    |
| `-i, --input_data`         | Name of the input data file. | **Required**                                                                                    |
| `-o, --output_data`        | Name of the expected output data file. | **Required**                                                                                    |
| `-c, --categories`         | Dictionary of search space categories and values. | Default Categories (see below)                                                                  |
| `-t, --train_num`          | Number of examples used for training. | `600`                                                                                           |
| `-n, --num_rounds`         | Number of iterations. | `30`                                                                                            |
| `-s, --min_spaces`         | Minimum number of search spaces which should have solutions, a larger number means a wider range of solutions. | `10`                                                                                            |
| `--input_converter`        | Name of the input converter class file. | `person_parse_input_converter`                                                                  |
| `--output_converter`       | Name of the output converter class file. | `person_parse_converter`                                                                        |

## Default Categories
The tuner explores various prompt variations based on the following default categories:
```python
default_categories = {
    "Specification Detail": ["Simple", "Medium", "Extremely Detailed"],
    "Use of Examples": ["No Example", "One Example", "Many Examples"],
    "Conciseness": ["Short", "Medium", "Long"],
    "Target Audience": ["Human", "Machine-Oriented"]
}
```

