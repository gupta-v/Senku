#pragma once

// ── TFT PINS ────────────────────────────────────────────────
#define TFT_CS 5
#define TFT_RST 4
#define TFT_DC 22
#define TFT_MOSI 23
#define TFT_SCLK 18

// ── COLOURS ─────────────────────────────────────────────────
#define C_BG 0x0000u // black
#define C_WHITE 0xFFFFu
#define C_GOLD 0xFEA0u   // spiky-hair highlight
#define C_SKIN 0xFDD6u   // face
#define C_HAIR 0x8C00u   // dark brown
#define C_ACCENT 0x07FFu // cyan — "ten billion percent"
#define C_DIM 0x4228u    // grey

// ── NETWORK ─────────────────────────────────────────────────
#define WIFI_SSID "Edith-LOQ"
#define WIFI_PASSWORD "12345678"
#define SERVER_BASE                                                            \
  "https://conclusions-drink-parliament-gratis.trycloudflare.com"

// ── TOUCH ───────────────────────────────────────────────────
#define TOUCH_PIN 27
#define TOUCH_THRESHOLD 35 // lower = touched
#define DEBOUNCE_MS 60

// ── THREAD / SLEEP ──────────────────────────────────────────
#define SLEEP_TIMEOUT_MS (2UL * 60UL * 1000UL) // 2 minutes
#define STREAM_TIMEOUT_MS 60000UL              // 60 s max per response
