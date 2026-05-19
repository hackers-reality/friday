//go:build windows

package main

import (
	"fmt"
	"log"
	"syscall"
	"unsafe"
)

var (
	kernel32Sys           = syscall.NewLazyDLL("kernel32.dll")
	psapi                 = syscall.NewLazyDLL("psapi.dll")
	procGlobalMemoryStatusEx = kernel32Sys.NewProc("GlobalMemoryStatusEx")
	procGetDiskFreeSpaceEx  = kernel32Sys.NewProc("GetDiskFreeSpaceExW")
	procOpenProcess         = kernel32Sys.NewProc("OpenProcess")
	procCloseHandle         = kernel32Sys.NewProc("CloseHandle")
	procEnumProcesses       = psapi.NewProc("EnumProcesses")
	procGetModuleBaseNameW  = psapi.NewProc("GetModuleBaseNameW")
	procGetProcessImageFileNameW = psapi.NewProc("GetProcessImageFileNameW")
	user32Sys               = syscall.NewLazyDLL("user32.dll")
	procGetForegroundWindow   = user32Sys.NewProc("GetForegroundWindow")
	procGetWindowTextW        = user32Sys.NewProc("GetWindowTextW")
	procGetWindowThreadProcessId = user32Sys.NewProc("GetWindowThreadProcessId")
)

type memoryStatusEx struct {
	dwLength                uint32
	dwMemoryLoad            uint32
	ullTotalPhys            uint64
	ullAvailPhys            uint64
	ullTotalPageFile        uint64
	ullAvailPageFile        uint64
	ullTotalVirtual         uint64
	ullAvailVirtual         uint64
	ullAvailExtendedVirtual uint64
}

func getMemoryUsage() (total, used uint64) {
	var mem memoryStatusEx
	mem.dwLength = uint32(unsafe.Sizeof(mem))
	ret, _, _ := procGlobalMemoryStatusEx.Call(uintptr(unsafe.Pointer(&mem)))
	if ret == 0 {
		return 0, 0
	}
	return mem.ullTotalPhys, mem.ullTotalPhys - mem.ullAvailPhys
}

func getDiskUsage() (total, free uint64) {
	path, err := syscall.UTF16PtrFromString("C:\\")
	if err != nil {
		return 0, 0
	}
	var freeBytes, totalBytes, totalFree uint64
	ret, _, _ := procGetDiskFreeSpaceEx.Call(
		uintptr(unsafe.Pointer(path)),
		uintptr(unsafe.Pointer(&freeBytes)),
		uintptr(unsafe.Pointer(&totalBytes)),
		uintptr(unsafe.Pointer(&totalFree)),
	)
	if ret == 0 {
		return 0, 0
	}
	return totalBytes, freeBytes
}

func GetProcesses() []ProcessInfo {
	pids := make([]uint32, 2048)
	var needed uint32
	ret, _, _ := procEnumProcesses.Call(
		uintptr(unsafe.Pointer(&pids[0])),
		uintptr(len(pids))*4,
		uintptr(unsafe.Pointer(&needed)),
	)
	if ret == 0 {
		return nil
	}

	count := int(needed / 4)
	processes := make([]ProcessInfo, 0, count)

	for i := 0; i < count && i < len(pids); i++ {
		pid := pids[i]
		if pid == 0 {
			continue
		}

		handle, _, _ := procOpenProcess.Call(
			0x0400|0x0010, // PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
			0,
			uintptr(pid),
		)
		if handle == 0 {
			continue
		}

		var exeName [260]uint16
		procGetModuleBaseNameW.Call(handle, 0, uintptr(unsafe.Pointer(&exeName[0])), uintptr(len(exeName)))
		procCloseHandle.Call(handle)

		name := syscall.UTF16ToString(exeName[:])
		if name == "" {
			continue
		}

		processes = append(processes, ProcessInfo{
			PID:  int(pid),
			Name: name,
		})
	}

	return processes
}

func GetActiveWindow() WindowInfo {
	hwnd, _, _ := procGetForegroundWindow.Call()
	if hwnd == 0 {
		return WindowInfo{}
	}

	var title [512]uint16
	procGetWindowTextW.Call(hwnd, uintptr(unsafe.Pointer(&title[0])), uintptr(len(title)))

	var pid uint32
	procGetWindowThreadProcessId.Call(hwnd, uintptr(unsafe.Pointer(&pid)))

	processName := ""
	exePath := ""
	handle, _, _ := procOpenProcess.Call(0x0400|0x0010, 0, uintptr(pid))
	if handle != 0 {
		var exeName [260]uint16
		procGetModuleBaseNameW.Call(handle, 0, uintptr(unsafe.Pointer(&exeName[0])), uintptr(len(exeName)))
		processName = syscall.UTF16ToString(exeName[:])

		var pathBuf [260]uint16
		procGetProcessImageFileNameW.Call(handle, uintptr(unsafe.Pointer(&pathBuf[0])), uintptr(len(pathBuf)))
		exePath = syscall.UTF16ToString(pathBuf[:])

		procCloseHandle.Call(handle)
	}

	log.Printf("[SYSTEM] Active window: %q [PID=%d]", syscall.UTF16ToString(title[:]), pid)
	return WindowInfo{
		Title:          syscall.UTF16ToString(title[:]),
		ProcessName:    processName,
		ExecutablePath: exePath,
		PID:            int(pid),
	}
}

func GetProcessInfo(pid int) ProcessInfo {
	handle, _, _ := procOpenProcess.Call(
		0x0400|0x0010,
		0,
		uintptr(pid),
	)
	if handle == 0 {
		return ProcessInfo{PID: pid, Name: fmt.Sprintf("pid:%d (access denied)", pid)}
	}
	defer procCloseHandle.Call(handle)

	var exeName [260]uint16
	procGetModuleBaseNameW.Call(handle, 0, uintptr(unsafe.Pointer(&exeName[0])), uintptr(len(exeName)))

	return ProcessInfo{
		PID:  pid,
		Name: syscall.UTF16ToString(exeName[:]),
	}
}
