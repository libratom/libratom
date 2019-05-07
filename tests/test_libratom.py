# pylint: disable=missing-docstring
import pytest

import libratom
from libratom.utils.pff import PffArchive


def test_version():
    assert libratom.__version__


def test_pffarchive_load_from_file_object(sample_pst_file):

    with sample_pst_file.open(mode='rb') as f, PffArchive(f) as archive:
        assert len([message for message in archive.messages()]) == 2668


def test_pffarchive_load_from_invalid_type():

    with pytest.raises(TypeError):
        _ = PffArchive(1)


@pytest.mark.parametrize("bfs", [False, True])
def test_pffarchive_iterate_over_messages(sample_pst_file, bfs):

    with PffArchive(sample_pst_file) as archive:
        for message in archive.messages(bfs=bfs):
            assert message.plain_text_body
