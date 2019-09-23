import mailbox
from typing import Union

class MboxArchive:
    def __init__(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def load(self, file: Union[Path, IOBase, str]) -> None:

        if isinstance(file, IOBase):
            self.data.open_file_object(file)
        elif isinstance(file, (Path, str)):
            self.data.open(str(file), "rb")
        else:
            raise TypeError(f"Unable to load {file} of type {type(file)}")

    @property
    def message_count(self) -> int:
        """
        Returns the total number of messages in the mailbox
        """

        return len(self.mailbox)