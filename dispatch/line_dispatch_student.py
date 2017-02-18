import time

from config.shell_scripts import SHOT

from common import *
from config.enums import Command, DataType


def end_msg(client, line):
    """
    Shows Desktop popup of received message
    :param client: clientprotocol
    :param line: line received
    :return:
    """
    message = '%s' % ' '.join(map(str, client.buffer))
    showDesktopMessage(message)
    client.buffer = []


def connection_refused(client, line):
    """
    Shoes Desktopmessage for connection refused
    :param client: clientprotocol
    :param line: line recieived
    :return:
    """
    showDesktopMessage('Connection refused!\n Client ID already taken!')
    client.factory.failcount = 100

def file_transfer_request(client, line):
    """
    Decides if a GET or a SEND operation needs to be dispatched and unboxes relevant attributes to be used in the actual
    sending/receiving functions
    :param client: ClientProtocol
    :param line: Line received from server
    :return:
    """
    client.file_data = clean_and_split_input(line)
    client.factory.files = get_file_list(client.factory.files_path)
    (trigger, task, filetype, filename, file_hash) = client.file_data[0:5]
    student_file_request_dispatcher[task](client, filetype, filename, file_hash)


def send_file_request(client, filetype, *args):
    """
    Dispatches Method to prepare requested file transfer and sends file
    :param client: clientprotocol
    :param filetype: Filetype to be sent as in (File, Folder, Screenshot)
    :param args: (filename, file_hash)
    :return:
    """
    filename = student_prepare_filetype_dispatcher[filetype](client, *args)
    client._sendFile(filename, filetype)


def get_file_request(client, *args):
    """
    Puts client into raw mode to receive files
    :param client: clientprotocol
    :param args:
    :return:
    """
    client = args[2]
    client.setRawMode()


def prepare_screenshot(client, filename, *args):
    """
    Prepares a screenshot to be sent
    :param client: clientprotocol
    :param filename: screenshot filename
    :param args: (file_hash, client)
    :return: filename
    """
    scriptfile = os.path.join(SCRIPTS_DIRECTORY, SHOT)
    screenshotfile = os.path.join(CLIENTSCREENSHOT_DIRECTORY, filename)
    command = "%s %s" % (scriptfile, screenshotfile)
    os.system(command)
    return filename


def prepare_folder(client, filename, *args):
    """
    Prepares requested folder to be sent as zip file
    :param client: clientprotocol
    :param filename: folder archive filename
    :param args: (file_hash, client)
    :return: filename
    """
    if filename in client.factory.files:
        target_folder = client.factory.files[filename[0]]
        output_filename = os.path.join(CLIENTZIP_DIRECTORY, filename)
        shutil.make_archive(output_filename, 'zip', target_folder)
        return "%s.zip" % filename


def prepare_abgabe(client, filename, *args):
    """
    Prepares Abgabe to be sent as zip archive
    :param client: clientprotocol
    :param filename: filename of abgabe archive
    :param args: (file_hash, client)
    :return: filename
    """
    client._triggerAutosave()
    time.sleep(2)  # what
    target_folder = ABGABE_DIRECTORY
    output_filename = os.path.join(CLIENTZIP_DIRECTORY, filename)
    shutil.make_archive(output_filename, 'zip', target_folder)  # create zip of folder
    return "%s.zip" % filename  # this is the filename of the zip file


"""
Dispatcher dictionaries, used to dispatch correct methods depending on Command/DataType received
"""
student_line_dispatcher = {
    Command.ENDMSG: end_msg,
    Command.REFUSED: connection_refused,
    Command.FILETRANSFER: file_transfer_request,

}

student_file_request_dispatcher = {
    Command.SEND: send_file_request,
    Command.GET: get_file_request
}

student_prepare_filetype_dispatcher = {
    DataType.SCREENSHOT: prepare_screenshot,
    DataType.FOLDER: prepare_folder,
    DataType.ABGABE: prepare_abgabe
}
