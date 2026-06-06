// ============================================================
//  SenkNoBunshin — main.cpp
// ============================================================
#include <Arduino.h>
#include <WiFi.h>

#include "config.h"
#include "display.h"
#include "network.h"
#include "touch.h"
#include "gif_player.h"

// ── System state ─────────────────────────────────────────────
enum SenkuMode {
    BOOT,
    IDLE_GIF,        // GIF playing, waiting for query
    THINKING,        // query sent — GIF paused, "Thinking..." shown
    STREAMING,       // tokens printing to TFT — GIF paused
    SHOW_RESPONSE,   // text stays on screen — response GIF plays
    SLEEPING,        // sleep GIF, thread cleared
    ERR_MODE
};
static SenkuMode mode = BOOT;

// ── Thread state ─────────────────────────────────────────────
static String        threadId     = "";
static bool          threadActive = false;
static unsigned long lastQueryMs  = 0;

// ── Serial input ──────────────────────────────────────────────
static String serialBuf = "";

// ── Response timer ────────────────────────────────────────────
static unsigned long responseShownAt = 0;

// ─────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial.println("\n=== SenkNoBunshin v2 ===");

    displayInit();
    showBoot("Connecting to WiFi...");

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 40) {
        delay(500); Serial.print('.'); tries++;
    }
    Serial.println();

    if (WiFi.status() != WL_CONNECTED) {
        showError("WiFi FAILED\nCheck SSID/password");
        mode = ERR_MODE;
        return;
    }

    Serial.printf("[WiFi] IP: %s\n", WiFi.localIP().toString().c_str());
    showBoot("WiFi OK!\n\nType a question\nin Serial Monitor\nand press Enter.");
    delay(1500);

    // Core 0: touch (priority 2) + GIF player (priority 1)
    xTaskCreatePinnedToCore(touchTaskCode, "Touch", 4096,  NULL, 2, NULL, 0);
    gifPlayerStart();   // starts its own task on Core 0

    lastQueryMs = millis();
    mode = IDLE_GIF;
    gifPlayerSetGif(GIF_CYCLE[0]);   // start with first GIF in cycle
}

// ─────────────────────────────────────────────────────────────
void loop() {
    unsigned long now = millis();

    // ── 1. Touch ──────────────────────────────────────────────
    if (touchWake) {
        touchWake = false;
        lastQueryMs = millis();   // reset idle timer on any touch

        if (mode == SLEEPING) {
            // Wake: resume GIF cycle
            Serial.println("[touch] Woken from sleep");
            mode = IDLE_GIF;
            gifPlayerSetGif(GIF_CYCLE[0]);
        } else if (mode == IDLE_GIF) {
            // Cycle to next expression
            gifPlayerCycleNext();
        } else if (mode == SHOW_RESPONSE) {
            // Dismiss response text → back to idle GIF
            mode = IDLE_GIF;
            gifPlayerSetGif(GIF_CYCLE[0]);
        }
    }

    // ── 2. SHOW_RESPONSE → IDLE after 2 min ──────────────────
    if (mode == SHOW_RESPONSE && (now - responseShownAt > SLEEP_TIMEOUT_MS)) {
        Serial.println("[response] Timeout — returning to idle GIF");
        mode = IDLE_GIF;
        gifPlayerSetGif(GIF_CYCLE[0]);
    }

    // ── 3. Auto-sleep after inactivity ───────────────────────
    if ((mode == IDLE_GIF) && (now - lastQueryMs > SLEEP_TIMEOUT_MS)) {
        threadActive = false;
        threadId     = "";
        gifPlayerSetGif(GIF_SLEEP);
        Serial.println("[sleep] Thread cleared. Sleeping.");
        mode = SLEEPING;
        return;
    }

    // ── 4. Serial input ───────────────────────────────────────
    while (Serial.available()) {
        char c = Serial.read();

        if (c == '\n' || c == '\r') {
            serialBuf.trim();
            if (serialBuf.length() == 0) { serialBuf = ""; continue; }

            if (mode == THINKING || mode == STREAMING) {
                Serial.println("[warn] Busy — ignoring input");
                serialBuf = "";
                continue;
            }

            String query = serialBuf;
            serialBuf = "";

            Serial.printf("[query] %s\n", query.c_str());
            lastQueryMs = millis();

            // Pause GIF, show query text on TFT
            gifPlayerSetGif("");
            showQuery(query);
            mode = THINKING;

            // Create thread if needed
            if (!threadActive) {
                Serial.println("[thread] Creating new thread...");
                if (!createThread(threadId)) {
                    showError("Thread create\nfailed");
                    mode = ERR_MODE;
                    return;
                }
                threadActive = true;
                Serial.printf("[thread] id=%s\n", threadId.c_str());
            } else {
                Serial.printf("[thread] Reusing id=%s\n", threadId.c_str());
            }

            // Stream response tokens to TFT (GIF stays paused)
            streamScreenHeader(query);
            mode = STREAMING;

            bool ok = streamRespond(query, threadId);

            if (ok) {
                showDone();
                lastQueryMs      = millis();
                responseShownAt  = millis();
                mode = SHOW_RESPONSE;
                gifPlayerSetGif(GIF_CYCLE[1]);  // play next expression during response
            } else {
                showError("Stream failed.\nCheck server.");
                mode = ERR_MODE;
            }

        } else {
            Serial.print(c);   // echo back
            serialBuf += c;
        }
    }

    delay(50);
}