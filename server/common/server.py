import logging
import signal
import socket
from multiprocessing.pool import ThreadPool
from threading import Event

import common.utils as utils
from common.bets_vault import BetsVault
from common.thread_safe_set import ThreadSafeSet


class Server:
    def __init__(self, port, listen_backlog, total_agencies):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._total_agencies = total_agencies
        self._is_running = True
        self._winners = None
        self._agencies_waiting = ThreadSafeSet()
        self._all_agencies_waiting = Event()
        self._bets_vault = BetsVault()

        signal.signal(signal.SIGINT, self.__shutdown)
        signal.signal(signal.SIGTERM, self.__shutdown)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        with ThreadPool(processes=6) as pool:
            while self._is_running:
                if client_sock := self.__accept_new_connection():
                    pool.apply_async(self.__handle_client_connection, (client_sock,))

    def __wait_for_winners(self, agency_id, client_sock):
        logging.debug(
            f'action: ready_for_winners | result: success | agency: {agency_id}'
        )
        waiting_count = self._agencies_waiting.add(agency_id)
        if waiting_count == self._total_agencies:
            self._winners = self._bets_vault.draw_winners()
            self._all_agencies_waiting.set()
        else:
            self._all_agencies_waiting.wait()

        agency_winners = [
            winner for winner in self._winners if winner.agency == agency_id
        ]
        logging.debug(
            f'action: send_winners | result: in_progress | agency: {agency_id} | winners: {len(agency_winners)}'
        )

        encoded_winners = utils.encode_winners(agency_winners)
        client_sock.sendall(encoded_winners)
        addr = client_sock.getpeername()
        logging.info(
            f'action: send_winners | result: success | ip: {addr[0]} | agency: {agency_id} | winners: {len(agency_winners)}'
        )
        self._agencies_waiting.remove(agency_id)
        if len(self._agencies_waiting) == 0:
            self._all_agencies_waiting.clear()
            self._winners = None

    def __decode_bets(self, encoded_bets, agency_id):
        return [
            utils.decode_bet(
                encoded_bets[i : i + utils.ENCODED_BET_SIZE],
                agency_id,
            )
            for i in range(0, len(encoded_bets), utils.ENCODED_BET_SIZE)
        ]

    def __send_confirmation(self, client_sock):
        confirmation_data = 1
        confirmation_byte = confirmation_data.to_bytes(1, byteorder='little')
        sent = self.__send_bytes(client_sock, confirmation_byte)
        if sent != 1:
            return False
        return True

    def __handle_client_connection(self, client_sock: socket.socket):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            agency_id, batch_size = None, None
            data = self.__read_bytes(client_sock, 2)
            if not data or len(data) != 2:
                logging.error(
                    'action: receive_message | result: fail | error: Connection closed by client'
                )
                return

            agency_id = data[0]
            batch_size = data[1]
            if batch_size == 0:
                # if batch_size is 0, it means that the agency is ready to receive winners
                self.__wait_for_winners(agency_id, client_sock)
                return

            bytes_to_receive = utils.ENCODED_BET_SIZE * batch_size
            encoded_bets = self.__read_bytes(client_sock, bytes_to_receive)
            if not encoded_bets:
                logging.error(
                    f'action: receive_message | result: fail | error: Connection closed by client | agency: {agency_id}'
                )
                return

            addr = client_sock.getpeername()
            logging.info(
                f'action: receive_message | result: success | ip: {addr[0]} | agency: {agency_id} | bets_size: {len(encoded_bets)} | bets_count: {len(encoded_bets) / utils.ENCODED_BET_SIZE}'
            )
            bets = self.__decode_bets(encoded_bets, agency_id)

            self._bets_vault.store_bets(bets)
            logging.info(
                f'action: apuesta_almacenada | result: success | bets_count: {len(bets)} | agency: {agency_id}'
            )

            sent = self.__send_confirmation(client_sock)
            if not sent:
                logging.error(
                    f'action: receive_message | result: fail | error: Connection closed by client | agency: {agency_id}'
                )
                return
            logging.debug(
                f'action: send_confirmation | result: success | ip: {addr[0]} | agency: {agency_id}'
            )
        except OSError as e:
            logging.error('action: receive_message | result: fail | error: {e}')
        finally:
            if client_sock:
                client_sock.close()
                logging.debug('action: close_connection | result: success')

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

    def __read_bytes(self, sock: socket.socket, size: int):
        data = []
        total_read = 0
        while total_read < size:
            chunk = sock.recv(size - total_read)
            if not chunk:
                return None
            data.append(chunk)
            total_read += len(chunk)
        return b''.join(data)

    def __send_bytes(self, sock: socket.socket, data: bytes):
        logging.debug(f'action: send_bytes | result: in_progress | bytes: {len(data)}')
        sent = 0
        while sent < len(data):
            sent += sock.send(data[sent:])
        return sent

    def __shutdown(self, signum, frame):
        """
        Graceful shutdown of the server on receiving a signal.
        """
        logging.debug(f'action: shutdown | result: in_progress | signal: {signum}')
        self._is_running = False
        self._server_socket.close()
