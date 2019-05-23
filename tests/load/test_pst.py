# pylint: disable=missing-docstring

from libratom.utils.pff import PffArchive


def test_extract_enron_messages(enron_dataset):

    for pst_file in enron_dataset.glob("**/*.pst"):
        with PffArchive(pst_file) as archive:
            for message in archive.messages():
                assert archive.format_message(message)
