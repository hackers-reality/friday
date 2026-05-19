package main

import (
	"log"
	"runtime"
)

func DiscoverCapabilities() []string {
	caps := []string{}

	if isScreenCaptureAvailable() {
		caps = append(caps, "screen_capture")
	}

	if runtime.GOOS == "windows" {
		caps = append(caps, "clipboard")
	}

	caps = append(caps, "exec", "filesystem", "system_info")

	log.Printf("[DISCOVER] Platform: %s/%s, Capabilities: %v", runtime.GOOS, runtime.GOARCH, caps)
	return caps
}

func isScreenCaptureAvailable() bool {
	defer func() {
		if r := recover(); r != nil {
			log.Printf("[DISCOVER] Screen capture not available: %v", r)
		}
	}()

	n := numActiveDisplays()
	return n > 0
}
