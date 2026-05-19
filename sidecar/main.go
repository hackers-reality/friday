package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	server := flag.String("server", "localhost:8090", "FRIDAY server WebSocket URL")
	token := flag.String("token", "", "JWT authentication token")
	name := flag.String("name", "", "Sidecar name (default: hostname)")
	port := flag.Int("port", 8095, "HTTP fallback server port")
	flag.Parse()

	if *token == "" {
		*token = os.Getenv("FRIDAY_SIDECAR_TOKEN")
	}

	if *name == "" {
		hostname, _ := os.Hostname()
		*name = hostname
	}

	log.SetFlags(log.LstdFlags | log.Lmicroseconds | log.Lshortfile)

	log.Printf("========================================")
	log.Printf("  FRIDAY Sidecar")
	log.Printf("  Name:       %s", *name)
	log.Printf("  Server:     %s", *server)
	log.Printf("  HTTP Port:  %d", *port)
	log.Printf("========================================")

	initAuth()
	initClipboard()

	caps := DiscoverCapabilities()

	ws := NewSidecarWS(*server, *token, *name, caps)
	go ws.Run()

	go StartHTTPServer(*port)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM, os.Interrupt)
	sig := <-sigCh
	log.Printf("[SIDECAR] Received signal %v, shutting down...", sig)

	ws.Close()
	time.Sleep(200 * time.Millisecond)
	log.Printf("[SIDECAR] Bye")
}
