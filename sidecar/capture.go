package main

import (
	"bytes"
	"errors"
	"fmt"
	"image"
	"image/png"
	"log"
	"sync"
	"time"

	"github.com/kbinani/screenshot"
)

var (
	captureMu          sync.Mutex
	lastCaptureTime    time.Time
	captureMinInterval = 2 * time.Second
)

func numActiveDisplays() int {
	return screenshot.NumActiveDisplays()
}

func CaptureMonitor(index int) ([]byte, error) {
	captureMu.Lock()
	defer captureMu.Unlock()

	if time.Since(lastCaptureTime) < captureMinInterval {
		return nil, errors.New("rate limited: please wait before next capture")
	}

	n := screenshot.NumActiveDisplays()
	if index < 0 || index >= n {
		return nil, fmt.Errorf("invalid monitor index %d (have %d)", index, n)
	}

	bounds := screenshot.GetDisplayBounds(index)
	img, err := screenshot.CaptureRect(bounds)
	if err != nil {
		return nil, fmt.Errorf("capture monitor %d: %w", index, err)
	}

	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		return nil, fmt.Errorf("encode png: %w", err)
	}

	lastCaptureTime = time.Now()
	log.Printf("[CAPTURE] Monitor %d: %dx%d %d bytes", index, bounds.Dx(), bounds.Dy(), buf.Len())
	return buf.Bytes(), nil
}

func CaptureScreen() ([]byte, int, int, error) {
	captureMu.Lock()
	defer captureMu.Unlock()

	if time.Since(lastCaptureTime) < captureMinInterval {
		return nil, 0, 0, errors.New("rate limited: please wait before next capture")
	}

	n := screenshot.NumActiveDisplays()
	if n == 0 {
		return nil, 0, 0, errors.New("no displays found")
	}

	minX, minY, maxX, maxY := 0, 0, 0, 0
	for i := 0; i < n; i++ {
		b := screenshot.GetDisplayBounds(i)
		if i == 0 || b.Min.X < minX {
			minX = b.Min.X
		}
		if i == 0 || b.Min.Y < minY {
			minY = b.Min.Y
		}
		if b.Max.X > maxX {
			maxX = b.Max.X
		}
		if b.Max.Y > maxY {
			maxY = b.Max.Y
		}
	}

	bounds := image.Rect(minX, minY, maxX, maxY)
	img, err := screenshot.CaptureRect(bounds)
	if err != nil {
		return nil, 0, 0, fmt.Errorf("capture all: %w", err)
	}

	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		return nil, 0, 0, fmt.Errorf("encode png: %w", err)
	}

	lastCaptureTime = time.Now()
	width := bounds.Dx()
	height := bounds.Dy()
	log.Printf("[CAPTURE] All monitors: %dx%d %d bytes", width, height, buf.Len())
	return buf.Bytes(), width, height, nil
}
