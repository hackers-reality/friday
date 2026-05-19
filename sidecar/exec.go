package main

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"log"
	"os/exec"
	"runtime"
	"strings"
	"time"
)

type ExecResult struct {
	Stdout     string `json:"stdout"`
	Stderr     string `json:"stderr"`
	ExitCode   int    `json:"exit_code"`
	DurationMs int64  `json:"duration_ms"`
}

func ExecuteCommand(command string, timeoutSec int) ExecResult {
	if timeoutSec <= 0 {
		timeoutSec = 30
	}
	start := time.Now()

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutSec)*time.Second)
	defer cancel()

	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.CommandContext(ctx, "cmd.exe", "/c", command)
	} else {
		cmd = exec.CommandContext(ctx, "/bin/sh", "-c", command)
	}

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	exitCode := 0
	err := cmd.Run()
	duration := time.Since(start).Milliseconds()

	if err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			exitCode = exitErr.ExitCode()
		} else if errors.Is(err, context.DeadlineExceeded) {
			exitCode = -1
			stderr.WriteString("\n[ERROR] Command timed out")
		} else {
			exitCode = -2
			stderr.WriteString(fmt.Sprintf("\n[ERROR] %v", err))
		}
	}

	out := strings.TrimRight(stdout.String(), "\r\n")
	serr := strings.TrimRight(stderr.String(), "\r\n")

	log.Printf("[EXEC] exit=%d duration=%dms cmd=%q", exitCode, duration, truncate(command, 120))
	return ExecResult{
		Stdout:     truncate(out, 100000),
		Stderr:     truncate(serr, 100000),
		ExitCode:   exitCode,
		DurationMs: duration,
	}
}

func ExecuteDetached(command string) (int, error) {
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd.exe", "/c", "start", "", command)
	} else {
		cmd = exec.Command("/bin/sh", "-c", command)
	}
	if err := cmd.Start(); err != nil {
		return 0, fmt.Errorf("detached exec: %w", err)
	}
	log.Printf("[EXEC] Detached PID=%d: %s", cmd.Process.Pid, truncate(command, 80))
	go cmd.Wait()
	return cmd.Process.Pid, nil
}

func truncate(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max] + "..."
}
