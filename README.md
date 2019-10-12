![Logo](https://github.com/libratom/ratom-logos/raw/master/basic_variations/RATOM_Vector_Logo_v1_300px.png)

# libratom

[![PyPI version](https://badge.fury.io/py/libratom.svg)](https://badge.fury.io/py/libratom)
[![Build Status](https://travis-ci.org/libratom/libratom.svg?branch=master)](https://travis-ci.org/libratom/libratom)
[![codecov](https://codecov.io/gh/libratom/libratom/branch/master/graph/badge.svg)](https://codecov.io/gh/libratom/libratom)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e432a64a5b2d45c4b4747a82cc1c291c)](https://app.codacy.com/app/ratom/libratom?utm_source=github.com&utm_medium=referral&utm_content=libratom/libratom&utm_campaign=Badge_Grade_Dashboard)
[![Twitter Follow](https://img.shields.io/twitter/follow/RATOM_project.svg?style=social&label=Follow)](https://twitter.com/RATOM_Project)

Python library and supporting utilities to parse and process PST and MBOX email sources.

***This project is under development***

## Installation

Libratom requires Python 3.6 or newer, and can be installed via the Python Package Index (PyPI). Installing via **pip** will automatically install all required dependencies.

To install and test this software in a new Python virtual environment in Ubuntu 16.04LTS or newer:

Make sure Python 3.6 or newer, python3-pip, and python3-venv are installed:
```shell
sudo apt install python3 python3-pip python3-venv
```

Create and activate a Python virtual environment:
```shell
python3 -m venv venv
source venv/bin/activate
```

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

The schema contains 3 tables representing file information, message information and entity information.

In the entity table, text is the entity instance, label\_ is the entity type, filepath is the PST or mbox file associated with this entity. Full message and file information for each entity are also available through message_id and file_report_id respectively. Note that pff_identifier (a message ID specific to PST files) will not be populated for messages located in mbox files. Examples of how to query these tables can be found in the **Interactive examples** section near the end of this README.

## Advanced CLI uses

The CLI provides additional flags to tune performance, output location, and verbosity of the tool. Some example use cases are provided below.

To use a different entity model, use the --spacy-model flag. The following example directs the tool to use the multi-language model:

```shell
(venv) user@host:~$ ratom entities -p --spacy-model xx_ent_wiki_sm /path/to/PST-or-mbox-file-or-directory
```

To specify the number of jobs that may be run concurrently, use the -j flag. The following example sets the number of concurrent jobs to 2:

```shell
(venv) user@host:~$ ratom entities -p -j 2 /path/to/PST-or-mbox-file-or-directory
```

To change the name or location used for the sqlite3 output file, use the -o flag. Specifying a directory will result in the automatically named file being written to that path. Specifying a path that includes a filename will force the use of that filename. In the following example, the sqlite3 database will be named filename.db:

```shell
(venv) user@host:~$ ratom entities -p -o /path/to/directory/filename.db /path/to/PST-or-mbox-file-or-directory
```

To view more detailed output during the job (for example, if you encounter unexpected failures), you can increase the level of output verbosity with the -v flag. Additional v's increase verbosity. In the following example, we have increased verbosity to level 2:

```shell
(venv) user@host:~$ ratom entities -p -vv /path/to/PST-or-mbox-file-or-directory
```

## Interactive examples

More usage documentation will appear here as the project matures. For now, you can try out some of the functionality in Jupyter notebooks we've prepared at:

[https://github.com/libratom/ratom-notebooks](https://github.com/libratom/ratom-notebooks)

## License(s)

Logos, documentation, and other non-software products of the RATOM team are distributed under the terms of Creative Commons 4.0 Attribution. Software items in RATOM repositories are distributed under the terms of the MIT License. See the LICENSE file for additional details.

&copy; 2019, The University of North Carolina at Chapel Hill.

## Development Team and Support

Developed by the RATOM team at the University of North Carolina at Chapel Hill.

See [https://ratom.web.unc.edu](https://ratom.web.unc.edu/) for additional project details, staff bios, and news.
