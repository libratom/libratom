![Logo](https://github.com/libratom/ratom-logos/raw/master/basic_variations/RATOM_Vector_Logo_v1_300px.png)

# libratom

[![PyPI version](https://badge.fury.io/py/libratom.svg)](https://badge.fury.io/py/libratom)
[![Build Status](https://travis-ci.org/libratom/libratom.svg?branch=master)](https://travis-ci.org/libratom/libratom)
[![codecov](https://codecov.io/gh/libratom/libratom/branch/master/graph/badge.svg)](https://codecov.io/gh/libratom/libratom)
[![Maintainability](https://api.codeclimate.com/v1/badges/da1ce430d2d5fb3b548a/maintainability)](https://codeclimate.com/github/libratom/libratom/maintainability)
[![Twitter Follow](https://img.shields.io/twitter/follow/RATOM_project.svg?style=social&label=Follow)](https://twitter.com/RATOM_Project)

Python library and supporting utilities to parse and process PST and mbox email sources.

## Installation

Libratom requires Python 3.6 or newer, and can be installed from the Python Package Index. Installing with **pip** will automatically install all required dependencies. These dependencies include a version of **libpff** that will be compiled automatically with C tooling during install. A selection of environments we have tested follows:

*   Ubuntu 16.04LTS, 18.04LTS (and newer) releases require build-essential, python3, python3-pip, and python3-venv packages
*   macOS 10.13 (and newer) releases require Xcode 9.4.1 (or newer), Xcode CLI tools, and Python 3 installed using Homebrew (or your preferred method)
*   Windows 10 releases require Visual Studio Code, Build Tools for Visual Studio, and Python 3 installed using Anaconda 3 (or your preferred method)

Need guidance setting up an environment on your platform? Navigate to one of the linked sections below before continuing.

*   [Windows environment setup](#windows-environment-setup)
*   [macOS environment setup](#macos-environment-setup)
*   [Ubuntu environment setup](#ubuntu-environment-setup)

We **strongly recommend** you create a Python virtual environment prior to installing libratom. If you followed one of the guides above, you should already have one activated. With the environment configured and a Python virtual environment created and activated, run the following commands.

Make sure pip is upgraded to the latest version:
```shell
pip install --upgrade pip
```

Install libratom:
```shell
pip install libratom
```

## Entity extraction

Libratom provides a CLI with planned support for a range of email processing tasks. Currently, the CLI supports entity extraction from individual PST and mbox files, or directories containing one or more PST and mbox files. 

To see available commands, type:

```shell
(venv) user@host:~$ ratom -h
```

To see detailed help for the entity extraction command, type:

```shell
(venv) user@host:~$ ratom entities -h
```

To run the extractor with default settings over a PST or mbox file, or a directory containing one or more PST and mbox files, type the following:

```shell
(venv) user@host:~$ ratom entities -p /path/to/PST-or-mbox-file-or-directory
```

Progress is displayed in a bar at the bottom of the window. To terminate a job early and shut down all workers, type Ctrl-C.

By default, the tool will use the spaCy en\_core\_web\_sm model, and will start as many concurrent jobs as there are virtual cores available. Entities are written to a sqlite3 file automatically named using the existing file or directory name and current datetime stamp, and with the following schema:

![RATOM database schema](https://libratom.github.io/ratom-db-schema.svg)

The schema contains five tables. Four tables are used to represent files, messages, attachments, and entities. A fifth table is used to store configuration and environment details relevant to a specific run.

In the entity table, text is the entity instance, label\_ is the entity type, filepath is the PST or mbox file associated with this entity. Full message and file information for each entity are also available through message_id and file_report_id respectively. Note that pff_identifier (a message ID specific to PST files) will not be populated for messages located in mbox files. Examples of how to query these tables can be found in the **Interactive examples** section near the end of this README.

## Advanced CLI uses

The CLI provides additional flags to tune performance, output location, and verbosity of the tool. Flags that do not take a value may be chained. For example, "-p -v" is equivalent to "-pv" Some example use cases are provided below.

The CLI is "quiet" and produces minimal output by default. A single -v flag enables some basic output about job status. To view more detailed output (for example, if you encounter unexpected failures), you can increase the level of output verbosity with -vv (verbosity level 2):

```shell
(venv) user@host:~$ ratom entities -p -vv /path/to/PST-or-mbox-file-or-directory
```

All remaining examples are presented with verbosity level 1 enabled.

To use a different entity model, use the --spacy-model flag. The following example directs the tool to use the multi-language model:

```shell
(venv) user@host:~$ ratom entities -pv --spacy-model xx_ent_wiki_sm /path/to/PST-or-mbox-file-or-directory
```

The tool will optimize the number of jobs that may be run concurrently on your system by default, using all available processor cores. To manually set the number of jobs that may be run concurrently, use the -j flag. The following example sets the number of concurrent jobs to 2:

```shell
(venv) user@host:~$ ratom entities -pv -j 2 /path/to/PST-or-mbox-file-or-directory
```

To change the name or location used for the sqlite3 output file, use the -o flag. Specifying a directory will result in the automatically named file being written to that path. Specifying a path that includes a filename will force the use of that filename. In the following example, the sqlite3 database will be named filename.db:

```shell
(venv) user@host:~$ ratom entities -pv -o /path/to/directory/filename.db /path/to/PST-or-mbox-file-or-directory
```

## Interactive examples

We have prepared a selection of Jupyter notebooks to demonstrate core functionality and additional scripts built using libratom. The repository linked below includes instructions for deploying these notebooks in an executable environment using MyBinder:

[https://github.com/libratom/ratom-notebooks](https://github.com/libratom/ratom-notebooks)

## Environment Setups for Windows, macOS, and Ubuntu

### Windows environment setup

First, install Visual Studio Code. Visit <https://code.visualstudio.com/download> to download and run the 64-bit User Installer for Windows 10. Follow the prompts, accepting all default selections.

Download and run the Build Tools for Visual Studio 2019 installer from <https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019>. Follow the prompts until you see a window with a Workloads tab in the top left hand corner.

In the Workloads tab, check the box for "C++ build tools". Click the Install button at the bottom right of the window. Once you see "Installation Succeeded!", close the window.

Visit <https://www.anaconda.com/distribution/> to download and install the 64-bit Python 3.7 Anaconda distribution. Follow the prompts, accepting all default selections.

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

<https://wsvincent.com/install-python3-mac/>

Next, create a new Python 3 virtual environment. Use the instructions in the previous link or create and activate one in your home directory with the following commands:

```shell
user-macbook:~ user$ python3 -m venv venv
user-macbook:~ user$ source venv/bin/activate
```

Follow the remaining instructions in the Installation section at the top of this README to upgrade pip and install libratom.

### Ubuntu environment setup

To install and test this software in a new Python virtual environment in Ubuntu 16.04LTS or newer:

Make sure Python 3.6 or newer, python3-pip, and python3-venv are installed. Open a terminal and type the following command:

```shell
sudo apt install python3 python3-pip python3-venv
```

Create and activate a Python virtual environment:

```shell
python3 -m venv venv
source venv/bin/activate
```

Follow the remaining instructions in the Installation section at the top of this README to upgrade pip and install libratom.

## License(s)

Logos, documentation, and other non-software products of the RATOM team are distributed under the terms of Creative Commons 4.0 Attribution. Software items in RATOM repositories are distributed under the terms of the MIT License. See the LICENSE file for additional details.

&copy; 2020, The University of North Carolina at Chapel Hill.

## Development Team and Support

Developed by the RATOM team at the University of North Carolina at Chapel Hill.

See [https://ratom.web.unc.edu](https://ratom.web.unc.edu/) for additional project details, staff bios, and news.
