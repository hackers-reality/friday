//go:build !windows

package main

import (
	"fmt"
	"log"
)

func testClipboard() bool {
	log.Printf("[CLIPBOARD] Not available on this platform")
	return false
}

func clipboardGet() (string, error) {
	return "", fmt.Errorf("clipboard not available on this platform")
}

func clipboardSet(text string) error {
	return fmt.Errorf("clipboard not available on this platform")
}
