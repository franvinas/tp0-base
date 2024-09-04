package common

import (
	"bytes"
	"encoding/binary"
	"strconv"
	"strings"
)

type Bet struct {
	Name      string
	Surname   string
	Document  uint32
	BirthDate string
	Number    uint32
}

func (bet Bet) Encode() []byte {
	buf := new(bytes.Buffer)

	nameBytes := []byte(bet.Name)
	if len(nameBytes) > 32 {
		nameBytes = nameBytes[:32]
	}
	buf.Write(nameBytes)
	if len(nameBytes) < 32 {
		buf.Write(make([]byte, 32-len(nameBytes)))
	}

	surnameBytes := []byte(bet.Surname)
	if len(surnameBytes) > 32 {
		surnameBytes = surnameBytes[:32]
	}
	buf.Write(surnameBytes)
	if len(surnameBytes) < 32 {
		buf.Write(make([]byte, 32-len(surnameBytes)))
	}

	binary.Write(buf, binary.LittleEndian, bet.Document)

	birthDateStr := strings.ReplaceAll(bet.BirthDate, "-", "")
	birthDateInt, _ := strconv.ParseUint(birthDateStr, 10, 32)
	binary.Write(buf, binary.LittleEndian, uint32(birthDateInt))

	binary.Write(buf, binary.LittleEndian, bet.Number)

	return buf.Bytes()
}

func ParseBet(line string) (Bet, error) {
	parts := strings.Split(line, ",")

	name := parts[0]
	surname := parts[1]
	document, err := strconv.ParseUint(parts[2], 10, 32)
	if err != nil {
		return Bet{}, err
	}
	birthDate := parts[3]
	number, err := strconv.ParseUint(parts[4], 10, 32)
	if err != nil {
		return Bet{}, err
	}

	bet := Bet{
		Name:      name,
		Surname:   surname,
		Document:  uint32(document),
		BirthDate: birthDate,
		Number:    uint32(number),
	}
	return bet, nil
}

func EncodeBatch(bets []Bet, agency string) []byte {
	buf := new(bytes.Buffer)

	agency_uint, _ := strconv.ParseUint(agency, 10, 8)
	binary.Write(buf, binary.LittleEndian, uint8(agency_uint))

	binary.Write(buf, binary.LittleEndian, uint8(len(bets)))

	for _, bet := range bets {
		buf.Write(bet.Encode())
	}

	return buf.Bytes()
}
