## Contributing Guidelines

Thank you for your interest in contributing to libratom. We look forward to your pull request. This document describes the main aspects of our development and review process.

Whenever a pull request is submitted or updated it triggers a build in our [CI environment](https://travis-ci.org/github/libratom/libratom). The build must be successful before the pull request can be reviewed.

#### Local Setup
The first thing you will likely want to do after you've forked libratom and cloned it locally is to set up a development environment. You can follow or adapt the steps below (from the root libratom directory):
1. Create and activate a virtual environment
    ```
    python -m venv libratom_dev_env
    source libratom_dev_env/bin/activate
    ```
2. Make sure pip is up to date
    ```
    pip install --upgrade pip
    ```
3. Install the development dependencies
   ```
   pip install -r requirements-dev.txt
   ```
4. Install the local source code
    ```
   pip install -e ./
   ```
   
We use [tox](https://tox.readthedocs.io/en/latest/) to run our test suite. We recommend that you run tox locally before submitting a pull request. It will run static analysis tools first and the test suite second. See our [tox.ini](https://github.com/libratom/libratom/blob/main/tox.ini) file for details.

#### Code Style
We use [black](https://black.readthedocs.io/en/stable/) as our code formatter. You can run it locally before committing or set it as a pre-commit hook. If necessary you can turn off formatting for a specific block of code with `# fmt: off` and back on with `# fmt: on`.

You will also need to run `isort libratom tests` before committing, also possibly as a pre-commit hook. See isort's [documentation](https://pycqa.github.io/isort/) for more information.

#### Type Hints
Type hints are optional but we encourage you to use them, as we do in most of the codebase. In situations where importing types causes cyclic imports you can use [forward references](https://www.python.org/dev/peps/pep-0484/#forward-references) or [delayed evaluation](https://www.python.org/dev/peps/pep-0563/).

#### Docstrings
##### Module Docstrings
Required. Please write a brief description of the module's contents unless its name is self-explanatory, e.g. `constants.py`.

##### Class and Method Docstrings
Required for classes and public methods. For method docstrings please describe the purpose of the method's parameters and returned value, not their types. Use type hints to specify types.

##### Function Docstrings
Optional. Function docstrings can help the code review process, but for internal code that's subject to change we don't require them. We prefer that you use type hints and keep the functions short and simple. 

#### Static Analysis
Both flake8 and pylint must run without issue (meaning a pylint score of 10/10).

This can mean fixing the code or adjusting the linter. Especially with pylint. As long as you can provide a rationale for it you are welcome to edit the rules in .pylintrc, or to silence it temporarily with `# pylint: disable=XXX` comments.

Where to include linter silencing comments is up to you. Technically it is preferable to have them inline or at the block level to limit their scope, but some might argue that it clutters the code. Having them at the top of the module keeps the code cleaner at the expense of granularity. It's also fine to use a mix of the two: some issues silenced module-wide and some inline.

#### Unit Tests
Any new code is expected to come tested and covered. If you need to test an internal piece of code that depends on its context or a hard to reach code path, don't hesitate to use mock objects/functions for the context.

The coverage targets are 90% overall, 85% for the code introduced in a pull request. The few parts of the codebase currently not covered are mostly hard to reach exception handling code.

We use [pytest](https://docs.pytest.org/en/stable/) as our testing library. Pytest is very powerful and allows you to cover a lot of test cases efficiently. It also introduces its own concepts and idioms. If you come from the standard unittest library you may want to familiarize yourself with pytest before writing tests.

