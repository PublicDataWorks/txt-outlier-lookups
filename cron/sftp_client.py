import paramiko
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SFTPServerClient:
    def __init__(self, hostname, port, username, password):
        self.__hostName = hostname
        self.__port = port
        self.__userName = username
        self.__password = password
        self.__SSH_Client = paramiko.SSHClient()
        self.__SFTP_Client = None

    def connect(self):
        try:
            self.__SSH_Client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.__SSH_Client.connect(
                hostname=self.__hostName,
                port=self.__port,
                username=self.__userName,
                password=self.__password,
                look_for_keys=False,
                allow_agent=False
            )
            self.__SFTP_Client = self.__SSH_Client.open_sftp()
        except Exception as excp:
            logger.error(f"Failed to connect to server {self.__hostName}:{self.__port}: {str(excp)}")
            raise Exception(excp)
        else:
            print(f"Connected to server {self.__hostName}:{self.__port} as {self.__userName}.")

    def disconnect(self):
        if self.__SFTP_Client:
            self.__SFTP_Client.close()
        self.__SSH_Client.close()
        print(f"{self.__userName} is disconnected to server {self.__hostName}:{self.__port}")

    def get_file_list(self, directory_path):
        try:
            file_list = self.__SFTP_Client.listdir(directory_path)
            return file_list
        except Exception as e:
            print(f"Failed to get file list: {str(e)}")
            return []

    def download_file(self, remote_file_path, local_file_path):
        try:
            self.__SFTP_Client.get(remote_file_path, local_file_path)
            print(f"Downloaded file from {remote_file_path} to {local_file_path}")
        except Exception as e:
            print(f"Failed to download file: {str(e)}")
