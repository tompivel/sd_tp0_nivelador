package client

import (
	"encoding/binary"
	"io"
	
	"github.com/7574-sistemas-distribuidos/tp-nivelador/src/safe_socket"
)

const (
	OpBatch   = 0x01
	OpBatchAck = 0x02
	OpEnd     = 0x03
	OpWinners = 0x04
)

// SerializeBet empaqueta una apuesta en binario puro (sin delimitadores).
func SerializeBet(b *Bet) []byte {
	// Size: 4 (Agency) + 1 (NameLen) + N (Name) + 1 (LastLen) + M (Last) + 4 (Doc) + 10 (Date) + 4 (Number)
	nameLen := byte(len(b.FirstName))
	lastLen := byte(len(b.LastName))
	
	size := 4 + 1 + int(nameLen) + 1 + int(lastLen) + 4 + 10 + 4
	data := make([]byte, size)
	
	offset := 0
	binary.BigEndian.PutUint32(data[offset:], b.AgencyID)
	offset += 4
	
	data[offset] = nameLen
	offset += 1
	copy(data[offset:], b.FirstName)
	offset += int(nameLen)
	
	data[offset] = lastLen
	offset += 1
	copy(data[offset:], b.LastName)
	offset += int(lastLen)
	
	binary.BigEndian.PutUint32(data[offset:], b.Document)
	offset += 4
	
	copy(data[offset:], b.Birthdate)
	offset += 10
	
	binary.BigEndian.PutUint32(data[offset:], b.Number)
	
	return data
}

// DeserializeBet extrae una apuesta y retorna la apuesta junto con el total de bytes leídos.
func DeserializeBet(data []byte) (*Bet, int) {
	if len(data) < 24 { // Minimum possible size
		return nil, 0
	}
	
	offset := 0
	agencyID := binary.BigEndian.Uint32(data[offset:])
	offset += 4
	
	nameLen := int(data[offset])
	offset += 1
	firstName := string(data[offset : offset+nameLen])
	offset += nameLen
	
	lastLen := int(data[offset])
	offset += 1
	lastName := string(data[offset : offset+lastLen])
	offset += lastLen
	
	document := binary.BigEndian.Uint32(data[offset:])
	offset += 4
	
	birthdate := string(data[offset : offset+10])
	offset += 10
	
	number := binary.BigEndian.Uint32(data[offset:])
	offset += 4
	
	return &Bet{
		AgencyID:  agencyID,
		FirstName: firstName,
		LastName:  lastName,
		Document:  document,
		Birthdate: birthdate,
		Number:    number,
	}, offset
}

func SendMessage(conn io.Writer, opcode byte, payload []byte) error {
	header := make([]byte, 5)
	header[0] = opcode
	binary.BigEndian.PutUint32(header[1:], uint32(len(payload)))
	
	if err := safe_socket.SendAll(conn, header); err != nil {
		return err
	}
	if len(payload) > 0 {
		if err := safe_socket.SendAll(conn, payload); err != nil {
			return err
		}
	}
	return nil
}

func RecvMessage(conn io.Reader) (byte, []byte, error) {
	header, err := safe_socket.RecvAll(conn, 5)
	if err != nil {
		return 0, nil, err
	}
	
	opcode := header[0]
	length := binary.BigEndian.Uint32(header[1:])
	
	var payload []byte
	if length > 0 {
		payload, err = safe_socket.RecvAll(conn, int(length))
		if err != nil {
			return 0, nil, err
		}
	}
	
	return opcode, payload, nil
}
