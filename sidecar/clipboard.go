package main

var clipboardAvailable bool

func initClipboard() {
	clipboardAvailable = testClipboard()
}

func ClipboardGet() (string, error) {
	return clipboardGet()
}

func ClipboardSet(text string) error {
	return clipboardSet(text)
}
