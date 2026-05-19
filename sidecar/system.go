package main

import (
	"os"
	"runtime"
	"time"
)

type ProcessInfo struct {
	PID  int     `json:"pid"`
	Name string  `json:"name"`
	CPU  float64 `json:"cpu_percent"`
	RAM  uint64  `json:"ram_bytes"`
}

type WindowInfo struct {
	Title          string `json:"title"`
	ProcessName    string `json:"process_name"`
	ExecutablePath string `json:"executable_path"`
	PID            int    `json:"pid"`
}

var startTime = time.Now()

func GetSystemInfo() map[string]any {
	hostname, _ := os.Hostname()
	info := map[string]any{
		"hostname":     hostname,
		"os":           runtime.GOOS,
		"architecture": runtime.GOARCH,
		"cpu_cores":    runtime.NumCPU(),
		"go_version":   runtime.Version(),
		"uptime_sec":   int64(time.Since(startTime).Seconds()),
	}

	memTotal, memUsed := getMemoryUsage()
	diskTotal, diskFree := getDiskUsage()

	info["ram_total_bytes"] = memTotal
	info["ram_used_bytes"] = memUsed
	info["ram_free_bytes"] = memTotal - memUsed
	info["disk_total_bytes"] = diskTotal
	info["disk_free_bytes"] = diskFree
	info["disk_used_bytes"] = diskTotal - diskFree

	return info
}

func getUptime() int64 {
	return int64(time.Since(startTime).Seconds())
}
