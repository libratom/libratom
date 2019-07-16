from pathlib import Path
import click


# https://github.com/pallets/click/issues/405#issuecomment-470812067
class PathPath(click.Path):
    """A Click path argument that returns a pathlib Path, not a string"""
    def convert(self, value, param, ctx):
        return Path(super().convert(value, param, ctx))


def validate_out_path(ctx, param, value):
    if value and value.is_file():
        raise click.BadParameter(f'{value} already exists')

    return value
