package main

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type CommandRequest struct {
	ID      string         `json:"id"`
	Command string         `json:"command"`
	Params  map[string]any `json:"params"`
}

type captureResult struct {
	data   []byte
	width  int
	height int
}

type outboundMsg struct {
	msgType int
	data    []byte
}

type commandHandler func(params map[string]any) (any, error)

var commandHandlers = map[string]commandHandler{
	"ping":            handlePingCmd,
	"capture_screen":  handleCaptureScreenCmd,
	"capture_monitor": handleCaptureMonitorCmd,
	"clipboard_get":   handleClipboardGetCmd,
	"clipboard_set":   handleClipboardSetCmd,
	"exec":            handleExecCmd,
	"system_info":     handleSystemInfoCmd,
	"processes":       handleProcessesCmd,
	"active_window":   handleActiveWindowCmd,
	"file_read":       handleFileReadCmd,
	"file_write":      handleFileWriteCmd,
	"file_list":       handleFileListCmd,
	"file_delete":     handleFileDeleteCmd,
	"capabilities":    handleCapabilitiesCmd,
}

func handlePingCmd(params map[string]any) (any, error) {
	return map[string]any{"status": "pong", "timestamp": time.Now().Unix()}, nil
}

func handleCapabilitiesCmd(params map[string]any) (any, error) {
	return map[string]any{"capabilities": DiscoverCapabilities()}, nil
}

func handleCaptureScreenCmd(params map[string]any) (any, error) {
	data, width, height, err := CaptureScreen()
	if err != nil {
		return nil, err
	}
	return &captureResult{data: data, width: width, height: height}, nil
}

func handleCaptureMonitorCmd(params map[string]any) (any, error) {
	index := 0
	if i, ok := params["index"]; ok {
		switch v := i.(type) {
		case float64:
			index = int(v)
		}
	}
	data, width, height, err := CaptureMonitor(index)
	if err != nil {
		return nil, err
	}
	return &captureResult{data: data, width: width, height: height}, nil
}

func handleClipboardGetCmd(params map[string]any) (any, error) {
	text, err := ClipboardGet()
	if err != nil {
		return nil, err
	}
	return map[string]any{"text": text}, nil
}

func handleClipboardSetCmd(params map[string]any) (any, error) {
	text, _ := params["text"].(string)
	if text == "" {
		return nil, fmt.Errorf("text parameter required")
	}
	if err := ClipboardSet(text); err != nil {
		return nil, err
	}
	return map[string]any{"status": "ok"}, nil
}

func handleExecCmd(params map[string]any) (any, error) {
	cmd, _ := params["cmd"].(string)
	if cmd == "" {
		cmd, _ = params["command"].(string)
	}
	if cmd == "" {
		return nil, fmt.Errorf("cmd or command parameter required")
	}
	timeout := 30
	if t, ok := params["timeout"]; ok {
		switch v := t.(type) {
		case float64:
			timeout = int(v)
		}
	}
	return ExecuteCommand(cmd, timeout), nil
}

func handleSystemInfoCmd(params map[string]any) (any, error) {
	return GetSystemInfo(), nil
}

func handleProcessesCmd(params map[string]any) (any, error) {
	return GetProcesses(), nil
}

func handleActiveWindowCmd(params map[string]any) (any, error) {
	return GetActiveWindow(), nil
}

func handleFileReadCmd(params map[string]any) (any, error) {
	path, _ := params["path"].(string)
	if path == "" {
		return nil, fmt.Errorf("path parameter required")
	}
	content, err := ReadFile(path)
	if err != nil {
		return nil, err
	}
	return map[string]any{"content": content, "path": path}, nil
}

func handleFileWriteCmd(params map[string]any) (any, error) {
	path, _ := params["path"].(string)
	content, _ := params["content"].(string)
	if path == "" {
		return nil, fmt.Errorf("path parameter required")
	}
	if err := WriteFile(path, content); err != nil {
		return nil, err
	}
	return map[string]any{"status": "ok", "path": path}, nil
}

func handleFileListCmd(params map[string]any) (any, error) {
	path, _ := params["path"].(string)
	if path == "" {
		path = "."
	}
	entries, err := ListDir(path)
	if err != nil {
		return nil, err
	}
	return map[string]any{"entries": entries, "path": path}, nil
}

func handleFileDeleteCmd(params map[string]any) (any, error) {
	path, _ := params["path"].(string)
	if path == "" {
		return nil, fmt.Errorf("path parameter required")
	}
	if err := DeleteFile(path); err != nil {
		return nil, err
	}
	return map[string]any{"status": "ok", "path": path}, nil
}

type SidecarWS struct {
	serverURL   string
	token       string
	name        string
	caps        []string
	conn        *websocket.Conn
	mu          sync.RWMutex
	writeCh     chan outboundMsg
	done        chan struct{}
	backoffTime time.Duration
}

func NewSidecarWS(serverURL, token, name string, caps []string) *SidecarWS {
	return &SidecarWS{
		serverURL: serverURL,
		token:     token,
		name:      name,
		caps:      caps,
		writeCh:   make(chan outboundMsg, 256),
		done:      make(chan struct{}),
	}
}

func (s *SidecarWS) Run() {
	s.backoffTime = 0
	for {
		if err := s.connect(); err != nil {
			wait := s.nextBackoff()
			log.Printf("[WS] Connect failed: %v, retry in %v", err, wait)
			time.Sleep(wait)
			continue
		}
		s.resetBackoff()
		log.Printf("[WS] Connected to %s as %s", s.serverURL, s.name)
		s.runConnected()
	}
}

func (s *SidecarWS) connect() error {
	u, err := url.Parse(s.serverURL)
	if err != nil {
		return fmt.Errorf("parse URL: %w", err)
	}
	u.Path = "/ws/sidecar"
	if u.Scheme == "http" {
		u.Scheme = "ws"
	} else if u.Scheme == "https" {
		u.Scheme = "wss"
	}

	header := http.Header{}
	header.Set("Authorization", "Bearer "+s.token)
	header.Set("X-Sidecar-Name", s.name)
	header.Set("X-Sidecar-Caps", strings.Join(s.caps, ","))

	dialer := *websocket.DefaultDialer
	dialer.HandshakeTimeout = 10 * time.Second

	conn, _, err := dialer.Dial(u.String(), header)
	if err != nil {
		return fmt.Errorf("dial: %w", err)
	}

	s.mu.Lock()
	s.conn = conn
	s.mu.Unlock()
	return nil
}

func (s *SidecarWS) getConn() *websocket.Conn {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.conn
}

func (s *SidecarWS) runConnected() {
	readDone := make(chan struct{})
	writeDone := make(chan struct{})

	go s.readLoop(readDone)
	go s.writeLoop(writeDone)
	go s.heartbeatLoop()
	go s.serverPongLoop()

	select {
	case <-readDone:
	case <-writeDone:
	}

	s.mu.Lock()
	if s.conn != nil {
		s.conn.Close()
		s.conn = nil
	}
	s.mu.Unlock()
}

func (s *SidecarWS) readLoop(done chan<- struct{}) {
	defer close(done)
	defer func() {
		if r := recover(); r != nil {
			log.Printf("[WS] Read panic: %v", r)
		}
	}()

	for {
		conn := s.getConn()
		if conn == nil {
			return
		}

		_, msg, err := conn.ReadMessage()
		if err != nil {
			if !websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
				log.Printf("[WS] Read error: %v", err)
			}
			return
		}

		var req CommandRequest
		if err := json.Unmarshal(msg, &req); err != nil {
			log.Printf("[WS] Invalid JSON: %v", err)
			continue
		}

		s.handleCommand(req)
	}
}

func (s *SidecarWS) handleCommand(req CommandRequest) {
	defer func() {
		if r := recover(); r != nil {
			log.Printf("[CMD] Panic %s/%s: %v", req.Command, req.ID, r)
			s.sendJSON(req.ID, false, nil, fmt.Sprintf("internal error"))
		}
	}()

	handler, ok := commandHandlers[req.Command]
	if !ok {
		s.sendJSON(req.ID, false, nil, "unknown command: "+req.Command)
		return
	}

	result, err := handler(req.Params)
	if err != nil {
		s.sendJSON(req.ID, false, nil, err.Error())
		return
	}

	if cr, ok := result.(*captureResult); ok {
		s.sendBinary(req.ID, cr.data)
		s.sendJSON(req.ID, true, map[string]any{
			"width":  cr.width,
			"height": cr.height,
			"size":   len(cr.data),
		}, "")
		return
	}

	s.sendJSON(req.ID, true, result, "")
}

func (s *SidecarWS) writeLoop(done chan<- struct{}) {
	defer close(done)
	defer func() {
		if r := recover(); r != nil {
			log.Printf("[WS] Write panic: %v", r)
		}
	}()

	for {
		select {
		case <-s.done:
			return
		case msg := <-s.writeCh:
			conn := s.getConn()
			if conn == nil {
				continue
			}
			if err := conn.WriteMessage(msg.msgType, msg.data); err != nil {
				log.Printf("[WS] Write error: %v", err)
				return
			}
		}
	}
}

func (s *SidecarWS) heartbeatLoop() {
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-s.done:
			return
		case <-ticker.C:
			if s.getConn() == nil {
				return
			}
			s.sendJSON("heartbeat", true, map[string]any{
				"status":    "alive",
				"name":      s.name,
				"timestamp": time.Now().Unix(),
			}, "")
		}
	}
}

func (s *SidecarWS) serverPongLoop() {
	conn := s.getConn()
	if conn == nil {
		return
	}
	conn.SetPongHandler(func(string) error {
		return nil
	})
}

func (s *SidecarWS) sendJSON(id string, success bool, result any, errMsg string) {
	resp := map[string]any{
		"id":      id,
		"success": success,
	}
	if result != nil {
		resp["result"] = result
	}
	if errMsg != "" {
		resp["error"] = errMsg
	}

	data, err := json.Marshal(resp)
	if err != nil {
		log.Printf("[WS] Marshal error: %v", err)
		return
	}
	s.writeCh <- outboundMsg{msgType: websocket.TextMessage, data: data}
}

func (s *SidecarWS) sendBinary(id string, data []byte) {
	idBytes := []byte(id)
	frame := make([]byte, 4+len(idBytes)+len(data))
	binary.BigEndian.PutUint32(frame[:4], uint32(len(idBytes)))
	copy(frame[4:], idBytes)
	copy(frame[4+len(idBytes):], data)
	s.writeCh <- outboundMsg{msgType: websocket.BinaryMessage, data: frame}
}

func (s *SidecarWS) nextBackoff() time.Duration {
	if s.backoffTime == 0 {
		s.backoffTime = 1 * time.Second
	} else {
		s.backoffTime *= 2
		if s.backoffTime > 60*time.Second {
			s.backoffTime = 60 * time.Second
		}
	}
	return s.backoffTime
}

func (s *SidecarWS) resetBackoff() {
	s.backoffTime = 0
}

func (s *SidecarWS) Close() {
	select {
	case <-s.done:
	default:
		close(s.done)
	}
	s.mu.Lock()
	if s.conn != nil {
		s.conn.Close()
		s.conn = nil
	}
	s.mu.Unlock()
}

func StartHTTPServer(port int) {
	if port <= 0 {
		return
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"alive","name":"sidecar"}`))
	})
	addr := fmt.Sprintf(":%d", port)
	log.Printf("[HTTP] Fallback listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Printf("[HTTP] Server error: %v", err)
	}
}
