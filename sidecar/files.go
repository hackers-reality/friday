package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
)

type FileInfo struct {
	Name    string `json:"name"`
	Size    int64  `json:"size"`
	IsDir   bool   `json:"is_dir"`
	ModTime string `json:"mod_time"`
}

var allowedPaths []string

func init() {
	env := os.Getenv("FRIDAY_SIDECAR_ALLOWED_PATHS")
	if env != "" {
		allowedPaths = strings.Split(env, string(os.PathListSeparator))
		for i := range allowedPaths {
			allowedPaths[i] = filepath.Clean(allowedPaths[i])
		}
		log.Printf("[FILES] Allowed paths: %v", allowedPaths)
	}
}

func resolvePath(path string) (string, error) {
	abs, err := filepath.Abs(path)
	if err != nil {
		return "", fmt.Errorf("cannot resolve path: %w", err)
	}
	abs = filepath.Clean(abs)

	if len(allowedPaths) == 0 {
		return abs, nil
	}

	for _, allowed := range allowedPaths {
		rel, err := filepath.Rel(allowed, abs)
		if err == nil && !strings.HasPrefix(rel, "..") {
			return abs, nil
		}
	}
	return "", fmt.Errorf("path not allowed: %s", abs)
}

func ReadFile(path string) (string, error) {
	p, err := resolvePath(path)
	if err != nil {
		return "", err
	}
	data, err := os.ReadFile(p)
	if err != nil {
		return "", fmt.Errorf("read file: %w", err)
	}
	return string(data), nil
}

func ReadFileBytes(path string) ([]byte, error) {
	p, err := resolvePath(path)
	if err != nil {
		return nil, err
	}
	return os.ReadFile(p)
}

func WriteFile(path, content string) error {
	p, err := resolvePath(path)
	if err != nil {
		return err
	}
	if err := os.WriteFile(p, []byte(content), 0644); err != nil {
		return fmt.Errorf("write file: %w", err)
	}
	return nil
}

func ListDir(path string) ([]FileInfo, error) {
	p, err := resolvePath(path)
	if err != nil {
		return nil, err
	}
	entries, err := os.ReadDir(p)
	if err != nil {
		return nil, fmt.Errorf("list dir: %w", err)
	}
	infos := make([]FileInfo, 0, len(entries))
	for _, e := range entries {
		info, err := e.Info()
		if err != nil {
			continue
		}
		infos = append(infos, FileInfo{
			Name:    e.Name(),
			Size:    info.Size(),
			IsDir:   e.IsDir(),
			ModTime: info.ModTime().Format("2006-01-02T15:04:05Z"),
		})
	}
	return infos, nil
}

func DeleteFile(path string) error {
	p, err := resolvePath(path)
	if err != nil {
		return err
	}
	if err := os.RemoveAll(p); err != nil {
		return fmt.Errorf("delete file: %w", err)
	}
	return nil
}

func Stat(path string) (FileInfo, error) {
	p, err := resolvePath(path)
	if err != nil {
		return FileInfo{}, err
	}
	info, err := os.Stat(p)
	if err != nil {
		return FileInfo{}, fmt.Errorf("stat: %w", err)
	}
	return FileInfo{
		Name:    info.Name(),
		Size:    info.Size(),
		IsDir:   info.IsDir(),
		ModTime: info.ModTime().Format("2006-01-02T15:04:05Z"),
	}, nil
}
