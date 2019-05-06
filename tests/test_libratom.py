# pylint: disable=missing-docstring
import libratom
from libratom.utils.pff import PffArchive


def test_version():
    assert libratom.__version__


def test_extract_plain_text_messages(enron_dataset_part003):

    # Get the first PST file of this enron subset
    pst_file = next(enron_dataset_part003.glob('*.pst'))

    with PffArchive(pst_file) as archive:
        for message in archive.messages():
            assert message.plain_text_body
