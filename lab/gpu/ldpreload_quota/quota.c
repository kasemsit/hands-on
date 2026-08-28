#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

static size_t used = 0;
static const size_t QUOTA = 100 * 1024 * 1024;   // โควตา 100 MB

void *malloc(size_t size) {
    static void *(*real_malloc)(size_t) = NULL;
    if (!real_malloc) real_malloc = dlsym(RTLD_NEXT, "malloc");

    if (used + size > QUOTA) {                    // ← เกินโควตา
        fprintf(stderr, "  [shim] ปฏิเสธ %zu MB (ใช้ไป %zu/%zu MB)\n",
                size>>20, used>>20, QUOTA>>20);
        return NULL;                              // ← คืน OOM
    }
    used += size;
    return real_malloc(size);                     // ← ส่งต่อของจริง
}
