![Logo](https://github.com/libratom/ratom-logos/raw/main/basic_variations/RATOM_Vector_Logo_v1_300px.png)

# libratom

[![PyPI version](https://badge.fury.io/py/libratom.svg)](https://badge.fury.io/py/libratom)
[![Build Status](https://github.com/libratom/libratom/actions/workflows/test_suite.yml/badge.svg?branch=main)](https://github.com/libratom/libratom/actions/workflows/test_suite.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/libratom/libratom/branch/main/graph/badge.svg)](https://codecov.io/gh/libratom/libratom)
[![Maintainability](https://api.codeclimate.com/v1/badges/da1ce430d2d5fb3b548a/maintainability)](https://codeclimate.com/github/libratom/libratom/maintainability)
[![Twitter Follow](https://img.shields.io/twitter/follow/RATOM_project.svg?style=social&label=Follow)](https://twitter.com/RATOM_Project)

Python library and supporting utilities to parse and process PST and mbox email sources.

## Installation

Libratom requires Python 3.8 or newer, and can be installed from the Python Package Index. Installing with **pip** will automatically install all required dependencies. These dependencies include a version of **libpff** that will be compiled automatically with C tooling during install. A selection of environments we have tested follows:

*   Ubuntu 18.04LTS, 20.04LTS, and 22.04LTS releases require build-essential, python3, python3-pip, and python3-venv packages
*   RHEL 9 requires python3, python3-pip, python3-devel, and the Development Tools package group.
*   macOS 10.14 (and newer) releases require Xcode 11 (or newer), Xcode CLI tools, and Python 3 installed using Homebrew (or your preferred method)
*   Windows 10/11 releases require Visual Studio Code, Build Tools for Visual Studio, and Python 3 installed using Anaconda 3 (or your preferred method)

Need guidance setting up an environment on your platform? Navigate to one of the linked sections below before continuing.

*   [Windows environment setup](#windows-environment-setup)
*   [macOS environment setup](#macos-environment-setup)
*   [Ubuntu environment setup](#ubuntu-environment-setup)
*   [RHEL environment setup](#rhel-environment-setup)

We **strongly recommend** you create a Python virtual environment prior to installing libratom. If you followed one of the guides above, you should already have one activated. With the environment configured and a Python virtual environment created and activated, run the following commands.

Make sure pip is upgraded to the latest version:
```shell
pip install --upgrade pip
```

Install libratom:
```shell
pip install libratom
```

## CLI Overview

Libratom provides a command line interface to run several different tasks. To see available commands, type:

```shell
(venv) user@host:~$ ratom -h
```

Follow one of the section links below for detailed explanations of how the available commands work:

*   [Entity extraction](#entity-extraction): Entity extraction from individual PST and mbox files, or directories containing PST and mbox files. Optionally write message bodies and headers to the database.
*   [Model management](#model-management): Management tool for spaCy language models. Use to display available models and install specific model versions.
*   [Scan and report](#scan-and-report): Quickly scan an email source and generate a report. Optionally write message bodies and headers to the database.
*   [Message export](#message-export): Export selected messages from PST files as one .eml file per message.

## Entity extraction

To see detailed help for the entity extraction command, type:

```shell
(venv) user@host:~$ ratom entities -h
```

To run the extractor with default settings over a PST or mbox file, or a directory containing one or more PST and mbox files, type the following:

```shell
(venv) user@host:~$ ratom entities -p -m /path/to/PST-or-mbox-file-or-directory
```

Note that the -m flag has been added to this command to write message bodies (stripped of inline attachments and markup) and message headers to the message table. If the -m flag is omitted, these entries will be null. Progress (enabled using the -p flag) is displayed in a bar at the bottom of the window. To terminate a job early and shut down all workers, type Ctrl-C.

By default, the tool will install and use the latest spaCy 3 en\_core\_web\_sm model (see the [model management](#model-management) section for how to list and install model versions). It will start as many concurrent jobs as there are virtual cores available. Entities are written to a sqlite3 file automatically named using the existing file or directory name and current datetime stamp, and with the following schema:

![RATOM database schema](https://libratom.github.io/ratom-db-schema-v3.png)

The schema contains five tables. Four tables are used to represent files, messages, attachments, and entities. A fifth table is used to store configuration and environment details relevant to a specific run.

In the entity table, text is the entity instance, label\_ is the entity type, filepath is the PST or mbox file associated with this entity. Full message and file information for each entity are also available through message_id and file_report_id respectively. Note that pff_identifier (a message ID specific to PST files) will not be populated for messages located in mbox files. Examples of how to query these tables can be found in the **Interactive examples** section near the end of this README.

## Advanced uses of the entity extraction command

The CLI provides additional flags to tune performance, output location, and verbosity of the tool. Flags that do not take a value may be chained. For example, "-p -v" is equivalent to "-pv" Some example use cases are provided below.

The CLI is "quiet" and produces minimal output by default. A single -v flag enables some basic output about job status. To view more detailed output (for example, if you encounter unexpected failures), you can increase the level of output verbosity with -vv (verbosity level 2):

```shell
(venv) user@host:~$ ratom entities -p -m -vv /path/to/PST-or-mbox-file-or-directory
```

All remaining examples are presented with verbosity level 1 enabled.

To use the latest version of a different entity model, use the --spacy-model flag. The following example directs the tool to use the multi-language model:

```shell
(venv) user@host:~$ ratom entities -p -m -v --spacy-model xx_ent_wiki_sm /path/to/PST-or-mbox-file-or-directory
```

The tool will optimize the number of jobs that may be run concurrently on your system by default, using all available processor cores. To manually set the number of jobs that may be run concurrently, use the -j flag. The following example sets the number of concurrent jobs to 2:

```shell
(venv) user@host:~$ ratom entities -p -m -v -j 2 /path/to/PST-or-mbox-file-or-directory
```

To change the name or location used for the sqlite3 output file, use the -o flag. Specifying a directory will result in the automatically named file being written to that path. Specifying a path that includes a filename will force the use of that filename. In the following example, the sqlite3 database will be named filename.db:

```shell
(venv) user@host:~$ ratom entities -p -m -v -o /path/to/directory/filename.db /path/to/PST-or-mbox-file-or-directory
```

As noted earlier, some of these options can be chained for convenience. The following example specifies that progress will be shown, the second level of verbosity will be used, message headers and bodies (stripped of inline attachments and markup) will be written to the database, 4 jobs will be run concurrently and the sqlite3 database will be named filename.db:

```shell
(venv) user@host:~$ ratom entities -pvvm -j 4 -o /path/to/directory/filename.db /path/to/PST-or-mbox-file-or-directory
```

## Model management

New spaCy releases are generally accompanied by newly trained models. Using different versions of models over the same collection may produce different results. Depending on your workflow and needs, you may wish to install earlier versions of models, upgrade models that were previously installed, or install multiple models. The model command assists with these tasks.

To see detailed help for the model command, type:

```shell
(venv) user@host:~$ ratom model -h
```

To see a list of available models, type:

```shell
(venv) user@host:~$ ratom model -l
```

To install a specific version of an available model, use the -i and --version flags. For example, to install the 3.0.0 version of en\_core\_web\_sm, type:

```shell
(venv) user@host:~$ ratom model -i en_core_web_sm --version 3.0.0
```

Note that a request to install a specific version will replace any existing version of that model, even if the existing version is newer.

## Scan and report

To generate a report (file metadata, message count, and attachment metadata) from an email source (file or directory) in the same sqlite3 databse format as the entity extraction command without actually extracting any entities, use the report command.

To see detailed help for the report command, type:

```shell
(venv) user@host:~$ ratom report -h
```

As an example, the following command generates a report (showing progress while running) from a single PST or MBOX file, or directory of files:

```shell
(venv) user@host:~$ ratom report -p /path/to/PST-or-mbox-file-or-directory
```

Similar to the entities command, adding the -m flag will cause message bodies (stripped of inline attachments and markup) and headers to be written to the message table:

```shell
(venv) user@host:~$ ratom report -p -m /path/to/PST-or-mbox-file-or-directory
```

## Message export

The emldump command generates .eml files from selected messages in one or more PST files. The use case for this command is having to extract messages from multiple PST files fetched from cloud storage onto a local filesystem.
To see its detailed help type:

```shell
(venv) user@host:~$ ratom emldump -h
```

The required input for emldump is the path to a JSON file listing the source PST files and for each PST file the identifiers of messages to be exported.

A sample JSON input is given below:

```shell
(venv) user@host:~$ cat files.json
[
  {
    "filename" : "andy_zipper_000_1_1.pst",
    "sha256": "7223f79c894f6911ca0fe9a105fa47da0edde31670590d45e2ddfdec37469c4d",
    "id_list": ["2203588", "2203620", "2203652"]
  },
  {
   "filename" : "andy_zipper_001_1_1.pst",
   "sha256": "c10d0bb5ac6ee4386c7c990b22f0d337f8f31cfcb685bb1739dd2d8293043134",
   "id_list": ["2133380", "2133412", "2133444"]
  }
]
```

Note that the JSON file contains filenames only. When invoking the command you can specify where those files are via the `-l` or `--location` option. By default the tool will look for them in the current working directory.

You may also specify a base destination folder for the output .eml files via the `-o` or `--out` option. By default the tool will create them under the current working directory, grouped in directories named after each `filename`.

For example, the above input file can be used as follows:

```shell
(venv) user@host:~$ ratom emldump -l /tmp/libratom/test_data/RevisedEDRMv1_Complete/andy_zipper/ -o /tmp/eml/ files.json
```


## Interactive examples

We have prepared a selection of Jupyter notebooks to demonstrate core functionality and additional scripts built using libratom. The repository linked below includes instructions for deploying these notebooks in an executable environment using MyBinder:

[https://github.com/libratom/ratom-notebooks](https://github.com/libratom/ratom-notebooks)

## Environment Setups for Windows, macOS, and Ubuntu

### Windows environment setup

First, install Visual Studio Code. Visit <https://code.visualstudio.com/download> to download and run the 64-bit User Installer for Windows 10. Follow the prompts, accepting all default selections.

Download and run the Build Tools for Visual Studio 2019 installer from <https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019>. Follow the prompts until you see a window with a Workloads tab in the top left hand corner.

In the Workloads tab, check the box for "C++ build tools". Click the Install button at the bottom right of the window. Once you see "Installation Succeeded!", close the window.

Visit <https://www.anaconda.com/products/individual> to download and install the 64-bit Python 3.8 or Python 3.9 Anaconda distribution. Find and double-click the downloaded executable and follow the prompts, accepting all default selections.

Open the Windows Start Menu, select Anaconda3 (64-bit) and click "Anaconda Prompt (Anaconda3)".

In the terminal that appears, create a new virtual environment in which to install libratom. Replace "username" in the prompt with your username. Do not replace the word "name" in the "--name" flag:

```shell
(base) C:\Users\username>conda create --name ratomenv
```

Type y to confirm any prompts and proceed. Activate the environment:

```shell
(base) C:\Users\username>conda activate ratomenv
```

Type y to confirm and proceed. At the next prompt, install pip:

```shell
(ratomenv) C:\Users\username>conda install pip
```

Type y to confirm and proceed. At the next prompt, install libratom:

```shell
(ratomenv) C:\Users\username>pip install libratom
```

Libratom and the ratom CLI tool should now be ready to use.

Python virtual environments can be deactivated and reactivated as needed. To deactivate the environment, type:

```shell
(ratomenv) C:\Users\username>conda deactivate
```

To remove the environment completely, type:

```shell
(base) C:\Users\username>conda env remove -n ratomenv
```

Need additional help getting started with conda? You can find a 20-minute starter guide at <https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html>.

### macOS environment setup

Install the latest version of Xcode from the App Store. Once Xcode is installed, open a terminal (you can find the terminal app by clicking the Spotlight magnifying glass and typing term).

Run the following to install/update the Xcode command line tools:

```shell
user-macbook:~ user$ xcode-select --install
```

You may need to run the following to agree to the Xcode/iOS licence (requires admin privileges):

```shell
user-macbook:~ user$ sudo xcodebuild -license
```

Follow the instructions at the link below to check your system and install Python 3 if needed:

<https://installpython3.com/mac/>

Next, create a new Python 3 virtual environment. Use the instructions in the previous link or create and activate one in your home directory with the following commands:

```shell
user-macbook:~ user$ python3 -m venv venv
user-macbook:~ user$ source venv/bin/activate
```

Follow the remaining instructions in the Installation section at the top of this README to upgrade pip and install libratom.

### Ubuntu environment setup

To install and test this software in a new Python virtual environment in Ubuntu 18.04LTS or newer:

Make sure Python 3.8 or newer, python3-pip, python3-venv, and build-essential are installed. Open a terminal and type the following command:

```shell
sudo apt install build-essential python3 python3-pip python3-venv
```

Create and activate a Python virtual environment:

```shell
python3 -m venv venv
source venv/bin/activate
```

Follow the remaining instructions in the Installation section at the top of this README to upgrade pip and install libratom.

### RHEL environment setup

These instructions use the *DNF* package manager, and have been tested in RHEL 9. In RHEL 9, you will need to install the python3-pip and python3 devel packages. In a terminal, run the following commands:

```shell
sudo dnf install python3-pip
sudo dnf install python3-devel
```

Reply "y" if prompted during the installations. Next, you'll need to install some development tools, particularly a C compiler. There are several ways to do this, but the simplest is to install the Development Tools group:

```shell
sudo dnf group install "Development Tools"
```

Create and activate a Python virtual environment:

```shell
python3 -m venv venv
source venv/bin/activate
```

Once you have completed these installs, follow the remaining instructions at the top of this README to upgrade pip and install libratom.

## License(s)

Logos, documentation, and other non-software products of the RATOM team are distributed under the terms of Creative Commons 4.0 Attribution. Software items in RATOM repositories are distributed under the terms of the MIT License. See the LICENSE file for additional details.

&copy; 2022, The University of North Carolina at Chapel Hill.

## Development Team and Support

Developed by the RATOM team at the University of North Carolina at Chapel Hill.

See [https://ratom.web.unc.edu](https://ratom.web.unc.edu/) for additional project details, staff bios, and news.
