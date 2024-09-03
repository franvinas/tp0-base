package common

import (
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
	ID            string
	ServerAddress string
	LoopPeriod    time.Duration
}

// Client Entity that encapsulates how
type Client struct {
	config  ClientConfig
	conn    net.Conn
	bets    []Bet
	running bool
	stop    chan bool
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig, bets []Bet) *Client {
	client := &Client{
		config:  config,
		bets:    bets,
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
func (c *Client) StartClientLoop() {
	go c.handleSignals()

	for i := 0; i < len(c.bets); i++ {
		if !c.running {
			log.Debugf("action: loop_stopped | result: success | client_id: %v", c.config.ID)
			return
		}

		err := c.createClientSocket()
		if err != nil {
			return
		}

		bet := c.bets[i]
		encoded_bet := bet.Encode()
		log.Debugf("action: send_bet | result: pending | client_id: %v | bet: %s", c.config.ID, encoded_bet)
		err = c.SendBytesToServer(encoded_bet)
		if err != nil {
			log.Errorf("action: send_bet | result: fail | client_id: %v | error: %v", c.config.ID, err)
			break
		}
		log.Infof("action: send_bet | result: success | client_id: %v | bet: %v", c.config.ID, bet.Encode())

		c.receiveConfirmation()

		// Wait a time between sending one message and the next one
		timer := time.NewTimer(c.config.LoopPeriod)
		select {
		case <-timer.C:
			continue
		case <-c.stop:
			log.Debugf("action: loop_stopped | result: success | client_id: %v", c.config.ID)
			return
		}

	}
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

func (c *Client) SendBytesToServer(data []byte) error {
	bytesWritten := 0
	dataLen := len(data)

	for bytesWritten < dataLen {
		n, err := c.conn.Write(data[bytesWritten:])
		if err != nil {
			return err
		}
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
