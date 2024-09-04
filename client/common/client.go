package common

import (
	"bufio"
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID             string
	ServerAddress  string
	LoopPeriod     time.Duration
	BatchMaxAmount int
}

// Client Entity that encapsulates how
type Client struct {
	config  ClientConfig
	conn    net.Conn
	running bool
	stop    chan bool
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config:  config,
		running: true,
		stop:    make(chan bool),
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	}
	c.conn = conn
	return nil
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() error {
	go c.handleSignals()

	fileName := fmt.Sprintf("data/agency-%s.csv", c.config.ID)
	file, err := os.Open(fileName)
	if err != nil {
		log.Criticalf("action: open_file | result: fail | error: %v", err)
		return err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for c.running {
		var bets []Bet

		for scanner.Scan() {
			line := scanner.Text()
			bet, err := ParseBet(line, c.config.ID)
			if err != nil {
				log.Errorf("action: parse_bet | result: fail | client_id: %v | error: %v", c.config.ID, err)
				break
			}
			bets = append(bets, bet)
			if len(bets) >= c.config.BatchMaxAmount {
				break
			}
		}
		if len(bets) == 0 {
			break
		}

		err := c.createClientSocket()
		if err != nil {
			return err
		}

		encoded_batch := EncodeBatch(bets)
		log.Debugf("action: send_batch | result: pending | client_id: %v | batch_size: %v", c.config.ID, len(encoded_batch))
		err = c.SendBytesToServer(encoded_batch)
		if err != nil {
			log.Errorf("action: send_batch | result: fail | client_id: %v | error: %v", c.config.ID, err)
			break
		}
		log.Infof("action: send_batch | result: success | client_id: %v | batch_size: %v", c.config.ID, len(encoded_batch))

		c.receiveConfirmation()
		log.Infof("action: batch_enviado | result: success | batch_size: %v", len(encoded_batch))

		// Wait a time between sending one message and the next one
		timer := time.NewTimer(c.config.LoopPeriod)
		select {
		case <-timer.C:
			continue
		case <-c.stop:
			log.Debugf("action: loop_stopped | result: success | client_id: %v", c.config.ID)
			return nil
		}

	}
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
	return nil
}

func (c *Client) SendBytesToServer(data []byte) error {
	log.Debugf("action: send_bytes | result: pending | client_id: %v | data_size: %v", c.config.ID, len(data))
	bytesWritten := 0
	dataLen := len(data)

	for bytesWritten < dataLen {
		n, err := c.conn.Write(data[bytesWritten:])
		if err != nil {
			return err
		}
		log.Debugf("action: send_bytes | result: success | client_id: %v | bytes_written: %v", c.config.ID, n)
		bytesWritten += n
		if bytesWritten >= dataLen {
			break
		}
	}

	return nil
}

func (c *Client) receiveConfirmation() {
	var data [1]byte
	_, err := c.conn.Read(data[:])
	if err != nil {
		log.Errorf("action: receive_confirmation | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return
	}
	msg := data[0]

	c.conn.Close()

	log.Infof("action: receive_confirmation | result: success | client_id: %v | message: %v",
		c.config.ID,
		msg,
	)
}

func (c *Client) handleSignals() {
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGTERM, syscall.SIGINT)
	sig := <-sigs
	log.Debugf("action: signal_received | signal: %v | client_id: %v", sig, c.config.ID)
	c.running = false
	c.conn.Close()
	c.stop <- true
}
