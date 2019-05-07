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


def test_pffarchive_iterate_over_folders_dfs(sample_pst_file):

    with PffArchive(sample_pst_file) as archive:
        for message in archive.messages(bfs=False):
            assert message.plain_text_body


def test_pffarchive_iterate_over_messages(sample_pst_file):

    with PffArchive(sample_pst_file) as archive:
        for message in archive.messages():
            assert message.plain_text_body
