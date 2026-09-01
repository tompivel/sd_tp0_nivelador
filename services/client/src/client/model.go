package client

import (
	"fmt"
	"strconv"
	"strings"
)

type Bet struct {
	AgencyID  uint32
	FirstName string
	LastName  string
	Document  uint32
	Birthdate string // 10 chars YYYY-MM-DD
	Number    uint32
}

func NewBetFromCSV(line string, agencyID string) (*Bet, error) {
	parts := strings.Split(line, ",")
	if len(parts) != 5 {
		return nil, fmt.Errorf("invalid csv line: expected 5 parts, got %d", len(parts))
	}

	agencyIDInt, err := strconv.ParseUint(agencyID, 10, 32)
	if err != nil {
		return nil, fmt.Errorf("invalid agency id: %v", err)
	}

	document, err := strconv.ParseUint(parts[2], 10, 32)
	if err != nil {
		return nil, fmt.Errorf("invalid document: %v", err)
	}

	number, err := strconv.ParseUint(parts[4], 10, 32)
	if err != nil {
		return nil, fmt.Errorf("invalid number: %v", err)
	}

	return &Bet{
		AgencyID:  uint32(agencyIDInt),
		FirstName: parts[0],
		LastName:  parts[1],
		Document:  uint32(document),
		Birthdate: parts[3],
		Number:    uint32(number),
	}, nil
}

func (b *Bet) ToCSV() string {
	return fmt.Sprintf("%s,%s,%d,%s,%d", b.FirstName, b.LastName, b.Document, b.Birthdate, b.Number)
}
