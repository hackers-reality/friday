//go:build windows

package main

import (
	"fmt"
	"log"
	"syscall"
	"unsafe"
)

var (
	user32           = syscall.NewLazyDLL("user32.dll")
	kernel32         = syscall.NewLazyDLL("kernel32.dll")
	procOpenClipboard      = user32.NewProc("OpenClipboard")
	procCloseClipboard     = user32.NewProc("CloseClipboard")
	procGetClipboardData   = user32.NewProc("GetClipboardData")
	procSetClipboardData   = user32.NewProc("SetClipboardData")
	procEmptyClipboard     = user32.NewProc("EmptyClipboard")
	procGlobalLock         = kernel32.NewProc("GlobalLock")
	procGlobalUnlock       = kernel32.NewProc("GlobalUnlock")
	procGlobalAlloc        = kernel32.NewProc("GlobalAlloc")
	procGlobalSize         = kernel32.NewProc("GlobalSize")
)

const (
	CF_UNICODETEXT = 13
	GMEM_MOVEABLE  = 0x0002
	GMEM_ZEROINIT  = 0x0040
)

func testClipboard() bool {
	ret, _, _ := procOpenClipboard.Call(0)
	if ret == 0 {
		log.Printf("[CLIPBOARD] OpenClipboard test failed")
		return false
	}
	procCloseClipboard.Call()
	log.Printf("[CLIPBOARD] Available")
	return true
}

func clipboardGet() (string, error) {
	ret, _, _ := procOpenClipboard.Call(0)
	if ret == 0 {
		return "", fmt.Errorf("open clipboard: %v", syscall.GetLastError())
	}
	defer procCloseClipboard.Call()

	h, _, _ := procGetClipboardData.Call(CF_UNICODETEXT)
	if h == 0 {
		return "", nil
	}

	ptr, _, _ := procGlobalLock.Call(h)
	if ptr == 0 {
		return "", fmt.Errorf("global lock: %v", syscall.GetLastError())
	}
	defer procGlobalUnlock.Call(h)

	size, _, _ := procGlobalSize.Call(h)
	if size == 0 {
		return "", nil
	}

	buf := make([]uint16, size/2)
	copy(buf, unsafe.Slice((*uint16)(unsafe.Pointer(ptr)), len(buf)))

	text := syscall.UTF16ToString(buf)
	return text, nil
}

func clipboardSet(text string) error {
	ret, _, _ := procOpenClipboard.Call(0)
	if ret == 0 {
		return fmt.Errorf("open clipboard: %v", syscall.GetLastError())
	}
	defer procCloseClipboard.Call()

	procEmptyClipboard.Call()

	utf16, err := syscall.UTF16FromString(text)
	if err != nil {
		return fmt.Errorf("utf16 encode: %w", err)
	}

	size := len(utf16) * 2
	h, _, _ := procGlobalAlloc.Call(GMEM_MOVEABLE|GMEM_ZEROINIT, uintptr(size))
	if h == 0 {
		return fmt.Errorf("global alloc: %v", syscall.GetLastError())
	}

	ptr, _, _ := procGlobalLock.Call(h)
	if ptr == 0 {
		return fmt.Errorf("global lock: %v", syscall.GetLastError())
	}
	copy(unsafe.Slice((*byte)(unsafe.Pointer(ptr)), size), unsafe.Slice((*byte)(unsafe.Pointer(&utf16[0])), size))
	procGlobalUnlock.Call(h)

	ret, _, _ = procSetClipboardData.Call(CF_UNICODETEXT, h)
	if ret == 0 {
		return fmt.Errorf("set clipboard data: %v", syscall.GetLastError())
	}

	return nil
}
