import csv
import datetime
import struct
import time


""" Bets storage location. """
STORAGE_FILEPATH = "./bets.csv"
""" Simulated winner number in the lottery contest. """
LOTTERY_WINNER_NUMBER = 7574

ENCODED_BET_SIZE = 76


""" A lottery bet registry. """
class Bet:
    def __init__(self, agency: str, first_name: str, last_name: str, document: str, birthdate: str, number: str):
        """
        agency must be passed with integer format.
        birthdate must be passed with format: 'YYYY-MM-DD'.
        number must be passed with integer format.
        """
        self.agency = int(agency)
        self.first_name = first_name
        self.last_name = last_name
        self.document = document
        self.birthdate = datetime.date.fromisoformat(birthdate)
        self.number = int(number)

""" Checks whether a bet won the prize or not. """
def has_won(bet: Bet) -> bool:
    return bet.number == LOTTERY_WINNER_NUMBER

"""
Persist the information of each bet in the STORAGE_FILEPATH file.
Not thread-safe/process-safe.
"""
def store_bets(bets: list[Bet]) -> None:
    with open(STORAGE_FILEPATH, 'a+') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_MINIMAL)
        for bet in bets:
            writer.writerow([bet.agency, bet.first_name, bet.last_name,
                             bet.document, bet.birthdate, bet.number])

"""
Loads the information all the bets in the STORAGE_FILEPATH file.
Not thread-safe/process-safe.
"""
def load_bets() -> list[Bet]:
    with open(STORAGE_FILEPATH, 'r') as file:
        reader = csv.reader(file, quoting=csv.QUOTE_MINIMAL)
        for row in reader:
            yield Bet(row[0], row[1], row[2], row[3], row[4], row[5])


"""
Decodes a bet from a string to a Bet object.
"""
def decode_bet(encoded_bet: bytes, agency: str) -> Bet:
    LITTLE_ENDIAN_UINT = '<I'

    if len(encoded_bet) != ENCODED_BET_SIZE:
        raise ValueError("Invalid encoded bet size")

    first_name = encoded_bet[:32].decode('utf-8').rstrip('\x00')
    last_name = encoded_bet[32:64].decode('utf-8').rstrip('\x00')
    document = struct.unpack(LITTLE_ENDIAN_UINT, encoded_bet[64:68])[0]
    birthdate_int = struct.unpack(LITTLE_ENDIAN_UINT, encoded_bet[68:72])[0]
    birthdate_str = str(birthdate_int)
    birthdate = f'{birthdate_str[:4]}-{birthdate_str[4:6]}-{birthdate_str[6:8]}'

    number = struct.unpack(LITTLE_ENDIAN_UINT, encoded_bet[72:])[0]

    return Bet(agency, first_name, last_name, document, birthdate, number)
