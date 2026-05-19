//go:build !windows

package main

func getMemoryUsage() (total, used uint64) {
	return 0, 0
}

func getDiskUsage() (total, free uint64) {
	return 0, 0
}

func GetProcesses() []ProcessInfo {
	return nil
}

func GetActiveWindow() WindowInfo {
	return WindowInfo{}
}

func GetProcessInfo(pid int) ProcessInfo {
	return ProcessInfo{PID: pid}
}
