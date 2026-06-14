#ifndef PARSER_H
#define PARSER_H

#include <stddef.h>

#define MAX_FIELD_LEN 256

typedef struct {
    char action[16];
    char subsystem[16];
    char devtype[32];
    char devpath[MAX_FIELD_LEN];
} uevent_info;

int uevent_parse(const char *buf, size_t len, uevent_info *out);
int uevent_target(const uevent_info *info);

#endif