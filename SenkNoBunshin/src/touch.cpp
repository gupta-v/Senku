#include "touch.h"
#include "config.h"

// Definition of shared volatile
volatile bool touchWake = false;

void touchTaskCode(void* pv) {
    bool         isTouched = false;
    unsigned long pressStart = 0;

    for (;;) {
        // Average 4 readings to reduce noise
        long sum = 0;
        for (int i = 0; i < 4; i++) {
            sum += touchRead(TOUCH_PIN);
            vTaskDelay(2 / portTICK_PERIOD_MS);
        }
        int  val = sum / 4;
        bool raw = (val < TOUCH_THRESHOLD);

        if (raw && !isTouched) {
            isTouched  = true;
            pressStart = millis();
        } else if (!raw && isTouched) {
            unsigned long dur = millis() - pressStart;
            if (dur > DEBOUNCE_MS) {
                touchWake = true;   // signal main loop
            }
            isTouched = false;
        }

        vTaskDelay(10 / portTICK_PERIOD_MS);
    }
}
