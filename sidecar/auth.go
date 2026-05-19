package main

import (
	"crypto/ed25519"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"os"
	"strings"
	"time"
)

type Claims struct {
	Sub  string   `json:"sub"`
	Iat  int64    `json:"iat"`
	Exp  int64    `json:"exp"`
	Caps []string `json:"caps"`
}

type Identity struct {
	Name         string
	Capabilities []string
}

var verifyKey ed25519.PublicKey

func initAuth() {
	keyB64 := os.Getenv("FRIDAY_SIDECAR_PUBLIC_KEY")
	if keyB64 == "" {
		log.Printf("[AUTH] No FRIDAY_SIDECAR_PUBLIC_KEY set, using development key")
		keyB64 = developmentPublicKey()
	}
	raw, err := base64.StdEncoding.DecodeString(keyB64)
	if err != nil {
		log.Fatalf("[AUTH] Invalid FRIDAY_SIDECAR_PUBLIC_KEY: %v", err)
	}
	if len(raw) != ed25519.PublicKeySize {
		log.Fatalf("[AUTH] Bad key length: got %d, want %d", len(raw), ed25519.PublicKeySize)
	}
	verifyKey = ed25519.PublicKey(raw)
	log.Printf("[AUTH] Public key loaded (%d bytes)", len(raw))
}

func developmentPublicKey() string {
	return "MCowBQYDK2VwAyEAf4QJGZyYoSN+LvK3qChcHWQVrVvsDs8TqgD6+0r6TAk="
}

func verifyToken(tokenStr string) (*Identity, error) {
	if verifyKey == nil {
		return nil, errors.New("auth not initialized")
	}

	parts := strings.Split(tokenStr, ".")
	if len(parts) != 3 {
		return nil, errors.New("invalid JWT: expected 3 parts")
	}

	headerJSON, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return nil, fmt.Errorf("invalid JWT header: %w", err)
	}

	var header struct {
		Alg string `json:"alg"`
		Typ string `json:"typ"`
	}
	if err := json.Unmarshal(headerJSON, &header); err != nil {
		return nil, fmt.Errorf("invalid JWT header json: %w", err)
	}
	if header.Alg != "EdDSA" {
		return nil, fmt.Errorf("unexpected algorithm: %s", header.Alg)
	}

	payloadJSON, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, fmt.Errorf("invalid JWT payload: %w", err)
	}

	var claims Claims
	if err := json.Unmarshal(payloadJSON, &claims); err != nil {
		return nil, fmt.Errorf("invalid JWT claims: %w", err)
	}

	now := time.Now().Unix()
	if now > claims.Exp {
		return nil, errors.New("token expired")
	}
	if now < claims.Iat-30 {
		return nil, errors.New("token not yet valid")
	}

	sig, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return nil, fmt.Errorf("invalid JWT signature: %w", err)
	}

	msg := []byte(parts[0] + "." + parts[1])
	if !ed25519.Verify(verifyKey, msg, sig) {
		return nil, errors.New("invalid JWT signature")
	}

	return &Identity{
		Name:         claims.Sub,
		Capabilities: claims.Caps,
	}, nil
}
