#include "network.h"
#include "display.h"   // appendToken()
#include "config.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Use an insecure client for the Cloudflare tunnel (no CA pinning needed —
// Cloudflare terminates TLS on their end; traffic to localhost is plain HTTP).
static WiFiClientSecure _secureClient;

static void _initClient() {
    _secureClient.setInsecure();   // skip certificate verification
}

// Helper: begin an HTTPClient on either http:// or https://
static bool _beginUrl(HTTPClient& http, const String& url) {
    if (url.startsWith("https://")) {
        _initClient();
        return http.begin(_secureClient, url);
    }
    return http.begin(url);
}

// ── Health check ─────────────────────────────────────────────
bool checkServerHealth() {
    if (WiFi.status() != WL_CONNECTED) return false;
    HTTPClient http;
    _beginUrl(http, String(SERVER_BASE) + "/senku/health");
    http.setTimeout(5000);
    int code = http.GET();
    http.end();
    return code == 200;
}

// ── Create thread ─────────────────────────────────────────────
bool createThread(String& outThreadId) {
    if (WiFi.status() != WL_CONNECTED) return false;

    HTTPClient http;
    _beginUrl(http, String(SERVER_BASE) + "/senku/create-thread");
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(8000);

    int code = http.POST("{}");
    if (code != 200) {
        Serial.printf("[network] create-thread HTTP %d\n", code);
        http.end();
        return false;
    }

    DynamicJsonDocument doc(256);
    DeserializationError err = deserializeJson(doc, http.getString());
    http.end();

    if (err || !doc.containsKey("thread_id")) {
        Serial.printf("[network] create-thread JSON error: %s\n", err.c_str());
        return false;
    }

    outThreadId = doc["thread_id"].as<String>();
    return outThreadId.length() > 0;
}

// ── Streaming respond ─────────────────────────────────────────
bool streamRespond(const String& query, const String& threadId) {
    if (WiFi.status() != WL_CONNECTED) return false;

    HTTPClient http;
    _beginUrl(http, String(SERVER_BASE) + "/senku/respond-stream");
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(STREAM_TIMEOUT_MS);

    // Build JSON body
    DynamicJsonDocument req(512);
    req["query"]     = query;
    req["thread_id"] = threadId;
    String body;
    serializeJson(req, body);

    int code = http.POST(body);
    if (code != 200) {
        Serial.printf("[network] respond-stream HTTP %d\n", code);
        http.end();
        return false;
    }

    // Read SSE lines (Stream* works for both WiFiClient and WiFiClientSecure)
    Stream*       stream   = http.getStreamPtr();
    String      lineBuf   = "";
    unsigned long deadline = millis() + STREAM_TIMEOUT_MS;
    bool          done     = false;

    while (http.connected() && millis() < deadline && !done) {
        if (stream->available()) {
            char c = stream->read();
            if (c == '\n') {
                // Process complete SSE line
                if (lineBuf.startsWith("data: ")) {
                    String data = lineBuf.substring(6);
                    data.trim();

                    if (data == "[DONE]") {
                        done = true;
                    } else {
                        DynamicJsonDocument ev(512);
                        if (!deserializeJson(ev, data)) {
                            if (ev.containsKey("token")) {
                                String tok = ev["token"].as<String>();
                                Serial.print(tok);
                                appendToken(tok);
                            }
                        }
                    }
                }
                lineBuf = "";
            } else if (c != '\r') {
                lineBuf += c;
            }
        } else {
            delay(1);
        }
    }

    Serial.println();
    http.end();

    if (!done) {
        Serial.println("[network] respond-stream timed out or disconnected");
    }
    return done;
}
