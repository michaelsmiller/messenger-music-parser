# Facebook Messenger Music YouTube Link Parser

This repo is capable of extracting YouTube links from the JSON of a messenger chat
(available by downloading all your Facebook messenger data). It then searches the links for
author, title, and emoji reactions in order to produce a database of recommendations
searchable by person reacting, and the reaction.

## Instructions

The best way to run this repository is with `pdm`.

1. Install the `pdm` python module (i.e. `pip install pdm`)
2. Enter the root directory of the project and run `pdm sync`. This installs all dependencies.
3. Run `pdm main` in the root directory to run the project.
