from itertools import chain
from os import path

import pytest

import codonPython.mesh as mesh


def mock_download(message_id, save_folder=None):
    if save_folder is not None:
        with open(path.join(save_folder, str(message_id)), "w") as file:
            file.write(str(message_id))
    return {
        "filename": message_id,
        "contents": message_id,
        "headers": {},
        "datafile": True,
    }


def mock_download_fail_auth(message_id, save_folder=None):
    raise mesh.MESHAuthenticationError


def mock_download_fail_gone(message_id, save_folder=None):
    raise mesh.MESHMessageAlreadyDownloaded


def mock_download_chooser_factory(auth_ids, gone_ids):
    def mock(message_id, save_folder=None):
        if message_id in auth_ids:
            return mock_download_fail_auth(message_id, save_folder)
        if message_id in gone_ids:
            return mock_download_fail_gone(message_id, save_folder)
        return mock_download(message_id, save_folder)

    return mock


def mock_inbox_factory(outputs_list):
    output_iter = (out for out in outputs_list)

    def mock_output(*args, **kwargs):
        try:
            return next(output_iter)
        except StopIteration:
            return []

    return mock_output


def mock_count_factory(counts_list):
    output_iter = (out for out in counts_list)

    def mock_output(*args, **kwargs):
        try:
            return next(output_iter)
        except StopIteration:
            return 0

    return mock_output


class Tracker:
    def __init__(self):
        self.count = 0
        self.data = []

    def inc(self, *args, **kwargs):
        self.count += 1
        self.data.append((args, kwargs))


@pytest.fixture
def track_ack(monkeypatch, mesh_connection):
    tracker = Tracker()
    monkeypatch.setattr(mesh_connection, "ack_download_message", tracker.inc)
    return tracker


@pytest.fixture
def patch_valid(monkeypatch, mesh_connection):
    monkeypatch.setattr(mesh_connection, "download_message", mock_download)
    monkeypatch.setattr(mesh_connection, "check_inbox_count", mock_count_factory([3]))
    monkeypatch.setattr(
        mesh_connection, "check_inbox", mock_inbox_factory([["1", "2", "3"]])
    )
    return mesh_connection


def test_CheckDownload_DownloadsCorrectSave(patch_valid, track_ack, tmpdir):
    p = tmpdir.mkdir("dl")
    out = patch_valid.check_and_download(save_folder=str(p), recursive=False)
    assert out is None
    assert p.join("1").read() == "1"
    assert p.join("2").read() == "2"
    assert p.join("3").read() == "3"
    assert track_ack.data == [(("1",), {}), (("2",), {}), (("3",), {})]


def test_CheckDownload_DownloadsCorrectGenerator(patch_valid, track_ack):
    out = patch_valid.check_and_download(save_folder=None, recursive=False)
    msg = next(out)
    assert msg == {"filename": "1", "contents": "1", "headers": {}, "datafile": True}
    msg = next(out)
    assert msg == {"filename": "2", "contents": "2", "headers": {}, "datafile": True}
    assert track_ack.data == [(("1",), {})]
    msg = next(out)
    assert msg == {"filename": "3", "contents": "3", "headers": {}, "datafile": True}
    assert track_ack.data == [(("1",), {}), (("2",), {})]
    with pytest.raises(StopIteration):
        msg = next(out)
    assert track_ack.data == [(("1",), {}), (("2",), {}), (("3",), {})]


@pytest.fixture
def patch_recurse(monkeypatch, mesh_connection):
    monkeypatch.setattr(mesh_connection, "download_message", mock_download)
    monkeypatch.setattr(
        mesh_connection, "check_inbox_count", mock_count_factory([501, 501, 1])
    )
    monkeypatch.setattr(
        mesh_connection,
        "check_inbox",
        mock_inbox_factory([["1", "2", "3"], ["4"], ["5"]]),
    )
    return mesh_connection


def test_CheckDownload_NoRecurseSave(patch_recurse, track_ack, tmpdir):
    p = tmpdir.mkdir("dl")
    out = patch_recurse.check_and_download(save_folder=str(p), recursive=False)
    assert out is None
    assert p.join("1").read() == "1"
    assert p.join("2").read() == "2"
    assert p.join("3").read() == "3"
    assert p.join("4").exists() is False
    assert p.join("5").exists() is False
    assert track_ack.data == [(("1",), {}), (("2",), {}), (("3",), {})]


def test_CheckDownload_RecurseSave(patch_recurse, track_ack, tmpdir):
    p = tmpdir.mkdir("dl")
    out = patch_recurse.check_and_download(save_folder=str(p), recursive=True)
    assert out is None
    assert p.join("1").read() == "1"
    assert p.join("2").read() == "2"
    assert p.join("3").read() == "3"
    assert p.join("4").read() == "4"
    assert p.join("5").read() == "5"
    assert track_ack.data == [
        (("1",), {}),
        (("2",), {}),
        (("3",), {}),
        (("4",), {}),
        (("5",), {}),
    ]


def test_CheckDownload_NoRecurseGen(patch_recurse, track_ack):
    out = patch_recurse.check_and_download(save_folder=None, recursive=False)
    msg = next(out)
    assert msg == {"filename": "1", "contents": "1", "headers": {}, "datafile": True}
    msg = next(out)
    assert msg == {"filename": "2", "contents": "2", "headers": {}, "datafile": True}
    assert track_ack.data == [(("1",), {})]
    msg = next(out)
    assert msg == {"filename": "3", "contents": "3", "headers": {}, "datafile": True}
    assert track_ack.data == [(("1",), {}), (("2",), {})]
    with pytest.raises(StopIteration):
        msg = next(out)
    assert track_ack.data == [(("1",), {}), (("2",), {}), (("3",), {})]


def test_CheckDownload_RecurseGen(patch_recurse, track_ack):
    out = patch_recurse.check_and_download(save_folder=None, recursive=True)
    msg = next(out)
    assert msg == {"filename": "1", "contents": "1", "headers": {}, "datafile": True}
    msg = next(out)
    assert msg == {"filename": "2", "contents": "2", "headers": {}, "datafile": True}
    assert track_ack.data == [(("1",), {})]
    msg = next(out)
    assert msg == {"filename": "3", "contents": "3", "headers": {}, "datafile": True}
    assert track_ack.data == [(("1",), {}), (("2",), {})]
    msg = next(out)
    assert msg == {"filename": "4", "contents": "4", "headers": {}, "datafile": True}
    assert track_ack.data == [(("1",), {}), (("2",), {}), (("3",), {})]
    msg = next(out)
    assert msg == {"filename": "5", "contents": "5", "headers": {}, "datafile": True}
    assert track_ack.data == [(("1",), {}), (("2",), {}), (("3",), {}), (("4",), {})]
    with pytest.raises(StopIteration):
        msg = next(out)
    assert track_ack.data == [
        (("1",), {}),
        (("2",), {}),
        (("3",), {}),
        (("4",), {}),
        (("5",), {}),
    ]


@pytest.fixture
def patch_errors(monkeypatch, mesh_connection):
    monkeypatch.setattr(
        mesh_connection,
        "download_message",
        mock_download_chooser_factory(["1", "2", "6"], ["3", "4", "9"]),
    )
    monkeypatch.setattr(
        mesh_connection, "check_inbox_count", mock_count_factory([501, 501, 1])
    )
    monkeypatch.setattr(
        mesh_connection,
        "check_inbox",
        mock_inbox_factory([["1", "2", "3", "4", "5"], ["6", "7"], ["8", "9"]]),
    )
    return mesh_connection


def test_CheckDownload_ErrorsNoRecurseSave(patch_errors, track_ack, tmpdir):
    p = tmpdir.mkdir("dl")
    with pytest.raises(mesh.MESHDownloadErrors) as exc:
        patch_errors.check_and_download(save_folder=str(p), recursive=False)
    assert exc.value.exceptions[0][0] == "1"
    assert type(exc.value.exceptions[0][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[1][0] == "2"
    assert type(exc.value.exceptions[1][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[2][0] == "3"
    assert type(exc.value.exceptions[2][1]) == mesh.MESHMessageAlreadyDownloaded
    assert exc.value.exceptions[3][0] == "4"
    assert type(exc.value.exceptions[3][1]) == mesh.MESHMessageAlreadyDownloaded
    assert len(exc.value.exceptions) == 4

    assert p.join("1").exists() is False
    assert p.join("2").exists() is False
    assert p.join("3").exists() is False
    assert p.join("4").exists() is False
    assert p.join("5").read() == "5"
    assert track_ack.data == [(("5",), {})]


def test_CheckDownload_ErrorsNoRecurseGen(patch_errors, track_ack):
    out = patch_errors.check_and_download(save_folder=None, recursive=False)
    msg = next(out)
    assert msg == {"filename": "5", "contents": "5", "headers": {}, "datafile": True}
    with pytest.raises(mesh.MESHDownloadErrors) as exc:
        msg = next(out)
    assert exc.value.exceptions[0][0] == "1"
    assert type(exc.value.exceptions[0][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[1][0] == "2"
    assert type(exc.value.exceptions[1][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[2][0] == "3"
    assert type(exc.value.exceptions[2][1]) == mesh.MESHMessageAlreadyDownloaded
    assert exc.value.exceptions[3][0] == "4"
    assert type(exc.value.exceptions[3][1]) == mesh.MESHMessageAlreadyDownloaded
    assert len(exc.value.exceptions) == 4

    assert track_ack.data == [(("5",), {})]


def test_CheckDownload_ErrorsRecurseSave(patch_errors, track_ack, tmpdir):
    p = tmpdir.mkdir("dl")
    with pytest.raises(mesh.MESHDownloadErrors) as exc:
        patch_errors.check_and_download(save_folder=str(p), recursive=True)
    assert exc.value.exceptions[0][0] == "1"
    assert type(exc.value.exceptions[0][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[1][0] == "2"
    assert type(exc.value.exceptions[1][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[2][0] == "3"
    assert type(exc.value.exceptions[2][1]) == mesh.MESHMessageAlreadyDownloaded
    assert exc.value.exceptions[3][0] == "4"
    assert type(exc.value.exceptions[3][1]) == mesh.MESHMessageAlreadyDownloaded
    assert exc.value.exceptions[4][0] == "6"
    assert type(exc.value.exceptions[4][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[5][0] == "9"
    assert type(exc.value.exceptions[5][1]) == mesh.MESHMessageAlreadyDownloaded
    assert len(exc.value.exceptions) == 6

    assert p.join("1").exists() is False
    assert p.join("2").exists() is False
    assert p.join("3").exists() is False
    assert p.join("4").exists() is False
    assert p.join("5").read() == "5"
    assert p.join("6").exists() is False
    assert p.join("7").read() == "7"
    assert p.join("8").read() == "8"
    assert p.join("9").exists() is False
    assert track_ack.data == [(("5",), {}), (("7",), {}), (("8",), {})]


def test_CheckDownload_ErrorsRecurseGen(patch_errors, track_ack):
    out = patch_errors.check_and_download(save_folder=None, recursive=True)
    msg = next(out)
    assert msg == {"filename": "5", "contents": "5", "headers": {}, "datafile": True}
    msg = next(out)
    assert msg == {"filename": "7", "contents": "7", "headers": {}, "datafile": True}
    assert track_ack.data == [(("5",), {})]
    msg = next(out)
    assert msg == {"filename": "8", "contents": "8", "headers": {}, "datafile": True}
    assert track_ack.data == [(("5",), {}), (("7",), {})]
    with pytest.raises(mesh.MESHDownloadErrors) as exc:
        msg = next(out)
    assert exc.value.exceptions[0][0] == "1"
    assert type(exc.value.exceptions[0][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[1][0] == "2"
    assert type(exc.value.exceptions[1][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[2][0] == "3"
    assert type(exc.value.exceptions[2][1]) == mesh.MESHMessageAlreadyDownloaded
    assert exc.value.exceptions[3][0] == "4"
    assert type(exc.value.exceptions[3][1]) == mesh.MESHMessageAlreadyDownloaded
    assert exc.value.exceptions[4][0] == "6"
    assert type(exc.value.exceptions[4][1]) == mesh.MESHAuthenticationError
    assert exc.value.exceptions[5][0] == "9"
    assert type(exc.value.exceptions[5][1]) == mesh.MESHMessageAlreadyDownloaded
    assert len(exc.value.exceptions) == 6

    assert track_ack.data == [(("5",), {}), (("7",), {}), (("8",), {})]


@pytest.fixture
def patch_many_errors(monkeypatch, mesh_connection):
    # This is for testing the early abort of the recursion if we hit 500 failed messages in one fetch
    # Failed messages will not be acknowledged, and will thus stay in the MESH system
    # If the issue is inherent to the message, and the inbox is full of messages with these issues
    # then we could enter an infinite loop without this abort
    monkeypatch.setattr(
        mesh_connection,
        "download_message",
        mock_download_chooser_factory(
            list(chain(range(300), range(500, 800))), list(range(1000, 1500))
        ),
    )
    monkeypatch.setattr(
        mesh_connection, "check_inbox_count", mock_count_factory([501, 501, 501, 1])
    )
    monkeypatch.setattr(
        mesh_connection,
        "check_inbox",
        mock_inbox_factory(
            [range(500), range(500, 1000), range(1000, 1500), range(1500, 1501)]
        ),
    )
    return mesh_connection


def test_CheckDownload_ErrorsEarlyTerminateSave(patch_many_errors, tmpdir, track_ack):
    p = tmpdir.mkdir("dl")
    with pytest.raises(mesh.MESHDownloadErrors) as exc:
        patch_many_errors.check_and_download(save_folder=p, recursive=True)
    assert len(exc.value.exceptions) == 1100
    for e, index in zip(
        exc.value.exceptions, chain(range(300), range(500, 800), range(1000, 1500))
    ):
        assert e[0] == index
    assert len(p.listdir()) == 400


def test_CheckDownload_ErrorsEarlyTerminateGen(patch_many_errors, track_ack):
    with pytest.raises(mesh.MESHDownloadErrors) as exc:
        for msg, index in zip(
            patch_many_errors.check_and_download(save_folder=None, recursive=True),
            chain(range(300, 500), range(800, 1000)),
        ):
            assert msg == {
                "filename": index,
                "contents": index,
                "headers": {},
                "datafile": True,
            }
    assert len(exc.value.exceptions) == 1100
    for e, index in zip(
        exc.value.exceptions, chain(range(300), range(500, 800), range(1000, 1500))
    ):
        assert e[0] == index
