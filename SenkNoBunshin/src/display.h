#pragma once
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include "config.h"

// ── Face expressions ─────────────────────────────────────────
enum FaceExpr { NORMAL, EXCITED, SMUG, TIRED };

// ── Streaming render state (used by appendToken) ─────────────
struct StreamState {
    int    x           = 2;
    int    y           = 16;
    String fullText    = "";
    bool   headerDrawn = false;
};

// ── Singleton TFT object (defined in display.cpp) ────────────
extern Adafruit_ST7735 tft;
extern StreamState      ss;

// ── Init ─────────────────────────────────────────────────────
void displayInit();

// ── Full-screen faces ────────────────────────────────────────
void drawSenkuFace(FaceExpr expr, bool blink);
void drawSleepFace();

// ── Transient screens ────────────────────────────────────────
void showBoot(const char* msg);
void showQuery(const String& q);
void showError(const char* msg);
void showDone();

// ── Streaming helpers ────────────────────────────────────────
void streamScreenHeader(const String& q);
void appendToken(const String& token);
