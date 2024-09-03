package common

import (
	"bytes"
	"encoding/binary"
	"strconv"
	"strings"
)

type Bet struct {
	Agency    uint8
	Name      string
	Surname   string
	Document  uint32
	BirthDate string
	Number    uint32
}

func (bet Bet) Encode() []byte {
	buf := new(bytes.Buffer)

	binary.Write(buf, binary.LittleEndian, bet.Agency)

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
