#include "parser.h"
#include <stdio.h>
#include <string.h>

const char test_buf1[] = "add@/devices/pci0000:00/.../usb1/1-1/1-1.4\0"
                   "ACTION=add\0"
                   "DEVPATH=/devices/pci0000:00/.../usb1/1-1/1-1.4\0"
                   "SUBSYSTEM=usb\0"
                   "DEVTYPE=usb_device\0"
                   "DEVNAME=/dev/bus/usb/001/005\0"
                   "PRODUCT=46d/c52b/1100\0";

const char test_buf2[] = "remove@/devices/.../1-1.4\0"
                          "ACTION=remove\0"
                          "DEVPATH=/devices/.../1-1.4\0"
                          "SUBSYSTEM=usb\0"
                          "DEVTYPE=usb_device\0";


int main(void) {
    uevent_info info;
    memset(&info, 0, sizeof(info));

    size_t len = sizeof(test_buf2);

    int ret = uevent_parse(test_buf2, len, &info);
    printf("parse result: %d\n", ret);
    printf("ACTION=%s\n", info.action);
    printf("SUBSYSTEM=%s\n", info.subsystem);
    printf("DEVTYPE=%s\n", info.devtype);
    printf("DEVPATH=%s\n", info.devpath);

    int target = uevent_target(&info);
    printf("is_target: %d\n", target);

    return 0;
}