package client

import (
	"encoding/binary"
	"io"
	
	"github.com/7574-sistemas-distribuidos/tp-nivelador/src/safe_socket"
)

const (
	// Protocol Operation Types
	OpBatch   = 0x01
	OpBatchAck = 0x02
	OpEnd     = 0x03
	OpWinners = 0x04
	// Protocol Parameter Sizes
	HEADER_SIZE = 5
	OP_CODE_SIZE = 1
	PAYLOAD_SIZE = 4
	AGENCY_SIZE = 4
	NAME_LEN_SIZE = 1
	LAST_LEN_SIZE = 1
	USER_ID_SIZE = 4
	BIRTH_DATE_SIZE = 10
	CODE_SIZE = 4
	BET_MIN_SIZE = 24
)

// SerializeBet packets a bet binarily (no delimeters).
func SerializeBet(b *Bet) []byte {
	// Bet Size: 4 (Agency) + 1 (NameLen) + N (Name) + 1 (LastLen) + M (Last) + 4 (Doc) + 10 (Date) + 4 (Number)
	nameLen := byte(len(b.FirstName))
	lastLen := byte(len(b.LastName))
	
	size := AGENCY_SIZE + NAME_LEN_SIZE + int(nameLen) + LAST_LEN_SIZE + int(lastLen) + USER_ID_SIZE + BIRTH_DATE_SIZE + CODE_SIZE
	data := make([]byte, size)
	
	offset := 0
	binary.BigEndian.PutUint32(data[offset:], b.AgencyID)
	offset += AGENCY_SIZE
	
	data[offset] = nameLen
	offset += NAME_LEN_SIZE
	copy(data[offset:], b.FirstName)
	offset += int(nameLen)
	
	data[offset] = lastLen
	offset += LAST_LEN_SIZE
	copy(data[offset:], b.LastName)
	offset += int(lastLen)
	
	binary.BigEndian.PutUint32(data[offset:], b.Document)
	offset += USER_ID_SIZE
	
	copy(data[offset:], b.Birthdate)
	offset += BIRTH_DATE_SIZE 
	
	binary.BigEndian.PutUint32(data[offset:], b.Number)
	
	return data
}

// DeserializeBet extracts a bet and returns it with the number of bytes read.
func DeserializeBet(data []byte) (*Bet, int) {
	if len(data) < BET_MIN_SIZE { 
		return nil, 0
	}
	
	offset := 0
	agencyID := binary.BigEndian.Uint32(data[offset:])
	offset += AGENCY_SIZE
	
	nameLen := int(data[offset])
	offset += NAME_LEN_SIZE
	if offset+nameLen > len(data) {
		return nil, 0
	}
	firstName := string(data[offset : offset+nameLen])
	offset += nameLen
	
	if offset >= len(data) {
		return nil, 0
	}
	lastLen := int(data[offset])
	offset += LAST_LEN_SIZE
	if offset+lastLen > len(data) {
		return nil, 0
	}
	lastName := string(data[offset : offset+lastLen])
	offset += lastLen
	
	if offset+ USER_ID_SIZE > len(data) {
		return nil, 0
	}
	document := binary.BigEndian.Uint32(data[offset:])
	offset += USER_ID_SIZE
	
	if offset + BIRTH_DATE_SIZE > len(data) {
		return nil, 0
	}
	birthdate := string(data[offset : offset+ BIRTH_DATE_SIZE])
	offset += BIRTH_DATE_SIZE
	
	if offset + CODE_SIZE > len(data) {
		return nil, 0
	}
	number := binary.BigEndian.Uint32(data[offset:])
	offset += CODE_SIZE
	
	return &Bet{
		AgencyID:  agencyID,
		FirstName: firstName,
		LastName:  lastName,
		Document:  document,
		Birthdate: birthdate,
		Number:    number,
	}, offset
}

// DeserializeBatch parses an array of bets from a single payload block.
func DeserializeBatch(payload []byte) []*Bet {
	var bets []*Bet
	offset := 0
	for offset < len(payload) {
		bet, read := DeserializeBet(payload[offset:])
		if read == 0 {
			break
		}
		offset += read
		bets = append(bets, bet)
	}
	return bets
}

func SendMessage(conn io.Writer, opcode byte, payload []byte) error {
	msg := make([]byte, HEADER_SIZE +len(payload))
	msg[0] = opcode
	binary.BigEndian.PutUint32(msg[OP_CODE_SIZE:HEADER_SIZE], uint32(len(payload)))
	
	if len(payload) > 0 {
		copy(msg[HEADER_SIZE:], payload)
	}
	
	return safe_socket.SendAll(conn, msg)
}

func RecvMessage(conn io.Reader) (byte, []byte, error) {
	header, err := safe_socket.RecvAll(conn, HEADER_SIZE)
	if err != nil {
		return 0, nil, err
	}
	
	opcode := header[0]
	length := binary.BigEndian.Uint32(header[OP_CODE_SIZE:])
	
	var payload []byte
	if length > 0 {
		payload, err = safe_socket.RecvAll(conn, int(length))
		if err != nil {
			return 0, nil, err
		}
	}
	
	return opcode, payload, nil
}
