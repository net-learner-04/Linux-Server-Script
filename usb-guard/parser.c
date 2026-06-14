#include "parser.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define MAX_FIELD_LEN 256

typedef struct {
    char action[16];
    char subsystem[16];
    char devtype[32]; 
    char devpath[MAX_FIELD_LEN];
} uevent_info;

/* size_t : 메모리나 객체의 크기를 바이트 단위로 나타내기 위해
 사용하는 부호 없는(unsigned) 정수 자료형 */

int uevent_parse(const char *buf, size_t len, uevent_info *out) {
    for (const char *p = buf; p < buf + len; p += strlen(p) + 1) {
        const char *eq = strchr(p, '=');

        if (eq == NULL) continue;

        size_t key_len = eq - p;
        const char *value = eq + 1;

        if (key_len == 6 && strncmp(p, "ACTION", 6) == 0) {
            strncpy(out->action, value, sizeof(out->action) - 1);
            out->action[sizeof(out->action) - 1] = '\0';
        } else if (key_len == 7 && strncmp(p, "DEVPATH", 7) == 0) {
            strncpy(out->devpath, value, sizeof(out->devpath) - 1);
            out->devpath[sizeof(out->devpath) - 1] = '\0';
        } else if (key_len == 9 && strncmp(p, "SUBSYSTEM", 9) == 0) {
            strncpy(out->subsystem, value, sizeof(out->subsystem) - 1);
            out->subsystem[sizeof(out->subsystem) - 1] = '\0';
        } else if (key_len == 7 && strncmp(p, "DEVTYPE", 7) == 0) {
            strncpy(out->devtype, value, sizeof(out->devtype) - 1);
            out->devtype[sizeof(out->devtype) - 1] = '\0';
        }
    }
    
    return 0;
}

int uevent_target(const uevent_info *info) {
    if (strcmp(info->action, "add") == 0 &&
     strcmp(info->subsystem, "usb") == 0 &&
      strcmp(info->devtype, "usb_device") == 0) {
        return 1;
    } else {
        return 0;
    }
}