import logging
import signal
import socket
import uuid

import common.utils as utils


class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._is_running = True
        self._clients = {}

        signal.signal(signal.SIGINT, self.__shutdown)
        signal.signal(signal.SIGTERM, self.__shutdown)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        while self._is_running:
            if client_sock := self.__accept_new_connection():
                client_id = uuid.uuid4()
                self._clients[client_id] = client_sock
                self.__handle_client_connection(client_sock)
                del self._clients[client_id]

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            chunks = []
            while chunk := client_sock.recv(4096):
                logging.debug(
                    f'action: receive_message | result: in_progress | chunk: {chunk}'
                )
                chunks.append(chunk)
                if b'\n' in chunk:
                    break

            msg = b''.join(chunks).rstrip().decode('utf-8')
            addr = client_sock.getpeername()
            logging.info(
                f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}'
            )
            bet = utils.decode_bet(msg)
            utils.store_bets([bet])

            confirmation_msg = 'OK\n'.encode('utf-8')
            total_sent = 0
            while total_sent < len(confirmation_msg):
                sent = client_sock.send(confirmation_msg[total_sent:])
                if sent == 0:
                    logging.error(
                        'action: receive_message | result: fail | error: Connection closed by client'
                    )
                    return
                total_sent += sent
        except OSError as e:
            logging.error('action: receive_message | result: fail | error: {e}')
        finally:
            if client_sock:
                client_sock.close()

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        if not self._is_running:
            return None
        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        try:
            c, addr = self._server_socket.accept()
        except OSError as e:
            if not self._is_running:
                return None
            logging.error(f'action: accept_connections | result: fail | error: {e}')
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        return c

    def __shutdown(self, signum, frame):
        """
        Graceful shutdown of the server on receiving a signal.
        """
        logging.debug(f'action: shutdown | result: in_progress | signal: {signum}')
        self._is_running = False
        self._server_socket.close()
        for client_sock in self._clients.values():
            client_sock.close()
