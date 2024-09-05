import logging
import signal
import socket
import uuid

import common.utils as utils


class Server:
    def __init__(self, port, listen_backlog, total_agencies):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._total_agencies = total_agencies
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
                self._clients[client_id] = {'socket': client_sock}
                self.__handle_client_connection(client_sock, client_id)
                if not self._clients[client_id].get('wating_winners'):
                    if client_sock:
                        client_sock.close()
                    del self._clients[client_id]

            if len(self._clients) == self._total_agencies and all(
                [client['wating_winners'] for client in self._clients.values()]
            ):
                winners = utils.draw_winners()
                winners_by_agency = {}
                for winner in winners:
                    if winner.agency not in winners_by_agency:
                        winners_by_agency[winner.agency] = []
                    winners_by_agency[winner.agency].append(winner)
                for client in self._clients.values():
                    agency_winners = winners_by_agency.get(client['agency'], [])
                    logging.debug(
                        f'action: send_winners | result: in_progress | agency: {client["agency"]} | winners: {len(agency_winners)}'
                    )
                    encoded_winners = utils.encode_winners(agency_winners)
                    client['socket'].sendall(encoded_winners)

                for client in self._clients.values():
                    if client['socket']:
                        client['socket'].close()
                self._clients.clear()

    def __handle_client_connection(self, client_sock, client_id):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        max_batch_size = (8 * 1024 - 2) // utils.ENCODED_BET_SIZE
        try:
            chunks = []
            bytes_received = 0
            max_bytes_to_receive = utils.ENCODED_BET_SIZE * max_batch_size + 2
            agency_id, batch_size = None, None

            while bytes_received < max_bytes_to_receive:
                chunk = client_sock.recv(max_bytes_to_receive - bytes_received)
                if not chunk:
                    break
                logging.debug(
                    f'action: receive_message | result: in_progress | chunk_size: {len(chunk)}'
                )
                bytes_received += len(chunk)
                if agency_id is None:
                    agency_id = chunk[0]
                    batch_size = chunk[1]
                    max_bytes_to_receive = utils.ENCODED_BET_SIZE * batch_size + 2
                    chunk = chunk[2:]
                    wating_winners = batch_size == 0
                    self._clients[client_id].update(
                        {'agency': agency_id, 'wating_winners': wating_winners}
                    )
                    if wating_winners:
                        addr = client_sock.getpeername()
                        logging.debug(
                            f'action: ready_for_winners | result: success | ip: {addr[0]} | agency: {agency_id}'
                        )
                        return
                chunks.append(chunk)

            encoded_bets = b''.join(chunks)
            addr = client_sock.getpeername()
            logging.info(
                f'action: receive_message | result: success | ip: {addr[0]} | agency: {agency_id} | bets_size: {len(encoded_bets)} | bets_count: {len(encoded_bets) / utils.ENCODED_BET_SIZE}'
            )
            bets = [
                utils.decode_bet(
                    encoded_bets[i : i + utils.ENCODED_BET_SIZE],
                    agency_id,
                )
                for i in range(0, len(encoded_bets), utils.ENCODED_BET_SIZE)
            ]

            utils.store_bets(bets)
            logging.info(
                f'action: apuesta_almacenada | result: success | bets_count: {len(bets)}'
            )

            confirmation_data = 1
            confirmation_byte = confirmation_data.to_bytes(1, byteorder='little')
            sent = client_sock.send(confirmation_byte)
            if sent == 0:
                logging.error(
                    'action: receive_message | result: fail | error: Connection closed by client'
                )
                return
        except OSError as e:
            logging.error('action: receive_message | result: fail | error: {e}')

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
        for client in self._clients.values():
            if client['socket']:
                client['socket'].close()
        self._clients.clear()
        logging.debug('action: shutdown | result: success')
