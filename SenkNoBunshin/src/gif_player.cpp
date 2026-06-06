#include "gif_player.h"
#include "config.h"
#include "display.h"   // tft singleton

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

static WiFiClientSecure _gifSecClient;
static bool _secInit = false;

// ── Shared control ────────────────────────────────────────────────────────
static volatile bool   _gifRunning  = false;
static char            _gifName[32] = "stare";  // current GIF to play
static SemaphoreHandle_t _gifMutex  = nullptr;

// Frame buffer: 160×128×2 = 40 960 bytes — allocated once
static uint16_t* _frameBuf = nullptr;

// ── Helpers ───────────────────────────────────────────────────────────────
static void _getGifName(char* out, size_t len) {
    xSemaphoreTake(_gifMutex, portMAX_DELAY);
    strncpy(out, _gifName, len);
    xSemaphoreGive(_gifMutex);
}

struct GifInfo { int frames; int delay_ms; };

static bool _fetchInfo(const char* name, GifInfo& info) {
    if (!_secInit) { _gifSecClient.setInsecure(); _secInit = true; }
    HTTPClient http;
    String url = String(SERVER_BASE) + "/senku/gif/" + name + "/info";
    
    bool ok = url.startsWith("https://") ? http.begin(_gifSecClient, url) : http.begin(url);
    if (!ok) {
        Serial.printf("[gif] http.begin failed for info: %s\n", url.c_str());
        return false;
    }
    
    http.setTimeout(8000);
    int code = http.GET();
    if (code != 200) { 
        Serial.printf("[gif] info GET returned %d (url: %s)\n", code, url.c_str());
        http.end(); 
        return false; 
    }

    DynamicJsonDocument doc(256);
    if (deserializeJson(doc, http.getString())) { http.end(); return false; }
    info.frames   = doc["frames"]   | 1;
    info.delay_ms = doc["delay_ms"] | 100;
    http.end();
    return true;
}

// ── Stream Reader ──────────────────────────────────────────────────────────
// Connects to the /stream endpoint and keeps the connection open.
static WiFiClient* _streamClient = nullptr;
static HTTPClient  _streamHttp;

static bool _openStream(const char* name) {
    if (_streamClient) {
        _streamHttp.end();
        _streamClient = nullptr;
    }
    if (!_secInit) { _gifSecClient.setInsecure(); _secInit = true; }
    
    String url = String(SERVER_BASE) + "/senku/gif/" + name + "/stream";
    bool ok = url.startsWith("https://") ? _streamHttp.begin(_gifSecClient, url) : _streamHttp.begin(url);
    if (!ok) return false;
    
    _streamHttp.setTimeout(8000);
    const char* headers[] = {"Content-Length", "X-Delay-Ms"};
    _streamHttp.collectHeaders(headers, 2);
    
    int code = _streamHttp.GET();
    if (code != 200) {
        _streamHttp.end();
        return false;
    }
    _streamClient = _streamHttp.getStreamPtr();
    return true;
}

static int _readNextStreamFrame() {
    if (!_streamClient || !_streamClient->connected()) return -1;
    
    // Read boundary headers
    String line;
    int delay_ms = 40;
    int content_len = 0;
    unsigned long t0 = millis();
    
    while (millis() - t0 < 5000) {
        line = _streamClient->readStringUntil('\n');
        line.trim();
        if (line.length() == 0) break; // End of headers
        if (line.startsWith("X-Delay-Ms:")) {
            delay_ms = line.substring(11).toInt();
        } else if (line.startsWith("Content-Length:")) {
            content_len = line.substring(15).toInt();
        }
    }
    
    if (content_len <= 0 || content_len > 160 * 128 * 2) return -1;
    if (delay_ms < 20) delay_ms = 40; // max 50fps
    
    // Read frame data
    size_t got = 0;
    t0 = millis();
    while (got < content_len && millis() - t0 < 8000) {
        if (_streamClient->available()) {
            uint8_t* dst = (uint8_t*)_frameBuf + got;
            int n = _streamClient->read(dst, content_len - got);
            if (n > 0) got += n;
        } else {
            delay(1);
        }
    }
    if (got < content_len) return -1;
    
    // Endian swap
    for (size_t i = 0; i < 160 * 128; i++) {
        uint8_t* p = (uint8_t*)&_frameBuf[i];
        uint8_t tmp = p[0]; p[0] = p[1]; p[1] = tmp;
    }
    
    // Read trailing \r\n after frame data
    _streamClient->readStringUntil('\n');
    return delay_ms;
}

// ── Task ─────────────────────────────────────────────────────────────────
void gifPlayerTask(void* pv) {
    char currentName[32] = "";

    for (;;) {
        if (!_gifRunning) { vTaskDelay(100 / portTICK_PERIOD_MS); continue; }
        if (WiFi.status() != WL_CONNECTED) { vTaskDelay(500 / portTICK_PERIOD_MS); continue; }

        // Check for GIF change
        char wanted[32];
        _getGifName(wanted, sizeof(wanted));

        if (strlen(wanted) == 0) {
            // Paused
            if (_streamClient) { _streamHttp.end(); _streamClient = nullptr; }
            currentName[0] = '\0';
            vTaskDelay(100 / portTICK_PERIOD_MS);
            continue;
        }

        if (strcmp(wanted, currentName) != 0) {
            Serial.printf("[gif] switching to '%s'\n", wanted);
            if (!_openStream(wanted)) {
                Serial.printf("[gif] failed to open stream for '%s'\n", wanted);
                vTaskDelay(2000 / portTICK_PERIOD_MS);
                continue;
            }
            strncpy(currentName, wanted, sizeof(currentName));
        }

        int delay_ms = _readNextStreamFrame();
        if (delay_ms < 0) {
            Serial.printf("[gif] stream read failed, reconnecting...\n");
            _streamHttp.end();
            _streamClient = nullptr;
            currentName[0] = '\0'; // Force reconnect next loop
            vTaskDelay(500 / portTICK_PERIOD_MS);
            continue;
        }

        tft.drawRGBBitmap(0, 0, _frameBuf, 160, 128);
        vTaskDelay(delay_ms / portTICK_PERIOD_MS);
    }
}

// ── Public API ────────────────────────────────────────────────────────────
void gifPlayerStart() {
    _frameBuf = (uint16_t*)malloc(160 * 128 * 2);
    if (!_frameBuf) {
        Serial.println("[gif] FATAL: cannot allocate frame buffer");
        return;
    }
    _gifMutex  = xSemaphoreCreateMutex();
    _gifRunning = true;
    xTaskCreatePinnedToCore(gifPlayerTask, "GIF", 8192, NULL, 1, NULL, 0);
    Serial.println("[gif] player started on Core 0");
}

void gifPlayerSetGif(const char* name) {
    if (!_gifMutex) return;
    xSemaphoreTake(_gifMutex, portMAX_DELAY);
    strncpy(_gifName, name ? name : "", sizeof(_gifName));
    xSemaphoreGive(_gifMutex);
}

void gifPlayerCycleNext() {
    if (!_gifMutex) return;
    // Find current index in cycle list
    char cur[32];
    _getGifName(cur, sizeof(cur));
    int idx = 0;
    for (int i = 0; i < GIF_CYCLE_LEN; i++) {
        if (strcmp(cur, GIF_CYCLE[i]) == 0) { idx = i; break; }
    }
    idx = (idx + 1) % GIF_CYCLE_LEN;
    gifPlayerSetGif(GIF_CYCLE[idx]);
    Serial.printf("[gif] cycled to '%s'\n", GIF_CYCLE[idx]);
}

void gifPlayerStop() {
    _gifRunning = false;
}
