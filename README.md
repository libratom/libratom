![Logo](https://github.com/libratom/ratom-logos/blob/master/basic_variations/RATOM_Vector_Logo_v1_300px.png)

# libratom

[![Build Status](https://travis-ci.org/libratom/libratom.svg?branch=master)](https://travis-ci.org/libratom/libratom)
[![codecov](https://codecov.io/gh/libratom/libratom/branch/master/graph/badge.svg)](https://codecov.io/gh/libratom/libratom)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e432a64a5b2d45c4b4747a82cc1c291c)](https://app.codacy.com/app/ratom/libratom?utm_source=github.com&utm_medium=referral&utm_content=libratom/libratom&utm_campaign=Badge_Grade_Dashboard)

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

Libratom provides a CLI with planned support for a range of email processing tasks. Currently, the CLI supports entity extraction from individual PST files and directories of PST files. 

To see available commands, type:

```shell
(venv) user@host:~$ ratom -h
```

To see detailed help for the entity extraction command, type:

```shell
(venv) user@host:~$ ratom entities -h
```

To run the extractor with default settings over a PST file or directory of PST files, type the following:

```shell
(venv) user@host:~$ ratom entities -p /path/to/PST-file-or-directory
```

Progress is displayed in a bar at the bottom of the window. To terminate a job early and shut down all workers, type Ctrl-C.

By default, the tool will use the spaCy en\_core\_web\_sm model, and will start as many concurrent jobs as there are virtual cores available. Entities are written to a sqlite3 file automatically named using the existing file or directory name and current datetime stamp, and with the following single-table schema:

```shell
sqlite> .schema
CREATE TABLE entities (
	id INTEGER NOT NULL, 
	text VARCHAR, 
	label_ VARCHAR, 
	filename VARCHAR, 
	message_id INTEGER, 
	PRIMARY KEY (id)
);
```

In this schema, id is the primary key, text is the entity instance, label\_ is the entity type, filename is the PST file associated with this message and entity instance, message\_id is the PST-internal identifier for the message.

## Additional libratom use cases

More usage documentation will appear here as the project matures. For now, you can try out some of the functionality in Jupyter notebooks we've prepared at:

[https://github.com/libratom/ratom-notebooks](https://github.com/libratom/ratom-notebooks)

## License(s)

Logos, documentation, and other non-software products of the RATOM team are distributed under the terms of Creative Commons 4.0 Attribution. Software items in RATOM repositories are distributed under the terms of the MIT License. See the LICENSE file for additional details.

## Development Team and Support

Product of the RATOM team. See [https://ratom.web.unc.edu](https://ratom.web.unc.edu/) for up to date information.
