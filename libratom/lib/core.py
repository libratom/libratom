# pylint: disable=missing-docstring,broad-except,import-outside-toplevel

import itertools
import json
import logging
from email import policy
from email.generator import Generator
from email.parser import Parser
from importlib import reload
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

import requests
import spacy
import thinc
from pkg_resources import load_entry_point
from requests import HTTPError
from spacy.language import Language

from libratom.lib import EmlArchive, MboxArchive, PffArchive
from libratom.lib.base import Archive, AttachmentMetadata
from libratom.lib.constants import RATOM_SPACY_MODEL_MAX_LENGTH, SPACY_MODEL_NAMES
from libratom.lib.exceptions import FileTypeError
from libratom.lib.pff import pff_msg_to_string

logger = logging.getLogger(__name__)

EXTENSION_TYPE_MAPPING = {
    ".pst": PffArchive,
    ".ost": PffArchive,
    ".mbox": MboxArchive,
    ".eml": EmlArchive,
}

_cached_spacy_models = {}


def get_ratom_settings() -> List[Tuple[str, Union[int, str]]]:
    return [
        (key, value) for key, value in globals().items() if key.startswith("RATOM_")
    ]


def open_mail_archive(path: Path) -> Optional[Archive]:
    try:
        archive_class = EXTENSION_TYPE_MAPPING[path.suffix]
    except KeyError as exc:
        raise FileTypeError(f"Unable to open {path}. Unsupported file type.") from exc

    return archive_class(path)


def get_set_of_files(path: Path) -> Set[Path]:
    if path.is_dir():
        valid_mail_files = itertools.chain(
            *[path.glob(f"**/*{extension}") for extension in EXTENSION_TYPE_MAPPING]
        )
        return set(valid_mail_files)

    return {path}


def get_spacy_models() -> Dict[str, List[str]]:

    releases = {}

    paginated_url = "https://api.github.com/repos/explosion/spacy-models/releases?page=1&per_page=100"

    try:
        while paginated_url:
            response = requests.get(url=paginated_url, timeout=(6.05, 30))

            if not response.ok:
                response.raise_for_status()

            # Get name-version pairs
            for release in json.loads(response.content):
                name, version = release["tag_name"].split("-", maxsplit=1)

                # Skip alpha/beta versions
                if "a" in version or "b" in version:
                    continue

                releases[name] = [*releases.get(name, []), version]

            # Get the next page of results
            try:
                paginated_url = response.links["next"]["url"]
            except (AttributeError, KeyError):
                break

    except HTTPError:
        releases = {name: [] for name in SPACY_MODEL_NAMES}

    return releases


def get_cached_spacy_model(name: str) -> Optional[Language]:
    """
    Returns a cached preloaded spaCy model
    """

    try:
        return _cached_spacy_models[name]
    except KeyError:
        model = _cached_spacy_models[name] = load_spacy_model(name)

    return model


def load_spacy_model(spacy_model_name: str) -> Optional[Language]:
    """
    Loads and returns a given spaCy model

    If the model is not present, an attempt will be made to download and install it
    """

    try:
        spacy_model = spacy.load(spacy_model_name)

    except OSError as exc:
        logger.info(f"Unable to load spacy model {spacy_model_name}")

        if "E050" in str(exc):
            # https://github.com/explosion/spaCy/blob/v2.1.6/spacy/errors.py#L207
            # Model not found, try installing it
            logger.info(f"Downloading {spacy_model_name}")

            from spacy.cli.download import msg as spacy_msg

            # Download quietly
            spacy_msg.no_print = True
            try:
                spacy.cli.download(spacy_model_name, False, False, "--quiet")
            except SystemExit:
                logger.error(f"Unable to install spacy model {spacy_model_name}")
                return None

            # Specific steps for transformer models (very brittle and likely not permanent)
            if spacy_model_name.endswith("_trf"):

                # If we just installed a transformer model along with spacy-transformers in a child process
                # we need to set up an entry point for spacy-transformers in the current process.
                # This entry point will be registered as a pipeline factory function by the model's language class.
                load_entry_point("spacy-transformers", "spacy_factories", "transformer")

                # If Pytorch was also just installed, certain modules that depend on it
                # may need reloading to work in the current process
                reload(thinc.util)
                reload(thinc.shims.pytorch)
                reload(thinc.shims.pytorch_grad_scaler)

            # Now try loading the model again
            spacy_model = spacy.load(spacy_model_name)

        else:
            logger.exception(exc)
            return None

    # Set text length limit for model
    spacy_model.max_length = RATOM_SPACY_MODEL_MAX_LENGTH

    return spacy_model


def export_messages_from_file(
    src_file: Path, msg_ids: Iterable[int], dest_folder: Path = None
) -> None:
    """
    Writes .eml files in a destination directory given a mailbox file (PST or mbox) and a list of message IDs
    """

    dest_folder = (dest_folder or Path.cwd()) / src_file.stem
    dest_folder.mkdir(parents=True, exist_ok=True)

    with open_mail_archive(src_file) as archive:
        for msg_id in msg_ids:
            try:
                # Get message from archive
                msg = archive.get_message_by_id(int(msg_id))

                # Process PST or MBOX message and attachments
                if isinstance(archive, MboxArchive):
                    # Extract attachments
                    attachments = [
                        AttachmentMetadata(
                            name=part.get_filename(),
                            content=part.get_payload(decode=True),
                        )
                        for part in msg.walk()
                        if (
                            content_disposition := part.get_content_disposition() or ""
                        ).startswith("attachment")
                        or content_disposition.startswith("inline")
                    ]

                    if attachments:
                        # Make directory for this message's attachments
                        attachments_folder = dest_folder / f"{msg_id}_attachments"
                        attachments_folder.mkdir(parents=True, exist_ok=True)

                        # Write files
                        for attachment in attachments:
                            (attachments_folder / attachment.name).write_bytes(
                                attachment.content
                            )

                else:  # PST archive
                    if msg.number_of_attachments > 0:
                        # Make directory for this message's attachments
                        attachments_folder = dest_folder / f"{msg_id}_attachments"
                        attachments_folder.mkdir(parents=True, exist_ok=True)

                        # Extract attachments and write files
                        for attachment in msg.attachments:
                            buffer = attachment.read_buffer(attachment.size)
                            (attachments_folder / attachment.name).write_bytes(buffer)

                    # Convert message to Python Message type
                    msg = Parser(policy=policy.default).parsestr(pff_msg_to_string(msg))

                # Write message as eml file
                with (dest_folder / f"{msg_id}.eml").open(
                    mode="w", encoding="utf-8", errors="replace"
                ) as eml_file:
                    Generator(eml_file).flatten(msg)

            except Exception as exc:
                logger.warning(
                    f"Skipping message {msg_id} from {src_file}, reason: {exc}",
                    exc_info=True,
                )
