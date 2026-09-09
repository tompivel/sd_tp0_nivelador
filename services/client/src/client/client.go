package client

import (
	"os"
	"os/signal"
	"syscall"
	"sync/atomic"
	"net"
	"time"
	"bufio"
	"fmt"
	"strconv"
	"github.com/7574-sistemas-distribuidos/tp-nivelador/src/logger"
)

const CONNECTION_ATTEMPTS_MAX = 10
const CONNECTION_ATTEMPS_DELAY_MS = 1000

type ClientConfig struct {
	ServerHost string
	ServerPort string
	InputFile  string
	OutputFile string
	AgencyId   string
	BatchSize  int
}

type Client struct {
	conn   net.Conn
	config ClientConfig
}

func NewClient(config ClientConfig) (*Client, error) {
	conn, err := connectToServer(config.ServerHost, config.ServerPort)
	if err != nil {
		logger.Warn("connect-to-server", logger.Fail)
		return nil, err
	}

	client := &Client{conn: conn, config: config}
	return client, nil
}

func connectToServer(host, port string) (net.Conn, error) {
	const action = "connect-to-server"
	var err error
	var conn net.Conn

	logger.Info(action, logger.InProgress)
	for i := range CONNECTION_ATTEMPTS_MAX {
		conn, err = net.Dial("tcp", host+":"+port)
		if err != nil {
			logger.Warn(action, logger.Fail, "attempt", i)
			time.Sleep(CONNECTION_ATTEMPS_DELAY_MS * time.Millisecond)
			continue
		}

		logger.Info(action, logger.Success)
		break
	}

	return conn, err
}

func (client *Client) setupSignalHandler() (chan struct{}, *atomic.Bool) {
	shuttingDown := &atomic.Bool{}
	done := make(chan struct{})
	
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGTERM)
	go func() {
		select {
		case <-sigs:
			logger.Info("shutdown", logger.InProgress, "Received SIGTERM, closing connection to abort pending operations")
			shuttingDown.Store(true)
			client.conn.Close()
		case <-done:
			return
		}
	}()
	
	return done, shuttingDown
}

func (client *Client) Run() (err error) {
	const mainAction = "run_client"
	
	done, shuttingDown := client.setupSignalHandler()
	defer close(done)
	
	defer func() {
		if shuttingDown.Load() {
			err = nil // Graceful exit if SIGTERM signaled
		}
	}()
	
	defer client.conn.Close()

	if err := client.processBetsFile(mainAction); err != nil {
		return err
	}
	
	// EOF
	if err := SendMessage(client.conn, OpEnd, nil); err != nil {
		return err
	}
	
	if err := client.receiveAndSaveWinners(); err != nil {
		return err
	}

	logger.Info(mainAction, logger.Success, "agency-id", client.config.AgencyId)
	return nil
}

func (client *Client) processBetsFile(action string) error {
	inputFile, err := os.Open(client.config.InputFile)
	if err != nil {
		logger.Error("open-input-file", logger.Fail, "err", err)
		return err
	}
	defer inputFile.Close()

	scanner := bufio.NewScanner(inputFile)
	
	expectedAgencyID, _ := strconv.ParseUint(client.config.AgencyId, 10, 32)
	batch := &Batch{AgencyID: uint32(expectedAgencyID)}
	
	for scanner.Scan() {
		line := scanner.Text()
		bet, err := NewBetFromCSV(line, client.config.AgencyId)
		if err != nil {
			logger.Error("parse-bet", logger.Fail, "err", err)
			continue
		}
		
		batch.Bets = append(batch.Bets, bet)
		
		if len(batch.Bets) >= client.config.BatchSize {
			if err := client.flushBatch(batch, action); err != nil {
				return err
			}
			batch.Bets = nil
		}
	}

	if err := scanner.Err(); err != nil {
		logger.Error("read-input-file", logger.Fail, "err", err)
		return err
	}
	
	return client.flushBatch(batch, action)
}

func (client *Client) flushBatch(batch *Batch, action string) error {
	if len(batch.Bets) == 0 {
		return nil
	}
	
	payload := SerializeBatch(batch)
	
	logger.Info(action, logger.InProgress, "agency-id", client.config.AgencyId, "sending-batch", len(batch.Bets))
	
	if err := SendMessage(client.conn, OpBatch, payload); err != nil {
		return err
	}
	
	opcode, _, err := RecvMessage(client.conn)
	if err != nil {
		return err
	}
	
	switch opcode {
	case OpBatchAck:
		return nil
	default:
		return fmt.Errorf("unexpected opcode %d, expected OpBatchAck", opcode)
	}
}

func (client *Client) receiveAndSaveWinners() error {
	outputFile, err := os.Create(client.config.OutputFile)
	if err != nil {
		logger.Error("open-output-file", logger.Fail, "err", err)
		return err
	}
	defer outputFile.Close()

	opcode, payload, err := RecvMessage(client.conn)
	if err != nil {
		return err
	}
	
	switch opcode {
	case OpWinners:
		batch, err := DeserializeBatch(payload)
		if err != nil {
			return err
		}
		
		expectedAgencyID, _ := strconv.ParseUint(client.config.AgencyId, 10, 32)
		if len(batch.Bets) > 0 && batch.AgencyID != uint32(expectedAgencyID) {
			return fmt.Errorf("received winners batch for different agency: %d", batch.AgencyID)
		}
		
		for _, bet := range batch.Bets {
			if _, err := outputFile.WriteString(bet.ToCSV() + "\n"); err != nil {
				return err
			}
		}
	default:
		return fmt.Errorf("unexpected opcode %d, expected OpWinners", opcode)
	}
	return nil
}
